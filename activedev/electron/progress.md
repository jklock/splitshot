# Electron Desktop App — Progress Ledger

## Task status board

| Task | Title | Status | Depends on | Proof |
| --- | --- | --- | --- | --- |
| `E01` | Electron shell | `pending` | none | — |
| `E02` | Python bundling | `pending` | `E01` | — |
| `E03` | Production build | `pending` | `E01`, `E02` | — |
| `E04` | CI and release | `pending` | `E03` | — |

## Log

| Date | Entry |
| --- | --- |
| `2026-05-04` | Created task pack. All tasks pending. |

## Done criteria (entire program)

- [ ] User downloads `.dmg`/`.exe`/`.AppImage` from GitHub Releases
- [ ] Installed app opens a native window with SplitShot running
- [ ] No terminal, no Python install, no browser tab required
- [ ] Import video, analyze, and export all work inside the app
- [ ] `.ssproj` files open on double-click
- [ ] Dev workflow unchanged: `uv run splitshot` still works
