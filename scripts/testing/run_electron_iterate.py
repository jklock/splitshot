#!/usr/bin/env python3
"""Run the cheapest valid Electron proof tier for iterative SplitShot validation."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from splitshot.domain.models import Project
from splitshot.persistence.projects import save_project

ROOT = Path(__file__).resolve().parents[2]
TMP_ROOT = ROOT / "tmp" / "codex"
DEFAULT_ARTIFACT_ROOT = ROOT / "artifacts" / "electron-iterate"
DEFAULT_WORKFLOW_PROJECT = ROOT / "05072026"
DEFAULT_INSTALLED_APP = Path("/Applications/SplitShot.app")
DEFAULT_UNPACKED_APP = ROOT / "electron" / "build" / "mac-arm64" / "SplitShot.app"
SOURCE_SCENARIOS = (
    "startup",
    "project",
    "media",
    "compose",
    "trim",
    "score",
    "splits",
    "markers",
    "overlay",
    "review",
    "export",
    "queue",
    "metrics",
    "shotml",
    "settings",
)
PACKAGED_SCENARIOS = ("launch", "panes", "trim", "queue-individual", "queue-combined", "full")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run SplitShot Electron proof on the cheapest valid tier.",
    )
    parser.add_argument("--tier", choices=("source", "unpacked", "installed"), required=True)
    parser.add_argument(
        "--scenario",
        action="append",
        dest="scenarios",
        help="Scenario or audit slice to run. Repeat for multiple source scenarios.",
    )
    parser.add_argument("--app", type=Path, default=None)
    parser.add_argument("--project-path", type=Path, default=None)
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument(
        "--build-if-needed",
        action="store_true",
        default=False,
        help="For unpacked tier, rebuild the local .app when missing or stale.",
    )
    return parser


def _env() -> dict[str, str]:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "TMPDIR": str(TMP_ROOT),
            "TMP": str(TMP_ROOT),
            "TEMP": str(TMP_ROOT),
            "SPLITSHOT_SETTINGS_PATH": str(TMP_ROOT / "electron-iterate-settings.json"),
        }
    )
    return env


def _default_scenarios(tier: str) -> list[str]:
    if tier == "source":
        return ["startup"]
    if tier == "unpacked":
        return ["launch"]
    return ["full"]


def _resolve_scenarios(tier: str, scenarios: list[str] | None) -> list[str]:
    resolved = list(scenarios or _default_scenarios(tier))
    valid = SOURCE_SCENARIOS if tier == "source" else PACKAGED_SCENARIOS
    invalid = [item for item in resolved if item not in valid]
    if invalid:
        raise SystemExit(f"Unsupported {tier} scenario(s): {', '.join(invalid)}")
    return resolved


def _quick_project_name(tier: str, scenarios: list[str]) -> str:
    return f"{tier}-{'-'.join(scenarios)}"


def _create_quick_project_bundle(name: str) -> Path:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    project_path = TMP_ROOT / f"{name}.ssproj"
    if project_path.exists():
        return project_path
    save_project(Project(name=name), project_path)
    return project_path


def _copy_project_tree(source_root: Path, bundle_root: Path) -> None:
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    bundle_root.parent.mkdir(parents=True, exist_ok=True)
    bundle_root.mkdir(parents=True, exist_ok=True)
    for path in source_root.rglob("*"):
        relative = path.relative_to(source_root)
        destination = bundle_root / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() in {".mp4", ".mov", ".m4v", ".mkv"}:
            try:
                destination.hardlink_to(path)
                continue
            except OSError:
                pass
        shutil.copy2(path, destination)


def _materialize_project_bundle(source_path: Path, *, slug: str) -> Path:
    resolved = source_path.expanduser().resolve()
    if resolved.suffix == ".ssproj":
        return resolved
    if not resolved.is_dir():
        return resolved
    bundle_root = TMP_ROOT / f"{slug}.ssproj"
    _copy_project_tree(resolved, bundle_root)
    return bundle_root


def _resolve_project_path(project_path: Path | None, tier: str, scenarios: list[str]) -> Path:
    if project_path is not None:
        return _materialize_project_bundle(
            project_path,
            slug=f"{tier}-custom-{'-'.join(scenarios)}",
        ).resolve()
    if tier == "source" and scenarios == ["startup"]:
        return _create_quick_project_bundle(_quick_project_name(tier, scenarios)).resolve()
    if tier in {"unpacked", "installed"} and scenarios == ["launch"]:
        return _create_quick_project_bundle(_quick_project_name(tier, scenarios)).resolve()
    if not DEFAULT_WORKFLOW_PROJECT.is_dir():
        raise SystemExit(
            "Workflow proof requires --project-path pointing to a real project; "
            f"the former local-only fixture is unavailable: {DEFAULT_WORKFLOW_PROJECT}"
        )
    return _materialize_project_bundle(
        DEFAULT_WORKFLOW_PROJECT,
        slug=f"{tier}-workflow-{'-'.join(scenarios)}",
    ).resolve()


def _resolve_app_path(tier: str, app: Path | None) -> Path | None:
    if tier == "source":
        return None
    if app is not None:
        return app.expanduser().resolve()
    if tier == "unpacked":
        return DEFAULT_UNPACKED_APP.resolve()
    return DEFAULT_INSTALLED_APP.resolve()


def _latest_mtime(paths: list[Path]) -> float:
    latest = 0.0
    for path in paths:
        if not path.exists():
            continue
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file():
                    latest = max(latest, child.stat().st_mtime)
        elif path.is_file():
            latest = max(latest, path.stat().st_mtime)
    return latest


def _should_rebuild_unpacked_app(app_path: Path) -> bool:
    if not app_path.exists():
        return True
    app_mtime = _latest_mtime([app_path])
    input_mtime = _latest_mtime(
        [
            ROOT / "electron" / "main.js",
            ROOT / "electron" / "preload.js",
            ROOT / "electron" / "package.json",
            ROOT / "scripts" / "bundle-python.js",
            ROOT / "pyproject.toml",
            ROOT / "uv.lock",
            ROOT / "src" / "splitshot",
        ]
    )
    return app_mtime < input_mtime


def _run(command: list[str], *, env: dict[str, str]) -> None:
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def _run_source_scenarios(
    scenarios: list[str], artifact_root: Path, project_path: Path, env: dict[str, str]
) -> dict[str, object]:
    command = [
        "node",
        str(ROOT / "electron" / "tests" / "iterate.test.js"),
        "--artifacts",
        str(artifact_root),
        "--project-path",
        str(project_path),
    ]
    for scenario in scenarios:
        command.extend(["--scenario", scenario])
    _run(command, env=env)
    result_path = artifact_root / "source-electron-iterate.json"
    return json.loads(result_path.read_text(encoding="utf-8"))


def _run_packaged_slice(
    app_path: Path,
    slice_name: str,
    artifact_root: Path,
    project_path: Path,
    env: dict[str, str],
) -> dict[str, object]:
    if slice_name == "full":
        sub_slices = ["launch", "panes", "trim", "queue-individual", "queue-combined"]
        aggregate: dict[str, object] = {
            "artifact_root": str(artifact_root),
            "timestamp": datetime.now(UTC).isoformat(),
            "slice": "full",
            "app": str(app_path),
            "project_path": str(project_path),
            "slices": {},
            "findings": [],
        }
        artifact_root.mkdir(parents=True, exist_ok=True)
        for sub_slice in sub_slices:
            sub_root = artifact_root / sub_slice
            result = _run_packaged_slice(app_path, sub_slice, sub_root, project_path, env)
            aggregate["slices"][sub_slice] = result
            findings = result.get("findings")
            if isinstance(findings, list):
                aggregate["findings"].extend(findings)
        audit_path = artifact_root / "audit.json"
        audit_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
        return aggregate

    command = [
        "uv",
        "run",
        "python",
        "scripts/audits/browser/run_installed_app_pane_audit.py",
        "--app",
        str(app_path),
        "--project-path",
        str(project_path),
        "--artifact-root",
        str(artifact_root),
        "--slice",
        slice_name,
    ]
    _run(command, env=env)
    return json.loads((artifact_root / "audit.json").read_text(encoding="utf-8"))


def _build_unpacked_app(app_path: Path, env: dict[str, str]) -> None:
    if sys.platform != "darwin":
        return
    _run(["npm", "--prefix", "electron", "run", "build:app:mac"], env=env)
    if not app_path.exists():
        raise SystemExit(f"Expected unpacked app at {app_path}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    env = _env()
    artifact_root = args.artifact_root.expanduser().resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)
    scenarios = _resolve_scenarios(args.tier, args.scenarios)
    project_path = _resolve_project_path(args.project_path, args.tier, scenarios)

    result: dict[str, object] = {
        "tier": args.tier,
        "scenarios": scenarios,
        "project_path": str(project_path),
        "timestamp": datetime.now(UTC).isoformat(),
    }

    if args.tier == "source":
        result["result"] = _run_source_scenarios(scenarios, artifact_root, project_path, env)
    else:
        app_path = _resolve_app_path(args.tier, args.app)
        assert app_path is not None
        if args.tier == "unpacked" and (
            args.build_if_needed or _should_rebuild_unpacked_app(app_path)
        ):
            _build_unpacked_app(app_path, env)
        if not app_path.exists():
            raise SystemExit(f"App not found: {app_path}")
        slice_name = "full" if "full" in scenarios else scenarios[0]
        result["app"] = str(app_path)
        result["result"] = _run_packaged_slice(
            app_path, slice_name, artifact_root, project_path, env
        )

    output_path = artifact_root / "run-electron-iterate.json"
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
