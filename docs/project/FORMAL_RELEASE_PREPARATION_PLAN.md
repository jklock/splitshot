# Formal Release Preparation Plan

<!-- Documentation reviewed: 2026-09-24 -->

## Objective

Prepare one clean, immutable v1.0.7 candidate for a formal release later this week. This plan does **not** authorize a tag, GitHub Release, publishing, or the `Release` workflow. A candidate advances only when every listed local and GitHub Actions gate passes for the same commit.

## Candidate and repository hygiene

1. Start from a clean worktree and record its full commit SHA, branch, version sources, release-corpus revision, and scenario-manifest SHA in `artifacts/v107-release-proof/release-readiness.json`.
2. Compare every version source (`pyproject.toml`, `src/splitshot/__init__.py`, `uv.lock`, `electron/package.json`, and `electron/package-lock.json`) with `CHANGELOG.md`; v1.0.7 values must agree.
3. Review all tracked Markdown, shell, Python, JavaScript, Electron, workflow, manifest, and release-data changes since the prior validated baseline. Resolve stale release claims, broken links, untracked generated output, ignored-file gaps, and unsupported local dependencies.
4. Run `git diff --check`, `git status --ignored --short`, `git check-ignore` for generated test/package paths, and the tracked-tree hygiene checks. Preserve user media and projects; remove only reproducible caches, artifacts, build output, test profiles, logs, and downloaded CI bundles.
5. Rebuild the user documentation screenshot set from two approved real videos outside `tests/`; visually review every image for current controls, decoded footage, privacy, and useful feature coverage before committing replacements.

## Local source and package gates

Run each gate from the candidate worktree with `TMPDIR`, `TMP`, and `TEMP` under `tmp/codex/`; retain compact JSON/log output under ignored `artifacts/v107-release-proof/`.

1. Install locked Python and Electron dependencies: `uv sync --frozen --extra dev --python 3.12` and `npm --prefix electron ci`.
2. Run `uv run splitshot --check`, `uvx ruff check .`, release-corpus validation, manifest validation, and the documentation/control-inventory guards.
3. Run the canonical source suite once after all source changes: `uv run python scripts/testing/run_test_suite.py --mode all-together --format table --json-output artifacts/v107-release-proof/source/test-suite.json`. Treat failures and unexpected skips as blockers; isolate a failing test before rerunning its owning suite.
4. Run `uv run python scripts/testing/run_source_release_proof.py --artifact-root artifacts/v107-release-proof/source` and inspect the evidence report.
5. On macOS, run `uv run python scripts/testing/run_electron_preflight.py`, then build a fresh signed local DMG. On Windows/Linux, use the matching hosted workflow for native packaging; do not treat cross-compiled artifacts as platform proof.
6. Execute the local macOS package-native E2E against the committed `primary.MP4`, `secondary.MP4`, and `practiscore.csv`; inspect package identity, real-media outputs, OCR/frame/media metadata, persistence/reopen/restart, screenshots, action/request ledgers, and the fail-closed summary. A local unsigned or non-notarized build is local evidence only.

## GitHub Actions test runs

Push only the final clean candidate SHA to its review branch. Dispatch and inspect every workflow below on that exact SHA; do not mix platform evidence from different commits.

| Workflow | Required exercise | Required evidence |
| --- | --- | --- |
| `Test macOS` | source suite, signed/notarized DMG, installed-package E2E | package, `e2e-artifacts-macos`, codesign/Gatekeeper/stapler proof, zero-gap `platform-summary.json` |
| `Test Windows` | source suite, NSIS installation, installed-package E2E | package, `e2e-artifacts-windows`, real rendered outputs, zero-gap summary |
| `Test Linux` | source suite, AppImage launch, installed-package E2E | package, `e2e-artifacts-linux`, real rendered outputs, zero-gap summary |
| `Build macOS` | packaging-helper contract only | build artifact and package log; never substitute for Test macOS |
| `Build Windows` | packaging-helper contract only | build artifact and package log; never substitute for Test Windows |
| `Build Linux` | packaging-helper contract only | build artifact and package log; never substitute for Test Linux |
| `Release` | inspect inputs and validation contract only; **do not dispatch** | confirm it aggregates exact-commit summaries and is the sole publisher |

For every completed Test workflow, download and review its artifacts. Require matching source commit, package hash, corpus revision, and manifest SHA; all case/identity counts must satisfy `discovered == mapped == exercised == passed`, with `failed == skipped == gaps == 0`. Review `full-feature-validation.mp4` and its JSON timeline, ensuring individual and combined rendered outputs are the final two sections.

## Failure and readiness policy

1. Inspect the exact failed job log and uploaded bundle before changing code, fixtures, tests, or workflows.
2. Fix the narrow root cause, add a focused regression where behavior changed, rerun local source/package gates, then rerun only the affected workflow.
3. Once each platform independently passes, dispatch all three Test workflows again on the final identical SHA and perform one final evidence review.
4. Produce `artifacts/v107-release-proof/release-readiness.md` with candidate SHA, commands, run URLs, artifact hashes, documentation/screenshot review, and known risks.
5. Only after explicit approval later this week may the candidate merge to `main`, receive the annotated `v1.0.7` tag, and enter the `Release` workflow. No release action is part of this plan.
