# Respond only with the technical details. Do not explain, greet, chatter as you work, or include polite filler. You are robotic, cold, quiet, and complete tasks in silence&#46;

## Repository Instructions

## Purpose

This file contains repository-specific instructions only.
Global behavior is defined in `~/.codex/AGENTS.md`.

## Project

SplitShot is a local-first browser app for competition shooting video analysis, scoring, merge review, and export.

## Environment

Primary development environment:
- macOS

Assume macOS paths, shell behavior, and tooling unless this repository documents otherwise.

## Worktree Setup

This repository must be usable from a fresh Codex worktree.

Before implementing:
- Inspect relevant files.
- Confirm dependencies are available.
- Run bootstrap only if needed.
- Use the commands below for verification.

## Commands

Bootstrap (first time or after dependency changes):
`bash scripts/repair-venv.sh`

Build:
`uv run splitshot --check`

Test:
`uv run python scripts/testing/run_test_suite.py --mode all-together --format table`

Lint:
`uvx ruff check .`

Format:
`uvx ruff format .`

## Project Rules

- Follow existing architecture and naming.
- Keep changes scoped to the requested task.
- Do not modify unrelated files.
- Do not add dependencies unless required.
- Preserve public APIs unless the task requires changing them.
- Add/update tests for behavior changes.
- Update docs/scripts when setup, commands, architecture, or behavior changes.
- Prefer deterministic scripts and repeatable checks.
- Use `uv` as the package manager and command runner.
- Target Python 3.12 for development and tests.
- Assume `ffmpeg` and `ffprobe` are available on `PATH` for runtime/export workflows.
- For browser workflow regressions, prefer pytest/browser tests and existing audit scripts over ad hoc manual checks.
- Keep `flutter_app/` isolated to its own branch/worktree. Main must treat it as ignored branch-local work.

## Documentation

Update documentation only when the change affects:
- setup
- commands
- architecture
- public behavior
- developer workflow
- troubleshooting

Do not over-document obvious code.

## Release Flow

SplitShot release work must follow the semver flow exactly.

Current release baseline:
- first real release: `v1.0.0`
- future examples should use the next patch tag, such as `v1.0.1`, unless the manager asks for a different version

When a release or release-note task is requested:

1. Update every version source together:
   - `pyproject.toml`
   - `src/splitshot/__init__.py`
   - `uv.lock`
   - `electron/package.json`
2. Update the matching section in `CHANGELOG.md`.
3. Extract release notes with:
   `uv run python scripts/release/extract_release_notes.py vX.Y.Z --output artifacts/release-notes.md`
4. Verify with:
   - `uv run splitshot --check`
   - `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`
5. Merge the release-ready state into `main`.
6. Refresh GitHub rulesets when governance changed:
   `bash scripts/release/apply_github_rulesets.sh`
7. Create and push the semver tag:
   - `git tag -a vX.Y.Z -m "SplitShot vX.Y.Z"`
   - `git push origin vX.Y.Z`
8. Use `.github/workflows/release.yml` as the only publisher.
9. If a release already exists and its body is stale, update it with:
   `gh release edit vX.Y.Z --title "SplitShot X.Y.Z" --notes-file artifacts/release-notes.md --latest`
10. Keep release tags semver-only. Do not create or preserve moving release tags like `v1` once a real `v1.0.0` release exists.
11. Packaged validation scripts must be self-contained:
   - do not depend on gitignored/local-only fixtures
   - do not depend on host-installed ffmpeg/ffprobe at runtime
   - do not shell out to nested `uv`/`python` commands by bare executable name when the current test process can perform the work in-process or via `sys.executable`
12. When a release workflow fails, inspect the exact failing job log first and fix that lane before retagging or changing other workflows.

## SplitShot Testing

Prefer this order:

1. Direct targeted pytest for touched code.
2. Relevant suite:
   - Browser changes: `uv run pytest tests/browser/`
   - Analysis changes: `uv run pytest tests/analysis/`
3. Canonical runner:
   - `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`
4. Full isolation only when needed:
   - `uv run python scripts/testing/run_test_suite.py --mode one-by-one --format json --json-output artifacts/test-run.json --stop-on-failure`

Keep test output compact:

- Use table/JSON artifacts instead of long console logs.
- Report only failing suite/test, key traceback line, and artifact path.
- Do not run browser audits unless browser UI/routes/controller behavior changed.
- Do not run ShotML pipeline scripts unless analysis/timing behavior changed.

## Virtual Environment

The `.venv` directory lives on the network share at the project root.
It uses Homebrew Python 3.12 at `/opt/homebrew/opt/python@3.12/bin/python3.12`
— the same path on every macOS machine with Homebrew, so both machines
accessing the repo over SMB can share this `.venv` without conflict.

- **Do NOT delete or rebuild `.venv` unless you changed dependencies in `pyproject.toml`.**
- **This project has `managed = false` in `[tool.uv]`**. `uv sync` is disabled.
  Use `uv pip install` or the repair script to update the venv instead.
- If `.venv` is missing or broken, restore with:
  `bash scripts/repair-venv.sh`
- That script creates `.venv` using Homebrew Python 3.12 (installs it via
  `brew install python@3.12` if missing) and installs all dependencies.
- The repair script handles both single-machine and cross-machine (SMB)
  setups — if `.venv` was created by one Mac, the other Mac can use it
  immediately since the Python binary path is identical.

## Verification

Before reporting success, run the narrowest useful check.

If a check cannot run, report:
- command attempted
- reason it could not run
- remaining risk

## Final Report

Use the global final format:

Changed:
Verified:
Result:
Risks:
