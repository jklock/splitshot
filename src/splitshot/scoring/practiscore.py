from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from splitshot.domain.models import ImportedStageScore


@dataclass(frozen=True, slots=True)
class PractiScoreStageImport:
    ruleset: str
    manual_penalties: float
    penalty_counts: dict[str, float]
    imported_stage: ImportedStageScore


IDPA_PENALTY_SECONDS = {
    "non_threats": 5.0,
    "procedural_errors": 3.0,
    "flagrant_penalties": 10.0,
    "failures_to_do_right": 20.0,
    "finger_pe": 3.0,
}


def normalize_match_type(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized not in {"uspsa", "ipsc", "idpa"}:
        raise ValueError("Match type must be USPSA, IPSC, or IDPA.")
    return normalized


def default_ruleset_for_match_type(match_type: str | None) -> str:
    normalized = normalize_match_type(match_type)
    if normalized == "idpa":
        return "idpa_time_plus"
    return f"{normalized}_minor"


def import_practiscore_stage(
    path: str | Path,
    match_type: str,
    stage_number: int,
    competitor_name: str,
    competitor_place: int | None = None,
    source_name: str | None = None,
) -> PractiScoreStageImport:
    stage = max(1, int(stage_number))
    normalized = normalize_match_type(match_type)
    results_path = Path(path)
    display_name = source_name or results_path.name
    clean_name = competitor_name.strip()
    if not clean_name:
        raise ValueError("Competitor name is required before importing PractiScore results.")
    if normalized == "idpa":
        return _import_idpa(results_path, display_name, stage, clean_name, competitor_place)
    return _import_hit_factor_report(
        results_path,
        display_name,
        normalized,
        stage,
        clean_name,
        competitor_place,
    )


def _import_idpa(
    path: Path,
    source_name: str,
    stage_number: int,
    competitor_name: str,
    competitor_place: int | None,
) -> PractiScoreStageImport:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    row = _find_competitor_row(
        rows,
        competitor_name,
        competitor_place,
        place_key="Place",
        first_name_key="First Name",
        last_name_key="Last Name",
    )
    stage_prefix = f"Stage {stage_number}"
    raw_seconds = _required_float(row.get(f"{stage_prefix} Time"), f"{stage_prefix} Time")
    points_down = _float_or_zero(row.get(f"{stage_prefix} PD"))
    non_threats = _float_or_zero(row.get(f"{stage_prefix} Hits on Non-Threat"))
    procedural_errors = _float_or_zero(row.get(f"{stage_prefix} Procedural Error"))
    failures_to_do_right = _float_or_zero(row.get(f"{stage_prefix} Failure to Do Right"))
    flagrant_penalties = _float_or_zero(row.get(f"{stage_prefix} Flagrant"))
    finger_penalties = _float_or_zero(row.get(f"{stage_prefix} Finger PE"))
    penalty_counts = {
        key: value
        for key, value in {
            "non_threats": non_threats,
            "procedural_errors": procedural_errors,
            "failures_to_do_right": failures_to_do_right,
            "flagrant_penalties": flagrant_penalties,
            "finger_pe": finger_penalties,
        }.items()
        if value
    }
    final_time = raw_seconds + points_down + sum(
        IDPA_PENALTY_SECONDS[key] * value
        for key, value in penalty_counts.items()
    )
    imported_stage = ImportedStageScore(
        source_name=source_name,
        source_path=str(path),
        match_type="idpa",
        competitor_name=_row_name(row, "First Name", "Last Name"),
        competitor_place=_int_or_none(row.get("Place")),
        stage_number=stage_number,
        stage_name=stage_prefix,
        division=str(row.get("Division", "")).strip(),
        classification=str(row.get("Class", "")).strip(),
        raw_seconds=raw_seconds,
        aggregate_points=points_down,
        shot_penalties=0.0,
        final_time=final_time,
        score_counts={"Points Down": points_down} if points_down else {},
    )
    return PractiScoreStageImport(
        ruleset="idpa_time_plus",
        manual_penalties=0.0,
        penalty_counts=penalty_counts,
        imported_stage=imported_stage,
    )


def _import_hit_factor_report(
    path: Path,
    source_name: str,
    match_type: str,
    stage_number: int,
    competitor_name: str,
    competitor_place: int | None,
) -> PractiScoreStageImport:
    competitor_headers: list[str] = []
    stage_headers: list[str] = []
    stage_result_headers: list[str] = []
    competitor_rows: list[dict[str, str]] = []
    stage_rows: dict[str, dict[str, str]] = {}
    stage_results: list[dict[str, str]] = []

    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("$"):
                continue
            if len(line) < 2 or line[1] != " ":
                continue
            prefix = line[0]
            values = next(csv.reader([line[2:]]))
            if prefix == "D":
                competitor_headers = values
            elif prefix == "E" and competitor_headers:
                competitor_rows.append(dict(zip(competitor_headers, values, strict=False)))
            elif prefix == "F":
                stage_headers = values
            elif prefix == "G" and stage_headers:
                stage_row = dict(zip(stage_headers, values, strict=False))
                stage_rows[str(stage_row.get("Number", "")).strip()] = stage_row
            elif prefix == "H":
                stage_result_headers = values
            elif prefix == "I" and stage_result_headers:
                stage_results.append(dict(zip(stage_result_headers, values, strict=False)))

    competitor_row = _find_competitor_row(
        competitor_rows,
        competitor_name,
        competitor_place,
        place_key="Place Overall",
        first_name_key="FirstName",
        last_name_key="LastName",
    )
    competitor_id = str(competitor_row.get("Comp", "")).strip()
    stage_key = str(stage_number)
    stage_result = next(
        (
            row
            for row in stage_results
            if str(row.get("Comp", "")).strip() == competitor_id
            and str(row.get("Stage", "")).strip() == stage_key
        ),
        None,
    )
    if stage_result is None:
        raise ValueError(
            f"No stage {stage_number} result was found for {competitor_name} in {source_name}."
        )
    power_factor = str(competitor_row.get("Power Factor", "Minor")).strip().lower()
    ruleset = f"{match_type}_{'major' if power_factor == 'major' else 'minor'}"
    misses = _float_or_zero(stage_result.get("Miss"))
    no_shoots = _float_or_zero(stage_result.get("No Shoot"))
    procedural_errors = _float_or_zero(stage_result.get("Procedural"))
    total_penalty = _float_or_zero(stage_result.get("Total Penalty"))
    total_points = _float_or_none(stage_result.get("Total Points"))
    miss_penalty = misses * 10.0
    no_shoot_penalty = no_shoots * 10.0
    procedural_penalty = procedural_errors * 10.0
    manual_penalties = max(0.0, total_penalty - miss_penalty - no_shoot_penalty - procedural_penalty)
    score_counts = {
        label: value
        for label, value in {
            "A": _float_or_zero(stage_result.get("A")),
            "B": _float_or_zero(stage_result.get("B")),
            "C": _float_or_zero(stage_result.get("C")),
            "D": _float_or_zero(stage_result.get("D")),
            "Miss": misses,
            "No Shoot": no_shoots,
        }.items()
        if value
    }
    stage_info = stage_rows.get(stage_key, {})
    imported_stage = ImportedStageScore(
        source_name=source_name,
        source_path=str(path),
        match_type=match_type,
        competitor_name=_row_name(competitor_row, "FirstName", "LastName"),
        competitor_place=_int_or_none(competitor_row.get("Place Overall")),
        stage_number=stage_number,
        stage_name=str(stage_info.get("Stage_name", "")).strip() or f"Stage {stage_number}",
        division=str(competitor_row.get("Division", "")).strip(),
        classification=str(competitor_row.get("Class", "")).strip(),
        power_factor=str(competitor_row.get("Power Factor", "")).strip(),
        raw_seconds=_required_float(stage_result.get("Time"), "Stage Time"),
        aggregate_points=_float_or_zero(stage_result.get("Raw Points")),
        total_points=total_points,
        shot_penalties=miss_penalty + no_shoot_penalty,
        hit_factor=_float_or_none(stage_result.get("Hit Factor")),
        stage_points=_float_or_none(stage_result.get("Stage Points")),
        stage_place=_int_or_none(stage_result.get("Stage Place")),
        score_counts=score_counts,
    )
    penalty_counts = {"procedural_errors": procedural_errors} if procedural_errors else {}
    return PractiScoreStageImport(
        ruleset=ruleset,
        manual_penalties=manual_penalties,
        penalty_counts=penalty_counts,
        imported_stage=imported_stage,
    )


def _find_competitor_row(
    rows: list[dict[str, str]],
    competitor_name: str,
    competitor_place: int | None,
    *,
    place_key: str,
    first_name_key: str,
    last_name_key: str,
) -> dict[str, str]:
    candidates = [
        row
        for row in rows
        if _name_matches(competitor_name, row.get(first_name_key, ""), row.get(last_name_key, ""))
    ]
    if competitor_place is not None:
        placed = [row for row in candidates if _int_or_none(row.get(place_key)) == competitor_place]
        if placed:
            candidates = placed
        elif candidates:
            raise ValueError(
                f"Found {competitor_name} in the results, but not with place {competitor_place}."
            )
    if not candidates:
        raise ValueError(f"Could not find {competitor_name} in the results file.")
    if len(candidates) == 1:
        return candidates[0]
    non_reentries = [row for row in candidates if str(row.get("Reentry", "No")).strip().lower() != "yes"]
    if len(non_reentries) == 1:
        return non_reentries[0]
    raise ValueError(
        f"Found multiple results for {competitor_name}. Enter the competitor place to disambiguate."
    )


def _name_matches(input_name: str, first_name: str, last_name: str) -> bool:
    target = _normalize_name(input_name)
    if not target:
        return False
    first = (first_name or "").strip()
    last = (last_name or "").strip()
    return target in {
        _normalize_name(f"{first} {last}"),
        _normalize_name(f"{last} {first}"),
        _normalize_name(f"{last}, {first}"),
    }


def _normalize_name(value: str) -> str:
    return "".join(char for char in value.lower() if char.isalnum())


def _row_name(row: dict[str, str], first_name_key: str, last_name_key: str) -> str:
    return f"{str(row.get(first_name_key, '')).strip()} {str(row.get(last_name_key, '')).strip()}".strip()


def _float_or_zero(value: str | None) -> float:
    return _float_or_none(value) or 0.0


def _float_or_none(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    return float(str(value).strip())


def _required_float(value: str | None, label: str) -> float:
    parsed = _float_or_none(value)
    if parsed is None:
        raise ValueError(f"{label} is missing from the PractiScore export.")
    return parsed


def _int_or_none(value: str | None) -> int | None:
    parsed = _float_or_none(value)
    if parsed is None:
        return None
    return int(parsed)