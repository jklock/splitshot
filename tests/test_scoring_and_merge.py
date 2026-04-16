from __future__ import annotations

from splitshot.domain.models import (
    ImportedStageScore,
    MergeLayout,
    PipSize,
    Project,
    ScoreLetter,
    ScoreMark,
    ShotEvent,
    VideoAsset,
)
from splitshot.merge.layouts import calculate_merge_canvas
from splitshot.scoring.logic import (
    apply_scoring_preset,
    calculate_hit_factor,
    calculate_scoring_summary,
    current_shot_index,
    scoring_presets_for_api,
)


def test_hit_factor_uses_shot_scores_and_penalties() -> None:
    project = Project()
    project.scoring.enabled = True
    project.scoring.penalties = 5
    project.analysis.beep_time_ms_primary = 100
    project.analysis.shots = [
        ShotEvent(time_ms=800, score=ScoreMark(letter=ScoreLetter.A)),
        ShotEvent(time_ms=1100, score=ScoreMark(letter=ScoreLetter.C)),
        ShotEvent(time_ms=1450, score=ScoreMark(letter=ScoreLetter.D)),
    ]

    hit_factor = calculate_hit_factor(project)
    assert hit_factor is not None
    assert round(hit_factor, 2) == round((5 + 3 + 1 - 5) / 1.35, 2)


def test_current_shot_tracks_playback_position() -> None:
    project = Project()
    project.analysis.shots = [
        ShotEvent(time_ms=800),
        ShotEvent(time_ms=1100),
        ShotEvent(time_ms=1450),
    ]

    assert current_shot_index(project, 799) is None
    assert current_shot_index(project, 1101) == 1
    assert current_shot_index(project, 1600) == 2


def test_scoring_presets_cover_hit_factor_and_time_plus() -> None:
    project = Project()
    project.scoring.enabled = True
    project.analysis.beep_time_ms_primary = 500
    project.analysis.shots = [
        ShotEvent(time_ms=1000, score=ScoreMark(letter=ScoreLetter.A)),
        ShotEvent(time_ms=1500, score=ScoreMark(letter=ScoreLetter.C)),
        ShotEvent(time_ms=2000, score=ScoreMark(letter=ScoreLetter.M)),
    ]

    apply_scoring_preset(project, "uspsa_major")
    project.scoring.penalties = 0
    summary = calculate_scoring_summary(project)
    assert summary["ruleset"] == "uspsa_major"
    assert summary["mode"] == "hit_factor"
    assert summary["display_label"] == "Hit Factor"
    assert summary["hit_factor"] == 0.0
    assert summary["shot_penalties"] == 10

    apply_scoring_preset(project, "idpa_time_plus")
    project.scoring.penalties = 3
    summary = calculate_scoring_summary(project)
    assert summary["ruleset"] == "idpa_time_plus"
    assert summary["mode"] == "time_plus"
    assert summary["display_label"] == "Final"
    assert summary["final_time"] == 1.5 + 5 + 3


def test_uspsa_minor_counts_misses_no_shoots_and_procedurals() -> None:
    project = Project()
    project.scoring.enabled = True
    project.analysis.beep_time_ms_primary = 500
    project.analysis.shots = [
        ShotEvent(time_ms=1000, score=ScoreMark(letter=ScoreLetter.A)),
        ShotEvent(time_ms=1500, score=ScoreMark(letter=ScoreLetter.C)),
        ShotEvent(time_ms=2000, score=ScoreMark(letter=ScoreLetter.M)),
        ShotEvent(time_ms=2500, score=ScoreMark(letter=ScoreLetter.NS)),
    ]

    apply_scoring_preset(project, "uspsa_minor")
    project.scoring.penalty_counts = {"procedural_errors": 1}
    summary = calculate_scoring_summary(project)

    assert summary["shot_points"] == 8
    assert summary["shot_penalties"] == 20
    assert summary["field_penalties"] == 10
    assert summary["hit_factor"] == 0.0


