# SplitShot Packaging

The current supported packaging path is source/repo distribution with one command:

```bash
uv run --python 3.12 splitshot
```

That launches the browser control interface by default. The secondary desktop UI is:

```bash
uv run --python 3.12 splitshot --desktop
```

Run the runtime check with:

```bash
uv run --python 3.12 splitshot --check
```

Native `.dmg` and `.exe` artifacts are optional later work. If/when they are needed, they must be built on the target operating system:

- Build macOS `.dmg` on macOS.
- Build Windows `.exe` on Windows.

Any distribution must include:

- SplitShot Python package.
- PySide6/Qt runtime.
- NumPy runtime.
- Browser-control static assets.
- `ffmpeg` and `ffprobe`.

## FFmpeg Placement

Before building, provide platform binaries in one of two ways:

1. Set `SPLITSHOT_FFMPEG_DIR` to a directory containing `ffmpeg` and `ffprobe`.
2. Put the binaries under:

```text
src/splitshot/resources/ffmpeg/macos/ffmpeg
src/splitshot/resources/ffmpeg/macos/ffprobe
src/splitshot/resources/ffmpeg/windows/ffmpeg.exe
src/splitshot/resources/ffmpeg/windows/ffprobe.exe
```

The runtime resolver checks bundled resources first, then falls back to `PATH` for development.

## macOS DMG

Optional later workflow:

```bash
uv sync --extra package
./packaging/build_macos.sh
```

Expected output:

```text
dist/SplitShot.dmg
```

## Windows EXE

Optional later workflow. Run in PowerShell on Windows:

```powershell
uv sync --extra package
powershell -ExecutionPolicy Bypass -File packaging/build_windows.ps1
```

Expected output:

```text
dist\SplitShot\SplitShot.exe
```

## Browser Control

The browser control UI is the default mode:

```bash
uv run --python 3.12 splitshot
```
