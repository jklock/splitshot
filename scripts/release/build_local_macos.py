#!/usr/bin/env python3
"""Build a local macOS Electron package using the same cert import path as CI."""

from __future__ import annotations

import os
import plistlib
import secrets
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from platform import machine

REPO = Path(__file__).resolve().parents[2]
LOGIN_KEYCHAIN = Path.home() / "Library" / "Keychains" / "login.keychain-db"
DEFAULT_IDENTITY = "Apple Development: jklockenkemper@icloud.com (34WPHG75HQ)"


def run(command: list[str], *, env: dict[str, str] | None = None, cwd: Path = REPO) -> None:
    print(f"[local-macos-build] {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def has_complete_notary_env(env: dict[str, str]) -> bool:
    api = [env.get("APPLE_API_KEY"), env.get("APPLE_API_KEY_ID"), env.get("APPLE_API_ISSUER")]
    fallback = [
        env.get("APPLE_ID"),
        env.get("APPLE_APP_SPECIFIC_PASSWORD"),
        env.get("APPLE_TEAM_ID"),
    ]
    api_any = any(api)
    fallback_any = any(fallback)
    if api_any and not all(api):
        raise SystemExit(
            "Incomplete Apple API key notarization env; set all of APPLE_API_KEY, "
            "APPLE_API_KEY_ID, APPLE_API_ISSUER."
        )
    if fallback_any and not all(fallback):
        raise SystemExit(
            "Incomplete Apple ID notarization env; set all of APPLE_ID, "
            "APPLE_APP_SPECIFIC_PASSWORD, APPLE_TEAM_ID."
        )
    return all(api) or all(fallback)


def export_identity(temp_dir: Path, identity: str) -> tuple[Path, str]:
    if not LOGIN_KEYCHAIN.exists():
        raise SystemExit(f"login keychain not found: {LOGIN_KEYCHAIN}")
    p12_password = f"splitshot-{secrets.token_urlsafe(24)}"
    p12_path = temp_dir / "splitshot-local-signing.p12"
    export_command = [
        "security",
        "export",
        "-k",
        str(LOGIN_KEYCHAIN),
        "-t",
        "identities",
        "-f",
        "pkcs12",
        "-P",
        p12_password,
        "-o",
        str(p12_path),
    ]
    run(export_command)
    verify_import(temp_dir, p12_path, p12_password, identity)
    return p12_path, p12_password


def existing_ffmpeg_override() -> str | None:
    candidates = [
        Path(
            "/Applications/SplitShot.app/Contents/Resources/bundle/src/splitshot/resources/ffmpeg/macos"
        ),
    ]
    for candidate in candidates:
        if (candidate / "ffmpeg").exists() and (candidate / "ffprobe").exists():
            return str(candidate)
    return None


def _portable_ffmpeg_arch() -> str:
    return "arm64" if machine().lower() in {"arm64", "aarch64"} else "amd64"


def _download(url: str, target: Path) -> None:
    print(f"[local-macos-build] download {url} -> {target}", flush=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    run(["curl", "-LfsS", "-o", str(target), url])


def _extract_tool_from_zip(archive: Path, tool_name: str, destination: Path) -> Path:
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            if Path(member.filename).name != tool_name or member.is_dir():
                continue
            extracted = destination / tool_name
            extracted.parent.mkdir(parents=True, exist_ok=True)
            with zipped.open(member) as source, extracted.open("wb") as target:
                shutil.copyfileobj(source, target)
            extracted.chmod(0o755)
            return extracted
    raise SystemExit(f"Could not find {tool_name} inside {archive}")


def prepare_portable_ffmpeg_override(temp_dir: Path) -> str:
    platform_dir = temp_dir / "portable-ffmpeg"
    platform_dir.mkdir(parents=True, exist_ok=True)
    arch = _portable_ffmpeg_arch()
    for tool in ("ffmpeg", "ffprobe"):
        archive = temp_dir / f"{tool}.zip"
        url = f"https://ffmpeg.martin-riedl.de/redirect/latest/macos/{arch}/release/{tool}.zip"
        _download(url, archive)
        _extract_tool_from_zip(archive, tool, platform_dir)
    return str(platform_dir)


def configure_ffmpeg_bundle_env(env: dict[str, str], temp_dir: Path) -> None:
    env.pop("SPLITSHOT_BUNDLED_FFMPEG_DIR", None)
    env.pop("SPLITSHOT_USE_HOST_FFMPEG", None)
    ffmpeg_override = existing_ffmpeg_override()
    if ffmpeg_override:
        env["SPLITSHOT_BUNDLED_FFMPEG_DIR"] = ffmpeg_override
        return
    env["SPLITSHOT_BUNDLED_FFMPEG_DIR"] = prepare_portable_ffmpeg_override(temp_dir)


def verify_import(temp_dir: Path, p12_path: Path, p12_password: str, identity: str) -> None:
    keychain_path = temp_dir / "splitshot-local-build.keychain-db"
    keychain_password = secrets.token_urlsafe(24)
    try:
        run(["security", "create-keychain", "-p", keychain_password, str(keychain_path)])
        run(["security", "unlock-keychain", "-p", keychain_password, str(keychain_path)])
        run(["security", "set-keychain-settings", str(keychain_path)])
        run(
            [
                "security",
                "import",
                str(p12_path),
                "-k",
                str(keychain_path),
                "-T",
                "/usr/bin/codesign",
                "-T",
                "/usr/bin/productbuild",
                "-P",
                p12_password,
            ]
        )
        result = subprocess.run(
            ["security", "find-identity", "-v", "-p", "codesigning", str(keychain_path)],
            cwd=REPO,
            check=True,
            text=True,
            capture_output=True,
        )
        if identity not in result.stdout:
            raise SystemExit(f"Exported cert did not expose expected identity: {identity}")
    finally:
        subprocess.run(["security", "delete-keychain", str(keychain_path)], cwd=REPO, check=False)


def install_latest_dmg() -> None:
    artifacts = sorted(
        (REPO / "electron" / "build").glob("*.dmg"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not artifacts:
        raise SystemExit("No DMG found under electron/build after local macOS build.")
    dmg = artifacts[0]
    attached = subprocess.run(
        ["hdiutil", "attach", str(dmg), "-nobrowse", "-readonly", "-plist"],
        cwd=REPO,
        check=True,
        capture_output=True,
    )
    attach_payload = plistlib.loads(attached.stdout)
    mount_points = [
        Path(str(entity["mount-point"]))
        for entity in attach_payload.get("system-entities", [])
        if entity.get("mount-point")
    ]
    if not mount_points:
        raise SystemExit(f"Mounted DMG did not report a mount point: {dmg}")
    mount_point = mount_points[0]
    try:
        app = mount_point / "SplitShot.app"
        if not app.exists():
            raise SystemExit(f"Mounted DMG did not contain SplitShot.app: {dmg}")
        destination = Path("/Applications/SplitShot.app")
        backup: Path | None = None
        if destination.exists():
            trash = Path.home() / ".Trash"
            trash.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            backup = trash / f"SplitShot-before-local-build-{timestamp}.app"
            if backup.exists():
                raise SystemExit(f"Refusing to overwrite existing backup: {backup}")
            shutil.move(str(destination), str(backup))
            print(f"[local-macos-build] preserved previous app at {backup}", flush=True)
        try:
            run(["/usr/bin/ditto", str(app), str(destination)])
        except Exception:
            if backup is not None and backup.exists() and not destination.exists():
                shutil.move(str(backup), str(destination))
            raise
    finally:
        subprocess.run(["hdiutil", "detach", str(mount_point), "-quiet"], cwd=REPO, check=False)


def main() -> int:
    if sys.platform != "darwin":
        raise SystemExit("Local macOS build helper only supports macOS.")
    identity = os.environ.get("SPLITSHOT_MAC_CERT_IDENTITY", DEFAULT_IDENTITY)
    env = os.environ.copy()
    notarize = has_complete_notary_env(env)
    temp_dir = Path(tempfile.mkdtemp(prefix="splitshot-local-signing-"))
    try:
        p12_path, p12_password = export_identity(temp_dir, identity)
        env["CSC_LINK"] = str(p12_path)
        env["CSC_KEY_PASSWORD"] = p12_password
        env["CSC_IDENTITY_AUTO_DISCOVERY"] = "false"
        env["CSC_NAME"] = identity
        env["SPLITSHOT_MAC_NOTARIZE"] = "1" if notarize else "0"
        configure_ffmpeg_bundle_env(env, temp_dir)
        run(["npm", "run", "build:mac"], env=env, cwd=REPO / "electron")
        install_latest_dmg()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
