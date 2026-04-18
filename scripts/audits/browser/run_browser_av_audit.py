from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, BrowserType, Page, Playwright, sync_playwright

from splitshot.browser.server import BrowserControlServer
from splitshot.ui.controller import ProjectController


ROOT = Path(__file__).resolve().parents[3]
TEST_VIDEO_DIR = ROOT / "tests" / "artifacts" / "test_video"
DEFAULT_PRIMARY_VIDEO = TEST_VIDEO_DIR / "TestVideo1.MP4"


@dataclass(frozen=True, slots=True)
class BrowserTarget:
    name: str
    browser_type_name: str
    display_name: str
    channel: str | None = None
    app_path: Path | None = None


BROWSER_TARGETS: dict[str, BrowserTarget] = {
    "chromium": BrowserTarget(
        name="chromium",
        browser_type_name="chromium",
        display_name="Chromium",
    ),
    "chrome": BrowserTarget(
        name="chrome",
        browser_type_name="chromium",
        display_name="Google Chrome",
        channel="chrome",
        app_path=Path("/Applications/Google Chrome.app"),
    ),
    "edge": BrowserTarget(
        name="edge",
        browser_type_name="chromium",
        display_name="Microsoft Edge",
        channel="msedge",
        app_path=Path("/Applications/Microsoft Edge.app"),
    ),
    "firefox": BrowserTarget(
        name="firefox",
        browser_type_name="firefox",
        display_name="Firefox",
    ),
    "safari": BrowserTarget(
        name="safari",
        browser_type_name="webkit",
        display_name="Safari (WebKit)",
    ),
    "webkit": BrowserTarget(
        name="webkit",
        browser_type_name="webkit",
        display_name="WebKit",
    ),
}
SUPPORTED_BROWSERS = tuple(BROWSER_TARGETS)


@dataclass(slots=True)
class CheckResult:
    name: str
    passed: bool
    detail: str
    data: dict[str, Any] | None = None


@dataclass(slots=True)
class BrowserAvAudit:
    browser: str
    log_path: str
    checks: list[CheckResult]
    data: dict[str, Any] | None = None

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit SplitShot primary-video AV behavior across real browsers via Playwright.",
    )
    parser.add_argument(
        "--browser",
        action="append",
        choices=SUPPORTED_BROWSERS,
        dest="browsers",
        help="Browser target to audit. Defaults to Firefox and Safari-class WebKit.",
    )
    parser.add_argument(
        "--primary-video",
        type=Path,
        default=DEFAULT_PRIMARY_VIDEO,
        help="Primary video path to import during the audit.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run headed instead of headless.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Optional path where the JSON report will be written.",
    )
    return parser


def default_browser_names() -> list[str]:
    return ["firefox", "webkit"]


def expect(condition: bool, name: str, detail: str, data: dict[str, Any] | None = None) -> CheckResult:
    return CheckResult(name=name, passed=condition, detail=detail, data=data)


def launch_browser(playwright: Playwright, target: BrowserTarget, headed: bool) -> Browser:
    if target.app_path is not None and not target.app_path.exists():
        raise FileNotFoundError(f"{target.display_name} is not installed at {target.app_path}")
    browser_type: BrowserType = getattr(playwright, target.browser_type_name)
    launch_kwargs: dict[str, Any] = {"headless": not headed}
    if target.channel:
        launch_kwargs["channel"] = target.channel
    return browser_type.launch(**launch_kwargs)


def open_page(playwright: Playwright, target: BrowserTarget, base_url: str, headed: bool) -> tuple[Browser, Page]:
    browser = launch_browser(playwright, target, headed)
    page = browser.new_page(viewport={"width": 1440, "height": 1024})
    page.goto(base_url, wait_until="domcontentloaded")
    page.wait_for_selector("#current-file")
    return browser, page


def show_project_tool(page: Page) -> None:
    page.locator("[data-tool='project']").click()
    page.wait_for_selector("#primary-file-path", state="visible")


