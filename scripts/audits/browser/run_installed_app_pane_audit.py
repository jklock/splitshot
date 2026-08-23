#!/usr/bin/env python3
"""Run pane screenshots, queue exports, and visual-parity checks against /Applications/SplitShot.app."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any
from urllib.request import urlopen
from uuid import uuid4

from playwright.sync_api import Browser, Page, Playwright, sync_playwright

from splitshot.domain.models import MergeLayout, MergeSource, ProjectStage, QueueStatus
from splitshot.media.probe import probe_video
from splitshot.persistence.projects import load_project, save_project

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_APP = Path("/Applications/SplitShot.app")
DEFAULT_PROJECT = ROOT / "05072026"
DEFAULT_ARTIFACT_PARENT = ROOT / "artifacts" / "installed-app-pane-audit"
TIMEOUT = 180
QUEUE_EXPORT_TIMEOUT_MS = 900_000
SLICE_CHOICES = ("launch", "panes", "trim", "queue-individual", "queue-combined", "full")
TOOLS = [
    "project",
    "media",
    "merge",
    "trim-sync",
    "scoring",
    "timing",
    "markers",
    "overlay",
    "review",
    "export",
    "queue",
    "metrics",
    "shotml",
    "settings",
]
TOOL_TITLES = {
    "project": "Project",
    "media": "Media",
    "merge": "Compose",
    "trim-sync": "Trim",
    "scoring": "Score",
    "timing": "Splits",
    "markers": "Markers",
    "overlay": "Overlay",
    "review": "Review",
    "export": "Export",
    "queue": "Queue",
    "metrics": "Metrics",
    "shotml": "ShotML",
    "settings": "Settings",
}
BASELINE_PANES = ("project", "scoring", "timing")


@dataclass(slots=True)
class AppSession:
    process: subprocess.Popen[str]
    port: int
    ready_file: Path
    stdout_log: Path
    stderr_log: Path
    executable: Path
    bundle: Path
    version: str

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit the installed SplitShot app with fresh screenshots and queue exports."
    )
    parser.add_argument("--app", type=Path, default=DEFAULT_APP)
    parser.add_argument("--project-path", type=Path, default=DEFAULT_PROJECT)
    parser.add_argument("--artifact-root", type=Path, default=None)
    parser.add_argument("--slice", choices=SLICE_CHOICES, default="full")
    parser.add_argument("--fresh-project-copy", action="store_true")
    return parser


def _now_slug() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _default_artifact_root() -> Path:
    return DEFAULT_ARTIFACT_PARENT / _now_slug()


def _app_executable(app_path: Path) -> Path:
    resolved = app_path.expanduser().resolve()
    if resolved.is_dir() and resolved.suffix == ".app":
        if sys.platform != "darwin":
            raise RuntimeError("App bundle paths are only supported on macOS.")
        executable = resolved / "Contents" / "MacOS" / "SplitShot"
    else:
        executable = resolved
    if not executable.exists():
        raise FileNotFoundError(f"SplitShot executable not found at {executable}")
    return executable


def _app_bundle_from_executable(executable: Path) -> Path:
    if executable.suffix == ".app":
        return executable
    parents = list(executable.parents)
    for parent in parents:
        if parent.suffix == ".app":
            return parent
    return executable


def _bundle_version(bundle: Path) -> str:
    if sys.platform != "darwin":
        return ""
    result = subprocess.run(
        ["defaults", "read", str(bundle / "Contents" / "Info"), "CFBundleShortVersionString"],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    return result.stdout.strip()


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_backend(port: int, expected_project: Path, timeout: int = TIMEOUT) -> dict[str, Any]:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout
    wanted = expected_project.resolve()
    while time.time() < deadline:
        try:
            response = urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=5)
            payload = json.loads(response.read().decode())
            project_path = Path(str(payload.get("project", {}).get("path") or ""))
            if project_path and project_path.resolve() == wanted:
                return payload
        except (
            urllib.error.URLError,
            ConnectionResetError,
            json.JSONDecodeError,
            FileNotFoundError,
        ):
            pass
        time.sleep(0.25)
    raise TimeoutError(f"Backend never loaded {expected_project}")


def _warm_installed_app_media(base_url: str, state: dict[str, Any]) -> None:
    import urllib.error

    urls = [f"{base_url}/media/primary"]
    secondary_url = str(
        ((state.get("media") or {}).get("secondary_url")) or "/media/secondary"
    ).strip()
    if secondary_url:
        urls.append(f"{base_url}{secondary_url}")
    for source in list((state.get("project") or {}).get("merge_sources") or []):
        source_id = str(source.get("id") or "").strip()
        if source_id:
            urls.append(f"{base_url}/media/merge/{source_id}")
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        try:
            with urlopen(url, timeout=TIMEOUT) as response:
                response.read(1)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                continue
            raise


def _wait_for_ready_file(
    proc: subprocess.Popen[str], ready_file: Path, timeout: int = TIMEOUT
) -> list[dict[str, Any]]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("Installed app exited before it reported ready")
        if ready_file.exists():
            events = [
                json.loads(line)
                for line in ready_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            names = {str(item.get("event")) for item in events}
            if {"backend-ready", "window-loaded", "window-ready-to-show", "app-ready"} <= names:
                return events
        time.sleep(0.25)
    raise TimeoutError(f"Ready file never reported app-ready: {ready_file}")


def _terminate_process(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is None:
        if os.name == "posix":
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except ProcessLookupError:
                return
            except OSError:
                proc.terminate()
        else:
            proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    return
            else:
                proc.kill()
            proc.wait(timeout=5)


def _current_and_ancestor_pids(process_rows: list[tuple[int, int, str]]) -> set[int]:
    parent_by_pid = {pid: ppid for pid, ppid, _command in process_rows}
    current = os.getpid()
    blocked = {current}
    while current in parent_by_pid:
        current = parent_by_pid[current]
        if current <= 1 or current in blocked:
            break
        blocked.add(current)
    return blocked


def _processes_matching_path(path: Path) -> list[int]:
    target = str(path)
    result = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,command="],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    process_rows: list[tuple[int, int, str]] = []
    for line in result.stdout.splitlines():
        raw = line.strip()
        if not raw:
            continue
        parts = raw.split(None, 2)
        if len(parts) < 3:
            continue
        pid_text, ppid_text, command = parts
        try:
            pid = int(pid_text)
            ppid = int(ppid_text)
        except ValueError:
            continue
        process_rows.append((pid, ppid, command))
    blocked = _current_and_ancestor_pids(process_rows)
    matches: list[int] = []
    for pid, _ppid, command in process_rows:
        if target in command and pid not in blocked:
            matches.append(pid)
    return matches


def _terminate_matching_processes(path: Path) -> None:
    pids = _processes_matching_path(path)
    if not pids:
        return
    force_signal = getattr(signal, "SIGKILL", signal.SIGTERM)
    for sig in (signal.SIGTERM, force_signal):
        remaining: list[int] = []
        for pid in pids:
            try:
                os.kill(pid, sig)
                remaining.append(pid)
            except ProcessLookupError:
                continue
        if not remaining:
            return
        deadline = time.time() + (5 if sig == signal.SIGTERM else 2)
        while time.time() < deadline and remaining:
            next_remaining: list[int] = []
            for pid in remaining:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    continue
                next_remaining.append(pid)
            remaining = next_remaining
            if remaining:
                time.sleep(0.1)
        if not remaining:
            return
        pids = remaining


def _tail_logs(stdout_log: Path, stderr_log: Path) -> str:
    parts: list[str] = []
    for log in (stdout_log, stderr_log):
        if log.exists():
            lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
            parts.append(f"== {log.name} ==\n" + "\n".join(lines[-20:]))
    return "\n\n".join(parts).strip()


def _spawn_installed_app(executable: Path, project_path: Path, artifact_root: Path) -> AppSession:
    bundle = _app_bundle_from_executable(executable)
    _terminate_matching_processes(bundle)
    port = _find_free_port()
    ready_file = artifact_root / "app-events.jsonl"
    stdout_log = artifact_root / "installed-app.stdout.log"
    stderr_log = artifact_root / "installed-app.stderr.log"
    env = {
        **dict(subprocess.os.environ),
        "CI": "1",
        "SPLITSHOT_ELECTRON_TEST": "1",
        "SPLITSHOT_ELECTRON_READY_FILE": str(ready_file),
        "SPLITSHOT_TEST_PORT": str(port),
    }
    command = [str(executable)]
    if sys.platform.startswith("linux"):
        env["ELECTRON_DISABLE_SANDBOX"] = "1"
        command.append("--no-sandbox")
    command.append(str(project_path))
    with (
        stdout_log.open("w", encoding="utf-8") as stdout_handle,
        stderr_log.open("w", encoding="utf-8") as stderr_handle,
    ):
        process = subprocess.Popen(
            command,
            cwd=executable.parent,
            env=env,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            start_new_session=(os.name == "posix"),
        )
    version = _bundle_version(bundle)
    return AppSession(
        process=process,
        port=port,
        ready_file=ready_file,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        executable=executable,
        bundle=bundle,
        version=version,
    )


def _project_copy_root(project_path: Path, artifact_root: Path) -> Path:
    bundle_name = (
        project_path.name if project_path.suffix == ".ssproj" else f"{project_path.name}.ssproj"
    )
    return artifact_root / "project-copy" / bundle_name


def _project_media_path(project_root: Path, name: str) -> Path:
    candidate = project_root / name
    if not candidate.exists():
        candidate = project_root / "Input" / name
    if not candidate.exists():
        raise FileNotFoundError(f"Required project media missing: {candidate}")
    return candidate


def _make_stage(
    stage_number: int, primary_path: Path, base_stage: ProjectStage | None = None
) -> ProjectStage:
    stage = deepcopy(base_stage) if base_stage is not None else ProjectStage()
    stage.id = uuid4().hex
    stage.label = f"Stage {stage_number}"
    stage.order_index = stage_number
    stage.imported_stage_number = stage_number
    stage.primary_media = probe_video(primary_path)
    stage.added_media = []
    stage.queue_status = QueueStatus.NOT_QUEUED
    stage.last_output_path = ""
    stage.last_processed_at = ""
    stage.merge.enabled = False
    stage.analysis.waveform_secondary = []
    stage.analysis.secondary_sources = []
    stage.analysis.secondary_analysis_status = ""
    stage.analysis.secondary_analysis_message = ""
    stage.analysis.analyzed_secondary_source_id = ""
    stage.analysis.sync_offset_ms = 0
    return stage


def _normalize_project_for_audit(project_root: Path) -> dict[str, Any]:
    project = load_project(project_root)
    original_stage = project.active_stage or (project.stages[0] if project.stages else None)
    if original_stage is None:
        raise RuntimeError(f"No stage found in {project_root}")

    stage2_primary = _project_media_path(project_root, "Stage2.MP4")
    stage3_primary = _project_media_path(project_root, "Stage3.MP4")
    stage4_primary = _project_media_path(project_root, "Stage4.MP4")

    stage2 = deepcopy(original_stage)
    stage2.label = "Stage 2"
    stage2.order_index = 2
    stage2.imported_stage_number = 2
    stage2.primary_media = probe_video(stage2_primary)

    existing_sources = {
        Path(source.asset.path).name: deepcopy(source) for source in stage2.added_media
    }
    stage2_source3 = existing_sources.get("Stage3.MP4", MergeSource())
    stage2_source3.asset = probe_video(stage3_primary)
    stage2_source4 = existing_sources.get("Stage4.MP4", MergeSource())
    stage2_source4.asset = probe_video(stage4_primary)
    stage2.added_media = [stage2_source3, stage2_source4]
    stage2.merge.enabled = True
    stage2.merge.layout = MergeLayout.PIP
    stage2.overlay.show_timer = True
    stage2.overlay.show_draw = True
    stage2.overlay.show_shots = True
    stage2.overlay.show_score = True
    if stage2.scoring.imported_stage is not None:
        stage2.scoring.imported_stage.stage_number = 2

    stage3 = _make_stage(3, stage3_primary, base_stage=original_stage)
    stage4 = _make_stage(4, stage4_primary, base_stage=original_stage)

    project.name = f"{project.name} Audit"
    project.output_root = str((project_root / "Output").resolve())
    project.stages = [stage2, stage3, stage4]
    project.active_stage_id = stage2.id
    project.primary_video = deepcopy(stage2.primary_media)
    project.secondary_video = deepcopy(stage2.added_media[0].asset)
    project.merge_sources = deepcopy(stage2.added_media)
    project.analysis = deepcopy(stage2.analysis)
    project.scoring = deepcopy(stage2.scoring)
    project.overlay = deepcopy(stage2.overlay)
    project.popups = deepcopy(stage2.popups)
    project.popup_template = deepcopy(stage2.popup_template)
    project.merge = deepcopy(stage2.merge)
    project.export = deepcopy(stage2.export)
    project.ui_state.review_show_pip = True
    project.ui_state.active_tool = "project"
    project.queue = []
    for stage in project.stages:
        stage.queue_status = QueueStatus.NOT_QUEUED
    project.touch()
    save_project(project, project_root)

    return {
        "project_root": str(project_root),
        "stage_labels": [stage.label for stage in project.stages],
        "active_stage_id": project.active_stage_id,
        "output_root": project.output_root,
    }


def _file_fingerprint(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    stat = path.stat()
    return {
        "path": str(path),
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _assert_file_unchanged(path: Path, before: dict[str, Any]) -> None:
    after = _file_fingerprint(path)
    if (
        after["mtime_ns"] != before["mtime_ns"]
        or after["size"] != before["size"]
        or after["sha256"] != before["sha256"]
    ):
        raise RuntimeError(f"Source file was mutated during audit: {path}")


def _prepare_project_copy(
    project_path: Path, artifact_root: Path, *, fresh: bool = False, normalize: bool = True
) -> tuple[Path, dict[str, Any]]:
    project_root = project_path.expanduser().resolve()
    if not project_root.exists():
        raise FileNotFoundError(f"Project path does not exist: {project_root}")
    copy_root = _project_copy_root(project_root, artifact_root)
    cache_meta_path = artifact_root / "project-copy" / "cache-meta.json"
    source_project_json = project_root / "project.json"
    source_fingerprint = (
        _file_fingerprint(source_project_json) if source_project_json.exists() else None
    )
    cached_fingerprint: dict[str, Any] | None = None
    if cache_meta_path.exists():
        try:
            cached_fingerprint = json.loads(cache_meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cached_fingerprint = None
    can_reuse = (
        not fresh
        and copy_root.exists()
        and source_fingerprint is not None
        and cached_fingerprint is not None
        and cached_fingerprint.get("sha256") == source_fingerprint.get("sha256")
    )
    if can_reuse:
        if normalize:
            return copy_root, _normalize_project_for_audit(copy_root)
        return copy_root, {"project_root": str(copy_root)}
    if copy_root.exists():
        shutil.rmtree(copy_root)
    copy_root.parent.mkdir(parents=True, exist_ok=True)
    copy_root.mkdir(parents=True, exist_ok=True)
    for relative_path in (
        Path("project.json"),
        Path("CSV") / "IDPA.csv",
        Path("Stage2.MP4"),
        Path("Stage3.MP4"),
        Path("Stage4.MP4"),
        Path("Input") / "Stage2.MP4",
        Path("Input") / "Stage3.MP4",
        Path("Input") / "Stage4.MP4",
    ):
        source = project_root / relative_path
        if not source.exists():
            continue
        destination = copy_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_file():
            if relative_path.suffix.lower() != ".mp4":
                shutil.copy2(source, destination)
                continue
            try:
                destination.hardlink_to(source)
            except OSError:
                shutil.copy2(source, destination)
    if source_fingerprint is not None:
        cache_meta_path.write_text(json.dumps(source_fingerprint, indent=2), encoding="utf-8")
    if normalize:
        return copy_root, _normalize_project_for_audit(copy_root)
    return copy_root, {"project_root": str(copy_root)}


def _open_page(playwright: Playwright, base_url: str) -> tuple[Browser, Page]:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1760, "height": 1600})
    page.goto(base_url, wait_until="domcontentloaded")
    page.wait_for_selector("#current-file", timeout=60_000)
    page.wait_for_timeout(500)
    return browser, page


def _api_post(page: Page, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    result = page.evaluate(
        """
        async ({ path, payload }) => {
          if (typeof callApi !== "function") {
            throw new Error("callApi is not available in the installed app runtime.");
          }
          return await callApi(path, payload);
        }
        """,
        {"path": path, "payload": payload},
    )
    if result is None:
        status_text = page.evaluate(
            """
            () => {
              const status = document.getElementById('status-message');
              return status instanceof HTMLElement ? status.textContent || '' : '';
            }
            """
        )
        raise RuntimeError(f"API call failed for {path}: {status_text or 'no status message'}")
    if not isinstance(result, dict):
        raise TypeError(f"Unexpected API result for {path}: {result!r}")
    return result


def _wait_for_processing_bar(page: Page, timeout_ms: int = 30_000) -> None:
    page.wait_for_function(
        "() => document.getElementById('processing-bar')?.hidden !== false",
        timeout=timeout_ms,
    )
    page.wait_for_timeout(150)


def _wait_for_active_tool(page: Page, tool: str) -> None:
    page.wait_for_function(
        """
        (tool) => {
          const inspector = document.querySelector('.inspector');
          const pane = document.querySelector(`[data-tool-pane="${tool}"]`);
          return inspector?.dataset?.activeTool === tool && pane?.classList?.contains('active') === true;
        }
        """,
        arg=tool,
        timeout=15_000,
    )


def _set_tool(page: Page, tool: str) -> None:
    page.locator(f'button[data-tool="{tool}"]').click(force=True)
    _wait_for_processing_bar(page)
    _wait_for_active_tool(page, tool)
    page.wait_for_timeout(200)


def _wait_for_visual_media_ready(page: Page, timeout_ms: int = 15_000) -> None:
    page.evaluate(
        """
        async () => {
          const isVisible = (element) =>
            element instanceof HTMLElement &&
            !element.hidden &&
            element.offsetParent !== null &&
            window.getComputedStyle(element).display !== 'none' &&
            window.getComputedStyle(element).visibility !== 'hidden';
          const waitForEvent = (target, name, fallbackMs = 500) =>
            new Promise((resolve) => {
              let settled = false;
              const finish = () => {
                if (settled) return;
                settled = true;
                resolve();
              };
              target.addEventListener(name, finish, { once: true });
              window.setTimeout(finish, fallbackMs);
            });
          const videos = Array.from(
            document.querySelectorAll('#primary-video, #secondary-video, #merge-preview-layer video')
          ).filter((element) => element instanceof HTMLVideoElement && isVisible(element));
          for (const video of videos) {
            if (!video.currentSrc) continue;
            if (video.readyState < HTMLMediaElement.HAVE_METADATA) {
              await waitForEvent(video, 'loadedmetadata', 1_000);
            }
            const seekTarget = Number.isFinite(video.duration) && video.duration > 0.05 ? 0.05 : 0;
            if (seekTarget > 0 && Math.abs((video.currentTime || 0) - seekTarget) > 0.02) {
              try {
                video.currentTime = seekTarget;
                await waitForEvent(video, 'seeked', 1_000);
              } catch (_error) {
                // Ignore seek priming failures and rely on decode readiness below.
              }
            }
            try {
              video.muted = true;
              const playAttempt = video.play();
              if (playAttempt && typeof playAttempt.then === 'function') {
                await Promise.race([playAttempt.catch(() => {}), new Promise((resolve) => window.setTimeout(resolve, 400))]);
              } else {
                await new Promise((resolve) => window.setTimeout(resolve, 150));
              }
            } catch (_error) {
              // Ignore playback priming failures and rely on decode readiness below.
            } finally {
              try {
                video.pause();
              } catch (_error) {}
            }
            if (typeof video.requestVideoFrameCallback === 'function') {
              await new Promise((resolve) => {
                let settled = false;
                const finish = () => {
                  if (settled) return;
                  settled = true;
                  resolve();
                };
                video.requestVideoFrameCallback(() => finish());
                window.setTimeout(finish, 500);
              });
            }
          }
        }
        """
    )
    page.wait_for_function(
        """
        () => {
          const isVisible = (element) =>
            element instanceof HTMLElement &&
            !element.hidden &&
            element.offsetParent !== null &&
            window.getComputedStyle(element).display !== 'none' &&
            window.getComputedStyle(element).visibility !== 'hidden';
          const mediaReady = (element) => {
            if (!isVisible(element)) return true;
            if (element instanceof HTMLImageElement) {
              return !element.currentSrc || element.complete;
            }
            if (element instanceof HTMLVideoElement) {
              return !element.currentSrc || (
                element.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA &&
                element.videoWidth > 0
              );
            }
            return true;
          };
          const media = [
            document.getElementById('primary-video'),
            document.getElementById('secondary-video'),
            document.getElementById('secondary-image'),
            ...Array.from(document.querySelectorAll('#merge-preview-layer video, #merge-preview-layer img')),
          ];
          return media.every((element) => mediaReady(element));
        }
        """,
        timeout=timeout_ms,
    )
    page.wait_for_timeout(250)


def _expand_all_collapsed_controls(page: Page, tool: str) -> None:
    page.evaluate(
        """
        (tool) => {
          const root = document.querySelector(`[data-tool-pane="${tool}"]`);
          if (!(root instanceof HTMLElement)) return;
          for (let loop = 0; loop < 12; loop += 1) {
            let changed = false;
            const buttons = Array.from(
              root.querySelectorAll('button.pane-toggle, button[data-section-toggle], button[data-popup-editor-section-toggle]')
            );
            for (const button of buttons) {
              if (!(button instanceof HTMLButtonElement)) continue;
              if (button.disabled || button.offsetParent === null) continue;
              const label = String(button.getAttribute('aria-label') || '').toLowerCase();
              const expanded = String(button.getAttribute('aria-expanded') || '').toLowerCase();
              const text = String(button.textContent || '').trim();
              const looksCollapsed = label.startsWith('expand') || expanded === 'false' || text === '>' || text === '▶';
              if (looksCollapsed) {
                button.click();
                changed = true;
              }
            }
            if (!changed) break;
          }
        }
        """,
        tool,
    )
    page.wait_for_timeout(250)


def _reset_inspector_scroll(page: Page) -> None:
    page.evaluate(
        """
        () => {
          const inspector = document.querySelector('.inspector');
          if (inspector instanceof HTMLElement) inspector.scrollTop = 0;
        }
        """
    )
    page.wait_for_timeout(150)


def _prepare_overlay_and_review_visibility(page: Page) -> None:
    page.evaluate(
        """
        () => {
          const mergeEnabled = document.getElementById('merge-enabled');
          if (mergeEnabled instanceof HTMLInputElement && !mergeEnabled.checked) mergeEnabled.click();
          const showPip = document.getElementById('show-pip');
          if (showPip instanceof HTMLInputElement && !showPip.checked) showPip.click();
          const reviewCheckboxIds = ['show-markers', 'show-pip', 'show-timer', 'show-draw', 'show-shots', 'show-score'];
          for (const id of reviewCheckboxIds) {
            const input = document.getElementById(id);
            if (input instanceof HTMLInputElement && !input.checked) input.click();
          }
        }
        """
    )
    page.wait_for_timeout(250)


def _prepare_timing_capture(page: Page) -> None:
    page.evaluate(
        """
        () => {
          const input = document.getElementById('timing-enabled');
          if (input instanceof HTMLInputElement && !input.checked) input.click();
        }
        """
    )
    page.wait_for_function(
        "() => document.getElementById('timing-enabled')?.checked === true",
        timeout=15_000,
    )
    page.wait_for_timeout(250)


def _prepare_markers_capture(page: Page) -> None:
    page.evaluate(
        """
        () => {
          const input = document.getElementById('markers-enable');
          if (input instanceof HTMLInputElement && !input.checked) input.click();
          const reviewInput = document.getElementById('show-markers');
          if (reviewInput instanceof HTMLInputElement && !reviewInput.checked) reviewInput.click();
        }
        """
    )
    page.wait_for_function(
        "() => document.getElementById('markers-enable')?.checked === true",
        timeout=15_000,
    )
    shot_id = str(
        page.evaluate("() => state?.project?.analysis?.shots?.[0]?.id || ''") or ""
    ).strip()
    if shot_id:
        _api_post(page, "/api/shots/select", {"shot_id": shot_id})
    popup_count = int(page.evaluate("() => (state?.project?.popups || []).length || 0") or 0)
    if popup_count == 0:
        page.evaluate(
            """
            () => {
              const button = document.getElementById('popup-add-bubble');
              if (button instanceof HTMLButtonElement) button.click();
            }
            """
        )
        page.wait_for_function(
            "() => (state?.project?.popups || []).length > 0",
            timeout=15_000,
        )
    page.wait_for_timeout(250)


def _prepare_review_capture(page: Page) -> None:
    _prepare_overlay_and_review_visibility(page)
    const_result = page.evaluate(
        """
        () => {
          const button = document.getElementById('review-add-imported-box');
          if (button instanceof HTMLButtonElement && !document.querySelector('#review-text-box-list .text-box-card')) {
            button.click();
            return true;
          }
          return false;
        }
        """
    )
    if const_result:
        page.wait_for_timeout(400)
    _expand_all_collapsed_controls(page, "review")


def _prepare_pane(page: Page, tool: str) -> None:
    _set_tool(page, tool)
    if tool in {"merge", "overlay", "review"}:
        _prepare_overlay_and_review_visibility(page)
    if tool == "timing":
        _prepare_timing_capture(page)
    if tool == "markers":
        _prepare_markers_capture(page)
    if tool == "review":
        _prepare_review_capture(page)
    else:
        _expand_all_collapsed_controls(page, tool)
    _wait_for_visual_media_ready(page)
    _reset_inspector_scroll(page)


def _capture_pane(page: Page, artifact_root: Path, tool: str, suffix: str = "") -> str:
    file_name = f"{tool}{suffix}.png"
    page.screenshot(path=str(artifact_root / file_name))
    return file_name


def _set_active_stage(page: Page, stage_id: str) -> None:
    current_stage_id = str(
        page.evaluate("() => state?.project?.active_stage_id || ''") or ""
    )
    if current_stage_id == stage_id:
        _wait_for_processing_bar(page)
        return
    _api_post(page, "/api/project/select-stage", {"active_stage_id": stage_id})
    page.wait_for_function(
        "(stageId) => state?.project?.active_stage_id === stageId",
        arg=stage_id,
        timeout=15_000,
    )
    _wait_for_processing_bar(page)


def _queue_stage_ids(page: Page) -> list[str]:
    return list(
        page.evaluate("() => (state?.project?.stages || []).map((stage) => String(stage.id || ''))")
    )


def _requeue_all_stages(page: Page) -> None:
    existing_queue_stage_ids = list(
        page.evaluate(
            "() => (state?.project?.queue || []).map((entry) => String(entry.stage_id || '')).filter(Boolean)"
        )
    )
    for stage_id in existing_queue_stage_ids:
        _api_post(page, "/api/project/queue/remove", {"stage_id": stage_id})
    if existing_queue_stage_ids:
        page.wait_for_function(
            "() => (state?.project?.queue || []).length === 0",
            timeout=30_000,
        )
    for stage_id in _queue_stage_ids(page):
        _api_post(page, "/api/project/queue/add", {"stage_id": stage_id})
    _wait_for_queue_statuses(page, ("queued",), expected_count=len(_queue_stage_ids(page)))


def _wait_for_queue_statuses(
    page: Page, statuses: tuple[str, ...], expected_count: int, timeout_ms: int = 300_000
) -> list[dict[str, Any]]:
    page.wait_for_function(
        """
        ({ statuses, expectedCount }) => {
          const entries = state?.project?.queue || [];
          return entries.length === expectedCount && entries.every((entry) => statuses.includes(String(entry.status || '')));
        }
        """,
        arg={"statuses": list(statuses), "expectedCount": expected_count},
        timeout=timeout_ms,
    )
    return list(page.evaluate("() => state?.project?.queue || []"))


def _read_export_log(page: Page) -> str:
    return str(
        page.locator("#export-log-output").inner_text()
        if page.locator("#export-log-output").count()
        else ""
    )


def _capture_export_log(page: Page, artifact_root: Path, suffix: str) -> dict[str, Any]:
    _set_tool(page, "export")
    page.locator("#show-export-log").click(force=True)
    page.wait_for_selector("#export-log-modal:not([hidden])", timeout=15_000)
    page.wait_for_timeout(200)
    file_name = _capture_pane(page, artifact_root, "export-log", suffix)
    text = _read_export_log(page)
    text_path = artifact_root / f"export-log{suffix}.txt"
    text_path.write_text(text, encoding="utf-8")
    page.locator("#close-export-log").click(force=True)
    page.wait_for_timeout(150)
    return {
        "screenshot": file_name,
        "text_file": text_path.name,
        "line_count": len([line for line in text.splitlines() if line.strip()]),
    }


def _dismiss_auto_open_processing_log(page: Page) -> None:
    page.wait_for_selector("#export-log-modal:not([hidden])", timeout=15_000)
    page.locator("#close-export-log").click(force=True)
    page.wait_for_function(
        "() => document.getElementById('export-log-modal')?.hidden === true",
        timeout=15_000,
    )


def _verify_video_file(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    info = json.loads(result.stdout)
    fmt = info.get("format") or {}
    video_stream = next(
        (stream for stream in info.get("streams", []) if stream.get("codec_type") == "video"),
        None,
    )
    if video_stream is None:
        raise RuntimeError(f"No video stream found in {path}")
    return {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size,
        "duration_s": float(fmt.get("duration") or 0.0),
        "codec": str(video_stream.get("codec_name") or ""),
        "width": int(video_stream.get("width") or 0),
        "height": int(video_stream.get("height") or 0),
    }


def _queue_output_dir(project_copy_root: Path) -> Path:
    return project_copy_root / "Output"


def _run_individual_exports(
    page: Page, artifact_root: Path, project_copy_root: Path
) -> dict[str, Any]:
    _set_tool(page, "queue")
    page.locator("#queue-process-btn").click(force=True)
    _dismiss_auto_open_processing_log(page)
    _set_tool(page, "media")
    entries = _wait_for_queue_statuses(
        page,
        ("complete", "failed"),
        expected_count=3,
        timeout_ms=QUEUE_EXPORT_TIMEOUT_MS,
    )
    log_artifacts = _capture_export_log(page, artifact_root, "-individual")
    proof_dir = artifact_root / "individual-exports"
    proof_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for entry in entries:
        output_path = Path(str(entry.get("output_path") or ""))
        verification = _verify_video_file(output_path) if output_path.exists() else None
        proof_copy = None
        if output_path.exists():
            proof_copy = proof_dir / output_path.name
            shutil.copy2(output_path, proof_copy)
        outputs.append(
            {
                "stage_id": entry.get("stage_id"),
                "status": entry.get("status"),
                "output_path": str(output_path),
                "verification": verification,
                "proof_copy": str(proof_copy) if proof_copy is not None else None,
            }
        )
    return {
        "queue_entries": outputs,
        "export_log": log_artifacts,
        "output_dir": str(_queue_output_dir(project_copy_root)),
    }


def _run_combined_export(
    page: Page, artifact_root: Path, project_copy_root: Path
) -> dict[str, Any]:
    before = {item.name for item in _queue_output_dir(project_copy_root).glob("Combined-*.mp4")}
    _requeue_all_stages(page)
    _set_tool(page, "queue")
    page.locator("#queue-combined-btn").click(force=True)
    _dismiss_auto_open_processing_log(page)
    _set_tool(page, "media")
    _wait_for_queue_statuses(
        page,
        ("complete", "failed"),
        expected_count=3,
        timeout_ms=QUEUE_EXPORT_TIMEOUT_MS,
    )
    page.wait_for_function(
        """
        () => {
          const entries = state?.project?.queue || [];
          return entries.every((entry) => entry.status !== 'processing');
        }
        """,
        timeout=QUEUE_EXPORT_TIMEOUT_MS,
    )
    page.wait_for_function(
        "() => Boolean(state?.project?.last_combined_output_path)",
        timeout=QUEUE_EXPORT_TIMEOUT_MS,
    )
    _wait_for_processing_bar(page, timeout_ms=QUEUE_EXPORT_TIMEOUT_MS)
    combined_output_path = str(
        page.evaluate("() => state?.project?.last_combined_output_path || ''") or ""
    ).strip()
    after_candidates = sorted(_queue_output_dir(project_copy_root).glob("Combined-*.mp4"))
    created = [path for path in after_candidates if path.name not in before]
    combined_path = (
        Path(combined_output_path)
        if combined_output_path
        else (created[-1] if created else (after_candidates[-1] if after_candidates else None))
    )
    log_artifacts = _capture_export_log(page, artifact_root, "-combined")
    if combined_path is None or not combined_path.exists():
        status_text = str(
            page.evaluate(
                """
                () => {
                  const status = document.getElementById('status-message');
                  return status instanceof HTMLElement ? status.textContent || '' : '';
                }
                """
            )
            or ""
        ).strip()
        return {
            "output_path": None,
            "verification": None,
            "export_log": log_artifacts,
            "error": status_text or "Combined export did not produce a *-combined.mp4 file",
        }
    return {
        "output_path": str(combined_path),
        "verification": _verify_video_file(combined_path),
        "export_log": log_artifacts,
        "error": None,
    }


def _export_findings(exports: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for entry in exports.get("individual", {}).get("queue_entries", []):
        if entry.get("status") != "complete":
            findings.append(
                {
                    "pane": "Queue",
                    "issue": f"Individual export for stage {entry.get('stage_id')} ended in status {entry.get('status')}",
                    "reference": "Queue should finish all queued individual renders successfully",
                    "category": "behavioral/state-driven",
                    "code_change_needed": True,
                }
            )
    combined_error = exports.get("combined", {}).get("error")
    if combined_error:
        findings.append(
            {
                "pane": "Queue",
                "issue": combined_error,
                "reference": "Queue should create one combined output after reprocessing the queued stages",
                "category": "behavioral/state-driven",
                "code_change_needed": True,
            }
        )
    return findings


def _capture_color_picker(page: Page, artifact_root: Path) -> str | None:
    _set_tool(page, "overlay")
    _expand_all_collapsed_controls(page, "overlay")
    swatch = page.locator("#overlay-pane .color-swatch-button").first
    if swatch.count() == 0 or not swatch.is_visible():
        return None
    swatch.click(force=True)
    page.wait_for_selector("#color-picker-modal:not([hidden])", timeout=15_000)
    page.wait_for_timeout(150)
    file_name = _capture_pane(page, artifact_root, "color-picker")
    page.locator("#close-color-picker").click(force=True)
    page.wait_for_timeout(150)
    return file_name


def _screenshot_suite(page: Page, artifact_root: Path) -> list[dict[str, Any]]:
    captures: list[dict[str, Any]] = []
    for tool in TOOLS:
        _prepare_pane(page, tool)
        captures.append(
            {
                "tool": tool,
                "title": TOOL_TITLES[tool],
                "file": _capture_pane(page, artifact_root, tool),
            }
        )
    color_picker = _capture_color_picker(page, artifact_root)
    if color_picker is not None:
        captures.append({"tool": "overlay", "title": "Color Picker", "file": color_picker})
    return captures


def _collect_dom_summary(page: Page) -> dict[str, Any]:
    return page.evaluate(
        """
        () => {
          const px = (value) => {
            const parsed = Number.parseFloat(String(value || '').replace('px', '').trim());
            return Number.isFinite(parsed) ? parsed : 0;
          };
          const medianValues = (values) => values.filter((value) => Number.isFinite(value) && value > 0);
          const countColumns = (element) => {
            if (!(element instanceof HTMLElement)) return 0;
            const style = window.getComputedStyle(element);
            if (style.display !== 'grid') return 1;
            const template = String(style.gridTemplateColumns || '').trim();
            if (!template || template === 'none') return 0;
            let depth = 0;
            let token = '';
            const tracks = [];
            for (const char of template) {
              if (char === '(') depth += 1;
              if (char === ')') depth = Math.max(0, depth - 1);
              if (depth === 0 && /\\s/.test(char)) {
                if (token.trim()) tracks.push(token.trim());
                token = '';
                continue;
              }
              token += char;
            }
            if (token.trim()) tracks.push(token.trim());
            return tracks.reduce((count, track) => {
              const repeatMatch = track.match(/^repeat\\((\\d+),/);
              return count + (repeatMatch ? Number(repeatMatch[1]) : 1);
            }, 0);
          };
          const collectPaneMetrics = (tool) => {
            const root = document.querySelector(`[data-tool-pane="${tool}"]`);
            if (!(root instanceof HTMLElement)) return null;
            const title = root.querySelector('.pane-title-row h3, :scope > .section-header > h3');
            const summary = root.querySelector('.pane-title-row .pane-summary-token, .pane-title-row small');
            const controlGrids = Array.from(
              root.querySelectorAll('.control-grid, .trim-bulk-grid, .trim-card-row, .merge-source-controls, .queue-stage-actions, .queue-controls-body, .metrics-grid, .shotml-controls-grid')
            );
            const cards = Array.from(
              root.querySelectorAll('.merge-media-card, .trim-source-card, .media-asset-row, .media-stage-nav-card, .queue-stage-card, .text-box-card, .score-shot-card, .popup-bubble-card')
            );
            const labels = Array.from(
              root.querySelectorAll('label, .merge-source-field > span, .queue-stage-copy small, .trim-source-card-copy small, .setting-summary, .hint')
            );
            const toggles = Array.from(root.querySelectorAll('button.pane-toggle, button[data-section-toggle]'));
            const titleRect = title instanceof HTMLElement ? title.getBoundingClientRect() : null;
            return {
              title_text: title?.textContent?.replace(/\\s+/g, ' ').trim() || '',
              title_font_size_px: title instanceof HTMLElement ? px(window.getComputedStyle(title).fontSize) : 0,
              title_font_weight: title instanceof HTMLElement ? Number(window.getComputedStyle(title).fontWeight) || 0 : 0,
              title_bottom_gap_px: titleRect && summary instanceof HTMLElement ? Math.max(0, summary.getBoundingClientRect().top - titleRect.bottom) : 0,
              summary_text: summary?.textContent?.replace(/\\s+/g, ' ').trim() || '',
              summary_font_size_px: summary instanceof HTMLElement ? px(window.getComputedStyle(summary).fontSize) : 0,
              section_labels: Array.from(root.querySelectorAll(':scope .section-header strong, :scope .section-header h3')).map((node) => node.textContent?.replace(/\\s+/g, ' ').trim() || '').filter(Boolean),
              card_padding_px: medianValues(cards.map((card) => px(window.getComputedStyle(card).paddingTop))),
              card_gap_px: medianValues(cards.map((card) => px(window.getComputedStyle(card).gap))),
              label_font_size_px: medianValues(labels.map((label) => px(window.getComputedStyle(label).fontSize))),
              input_height_px: medianValues(
                Array.from(root.querySelectorAll('input:not([type="checkbox"]):not([type="range"]), select, button.btn, button.btn-sm'))
                  .map((element) => element.getBoundingClientRect().height)
              ),
              control_column_counts: controlGrids.map((element) => ({
                class_name: element.className,
                column_count: countColumns(element),
              })),
              toggle_right_offsets_px: toggles.map((button) => Math.max(0, root.getBoundingClientRect().right - button.getBoundingClientRect().right)),
              has_hint_text: Array.from(root.querySelectorAll('.hint')).map((node) => node.textContent?.replace(/\\s+/g, ' ').trim() || '').filter(Boolean),
            };
          };
          return {
            pane_metrics: {
              project: collectPaneMetrics('project'),
              media: collectPaneMetrics('media'),
              merge: collectPaneMetrics('merge'),
              'trim-sync': collectPaneMetrics('trim-sync'),
              scoring: collectPaneMetrics('scoring'),
              timing: collectPaneMetrics('timing'),
              markers: collectPaneMetrics('markers'),
              overlay: collectPaneMetrics('overlay'),
              review: collectPaneMetrics('review'),
              export: collectPaneMetrics('export'),
              queue: collectPaneMetrics('queue'),
              metrics: collectPaneMetrics('metrics'),
              shotml: collectPaneMetrics('shotml'),
              settings: collectPaneMetrics('settings'),
            },
            helper_copy: Array.from(document.querySelectorAll('.hint'))
              .map((node) => node.textContent?.replace(/\\s+/g, ' ').trim() || '')
              .filter(Boolean),
            queue_cards: Array.from(document.querySelectorAll('#queue-pane .queue-stage-card strong')).map((node) => node.textContent?.trim() || ''),
          };
        }
        """
    )


def _median_or_zero(values: list[float]) -> float:
    cleaned = [float(value) for value in values if isinstance(value, (int, float)) and value > 0]
    return float(median(cleaned)) if cleaned else 0.0


def _categorize_failure(message: str) -> tuple[str, bool]:
    normalized = message.lower()
    if (
        "helper" in normalized
        or "summary" in normalized
        or "hint" in normalized
        or "text" in normalized
    ):
        return "markup/copy", True
    if (
        "column" in normalized
        or "padding" in normalized
        or "height" in normalized
        or "font" in normalized
        or "toggle" in normalized
    ):
        return "CSS/layout", True
    if "queue" in normalized or "missing" in normalized or "stage" in normalized:
        return "behavioral/state-driven", True
    return "screenshot-only", False


def _compute_visual_findings(dom_summary: dict[str, Any]) -> list[dict[str, Any]]:
    pane_metrics = dict(dom_summary.get("pane_metrics") or {})
    baseline_metrics = [pane_metrics.get(name) for name in BASELINE_PANES if pane_metrics.get(name)]
    baseline = {
        "title_font_size_px": _median_or_zero(
            [item.get("title_font_size_px", 0) for item in baseline_metrics]
        ),
        "summary_font_size_px": _median_or_zero(
            [item.get("summary_font_size_px", 0) for item in baseline_metrics]
        ),
        "label_font_size_px": _median_or_zero(
            [
                _median_or_zero(list(item.get("label_font_size_px") or []))
                for item in baseline_metrics
            ]
        ),
        "card_padding_px": _median_or_zero(
            [_median_or_zero(list(item.get("card_padding_px") or [])) for item in baseline_metrics]
        ),
        "input_height_px": _median_or_zero(
            [_median_or_zero(list(item.get("input_height_px") or [])) for item in baseline_metrics]
        ),
        "toggle_right_offset_px": _median_or_zero(
            [
                _median_or_zero(list(item.get("toggle_right_offsets_px") or []))
                for item in baseline_metrics
            ]
        ),
    }
    failures: list[dict[str, Any]] = []
    for tool, metrics in pane_metrics.items():
        if not isinstance(metrics, dict):
            continue
        title_size = float(metrics.get("title_font_size_px") or 0)
        label_size = _median_or_zero(list(metrics.get("label_font_size_px") or []))
        card_padding = _median_or_zero(list(metrics.get("card_padding_px") or []))
        input_height = _median_or_zero(list(metrics.get("input_height_px") or []))
        toggle_offset = _median_or_zero(list(metrics.get("toggle_right_offsets_px") or []))
        hint_text = [item for item in list(metrics.get("has_hint_text") or []) if item]
        issues: list[str] = []
        if (
            baseline["title_font_size_px"]
            and abs(title_size - baseline["title_font_size_px"]) > 0.4
        ):
            issues.append(
                f"title font {title_size:.2f}px drifts from Project/Score/Splits baseline {baseline['title_font_size_px']:.2f}px"
            )
        if (
            baseline["label_font_size_px"]
            and label_size
            and abs(label_size - baseline["label_font_size_px"]) > 0.5
        ):
            issues.append(
                f"label font {label_size:.2f}px drifts from Project/Score/Splits baseline {baseline['label_font_size_px']:.2f}px"
            )
        if (
            baseline["card_padding_px"]
            and card_padding
            and abs(card_padding - baseline["card_padding_px"]) > 3.0
        ):
            issues.append(
                f"card padding {card_padding:.2f}px drifts from Project/Score/Splits baseline {baseline['card_padding_px']:.2f}px"
            )
        if (
            baseline["input_height_px"]
            and input_height
            and abs(input_height - baseline["input_height_px"]) > 4.0
        ):
            issues.append(
                f"control height {input_height:.2f}px drifts from Project/Score/Splits baseline {baseline['input_height_px']:.2f}px"
            )
        if (
            baseline["toggle_right_offset_px"]
            and toggle_offset
            and abs(toggle_offset - baseline["toggle_right_offset_px"]) > 10.0
        ):
            issues.append(
                f"toggle alignment {toggle_offset:.2f}px drifts from Project/Score/Splits baseline {baseline['toggle_right_offset_px']:.2f}px"
            )
        if hint_text and tool not in {"project", "scoring", "timing", "settings"}:
            issues.append(f"unexpected helper/explanatory text present: {hint_text}")
        for issue in issues:
            category, code_change_needed = _categorize_failure(issue)
            failures.append(
                {
                    "pane": TOOL_TITLES.get(tool, tool),
                    "issue": issue,
                    "reference": "Project, Score, and Splits inspector structure",
                    "category": category,
                    "code_change_needed": code_change_needed,
                }
            )
    return failures


def _trim_state_summary(state: dict[str, Any]) -> dict[str, Any]:
    project = dict(state.get("project") or {})
    primary_video = dict(project.get("primary_video") or {})
    primary_trim = dict(project.get("primary_trim_derivative") or {})
    merge_sources = list(project.get("merge_sources") or [])
    return {
        "primary": {
            "trim_active": bool(primary_video.get("trim_active")),
            "effective_media_path": str(primary_video.get("effective_media_path") or ""),
            "original_path": str(primary_video.get("original_path") or ""),
            "active_display_name": str(primary_video.get("active_display_name") or ""),
            "active_path_kind": str(primary_trim.get("active_path_kind") or ""),
            "derivative_path": str(primary_trim.get("derivative_path") or ""),
        },
        "sources": [
            {
                "id": str(source.get("id") or ""),
                "trim_active": bool(source.get("trim_active")),
                "effective_media_path": str(source.get("effective_media_path") or ""),
                "original_media_path": str(source.get("original_media_path") or ""),
                "active_display_name": str(source.get("active_display_name") or ""),
                "active_path_kind": str(
                    (source.get("trim_derivative") or {}).get("active_path_kind") or ""
                ),
                "derivative_path": str(
                    (source.get("trim_derivative") or {}).get("derivative_path") or ""
                ),
            }
            for source in merge_sources
        ],
    }


def _run_trim_slice(page: Page, artifact_root: Path) -> dict[str, Any]:
    _set_tool(page, "trim-sync")
    _api_post(page, "/api/primary/trim", {"clear": True})
    cleared_state = _api_post(page, "/api/merge/source/trim-all", {"clear": True})
    _wait_for_visual_media_ready(page)
    applied_state = _api_post(
        page,
        "/api/merge/source/trim-all",
        {
            "keep_before_beep_s": 2,
            "keep_after_last_shot_s": 2,
            "clear": False,
        },
    )
    _wait_for_visual_media_ready(page)
    summary = {
        "cleared": _trim_state_summary(cleared_state),
        "applied": _trim_state_summary(applied_state),
        "screenshot": _capture_pane(page, artifact_root, "trim-sync", "-slice"),
    }
    primary_cleared = summary["cleared"]["primary"]
    primary_applied = summary["applied"]["primary"]
    if primary_cleared["trim_active"]:
        raise RuntimeError("Primary trim should clear before trim slice apply.")
    if not primary_applied["trim_active"]:
        raise RuntimeError("Primary trim did not become active after trim slice apply.")
    if not all(source["trim_active"] for source in summary["applied"]["sources"]):
        raise RuntimeError("Not all added media sources became trim-active after trim slice apply.")
    return summary


def _write_report(artifact_root: Path, payload: dict[str, Any]) -> None:
    (artifact_root / "audit.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    lines = []
    findings = payload.get("findings") or []
    for finding in findings:
        lines.append(
            f"- {finding['pane']}: {finding['issue']} "
            f"[{finding['category']}; code_change_needed={finding['code_change_needed']}]"
        )
    if not lines:
        lines.append("- No visual consistency defects detected.")
    (artifact_root / "findings.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    artifact_root = (args.artifact_root or _default_artifact_root()).expanduser().resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)

    executable = _app_executable(args.app)
    source_project_json = args.project_path.expanduser().resolve() / "project.json"
    source_project_fingerprint = _file_fingerprint(source_project_json)
    project_copy_root, project_prep = _prepare_project_copy(
        args.project_path,
        artifact_root,
        fresh=args.fresh_project_copy,
        normalize=args.slice != "launch",
    )
    app_session = _spawn_installed_app(executable, project_copy_root, artifact_root)
    try:
        ready_events = _wait_for_ready_file(app_session.process, app_session.ready_file)
        initial_state = _wait_for_backend(app_session.port, project_copy_root)
        payload: dict[str, Any] = {
            "artifact_root": str(artifact_root),
            "timestamp": datetime.now(UTC).isoformat(),
            "slice": args.slice,
            "app": {
                "bundle": str(app_session.bundle),
                "executable": str(app_session.executable),
                "version": app_session.version,
            },
            "project": {
                "source": str(args.project_path.expanduser().resolve()),
                "copy": str(project_copy_root),
                "prep": project_prep,
                "source_project_json_guard": {
                    "path": str(source_project_json),
                    "sha256": source_project_fingerprint["sha256"],
                },
                "loaded_state_path": initial_state.get("project", {}).get("path"),
            },
            "launch": {
                "port": app_session.port,
                "ready_events": ready_events,
            },
            "findings": [],
        }
        if args.slice == "launch":
            _assert_file_unchanged(source_project_json, source_project_fingerprint)
            _write_report(artifact_root, payload)
            print(json.dumps(payload, indent=2))
            return 0

        _warm_installed_app_media(app_session.base_url, initial_state)
        with sync_playwright() as playwright:
            browser, page = _open_page(playwright, app_session.base_url)
            page.wait_for_function(
                "() => (state?.project?.stages || []).length === 3",
                timeout=120_000,
            )
            stage_ids = _queue_stage_ids(page)
            if len(stage_ids) != 3:
                raise RuntimeError(
                    f"Expected 3 stages in normalized project, found {len(stage_ids)}"
                )
            _set_active_stage(page, stage_ids[0])

            if args.slice in {"panes", "full"}:
                payload["screenshots"] = _screenshot_suite(page, artifact_root)
                payload["dom"] = _collect_dom_summary(page)
                payload["project"]["queue_card_labels"] = payload["dom"].get("queue_cards") or []

            if args.slice in {"trim", "full"}:
                payload["trim"] = _run_trim_slice(page, artifact_root)

            if args.slice in {"queue-individual", "queue-combined", "full"}:
                _requeue_all_stages(page)
            if args.slice in {"queue-individual", "full"}:
                payload.setdefault("exports", {})["individual"] = _run_individual_exports(
                    page, artifact_root, project_copy_root
                )
            if args.slice in {"queue-combined", "full"}:
                payload.setdefault("exports", {})["combined"] = _run_combined_export(
                    page, artifact_root, project_copy_root
                )

            findings: list[dict[str, Any]] = []
            if args.slice in {"panes", "full"}:
                findings.extend(_compute_visual_findings(payload.get("dom") or {}))
            if "exports" in payload:
                findings.extend(_export_findings(payload["exports"]))
            payload["findings"] = findings

            _assert_file_unchanged(source_project_json, source_project_fingerprint)
            _write_report(artifact_root, payload)
            print(json.dumps(payload, indent=2))
            browser.close()
    except Exception as exc:
        (artifact_root / "failure.txt").write_text(
            f"{exc}\n\n{_tail_logs(app_session.stdout_log, app_session.stderr_log)}\n",
            encoding="utf-8",
        )
        raise
    finally:
        _terminate_process(app_session.process)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
