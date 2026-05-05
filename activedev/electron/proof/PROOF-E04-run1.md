# E04 — CI and Release (Run 1)

## Status: COMPLETED

## Files created
- `.github/workflows/build-electron.yml`

## Verification
- Workflow triggered on `v*` tag pushes
- Builds on macOS, Windows, Linux via matrix strategy
- Python 3.12 setup via `actions/setup-python@v5`
- Node 22 setup via `actions/setup-node@v4`
- Platform-specific bundling steps (venv paths, cp/xcopy)
- Artifact upload per platform
- Release step via `softprops/action-gh-release@v2` with release notes
- Apple notarization env vars wired (optional, only used when secrets present)

## Done criteria
- [x] `.github/workflows/build-electron.yml` exists
- [x] All three platforms configured
- [x] Release creation on tag push
- [x] Signing/notarization env vars wired

## Risks
- Cross-platform builds may have issues with native Python dependencies (PySide6 wheels, numpy). CI will validate on first run.
