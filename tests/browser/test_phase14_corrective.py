"""Corrective assertions for pane ownership, media workflow, queue routing, and review formatting.

Phase 16D updated for restored match-context ownership in Project, backend-driven media dialogs,
queue filtering, and full workflow proof.
"""

from __future__ import annotations

from pathlib import Path

STATIC_ROOT = Path("src/splitshot/browser/static")


# ---------------------------------------------------------------------------
# V107-1400 — Project context ownership (RESTORED)
# ---------------------------------------------------------------------------


def test_project_has_practiscore_competitor_selectors():
    html = (STATIC_ROOT / "index.html").read_text()
    assert 'id="match-competitor-name"' in html
    assert 'id="match-competitor-place"' in html
    assert 'id="match-class"' in html
    assert 'id="match-division"' in html


def test_project_does_not_render_stage_number_in_project_pane():
    source = (STATIC_ROOT / "panes" / "project-pane.js").read_text()
    within = source[
        source.index("readPractiScoreContextPayload") : source.index(
            "readPractiScoreContextPayload"
        )
        + 500
    ]
    assert "stage_number" not in within


def test_project_practiscore_functions_are_implemented():
    source = (STATIC_ROOT / "panes" / "project-pane.js").read_text()
    assert "ensurePractiScoreSelectionControls" in source
    assert "renderPractiScoreSelect" in source
    assert "renderPractiScoreOptionLists" in source
    assert "syncPractiScoreSelectionFields" in source
    assert "match-competitor-name" in source
    assert "match-competitor-place" in source
    assert "match-class" in source
    assert "match-division" in source


def test_project_reads_classification_and_division_in_payload():
    source = (STATIC_ROOT / "panes" / "project-pane.js").read_text()
    within = source[
        source.index("readPractiScoreContextPayload") : source.index(
            "readPractiScoreContextPayload"
        )
        + 500
    ]
    assert "classification" in within
    assert "division" in within


def test_practiscore_context_payload_includes_classification_and_division():
    source = (STATIC_ROOT / "panes" / "project-pane.js").read_text()
    within = source[
        source.index("readPractiScoreContextPayload") : source.index(
            "readPractiScoreContextPayload"
        )
        + 500
    ]
    assert "classification" in within
    assert "division" in within
    assert "match-class" in source
    assert "match-division" in source


def test_controller_set_practiscore_context_accepts_classification_division():
    source = Path("src/splitshot/ui/controller.py").read_text()
    within = source[
        source.index("def set_practiscore_context") : source.index("def set_practiscore_context")
        + 2000
    ]
    assert "classification" in within
    assert "division" in within


def test_server_practiscore_context_passes_classification_division():
    source = Path("src/splitshot/browser/server.py").read_text()
    within = source[
        source.index("def _set_practiscore_context") : source.index("def _set_practiscore_context")
        + 2000
    ]
    assert "classification" in within
    assert "division" in within


def test_scoring_state_has_classification_division_fields():
    source = Path("src/splitshot/domain/models.py").read_text()
    within = source[source.index("class ScoringState") : source.index("class ScoringState") + 800]
    assert "classification" in within
    assert "division" in within


def test_scoring_from_dict_handles_classification_division():
    source = Path("src/splitshot/domain/models.py").read_text()
    within = source[
        source.index("def _scoring_from_dict") : source.index("def _scoring_from_dict") + 1000
    ]
    assert "classification" in within
    assert "division" in within


def test_project_summary_line_is_removed_but_container_remains():
    source = (STATIC_ROOT / "panes" / "project-pane.js").read_text()
    within = source[
        source.index("renderPractiScoreImportSummary") : source.index(
            "renderPractiScoreImportSummary"
        )
        + 1500
    ]
    assert "practiscore-import-summary" in within
    assert 'summary.textContent = ""' in within
    assert "summary.hidden = true" in within
    assert "John Klockenkemper" not in within


def test_project_does_not_own_stage_media():
    source = (STATIC_ROOT / "panes" / "project-pane.js").read_text()
    start = source.index("renderPractiScoreImportSummary")
    within = source[start : start + 1200]
    assert "primary_media" not in within
    assert "added_media" not in within
    assert "file_intake" not in within.lower()


def test_project_owns_output_root_control():
    html = (STATIC_ROOT / "index.html").read_text()
    assert 'id="project-output-root"' in html
    assert 'id="browse-project-output-root"' in html