def test_ipsc_major_matches_major_hit_factor_values() -> None:
    project = Project()
    project.scoring.enabled = True
    project.analysis.beep_time_ms_primary = 500
    project.analysis.shots = [
        ShotEvent(time_ms=1000, score=ScoreMark(letter=ScoreLetter.A)),
        ShotEvent(time_ms=1500, score=ScoreMark(letter=ScoreLetter.C)),
        ShotEvent(time_ms=2000, score=ScoreMark(letter=ScoreLetter.D)),
    ]

    apply_scoring_preset(project, "ipsc_major")
    summary = calculate_scoring_summary(project)

    assert summary["shot_points"] == 11
    assert summary["hit_factor"] == 11 / 1.5


def test_idpa_time_plus_uses_points_down_and_penalty_seconds() -> None:
    project = Project()
    project.scoring.enabled = True
    project.analysis.beep_time_ms_primary = 500
    project.analysis.shots = [
        ShotEvent(time_ms=1000, score=ScoreMark(letter=ScoreLetter.DOWN_0)),
        ShotEvent(time_ms=1500, score=ScoreMark(letter=ScoreLetter.DOWN_1)),
        ShotEvent(time_ms=2000, score=ScoreMark(letter=ScoreLetter.DOWN_3)),
        ShotEvent(time_ms=2500, score=ScoreMark(letter=ScoreLetter.M)),
    ]

    apply_scoring_preset(project, "idpa_time_plus")
    project.scoring.penalty_counts = {
        "non_threats": 1,
        "procedural_errors": 2,
        "flagrant_penalties": 1,
        "failures_to_do_right": 1,
    }
    summary = calculate_scoring_summary(project)

    assert summary["shot_points"] == 9
    assert summary["field_penalties"] == 41
    assert summary["final_time"] == 2.0 + 9 + 41


def test_scoring_summary_exposes_token_text_colors() -> None:
    project = Project()

    apply_scoring_preset(project, "idpa_time_plus")
    summary = calculate_scoring_summary(project)
    color_options = {item["key"]: item for item in summary["scoring_color_options"]}

    assert "-0" in color_options
    assert "PE" in color_options
    assert color_options["PE"]["label"] == "PE"
    assert color_options["PE"]["description"] == "Procedural Error"
    assert "NT" in color_options
    assert "-0|procedural_errors" not in color_options


def test_imported_stage_summary_uses_official_aggregate_values() -> None:
    project = Project()
    project.scoring.enabled = True
    project.scoring.penalties = 2.0
    project.scoring.penalty_counts = {"procedural_errors": 1}
    project.scoring.imported_stage = ImportedStageScore(
        match_type="uspsa",
        competitor_name="Stephen Lutman",
        stage_number=1,
        stage_name="Stage 1 Swangin’",
        raw_seconds=23.24,
        aggregate_points=101.0,
        total_points=101.0,
        shot_penalties=0.0,
        hit_factor=4.3460,
        stage_points=125.0,
        stage_place=1,
        score_counts={"A": 15.0, "C": 8.0, "D": 2.0},
    )

    apply_scoring_preset(project, "uspsa_minor")
    summary = calculate_scoring_summary(project)

    assert summary["raw_seconds"] == 23.24
    assert summary["shot_points"] == 101.0
    assert summary["shot_penalties"] == 0.0
    assert summary["field_penalties"] == 10.0
    assert summary["total_penalties"] == 12.0
    assert summary["hit_factor"] == 101.0 / 23.24
    assert summary["imported_stage"]["stage_place"] == 1
    assert summary["imported_overlay_text"] == "Official\nRaw 23.24\nPoints 101\nHF 4.3460"


def test_imported_stage_hit_factor_uses_official_total_points_and_raw_time() -> None:
    project = Project()
    project.scoring.enabled = True
    project.scoring.imported_stage = ImportedStageScore(
        match_type="uspsa",
        competitor_name="Match Shooter",
        stage_number=2,
        raw_seconds=23.28,
        aggregate_points=106.0,
        total_points=96.0,
        shot_penalties=10.0,
        hit_factor=4.12,
    )

    apply_scoring_preset(project, "uspsa_minor")
    summary = calculate_scoring_summary(project)

    assert summary["hit_factor"] == 96.0 / 23.28
    assert summary["display_value"] == "4.12"


