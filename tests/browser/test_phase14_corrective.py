"""Phase 14 corrective assertions — Project context, Media workflow, Queue routing, Review formatting."""

from __future__ import annotations

from pathlib import Path

STATIC_ROOT = Path("src/splitshot/browser/static")


# ---------------------------------------------------------------------------
# V107-1400 — Project context ownership
# ---------------------------------------------------------------------------

def test_project_retains_competitor_selectors():
    source = (STATIC_ROOT / "panes" / "project-pane.js").read_text()
    assert "renderPractiScoreOptionLists" in source
    assert "syncPractiScoreSelectionFields" in source
    assert "renderPractiScoreImportSummary" in source
    assert "match-stage-number" in source
    assert "match-competitor-name" in source
    assert "match-competitor-place" in source


def test_project_summary_is_four_row_contract():
    source = (STATIC_ROOT / "panes" / "project-pane.js").read_text()
    within = source[source.index("renderPractiScoreImportSummary"):]
    assert '"Name"' in within
    assert '"Place"' in within
    assert '"Match Time"' in within
    assert '"Division"' in within


def test_project_does_not_own_stage_media():
    source = (STATIC_ROOT / "panes" / "project-pane.js").read_text()
    within = source[source.index("renderPractiScoreImportSummary"):source.index("renderPractiScoreImportSummary") + source[source.index("renderPractiScoreImportSummary"):].index("function") if "function" in source[source.index("renderPractiScoreImportSummary"):] else len(source[source.index("renderPractiScoreImportSummary"):])]
    # The four-row summary must not include media-file language
    assert "primary_media" not in within
    assert "added_media" not in within
    assert "file_intake" not in within.lower()


# ---------------------------------------------------------------------------
# V107-1410 — Media stage-first workflow
# ---------------------------------------------------------------------------

def test_media_pane_has_stage_toggles():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "scoring-shot-toggle" in source
    assert "media-stage-toggle" in source
    assert "section-header-with-toggle" in source
    assert "isStageExpanded" in source
    assert "toggleStage" in source


def test_media_pane_uses_openMediaAddMoreInput_not_openMergeMediaInput():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "openMediaAddMoreInput" in source
    assert "openMergeMediaInput" not in source


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
    assert 'openPrimaryForStage(button.dataset.stageId || "")' not in source


def test_media_pane_has_add_more_and_edit_stage():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "media-add-more-btn" in source
    assert "media-edit-stage-btn" in source
    assert "Add More" in source
    assert "Edit Stage" in source


def test_media_pane_has_no_inline_competitor_edits():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "data-stage-field" not in source
    assert "competitor_name" not in source.lower()
    assert "competitor_place" not in source.lower()
    assert "Save Stage Details" not in source
    assert "Save Stage" not in source


def test_media_pane_has_no_filler_copy():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "pane-flow-hint" not in source


def test_media_file_rows_use_asset_meta():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "assetMeta" in source
    assert "assetTypeLabel" in source


def test_media_pane_expansion_is_persisted():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "splitshot.media.stageExpanded" in source
    assert "localStorage" in source


# ---------------------------------------------------------------------------
# V107-1420 — Queue routing, filler removal, Compose overlap
# ---------------------------------------------------------------------------

def test_media_inventory_and_stage_navigator_are_separate():
    source = (STATIC_ROOT / "panes" / "media-pane.js").read_text()
    assert "media-pane-active-stage" in source
    assert "media-stage-nav-list" in source
    assert "renderPrimarySection" in source
    assert "renderAddedSection" in source
    assert "renderStageNavigatorRow" in source


def test_queue_edit_stage_routes_to_media_not_merge():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert 'setActiveTool("media")' in source
    assert 'setActiveTool("merge")' not in source


def test_queue_activity_log_is_media():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    within_edit = source[source.index("editStage"):]
    assert 'tool: "media"' in within_edit
    assert 'tool: "merge"' not in within_edit


def test_queue_has_no_filler_copy():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "pane-flow-hint" not in source


def test_media_add_more_input_exists_in_html():
    html = (STATIC_ROOT / "index.html").read_text()
    assert 'id="media-add-more-input"' in html


