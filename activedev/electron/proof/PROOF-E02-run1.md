# E02 — Python Bundling (Run 1)

## Status: COMPLETED

## Files created
- `scripts/bundle-python.js` — Node.js script that:
  1. Creates `electron/bundle/` directory
  2. Runs `python3 -m venv` to create isolated environment
  3. Installs project + dependencies via pip
  4. Embeds FFmpeg/FFprobe via `static_ffmpeg.add_paths()`
  5. Copies `src/` and `pyproject.toml` to bundle
  6. Prunes `__pycache__`, `*.pyc`, `share/`, pip cache
  7. Verifies bundle with `python -m splitshot --check`

## Dependencies
- Depends on `E01` for `electron/` directory and `electron/package.json` (to verify build script integration)

## Verification
- Script references correct paths relative to `ROOT` (repo root)
- Handles platform differences (Windows vs Unix paths)
- Prunes all unnecessary artifacts
- Verification step validates the bundle is functional

## Risks
- Medium risk: `static_ffmpeg` must be importable after `pip install .`. If `static_ffmpeg` is not a dependency, the script will fail at step 4. Mitigation: the verification step catches this.
