# Limitations

This page records the current constraints that are visible in the source tree and runtime behavior.

## Media Toolchain

- SplitShot requires `ffmpeg` and `ffprobe`.
- Source runs require those tools on `PATH`.
- Packaged Electron builds are expected to bundle those tools and prepend the bundled directory to `PATH` at runtime.
- The export pipeline expects a Qt GUI application context before it draws overlay frames.
- Headless mode (`--headless`) runs the HTTP server without Qt, but export still requires Qt for overlay frame rendering.

## Export Scope

- Supported output containers are `.mp4`, `.m4v`, `.mov`, and `.mkv`.
- The video encoder options are H.264 and HEVC.
- Audio export uses AAC.
- Color output is configured for Rec.709 SDR.
- The export pipeline renders locally and does not call a remote service.

## Browser Surface

- The browser server binds to `127.0.0.1` by default.
- Native file pickers are supported on macOS, Windows, and Linux. After a project is selected, each picker starts in its owned project subfolder, but the operating-system dialog can still navigate elsewhere; external selections are copied into the project before use. Availability still depends on the host desktop session and its native-dialog dependencies.
- Browser file imports are handled locally and are not cloud-backed.
- Browser-uploaded media larger than 8 GiB are rejected; use the direct path import workflow for larger local files.
- The browser review page shows the primary video, an optional secondary angle, and merge media, but the authoritative state still lives in the shared controller.

## Analysis and Scoring

- Shot and beep detection are derived from extracted audio plus the embedded classifier model.
- Detection sensitivity is controlled by the threshold setting; raising the threshold makes detection stricter.
- Scoring presets are limited to the preset sets defined in the source tree.

## Persistence

- Project saves are bundle directories with a `.ssproj` suffix, not single flat files.
- A project contains `project.json`, `Input/`, `CSV/`, `Markers/`, and `Output/`.
- Import operations copy external selections into the project before use. Saving and autosaving write metadata only and do not repair manually introduced external paths.
- Project-local paths are portable across macOS, Windows, and Linux; paths deliberately introduced outside the project remain machine-specific.

## Electron Desktop App

- The Electron shell has build and smoke coverage for macOS, Windows, and Linux in CI, but macOS remains the only signed/notarized release path.
- The Electron app bundles the Python backend via `scripts/bundle-python.js`. The bundle must be regenerated when `src/splitshot/` or `pyproject.toml` changes.
- The `--headless` CLI flag is used by the Electron shell to start the Python backend. Running `splitshot` directly (without `--headless`) launches the Qt desktop runtime, which is redundant inside Electron.

## Governance

- The repository includes a root LICENSE file and uses the MIT License.
- Historical planning directories are not part of the active documentation set.
- Current product guidance lives in this `docs/` directory, the package-level `src/splitshot/.../README.md` files, and the browser audit scripts under `scripts/`.
