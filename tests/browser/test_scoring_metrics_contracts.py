from __future__ import annotations

from pathlib import Path

from splitshot.browser.state import browser_state
from splitshot.domain.models import ImportedStageScore, Project, ScoreLetter, ScoreMark, ShotEvent
from splitshot.scoring.logic import apply_scoring_preset


STATIC_ROOT = Path("src/splitshot/browser/static")


def test_browser_state_projects_active_preset_scores_to_score_and_metrics_rows() -> None:
    project = Project()
    project.scoring.enabled = True
    project.analysis.beep_time_ms_primary = 0
    project.analysis.shots = [
        ShotEvent(
            time_ms=1_000,
            score=ScoreMark(
                letter=ScoreLetter.DOWN_3,
                penalty_counts={"non_threats": 1},
            ),
        ),
    ]
    apply_scoring_preset(project, "uspsa_minor")
    shot = project.analysis.shots[0]
    assert shot.score is not None

    shot.score.letter = ScoreLetter.DOWN_3
    shot.score.penalty_counts = {"non_threats": 1}
    project.scoring.penalty_counts = {"non_threats": 2}

    payload = browser_state(project, "Ready.")

    assert payload["project"]["analysis"]["shots"][0]["score"]["letter"] == "A"
    assert payload["project"]["analysis"]["shots"][0]["score"]["penalty_counts"] == {}
    assert payload["project"]["scoring"]["penalty_counts"] == {}
    assert payload["split_rows"][0]["score_letter"] == "A"
    assert payload["split_rows"][0]["penalty_counts"] == {}
    assert payload["timing_segments"][0]["score_letter"] == "A"
    assert payload["timing_segments"][0]["penalty_counts"] == {}
    assert payload["scoring_summary"]["shot_points"] == 5
    assert payload["scoring_summary"]["field_penalties"] == 0
    assert payload["metrics"]["scoring_summary"]["shot_points"] == 5
    assert payload["metrics"]["scoring_summary"]["field_penalties"] == 0


def test_browser_state_refreshes_imported_stage_context_for_metrics_consumers() -> None:
    project = Project()
    project.scoring.enabled = True
    project.analysis.beep_time_ms_primary = 0
    project.analysis.shots = [ShotEvent(time_ms=2_000, score=ScoreMark(letter=ScoreLetter.A))]
    apply_scoring_preset(project, "uspsa_minor")
    project.scoring.imported_stage = ImportedStageScore(
        source_name="old-report.txt",
        match_type="uspsa",
        competitor_name="First Shooter",
        competitor_place=5,
        stage_number=1,
        raw_seconds=2.0,
        aggregate_points=50.0,
        total_points=45.0,
        shot_penalties=5.0,
    )

    first = browser_state(project, "Ready.")["scoring_summary"]["imported_stage"]
    assert first["source_name"] == "old-report.txt"
    assert first["stage_number"] == 1
    assert first["competitor_name"] == "First Shooter"
    assert first["competitor_place"] == 5

    project.scoring.imported_stage = ImportedStageScore(
        source_name="new-report.txt",
        match_type="uspsa",
        competitor_name="Second Shooter",
        competitor_place=2,
        stage_number=3,
        raw_seconds=2.0,
        aggregate_points=55.0,
        total_points=53.0,
        shot_penalties=2.0,
    )
    second_payload = browser_state(project, "Ready.")
    second = second_payload["scoring_summary"]["imported_stage"]

    assert second["source_name"] == "new-report.txt"
    assert second["stage_number"] == 3
    assert second["competitor_name"] == "Second Shooter"
    assert second["competitor_place"] == 2
    assert second_payload["scoring_summary"]["shot_points"] == 55.0
    assert second_payload["scoring_summary"]["shot_penalties"] == 2.0


def test_browser_state_defines_missing_beep_raw_time_and_confidence_projection() -> None:
    project = Project()
    project.scoring.enabled = True
    project.analysis.beep_time_ms_primary = None
    project.analysis.shots = [
        ShotEvent(time_ms=900, confidence=None, score=ScoreMark(letter=ScoreLetter.A)),
        ShotEvent(time_ms=1_400, confidence=0.76, score=ScoreMark(letter=ScoreLetter.C)),
    ]
    apply_scoring_preset(project, "uspsa_minor")

    payload = browser_state(project, "Ready.")

    assert payload["metrics"]["beep_ms"] is None
    assert payload["metrics"]["raw_time_ms"] is None
    assert payload["metrics"]["draw_ms"] is None
    assert payload["split_rows"][0]["cumulative_ms"] is None
    assert payload["timing_segments"][0]["cumulative_ms"] is None
    assert payload["split_rows"][0]["confidence"] is None
    assert payload["timing_segments"][0]["confidence"] is None
    assert payload["split_rows"][1]["confidence"] == 0.76
    assert payload["timing_segments"][1]["confidence"] == 0.76


