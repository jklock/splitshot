# Browser Test Coverage Reference

This document provides a test-by-test coverage breakdown for the primary browser E2E and interaction suites.

For each test, this reference answers:
- What behavior the test validates.
- Which concrete controls/selectors/buttons are exercised.
- Which functions/state paths are asserted.
- Which persistence/export/download behaviors are validated.

Scope of this reference:
- tests/browser/test_browser_remaining_controls_e2e.py
- tests/browser/test_settings_defaults_truth_gate.py
- tests/browser/test_browser_full_app_e2e.py
- tests/browser/test_settings_e2e.py
- tests/browser/test_metrics_e2e.py
- tests/browser/test_browser_interactions.py

## Coverage Legend

- Control surface: concrete UI controls used by the test (ID selectors, data attributes, key classes).
- State/function assertions: key JS functions or state paths explicitly checked by predicates.
- Artifact/persistence: reload, save/open, export payload, preview parity, or download behavior.

---

## tests/browser/test_browser_remaining_controls_e2e.py

### Helper Abstractions

- _open_test_page: launches browser page and navigates to app URL.
- _load_primary_video: sets #primary-file-input and waits for waveform shot cards.
- _open_tool: routes using button[data-tool="..."] and verifies activeTool.
- _set_input_value: writes control values with input/change events.
- _set_checkbox: toggles checkbox controls with change events.
- _ensure_overlay_visible: enables overlay if hidden.
- _select_visible_shot: selects a timing row and returns selected shot metadata.
- _ensure_popup_card_open: expands popup cards when collapsed.
- _ensure_text_box_card_open: expands review text-box card editors.
- _popup_state: reads popup object from state.project.popups.

### test_waveform_shell_remaining_controls_and_workbench_toggles_survive_routes

- Validates: waveform zoom/amplitude/reset controls and timing/scoring workbench expansion survive route switching.
- Control surface:
  - #expand-waveform
  - #zoom-waveform-in, #zoom-waveform-out
  - #amp-waveform-in, #amp-waveform-out
  - #reset-waveform-view
  - #expand-timing, #collapse-timing
  - #expand-scoring, #collapse-scoring
- State/function assertions:
  - waveformZoomX, waveformOffsetMs
  - waveformShotAmplitudeById
  - state.project.ui_state.timing_expanded
  - scoringWorkbenchExpanded
  - activeTool
- Artifact/persistence:
  - Expansion state remains valid after tool routing.

### test_markers_template_toggle_and_popup_bubble_authoring_controls_commit_state

- Validates: popup template enable and full bubble authoring pipeline commit state correctly.
- Control surface:
  - #popup-template-enabled
  - #popup-import-shots
  - data-popup-field controls: name, content_type, text, image_path, image_scale_mode, anchor_mode, shot_id, duration_s, x, y, width, height, quadrant, follow_motion
  - data-popup-action controls: browse_image, add_keyframe, prev_keyframe, next_keyframe, copy_motion_prev, apply_motion_visible, clear_motion_path
- State/function assertions:
  - state.project.popups[] field updates
  - selectedPopupKeyframeOffsetMs
  - sortedPopupBubblesForTimeline
  - follow_motion and motion_path propagation
- Artifact/persistence:
  - Captured popup snapshot proves authored state is fully committed.

### test_review_text_box_style_controls_and_color_picker_modal_commit_preview

- Validates: review text-box text, color picker interactions, and preview color rendering.
- Control surface:
  - #review-add-text-box
  - textarea[data-text-box-field="text"]
  - button[data-text-box-field="text_color"]
  - #color-picker-hex
  - #close-color-picker
  - #custom-overlay [data-text-box-id]
- State/function assertions:
  - state.project.overlay.text_boxes[].text
  - state.project.overlay.text_boxes[].text_color
  - activeColorPickerControl/modal visibility
  - computed style color on rendered badge
- Artifact/persistence:
  - Live overlay preview reflects selected color values.

### test_overlay_badge_style_grid_applies_timer_shot_current_and_score_styles

- Validates: badge style grid updates timer/shot/current-shot styling and font behavior.
- Control surface:
  - #show-timer, #show-shots, #show-score
  - #overlay-font-family
  - #badge-style-grid .style-card[data-badge]
  - badge background/text/opacity inputs
