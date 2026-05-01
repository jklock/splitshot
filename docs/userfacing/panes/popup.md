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

The guided motion workflow is:

1. `Step 0` is the marker's `Base` position.
2. Move the playhead to the next time where the marker should change position.
3. Click `Add Step`.
4. New authored steps start in the center of the frame so they are immediately visible.
5. Authored points are labeled `Step 1`, `Step 2`, `Step 3`, and so on.
6. Use `Previous Step` and `Next Step` to jump the video between the authored points.
7. Use the compact X/Y fields or drag the orange circle on the video to refine the selected point.
8. Use `Remove Step` to remove the selected authored step.
9. Use `Clear path` to remove all authored motion and turn motion off.

The editor still persists motion internally as a path of authored points, but the user-facing flow is step-based rather than keyframe-based.

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

## Proof

Validated against:

- `node --check src/splitshot/browser/static/app.js`
- `uv run python -m compileall -q src/splitshot`
- `uv run pytest tests/browser/test_browser_static_ui.py tests/browser/test_browser_control_inventory_audit.py tests/browser/test_browser_control_coverage_matrix.py tests/browser/test_browser_interactions.py::test_marker_collapsed_navigation_and_marker_list_selection_stay_in_sync tests/browser/test_browser_interactions.py::test_marker_badge_drag_keeps_motion_path_intact_when_editing_base_point tests/browser/test_browser_interactions.py::test_marker_template_controls_drive_new_shot_marker_defaults tests/browser/test_browser_interactions.py::test_marker_motion_toggle_keeps_current_marker_selected tests/browser/test_browser_remaining_controls_e2e.py::test_markers_template_toggle_and_popup_bubble_authoring_controls_commit_state -q`
