# UI

The UI package contains the shared controller used by the browser surface.

## Files

- [controller.py](controller.py) owns project mutations, settings persistence, and signal emission.

## Controller Responsibilities

`ProjectController` is the shared mutation layer for the whole application. It:

- loads and saves `AppSettings`
- loads and saves `.ssproj` project bundles
- probes media files into `VideoAsset` objects
- runs analysis for primary and secondary media
- maintains merge, overlay, scoring, and export state on the shared `Project`
- emits Qt signals when project state, settings, or status changes

The helper functions at the top of `controller.py` reset media-dependent state, derive PiP size and badge size defaults, and keep secondary media synchronized with the merge-source list.

## Shared Behavior

The browser UI and other runtime services use the same controller, the same project model, and the same export pipeline. The controller remains the single mutation layer for project state.

**Last updated:** 2026-04-15
**Referenced files last updated:** 2026-04-15
