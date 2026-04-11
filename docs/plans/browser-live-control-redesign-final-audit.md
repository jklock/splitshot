# Browser Live Control Redesign Final Audit

## Result

This pass replaces the rejected browser control page with a local-first, Shot Streamer-inspired workflow shell:

- Left workflow rail for Open, Review, Timing, Edit, Merge, Overlay, Scoring, Layout, and Export.
- Primary and secondary video selection use native browser file pickers.
- File picker selections are sent only to the local `127.0.0.1` SplitShot server and stored in a local session media directory.
- Path-based import APIs remain available for automation and advanced workflows.
- Review page includes playable primary video and a live overlay preview tied to playback time.
- Timing page exposes draw, split, cumulative beep-to-shot, absolute, confidence, source, and score values.
- Edit page keeps waveform add-shot, move-beep, selected-shot nudge, and delete controls.
- Merge page exposes secondary video selection, beep-based sync offset, manual 1 ms / 10 ms nudges, layout, PiP size, and swap.
- Overlay page exposes position, badge size, timer/shot/current/score badge background color, text color, opacity, and score-letter colors.
- Scoring page exposes USPSA/IPSC minor, USPSA/IPSC major, IDPA time-plus, Steel Challenge time-plus, and 3-Gun/UML time-plus presets.
- Layout/export pages retain aspect ratio, crop center, quality, and MP4 export controls.

## Feature Validation

- Local file selection: covered by `test_browser_file_picker_endpoint_imports_selected_primary_video`.
- Browser state after analysis: covered by `test_browser_state_exposes_metrics_after_primary_ingest`.
- Shot edit/scoring API: covered by `test_browser_control_api_imports_and_edits_video`.
- Merge/sync/swap: covered by `test_browser_control_api_syncs_and_swaps_secondary_video`.
- Overlay style and scoring preset APIs: covered by `test_browser_control_api_updates_overlay_styles_and_scoring_preset`.
- Browser UI contract: covered by `test_browser_ui_is_local_first_left_rail_shell` and `test_browser_ui_exposes_video_overlay_and_scoring_controls`.
- Hit Factor now uses raw beep-to-final-shot time when a beep is present.

## Validation Commands

- `uv run pytest tests/test_browser_static_ui.py tests/test_browser_control.py tests/test_scoring_and_merge.py`
  - Result: `11 passed`
- `uv run pytest`
  - Result: `38 passed`
- `node --check src/splitshot/browser/static/app.js`
  - Result: JavaScript syntax check passed.
- `uv run --python 3.12 splitshot --check`
  - Result: FFmpeg, FFprobe, and browser assets present.
- `QT_QPA_PLATFORM=offscreen uv run --python 3.12 python - <<'PY' ...`
  - Result: `desktop-smoke-ok`

## Residual Risks

- Browser security prevents reading an arbitrary absolute path directly from a file input. The implemented behavior is the practical local solution: selected files are copied to the local SplitShot server session directory.
- Browser export save dialogs remain cross-browser inconsistent, so output MP4 path entry remains the reliable local export mechanism.
- The scoring presets are editable approximations around SplitShot's available shot-letter model; match-specific rule variations should remain configurable rather than hard-coded.
