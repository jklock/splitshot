# Browser Video Waveform Priority Gap Analysis

## Current Gaps

- A command strip at the top consumes space before the video.
- An empty-state row consumes space before the video.
- A horizontal metrics row consumes space before the video.
- The video is third or fourth in the visual order instead of first.
- Split cards occupy central space even though they are secondary data.
- Session controls and metrics are distributed across the page instead of being collapsed into the inspector.
- The current layout is more fragile because multiple fixed rows compete with the video and waveform.

## Closure Plan

- Delete the top command, empty-state, and metric rows from the main content flow.
- Move command buttons and hidden file inputs into the sidebar.
- Move metrics into a compact sidebar grid.
- Move split cards into the sidebar review pane.
- Make the main review stack exactly two primary rows: video and waveform.
- Keep timeline markers attached to the waveform panel.
- Update JavaScript to stop requiring removed empty-state markup.
- Update tests to lock the new priority hierarchy.

## Residual Risks

- The right sidebar can still require internal scrolling when advanced tool panes are open.
- Very narrow screens need responsive stacking, but desktop browser usage remains the target for the cockpit.
- Native browser video controls differ slightly by browser, so the center video row must remain flexible.
