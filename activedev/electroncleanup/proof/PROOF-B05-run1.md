# B05 — File associations all 3 platforms

## Status: Complete

## Remediation note

This proof supersedes the earlier claim that package metadata alone completed
cross-platform file-open support. The runtime handlers now exist and are
covered by automated tests.

## Changes

- `electron/launch-intent.js`
  - Normalizes `.ssproj` bundles and `project.json` paths
  - Parses `splitshot://open?path=...` deep links
  - Queues launch intents until the window and backend are ready
- `electron/main.js`
  - Uses `--project` for first-launch project opens
  - Handles macOS `open-file`
  - Handles macOS `open-url`
  - Handles subsequent Windows/Linux-style opens through `second-instance`
- `electron/preload.js`
  - Bridges project-open events into the renderer
- `src/splitshot/browser/static/app.js`
  - Opens incoming project intents through the existing `/api/project/open` flow
- `electron/package.json`
  - Keeps `.ssproj` file associations
  - Keeps `splitshot` protocol registration
  - Adds Linux desktop MIME/protocol metadata for `x-scheme-handler/splitshot`

## Verification

```bash
npm --prefix electron run test:launch-intent
npm --prefix electron run test:electron-smoke
```

- `test:launch-intent` proves argv parsing, protocol parsing, `.ssproj`/`project.json`
  normalization, and launch-intent queue draining.
- `test:electron-smoke` proves:
  - startup project open via argv
  - simulated second-instance project open
  - protocol URL delivery through `splitshot://open?path=...`

## Remaining live-proof gap

- Installed-app double-click behavior still depends on current platform builds.
  That artifact-level proof now lives under the refreshed CI/release workflow
  rather than this task file claiming it from configuration alone.
