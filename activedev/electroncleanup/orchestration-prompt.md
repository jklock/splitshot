# SplitShot Electron Cleanup — Orchestration Prompt

## Mission

Fix the Electron integration so there is **zero perceptible difference**
between `uv run splitshot` and the Electron `.app`/`.exe`/`.AppImage`.

The Electron wrapper must be nothing more than `native CLI + packaging`.
Identical function, identical quality, identical speed, identical
testability — on macOS, Windows, and Linux.

## Context

The Electron integration was built quickly and cut corners:

1. Custom `backend.py` duplicates CLI startup logic — any CLI change
   causes silent drift.
2. Preload exposes IPC methods with no handlers — dead/broken code.
3. No app menu, no file associations, no macOS event handling.
4. Bundle script hardcodes Python 3.12 paths, uses `which ffmpeg`,
   and does fragile uv-symlink resolution.
5. CI duplicates bundling logic inline and runs it twice per platform.
6. No Linux-specific treatment — icons, MIME types, system deps, testing.
7. No testing of the actual Electron app — parity audit tests
   `backend.py` directly.

This cleanup fixes all of that.

## Architecture

```
Track A: Native CLI (non-Electron)     Track B: Electron Packaging
  ┌─────────────┐                        ┌─────────────┐
  │ A01: --     │                        │ B01: Cleanup │
  │ headless    │                        │ root + assets│
  └──────┬──────┘                        └──────┬──────┘
         │                                      │
  ┌──────▼──────┐                               │
  │ A02: Port   │                        ┌──────▼──────┐
  │ conflict    │                        │ B02: Use CLI│
  │ resolution  │                        │ entrypoint  │
  └──────┬──────┘                        └──────┬──────┘
         │                                      │
  ┌──────▼──────┐                ┌──────┬───────┼──────┬──────┐
  │ A03: Clean  │                │      │       │      │      │
  │ shutdown    │           ┌────▼┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐  │
  └─────────────┘           │ B03 │ │ B04 │ │ B05 │ │ B06 │  │
                            │ IPC │ │Menu │ │File │ │ Dev │  │
                            └─────┘ └─────┘ └─────┘ └──┬──┘  │
                                                        │     │
                                                  ┌────▼──┐  │
                                                  │ B07   │  │
                                                  │ Build │  │
                                                  └───┬───┘  │
                                                      │     │
                                                  ┌───▼───┐ │
                                                  │ B08   │◄┘
                                                  │Tests  │
                                                  └───────┘
```

- **A01** blocks **B02** (B02 rewrites main.js to use `--headless`)
- **A01** and **A02** are additive (port resolution added to headless mode)
- **A03** replaces backend.py, depends on A01 existing
- **B01** has no deps, can run first or in parallel with A01
- **B03/B04/B05/B06** are parallel after B02
- **B06 → B07** (dev workflow fixes → build pipeline)
- **B08** is last, needs A01 + B02 + B07
- **B03/B04/B05** independent of each other

## Task ownership

| Task | Owner | Touches |
|------|-------|---------|
| `A01` | `subagent-a01` | `src/splitshot/cli.py` |
| `A02` | `subagent-a02` | `src/splitshot/cli.py`, `src/splitshot/browser/server.py` |
| `A03` | `subagent-a03` | `src/splitshot/cli.py`, `electron/backend.py` |
| `B01` | `subagent-b01` | `./main.js`, `electron/build/`, `electron/assets/`, `.gitignore`, `electron/package.json` |
| `B02` | `subagent-b02` | `electron/main.js`, `electron/backend.py`, `electron/preload.js` |
| `B03` | `subagent-b03` | `electron/main.js`, `electron/preload.js` |
| `B04` | `subagent-b04` | `electron/main.js` |
| `B05` | `subagent-b05` | `electron/main.js`, `electron/package.json` |
| `B06` | `subagent-b06` | `electron/package.json`, `electron/main.js` |
| `B07` | `subagent-b07` | `scripts/bundle-python.js`, `.github/workflows/build-electron.yml`, `electron/package.json`, `electron/assets/` |
| `B08` | `subagent-b08` | `scripts/audits/electron_parity_audit.py`, `tests/electron/`, `.github/workflows/build-electron.yml`, `electron/package.json` |

## File access rules

- **Track A subagents** may only modify files in `src/splitshot/` and
  `electron/backend.py`. Never touch `electron/main.js`, `electron/package.json`,
  `.github/`, or `scripts/`.
- **Track B subagents** may only modify files in `electron/`, `scripts/`,
  `.github/`, `tests/`, and `./main.js` (delete). Never touch anything
  under `src/` or `pyproject.toml`.
- No subagent may modify files outside its `touches` list.
- `B02` must wait for `A01` to complete before starting.
- `B07` must wait for `B06` (and `B01`) before starting.
- `B08` must wait for `A01`, `B02`, and `B07`.

## Execution order

```
Phase 1 (parallel):
  A01 ── headless CLI mode
  B01 ── root cleanup + asset reorganization

Phase 2 (after A01 + B01):
  A02 ── port conflict resolution (after A01)
  A03 ── clean shutdown (after A01)
  B02 ── CLI entrypoint (after A01 + B01)

Phase 3 (after B02):
  B03 ── IPC bridge
  B04 ── Application menu
  B05 ── File associations
  B06 ── Dev workflow

Phase 4 (after B01 + B06):
  B07 ── Build pipeline (all 3 platforms)

Phase 5 (after A01 + B02 + B07):
  B08 ── Testing (parity, e2e, installer verify)
```

## Validation

After all tasks complete, run:

```bash
# Track A — Native CLI
uv run splitshot --check
uv run splitshot --headless --no-open
uv run pytest tests/ -q

# Track B — macOS
npm --prefix electron run bundle
npm --prefix electron run check
npm --prefix electron run build:mac
ls electron/build/*.dmg

# Track B — Windows
npm --prefix electron run bundle
npm --prefix electron run build:win
ls electron/build/*.exe

# Track B — Linux
npm --prefix electron run bundle
npm --prefix electron run build:linux
ls electron/build/*.AppImage

# Track B — Dev
npm --prefix electron run dev

# Parity audit
uv run python scripts/audits/electron_parity_audit.py --mode parity

# Regression
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
uvx ruff check .
```

## Progress tracking

Each subagent must update `activedev/electroncleanup/progress.md` when it
starts and finishes a task. Proof files go in `activedev/electroncleanup/proof/`
following the `PROOF-{TASK_ID}-run{N}.md` naming convention.

## Handoff

After all 11 tasks complete:

1. The `uv run splitshot` path is unchanged and works identically
2. `splitshot --headless --no-open` provides a Qt-free server for Electron
3. `npm run dev` gives fast Electron development without bundling
4. `npm run bundle && npm run build:{mac,win,linux}` produces installers
5. CI builds all three platforms on tag pushes with full test pipeline
6. The parity audit proves native == bundled at every API endpoint

Next steps after cleanup:
- Set up Apple Developer account for notarization
- Set up Code signing for Windows (EV cert)
- Set up `splitshot.studio` landing page with download links
- Consider auto-update via `electron-updater`
