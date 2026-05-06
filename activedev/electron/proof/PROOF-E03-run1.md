# E03 — Production Build (Run 1)

## Status: PARTIAL

## Remediation note

This proof no longer treats icon generation and dependency install as
equivalent to a verified production build.

## What is now verified

- `electron/package.json` contains the current builder configuration used by CI.
- `node scripts/bundle-python.js` succeeds and refreshes the packaged backend.
- Source-level Electron smoke coverage now proves startup/runtime project-open
  behavior before packaging.

## Verification

```bash
node scripts/bundle-python.js
npm --prefix electron run test:electron-smoke
```

## Current artifact-proof status

- A fresh local `npm --prefix electron run build:mac` was attempted on
  `2026-05-06` and progressed through bundling/signing but did not complete in
  time to serve as trustworthy close-out evidence.
- Artifact-level completion is therefore deferred to the refreshed GitHub
  Actions run for this branch instead of being claimed from icons alone.

## Done criteria
- [x] App icons generated for macOS (`.icns`) and base `.png` for Linux/Windows
- [x] `electron/package.json` build config verified
- [x] `npm --prefix electron install` succeeded
- [ ] Fresh current-branch installer artifacts verified

## Risks

- Do not mark this task complete again until the current branch’s workflow run
  produces installers and the proof links that run directly.