# ---------------------------------------------------------------------------
# V107-1410 — Media stage-first workflow
# ---------------------------------------------------------------------------


def test_media_pane_uses_flat_og_sections():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "media-section-toggle" in source
    assert "sectionExpanded" in source
    assert "Active Stage" not in source
    assert "media-active-stage-label" in source
    assert "<strong>Primary Media</strong>" in source
    assert "<strong>Secondary Media</strong>" in source


def test_media_pane_uses_backend_dialog_not_file_inputs():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "pickPath" in source
    assert 'callApi("/api/project/stage/import-primary"' in source
    assert 'callApi("/api/project/stage/import-added"' in source


def test_media_pane_has_file_rows_with_primary_badge():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "media-asset-row" in source
    assert "media-set-primary-btn" in source
    assert "media-remove-file-btn" in source
    assert "renderInventoryFileRow" in source


def test_media_pane_uses_real_set_primary_route():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert 'callApi("/api/project/stage/set-primary"' in source


def test_media_pane_has_add_more_and_create_stage():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "media-add-more-btn" in source
    assert "media-add-stage-btn" in source
    assert 'class="btn-sm media-add-stage-btn"' in source
    assert "Add Media" in source
    assert 'callApi("/api/project/stage/create"' in source


def test_media_pane_has_stage_name_edit_not_competitor_edits():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "media-save-stage-btn" in source
    assert "competitor_name" not in source.lower()
    assert "competitor_place" not in source.lower()


def test_media_pane_has_no_filler_copy():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "pane-flow-hint" not in source


def test_media_file_rows_use_asset_meta():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "assetMeta" in source
    assert "assetTypeLabel" in source


def test_media_pane_has_no_inventory_wrapper_or_count_chips():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "splitshot.media.sectionExpanded" in source
    assert "pane-summary-token" not in source
    assert "<strong>Stages</strong>" not in source


def test_media_pane_locks_stage_mutations_while_an_import_is_pending():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "mediaMutationPending" in source
    assert "runMediaMutation" in source
    assert 'pane.setAttribute("aria-busy"' in source
    assert 'mediaMutationPending ? "disabled" : ""' in source


# ---------------------------------------------------------------------------
# V107-1420 — Queue routing, filtering, filler removal, Compose overlap
# ---------------------------------------------------------------------------


def test_media_inventory_uses_active_stage_selector_only():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "renderActiveStageSection" in source
    assert "renderStagesSection" in source
    assert "Primary Media" in source
    assert "Secondary Media" in source
    assert "renderInventoryFileRow" in source
    assert "Stage Navigator" not in source
    assert "data-stage-nav-id" not in source


def test_media_active_stage_is_not_collapsible_and_does_not_queue():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    active_section = source[
        source.index("function renderActiveStageSection") : source.index(
            "function renderStagesSection"
        )
    ]
    assert "pane-toggle" not in active_section
    assert "Queue Stage" not in source
    assert "Requeue" not in source
    assert "/api/project/queue/" not in source


def test_media_picker_root_is_fixed_to_project_input():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    within = source[
        source.index("function mediaPickerDefaultRoot") : source.index("function selectStage")
    ]
    assert "stage?.primary_media?.path" not in within
    assert "stageAddedMedia(stage)[0]" not in within
    assert 'joinProjectPath(projectPath, "Input")' in within
    assert "projectPath ||" in within


def test_queue_has_no_filler_copy():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "pane-flow-hint" not in source


def test_queue_visible_entries_excludes_not_queued():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    within = source[source.index("visibleQueueEntries") : source.index("visibleQueueEntries") + 500]
    assert 'status !== "not_queued"' in within


def test_queue_stale_label_exists():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert 'stale: "Stale"' in source


def test_queue_has_no_stage_toggles():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "queue-stage-toggle" not in source
    assert "isStageExpanded" not in source
    assert "toggleStage" not in source


def test_queue_has_no_persisted_expansion_state():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "splitshot.queue.stageExpanded" not in source
    assert "localStorage" not in source


def test_export_drops_output_path_browser_controls():
    html = (STATIC_ROOT / "index.html").read_text()
    assert 'id="export-path"' not in html
    assert 'id="browse-export-path"' not in html


# ---------------------------------------------------------------------------
# V107-1430 — Review summary denominator formatting
# ---------------------------------------------------------------------------