def test_media_add_more_input_has_handler_in_shell():
    shell = (STATIC_ROOT / "lib" / "shell-runtime.js").read_text()
    assert 'media-add-more-input' in shell
    assert 'addEventListener("change"' in shell


def test_app_js_wires_openMediaAddMoreInput():
    app = (STATIC_ROOT / "app.js").read_text()
    assert "openMediaAddMoreInput" in app
    assert 'media-add-more-input' in app


def test_queue_needs_requeue_label_exists():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "Needs requeue" in source


def test_queue_has_stage_toggles():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "scoring-shot-toggle" in source
    assert "queue-stage-toggle" in source
    assert "section-header-with-toggle" in source
    assert "isStageExpanded" in source
    assert "toggleStage" in source


def test_queue_expansion_is_persisted():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "splitshot.queue.stageExpanded" in source
    assert "localStorage" in source


# ---------------------------------------------------------------------------
# V107-1430 — Review summary denominator formatting
# ---------------------------------------------------------------------------

def test_formatPlacement_uses_denominator():
    source = (STATIC_ROOT / "panes" / "review-pane.js").read_text()
    start = source.index("function formatPlacement")
    within = source[start:start + 600]
    assert "${numericPlace}/${numericTotal}" in within
    assert "String(numericPlace)" in within


def test_formatPlacement_has_no_hash_format():
    source = (STATIC_ROOT / "panes" / "review-pane.js").read_text()
    within = source[source.index("formatPlacement"):source.index("formatPlacement") + 400]
    assert "#" not in within  # no ordinal-hash formatting


def test_review_metric_value_wires_placement_dimensions():
    source = (STATIC_ROOT / "panes" / "review-pane.js").read_text()
    within = source[source.index("reviewMetricValue"):]
    assert "overall_placement" in within
    assert "division_placement" in within
    assert "class_placement" in within
    assert "division_class_placement" in within
    assert "formatPlacement" in within


def test_review_passes_denominator_to_all_placement_fields():
    source = (STATIC_ROOT / "panes" / "review-pane.js").read_text()
    within = source[source.index("reviewMetricValue"):]
    assert 'formatPlacement(imported.competitor_place, groups.overall.items.length)' in within
    assert 'formatPlacement(groups.division.place, groups.division.items.length)' in within
    assert 'formatPlacement(groups.class.place, groups.class.items.length)' in within
    assert 'formatPlacement(groups.divisionClass.place, groups.divisionClass.items.length)' in within
def test_queue_uses_compact_stage_cards():
    source = (STATIC_ROOT / "panes" / "queue-pane.js").read_text()
    assert "queue-stage-card" in source
    assert "queue-status-pill" in source
    assert "queue-pane-actions" in source


def test_trim_uses_source_cards_and_bulk_sections():
    source = (STATIC_ROOT / "panes" / "trim-sync-pane.js").read_text()
    assert "trim-source-card" in source
    assert "trim-bulk-grid" in source
    assert "trim-card-row" in source
    assert "trim-sync-nudge-buttons" in source


def test_waveform_renderer_declares_lane_clipping():
    source = (STATIC_ROOT / "components" / "waveform.js").read_text()
    assert 'canvas.dataset.waveformLaneClipping = "isolated"' in source
    assert 'canvas.dataset.waveformLaneBleed = "false"' in source
    assert "ctx.clip();" in source


def test_merge_pane_uses_shared_shell_wrapper():
    html = (STATIC_ROOT / "index.html").read_text()
    assert 'class="pane-section merge-pane-shell"' in html


def test_phase15_pane_css_forces_single_column_flow_in_new_panes():
    css = (STATIC_ROOT / "styles" / "panes.css").read_text()
    assert ".media-stage-nav-actions,\n.queue-stage-actions {" in css
    assert "grid-template-columns: minmax(0, 1fr);" in css
    assert ".trim-bulk-grid,\n.trim-card-row {" in css


def test_v107_pane_audit_collects_visual_parity_metrics():
    source = Path("scripts/audits/browser/run_v107_pane_audit.py").read_text()
    assert '"pane_metrics"' in source
    assert '"visual_parity"' in source
    assert "Pane visual parity audit failed" in source
    assert "toggle_right_offsets_px" in source
    assert "control_column_counts" in source
