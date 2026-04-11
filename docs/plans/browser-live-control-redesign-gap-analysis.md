# Browser Live Control Redesign Gap Analysis

## Current Gaps

- Browser UI does not follow the left-rail workflow users expect from the comparison app.
- Primary and secondary video selection requires typing paths instead of opening a file picker.
- Video review does not expose a live overlay preview tied to playback time.
- Overlay customization is limited to position and badge size in browser mode.
- Scoring mode does not expose practical-shooting ruleset presets in browser mode.
- Sync offset can be computed but not adjusted directly from browser mode.
- Static UI tests currently lock in the rejected top-tab/sharp-grid design.

## Required Fixes

- Replace the top-tab shell with left rail navigation and persistent page state.
- Add multipart local file endpoints and wire `<input type="file">` controls.
- Keep path-based APIs as an advanced fallback while making file picker selection primary.
- Add DOM overlay rendering in the browser video viewport.
- Add color, text color, opacity, and scoring color controls.
- Add scoring profile model helpers and API support.
- Add sync offset nudge controls.
- Rewrite UI tests to validate feature presence and local usability, not visual trivia.

## Residual Constraints

- A browser cannot directly read arbitrary absolute file paths from a file picker for security reasons. SplitShot solves this by sending the selected file to the local `127.0.0.1` server and storing it in a local session directory, with no cloud transfer.
- Browser save dialogs for arbitrary output paths are not universally available without browser-specific File System Access APIs. SplitShot keeps an output path field and local export API for reliable cross-browser operation.
- Desktop mode remains functional but this pass prioritizes browser parity because browser mode is the default.

