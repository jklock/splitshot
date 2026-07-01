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


def test_media_pane_has_section_toggles():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "media-section-toggle" in source
    assert "sectionExpanded" in source
    assert "toggleSection" in source
    assert "Active Stage" in source
    assert 'data-media-section="stages"' in source


def test_media_pane_uses_backend_dialog_not_file_inputs():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "pickPath" in source
    assert 'callApi("/api/project/stage/import-primary"' in source
    assert 'callApi("/api/project/stage/import-added"' in source


def test_media_pane_has_file_rows_with_primary_badge():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "media-asset-row" in source
    assert "primary-badge" in source
    assert "media-set-primary-btn" in source
    assert "media-remove-file-btn" in source
    assert "renderInventoryFileRow" in source


def test_media_pane_uses_real_set_primary_route():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert 'callApi("/api/project/stage/set-primary"' in source


def test_media_pane_has_add_more_edit_stage_and_create_stage():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "media-add-more-btn" in source
    assert "media-edit-stage-btn" in source
    assert "media-add-stage-btn" in source
    assert "media-add-stage-full" in source
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


def test_media_pane_expansion_is_persisted():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "splitshot.media.sectionExpanded" in source
    assert "localStorage" in source


# ---------------------------------------------------------------------------
# V107-1420 — Queue routing, filtering, filler removal, Compose overlap
# ---------------------------------------------------------------------------


def test_media_inventory_and_stage_navigator_are_separate():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "renderActiveStageSection" in source
    assert "renderStagesSection" in source
    assert "Primary" in source
    assert "Active Media" in source
    assert "Stage Navigator" in source
    assert "renderInventoryFileRow" in source
    assert "media-stage-card" not in source


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


def test_media_picker_root_prefers_stage_media_then_project_input():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    within = source[
        source.index("function mediaPickerDefaultRoot") : source.index(
            "function readSectionExpansion"
        )
    ]
    assert "stage?.primary_media?.path" in within
    assert "stageAddedMedia(stage)[0]" in within
    assert 'joinProjectPath(projectPath, "Input")' in within
    assert "projectPath ||" in within


def test_queue_has_no_filler_copy():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "pane-flow-hint" not in source


def test_queue_visible_entries_excludes_not_queued():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    within = source[source.index("visibleQueueEntries") : source.index("visibleQueueEntries") + 500]
    assert 'status !== "not_queued"' in within


def test_queue_needs_requeue_label_exists():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "Needs requeue" in source


def test_queue_has_stage_toggles():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "pane-toggle" in source
    assert "queue-stage-toggle" in source
    assert "section-header-with-toggle" in source
    assert "isStageExpanded" in source
    assert "toggleStage" in source


def test_queue_expansion_is_persisted():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "splitshot.queue.stageExpanded" in source
    assert "localStorage" in source


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
    assert "division_class_placement" in within
    assert "formatPlacement" in within


def test_review_passes_denominator_to_all_placement_fields():
    source = (STATIC_ROOT / "panes" / "review-pane.js").read_text()
    within = source[source.index("reviewMetricValue") :]
    assert "formatPlacement(imported.competitor_place, groups.overall.items.length)" in within
    assert "formatPlacement(groups.division.place, groups.division.items.length)" in within
    assert "formatPlacement(groups.class.place, groups.class.items.length)" in within
    assert (
        "formatPlacement(groups.divisionClass.place, groups.divisionClass.items.length)" in within
    )


def test_queue_uses_compact_stage_cards():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "queue-stage-card" in source
    assert "queue-status-pill" in source
    assert "Queue Controls" in source
    assert "Queued Stages" in source


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
    assert "Undo Last Change" in source
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


def test_phase15_pane_css_forces_single_column_flow_in_new_panes():
    css = (STATIC_ROOT / "styles" / "panes.css").read_text()
    assert ".media-stage-nav-actions,\n.queue-stage-actions {" in css
    assert "grid-template-columns: minmax(0, 1fr);" in css
    assert ".trim-bulk-grid,\n.trim-card-row {" in css
    assert ".media-stage-nav-actions-split" in css
    assert ".merge-source-layout-row" in css


def test_compose_active_source_places_opacity_before_layout():
    source = (STATIC_ROOT / "panes" / "merge-pane.js").read_text()
    within = source[
        source.index("const placementModeSelect") : source.index(
            "const body = documentObject.createElement"
        )
    ]
    assert "const opacityAndLayoutRow" in within
    assert "opacityAndLayoutRow.append(buildSourceOpacityInput(), placementModeLabelEl);" in within


def test_v107_pane_audit_collects_visual_parity_metrics():
    source = Path("scripts/audits/browser/run_v107_pane_audit.py").read_text()
    assert '"pane_metrics"' in source
    assert '"visual_parity"' in source
    assert "Pane visual parity audit failed" in source
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
