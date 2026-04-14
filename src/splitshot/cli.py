from __future__ import annotations

import argparse
import sys
from importlib import resources
from pathlib import Path
from typing import Sequence

from splitshot.app import run as run_desktop_app
from splitshot.browser.server import BrowserControlServer
from splitshot.media.ffmpeg import resolve_media_binary
from splitshot.ui.controller import ProjectController


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
    controller = ProjectController()
    if project_path is not None:
        controller.open_project(str(project_path))
    server = BrowserControlServer(controller=controller, host=host, port=port, log_level=log_level)
    print(f"SplitShot browser control running at {server.url}")
    print(f"SplitShot activity log: {server.activity.path}")
    server.serve_forever(open_browser=open_browser)
    return 0


def run_desktop(project_path: Path | None = None) -> int:
    return run_desktop_app(project_path=project_path)


def run_check() -> int:
    print("SplitShot runtime check")
    for tool in ("ffmpeg", "ffprobe"):
        print(f"- {tool}: {resolve_media_binary(tool)}")
    static_root = resources.files("splitshot.browser.static")
    for asset in ("index.html", "styles.css", "app.js"):
        target = static_root / asset
        if not target.is_file():
            raise SystemExit(f"Missing browser asset: {asset}")
        print(f"- browser:{asset}: present")
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
