# E04 — CI and Release (Run 1)

## Status: PARTIAL

## Remediation note

This proof no longer treats the existence of a workflow file as sufficient
evidence that the release path works.

## What is now implemented

- `.github/workflows/build-electron.yml` now includes:
  - manual `workflow_dispatch` smoke runs
  - explicit macOS PKCS#12 validation/import preflight
  - notarization credential validation
  - launch-intent unit tests
  - headless backend tests
  - bundled parity audit
  - Electron source smoke tests
  - installer verification and Linux desktop metadata verification
  - release publishing only for real `v*` tags

## Verification

- Successful trusted smoke run on the prior signing remediation branch state:
  - GitHub Actions run `25440219571`
- Fresh current-branch run exercising the expanded workflow:
  - GitHub Actions run `25443470653` (in progress at proof update time)

## Done criteria
- [x] `.github/workflows/build-electron.yml` exists
- [x] All three platforms configured
- [x] Release creation on tag push
- [x] Signing/notarization env vars wired
- [ ] Fresh current-branch workflow run completed with the expanded checks

## Risks

- Do not mark this task complete until run `25443470653` or a newer equivalent
  completes successfully and is linked here.
