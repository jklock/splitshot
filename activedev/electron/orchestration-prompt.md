# SplitShot Electron — Orchestration Prompt

## Mission

Package SplitShot as a native desktop Electron application so non-technical users can download, install, and run it without touching a terminal, installing Python, or running `uv`.

## Context

The user base is non-technical competition shooters. The existing app requires:
1. Install Python 3.12
2. Install `uv`
3. Run `uv sync --extra dev`
4. Run `uv run splitshot`

This is a non-starter for the target audience. The Electron wrapper must eliminate every one of those steps. The user downloads a `.dmg`, drags to Applications, double-clicks, and SplitShot opens in a native window.

## Architecture

```
User downloads SplitShot.dmg
        │
        ▼
  Double-click → SplitShot.app opens
        │
        ├── Electron BrowserWindow appears
        ├── Spawns bundled python as child process (port 8765)
        ├── Loads http://127.0.0.1:8765 in the window
        ├── User imports video, analyzes, exports
        └── Close window → kills python process
```

The Python backend (`server.py`, `controller.py`, `pipeline.py`, etc.) is bundled inside the `.app` as a self-contained Python virtual environment. No existing Python or JS code changes.

## Files that already exist

| File | Purpose |
| --- | --- |
| `activedev/electron/plan.md` | Full end-to-end architecture plan |
| `activedev/electron/progress.md` | Task status ledger |
| `activedev/electron/tasks/E01-electron-shell.md` | Electron main process + window |
| `activedev/electron/tasks/E02-python-bundling.md` | Python bundle script |
| `activedev/electron/tasks/E03-production-build.md` | Installer build + icons |
| `activedev/electron/tasks/E04-ci-and-release.md` | GitHub Actions + release |

## Execution order

```text
E01 ──┐
      ├──> E03 ──> E04
E02 ──┘
```

- **E01** and **E02** are independent and can run in **parallel**.
- **E03** depends on both E01 and E02 completing.
- **E04** depends on E03.

## Task ownership

| Task | Owner | Touches |
| --- | --- | --- |
| `E01` | `subagent-e01` | `electron/main.js`, `electron/preload.js`, `electron/package.json`, `.gitignore` |
| `E02` | `subagent-e02` | `scripts/bundle-python.js`, `.gitignore` |
| `E03` | `subagent-e03` | `electron/build/`, app icons, `electron/package.json` (build config) |
| `E04` | `subagent-e04` | `.github/workflows/build-electron.yml` |

## File access rules

- No subagent may modify any file under `src/`, `pyproject.toml`, or `tests/`.
- No subagent may modify files outside its `touches` list.
- The order agent (`E03`, `E04`) must wait for all dependencies to complete before starting.

## Validation

After all tasks complete, run:

```bash
npm --prefix electron install
npm --prefix electron run build:mac
ls electron/build/SplitShot.dmg

# Dev workflow still works
uv run splitshot --check
uv run pytest tests/ -q
```

## Progress tracking

Each subagent must update `activedev/electron/progress.md` when it starts and finishes a task.

## Handoff

After E04 completes, the Electron program is ready. Next steps:
- Distribute the `.dmg` to beta testers
- Set up Apple Developer account for notarization
- Set up `splitshot.studio` landing page with download link
