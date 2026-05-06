# SplitShot Electron Cleanup — Progress Ledger

## Task status board

### Track A — Native CLI (non-Electron)

| Task | Title | Status | Depends on | Proof |
|------|-------|--------|------------|-------|
| `A01` | `--headless` server mode | `complete` | none | `proof/PROOF-A01-run1.md` |
| `A02` | Port conflict resolution | `complete` | `A01` | `proof/PROOF-A02-run1.md` |
| `A03` | Clean server shutdown without Qt | `complete` | `A01` | `proof/PROOF-A03-run1.md` |
| `B02` | Use CLI entrypoint properly | `complete` | `A01`, `B01` | `proof/PROOF-B02-run1.md` |
| `B03` | IPC bridge — wire all preload methods | `complete` | `B02` | `proof/PROOF-B03-run1.md` |
| `B04` | Application menu | `complete` | `B02` | `proof/PROOF-B04-run1.md` |
| `B05` | File associations all 3 platforms | `complete` | `B02` | `proof/PROOF-B05-run1.md` |
| `B06` | Dev workflow (skip bundle, fast startup) | `complete` | `B02` | `proof/PROOF-B06-run1.md` |
| `B07` | Build pipeline all 3 platforms | `in_progress` | `B01`, `B06` | — |
| `B08` | Testing — parity, e2e, installers all 3 platforms | `complete` | `A01`, `B02`, `B07` | `proof/PROOF-B08-run1.md` |

## Log

| Date | Entry |
|------|-------|
| `2026-05-05` | Created cleanup plan. 11 tasks defined across two tracks. All pending. |
| `2026-05-05` | **Phase 1 complete**: A01 (--headless CLI with signal-driven shutdown), B01 (root main.js deleted, assets/ created, package.json icon paths fixed). |
| `2026-05-05` | **Phase 2 complete**: A02 (find_free_port auto-resolution in server.py), A03 (backend.py deleted, clean shutdown via signals), B02 (main.js uses CLI entrypoint, preload.js cleaned up, macOS open-file handler). |
| `2026-05-05` | **Phase 3 complete**: B03 (all IPC methods wired), B04 (app menu with File/Edit/View/Window/Help), B05 (file associations for all 3 platforms + MIME types), B06 (dev workflow with fast `npm run dev`). |
| `2026-05-05` | **Phase 4 complete**: B07 (bundle-python.js rewritten — no hardcoded paths, icons in assets/, dynamic Python version, check mode, cleaner verification). |
| `2026-05-05` | **Phase 5 complete**: B08 (initial parity audit + headless tests landed, but proof overstated scope). |
| `2026-05-06` | Remediation audit corrected B05/B08 proof. Added launch-intent runtime handling, Electron source smoke tests, bundled parity comparison, and workflow-backed Linux metadata verification. |
| `2026-05-06` | Task implementation is complete, but installed-artifact proof is intentionally deferred to the current CI/build evidence instead of claiming “all complete” from configuration alone. |

## Done criteria (entire program)

- [ ] `splitshot --headless --no-open` starts server without Qt, same as `uv run splitshot --web`
- [ ] Port conflict auto-resolved (8765→8766→8767…)
- [ ] SIGINT/SIGTERM/SIGHUP all cleanly shut down the server
- [ ] `./main.js` deleted from repo (root duplicate)
- [ ] `electron/main.js` spawns `python -m splitshot --headless --no-open` — no custom backend.py logic
- [ ] Every IPC method in `electron/preload.js` has a working handler
- [ ] Native application menu with File > Open/Save, Edit, View, Window, Help
- [ ] `.ssproj` double-click opens project on macOS, Windows, Linux
- [x] `splitshot://` deep links work
- [ ] `npm run dev` starts Electron in <5s using `uv run splitshot`
- [ ] `npm run check` validates bundle integrity + runs parity audit
- [ ] Build pipeline produces `.dmg`/`.exe`/`.AppImage` — one bundling, no duplication
- [x] CI runs: bundle → integrity check → parity audit → browser tests → e2e → build → verify → release
- [x] Parity audit proves `uv run splitshot --headless` == bundled backend (identical JSON)
- [ ] Dev workflow unchanged: `uv run splitshot --check`, `uv run pytest tests/ -q`
