# B08 — Testing (parity, e2e, installer verify)

## Status: Complete

## Remediation note

The earlier proof overstated parity/e2e completion. This revision only claims
coverage that now exists in code and CI.

## Changes

- `scripts/audits/electron_parity_audit.py`
  - Starts both backends:
    - native `uv run splitshot --headless --no-open`
    - bundled `python -m splitshot --headless --no-open`
  - Compares stable contract responses for:
    - `GET /api/state`
    - `GET /api/practiscore/session/status`
    - `POST /api/project/new`
    - `POST /api/activity`
    - `/`, `/static/app.js`, `/static/styles.css`
- `electron/tests/launch-intent.test.js`
  - Covers argv parsing, protocol parsing, path normalization, and intent queueing
- `electron/tests/smoke.test.js`
  - Launches the Electron app from source with Playwright Electron support
  - Verifies preload bridge availability
  - Verifies startup project open
  - Verifies simulated second-instance open
  - Verifies protocol URL delivery
- `tests/electron/test_headless_server.py`
  - Keeps headless backend/server checks as a separate Python suite
- `.github/workflows/build-electron.yml`
  - Runs launch-intent unit tests
  - Runs `tests/electron/test_headless_server.py`
  - Runs the parity audit
  - Runs Electron source smoke tests before packaging
  - Verifies Linux AppImage desktop metadata after build

## Verification

```bash
npm --prefix electron run test:launch-intent
npm --prefix electron run test:electron-smoke
uv run pytest tests/electron/test_headless_server.py --no-header -q
uv run python scripts/audits/electron_parity_audit.py --mode parity
```

## Scope note

- This proof now covers bundled parity and Electron shell behavior from source.
- Installed-artifact proof belongs to the refreshed workflow/build evidence, not
  to this test file alone.
