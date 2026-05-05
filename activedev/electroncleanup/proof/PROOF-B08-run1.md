# B08 — Testing (parity, e2e, installer verify)

## Status: Complete

## Changes

- `scripts/audits/electron_parity_audit.py`: Complete rewrite
  - Uses `uv run splitshot --headless --no-open` instead of deprecated `backend.py`
  - Supports `--mode dev` (direct) and `--mode bundled` (via bundle venv)
  - Tests Function, Quality, Speed, and Browser test suite

- `tests/electron/`: Created new test directory
  - `__init__.py`: Package marker
  - `test_headless_server.py`: Tests for:
    - Server starts and serves API state
    - Static assets served correctly
    - Port conflict resolution
    - `--check` flag validation

- `.github/workflows/build-electron.yml`: Already updated in B07 with parity audit step

## Verification

```bash
uv run pytest tests/electron/ -q -x --timeout=60
uv run python scripts/audits/electron_parity_audit.py --mode parity
```
