from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math

from splitshot.domain.models import ImportedStageScore, Project, ScoreLetter, ScoreMark, ShotEvent
from splitshot.timeline.model import raw_time_ms


@dataclass(frozen=True, slots=True)
class ScoringPreset:
    id: str
    name: str
    sport: str
    mode: str
    description: str
    point_map: dict[str, float]
    penalty_label: str
    score_penalty_map: dict[str, float] = field(default_factory=dict)
    score_options: tuple[str, ...] = field(default_factory=tuple)
    penalty_fields: tuple["PenaltyField", ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class PenaltyField:
    id: str
    label: str
    value: float
    unit: str
    description: str = ""


USPSA_IPSC_PENALTIES = (
    PenaltyField("procedural_errors", "Procedural Error", 10, "points", "Usually -10 points each."),
    PenaltyField("manual_no_shoots", "Extra No-Shoot", 10, "points", "Use for no-shoots not tied to a shot marker."),
    PenaltyField("manual_misses", "Extra Miss", 10, "points", "Use for misses not tied to a shot marker."),
)

IDPA_PENALTIES = (
    PenaltyField("non_threats", "Non-Threat", 5, "seconds", "+5 seconds each."),
    PenaltyField("procedural_errors", "Procedural Error", 3, "seconds", "+3 seconds each."),
    PenaltyField("flagrant_penalties", "Flagrant Penalty", 10, "seconds", "+10 seconds each."),
    PenaltyField("failures_to_do_right", "Failure To Do Right", 20, "seconds", "+20 seconds each."),
    PenaltyField("finger_pe", "Finger PE", 3, "seconds", "+3 seconds each."),
)

STEEL_PENALTIES = (
    PenaltyField("steel_misses", "Plate Miss", 3, "seconds", "+3 seconds each."),
    PenaltyField("stop_plate_failures", "Stop Plate Failure", 30, "seconds", "30 second string."),
)

GPA_PENALTIES = (
    PenaltyField("non_threats", "Non-Threat", 5, "seconds", "+5 seconds each."),
    PenaltyField("steel_not_down", "Steel Not Down", 10, "seconds", "+10 seconds each."),
)


PENALTY_FIELD_SHORT_LABELS = {
    "procedural_errors": "PE",
    "manual_no_shoots": "NS",
    "manual_misses": "M",
    "non_threats": "NT",
    "flagrant_penalties": "FP",
    "failures_to_do_right": "FTDR",
    "finger_pe": "FPE",
    "steel_misses": "PM",
    "stop_plate_failures": "SPF",
    "steel_not_down": "SND",
}


SCORING_PRESETS: dict[str, ScoringPreset] = {
    "uspsa_minor": ScoringPreset(
        id="uspsa_minor",
        name="USPSA Minor",
        sport="USPSA",
        mode="hit_factor",
        description="Minor PF HF scoring with A, C, D, M, and NS.",
        point_map={
            ScoreLetter.A.value: 5,
            ScoreLetter.C.value: 3,
            ScoreLetter.D.value: 1,
            ScoreLetter.M.value: 0,
            ScoreLetter.NS.value: 0,
            ScoreLetter.MU.value: 0,
            ScoreLetter.M_NS.value: 0,
        },
        score_penalty_map={
            ScoreLetter.M.value: 10,
            ScoreLetter.NS.value: 10,
            ScoreLetter.M_NS.value: 20,
        },
        score_options=(
            ScoreLetter.A.value,
            ScoreLetter.C.value,
            ScoreLetter.D.value,
            ScoreLetter.M.value,
            ScoreLetter.NS.value,
            ScoreLetter.M_NS.value,
        ),
        penalty_fields=USPSA_IPSC_PENALTIES,
        penalty_label="Penalty points",
    ),
    "uspsa_major": ScoringPreset(
        id="uspsa_major",
        name="USPSA Major",
        sport="USPSA",
        mode="hit_factor",
        description="Major PF HF scoring with A, C, D, M, and NS.",
        point_map={
            ScoreLetter.A.value: 5,
            ScoreLetter.C.value: 4,
            ScoreLetter.D.value: 2,
            ScoreLetter.M.value: 0,
            ScoreLetter.NS.value: 0,
            ScoreLetter.MU.value: 0,
            ScoreLetter.M_NS.value: 0,
        },
        score_penalty_map={
            ScoreLetter.M.value: 10,
            ScoreLetter.NS.value: 10,
            ScoreLetter.M_NS.value: 20,
        },
        score_options=(
            ScoreLetter.A.value,
            ScoreLetter.C.value,
            ScoreLetter.D.value,
            ScoreLetter.M.value,
            ScoreLetter.NS.value,
            ScoreLetter.M_NS.value,
        ),
        penalty_fields=USPSA_IPSC_PENALTIES,
        penalty_label="Penalty points",
    ),
    "ipsc_minor": ScoringPreset(
        id="ipsc_minor",
        name="IPSC Minor",
        sport="IPSC",
        mode="hit_factor",
        description="Minor PF HF scoring with A, C, D, M, and NS.",
        point_map={
            ScoreLetter.A.value: 5,
            ScoreLetter.C.value: 3,
            ScoreLetter.D.value: 1,
            ScoreLetter.M.value: 0,
            ScoreLetter.NS.value: 0,
            ScoreLetter.M_NS.value: 0,
        },
        score_penalty_map={
            ScoreLetter.M.value: 10,
            ScoreLetter.NS.value: 10,
            ScoreLetter.M_NS.value: 20,
        },
        score_options=(
            ScoreLetter.A.value,
            ScoreLetter.C.value,
            ScoreLetter.D.value,
            ScoreLetter.M.value,
            ScoreLetter.NS.value,
            ScoreLetter.M_NS.value,
        ),
        penalty_fields=USPSA_IPSC_PENALTIES,
        penalty_label="Penalty points",
    ),
    "ipsc_major": ScoringPreset(
        id="ipsc_major",
        name="IPSC Major",
        sport="IPSC",
        mode="hit_factor",
        description="Major PF HF scoring with A, C, D, M, and NS.",
        point_map={
            ScoreLetter.A.value: 5,
            ScoreLetter.C.value: 4,
            ScoreLetter.D.value: 2,
            ScoreLetter.M.value: 0,
            ScoreLetter.NS.value: 0,
            ScoreLetter.M_NS.value: 0,
        },
        score_penalty_map={
            ScoreLetter.M.value: 10,
            ScoreLetter.NS.value: 10,
            ScoreLetter.M_NS.value: 20,
        },
        score_options=(
            ScoreLetter.A.value,
            ScoreLetter.C.value,
            ScoreLetter.D.value,
            ScoreLetter.M.value,
            ScoreLetter.NS.value,
            ScoreLetter.M_NS.value,
        ),
        penalty_fields=USPSA_IPSC_PENALTIES,
        penalty_label="Penalty points",
    ),
    "idpa_time_plus": ScoringPreset(
        id="idpa_time_plus",
        name="IDPA - Time Plus",
        sport="IDPA",
        mode="time_plus",
        description="Time-plus scoring with PD, M, NS, PE, FP, FTDR, and FPE.",
        point_map={
            ScoreLetter.DOWN_0.value: 0,
            ScoreLetter.DOWN_1.value: 1,
            ScoreLetter.DOWN_3.value: 3,
            ScoreLetter.M.value: 5,
            ScoreLetter.NS.value: 5,
            ScoreLetter.M_NS.value: 10,
        },
        score_options=(
            ScoreLetter.DOWN_0.value,
            ScoreLetter.DOWN_1.value,
            ScoreLetter.DOWN_3.value,
            ScoreLetter.M.value,
            ScoreLetter.NS.value,
            ScoreLetter.M_NS.value,
        ),
        penalty_fields=IDPA_PENALTIES,
        penalty_label="Penalty seconds",
    ),
    "steel_challenge": ScoringPreset(
        id="steel_challenge",
        name="Steel Challenge",
        sport="Steel Challenge",
        mode="time_plus",
        description="Time scoring with PM and SPF.",
        point_map={
            ScoreLetter.STEEL_HIT.value: 0,
            ScoreLetter.M.value: 3,
            ScoreLetter.STEEL_STOP_FAIL.value: 30,
        },
        score_options=(
            ScoreLetter.STEEL_HIT.value,
            ScoreLetter.M.value,
            ScoreLetter.STEEL_STOP_FAIL.value,
        ),
        penalty_fields=STEEL_PENALTIES,
        penalty_label="Penalty seconds",
    ),
    "gpa_time_plus": ScoringPreset(
        id="gpa_time_plus",
        name="GPA 0.5 Scoring",
        sport="GPA",
        mode="time_plus",
        description="Time-plus scoring with PD x0.5, M, NT, and SND.",
        point_map={
            ScoreLetter.GPA_0.value: 0,
            ScoreLetter.GPA_1.value: 0.5,
            ScoreLetter.GPA_3.value: 1.5,
            ScoreLetter.GPA_10.value: 5,
            ScoreLetter.M.value: 5,
        },
        score_options=(
            ScoreLetter.GPA_0.value,
            ScoreLetter.GPA_1.value,
            ScoreLetter.GPA_3.value,
            ScoreLetter.GPA_10.value,
            ScoreLetter.M.value,
        ),
        penalty_fields=GPA_PENALTIES,
        penalty_label="Penalty seconds",
    ),
}


def scoring_presets_for_api() -> list[dict[str, object]]:
    return [
        asdict(preset)
        for preset in SCORING_PRESETS.values()
        if preset.id != "gpa_time_plus"
    ]


def get_scoring_preset(ruleset: str) -> ScoringPreset:
    return SCORING_PRESETS.get(ruleset, SCORING_PRESETS["uspsa_minor"])


def default_score_letter_for_ruleset(ruleset: str) -> ScoreLetter:
    preset = get_scoring_preset(ruleset)
    if preset.score_options:
        first_option = preset.score_options[0]
        try:
            return ScoreLetter(first_option)
        except ValueError:
            pass
    return ScoreLetter.A


def default_score_mark_for_ruleset(ruleset: str) -> ScoreMark:
    return ScoreMark(letter=default_score_letter_for_ruleset(ruleset))


def penalty_field_short_label(field_id: str, fallback_label: str = "") -> str:
    return PENALTY_FIELD_SHORT_LABELS.get(field_id, fallback_label or field_id.replace("_", " "))


def scoring_color_key(
    letter: str,
    penalty_counts: dict[str, float] | None = None,
    *,
    penalty_field_ids: list[str] | tuple[str, ...] | None = None,
) -> str:
    return str(letter).strip()


def _scoring_color_options(preset: ScoringPreset) -> list[dict[str, object]]:
    options: list[dict[str, object]] = []
    seen_tokens: set[str] = set()

    def add_option(token: str, description: str = "") -> None:
        normalized_token = str(token).strip()
        if not normalized_token or normalized_token in seen_tokens:
            return
        seen_tokens.add(normalized_token)
        options.append(
            {
                "key": normalized_token,
                "label": normalized_token,
                "description": description,
            }
        )

    for letter in preset.score_options:
        add_option(letter, "Score token")
    for field in preset.penalty_fields:
        add_option(penalty_field_short_label(field.id, field.label), field.label)
    return options


def apply_scoring_preset(project: Project, ruleset: str) -> None:
    preset = get_scoring_preset(ruleset)
    project.scoring.ruleset = preset.id
    project.scoring.point_map = dict(preset.point_map)
    valid_fields = {field.id for field in preset.penalty_fields}
    project.scoring.penalty_counts = {
        key: value
        for key, value in project.scoring.penalty_counts.items()
        if key in valid_fields
    }
    ensure_default_shot_scores(project)


def _shot_score_total(project: Project) -> float:
    if project.scoring.imported_stage is not None:
        return float(project.scoring.imported_stage.aggregate_points)
    default_score = default_score_mark_for_ruleset(project.scoring.ruleset)
    return sum(
        project.scoring.point_map.get((shot.score or default_score).letter.value, 0)
        for shot in project.analysis.shots
    )


def _shot_penalty_total(project: Project, preset: ScoringPreset) -> float:
    if project.scoring.imported_stage is not None:
        return float(project.scoring.imported_stage.shot_penalties)
    default_score = default_score_mark_for_ruleset(project.scoring.ruleset)
    return sum(
        preset.score_penalty_map.get((shot.score or default_score).letter.value, 0)
        + sum(
            field.value * max(0.0, float((shot.score or default_score).penalty_counts.get(field.id, 0)))
            for field in preset.penalty_fields
        )
        for shot in project.analysis.shots
    )


def _field_penalty_total(project: Project, preset: ScoringPreset) -> float:
    return sum(
        max(0.0, float(project.scoring.penalty_counts.get(field.id, 0))) * field.value
        for field in preset.penalty_fields
    )


def total_penalties(project: Project, preset: ScoringPreset | None = None) -> float:
    active_preset = preset or get_scoring_preset(project.scoring.ruleset)
    return (
        float(project.scoring.penalties)
        + _shot_penalty_total(project, active_preset)
        + _field_penalty_total(project, active_preset)
    )


def _format_overlay_stat(value: float | None, *, decimals: int = 2) -> str:
    if value is None:
        return ""
    rounded = round(float(value))
    if abs(float(value) - rounded) < 1e-9:
        return str(int(rounded))
    return f"{float(value):.{decimals}f}".rstrip("0").rstrip(".")


def format_imported_stage_overlay_text(
    imported_stage: ImportedStageScore | None,
    *,
    raw_seconds: float | None = None,
    final_time: float | None = None,
) -> str:
    if imported_stage is None:
        return ""

    display_raw_seconds = (
        float(raw_seconds)
        if raw_seconds is not None
        else (
            float(imported_stage.raw_seconds)
            if imported_stage.raw_seconds is not None
            else None
        )
    )
    display_final_time = (
        float(final_time)
        if final_time is not None
        else (
            float(imported_stage.final_time)
            if imported_stage.final_time is not None
            else None
        )
    )

    lines = ["Imported"]
    if display_raw_seconds is not None:
        lines.append(f"Raw {display_raw_seconds:.2f}")

    if imported_stage.match_type == "idpa":
        lines.append(f"PD {_format_overlay_stat(imported_stage.aggregate_points)}")
        if display_final_time is not None:
            lines.append(f"Final {display_final_time:.2f}")
        return "\n".join(lines)

    points_value = (
        float(imported_stage.total_points)
        if imported_stage.total_points is not None
        else float(imported_stage.aggregate_points)
    )
    lines.append(f"Points {_format_overlay_stat(points_value)}")

    hit_factor_value = imported_stage.hit_factor
    if hit_factor_value is None and imported_stage.total_points is not None and display_raw_seconds:
        if display_raw_seconds > 0:
            hit_factor_value = max(0.0, float(imported_stage.total_points)) / display_raw_seconds
    if hit_factor_value is not None:
        lines.append(f"HF {float(hit_factor_value):.4f}")
    return "\n".join(lines)


def calculate_hit_factor(project: Project) -> float | None:
    preset = get_scoring_preset(project.scoring.ruleset)
    raw_ms = raw_time_ms(project)
    imported_stage = project.scoring.imported_stage
    video_raw_seconds = None if raw_ms is None else raw_ms / 1000.0
    raw_seconds = (
        video_raw_seconds
        if video_raw_seconds is not None
        else (
            float(imported_stage.raw_seconds)
            if imported_stage is not None and imported_stage.raw_seconds is not None
            else None
        )
    )
    if (
        not project.scoring.enabled
        or preset.mode != "hit_factor"
        or raw_seconds is None
        or raw_seconds <= 0
    ):
        return None
    if imported_stage is not None:
        if imported_stage.total_points is not None:
            return max(0.0, float(imported_stage.total_points)) / raw_seconds
        if imported_stage.hit_factor is not None and video_raw_seconds is None:
            return float(imported_stage.hit_factor)

    adjusted_points = max(0.0, _shot_score_total(project) - total_penalties(project, preset))
    if adjusted_points == 0:
        return 0.0
    return adjusted_points / raw_seconds


def calculate_scoring_summary(project: Project) -> dict[str, object]:
    preset = get_scoring_preset(project.scoring.ruleset)
    raw_ms = raw_time_ms(project)
    imported_stage = project.scoring.imported_stage
    video_raw_seconds = None if raw_ms is None else raw_ms / 1000.0
    official_raw_seconds = (
        float(imported_stage.raw_seconds)
        if imported_stage is not None and imported_stage.raw_seconds is not None
        else None
    )
    raw_seconds = (
        video_raw_seconds
        if video_raw_seconds is not None
        else official_raw_seconds
    )
    shot_points = _shot_score_total(project)
    shot_penalties = _shot_penalty_total(project, preset)
    field_penalties = _field_penalty_total(project, preset)
    total_penalty_value = total_penalties(project, preset)
    hit_factor_value = calculate_hit_factor(project)
    official_final_time = (
        float(imported_stage.final_time)
        if imported_stage is not None and imported_stage.final_time is not None
        else None
    )
    computed_final_time = (
        None
        if preset.mode == "hit_factor" or raw_seconds is None
        else max(0.0, raw_seconds + shot_points + total_penalty_value)
    )
    summary: dict[str, object] = {
        "enabled": project.scoring.enabled,
        "ruleset": preset.id,
        "ruleset_name": preset.name,
        "sport": preset.sport,
        "mode": preset.mode,
        "description": preset.description,
        "penalty_label": preset.penalty_label,
        "score_options": list(preset.score_options),
        "scoring_color_options": _scoring_color_options(preset),
        "score_values": dict(preset.point_map),
        "score_penalties": dict(preset.score_penalty_map),
        "penalty_fields": [
            {**asdict(field), "count": project.scoring.penalty_counts.get(field.id, 0)}
            for field in preset.penalty_fields
        ],
        "raw_seconds": raw_seconds,
        "official_raw_seconds": official_raw_seconds,
        "raw_delta_seconds": (
            None
            if raw_seconds is None or official_raw_seconds is None
            else raw_seconds - official_raw_seconds
        ),
        "shot_points": shot_points,
        "penalties": project.scoring.penalties,
        "shot_penalties": shot_penalties,
        "field_penalties": field_penalties,
        "total_penalties": total_penalty_value,
        "hit_factor": hit_factor_value,
        "final_time": computed_final_time,
        "official_final_time": official_final_time,
        "final_delta_seconds": (
            None
            if computed_final_time is None or official_final_time is None
            else computed_final_time - official_final_time
        ),
        "imported_stage": None if imported_stage is None else asdict(imported_stage),
        "imported_overlay_text": format_imported_stage_overlay_text(
            imported_stage,
            raw_seconds=raw_seconds,
            final_time=computed_final_time,
        ),
        "display_label": "Hit Factor" if preset.mode == "hit_factor" else "Final",
        "display_value": "--",
    }
    if not project.scoring.enabled or raw_seconds is None:
        return summary
    if preset.mode == "hit_factor":
        value = hit_factor_value
        summary["display_value"] = "--" if value is None else f"{float(value):.2f}"
        return summary

    if computed_final_time is not None:
        summary["display_value"] = f"{computed_final_time:.2f}"
    return summary


def assign_score(
    shot: ShotEvent,
    letter: ScoreLetter | None = None,
    penalty_counts: dict[str, float] | None = None,
) -> None:
    if shot.score is None:
        shot.score = ScoreMark(letter=letter or ScoreLetter.A)
    elif letter is not None:
        shot.score.letter = letter
    if penalty_counts is not None and shot.score is not None:
        shot.score.penalty_counts = {
            str(key): max(0.0, float(value))
            for key, value in penalty_counts.items()
            if max(0.0, float(value)) > 0
        }


def ensure_default_shot_scores(project: Project) -> None:
    default_score = default_score_mark_for_ruleset(project.scoring.ruleset)
    preset = get_scoring_preset(project.scoring.ruleset)
    valid_letters = {str(option) for option in preset.score_options}
    valid_fields = {field.id for field in preset.penalty_fields}
    for shot in project.analysis.shots:
        if shot.score is None:
            shot.score = ScoreMark(letter=default_score.letter)
            continue
        if shot.score.letter.value not in valid_letters:
            shot.score.letter = default_score.letter
        shot.score.penalty_counts = {
            str(key): max(0.0, float(value))
            for key, value in shot.score.penalty_counts.items()
            if key in valid_fields and max(0.0, float(value)) > 0
        }


def set_score_position(shot: ShotEvent, x_norm: float, y_norm: float) -> None:
    if shot.score is None:
        shot.score = ScoreMark()
    shot.score.x_norm = x_norm
    shot.score.y_norm = y_norm


def shot_display_time_ms(project: Project, shot_time_ms: int) -> int:
    normalized_shot_time = max(0, int(shot_time_ms))
    fps = float(getattr(project.primary_video, "fps", 0) or 0)
    if fps <= 0:
        return normalized_shot_time
    frame_duration_ms = 1000.0 / fps
    frame_index = math.ceil((normalized_shot_time / frame_duration_ms) - 1e-9)
    frame_boundary_ms = math.ceil((frame_index * frame_duration_ms) - 1e-9)
    return max(normalized_shot_time, int(frame_boundary_ms))


def current_shot_index(project: Project, position_ms: int) -> int | None:
    current_index = None
    for index, shot in enumerate(project.analysis.shots):
        if shot_display_time_ms(project, shot.time_ms) <= position_ms:
            current_index = index
        else:
            break
    return current_index
