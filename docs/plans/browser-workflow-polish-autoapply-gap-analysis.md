# Browser Workflow Polish And Auto-Apply Gap Analysis

## Current Gaps

- Project is last in the rail even though it is the starting point for local video/project work.
- Edit mode duplicates waveform controls that already live in the main workspace.
- Selected-shot nudge/delete controls appear in review/scoring contexts where they obscure more important task controls.
- The review overlay text can cover content in the video area.
- The waveform drawing starts too low in the waveform panel.
- Settings-style controls require Apply buttons even though the app runs locally and can save changes immediately.
- Overlay color controls are too large for a right-side tool inspector.
- Project/export path fields require manual path typing without a local chooser button.
- Video import has console/log activity but no persistent page-level processing bar.
- The documented launch command still allows users to believe `--python 3.12` is required.

## Closure Plan

- Reorder/remove rail tools and tests accordingly.
- Move timing edit controls into the Timing pane and leave Review focused on video, waveform, and splits.
- Make scoring self-describing and tied to selected shot assignment.
- Remove the floating video status element and use only the top metrics/status strip.
- Reorder waveform DOM/CSS so the waveform canvas starts at the top of the box.
- Add debounced auto-apply handlers for all non-destructive settings.
- Add chooser endpoints and path-picker buttons.
- Add `.python-version` and README command wording updates.
- Add feature tests for these user-facing behaviors.

## Residual Risk

- Native file chooser behavior depends on the user launching the local server in an environment allowed to show OS dialogs. The API will return a clear error if the dialog backend cannot open.

## Closure Status

- All listed implementation gaps are closed in the browser UI, browser server, README launch path, and tests.
- The remaining risk is OS dialog availability when a local browser-control server is launched from a constrained environment.
