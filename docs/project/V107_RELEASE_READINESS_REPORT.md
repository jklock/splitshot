# v1.0.7 Release-Readiness Report

<!-- Reported: 2026-09-25 -->

## Status

**BLOCKED (fail-closed).** The candidate must not be merged, tagged, published, released, or sent to the `Release` workflow.

- Candidate evaluated before this report: `2cd933cef0d2051bb1247cbd3932a0f73a8c73a3`
- Branch state at block: `v107...origin/v107` (synchronized)
- Release action: none taken
- Test or Build workflow dispatches: none; local package/runtime gate did not pass

## Repository reconciliation

`codex/v107-release-prep` was reconciled into `v107` and pushed. Its commits are `f58e6c0` (release-readiness documentation and a scoring-workbench persistence wait) and `2cd933c` (formal release-preparation plan). This report is committed on top of that reconciliation. `codex/v107-formal-release-plan` and `codex/v107-release-prep` are clean and duplicate the merged candidate, so they are eligible for removal once workspace cleanup resumes.

`codex/v107-release-prep-execution` remains required for preservation: its worktree contains uncommitted documentation screenshots, browser/Electron/package scripts, static UI files, and tests. It was neither removed nor committed because its provenance and intended scope were not established by this release request. Consequently, the requested state of only local `main` and `v107` branches has not been reached.

## Commands and results

| Command | Result |
| --- | --- |
| `uv run pytest tests/browser/test_browser_interactions.py -k scoring_workbench_rows_lock_edit_delete_and_restore --basetemp=tmp/codex/pytest -q` | PASS: 1 passed, 44 deselected (8.43s) |
| `git diff --check` for reconciled changes | PASS |
| `git merge --ff-only codex/v107-release-prep` | PASS |
| `git push origin v107` | PASS; `origin/v107` equals the final SHA |
| `uv sync --frozen --extra dev --python 3.12` | Provisioning completed sufficiently to create the locked `.venv`; command output was interrupted by the runtime-gate investigation, so it is not release proof |
| `npm --prefix electron ci` | PASS: 288 packages installed; npm reported 13 high-severity dependency-audit findings |
| `uv run splitshot --check` (through `run_electron_preflight.py`) | BLOCKED: hung while importing PySide6/QtWebEngine before runtime-check output; terminated after diagnostic capture |

## Blocking evidence

The sampled `splitshot --check` process was inside `PySide6`/`shiboken6` lazy import and macOS dynamic-loader file operations while loading QtWebEngine. The sample is retained at `tmp/codex/preflight-hang-sample.txt` (ignored). The process produced no successful runtime-check result. A signed macOS app, local package-native E2E, source suite, corpus/manifest/runtime evidence, output-video review, and all remote Test/Build runs remain unexecuted by policy.

## Workflow and artifact evidence

No GitHub Actions runs were created. Therefore there are no workflow URLs, run IDs, platform artifacts, artifact hashes, evidence paths, or screenshot/video-review findings. Fabricating or mixing prior evidence would violate the exact-SHA requirement.

## Remaining risks

1. The QtWebEngine import hang blocks all macOS runtime/package validation.
2. The uncommitted execution worktree prevents safe deletion of its worktree and branch.
3. `npm ci` reports 13 high-severity audit findings; this is untriaged and must be assessed before release acceptance.
