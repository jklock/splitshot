# Markers Pane

This page describes the marker surface exactly as it works now in the browser shell.

## Compact Pane

The `Markers` inspector pane always shows:

- `Enable Markers`
- `Edit` when the marker editor is closed
- `Collapse` when the marker editor is open
- `Add Time Marker`
- the compact marker list

The compact pane does not show the selected-marker editor until edit mode is open.

## Edit Mode

Click `Edit` to open marker edit mode. In edit mode:

- the bottom workbench opens with the marker list and marker workbench controls
- the workbench toolbar includes `Add Time Marker`, `Add Selected Shot`, and `Import Shots`
- the right inspector shows `Selected Marker`
- the compact button changes from `Edit` to `Collapse`

Click `Collapse` to close edit mode. There is no second collapse button in the bottom workbench.

## Selected Marker

The selected-marker header contains:

- marker name
- enabled checkbox
- `Duplicate`
- `Remove`

These controls stay in the right inspector only while edit mode is open.

## Motion

`Motion` is controlled by one checkbox: `Enable Motion`.

When `Enable Motion` is off:

- the marker stays fixed
- the guided motion step section is hidden

When `Enable Motion` is on:

- the guided motion step section appears
- the guided actions are shown as a compact 2x2 button block with a red `Clear path` button below it
- the marker can store and replay a motion path
- only the currently selected motion point is shown on the video, as an orange circle
- the video remains a placement surface only while you edit motion points

The guided motion workflow is:

1. `Start` is the marker's base position at the beginning of its duration.
2. `Finish` is the marker position at the end of its duration.
3. Place `Start` and `Finish` on the video first.
4. Click `Generate` to let SplitShot try to trace the visible motion between those points from the video.
5. If tracking cannot lock onto the video detail, `Generate` falls back to evenly spaced in-between points between `Start` and `Finish`.
6. Use `Add Detail` to split the largest remaining time gap when you need one more hand-tuned point.
7. Use `Previous` and `Next` to jump between `Start`, generated `Auto` points, hand-authored `Detail` points, and `Finish`.
8. Use the compact X/Y fields or drag the orange circle on the video to refine the currently selected point.
9. Use `Remove Detail` to delete the selected in-between point.
10. Use `Clear path` to remove all authored motion and turn motion off.

The editor still persists motion internally as a `motion_path`, but the user-facing flow stays `Start`/`Finish`/`Auto`/`Detail` rather than exposing a separate keyframe editor.

## Settings Defaults

The `Settings > Markers` section controls defaults for newly created markers:

- enabled
- content type
- text source
- duration
- width
- height
- `Enable motion`
- background color
- text color
- opacity

The `Enable motion` setting in `Settings` controls whether new markers start with motion enabled. It is a default only. Existing markers keep their own motion checkbox state.

## Relevant checks

Use these checks when you want to validate the current marker surface:

- `node --check src/splitshot/browser/static/app.js`
- `uv run python -m compileall -q src/splitshot`
- `uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control_inventory_audit.py tests/browser/test_browser_control_coverage_matrix.py tests/browser/test_browser_rail_layout.py::test_marker_workbench_bottom_resize_is_temporary_and_restores_waveform_height tests/browser/test_browser_interactions.py::test_marker_collapsed_navigation_and_marker_list_selection_stay_in_sync tests/browser/test_browser_interactions.py::test_marker_badge_drag_keeps_motion_path_intact_when_editing_base_point tests/browser/test_browser_interactions.py::test_marker_template_controls_drive_new_shot_marker_defaults tests/browser/test_browser_interactions.py::test_marker_motion_toggle_keeps_current_marker_selected tests/browser/test_browser_interactions.py::test_generate_motion_path_falls_back_to_single_in_between_for_small_meaningful_travel tests/browser/test_browser_interactions.py::test_generate_motion_path_falls_back_to_evenly_spaced_points_for_longer_travel tests/browser/test_browser_interactions.py::test_generate_motion_path_prefers_traced_motion_when_available tests/browser/test_browser_remaining_controls_e2e.py::test_markers_template_toggle_and_popup_bubble_authoring_controls_commit_state -q`
