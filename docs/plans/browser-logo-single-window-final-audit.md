# Browser Logo Single Window Final Audit

## Feature Match

- The browser rail now uses the supplied SplitShot logo from `/static/logo.png`.
- The top-left rail cell is logo-only in the visible UI.
- Literal apple markers were removed from every tool button.
- Tool labels are text-only, bold, and fit in a wider 76px rail.
- The former sticky top bar was removed.
- Open stage video, add second angle, and refresh remain available in a compact command strip.
- The command strip preserves the existing file picker behavior through the same DOM IDs.
- Metrics, video review, timeline, waveform, split cards, and inspector remain in one active workspace.

## Usability And Layout

- Desktop browser body scrolling is disabled with a fixed `100vh` cockpit shell.
- The main cockpit grid uses fixed command and metric bands with a flexible review area.
- Video height is flexible instead of hardcoded to a large viewport percentage.
- Split cards and inspector content scroll internally when needed so the browser page itself stays fixed.
- All cards and controls retain sharp square corners.

## Validation

- `node --check src/splitshot/browser/static/app.js`
- `uv run --python 3.12 pytest tests/test_browser_static_ui.py`
- `uv run --python 3.12 pytest`
- Browser server smoke check confirmed `/` returns HTML and `/static/logo.png` returns `image/png`.

## Result

The requested logo, rail cleanup, top-bar removal, command relocation, and single-window browser layout are complete. The remaining risk is visual tuning across uncommon browser chrome sizes, but the implementation now constrains the application shell rather than letting the document page scroll.
