# Browser Overlay + Score Cleanup Final Audit

## Scope

This pass corrected the specific regressions called out in the latest screenshots and revalidated the broader feature path that depends on them: local analysis, overlay preview, per-shot scoring, merge/PiP export, and Stage1 artifact generation.

## View Audit

- Splits: the large split-card grid was removed. Timing data remains available through the timing table and waveform tools instead of the cluttered card wall.
- Scoring: the `Behavior` row and score-position workflow were removed. Each shot row now exposes an inline score selector tied directly to that shot.
- Overlay/Layout: live overlay badges are compact square elements again. Positioning uses quadrant/custom coordinates without stretching `left` or `right` modes into full-height bars.
- Project: the left rail is smaller and the destructive project action is separated by spacing from the normal project actions.
- Export: the real FFmpeg export path was fixed so a successful encode is not marked failed only because the decoder logs an expected `Broken pipe` after pipe shutdown.

## Validation

- `node --check src/splitshot/browser/static/app.js`
- `uv run pytest tests/test_browser_static_ui.py tests/test_browser_control.py::test_browser_control_api_updates_overlay_styles_and_scoring_preset tests/test_export.py::test_overlay_renderer_embeds_score_inside_shot_badge`
- `uv run pytest tests/test_browser_static_ui.py`
- `uv run pytest`
- Generated `/Volumes/Storage/GitHub/splitshot/artifacts/stage1-all-options.mp4`
- Generated `/Volumes/Storage/GitHub/splitshot/artifacts/stage1-all-options-preview.png`

## Stage1 Output

- Output: `/Volumes/Storage/GitHub/splitshot/artifacts/stage1-all-options.mp4`
- Preview: `/Volumes/Storage/GitHub/splitshot/artifacts/stage1-all-options-preview.png`
- Codec: H.264
- Size: 720 x 1280
- Frame rate: 30 fps
- Duration: 31.4 seconds
- Enabled artifacts: timer, draw, current shot split, per-shot score value, hit factor, custom review box, and PiP merge.