- State/function assertions:
  - state.project.overlay badge style objects
  - renderLiveOverlay
  - #live-overlay .timer-badge and .shot-badge styles
- Artifact/persistence:
  - Live overlay rendered styles match configured control values.

### test_merge_remaining_controls_commit_default_and_per_source_state

- Validates: merge defaults and per-source controls, sync nudges, and source removal.
- Control surface:
  - #merge-media-input
  - #merge-enabled
  - #merge-layout
  - #pip-size, #pip-x, #pip-y
  - .merge-media-card controls for size/opacity/x/y
  - per-card sync buttons (-10/-1/+1/+10)
  - [data-merge-source-remove]
- State/function assertions:
  - state.project.merge.layout/enabled
  - state.project.merge_sources[] pip_size_percent/opacity/pip_x/pip_y/sync_offset_ms
- Artifact/persistence:
  - Source collection updates correctly after removal.

### test_export_remaining_encoding_controls_drive_export_payload

- Validates: export UI controls map to export payload used for render.
- Control surface:
  - #quality, #aspect-ratio
  - #target-width, #target-height
  - #frame-rate
  - #video-codec, #video-bitrate
  - #audio-codec, #audio-sample-rate, #audio-bitrate
  - #color-space, #ffmpeg-preset, #two-pass
  - #export-path, #export-video
- State/function assertions:
  - Export payload values captured from mocked export path
  - state.project.export output path/log state
- Artifact/persistence:
  - Payload contract is explicitly validated field-by-field.

### test_shotml_remaining_numeric_controls_commit_from_browser

- Validates: remaining SHOTML controls commit into analysis settings.
- Control surface:
  - [data-shotml-section="threshold"] toggle
  - [data-shotml-setting] controls across numeric/select/checkbox inputs
- State/function assertions:
  - state.project.analysis.shotml_settings keys and values
- Artifact/persistence:
  - Control changes survive route-level interaction and settle in project analysis state.

### test_shotml_section_toggles_persist_routes_and_proposal_actions_apply_or_discard

- Validates: SHOTML section expansion persistence and proposal apply/discard behavior.
- Control surface:
  - [data-shotml-section] + [data-section-toggle]
  - .shotml-proposal-row buttons (Apply/Discard)
- State/function assertions:
  - state.project.analysis.timing_change_proposals[].status
  - state.project.analysis.shots[].time_ms
- Artifact/persistence:
  - Applied proposal mutates timing; discarded proposal preserves timing.

---

## tests/browser/test_settings_defaults_truth_gate.py

### Helper Abstractions

- _open_settings: routes to settings tool and waits for visible pane.
- _expand_settings_section: opens collapsed settings section.
- _set_control: typed setter for checkbox/select/input controls.
- _set_project_path: sets #project-path with events.
- _apply_settings_defaults_and_wait: applies defaults and waits for postcondition.

### test_settings_defaults_seed_fresh_project_overlay_marker_export_pip_and_shotml_state

- Validates: settings defaults seed new project for overlay/marker/export/pip/shotml.
- Control surface:
  - Settings sections: pip, overlay, markers, export, shotml
  - controls including default pip size/coords, overlay colors/opacities/badges, marker template defaults, export codec/preset/two-pass, shotml threshold
- State/function assertions:
  - applySettingsDefaults
  - readSettingsDefaultsPayload
  - createNewProject
  - state.settings and state.project defaults snapshots
- Artifact/persistence:
  - Fresh project starts with seeded defaults.

### test_settings_landing_pane_and_reopen_last_tool_apply_after_reload

- Validates: landing pane and reopen-last-tool influence post-reload active tool.
- Control surface:
  - #settings-scope
  - #settings-default-tool
  - #settings-reopen-last-tool
- State/function assertions:
  - applySettingsDefaults
  - activeTool after create/reload cycles
- Artifact/persistence:
  - Reload behavior matches configured default/open logic.

### test_settings_scope_separates_app_and_folder_defaults_for_new_projects

- Validates: folder-scoped defaults can diverge from app-scoped defaults.
- Control surface:
  - #settings-scope (app then folder)
  - #settings-default-tool
- State/function assertions:
  - applySettingsDefaults
  - useProjectFolder
  - activeTool in each folder context
- Artifact/persistence:
  - Distinct projects observe expected scope-specific defaults.

---

## tests/browser/test_browser_full_app_e2e.py