def test_formatPlacement_uses_denominator():
    source = (STATIC_ROOT / "panes" / "review-pane.js").read_text()
    start = source.index("function formatPlacement")
    within = source[start : start + 600]
    assert "${numericPlace}/${numericTotal}" in within
    assert "String(numericPlace)" in within


def test_formatPlacement_has_no_hash_format():
    source = (STATIC_ROOT / "panes" / "review-pane.js").read_text()
    within = source[source.index("formatPlacement") : source.index("formatPlacement") + 400]
    assert "#" not in within


def test_review_metric_value_wires_placement_dimensions():
    source = (STATIC_ROOT / "panes" / "review-pane.js").read_text()
    within = source[source.index("reviewMetricValue") :]
    assert "overall_placement" in within
    assert "division_placement" in within
    assert "class_placement" in within
    assert 'case "division_class_placement"' not in within
    assert "formatPlacement" in within


def test_review_passes_denominator_to_supported_placement_fields():
    source = (STATIC_ROOT / "panes" / "review-pane.js").read_text()
    within = source[source.index("reviewMetricValue") :]
    assert "formatPlacement(groups.overall.place, groups.overall.items.length)" in within
    assert "formatPlacement(groups.division.place, groups.division.items.length)" in within
    assert "formatPlacement(groups.class.place, groups.class.items.length)" in within
    assert "formatPlacement(groups.divisionClass.place" not in within


def test_review_uses_final_standings_and_defaults_to_actual_three_cohorts():
    source = (STATIC_ROOT / "panes" / "review-pane.js").read_text()
    assert "buildFinalStandingsComparison" in source
    assert "DEFAULT_SUMMARY_METRIC_IDS" in source
    default_block = source[
        source.index("DEFAULT_SUMMARY_METRIC_IDS") : source.index("DEFAULT_SUMMARY_METRIC_IDS")
        + 300
    ]
    assert '"overall_placement"' in default_block
    assert '"division_class_placement"' not in default_block
    assert "buildCompetitionComparison" not in source


def test_review_uses_generic_selectors_and_actual_sport_identity_in_output():
    source = (STATIC_ROOT / "panes" / "review-pane.js").read_text()
    assert "competitionIdentityLabels" in source
    assert 'label: "Division"' in source
    assert 'outputLabel: identity.division || "Division"' in source
    assert 'label: "Class"' in source
    assert 'outputLabel: identity.classification || "Class"' in source
    assert '{ id: "overall_placement", label: "Overall", separator: " - " }' in source
    assert '`${def.outputLabel || def.label}${def.separator || " "}${value}`' in source
    assert 'label: "Division + Class Placement"' not in source


def test_metrics_uses_actual_standings_and_compact_sport_labels():
    source = (STATIC_ROOT / "panes" / "metrics-pane.js").read_text()
    assert "buildFinalStandingsComparison" in source
    assert "competitionIdentityLabels" in source
    assert "`${label} - ${cohort.place}/${cohort.count}`" in source
    assert "Division Placement" not in source
    assert "Class Placement" not in source
    assert "Classification Placement" not in source


def test_practiscore_file_import_uses_backend_match_type_inference():
    source = (STATIC_ROOT / "lib" / "shell-runtime.js").read_text()
    start = source.index('$("practiscore-file-input").addEventListener("change"')
    within = source[start : start + 700]
    assert 'postFile("/api/files/practiscore"' in within
    assert "readPractiScoreMatchSelection" not in within
    assert "match_type:" not in within


def test_trim_bulk_actions_send_the_explicit_selected_stage_ids():
    source = (STATIC_ROOT / "panes" / "trim-sync-pane.js").read_text()
    assert "selectedTrimStageIds" in source
    assert 'id="trim-stage-select-all"' in source
    assert 'id="trim-stage-clear"' in source
    assert "data-trim-stage-id" in source
    assert "stage_ids: stageIds" in source


def test_review_summary_uses_imported_score_time_raw_time_and_penalties():
    source = (STATIC_ROOT / "panes" / "review-pane.js").read_text()
    within = source[source.index("function reviewMetricValue") :]
    assert "imported.final_time" in within
    assert "imported.raw_seconds ?? summary.raw_seconds" in within
    assert "summary.total_penalties ?? imported.shot_penalties" in within


