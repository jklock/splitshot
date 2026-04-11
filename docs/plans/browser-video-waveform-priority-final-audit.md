# Browser Video Waveform Priority Final Audit

## Feature Match

- The main browser workspace now contains only the two primary work surfaces: video first and waveform second.
- The top command strip was removed.
- The empty-state row was removed.
- The horizontal metrics row was removed.
- Open stage video, add second angle, refresh, status, metrics, selected-shot tools, split cards, readiness, scoring, overlay, merge, layout, export, and project controls now live in the right sidebar.
- The left rail remains navigation-only.
- The logo is constrained to a 56px rail asset inside the 76px rail cell.

## Usability And Layout

- Video receives the majority of available center space.
- Waveform remains directly connected to video review and editing.
- Secondary controls no longer steal vertical space above the video.
- Metrics and splits are still visible, but no longer dominate the main workspace.
- The desktop shell remains fixed-height with overflow contained inside sidebar/split areas.
- The design keeps square, contiguous controls.

## Validation

- `node --check src/splitshot/browser/static/app.js`
- `uv run --python 3.12 pytest tests/test_browser_static_ui.py`
- `uv run --python 3.12 pytest`
- Browser server smoke check verified `/`, `/static/logo.png`, and the video -> waveform -> inspector DOM order.

## Result

The browser UI now follows the intended priority order: video, waveform, everything else in the sidebar. The prior top rows cannot return without failing static UI tests.