def test_imported_stage_overlay_text_uses_idpa_official_fields() -> None:
    project = Project()
    project.scoring.enabled = True
    project.scoring.imported_stage = ImportedStageScore(
        match_type="idpa",
        competitor_name="Match Shooter",
        stage_number=2,
        raw_seconds=29.83,
        aggregate_points=5.0,
        final_time=39.83,
    )

    apply_scoring_preset(project, "idpa_time_plus")
    summary = calculate_scoring_summary(project)

    assert summary["imported_overlay_text"] == "Official\nRaw 29.83\nPD 5\nFinal 39.83"


def test_steel_and_gpa_time_plus_presets_are_explicit() -> None:
    steel = Project()
    steel.scoring.enabled = True
    steel.analysis.beep_time_ms_primary = 100
    steel.analysis.shots = [
        ShotEvent(time_ms=1100, score=ScoreMark(letter=ScoreLetter.STEEL_HIT)),
        ShotEvent(time_ms=1600, score=ScoreMark(letter=ScoreLetter.M)),
    ]
    apply_scoring_preset(steel, "steel_challenge")
    steel.scoring.penalty_counts = {"stop_plate_failures": 1}
    steel_summary = calculate_scoring_summary(steel)
    assert steel_summary["final_time"] == 1.5 + 3 + 30

    gpa = Project()
    gpa.scoring.enabled = True
    gpa.analysis.beep_time_ms_primary = 100
    gpa.analysis.shots = [
        ShotEvent(time_ms=1100, score=ScoreMark(letter=ScoreLetter.GPA_1)),
        ShotEvent(time_ms=1600, score=ScoreMark(letter=ScoreLetter.GPA_3)),
        ShotEvent(time_ms=2100, score=ScoreMark(letter=ScoreLetter.GPA_10)),
    ]
    apply_scoring_preset(gpa, "gpa_time_plus")
    gpa.scoring.penalty_counts = {"non_threats": 1, "steel_not_down": 1}
    gpa_summary = calculate_scoring_summary(gpa)
    assert gpa_summary["final_time"] == 2.0 + 0.5 + 1.5 + 5 + 15


def test_browser_api_hides_gpa_preset() -> None:
    preset_ids = {preset["id"] for preset in scoring_presets_for_api()}

    assert "gpa_time_plus" not in preset_ids
    assert {"uspsa_minor", "uspsa_major", "ipsc_minor", "ipsc_major", "idpa_time_plus", "steel_challenge"}.issubset(preset_ids)


def test_merge_canvas_covers_layouts() -> None:
    primary = VideoAsset(path="primary.mp4", width=640, height=360, fps=30.0)
    secondary = VideoAsset(path="secondary.mp4", width=1280, height=720, fps=30.0)

    side = calculate_merge_canvas(primary, secondary, MergeLayout.SIDE_BY_SIDE, PipSize.MEDIUM)
    assert side.width > 640
    assert side.height == 720

    above = calculate_merge_canvas(primary, secondary, MergeLayout.ABOVE_BELOW, PipSize.MEDIUM)
    assert above.width == 1280
    assert above.height > 720

    pip = calculate_merge_canvas(primary, secondary, MergeLayout.PIP, PipSize.LARGE)
    assert pip.width == 640
    assert pip.secondary_rect is not None
    assert pip.secondary_rect.width < pip.width


def test_merge_canvas_positions_pip_from_normalized_coordinates() -> None:
    primary = VideoAsset(path="primary.mp4", width=640, height=360, fps=30.0)
    secondary = VideoAsset(path="secondary.mp4", width=1280, height=720, fps=30.0)

    top_left = calculate_merge_canvas(primary, secondary, MergeLayout.PIP, 35, 0.0, 0.0)
    bottom_right = calculate_merge_canvas(primary, secondary, MergeLayout.PIP, 35, 1.0, 1.0)

    assert top_left.secondary_rect is not None
    assert bottom_right.secondary_rect is not None
    assert top_left.secondary_rect.x == 0
    assert top_left.secondary_rect.y == 0
    assert top_left.secondary_rect.x < bottom_right.secondary_rect.x
    assert top_left.secondary_rect.y < bottom_right.secondary_rect.y
    assert bottom_right.secondary_rect.x + bottom_right.secondary_rect.width == primary.width
    assert bottom_right.secondary_rect.y + bottom_right.secondary_rect.height == primary.height