def test_badge_opacity_field_removes_stepper_space_and_keeps_suffix_gap():
    source = (STATIC_ROOT / "styles" / "panes.css").read_text()
    start = source.index("#badge-style-grid .badge-style-card .opacity-percent-input")
    within = source[start : start + 1200]
    assert "padding: var(--space-1) 0.75rem" in within
    assert "text-align: left" in within
    assert "grid-template-columns: minmax(76px, 1fr) auto" in within
    assert "gap: 12px" in within


def test_queue_uses_compact_stage_cards():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "queue-stage-card" in source
    assert "queue-status-text" in source
    assert "queue-status-pill" not in source
    assert "Queue Controls" not in source
    assert "<strong>${stageLabel(stage)}</strong>" in source
    assert "Match Stages" in source


def test_queue_owns_membership_actions_without_edit_or_remove():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "queue-membership-btn" in source
    assert '"Queue"' in source
    assert '"Requeue"' in source
    assert '"Unqueue"' in source
    assert "Edit Stage" not in source
    assert "Remove" not in source


def test_trim_uses_source_cards_and_bulk_sections():
    source = (STATIC_ROOT / "panes" / "trim-sync-pane.js").read_text()
    assert "trim-source-card" in source
    assert "trim-global-row" in source
    assert "trim-card-row" in source
    assert "trim-sync-nudge-buttons" in source
    assert "computedTrimLabel" in source
    assert ">Undo<" in source
    assert "trim-undo-btn" in source
    assert "setStatus" in source


def test_waveform_renderer_declares_lane_clipping():
    source = (STATIC_ROOT / "components" / "waveform.js").read_text()
    assert 'canvas.dataset.waveformLaneClipping = "isolated"' in source
    assert 'canvas.dataset.waveformLaneBleed = "false"' in source
    assert 'canvas.dataset.waveformTimeScaleVisible = "true"' in source
    assert "ctx.clip();" in source


def test_merge_pane_uses_shared_shell_wrapper():
    html = (STATIC_ROOT / "index.html").read_text()
    assert 'class="pane-section merge-pane-shell"' in html


def test_corrected_panes_use_the_og_borderless_disclosure_glyphs():
    for relative_path in (
        "panes/media-pane.js",
        "panes/merge-pane.js",
        "panes/trim-sync-pane.js",
    ):
        source = (STATIC_ROOT / relative_path).read_text()
        assert '? "v" : ">"' in source
        assert "\\u25BC" not in source
        assert "\\u25B6" not in source


def test_phase15_pane_css_forces_single_column_flow_in_new_panes():
    css = (STATIC_ROOT / "styles" / "panes.css").read_text()
    assert ".media-pane-actions,\n.queue-stage-actions {" in css
    assert "grid-template-columns: minmax(0, 1fr);" in css
    assert ".trim-bulk-grid,\n.trim-card-row {" in css
    assert ".media-pane-actions-split" in css
    assert ".merge-source-controls" in css


def test_compose_active_source_places_opacity_before_layout():
    source = (STATIC_ROOT / "panes" / "merge-pane.js").read_text()
    within = source[
        source.index("const placementModeSelect") : source.index(
            "const body = documentObject.createElement"
        )
    ]
    assert "opacityField = buildSourceOpacityInput()" in within
    opacity_idx = within.index("opacityField,\n          placementModeLabelEl,")
    assert opacity_idx > within.index("opacityField = buildSourceOpacityInput()")


def test_v107_pane_audit_collects_visual_parity_metrics():
    source = Path("scripts/audits/browser/run_v107_pane_audit.py").read_text()
    assert '"pane_metrics"' in source
    assert '"visual_parity"' in source
    assert "Pane visual audit failed" in source
    assert "toggle_right_offsets_px" in source
    assert "control_column_counts" in source


def test_shell_runtime_wires_practiscore_selectors():
    source = (STATIC_ROOT / "lib" / "shell-runtime.js").read_text()
    assert "match-competitor-name" in source
    assert "match-competitor-place" in source
    assert "match-class" in source
    assert "match-division" in source
    assert "syncPractiScoreSelectionFields" in source


def test_project_pane_functions_return_results_not_noop():
    source = (STATIC_ROOT / "panes" / "project-pane.js").read_text()
    ensure_start = source.index("function ensurePractiScoreSelectionControls")
    ensure_end = source.index("function renderPractiScoreSelect", ensure_start)
    ensure_body = source[ensure_start:ensure_end]
    assert "currentState()?.practiscore_options" in ensure_body
    assert len(ensure_body) > 20