def import_primary_video(page: Page, primary_video: Path) -> dict[str, Any]:
    show_project_tool(page)
    page.locator("#primary-file-path").fill(str(primary_video))
    page.locator("#primary-file-path").press("Enter")
    page.wait_for_function("() => (state?.project?.analysis?.shots?.length || 0) > 0", timeout=120_000)
    page.wait_for_function(
        """
        () => {
          const video = document.getElementById('primary-video');
          return Boolean(
            video
            && Number.isFinite(video.duration)
            && video.duration > 0
            && video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA
          );
        }
        """,
        timeout=30_000,
    )
    return page.evaluate(
        """
        () => ({
          shot_count: state?.project?.analysis?.shots?.length || 0,
          current_file: document.getElementById('current-file')?.textContent?.trim() || '',
          primary_snapshot: primaryVideoStateSnapshot(document.getElementById('primary-video')),
        })
        """
    )


def collect_video_probe(page: Page) -> dict[str, Any]:
    page.locator("#primary-video").click(position={"x": 30, "y": 30})
    return page.evaluate(
        """
        async () => {
          const video = document.getElementById('primary-video');
          const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));
          const snap = () => primaryVideoStateSnapshot(video);
          const initial = snap();
          let playError = null;
          try {
            await video.play();
          } catch (error) {
            playError = String(error);
          }
          await wait(1200);
          const afterPlay = snap();
          video.muted = true;
          await wait(120);
          const muted = snap();
          video.muted = false;
          await wait(120);
          const unmuted = snap();
          video.pause();
          const initialTime = Number(initial.current_time_s || 0);
          const afterPlayTime = Number(afterPlay.current_time_s || 0);
          return {
            initial,
            after_play: afterPlay,
            muted,
            unmuted,
            play_error: playError,
            advanced_s: Math.round((afterPlayTime - initialTime) * 1000) / 1000,
          };
        }
        """
    )


