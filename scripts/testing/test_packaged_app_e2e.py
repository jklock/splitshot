#!/usr/bin/env python3
"""Full E2E test: launch app, run Playwright browser interactions, record video."""

from __future__ import annotations

import argparse
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

REPO = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO / "artifacts"
DEFAULT_VIDEO_FIXTURE = REPO / "tests" / "fixtures" / "media" / "stage.mp4"
CLIP1_VIDEO = REPO / "docs" / "Clip1.MP4"
TIMEOUT = 120


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
    return ARTIFACTS_DIR / "v106-phase-12-proof" / suffix


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
    return any(token in normalized for token in ("shot", "draw", "timer", "split", "factor", "hit"))


def _playwright_export_file(artifact_root: Path) -> Path:
    return artifact_root / "exports" / "e2e-export-test.mp4"


def _prepare_release_proof_videos(
    out_dir: Path,
    primary_source: Path | None,
    secondary_source: Path | None,
    tertiary_source: Path | None,
) -> tuple[Path, Path, Path]:
    primary_source_path = (primary_source or CLIP1_VIDEO).resolve()
    secondary_source_path = (secondary_source or primary_source_path).resolve()
    tertiary_source_path = (tertiary_source or primary_source_path).resolve()

    primary = _prepare_test_video(out_dir, source_override=primary_source_path)
    secondary = out_dir / f"{secondary_source_path.stem}-secondary{secondary_source_path.suffix}"
    tertiary = out_dir / f"{tertiary_source_path.stem}-tertiary{tertiary_source_path.suffix}"
    shutil.copy2(secondary_source_path, secondary)
    shutil.copy2(tertiary_source_path, tertiary)
    return primary, secondary, tertiary


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
            "tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:+-. ",
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
    parser.add_argument("--tertiary-video", type=Path, default=None)
    args = parser.parse_args()

    executable = args.app.resolve()
    if not executable.exists():
        print(f"FAIL: executable not found at {executable}", file=sys.stderr)
        return 1

    work_dir = Path(tempfile.mkdtemp(prefix="sshot-e2e-"))
    log_dir = Path(tempfile.mkdtemp(prefix="sshot-e2e-logs-"))
    ready_file = work_dir / "events.jsonl"
    port = _free_port()
    project_path = work_dir / "e2e.ssproj"
    scope = args.scope or os.environ.get("SPLITSHOT_E2E_SCOPE", "standard")
    artifact_root = (
        args.artifact_root
        or Path(os.environ.get("SPLITSHOT_E2E_ARTIFACT_ROOT", _default_packaged_artifact_root()))
    ).resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)

    if scope == "release-proof":
        video_path, secondary_video_path, tertiary_video_path = _prepare_release_proof_videos(
            work_dir,
            args.primary_video,
            args.secondary_video,
            args.tertiary_video,
        )
    else:
        video_path = _prepare_test_video(work_dir, source_override=args.primary_video)
        secondary_video_path = None
        tertiary_video_path = None

    export_file = _playwright_export_file(artifact_root)
    export_file.parent.mkdir(parents=True, exist_ok=True)
    export_file.unlink(missing_ok=True)

    print("Creating project bundle...", flush=True)
    _create_project_bundle(project_path)

    log_out = log_dir / "stdout.log"
    log_err = log_dir / "stderr.log"

    env = {
        **os.environ,
        "CI": "1",
        "SPLITSHOT_ELECTRON_TEST": "1",
        "SPLITSHOT_ELECTRON_READY_FILE": str(ready_file),
        "SPLITSHOT_TEST_PORT": str(port),
    }
    cmd = [str(executable)]
    if sys.platform.startswith("linux"):
        env["ELECTRON_DISABLE_SANDBOX"] = "1"
        cmd.append("--no-sandbox")
    cmd.append(str(project_path))

    print(f"E2E port={port}", flush=True)
    with log_out.open("w") as o, log_err.open("w") as e:
        proc = subprocess.Popen(cmd, cwd=executable.parent, env=env, stdout=o, stderr=e, text=True)

    try:
        deadline = time.time() + 60
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"App exited (code {proc.returncode})")
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=5)
                break
            except (urllib.error.URLError, ConnectionResetError):
                time.sleep(0.25)
        else:
            raise TimeoutError("Backend did not respond")
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
        if tertiary_video_path is not None:
            pw_env["E2E_TERTIARY_VIDEO_PATH"] = str(tertiary_video_path)
        for bad in ("QT_QPA_PLATFORM", "APPIMAGE_EXTRACT_AND_RUN"):
            pw_env.pop(bad, None)

        result = subprocess.run(
            ["node", str(pw_script)],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
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

        if summary.get("result") != "passed":
            raise RuntimeError(
                f"Playwright summary reported failure: {summary.get('failures') or summary.get('error') or 'unknown'}"
            )

        if result.returncode != 0:
            print(f"FAIL: Playwright exited code {result.returncode}", file=sys.stderr, flush=True)
            if result.stderr:
                print(result.stderr, file=sys.stderr, flush=True)
            raise RuntimeError("Playwright E2E failed")

        if sys.platform == "win32" and os.environ.get("SPLITSHOT_E2E_OCR_PROOF") == "1":
            _proof_windows_export_text(_playwright_export_file(artifact_root), artifact_root)

        print("PASS: full E2E test completed", flush=True)
        return 0

    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr, flush=True)
        if proc.poll() is not None:
            print(f"FAIL: exit code {proc.returncode}", file=sys.stderr, flush=True)
        for l in [log_out, log_err]:
            if l and l.exists():
                lines = l.read_text(encoding="utf-8", errors="replace").splitlines()
                print(f"--- {l.name} tail ---", file=sys.stderr, flush=True)
                print("\n".join(lines[-20:]), file=sys.stderr, flush=True)
        return 1
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
