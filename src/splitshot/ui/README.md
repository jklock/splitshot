# UI

The UI package contains the PySide6 desktop interface and the shared controller that powers both user surfaces.

## Files

- [controller.py](controller.py) owns project mutations, settings persistence, and signal emission.
- [main_window.py](main_window.py) builds the desktop window, navigation rail, review surface, and inspector panels.
- [widgets/](widgets) contains the reusable dashboard, waveform, and overlay preview widgets.

## Controller Responsibilities

`ProjectController` is the shared mutation layer for the whole application. It:

- loads and saves `AppSettings`
- loads and saves `.ssproj` project bundles
- probes media files into `VideoAsset` objects
- runs analysis for primary and secondary media
- maintains merge, overlay, scoring, and export state on the shared `Project`
- emits Qt signals when project state, settings, or status changes

The helper functions at the top of `controller.py` reset media-dependent state, derive PiP size and badge size defaults, and keep secondary media synchronized with the merge-source list.

## Desktop Window

`MainWindow` creates the PySide6 experience with these major sections:

- a left navigation rail with Manage, Upload, Merge, Overlay, Scoring, Layout, Swap, and Export pages
- a top header with the current project name and status pill
- a central review stack with playback, waveform editing, split cards, and the preview container
- a right inspector with page-specific controls

## Widgets

- `WaveformEditor` provides the interactive shot timeline editor.
- `OverlayPreview` shows on-video placement for score marks, crop boxes, and review overlays.
- `DashboardWidget` helpers in `widgets/dashboard.py` render the split cards, upload state, and summary cards.

## Shared Behavior

The desktop UI uses the same controller, the same project model, and the same export pipeline as the browser UI. The difference is the presentation layer, not the underlying data flow.

**Last updated:** 2026-04-13
**Referenced files last updated:** 2026-04-13