### Helper Abstractions

- _exercise_shell_routing: opens each major rail tool and validates active routing.
- _exercise_waveform_and_timing: performs waveform/timing edits and event creation.
- _exercise_markers_review_overlay: marker import/editor actions plus review/overlay changes.
- _exercise_merge_and_export: merge source configuration and export control wiring.
- _exercise_settings_and_shotml: settings defaults controls plus shotml threshold reset flow.

### test_browser_full_app_e2e_calls_surface_workflows

- Validates: full end-to-end cross-surface workflow across all primary browser tools.
- Control surface:
  - Major tool rail buttons and each pane-specific controls
- State/function assertions:
  - Aggregated state transitions across timing, markers, review, overlay, merge, export, settings, shotml
- Artifact/persistence:
  - End-to-end workflow executes with no broken control paths.

### test_browser_full_app_practiscore_timing_scoring_save_reload_persistence_truth_gate

- Validates: PractiScore ingest plus timing/scoring save-reload persistence path.
- Control surface:
  - #practiscore-file-input
  - scoring and timing tool controls
- State/function assertions:
  - state.project.scoring stage fields
  - timing/scoring state after reopen
- Artifact/persistence:
  - Project reopen preserves imported scoring context and edits.

### test_browser_full_app_markers_review_overlay_export_preview_parity_truth_gate

- Validates: markers/review/overlay changes remain coherent through export flow.
- Control surface:
  - Marker controls, review text-box controls, overlay style controls, export controls
- State/function assertions:
  - state.project.popups
  - state.project.overlay.text_boxes
- Artifact/persistence:
  - Preview/export flow parity for authored overlays/markers.

### test_browser_full_app_merge_export_sync_truth_gate

- Validates: merge settings survive and drive export in truth-gate workflow.
- Control surface:
  - Merge enable/layout/source controls + export controls
- State/function assertions:
  - state.project.merge.layout and related source state
- Artifact/persistence:
  - Export path observes merge configuration.

### test_browser_full_app_settings_defaults_seed_fresh_project_truth_gate

- Validates: settings defaults path seeds a freshly created project in full-app flow.
- Control surface:
  - Settings defaults controls
  - project creation controls
- State/function assertions:
  - createNewProject
  - state.project.analysis.shotml_settings baseline presence
- Artifact/persistence:
  - Defaults survive fresh create + reload cycle.

### test_browser_full_app_shotml_rerun_apply_or_discard_truth_gate

- Validates: shotml threshold, manual nudge, proposal generation, apply/discard behaviors.
- Control surface:
  - #threshold, #apply-threshold
  - timing nudge buttons
  - proposal Apply/Discard buttons
- State/function assertions:
  - detection_threshold in shotml settings
  - state.project.analysis.timing_change_proposals status
  - shot.time_ms transitions for apply/discard
- Artifact/persistence:
  - Truth-gate proposal semantics are preserved end-to-end.

---

## tests/browser/test_settings_e2e.py

### Helper Abstractions

- _settings_section_selector: stable selector builder for settings sections.
- _expand_settings_section: robust section open helper.
- _set_settings_control: typed control setter for settings values.
- _apply_settings_defaults_and_wait: apply defaults then wait for exact predicate.

### test_settings_section_toggles_survive_tool_route_changes

- Validates: settings section collapse/expand states survive leaving and returning to settings.
- Control surface:
  - [data-settings-section] and [data-section-toggle]
  - tool route buttons (project/timing/settings)
- State/function assertions:
  - section classList collapsed state
  - activeTool route checks
- Artifact/persistence:
  - intra-session route resilience for settings UI state.

### test_settings_import_current_and_reset_defaults_round_trip_visible_project_defaults

- Validates: importing current project defaults and reset-defaults round trip values.
- Control surface:
  - #settings-import-current
  - #settings-reset-defaults
  - merge/export controls used to produce current state
- State/function assertions:
  - state.settings merge/export defaults
  - state.project merge/export values after reset
- Artifact/persistence:
  - Round-trip default import/reset contracts stay intact.

### test_settings_global_template_fields_update_defaults_state_and_reset

- Validates: global-template fields update settings and reset returns expected values.
- Control surface:
  - #settings-default-tool
  - #settings-reopen-last-tool
- State/function assertions:
  - state.settings.default_tool
  - state.settings.reopen_last_tool
