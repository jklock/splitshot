# Browser Logo Single Window Plan

## Goal

Make the browser control interface operate as a compact local tool that fits inside one browser viewport without page scrolling.

## User Requirements

- Use `logo.png` as the SplitShot logo.
- Make the top-left rail cell logo-only.
- Remove the literal apple markers from the tool rail.
- Keep rail text bold and readable.
- Increase the left rail width by roughly 10% so tool labels fit.
- Remove the full top bar.
- Move the primary actions into the workspace below the removed top bar.
- Keep the page hard-edged with no rounded cards.
- Prevent whole-page scrolling in the normal desktop browser viewport.

## UI Plan

- Copy the provided logo into the browser static assets and reference it from the rail brand.
- Replace each rail item with text-only bold labels.
- Keep the active rail affordance as a square orange cell.
- Replace the sticky header with a compact command strip inside the cockpit content.
- Preserve the same file chooser buttons and hidden file inputs.
- Keep the metrics, video, waveform, split list, and inspector in one workspace.
- Use a fixed-height viewport grid so the browser body does not scroll.
- Let the video and timeline areas flex while keeping controls visible.

## Functional Plan

- Preserve existing local file browser behavior for primary and secondary stage videos.
- Preserve refresh, new project, review tool selection, timing edits, scoring, overlay, merge, layout, and export controls.
- Keep the session state active while moving controls.
- Make JavaScript tolerant of hidden or missing presentational nodes.

## Test Plan

- Verify the static UI contains the logo reference and not the apple markers.
- Verify the full top bar markup is gone.
- Verify the command actions still exist exactly once.
- Verify the one-viewport shell CSS disables body scrolling and uses fixed viewport height.
- Verify the rail width increased from the prior 68px shell.
- Run the existing feature test suite to catch browser, analysis, project, and export regressions.
