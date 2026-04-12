# Browser Project + Waveform Flow Gap Analysis

## What Failed

- The waveform was split across multiple visual layers: a canvas plus a separate timeline strip. That made the lower blue area feel disconnected and created alignment risk between timeline markers and waveform hit testing.
- Project actions were still too path-field centered. The visible buttons did not consistently behave like local file-browser actions.
- Open Project reused the text field path and did not enforce a full browser-state cleanup after loading a different project.
- Display-name state was stored outside the project and was not cleared on project new/open/delete.
- Existing tests checked that buttons were wired, but not that the correct file-dialog kinds and durable project state transitions occurred.

## Remediation

- Treat the waveform canvas as the single source of truth for visual timing markers.
- Add explicit project-open and project-save dialog modes at the server boundary.
- Refresh browser media element source state after project transitions.
- Clear server display-name cache when loading or clearing projects.
- Add server/API and static tests for dialog kind behavior, stale media replacement, and removed timeline strip UI.
