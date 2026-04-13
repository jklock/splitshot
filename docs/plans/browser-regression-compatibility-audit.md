# Browser Regression And Compatibility Audit

## Purpose

This audit is meant to catch the class of regressions where browser, export, and desktop behavior drift apart after incremental fixes. The recent history on `main` shows repeated break/fix cycles concentrated in the browser overlay, project-path, and auto-apply workflows.

## Representative History

- `941eb15` Fix browser workflow regressions and media support
- `fd2c819` fix(browser): repair project dialogs and waveform panel
- `19cf3fe` fix(browser): clean overlay and scoring workflow
- `01594d9` fix(browser): repair waterfall review workflow
- `832ce55` fix(browser): stabilize dynamic layout and scoring controls
- `33af1eb` fix(browser): polish workflow and auto-apply controls

## Recurring Regression Classes

### 1. Always-populated browser fields override preset logic

- Symptom: a preset appears to apply, then silently reverts on the next auto-apply round-trip.
- Example: `badge_size` vs `overlay.font_size` in `src/splitshot/browser/static/app.js` and `src/splitshot/ui/controller.py`.
- Root cause: browser payloads always include a derived field, so the server treats the derived value as explicit user input.

### 2. Local browser drafts are lost during server-driven rerenders

- Symptom: typed values disappear or revert after an API call.
- Examples: project path draft, export path draft, color picker state.
- Root cause: `callApi()` applies remote state and fully rerenders controls, replacing active DOM nodes while the user is still editing.

### 3. Browser preview and export renderer use different defaults

- Symptom: preview looks correct, exported output does not match.
- Examples: custom quadrant fallback coordinates, split badge formatting, final/draw badge timing.
- Root cause: browser and Qt renderer each implement overlay rules separately.

### 4. Browser-only interaction rules are not mirrored in persisted state

- Symptom: a control appears to work until the project is saved, reopened, or exported.
- Examples: custom quadrant with empty coordinate fields, auto-applied overlay control defaults.
- Root cause: browser preview applies client-only fallbacks, but the persisted project state does not carry the same normalized values.

### 5. Native control behavior differs across browser engines

- Symptom: a control works in Chromium/simplebrowser but fails or becomes unstable in Safari/WebKit.
- Example: color inputs inside auto-applied overlay grids.
- Root cause: native controls such as `input[type="color"]` behave differently across engines, and DOM replacement during active interaction is especially fragile in WebKit.

## Audit Method

### A. Search for paired implementations before editing behavior

Run these searches together:

- `badge_size|font_size|set_badge_size|syncOverlayFontSizePreset`
- `custom_x|custom_y|shot_quadrant|custom_box_quadrant|positionOverlayContainer|_paint_badges`
- `show_draw|show_score|display_label|Final|Draw|Shot`
- `callApi\(|applyRemoteState\(|renderControls\(|renderStyleControls`

Files to inspect as a set:

- `src/splitshot/browser/static/app.js`
- `src/splitshot/overlay/render.py`
- `src/splitshot/ui/controller.py`
- `src/splitshot/scoring/logic.py`
- relevant browser/export tests

### B. Verify invariants, not only API state

For each overlay or project-control edit, verify:

- browser preview matches exported overlay rules
- server payload does not include derived values unless they are intentionally committed
- custom/default fallbacks are identical in browser and export paths
- active form controls are not destroyed during native picker or text-entry interaction
- saved/reopened project state round-trips without losing in-progress values

### C. Prefer commit-on-change for fragile native controls

For browser engines with native pickers or dialogs:

- use local preview updates on `input`
- commit to the server on `change`
- avoid full control rerenders while the picker is open

This is required for `input[type="color"]` and any future native file/path/dialog backed control.

### D. Bump browser bundle versions after static JS/CSS fixes

- If `src/splitshot/browser/static/app.js` or `styles.css` changes, update the versioned asset URL in `index.html`.
- Reload the live page before validating behavior.

### E. Add parity tests in pairs

When a browser fix touches overlay, add both:

- a browser/static or browser-control regression
- an export/renderer regression

This is the minimum guard against fixing the preview while breaking the export path, or vice versa.

## Compatibility Checks For macOS And Windows

### Color controls

- Audit `input[type="color"]` handlers for `input` vs `change` behavior.
- Ensure color selection does not depend on Chromium-specific picker behavior.
- Treat the native picker UI as engine-specific; the requirement is stable value selection, not identical dialogs.
- Keep a text/hex fallback on the roadmap if native picker behavior remains inconsistent in manual Safari testing.

### Overlay positioning

- Verify the same quadrant/custom-coordinate rules in browser preview and Qt export.
- Empty custom coordinates must resolve to the same visible position everywhere.

### Auto-apply workflows

- Verify that edits made in browser controls survive a server round-trip.
- Search for controls rendered from server state immediately after the same control posts to the server.

## Definition Of Done For Overlay/UI Fixes

- matching browser preview and export behavior
- stable state after save/open and after rerender
- static asset version bumped when browser JS changes
- browser regression plus export regression added
- manual live browser reload verification performed