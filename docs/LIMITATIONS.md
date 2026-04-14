# Limitations

This page records the current constraints that are visible in the source tree and runtime behavior.

## Media Toolchain

- SplitShot requires `ffmpeg` and `ffprobe`.
- If those tools are not on `PATH`, the app can use bundled binaries through `SPLITSHOT_FFMPEG_DIR` or packaged resources.
- The export pipeline expects a Qt GUI application context before it draws overlay frames.

## Export Scope

- Supported output containers are `.mp4`, `.m4v`, `.mov`, and `.mkv`.
- The video encoder options are H.264 and HEVC.
- Audio export uses AAC.
- Color output is configured for Rec.709 SDR.
- The export pipeline renders locally and does not call a remote service.

## Browser Surface

- The browser server binds to `127.0.0.1` by default.
- Native file picker support is platform dependent; the app falls back to platform-specific dialogs when it can.
- Browser uploads are handled locally and are not cloud-backed.
- The browser review page shows the primary video, an optional secondary angle, and merge media, but the authoritative state still lives in the shared controller.

## Analysis and Scoring

- Shot and beep detection are derived from extracted audio plus the embedded classifier model.
- Detection sensitivity is controlled by the threshold setting; raising the threshold makes detection stricter.
- Scoring presets are limited to the preset sets defined in the source tree.

## Persistence

- Project saves are bundle directories with a `.ssproj` suffix, not single flat files.
- Saved bundles copy browser-session media when the source path points into a temporary browser session directory.

## Governance

- The repository includes a root LICENSE file and uses the MIT License.
- The docs/plans and docs/todos directories are implementation history and task tracking, not the primary user manual.

**Last updated:** 2026-04-13
**Referenced files last updated:** n/a
