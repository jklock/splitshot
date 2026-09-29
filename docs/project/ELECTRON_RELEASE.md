# Electron Packaging and Release Validation

This runbook describes the durable packaging and validation path for SplitShot on macOS, Windows, and Linux. It does not replace the repository release policy in [GOVERNANCE.md](GOVERNANCE.md).

## Prerequisites

- Python 3.12 with `uv`
- Node.js 22 with `npm`
- `ffmpeg` and `ffprobe` on `PATH` for source checks
- Platform signing credentials when producing a signed distribution

Install the locked dependencies:

```bash
uv sync --frozen --extra dev --python 3.12
npm --prefix electron ci
```

## Local Validation

Run the runtime check and the smallest relevant suite first. Before a release review, run the canonical suite and validate the committed release corpus:

```bash
uv run splitshot --check
uv run python scripts/testing/validate_release_data.py
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
```

Build on the matching platform:

```bash
npm --prefix electron run build:mac
npm --prefix electron run build:win
npm --prefix electron run build:linux
```

The tracked `tests/release_data/` corpus is intentional. It makes package validation self-contained and must remain byte-stable unless its manifest is updated in the same change.

## Cross-Platform Test Review

Dispatch **Test macOS**, **Test Windows**, and **Test Linux** only after the reviewed commit is pushed. Each workflow runs the source suite, builds the native package, validates an installed package with the committed corpus, and uploads its package plus E2E evidence.

Review each workflow's package and `e2e-artifacts-*` upload. Require one commit identity across all runs, no failed, skipped, or unmapped validation cases, and inspect the full-feature recording plus individual and combined rendered outputs. Build-only workflows are packaging helpers and do not replace these test workflows.

## Publishing

Follow [GOVERNANCE.md](GOVERNANCE.md) for the version update, changelog, merge, tag, and release steps. `.github/workflows/release.yml` is the only publishing workflow. Do not create a release from a package build or from mixed-platform evidence.