- Artifact/persistence:
  - Reset-defaults path restores project baseline tool behavior.

### test_settings_default_controls_commit_to_settings_state_and_reset

- Validates: default match type, pip size, export quality, two-pass commit and reset.
- Control surface:
  - #settings-default-match-type
  - #settings-pip-size
  - #settings-export-quality
  - #settings-export-two-pass
- State/function assertions:
  - state.settings field values before/after reset
- Artifact/persistence:
  - Commit/reset behavior for core defaults remains deterministic.

### test_settings_remaining_defaults_commit_and_reset_all_panels

- Validates: extended defaults across pip/export/overlay panels commit/reset correctly.
- Control surface:
  - #settings-merge-layout
  - #settings-export-preset/frame-rate/video-codec/ffmpeg-preset/two-pass
  - #settings-overlay-position, #settings-badge-size
  - overlay custom and badge color/opacity controls
  - #settings-reset-defaults
- State/function assertions:
  - broad settings defaults state coverage across panel families
- Artifact/persistence:
  - no stale defaults survive reset-defaults across the expanded settings surface.

---

## tests/browser/test_metrics_e2e.py

### Helper Abstractions

- _open_scoring_workbench / _open_timing_workbench / _open_metrics_pane: route and expand each workbench pane.
- _select_scoring_preset_with_penalties: picks a preset with live penalty fields.
- _metrics_table_rows / _metrics_row_for_shot: table extraction utilities for row-level assertions.
- _metrics_summary_values: summary-card extraction for aggregate assertions.

### test_metrics_pane_reflects_scoring_workbench_edits_and_restore

- Validates: scoring edits and restore flow propagate to metrics rows.
- Control surface:
  - #expand-scoring
  - scoring row .lock-button
  - select[data-score-field="letter"]
  - restore button
- State/function assertions:
  - state.timing_segments score_letter
  - metrics row correspondence by shot id
- Artifact/persistence:
  - Metrics table remains downstream-consistent with scoring edits.

### test_metrics_pane_reflects_timing_event_position_and_delete

- Validates: timing event insertion/deletion appears in metrics table actions context.
- Control surface:
  - #timing-event-kind
  - #timing-event-label
  - #timing-event-position
  - #add-timing-event
  - remove timing event button
- State/function assertions:
  - state.project.analysis.events
  - metrics table text includes/excludes event label
- Artifact/persistence:
  - Metrics view tracks timing-event lifecycle accurately.

### test_selected_shot_nudge_and_delete_propagate_to_metrics

- Validates: nudge and delete selected shot update metrics row and summary counts.
- Control surface:
  - timing row selection
  - button[data-nudge="10"]
  - #delete-selected
- State/function assertions:
  - state.project.analysis.shots
  - selectedShotId
  - shot.time_ms
- Artifact/persistence:
  - Metrics summary "Shots" decrements after delete.

### test_metrics_export_buttons_download_current_metrics_context

- Validates: metrics CSV/TXT export downloads include current event and table context.
- Control surface:
  - #metrics-export-csv
  - #metrics-export-text
- State/function assertions:
  - current metrics table content includes event labels
- Artifact/persistence:
  - download file names/suffixes and content structure are validated.

---

## tests/browser/test_browser_interactions.py

### Helper Abstractions

- _open_tool: deterministic tool routing helper.
- _select_waveform_shot: select shot by timing row and return source metadata.
- _shot_linked_popup_count / _import_shot_linked_markers: marker population helpers.
- _ensure_overlay_visible: robust overlay enable helper.

### Waveform and Navigation Interactions

#### test_waveform_controls_expand_zoom_and_amplitude_update_project_state

- Validates: waveform zoom/amplitude modes and reset behavior.
- Controls:
  - #expand-waveform
  - #zoom-waveform-in/out
  - #amp-waveform-in/out
  - button[data-waveform-mode="add"], button[data-waveform-mode="select"]
  - #reset-waveform-view
- State/assertions:
  - waveformZoomX, waveformOffsetMs, waveformShotAmplitudeById, waveformMode
  - localStorage waveform values

#### test_waveform_pan_drag_updates_zoomed_viewport_offset

- Validates: panning in zoomed waveform updates viewport offset.
- Controls:
  - waveform drag surface
- State/assertions:
  - waveformOffsetMs changes after drag

