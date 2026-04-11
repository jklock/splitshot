# Browser Layout Popout QA Gap Analysis

## Current Gaps

- Logo is technically larger but visually too small because the source asset has padding and is not scaled in the clipped rail cell.
- The top metric strip uses content-sized metric cells, so its boxes do not align with the main grid below.
- Long file paths in the right sidebar force horizontal visual movement and overlap.
- Uploaded videos display temp UUID prefixes instead of the chosen local filename.
- Waveform expansion only hides the sidebar; it does not make the waveform take over the primary work area clearly enough.
- Button logging is partial because many buttons log only through their downstream action handlers.
- There is no explicit QA artifact that says what every button does.

## Closure Plan

- Scale the logo inside an enlarged clipped rail brand cell.
- Make the top strip a 5-column grid with fixed metric columns and a controlled filename cell.
- Clamp the inspector width and remove horizontal overflow.
- Preserve upload display names in the browser server session and emit them in API state.
- Update the frontend to render display names in top strip and project details.
- Change waveform-expanded layout so the waveform panel is the only visible main work surface.
- Install a generic document-level button click logger.
- Create a button QA audit document and tests around critical button behavior.

## Residual Risks

- Without browser automation, pointer drag behavior is still validated through event wiring and API effects rather than a real rendered pointer session.
- Long project paths can still be visually dense, but they will no longer resize the sidebar or overlap outside their cells.

## Closure Status

- All listed implementation gaps are closed in the browser UI and server state layer.
- The remaining risk is test-tooling scope: the repo does not currently include a rendered browser automation dependency, so the final validation uses static UI contracts, browser server/API tests, runtime checks, and activity-log smoke coverage.
