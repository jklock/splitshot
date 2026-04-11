# Browser Review Cockpit Gap Analysis

## Current Gaps

- The browser UI uses separate pages for open, review, timing, edit, merge, overlay, scoring, layout, and export.
- Common tasks require leaving the video/timeline context.
- Tool navigation is workflow-page navigation instead of contextual inspector selection.
- Tests currently assert page shell behavior rather than persistent cockpit behavior.

## Fixes

- Replace page sections with a persistent cockpit layout.
- Replace page selection with tool selection.
- Reuse existing IDs where practical so current JavaScript behavior can be adapted without replacing backend APIs.
- Add a tool drawer renderer that moves existing timing, edit, merge, overlay, scoring, layout, project, and export controls into one inspector.
- Update static UI tests to validate the persistent cockpit workflow.

