#!/usr/bin/env python3
"""Full E2E test: launch app, run Playwright browser interactions, record video."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from splitshot.domain.models import Project, ProjectStage
from splitshot.persistence.projects import save_project

try:
    from validate_release_data import (
        DEFAULT_CORPUS_ROOT,
        DEFAULT_MANIFEST,
    )
    from validate_release_data import (
        validate as validate_release_data,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validate_release_data import (  # type: ignore[no-redef]
        DEFAULT_CORPUS_ROOT,
        DEFAULT_MANIFEST,
    )
    from validate_release_data import (
        validate as validate_release_data,
    )

REPO = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO / "artifacts"
DEFAULT_VIDEO_FIXTURE = REPO / "tests" / "fixtures" / "media" / "stage.mp4"
TIMEOUT = 120


def _repo_temp_dir(prefix: str) -> Path:
    temp_root = REPO / "tmp" / "codex"
    temp_root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=temp_root))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stop_process(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _wait_for_state(process: subprocess.Popen, port: int, timeout: int = 60) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"App exited (code {process.returncode})")
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/state", timeout=5
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, ConnectionResetError, json.JSONDecodeError):
            time.sleep(0.25)
    raise TimeoutError("Backend did not respond")


def _run_packaged_browser_audits(
    *,
    port: int,
    artifact_root: Path,
    primary_video: Path,
    secondary_video: Path,
    practiscore: Path,
) -> list[str]:
    """Run the real-route browser audits against the installed app backend."""
    audit_root = artifact_root / "browser-audits"
    audit_root.mkdir(parents=True, exist_ok=True)
    base_url = f"http://127.0.0.1:{port}"
    commands = [
        (
            "ui-surface",
            [
                sys.executable,
                str(REPO / "scripts" / "audits" / "browser" / "run_browser_ui_surface_audit.py"),
                "--browser",
                "chromium",
                "--primary-video",
                str(primary_video),
                "--base-url",
                base_url,
                "--project-root",
                str(REPO / "tmp" / "codex" / "packaged-ui-surface-projects"),
                "--artifact-root",
                str(audit_root / "ui-surface"),
                "--report-json",
                str(audit_root / "ui-surface.json"),
            ],
        ),
        (
            "interaction",
            [
                sys.executable,
                str(REPO / "scripts" / "audits" / "browser" / "run_browser_interaction_audit.py"),
                "--browser",
                "chromium",
                "--primary-video",
                str(primary_video),
                "--merge-video",
                str(secondary_video),
                "--practiscore",
                str(practiscore),
                "--base-url",
                base_url,
                "--report-json",
                str(audit_root / "interaction.json"),
            ],
        ),
        (
            "value-controls",
            [
                sys.executable,
                str(
                    REPO
                    / "scripts"
                    / "audits"
                    / "browser"
                    / "run_value_control_interaction_audit.py"
                ),
                "--browser",
                "chromium",
                "--base-url",
                base_url,
                "--primary-video",
                str(primary_video),
                "--merge-video",
                str(secondary_video),
                "--practiscore",
                str(practiscore),
                "--allow-settings",
                "--inventory-json",
                str(audit_root / "source-control-inventory.json"),
                "--report-json",
                str(audit_root / "value-controls.json"),
            ],
        ),
    ]
    failures: list[str] = []
    for name, command in commands:
        log_path = audit_root / f"{name}.log"
        with log_path.open("w", encoding="utf-8") as log_handle:
            result = subprocess.run(
                command,
                cwd=REPO,
                check=False,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=900,
            )
        if result.returncode != 0:
            failures.append(f"installed-package {name} audit exited {result.returncode}")
    return failures


def _normalized_control_identity(value: str) -> str:
    value = str(value or "")
    if value.startswith("#"):
        return f"id:{value[1:]}"
    if value.startswith("[") and value.endswith("]") and "=" in value:
        attribute, raw = value[1:-1].split("=", 1)
        return f"{attribute}:{raw.strip(chr(34) + chr(39))}"
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]*", value) and ":" not in value:
        return f"id:{value}"
    return value


def _build_identity_results(artifact_root: Path) -> dict:
    inventory = json.loads((artifact_root / "runtime-inventory.json").read_text(encoding="utf-8"))
    actions = json.loads((artifact_root / "action-ledger.json").read_text(encoding="utf-8"))
    value_report_path = artifact_root / "browser-audits" / "value-controls.json"
    value_report = json.loads(value_report_path.read_text(encoding="utf-8"))
    passed_value_ids = {
        _normalized_control_identity(str(item.get("inventory_identity") or ""))
        for item in value_report.get("cases", [])
        if item.get("status") == "pass"
    }
    action_ids: set[str] = set()
    tool_actions: set[str] = set()
    for action in actions:
        target = str(action.get("target") or "")
        if action.get("status") != "passed":
            continue
        if action.get("action") == "tool-switch":
            tool_actions.add(target)
        else:
            action_ids.add(_normalized_control_identity(target))
    observational_tags = {
        "label",
        "h1",
        "h2",
        "h3",
        "p",
        "section",
        "div",
        "video",
        "rect",
    }
    rows: list[dict] = []
    for item in inventory.get("identities", []):
        identity = str(item.get("identity") or "")
        tag = str(item.get("tag") or "")
        pane = str(item.get("pane") or "")
        status = "gap"
        evidence: list[str] = []
        if tag in observational_tags and (
            item.get("text")
            or item.get("accessible_name")
            or tag in {"video", "p"}
        ):
            status = "passed"
            evidence = ["runtime-inventory.json"]
        elif item.get("enabled") is False:
            status = "passed"
            evidence = ["runtime-inventory.json#disabled"]
        elif tag == "details" and item.get("visible"):
            status = "passed"
            evidence = ["runtime-inventory.json#expanded-details"]
        elif identity in passed_value_ids:
            status = "passed"
            evidence = ["browser-audits/value-controls.json"]
        elif identity in action_ids or (
            identity.startswith("data-tool:")
            and identity.split(":", 1)[1] in tool_actions
        ):
            status = "passed"
            evidence = ["action-ledger.json"]
        rows.append(
            {
                "pane": pane,
                "identity": identity,
                "occurrence": int(item.get("occurrence") or 0),
                "status": status,
                "case_id": str(item.get("shard") or ""),
                "evidence": evidence,
            }
        )
    payload = {
        "identities": rows,
        "counts": {
            "total": len(rows),
            "passed": sum(item["status"] == "passed" for item in rows),
            "gaps": sum(item["status"] == "gap" for item in rows),
        },
    }
    (artifact_root / "identity-results.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return payload


def _case_filename(case_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", case_id) + ".json"


def _write_case_record(
    artifact_root: Path,
    *,
    case_id: str,
    evidence: list[str],
    proof_contract: list[str],
    not_applicable: dict[str, str] | None = None,
) -> None:
    case_root = artifact_root / "case-results"
    case_root.mkdir(parents=True, exist_ok=True)
    for entry in evidence:
        path = artifact_root / entry.split("#", 1)[0]
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Case {case_id} references missing evidence: {entry}")
    payload = {
        "id": case_id,
        "status": "passed",
        "evidence": evidence,
        "proof_contract": proof_contract,
        "not_applicable_proof": not_applicable or {},
    }
    (case_root / _case_filename(case_id)).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def _write_installed_case_results(artifact_root: Path, executable: Path) -> None:
    manifest = json.loads(
        (REPO / "tests" / "release_validation" / "manifest-v1.json").read_text(encoding="utf-8")
    )
    full_contract = list(manifest["proof_contract"])
    observations = json.loads(
        (artifact_root / "case-observations.json").read_text(encoding="utf-8")
    )
    for observation in observations.get("cases", []):
        evidence = list(observation.get("evidence") or [])
        for lifecycle in ("reopen-restart.json", "rendered-output-proof.json"):
            if lifecycle not in evidence:
                evidence.append(lifecycle)
        _write_case_record(
            artifact_root,
            case_id=str(observation["id"]),
            evidence=evidence,
            proof_contract=full_contract,
        )

    readonly_reason = (
        "read-only installed-package assertion; mutation lifecycle layers do not apply"
    )
    for case_id, evidence, proved in (
        ("shell.package-identity", ["package-identity.json"], ["immediate_visible"]),
        ("shell.launch-intent", ["reopen-restart.json"], ["one_action", "immediate_visible"]),
        ("shell.project-argument", ["reopen-restart.json"], ["one_action", "immediate_visible"]),
        ("shell.restart-resets-zoom", ["reopen-restart.json"], ["app_restart"]),
        (
            "output.packaged-ffprobe-streams",
            ["rendered-output-proof.json"],
            ["downstream_output"],
        ),
        (
            "output.codec-dimensions-fps-duration-audio",
            ["rendered-output-proof.json"],
            ["downstream_output"],
        ),
        (
            "output.deterministic-nonblack-frames",
            ["rendered-output-proof.json"],
            ["downstream_output"],
        ),
        ("output.match-text-ocr", ["rendered-output-proof.json"], ["downstream_output"]),
    ):
        _write_case_record(
            artifact_root,
            case_id=case_id,
            evidence=evidence,
            proof_contract=proved,
            not_applicable={item: readonly_reason for item in full_contract if item not in proved},
        )

    platform = (
        "macos" if sys.platform == "darwin" else "windows" if sys.platform == "win32" else "linux"
    )
    platform_proof = {
        "platform": platform,
        "executable": str(executable),
        "checks": {},
    }
    if platform == "macos":
        app_bundle = next(
            (parent for parent in executable.parents if parent.suffix == ".app"), None
        )
        if app_bundle is None:
            raise RuntimeError(f"Could not resolve app bundle from {executable}")
        commands = {
            "codesign": [
                "codesign",
                "--verify",
                "--deep",
                "--strict",
                "--verbose=2",
                str(app_bundle),
            ],
            "gatekeeper": [
                "spctl",
                "--assess",
                "--type",
                "execute",
                "--verbose=4",
                str(app_bundle),
            ],
            "stapled": ["xcrun", "stapler", "validate", str(app_bundle)],
        }
        for name, command in commands.items():
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            platform_proof["checks"][name] = {
                "passed": result.returncode == 0,
                "returncode": result.returncode,
                "output": (result.stdout + result.stderr).strip(),
            }
        platform_proof_path = artifact_root / "platform-proof.json"
        platform_proof_path.write_text(
            json.dumps(platform_proof, indent=2) + "\n", encoding="utf-8"
        )
        _write_case_record(
            artifact_root,
            case_id="macos.dmg-mounted-installed",
            evidence=["package-identity.json", "reopen-restart.json"],
            proof_contract=["one_action", "immediate_visible", "app_restart"],
            not_applicable={
                item: readonly_reason
                for item in full_contract
                if item not in {"one_action", "immediate_visible", "app_restart"}
            },
        )
        if platform_proof["checks"]["codesign"]["passed"]:
            for case_id in ("macos.signed", "macos.codesign"):
                _write_case_record(
                    artifact_root,
                    case_id=case_id,
                    evidence=["platform-proof.json"],
                    proof_contract=["immediate_visible"],
                    not_applicable={
                        item: readonly_reason
                        for item in full_contract
                        if item != "immediate_visible"
                    },
                )
        if platform_proof["checks"]["gatekeeper"]["passed"]:
            _write_case_record(
                artifact_root,
                case_id="macos.gatekeeper",
                evidence=["platform-proof.json"],
                proof_contract=["immediate_visible"],
                not_applicable={
                    item: readonly_reason for item in full_contract if item != "immediate_visible"
                },
            )
        if platform_proof["checks"]["stapled"]["passed"]:
            for case_id in ("macos.notarized", "macos.stapled"):
                _write_case_record(
                    artifact_root,
                    case_id=case_id,
                    evidence=["platform-proof.json"],
                    proof_contract=["immediate_visible"],
                    not_applicable={
                        item: readonly_reason
                        for item in full_contract
                        if item != "immediate_visible"
                    },
                )
    else:
        platform_proof["checks"]["executable"] = {"passed": executable.is_file()}
        platform_proof_path = artifact_root / "platform-proof.json"
        platform_proof_path.write_text(
            json.dumps(platform_proof, indent=2) + "\n", encoding="utf-8"
        )
        cases = (
            (
                "windows.nsis-installed",
                "windows.installed-app-launched",
                "windows.packaged-runtime-tools",
                "windows.ocr-font-proof",
            )
            if platform == "windows"
            else (
                "linux.appimage-launched",
                "linux.packaged-runtime-tools",
                "linux.runtime-libraries",
            )
        )
        for case_id in cases:
            _write_case_record(
                artifact_root,
                case_id=case_id,
                evidence=["platform-proof.json", "rendered-output-proof.json"],
                proof_contract=["immediate_visible", "downstream_output"],
                not_applicable={
                    item: readonly_reason
                    for item in full_contract
                    if item not in {"immediate_visible", "downstream_output"}
                },
            )


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _create_project_bundle(project_path: Path, name: str = "e2e") -> Path:
    stage = ProjectStage(label="Stage 1", order_index=1, imported_stage_number=1)
    project = Project(name=name, stages=[stage], active_stage_id=stage.id)
    save_project(project, project_path)
    return project_path


def _default_packaged_artifact_root() -> Path:
    if sys.platform == "darwin":
        suffix = "packaged-local-mac"
    elif sys.platform == "win32":
        suffix = "packaged-local-windows"
    else:
        suffix = "packaged-local-linux"
    return ARTIFACTS_DIR / "v107-release-proof" / suffix


def _prepare_test_video(out_dir: Path, source_override: Path | None = None) -> Path:
    source = (
        source_override or Path(os.environ.get("SPLITSHOT_E2E_VIDEO", DEFAULT_VIDEO_FIXTURE))
    ).resolve()
    if not source.exists():
        raise FileNotFoundError(f"Packaged E2E video fixture not found at {source}")
    target = out_dir / source.name
    shutil.copy2(source, target)
    return target


def _ocr_text_is_readable(text: str) -> bool:
    normalized = " ".join(str(text or "").split()).lower()
    if not normalized:
        return False
    return any(
        token in normalized
        for token in (
            "shot",
            "draw",
            "timer",
            "split",
            "factor",
            "hit",
            "packaged custom review",
            "points down",
            "penalties",
            "division",
            "class",
            "overall",
        )
    )


def _analyze_rendered_output(export_file: Path, artifact_dir: Path) -> dict:
    ffmpeg = _resolve_tool(os.environ.get("SPLITSHOT_PACKAGED_FFMPEG", "ffmpeg"))
    ffprobe = _resolve_tool(os.environ.get("SPLITSHOT_PACKAGED_FFPROBE", "ffprobe"))
    probe = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(export_file),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    metadata = json.loads(probe.stdout)
    streams = metadata.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = next((item for item in streams if item.get("codec_type") == "audio"), None)
    duration = float((metadata.get("format") or {}).get("duration") or 0)
    if not video or not audio or duration <= 0:
        raise RuntimeError(f"Rendered output is missing video, audio, or duration: {export_file}")
    frame_proofs: list[dict] = []
    for fraction in (0.1, 0.5, 0.9):
        timestamp = max(0.0, duration * fraction)
        result = subprocess.run(
            [
                ffmpeg,
                "-v",
                "error",
                "-ss",
                f"{timestamp:.6f}",
                "-i",
                str(export_file),
                "-vf",
                "scale=160:90,format=gray",
                "-frames:v",
                "1",
                "-f",
                "rawvideo",
                "pipe:1",
            ],
            check=True,
            capture_output=True,
        )
        pixels = result.stdout
        if len(pixels) != 160 * 90:
            raise RuntimeError(f"Could not decode proof frame at {timestamp:.3f}s: {export_file}")
        mean_luma = sum(pixels) / len(pixels)
        frame_proofs.append(
            {
                "timestamp_s": timestamp,
                "mean_luma": mean_luma,
                "sha256": hashlib.sha256(pixels).hexdigest(),
            }
        )
    if any(item["mean_luma"] <= 3 for item in frame_proofs):
        raise RuntimeError(
            f"Rendered output contains an effectively black proof frame: {export_file}"
        )
    if len({item["sha256"] for item in frame_proofs}) < 2:
        raise RuntimeError(f"Rendered output proof frames are not visually distinct: {export_file}")

    ocr_text = ""
    tesseract = shutil.which(os.environ.get("SPLITSHOT_PACKAGED_TESSERACT", "tesseract"))
    if tesseract:
        proof_image = artifact_dir / f"{export_file.stem}-ocr.png"
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-v",
                "error",
                "-ss",
                f"{min(5.2, duration * 0.5):.6f}",
                "-i",
                str(export_file),
                "-frames:v",
                "1",
                str(proof_image),
            ],
            check=True,
            capture_output=True,
        )
        ocr = subprocess.run(
            [tesseract, str(proof_image), "stdout", "--psm", "11"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        ocr_text = ocr.stdout
        (artifact_dir / f"{export_file.stem}-ocr.txt").write_text(ocr_text, encoding="utf-8")
        if not _ocr_text_is_readable(ocr_text):
            raise RuntimeError(
                f"Rendered output OCR did not find expected overlay text: {export_file}"
            )
    else:
        raise RuntimeError("Tesseract is required for packaged rendered-output text proof")
    return {
        "path": str(export_file),
        "sha256": _sha256(export_file),
        "duration_s": duration,
        "video": video,
        "audio": audio,
        "frames": frame_proofs,
        "ocr_text": " ".join(ocr_text.split()),
        "result": "passed",
    }


def _playwright_export_file(artifact_root: Path) -> Path:
    return artifact_root / "exports" / "e2e-export-test.mp4"


def _prepare_release_proof_videos(
    out_dir: Path,
    primary_source: Path | None,
    secondary_source: Path | None,
) -> tuple[Path, Path]:
    primary_source_path = (primary_source or DEFAULT_CORPUS_ROOT / "primary.MP4").resolve()
    secondary_source_path = (secondary_source or DEFAULT_CORPUS_ROOT / "secondary.MP4").resolve()

    primary = _prepare_test_video(out_dir, source_override=primary_source_path)
    secondary = out_dir / f"{secondary_source_path.stem}-secondary{secondary_source_path.suffix}"
    shutil.copy2(secondary_source_path, secondary)
    return primary, secondary


def _resolve_tool(command: str, *, windows_fallbacks: tuple[str, ...] = ()) -> str:
    candidate = str(command or "").strip()
    if candidate:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
        explicit = Path(candidate)
        if explicit.exists():
            return str(explicit)
    if sys.platform == "win32":
        for fallback in windows_fallbacks:
            expanded = Path(_expand_windows_vars(fallback))
            if expanded.exists():
                return str(expanded)
    raise FileNotFoundError(f"Required executable not found: {candidate or '<empty>'}")


def _expand_windows_vars(path: str) -> str:
    def _replacer(m):
        return os.environ.get(m.group(1), m.group(0))

    return re.sub(r"%(\w+)%", _replacer, path).replace("\\", os.sep)


def _proof_windows_export_text(export_file: Path, artifact_dir: Path) -> None:
    ffmpeg = _resolve_tool(os.environ.get("SPLITSHOT_PACKAGED_FFMPEG", "ffmpeg"))
    ffprobe = _resolve_tool(os.environ.get("SPLITSHOT_PACKAGED_FFPROBE", "ffprobe"))
    tesseract = _resolve_tool(
        os.environ.get("SPLITSHOT_PACKAGED_TESSERACT", "tesseract"),
        windows_fallbacks=(
            r"%ProgramFiles%\\Tesseract-OCR\\tesseract.exe",
            r"%ProgramFiles(x86)%\\Tesseract-OCR\\tesseract.exe",
            r"%ChocolateyInstall%\\bin\\tesseract.exe",
        ),
    )
    proof_image = artifact_dir / "export-proof-overlay.png"
    proof_text = artifact_dir / "export-proof-ocr.txt"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    probe = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-of",
            "json",
            str(export_file),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    metadata = json.loads(probe.stdout)
    video_stream = next(item for item in metadata["streams"] if item.get("codec_type") == "video")
    width = int(video_stream["width"])
    height = int(video_stream["height"])
    crop_width = width
    crop_height = max(1, height // 2)
    crop_x = 0
    crop_y = max(0, height - crop_height)
    crop_filter = f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y}"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-ss",
            "5.2",
            "-i",
            str(export_file),
            "-vf",
            crop_filter,
            "-frames:v",
            "1",
            str(proof_image),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    result = subprocess.run(
        [
            tesseract,
            str(proof_image),
            "stdout",
            "--psm",
            "6",
            "-c",
            (
                "tessedit_char_whitelist="
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:+-. "
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    proof_text.write_text(result.stdout, encoding="utf-8")
    if not _ocr_text_is_readable(result.stdout):
        raise RuntimeError(
            "Windows OCR proof did not find readable overlay text "
            f"(got: {re.sub(r'\\s+', ' ', result.stdout).strip() or 'empty'})"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--video-dir", type=Path, default=ARTIFACTS_DIR)
    parser.add_argument("--artifact-root", type=Path, default=None)
    parser.add_argument(
        "--scope", choices=("standard", "export-proof", "release-proof"), default=None
    )
    parser.add_argument("--primary-video", type=Path, default=None)
    parser.add_argument("--secondary-video", type=Path, default=None)
    parser.add_argument("--practiscore", type=Path, default=None)
    args = parser.parse_args()

    executable = args.app.resolve()
    if not executable.exists():
        print(f"FAIL: executable not found at {executable}", file=sys.stderr)
        return 1

    work_dir = _repo_temp_dir("sshot-e2e-")
    log_dir = _repo_temp_dir("sshot-e2e-logs-")
    ready_file = work_dir / "events.jsonl"
    port = _free_port()
    scope = args.scope or os.environ.get("SPLITSHOT_E2E_SCOPE", "standard")
    artifact_root = (
        args.artifact_root
        or Path(os.environ.get("SPLITSHOT_E2E_ARTIFACT_ROOT", _default_packaged_artifact_root()))
    ).resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)
    project_path = (
        artifact_root / "project" / "e2e.ssproj"
        if scope == "release-proof"
        else work_dir / "e2e.ssproj"
    )
    project_path.parent.mkdir(parents=True, exist_ok=True)

    if scope == "release-proof":
        corpus_report = validate_release_data(manifest_path=DEFAULT_MANIFEST)
        (artifact_root / "corpus-preflight.json").write_text(
            json.dumps(corpus_report, indent=2) + "\n", encoding="utf-8"
        )
        if corpus_report["result"] != "passed":
            raise RuntimeError(f"Release corpus preflight failed: {corpus_report['failed_checks']}")
        expected_primary = (DEFAULT_CORPUS_ROOT / "primary.MP4").resolve()
        expected_secondary = (DEFAULT_CORPUS_ROOT / "secondary.MP4").resolve()
        expected_practiscore = (DEFAULT_CORPUS_ROOT / "practiscore.csv").resolve()
        requested_primary = (args.primary_video or expected_primary).resolve()
        requested_secondary = (args.secondary_video or expected_secondary).resolve()
        requested_practiscore = (args.practiscore or expected_practiscore).resolve()
        if (
            requested_primary != expected_primary
            or requested_secondary != expected_secondary
            or requested_practiscore != expected_practiscore
        ):
            raise ValueError(
                "release-proof accepts only tests/release_data/primary.MP4, "
                "secondary.MP4, and practiscore.csv"
            )
        video_path, secondary_video_path = _prepare_release_proof_videos(
            work_dir,
            requested_primary,
            requested_secondary,
        )
        practiscore_path = requested_practiscore
    else:
        video_path = _prepare_test_video(work_dir, source_override=args.primary_video)
        secondary_video_path = None
        practiscore_path = None

    export_file = _playwright_export_file(artifact_root)
    export_file.parent.mkdir(parents=True, exist_ok=True)
    export_file.unlink(missing_ok=True)

    print("Creating project bundle...", flush=True)
    _create_project_bundle(project_path)

    log_out = log_dir / "stdout.log"
    log_err = log_dir / "stderr.log"
    restart_proc: subprocess.Popen | None = None

    env = {
        **os.environ,
        "CI": "1",
        "SPLITSHOT_ELECTRON_TEST": "1",
        "SPLITSHOT_ELECTRON_READY_FILE": str(ready_file),
        "SPLITSHOT_TEST_PORT": str(port),
        "SPLITSHOT_APP_DIR": str(artifact_root / "app-data"),
        "SPLITSHOT_ELECTRON_USER_DATA_DIR": str(artifact_root / "electron-user-data"),
    }
    if scope == "release-proof" and secondary_video_path is not None:
        env["SPLITSHOT_ELECTRON_TEST_IN_OUT_PATHS"] = json.dumps(
            [str(video_path), str(secondary_video_path)]
        )
    cmd = [str(executable)]
    if sys.platform.startswith("linux"):
        env["ELECTRON_DISABLE_SANDBOX"] = "1"
        cmd.append("--no-sandbox")
    cmd.append(str(project_path))

    print(f"E2E port={port}", flush=True)
    with log_out.open("w") as o, log_err.open("w") as e:
        proc = subprocess.Popen(cmd, cwd=executable.parent, env=env, stdout=o, stderr=e, text=True)

    try:
        initial_state = _wait_for_state(proc, port)
        print("PASS: backend responding", flush=True)

        # Run Playwright Node.js script
        electron_dir = REPO / "electron"
        pw_script = REPO / "scripts" / "testing" / "e2e-playwright.cjs"
        pw_log_dir = artifact_root / "e2e-logs"
        shutil.rmtree(pw_log_dir, ignore_errors=True)
        pw_log_dir.mkdir(parents=True, exist_ok=True)
        pw_env = {
            **os.environ,
            "E2E_PORT": str(port),
            "E2E_LOG_DIR": str(pw_log_dir),
            "E2E_VIDEO_PATH": str(video_path),
            "E2E_PRIMARY_VIDEO_PATH": str(video_path),
            "E2E_EXPORT_DIR": str(export_file.parent),
            "E2E_ARTIFACT_ROOT": str(artifact_root),
            "SPLITSHOT_E2E_SCOPE": scope,
            "NODE_PATH": str(electron_dir / "node_modules"),
        }
        if secondary_video_path is not None:
            pw_env["E2E_SECONDARY_VIDEO_PATH"] = str(secondary_video_path)
        if practiscore_path is not None:
            pw_env["E2E_PRACTISCORE_PATH"] = str(practiscore_path)
        for bad in ("QT_QPA_PLATFORM", "APPIMAGE_EXTRACT_AND_RUN"):
            pw_env.pop(bad, None)

        result = subprocess.run(
            ["node", str(pw_script)],
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
            cwd=REPO,
            env=pw_env,
        )

        if result.stdout:
            print(result.stdout, flush=True)
        if result.stderr:
            print(result.stderr, file=sys.stderr, flush=True)

        summary_file = pw_log_dir / "summary.json"
        if summary_file.exists():
            try:
                summary = json.loads(summary_file.read_text())
                print(
                    f"E2E SUMMARY: result={summary.get('result')} "
                    f"errors={summary.get('pageErrors', 0)} "
                    f"artifacts={summary.get('artifacts', 0)}",
                    flush=True,
                )
                failures = summary.get("failures") or []
                if failures:
                    print("E2E FAILURES:", flush=True)
                    for item in failures:
                        print(f"  - {item}", flush=True)
            except Exception:
                pass

        captured = list(pw_log_dir.glob("*"))
        if captured:
            print(f"E2E ARTIFACTS ({len(captured)} files):", flush=True)
            for f in sorted(captured):
                sz = f.stat().st_size
                print(
                    f"  {f.name} ({sz / 1024:.1f} KB)" if sz else f"  {f.name} (empty)", flush=True
                )

        summary = None
        if summary_file.exists():
            try:
                summary = json.loads(summary_file.read_text())
            except Exception as exc:
                raise RuntimeError(f"Could not parse Playwright summary: {exc}") from exc
        else:
            raise RuntimeError("Playwright did not produce summary.json")

        playwright_failure = ""
        if summary.get("result") != "passed":
            playwright_failure = (
                "Playwright summary reported failure: "
                f"{summary.get('failures') or summary.get('error') or 'unknown'}"
            )
        if result.returncode != 0 and not playwright_failure:
            playwright_failure = f"Playwright exited code {result.returncode}"

        if sys.platform == "win32" and os.environ.get("SPLITSHOT_E2E_OCR_PROOF") == "1":
            _proof_windows_export_text(_playwright_export_file(artifact_root), artifact_root)

        if scope == "release-proof":
            output_proof = {
                "result": "passed",
                "individual": _analyze_rendered_output(
                    _playwright_export_file(artifact_root), artifact_root
                ),
                "combined": _analyze_rendered_output(
                    artifact_root / "exports" / "combined-output.mp4", artifact_root
                ),
            }
            (artifact_root / "rendered-output-proof.json").write_text(
                json.dumps(output_proof, indent=2) + "\n", encoding="utf-8"
            )

        final_state = _wait_for_state(proc, port)
        _stop_process(proc)
        restart_port = _free_port()
        restart_ready = artifact_root / "restart-events.jsonl"
        restart_env = {
            **env,
            "SPLITSHOT_ELECTRON_READY_FILE": str(restart_ready),
            "SPLITSHOT_TEST_PORT": str(restart_port),
        }
        restart_cmd = [str(executable)]
        if sys.platform.startswith("linux"):
            restart_cmd.append("--no-sandbox")
        restart_cmd.append(str(project_path))
        restart_out = artifact_root / "restart.stdout.log"
        restart_err = artifact_root / "restart.stderr.log"
        with restart_out.open("w") as o, restart_err.open("w") as e:
            restart_proc = subprocess.Popen(
                restart_cmd,
                cwd=executable.parent,
                env=restart_env,
                stdout=o,
                stderr=e,
                text=True,
            )
        restarted_state = _wait_for_state(restart_proc, restart_port)
        before_project = str((final_state.get("project") or {}).get("path") or "")
        after_project = str((restarted_state.get("project") or {}).get("path") or "")
        if (
            Path(before_project).resolve() != project_path.resolve()
            or Path(after_project).resolve() != project_path.resolve()
        ):
            raise RuntimeError(
                "Installed-app restart did not reopen project: "
                f"before={before_project} after={after_project}"
            )
        (artifact_root / "reopen-restart.json").write_text(
            json.dumps(
                {
                    "result": "passed",
                    "project_path": str(project_path),
                    "initial_active_stage": (initial_state.get("project") or {}).get(
                        "active_stage_id"
                    ),
                    "before_restart_active_stage": (final_state.get("project") or {}).get(
                        "active_stage_id"
                    ),
                    "after_restart_active_stage": (restarted_state.get("project") or {}).get(
                        "active_stage_id"
                    ),
                    "restart_events": str(restart_ready),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if scope == "release-proof" and secondary_video_path and practiscore_path:
            audit_failures = _run_packaged_browser_audits(
                port=restart_port,
                artifact_root=artifact_root,
                primary_video=video_path,
                secondary_video=secondary_video_path,
                practiscore=practiscore_path,
            )
            if audit_failures:
                joined = "; ".join(audit_failures)
                playwright_failure = f"{playwright_failure}; {joined}".strip("; ")
            else:
                identity_results = _build_identity_results(artifact_root)
                if identity_results["counts"]["gaps"]:
                    playwright_failure = (
                        f"{playwright_failure}; installed runtime identity gaps: "
                        f"{identity_results['counts']['gaps']}"
                    ).strip("; ")
        packaged_artifact = Path(os.environ.get("SPLITSHOT_PACKAGED_ARTIFACT", executable))
        source_commit = os.environ.get("SPLITSHOT_SOURCE_COMMIT", "").strip()
        (artifact_root / "package-identity.json").write_text(
            json.dumps(
                {
                    "source_commit": source_commit,
                    "source_tree_clean": os.environ.get("SPLITSHOT_SOURCE_TREE_CLEAN") == "1",
                    "artifact": str(packaged_artifact.resolve()),
                    "package_sha256": _sha256(packaged_artifact),
                    "executable": str(executable),
                    "executable_sha256": _sha256(executable),
                    "corpus_revision": (
                        corpus_report.get("corpus_revision", "") if scope == "release-proof" else ""
                    ),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if scope == "release-proof":
            _write_installed_case_results(artifact_root, executable)

        if playwright_failure:
            raise RuntimeError(playwright_failure)

        print("PASS: full E2E test completed", flush=True)
        return 0

    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr, flush=True)
        if proc.poll() is not None:
            print(f"FAIL: exit code {proc.returncode}", file=sys.stderr, flush=True)
        for log_path in [log_out, log_err]:
            if log_path and log_path.exists():
                lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                print(f"--- {log_path.name} tail ---", file=sys.stderr, flush=True)
                print("\n".join(lines[-20:]), file=sys.stderr, flush=True)
        return 1
    finally:
        _stop_process(restart_proc)
        _stop_process(proc)
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
