from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path
from typing import Sequence

from splitshot.media.ffmpeg import MediaError, resolve_media_binary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="splitshot",
        description="SplitShot local stage video analyzer. Browser control is the default mode.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--web",
        action="store_true",
        help="Launch the local browser control interface. This is the default.",
    )
    mode.add_argument(
        "--desktop",
        action="store_true",
        help="Launch the secondary PySide desktop interface.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Browser bind host.")
    parser.add_argument("--port", type=int, default=8765, help="Browser bind port.")
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser automatically.")
    parser.add_argument(
        "--log-level",
        choices=("off", "error", "warning", "info", "debug"),
        default="off",
        help="Mirror browser activity logs to the terminal at or above this level. File logging stays on.",
    )
    parser.add_argument("--project", type=Path, help="Optional .ssproj bundle to open at startup.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the local media toolchain and packaged browser assets, then exit.",
    )
    return parser


def run_browser(
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    project_path: Path | None = None,
    log_level: str = "off",
) -> int:
    try:
        BrowserControlServer, ProjectController = _browser_runtime()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"SplitShot browser runtime is unavailable: {exc}") from exc

    controller = ProjectController()
    if project_path is not None:
        controller.open_project(str(project_path))
    server = BrowserControlServer(controller=controller, host=host, port=port, log_level=log_level)
    if not open_browser:
        print(f"Open SplitShot at {server.url}")
    if log_level != "off":
        print(f"SplitShot activity log: {server.activity.path}")
    server.serve_forever(open_browser=open_browser)
    return 0


def run_desktop(project_path: Path | None = None) -> int:
    try:
        run_desktop_app = _desktop_runtime()
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"SplitShot desktop runtime is unavailable: {exc}") from exc
    return run_desktop_app(project_path=project_path)


def _browser_runtime():
    from splitshot.browser.server import BrowserControlServer
    from splitshot.ui.controller import ProjectController

    return BrowserControlServer, ProjectController


def _desktop_runtime():
    from splitshot.app import run as run_desktop_app

    return run_desktop_app


def _platform_label() -> str:
    if sys.platform.startswith("darwin"):
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    return "linux"


def _check_media_tool(tool: str) -> str:
    resolved = resolve_media_binary(tool)
    process = subprocess.run(
        [resolved, "-version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        error_text = process.stderr.strip() or process.stdout.strip() or "unknown error"
        raise MediaError(f"{tool} failed to start: {error_text}")
    return resolved


def _check_qt_runtime() -> str:
    try:
        from PySide6 import __version__ as pyside_version
        from splitshot.export.pipeline import prepare_export_runtime
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"PySide6 runtime unavailable: {exc}") from exc

    prepare_export_runtime()
    return pyside_version


def _check_dialog_runtime() -> str:
    if sys.platform.startswith("darwin"):
        helper = shutil.which("osascript")
        if not helper:
            raise RuntimeError("macOS file dialogs require osascript, but it was not found in PATH.")
        return helper

    try:
        import tkinter  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Native file dialogs require tkinter in this environment: {exc}") from exc

    return "tkinter"


def run_check() -> int:
    print("SplitShot runtime check")
    print(f"- platform: {_platform_label()}")
    print(f"- python: {sys.executable}")

    failures: list[str] = []

    for tool in ("ffmpeg", "ffprobe"):
        try:
            print(f"- {tool}: {_check_media_tool(tool)}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{tool}: {exc}")

    try:
        print(f"- qt: PySide6 {_check_qt_runtime()}")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"qt: {exc}")

    try:
        print(f"- dialogs: {_check_dialog_runtime()}")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"dialogs: {exc}")

    static_root = resources.files("splitshot.browser.static")
    for asset in ("index.html", "styles.css", "app.js"):
        target = static_root / asset
        if not target.is_file():
            failures.append(f"browser:{asset}: missing")
            continue
        print(f"- browser:{asset}: present")

    if failures:
        for failure in failures:
            print(f"- failure: {failure}")
        raise SystemExit("SplitShot runtime check failed.")

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.check:
        return run_check()
    if args.desktop:
        return run_desktop(project_path=args.project)
    return run_browser(
        host=args.host,
        port=args.port,
        open_browser=not args.no_open,
        project_path=args.project,
        log_level=args.log_level,
    )


def desktop_main(argv: Sequence[str] | None = None) -> int:
    forwarded = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(["--desktop", *forwarded])
    return run_desktop(project_path=args.project)


def web_main(argv: Sequence[str] | None = None) -> int:
    forwarded = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(["--web", *forwarded])
    return run_browser(
        host=args.host,
        port=args.port,
        open_browser=not args.no_open,
        project_path=args.project,
        log_level=args.log_level,
    )
