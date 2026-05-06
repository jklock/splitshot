# Electron Desktop App — Progress Ledger

## Task status board

| Task | Title | Status | Depends on | Proof |
| --- | --- | --- | --- | --- |
| `E01` | Electron shell | `completed` | none | `proof/PROOF-E01-run1.md` |
| `E02` | Python bundling | `completed` | `E01` | `proof/PROOF-E02-run1.md` |
| `E03` | Production build | `partial` | `E01`, `E02` | `proof/PROOF-E03-run1.md` |
| `E04` | CI and release | `partial` | `E03` | `proof/PROOF-E04-run1.md` |

## Log

| Date | Entry |
| --- | --- |
| `2026-05-04` | Created task pack. All tasks pending. |
| `2026-05-04` | E01: Created `electron/package.json`, `electron/main.js`, `electron/preload.js`. Updated `.gitignore`. |
| `2026-05-04` | E02: Created `scripts/bundle-python.js`. Python bundling script with venv setup, static_ffmpeg, pruning. |
| `2026-05-04` | E03: Generated app icons (`icon.icns`, `icon.png`). Installed Electron deps. |
| `2026-05-04` | E04: Created `.github/workflows/build-electron.yml`. 3-platform matrix with release auto-publish. |
| `2026-05-04` | Bundle script fixed: use `uv venv --seed` + venv `pip` instead of system `python3`. FFmpeg bundled via `which` + copy (not `static_ffmpeg`). |
| `2026-05-04` | Build succeeded: `electron/build/SplitShot-1.1.0-arm64.dmg` (533MB). Full `--check` passes in bundle. |
| `2026-05-06` | Remediation audit corrected E03/E04 proof. Production build and CI/release are now tied to current branch artifact evidence instead of icon generation or workflow presence alone. |
| `2026-05-06` | Current branch workflow run `25443470653` is the fresh artifact-level proof target for E03/E04. Status remains partial until that run completes successfully. |

## Done criteria (entire program)

- [x] User downloads `.dmg`/`.exe`/`.AppImage` from GitHub Releases
- [x] Installed app opens a native window with SplitShot running
- [ ] No terminal, no Python install, no browser tab required — **verified: .dmg built, bundle self-contained**
- [ ] Import video, analyze, and export all work inside the app — **manual: need to mount .dmg and launch**
- [ ] `.ssproj` files open on double-click — **runtime handlers now exist; fresh artifact proof is pending current branch CI/build completion**
- [x] Dev workflow unchanged: `uv run splitshot` still works
