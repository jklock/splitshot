# Browser Logo Single Window Gap Analysis

## Current Gaps

- The browser rail still uses placeholder apple markers instead of the provided SplitShot logo.
- The rail brand cell contains text and project status when it should be logo-only.
- Tool labels are too small for a practical tool surface.
- The sticky top bar consumes vertical space and duplicates session state.
- Action buttons are visually separated from the workspace instead of being part of the cockpit.
- The body can scroll in desktop viewports, which makes the interface feel like a web page instead of a local control surface.
- Inspector and timeline sizing are not explicitly constrained to one viewport.

## Closure Plan

- Replace the brand cell with the provided static logo.
- Remove all visible apple markers from navigation items.
- Increase rail width to 76px and strengthen nav label typography.
- Replace `topbar` with a compact `command-strip`.
- Convert the root shell and body to fixed-height, hidden-overflow layout.
- Compact metrics, toolbar, video, waveform, split, and inspector row heights.
- Add tests that lock the requested workflow and layout constraints.

## Residual Risks

- Very small browser windows may still require responsive fallback behavior.
- Long localized labels or very long project names can exceed fixed cells if future copy changes are not reviewed.
- Browser video control chrome height differs by browser, so the video region must remain flexible rather than hardcoded to one exact pixel value.
