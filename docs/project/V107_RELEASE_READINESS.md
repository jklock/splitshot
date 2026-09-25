# v1.0.7 Release Readiness

<!-- Documentation reviewed: 2026-09-18 -->

This is the release-preparation checklist for the feature-frozen v1.0.7 line. It does not authorize tagging, publication, or a GitHub Release. A green package build, a source-only test run, or a screenshot set is not a release pass.

## Candidate identity and cleanup

- Candidate branch: `codex/v107-release-prep` from `v107` commit `52d17a5d8308c18d452bfc3616f945882063402a`; record the final commit again after documentation or defect fixes.
- Generated artifacts belong in ignored locations: `tmp/codex/`, `artifacts/`, `electron/build/`, `electron/bundle/`, `electron/node_modules/`, test results, caches, and logs.
- Preserve user projects and real recordings. Before deleting ignored state, inspect with `git clean -ndX`; use `git check-ignore -v` to prove each generated path is ignored. Never use a blanket cleanup that can remove local configuration, user media, or project folders.
- The tracked release corpus is the exception: `tests/release_data/primary.MP4`, `secondary.MP4`, and `practiscore.csv` remain versioned and checksum-validated.

## Documentation and control reference

The control contract is deliberately split so that users get behavior-oriented instructions while maintainers can trace every control to code and proof:

| Reference | Owns |
| --- | --- |
| `docs/userfacing/panes/*.md` | Every left-rail pane’s purpose, controls, preview/output effect, persistence, and recovery workflow |
| `docs/project/browser-control-qa-matrix.md` | Control-family ownership, primary test suites, and behavior contracts |
| `tests/browser/test_browser_control_inventory_audit.py` | Static, dynamic-literal, and programmatic control inventory guard |
| `scripts/audits/browser/pane_function_audit.py` | Pane function to selector/route/controller/persistence/proof trace |
| `docs/project/browser-pane-ownership.md` | Boundary rules between panes and shared shell |
| `docs/project/ELECTRON_RELEASE.md` | Local, Test-platform, and formal Release workflow requirements |

The 2026-09-18 static function audit found 562 pane-function rows, 351 control traces, and no open rows. That is a documentation and source-trace result only; it is not installed-package acceptance.

### All tracked Markdown files reviewed

The following files were reviewed against the current v1.0.7 source/UI/workflow contract. Files were edited only when stale or incomplete; stable policy, license-adjacent, and subsystem-reference documents were retained without cosmetic churn.

- Repository and contribution: `.github/PULL_REQUEST_TEMPLATE.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md` — reviewed; no product-contract changes required.
- Release and entry points: `README.md`, `CHANGELOG.md`, `docs/README.md`, `docs/project/ELECTRON_RELEASE.md`, `docs/project/EXHAUSTIVE_PACKAGED_RELEASE_VALIDATION_PLAN.md`, `docs/project/GOVERNANCE.md`, `docs/project/LIMITATIONS.md` — release boundary, 15-pane rail, and fail-closed proof language reviewed; this checklist, README, changelog, and docs index were updated.
- Engineering references: `docs/project/ARCHITECTURE.md`, `docs/project/DEVELOPING.md`, `docs/project/SHOTML_ARCHITECTURE.md`, `docs/project/browser-control-qa-matrix.md`, `docs/project/browser-pane-ownership.md`, `docs/tests/TEST_SUITE_GUIDE.md`, `scripts/README.md`, `electron/README.md` — reviewed against current source/test/workflow ownership; the QA matrix now links the human and executable control contracts.
- User guides: `docs/userfacing/USER_GUIDE.md`, `workflow.md`, `troubleshooting.md`, `project-structure.md`, and `panes/{project,media,compose,trim,score,splits,markers,overlay,review,export,intro-outro,queue,metrics,shotml,settings}.md` — reviewed as the complete 15-pane user-control reference; screenshot freshness remains a separate required gate below.
- Source-tree references: `src/splitshot/README.md`, `analysis/README.md`, `benchmarks/README.md`, `browser/README.md`, `browser/static/README.md`, `domain/README.md`, `export/README.md`, `media/README.md`, `merge/README.md`, `overlay/README.md`, `persistence/README.md`, `presentation/README.md`, `scoring/README.md`, `timeline/README.md`, `ui/README.md`, and `utils/README.md` — reviewed; no public or architectural drift identified.
- Analysis reference: `docs/analysis/SHOTML.md` — reviewed; no v1.0.7 release-prep edit required.

## Screenshot and local real-media gate

- Before replacing `docs/screenshots/`, supply two different maintainer-approved real video paths outside `tests/`:

  ```bash
  uv run python scripts/docs/capture_browser_screenshots.py \
    --primary-video /absolute/path/to/approved-primary.mp4 \
    --secondary-video /absolute/path/to/approved-secondary.mp4
  ```

- Review every generated 1400×900 image for current controls, decoded non-black footage, privacy, sharpness, and useful expanded-state coverage. Do not claim fresh screenshots until this has completed.
- Run and retain the local real-media E2E evidence for stage import, secondary layout/sync, Trim, ShotML, Splits, PractiScore/Score, Markers, Overlay, Review, Export, In / Out, Queue, Metrics, individual output, combined output, persistence/reopen, and output inspection.

## Required validation order

1. Run targeted documentation/control/screenshot tooling tests for changed files.
2. Run `uv run splitshot --check`, Electron preflight, and `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`.
3. Resolve every failure with a focused regression test and rerun the affected local scenario before advancing.
4. Push one final candidate commit and dispatch **Test macOS**, **Test Windows**, and **Test Linux** for that exact commit. Build workflows alone are insufficient.
5. Inspect every uploaded package and E2E bundle. Each platform summary must have matching candidate commit/corpus/manifest identity with `failed == 0`, `skipped == 0`, and `gaps == 0`; verify rendered individual and combined outputs plus the ordered `full-feature-validation` record.
6. If one platform fails, correct its root cause, rerun local gates, rerun that platform, then rerun all three platforms on the final identical commit.

The formal `Release` workflow, semver tagging, and publishing remain out of scope until all gates above pass and explicit approval is given.
