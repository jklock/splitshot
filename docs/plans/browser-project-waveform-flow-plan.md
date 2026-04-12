# Browser Project + Waveform Flow Plan

## Goal

Repair the browser workflow issues shown in the latest screenshots: the waveform must be one coherent editing window, and Project actions must behave like normal local-file actions with durable state after save/open/new.

## Requirements

- Remove the separate blue timeline strip layer and keep waveform scale, beep, shot markers, selected region, and zoom in the waveform canvas.
- Prevent stale video from remaining visible after New Project or after opening a project with missing media.
- Make Project buttons open appropriate local file browsers instead of requiring users to type paths first.
- Make Save Project save to the current path when present, and open a save dialog when no path exists.
- Make Open Project use an open-file dialog for `.ssproj` files, then refresh all UI state from the loaded project.
- Keep path-entry fields as visible state/fallback, but not as the primary workflow.
- Add feature tests for project dialog behavior and stale media clearing.

## Implementation

1. Remove `timeline-strip` markup, renderer calls, CSS, and tests.
2. Add project open/save dialog kinds so the server can distinguish opening an existing `.ssproj` from choosing a save target.
3. Wire Project `Open Project` and `Browse` to an open-project dialog.
4. Wire Project `Save Project` to save directly when a path exists and to save-as dialog when no path exists.
5. Add client-side state reset for video elements when primary/secondary paths are unavailable or changed.
6. Clear server display-name mapping on project new/open/delete so stale session upload names cannot leak into the loaded state.
7. Add tests that prove project dialogs are called with the correct kinds and loaded projects replace stale media state.