#### test_waveform_shot_drag_moves_selected_shot_time

- Validates: dragging a shot marker updates shot timing.
- Controls:
  - waveform shot drag target
- State/assertions:
  - shot.time_ms changes for selected shot

#### test_waveform_viewport_window_drag_persists_after_reload

- Validates: viewport window drag persists through reload.
- Controls:
  - waveform viewport window/handle drag
- State/assertions:
  - persisted waveform offset values and restored viewport state

### Overlay, Review, and Marker Controls

#### test_overlay_visibility_and_badge_toggles_round_trip_through_browser_ui

- Validates: show/hide overlay badges and round-trip state.
- Controls:
  - #show-overlay, #show-timer, #show-draw, #show-shots, #show-score
- State/assertions:
  - state.project.overlay visibility flags

#### test_review_add_custom_text_box_creates_editor_card

- Validates: creating review custom text box creates editable card.
- Controls:
  - #review-add-text-box
- State/assertions:
  - text box list count increment

#### test_review_text_box_drag_updates_overlay_coordinates

- Validates: text-box drag mutates x/y coordinates.
- Controls:
  - review card and #custom-overlay drag element
- State/assertions:
  - state.project.overlay.text_boxes coordinates differ post-drag

#### test_review_text_box_color_swatches_and_opacity_update_live_preview

- Validates: text-box background/text colors and opacity update state and preview.
- Controls:
  - color swatches, #color-picker-hex, opacity input
- State/assertions:
  - box.background_color, box.text_color, box.opacity
  - computed style reflects expected RGB

#### test_review_text_box_source_switches_to_imported_summary_and_renders_after_final_shot

- Validates: imported_summary source behavior and after-final visibility.
- Controls:
  - source select, text override field
- State/assertions:
  - box.source, box.quadrant
  - rendered overlay visibility after final shot time

#### test_review_text_box_custom_position_size_and_stack_lock_update_state_and_stage

- Validates: custom geometry and lock-to-stack behavior.
- Controls:
  - quadrant/x/y/width/height/lock_to_stack controls
- State/assertions:
  - box geometry fields
  - lock disables direct placement controls
  - rendered geometry matches configured values

#### test_markers_import_shots_select_selected_marker_and_seek_video

- Validates: marker import aligns with selected shot and seek behavior.
- Controls:
  - #popup-import-shots
  - shot-linked marker list and timeline bars
- State/assertions:
  - selectedPopupBubbleId ties to selected shot marker
  - video current time matches selected marker shot time

#### test_marker_collapsed_navigation_and_timeline_bar_select_visible_markers

- Validates: collapsed marker authoring nav and timeline selection.
- Controls:
  - #popup-toggle-authoring
  - #popup-next-compact / #popup-prev-compact
  - popup timeline bar buttons
- State/assertions:
  - selectedPopupBubbleId changes as expected

#### test_marker_shot_editor_steps_duplicate_delete_and_close

- Validates: shot editor previous/next/duplicate/delete/done flow.
- Controls:
  - #popup-open-shot-editor
  - #popup-shot-editor-prev/next/duplicate/delete/done
- State/assertions:
  - popup counts and selected popup transitions

#### test_marker_template_controls_drive_new_shot_marker_defaults

- Validates: template controls define defaults for new shot-linked markers.
- Controls:
  - #popup-template-text-source/content-type/duration/quadrant/width/height/follow-motion
  - #popup-add-bubble
- State/assertions:
  - new popup fields inherit template settings

#### test_marker_play_window_and_loop_controls_follow_selected_marker_window

- Validates: marker play window and loop controls enforce visible playback interval.
- Controls:
  - #popup-play-window
  - #popup-loop-window
- State/assertions:
  - popupPlaybackWindow state
  - video play/pause/currentTime transitions

#### test_time_marker_list_cards_select_marker_and_seek_video

- Validates: time marker cards select and seek correctly.
- Controls:
  - time-marker cards in list
- State/assertions:
  - selectedPopupBubbleId
  - video current time aligns with marker time

#### test_popup_bubble_enabled_checkbox_hides_and_restores_live_badge

- Validates: popup enabled checkbox toggles rendered overlay badge visibility.
- Controls:
  - input[data-popup-field="enabled"]
- State/assertions:
  - bubble.enabled
  - badge present/absent in #popup-overlay

