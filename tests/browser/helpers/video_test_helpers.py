import os
from pathlib import Path

from splitshot.browser.server import BrowserControlServer

from .activity_tracker import ActivityTracker


DEFAULT_VIEWPORT = {"width": 1280, "height": 900}

_REPO_ROOT = Path(__file__).resolve().parents[3]
_VIDEO_SOURCE = _REPO_ROOT / "05072026"
_REAL_VIDEO_MAP = {
    "primary": _VIDEO_SOURCE / "Stage2.MP4",
    "merge": _VIDEO_SOURCE / "Stage3.MP4",
    "merge2": _VIDEO_SOURCE / "Stage4.MP4",
}


_TEMP_BASE = _REPO_ROOT / "tmp" / "codex" / "video_source"

_VIDEO_COUNTER = 0


def _resolve_video(name: str) -> Path:
    """Return symlink to real video from 05072026/, or None if unavailable."""
    global _VIDEO_COUNTER
    real = _REAL_VIDEO_MAP.get(name)
    if real is not None and real.exists():
        _VIDEO_COUNTER += 1
        _TEMP_BASE.mkdir(parents=True, exist_ok=True)
        dest = _TEMP_BASE / f"{name}-{_VIDEO_COUNTER}.mp4"
        if dest.is_symlink() and not dest.exists():
            dest.unlink()
        if not dest.exists():
            os.symlink(str(real.resolve()), str(dest))
        if not dest.exists():
            raise FileNotFoundError(f"Expected repo-local video symlink to exist: {dest}")
        return dest
    return None


def open_page(playwright, server: BrowserControlServer, viewport: dict | None = None):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport=viewport or DEFAULT_VIEWPORT)
    page.set_default_timeout(180000)
    page.on("dialog", lambda dialog: dialog.accept())
    page.goto(server.url, wait_until="domcontentloaded")
    return browser, page


def create_project(page, project_dir: str) -> None:
    page.evaluate("(path) => createNewProject(path)", project_dir)
    page.wait_for_function("() => Boolean(state?.project?.path)", timeout=180000)


def import_primary_video(page, path: Path) -> None:
    page.locator("#primary-file-input").set_input_files(str(path))
    page.wait_for_function("() => Boolean(state?.project?.primary_video?.path)", timeout=180000)


def import_merge_video(page, path: Path, expected_count: int = 1) -> None:
    page.locator("#merge-media-input").set_input_files(str(path))
    page.wait_for_function(
        f"() => (state?.project?.merge_sources || []).length >= {expected_count}",
        timeout=180000,
    )


def open_tool(page, tool_id: str) -> None:
    page.locator(f'button[data-tool="{tool_id}"]').click(force=True)
    page.wait_for_function("(tool) => activeTool === tool", arg=tool_id, timeout=30000)


def ensure_stage_in_project(
    page, stage_id: str = "test-stage-1", label: str = "Stage 1", primary_path: str | None = None
) -> None:
    """Ensure at least one stage exists in the project."""
    page.evaluate(
        """({ stage_id, label, primary_path }) => {
            if (!state.project.stages) state.project.stages = [];
            const exists = state.project.stages.some(s => s.id === stage_id);
            if (!exists) {
                state.project.stages.push({
                    id: stage_id,
                    label,
                    order_index: state.project.stages.length,
                    primary_media: primary_path ? { path: primary_path } : null,
                    added_media: [],
                });
            }
            state.project.active_stage_id = stage_id;
        }""",
        {
            "stage_id": stage_id,
            "label": label,
            "primary_path": str(primary_path) if primary_path else None,
        },
    )


def ensure_project_with_primary_and_merge(
    page, primary_path: Path, merge_path: Path, project_name: str
) -> None:
    if not page.evaluate("Boolean(state?.project?.path)"):
        project_dir = str(primary_path.parent / project_name)
        create_project(page, project_dir)
    if not page.evaluate("Boolean(state?.project?.primary_video?.path)"):
        import_primary_video(page, primary_path)
    merge_count = page.evaluate("() => (state?.project?.merge_sources || []).length")
    if merge_count == 0:
        import_merge_video(page, merge_path)


def navigate_to_tool(page, tool_id: str) -> None:
    page.locator(f'button[data-tool="{tool_id}"]').click(force=True)
    page.wait_for_timeout(300)
    assert page.evaluate("activeTool") == tool_id


def wait_for_ui_settled(page, timeout: int = 15000) -> None:
    page.wait_for_function(
        "() => document.getElementById('processing-bar')?.hidden !== false",
        timeout=timeout,
    )
    page.wait_for_timeout(150)


def get_state(page, expr: str):
    return page.evaluate(f"() => {expr}")


def get_merge_source_state(page, source_id: str | None = None, index: int = 0):
    return page.evaluate(
        """(idx) => {
            const sources = state?.project?.merge_sources || [];
            if (!sources.length) return null;
            const s = sources[idx] || sources[0];
            const td = s.trim_derivative;
            return {
                source_id: s.id,
                has_derivative: Boolean(td),
                active_path_kind: td?.active_path_kind ?? null,
                derivative_path: td?.derivative_path ?? null,
                effective_media_path: s.effective_media_path ?? s.asset?.path ?? null,
                trim_active: Boolean(s.trim_active),
                start_s: td?.start_s ?? null,
                end_s: td?.end_s ?? null,
                sync_offset_ms: s.sync_offset_ms ?? 0,
                pip_size_percent: s.pip_size_percent ?? null,
                opacity: s.opacity ?? null,
                placement_mode: s.placement?.mode ?? null,
                waveform_sample_count: s.waveform_sample_count ?? null,
            };
        }""",
        index,
    )


def get_primary_media_state(page):
    return page.evaluate(
        """() => {
            const primary = state?.project?.primary_video || {};
            const td = state?.project?.primary_trim_derivative || {};
            return {
                has_derivative: Boolean(td && Object.keys(td).length),
                active_path_kind: td?.active_path_kind ?? null,
                derivative_path: td?.derivative_path ?? null,
                effective_media_path: primary?.effective_media_path ?? primary?.path ?? null,
                trim_active: Boolean(primary?.trim_active),
                start_s: td?.start_s ?? null,
                end_s: td?.end_s ?? null,
                active_display_name: primary?.active_display_name ?? "",
                original_display_name: primary?.original_display_name ?? "",
                active_duration_ms: primary?.active_duration_ms ?? primary?.duration_ms ?? null,
            };
        }"""
    )


def setup_server_and_browser(synthetic_video_factory, primary_kwargs=None, merge_kwargs=None):
    primary_kwargs = dict(primary_kwargs or {})
    merge_kwargs = dict(merge_kwargs or {})
    primary_kwargs.setdefault("name", "primary")
    primary_kwargs.setdefault("duration_ms", 4000)
    primary_kwargs.setdefault("beep_ms", 500)
    primary_kwargs.setdefault("shot_times_ms", [800, 1200, 1600])
    merge_kwargs.setdefault("name", "merge")
    merge_kwargs.setdefault("duration_ms", 4000)
    merge_kwargs.setdefault("beep_ms", 600)

    primary_path = _resolve_video(primary_kwargs["name"])
    merge_path = _resolve_video(merge_kwargs["name"])
    if primary_path is None:
        primary_path = Path(synthetic_video_factory(**primary_kwargs))
    if merge_path is None:
        merge_path = Path(synthetic_video_factory(**merge_kwargs))
    server = BrowserControlServer(port=0)
    server.start_background(open_browser=False)
    tracker = ActivityTracker(server.url)
    return server, tracker, primary_path, merge_path
