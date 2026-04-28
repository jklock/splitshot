# Repository Instructions

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

Bootstrap:
`uv sync --extra dev`

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

## Documentation

Update documentation only when the change affects:
- setup
- commands
- architecture
- public behavior
- developer workflow
- troubleshooting

Do not over-document obvious code.

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