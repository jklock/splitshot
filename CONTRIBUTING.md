# Contributing

Contributions should preserve SplitShot's local-first workflow, shared controller model, and evidence-backed test discipline.

The v1.0.7 release line is feature-frozen. Changes targeting it should correct defects, tests, packaging, or documentation without expanding the product surface.

## Start Here

Read these before changing code:

1. [README.md](README.md)
2. [docs/project/DEVELOPING.md](docs/project/DEVELOPING.md)
3. [docs/project/ARCHITECTURE.md](docs/project/ARCHITECTURE.md)
4. [docs/tests/TEST_SUITE_GUIDE.md](docs/tests/TEST_SUITE_GUIDE.md)
5. [scripts/README.md](scripts/README.md)

## Workflow

1. Make a focused change.
2. Run the narrowest useful validation first.
3. Expand to the owning suite if behavior changed.
4. Update docs when setup, commands, architecture, behavior, or troubleshooting changed.
5. Open a pull request from a short-lived branch after the relevant checks pass.
6. Delete the branch after merge unless it still carries active work.

## Required Checks

Use Python 3.12 with `uv`, Node.js 22 with `npm ci`, and make sure `ffmpeg` and `ffprobe` are on `PATH` for source media/export checks.

- Browser-visible route or static-shell changes:
  run the narrow browser/static tests that own the surface.
- Analysis changes:
  run the directly affected analysis or script tests first.
- Export or media changes:
  run the owning export/media tests first.
- When in doubt:
  use `uv run python scripts/testing/run_test_suite.py --list` and pick the smallest owning suite.

Common commands:

```bash
uv run splitshot --check
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
uvx ruff check .
```

## Review Expectations

- Keep diffs scoped.
- Prefer existing patterns over new abstractions unless the current design is the problem.
- Add or update tests when behavior changes.
- Do not claim success without a command or a concrete blocker.
- Keep docs and scripts aligned with the new behavior in the same change.

## Pull Requests

- Use a branch for every change.
- Treat `main` as PR-first. Maintainer bypass exists for hotfixes and release recovery, not as the default workflow.
- Describe the problem, exact fix, verification, and residual risks.
- Call out browser UI, project-model, analysis, export, or release-flow changes explicitly.
- Note follow-up work instead of hiding it in commit history.

## Read This Next

- [docs/project/DEVELOPING.md](docs/project/DEVELOPING.md)
- [docs/tests/TEST_SUITE_GUIDE.md](docs/tests/TEST_SUITE_GUIDE.md)
- [scripts/README.md](scripts/README.md)
- [docs/project/GOVERNANCE.md](docs/project/GOVERNANCE.md)