def test_static_metrics_pane_and_exports_share_current_row_model() -> None:
    js = (STATIC_ROOT / "app.js").read_text()

    assert js.count("const rows = buildMetricsRows();") == 5
    assert "const confidence = splitRowShotMLConfidence(row);" in js
    assert 'title: "Shot / Interval Timeline"' in js
    assert 'title: "Split / Interval Bar Chart"' in js
    assert 'title: "Run Comparison Overlay"' in js
    assert 'title: "Stage Segment Breakdown"' in js
    assert 'function buildMetricsStageSegments(points = []) {' in js
    assert 'ShotML Reference' in js
    assert 'return `${clamped.toFixed(1)}%`;' in js
    assert "estimated confidence" not in js
    assert "ShotML ${formatConfidenceValue(entry.confidence)}" in js
    assert "scoreStatus.dataset.importedSource = imported.source_name || \"\";" in js
    assert "scoreStatus.dataset.importedStage = imported.stage_number ?? \"\";" in js
    assert "scoreStatus.dataset.importedCompetitor = imported.competitor_name || \"\";" in js
    assert "scoreStatus.dataset.importedPlace = imported.competitor_place ?? \"\";" in js
    assert '"result_label"' in js
    assert '"result_value"' in js
    assert '"raw_time_s"' in js
    assert '"interval_label"' in js
    assert '"actions"' in js
    assert '"pair_label"' in js
    assert '"category_id"' in js
    assert '"category_label"' in js
    assert '"shotml_split_s"' in js
    assert '"adjustment_s"' in js
    assert '"practiscore_raw_s"' in js
    assert '"raw_delta_s"' in js
    assert '"shotml_confidence"' in js
    assert '"Split Timeline"' in js
    assert '"Stage Segments"' in js
    assert '"Run Comparison Overlay"' in js


def test_static_scoring_pane_extracts_owned_scoring_blocks_into_module() -> None:
    app_js = (STATIC_ROOT / "app.js").read_text()
    scoring_js = (STATIC_ROOT / "panes" / "scoring-pane.js").read_text()
    pane_base_js = (STATIC_ROOT / "panes" / "pane-base.js").read_text()

    assert 'import { createScoringPane } from "./panes/scoring-pane.js";' in app_js
    assert "scoringPane = createScoringPane({" in app_js
    assert "function setScoringWorkbenchExpanded(expanded, { persistUiState = true } = {}) {" in app_js
    assert "return scoringPane?.setScoringWorkbenchExpanded(expanded, { persistUiState }) ?? Boolean(expanded);" in app_js
    assert 'function renderScoringTable(tableId = "scoring-table") {' in app_js
    assert "return scoringPane?.renderScoringTable(tableId);" in app_js
    assert "function renderScoringTables() {" in app_js
    assert "return scoringPane?.renderScoringTables();" in app_js
    assert "function readScoringPayload() {" in app_js
    assert "return scoringPane?.readScoringPayload()" in app_js
    assert "function toggleScoringRowEdit(" not in app_js
    assert "function applyShotScoringUpdate(" not in app_js
    assert "function buildScoringPenaltyEditor(" not in app_js

    assert "export function createScoringPane({" in scoring_js
    assert "const scoringPaneBase = createPaneBase({" in scoring_js
    assert 'expandedClass: "scoring-expanded"' in scoring_js
    assert 'sectionId: "scoring-workbench"' in scoring_js
    assert "function toggleScoringRowEdit(shotId) {" in scoring_js
    assert "function applyShotScoringUpdate(shotId, scope) {" in scoring_js
    assert "function buildScoringPenaltyEditor(segment, rowScope, penaltyFields) {" in scoring_js
    assert "function importedStageRecordedScoreLabel(imported) {" in scoring_js
    assert "function renderPractiScoreSummaries() {" in scoring_js
    assert '"Recorded Score"' in scoring_js
    assert '"Recorded Penalty"' in scoring_js
    assert "function readScoringPayload() {" in scoring_js
    assert "async function applyScoringSettings(scoringPayload = readScoringPayload(), ruleset = $(\"scoring-preset\")?.value || \"\") {" in scoring_js
    assert "function scheduleScoringApply() {" in scoring_js

    assert "export function createPaneBase({" in pane_base_js
    assert "collapseClasses = []" in pane_base_js
    assert 'activityName = "pane.expand"' in pane_base_js
    assert "setExpandedState = () => {}" in pane_base_js
    assert "scoring" not in pane_base_js.lower()