#### test_popup_bubble_card_actions_toggle_duplicate_and_remove_markers

- Validates: card toggle/duplicate/remove actions and timeline rerender coherence.
- Controls:
  - data-popup-action="toggle"/"duplicate"/"remove"
- State/assertions:
  - popup collection count and selected popup behavior

### SHOTML and Merge/Export Interactions

#### test_shotml_threshold_apply_and_reset_defaults_update_project_analysis

- Validates: threshold apply and reset-defaults in SHOTML panel.
- Controls:
  - #threshold, #apply-threshold, #reset-shotml-defaults
- State/assertions:
  - project analysis detection threshold values

#### test_shotml_settings_controls_commit_and_reset_defaults_update_project_analysis

- Validates: broad SHOTML control set commits and resets as a group.
- Controls:
  - [data-shotml-setting] controls
  - #reset-shotml-defaults
- State/assertions:
  - state.project.analysis.shotml_settings matches mutated and reset snapshots

#### test_merge_controls_update_live_preview_layout_and_position

- Validates: merge layouts and PiP source controls update preview positioning and size.
- Controls:
  - #merge-media-input, #merge-enabled, #merge-layout
  - source-level size/x/y controls
- State/assertions:
  - merge layout state
  - preview item styles (left/top/width/height)

#### test_merge_default_pip_controls_commit_to_state_and_label

- Validates: default PiP controls commit and label updates.
- Controls:
  - #pip-size, #pip-x, #pip-y, #pip-size-label
- State/assertions:
  - state.project.merge pip_size_percent/x/y

#### test_overlay_color_picker_updates_timer_badge_preview_and_reopens_with_selected_hex

- Validates: overlay badge color-picker modal updates and re-open selected color state.
- Controls:
  - timer badge color swatch in #badge-style-grid
  - #color-picker-hue, #color-picker-saturation, #color-picker-lightness
  - #color-picker-hex
  - #close-color-picker
- State/assertions:
  - state.project.overlay.timer_badge.background_color
  - modal target/current/hex values and live preview color

#### test_overlay_badge_position_controls_update_state_and_persist

- Validates: timer/draw/score position controls and stack-lock interactions.
- Controls:
  - timer/draw/score x/y controls and lock checkboxes
- State/assertions:
  - position and lock values in overlay state
  - control enabled/disabled behavior

#### test_overlay_font_controls_apply_to_timer_badge_and_bubble_size_override

- Validates: font family/size/bold/italic and bubble size controls.
- Controls:
  - #overlay-font-family, #overlay-font-size
  - #overlay-font-bold, #overlay-font-italic
  - #bubble-width, #bubble-height
- State/assertions:
  - overlay font and size fields
  - rendered timer badge typography styles

#### test_export_log_modal_opens_closes_backdrop_and_downloads_last_log

- Validates: export log modal open/close/backdrop/download behavior.
- Controls:
  - #show-export-log
  - #close-export-log
  - #export-export-log
- State/assertions:
  - export log modal visibility transitions
- Artifact/persistence:
  - exported log file download with expected content/suffix

#### test_export_controls_update_preset_and_settings_state

- Validates: export preset and detailed export controls commit to state.
- Controls:
  - export preset/quality/aspect/codec/bitrate/frame-rate/color-space/two-pass/path controls
- State/assertions:
  - state.project.export values reflect control updates

#### test_scoring_workbench_rows_lock_edit_delete_and_restore

- Validates: scoring workbench lock/edit/delete/restore row actions.
- Controls:
  - scoring row lock button
  - score letter select
  - penalty inputs
  - delete and restore actions
- State/assertions:
  - state.timing_segments and analysis shot list transitions

---

## Coverage Totals for This Reference

- Files documented: 6
- Tests documented: 46
- Dominant surfaces covered:
  - Waveform and timing editing
  - Markers/review/overlay authoring and rendering
  - Merge/PiP/export control contracts
  - Settings defaults/scoping and truth-gate seeding
  - SHOTML tuning and proposal actions
  - Metrics downstream propagation and exports

## Notes

- This file documents test intent and covered surfaces; it is not a replacement for reading assertions directly in the test source.
- For broader non-E2E/contract coverage (including server API/unit-heavy browser-control tests), use tests/browser/test_browser_control.py and related contract files as the next reference layer.
