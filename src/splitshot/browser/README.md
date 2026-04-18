# Browser

The browser package serves the primary SplitShot experience: a local HTTP server, JSON API, activity logging, and the browser shell assets.

## Files

- [cli.py](cli.py) exposes the browser entry point used by `splitshot-web`.
- [server.py](server.py) runs the HTTP server, serves the static UI, and handles all browser API routes.
- [state.py](state.py) converts the shared `Project` into the JSON payload consumed by the browser shell.
- [activity.py](activity.py) writes per-run JSONL activity logs.
- [static/](static) contains `index.html`, `app.js`, `styles.css`, and the branding image.

## Server Responsibilities

`BrowserControlServer` handles:

- static file serving for the browser shell
- `/api/state` serialization
- `/media/primary` and `/media/secondary` playback URLs
- project, analysis, scoring, merge, overlay, sync, and export POST routes
- native file-picking dialogs for local media selection and export paths

## Activity Logging

`ActivityLogger` writes a timestamped JSONL log under `logs/` by default. The server logs HTTP requests, API calls, dialog selections, export progress, and streamed export log lines.

Every record now carries a `level` field. File logging stays on for every run, while terminal mirroring is opt-in through `splitshot --log-level info` (or `debug`, `warning`, `error`). The default level is `off`, which keeps the terminal quiet unless you explicitly request live log output.

## State Serialization

`browser_state` combines:

- the serialized `Project`
- derived stage metrics and timing segments
- split rows
- scoring and export preset summaries
- media availability flags and playback URLs
- repeatable overlay text-box state used by Review and Export

## Runtime Notes

- The browser server is local-only and binds to `127.0.0.1` by default.
- On macOS it uses AppleScript dialogs for native file selection.
- The server keeps a temporary session directory for imported local files that need to survive long enough for analysis or export.

**Last updated:** 2026-04-15
**Referenced files last updated:** 2026-04-15
