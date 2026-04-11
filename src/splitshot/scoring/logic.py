from __future__ import annotations

from dataclasses import asdict, dataclass

from splitshot.domain.models import Project, ScoreLetter, ScoreMark, ShotEvent
from splitshot.timeline.model import raw_time_ms


@dataclass(frozen=True, slots=True)
class ScoringPreset:
    id: str
    name: str
    sport: str
    mode: str
    description: str
    point_map: dict[str, int]
    penalty_label: str


SCORING_PRESETS: dict[str, ScoringPreset] = {
    "uspsa_minor": ScoringPreset(
        id="uspsa_minor",
        name="USPSA / IPSC Minor",
        sport="USPSA, IPSC, PCSL",
        mode="hit_factor",
        description="Hit Factor: scored points divided by raw beep-to-final-shot time.",
        point_map={
            ScoreLetter.A.value: 5,
            ScoreLetter.C.value: 3,
            ScoreLetter.D.value: 1,
            ScoreLetter.M.value: 0,
            ScoreLetter.NS.value: 0,
            ScoreLetter.MU.value: 0,
            ScoreLetter.M_NS.value: 0,
        },
        penalty_label="Penalty points",
    ),
    "uspsa_major": ScoringPreset(
        id="uspsa_major",
        name="USPSA / IPSC Major",
        sport="USPSA, IPSC, PCSL",
        mode="hit_factor",
        description="Hit Factor with major power-factor C/D values.",
        point_map={
            ScoreLetter.A.value: 5,
            ScoreLetter.C.value: 4,
            ScoreLetter.D.value: 2,
            ScoreLetter.M.value: 0,
            ScoreLetter.NS.value: 0,
            ScoreLetter.MU.value: 0,
            ScoreLetter.M_NS.value: 0,
        },
        penalty_label="Penalty points",
    ),
    "idpa_time_plus": ScoringPreset(
        id="idpa_time_plus",
        name="IDPA Time Plus",
        sport="IDPA",
        mode="time_plus",
        description="Final score estimate: raw time plus points-down and penalty seconds.",
        point_map={
            ScoreLetter.A.value: 0,
            ScoreLetter.C.value: 1,
            ScoreLetter.D.value: 3,
            ScoreLetter.M.value: 5,
            ScoreLetter.NS.value: 5,
            ScoreLetter.MU.value: 0,
            ScoreLetter.M_NS.value: 10,
        },
        penalty_label="Penalty seconds",
    ),
    "steel_challenge": ScoringPreset(
        id="steel_challenge",
        name="Steel Challenge",
        sport="Steel Challenge",
        mode="time_plus",
        description="Final score estimate: raw string time plus miss/penalty seconds.",
        point_map={
            ScoreLetter.A.value: 0,
            ScoreLetter.C.value: 0,
            ScoreLetter.D.value: 0,
            ScoreLetter.M.value: 3,
            ScoreLetter.NS.value: 0,
            ScoreLetter.MU.value: 0,
            ScoreLetter.M_NS.value: 3,
        },
        penalty_label="Penalty seconds",
    ),
    "three_gun_time_plus": ScoringPreset(
        id="three_gun_time_plus",
        name="3-Gun / UML Time Plus",
        sport="3-Gun, UML, Multigun",
        mode="time_plus",
        description="Final score estimate: raw time plus hit/miss/procedural penalty seconds.",
        point_map={
            ScoreLetter.A.value: 0,
            ScoreLetter.C.value: 0,
            ScoreLetter.D.value: 0,
            ScoreLetter.M.value: 5,
            ScoreLetter.NS.value: 5,
            ScoreLetter.MU.value: 0,
            ScoreLetter.M_NS.value: 10,
        },
        penalty_label="Penalty seconds",
    ),
}


def scoring_presets_for_api() -> list[dict[str, object]]:
    return [asdict(preset) for preset in SCORING_PRESETS.values()]


def get_scoring_preset(ruleset: str) -> ScoringPreset:
    return SCORING_PRESETS.get(ruleset, SCORING_PRESETS["uspsa_minor"])


def apply_scoring_preset(project: Project, ruleset: str) -> None:
    preset = get_scoring_preset(ruleset)
    project.scoring.ruleset = preset.id
    project.scoring.point_map = dict(preset.point_map)


def _shot_score_total(project: Project) -> int:
    return sum(
        project.scoring.point_map.get(shot.score.letter.value, 0)
        for shot in project.analysis.shots
        if shot.score is not None
    )


def calculate_hit_factor(project: Project) -> float | None:
    raw_ms = raw_time_ms(project)
    if (
        not project.scoring.enabled
        or get_scoring_preset(project.scoring.ruleset).mode != "hit_factor"
        or raw_ms is None
        or raw_ms <= 0
    ):
        return None

    adjusted_points = max(0, _shot_score_total(project) - project.scoring.penalties)
    if adjusted_points == 0:
        return 0.0
    return adjusted_points / (raw_ms / 1000.0)


def calculate_scoring_summary(project: Project) -> dict[str, object]:
    preset = get_scoring_preset(project.scoring.ruleset)
    raw_ms = raw_time_ms(project)
    raw_seconds = None if raw_ms is None else raw_ms / 1000.0
    shot_points = _shot_score_total(project)
    summary: dict[str, object] = {
        "enabled": project.scoring.enabled,
        "ruleset": preset.id,
        "ruleset_name": preset.name,
        "sport": preset.sport,
        "mode": preset.mode,
        "description": preset.description,
        "penalty_label": preset.penalty_label,
        "raw_seconds": raw_seconds,
        "shot_points": shot_points,
        "penalties": project.scoring.penalties,
        "hit_factor": calculate_hit_factor(project),
        "final_time": None,
        "display_label": "Hit Factor" if preset.mode == "hit_factor" else "Final Time",
        "display_value": "--",
    }
    if not project.scoring.enabled or raw_seconds is None:
        return summary
    if preset.mode == "hit_factor":
        value = summary["hit_factor"]
        summary["display_value"] = "--" if value is None else f"{float(value):.2f}"
        return summary

    final_time = max(0.0, raw_seconds + shot_points + project.scoring.penalties)
    summary["final_time"] = final_time
    summary["display_value"] = f"{final_time:.2f}"
    return summary


def assign_score(shot: ShotEvent, letter: ScoreLetter) -> None:
    shot.score = ScoreMark(letter=letter)


def set_score_position(shot: ShotEvent, x_norm: float, y_norm: float) -> None:
    if shot.score is None:
        shot.score = ScoreMark()
    shot.score.x_norm = x_norm
    shot.score.y_norm = y_norm


def current_shot_index(project: Project, position_ms: int) -> int | None:
    current_index = None
    for index, shot in enumerate(project.analysis.shots):
        if shot.time_ms <= position_ms:
            current_index = index
        else:
            break
    return current_index