def media_start_summary(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    starts = [entry for entry in entries if entry.get("event") == "media.start"]
    return [
        {
            "proxied": bool(entry.get("proxied")),
            "proxy_reason": entry.get("proxy_reason"),
            "served_path": entry.get("served_path"),
            "start": entry.get("start"),
            "end": entry.get("end"),
        }
        for entry in starts[-3:]
    ]


def _snapshot_has_audio_signal(snapshot: dict[str, Any]) -> bool:
    if snapshot.get("moz_has_audio") is True:
        return True
    audio_tracks = snapshot.get("audio_tracks")
    if isinstance(audio_tracks, (int, float)) and audio_tracks > 0:
        return True
    decoded_bytes = snapshot.get("webkit_audio_decoded_bytes")
    return isinstance(decoded_bytes, (int, float)) and decoded_bytes > 0


def run_browser_audit(
    playwright: Playwright,
    target_name: str,
    primary_video: Path,
    headed: bool,
) -> BrowserAvAudit:
    target = BROWSER_TARGETS[target_name]
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0, log_level="off")
    server.start_background(open_browser=False)
    browser: Browser | None = None
    try:
        try:
            browser, page = open_page(playwright, target, server.url, headed)
        except Exception as error:  # noqa: BLE001
            return BrowserAvAudit(
                browser=target_name,
                log_path=str(server.activity.path),
                checks=[
                    CheckResult(
                        name="browser_available",
                        passed=False,
                        detail=f"{target.display_name} could not be launched: {error}",
                    )
                ],
                data=None,
            )

        before_seq = int(server.activity.snapshot()["cursor"])
        import_state = import_primary_video(page, primary_video)
        probe = collect_video_probe(page)
        entries = server.activity.snapshot(after_seq=before_seq, limit=400)["entries"]
        compat_created = [entry for entry in entries if entry.get("event") == "media.compatibility.created"]
        compat_rejected = [entry for entry in entries if entry.get("event") == "media.compatibility.rejected"]
        media_starts = media_start_summary(entries)

        proxied_preview = any(entry.get("proxied") for entry in media_starts)
        audio_signal = any(
            _snapshot_has_audio_signal(snapshot)
            for snapshot in (
                import_state["primary_snapshot"],
                probe["initial"],
                probe["after_play"],
                probe["unmuted"],
            )
        )
        mute_round_trip = (
            probe["muted"].get("muted") is True
            and probe["unmuted"].get("muted") is False
            and probe["unmuted"].get("default_muted") is False
        )
        playback_advanced = probe.get("play_error") is None and float(probe.get("advanced_s") or 0.0) > 0.25
        analysis_loaded = int(import_state.get("shot_count") or 0) > 0 and float(import_state["primary_snapshot"].get("duration_s") or 0.0) > 0

        data = {
            "log_path": str(server.activity.path),
            "import_state": import_state,
            "probe": probe,
            "media_starts": media_starts,
            "compat_created": len(compat_created),
            "compat_rejected": len(compat_rejected),
        }
        checks = [
            expect(
                analysis_loaded,
                "analysis_loaded",
                "Primary import should finish with shots detected and a loaded primary video.",
                {
                    "shot_count": import_state.get("shot_count"),
                    "duration_s": import_state["primary_snapshot"].get("duration_s"),
                },
            ),
            expect(
                proxied_preview and not compat_rejected,
                "compatibility_preview_served",
                "The browser should receive a proxied compatibility preview without rejection.",
                {
                    "media_starts": media_starts,
                    "compat_created": len(compat_created),
                    "compat_rejected": len(compat_rejected),
                },
            ),
            expect(
                audio_signal,
                "audio_signal_detected",
                "Browser media state should expose an audio-capable signal after import or playback.",
                {
                    "initial": probe["initial"],
                    "after_play": probe["after_play"],
                },
            ),
            expect(
                playback_advanced,
                "playback_advances",
                "Playback should advance after the scripted click-plus-play path.",
                {
                    "advanced_s": probe.get("advanced_s"),
                    "play_error": probe.get("play_error"),
                    "initial_time_s": probe["initial"].get("current_time_s"),
                    "after_play_time_s": probe["after_play"].get("current_time_s"),
                },
            ),
            expect(
                mute_round_trip,
                "mute_round_trip",
                "Mute then unmute should leave the primary video unmuted with defaultMuted cleared.",
                {
                    "muted": probe["muted"],
                    "unmuted": probe["unmuted"],
                },
            ),
        ]
        return BrowserAvAudit(
            browser=target_name,
            log_path=str(server.activity.path),
            checks=checks,
            data=data,
        )
    finally:
        if browser is not None:
            browser.close()
        server.shutdown()


def summarize_results(results: list[BrowserAvAudit]) -> str:
    lines = ["# Browser AV Audit", ""]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"## {result.browser}: {status}")
        lines.append(f"- Log: {result.log_path}")
        for check in result.checks:
            mark = "PASS" if check.passed else "FAIL"
            lines.append(f"- {mark} {check.name}: {check.detail}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    browsers = args.browsers or default_browser_names()
    primary_video = args.primary_video.resolve()
    if not primary_video.is_file():
        raise SystemExit(f"Primary video not found: {primary_video}")

    with sync_playwright() as playwright:
        results = [
            run_browser_audit(playwright, browser_name, primary_video, args.headed)
            for browser_name in browsers
        ]

    payload = {
        "primary_video": str(primary_video),
        "results": [
            {
                "browser": result.browser,
                "passed": result.passed,
                "log_path": result.log_path,
                "checks": [asdict(check) for check in result.checks],
                "data": result.data,
            }
            for result in results
        ],
    }
    if args.report_json is not None:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(summarize_results(results))
    print(json.dumps(payload, indent=2))
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
