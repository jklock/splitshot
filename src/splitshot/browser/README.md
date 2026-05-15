# Browser

This package owns the browser-first runtime: the local HTTP server, JSON API, activity logging, PractiScore session plumbing, and browser-state serialization.

## Purpose

Use this package when the change touches routes, browser-session behavior, file import/export surfaces, activity logs, PractiScore session flow, or browser JSON payloads.

## Read This First

- [server.py](server.py)
- [state.py](state.py)
- [static/README.md](static/README.md)

## Main Files

- [cli.py](cli.py): browser runtime entrypoint
- [server.py](server.py): HTTP server and browser API surface
- [state.py](state.py): `Project` to browser-state serializer
- [activity.py](activity.py): JSONL activity logging
- [practiscore_profile.py](practiscore_profile.py), [practiscore_session.py](practiscore_session.py), [practiscore_qt_runtime.py](practiscore_qt_runtime.py): manual PractiScore login flow and persistent profile handling
- [static/](static): browser shell modules, styles, and assets

## Runtime Flow

1. The CLI starts `BrowserControlServer`.
2. The server exposes `/api/state`, mutation routes, media routes, and static assets.
3. `browser_state` serializes the shared controller-backed `Project`.
4. Activity logs stream request, export, and dialog events to JSONL.

## Key Extension Points

- `BrowserControlServer`
- `browser_state`
- activity logging and PractiScore session helpers

## Related Tests

- [../../../tests/browser/](../../../tests/browser/)
- [../../../tests/electron/test_headless_server.py](../../../tests/electron/test_headless_server.py)

## Related Docs

- [../../../docs/project/ARCHITECTURE.md](../../../docs/project/ARCHITECTURE.md)
- [static/README.md](static/README.md)
- [../../../docs/project/browser-control-qa-matrix.md](../../../docs/project/browser-control-qa-matrix.md)
