from __future__ import annotations

import shutil
import subprocess
from importlib import resources
from pathlib import Path

from splitshot.media.ffmpeg import resolve_media_binary


def _version(binary: str) -> str:
    result = subprocess.run(
        [binary, "-version"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()[0]


def main() -> None:
    checks: list[tuple[str, str]] = []

    ffmpeg = resolve_media_binary("ffmpeg")
    ffprobe = resolve_media_binary("ffprobe")
    checks.append(("ffmpeg", f"{ffmpeg} :: {_version(ffmpeg)}"))
    checks.append(("ffprobe", f"{ffprobe} :: {_version(ffprobe)}"))

    browser_assets = resources.files("splitshot.browser.static")
    for asset in ("index.html", "styles.css", "app.js"):
        asset_path = browser_assets / asset
        if not asset_path.is_file():
            raise SystemExit(f"Missing browser asset: {asset}")
        checks.append((f"browser:{asset}", "present"))

    for script in ("packaging/build_macos.sh", "packaging/build_windows.ps1", "packaging/splitshot.spec"):
        path = Path(script)
        if not path.exists():
            raise SystemExit(f"Missing packaging file: {script}")
        checks.append((script, "present"))

    if shutil.which("hdiutil"):
        checks.append(("macOS dmg tool", "hdiutil present"))
    else:
        checks.append(("macOS dmg tool", "hdiutil not present on this platform"))

    print("SplitShot toolchain validation")
    for name, result in checks:
        print(f"- {name}: {result}")


if __name__ == "__main__":
    main()
