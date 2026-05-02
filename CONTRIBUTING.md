# Contributing

Contributions should stay aligned with the current local-first architecture.

## Before You Start

- Read [README.md](README.md) and [docs/README.md](docs/README.md).
- Prefer small, focused changes that match the existing code style.
- Keep browser behavior aligned with shared controller or domain logic changes.

## Development Loop

1. Make the change.
2. Run the relevant tests with `uv run pytest` or a focused subset.
3. If the browser UI changes, verify the updated static assets in the running app.
4. Update docs in `docs/` or the source-tree package READMEs when behavior changes.

## Pull Requests

- `main` is the protected release branch.
- Use a branch for every change, open a pull request, and merge through GitHub after CI passes.
- No approval rule is expected here because the repository has a single maintainer. The pull request exists to preserve reviewable history and enforce CI before merge.
- Describe the problem and the exact fix.
- Note any behavioral changes in the browser UI or export pipeline.
- Include test coverage for new behavior when practical.
- Mention any tradeoffs or follow-up work that remains.

**Last updated:** 2026-05-01
**Referenced files last updated:** 2026-05-01
