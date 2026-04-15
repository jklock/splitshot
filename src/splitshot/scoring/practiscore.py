from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from splitshot.domain.models import ImportedStageScore


@dataclass(frozen=True, slots=True)
class PractiScoreStageImport:
    ruleset: str
    manual_penalties: float
    penalty_counts: dict[str, float]
    imported_stage: ImportedStageScore


@dataclass(frozen=True, slots=True)
class PractiScoreContext:
    match_type: str
    stage_number: int
    competitor_name: str
    competitor_place: int | None = None


@dataclass(frozen=True, slots=True)
class _HitFactorReport:
    competitor_rows: list[dict[str, str]]
    stage_rows: dict[str, dict[str, str]]
    stage_results: list[dict[str, str]]


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


def infer_practiscore_context(
    path: str | Path,
    match_type: str | None = None,
    stage_number: int | None = None,
    competitor_name: str | None = None,
    competitor_place: int | None = None,
) -> PractiScoreContext:
    results_path = Path(path)
    normalized_match_type = normalize_match_type(match_type) if match_type else _infer_match_type(results_path)
    clean_name = (competitor_name or "").strip()
    resolved_stage_number = None if stage_number is None else max(1, int(stage_number))

    if normalized_match_type == "idpa":
        rows = _load_idpa_rows(results_path)
        competitor_row = _select_competitor_row(
            rows,
            clean_name or None,
            competitor_place,
            place_key="Place",
            first_name_key="First Name",
            last_name_key="Last Name",
        )
        if resolved_stage_number is None:
            resolved_stage_number = _infer_idpa_stage_number(competitor_row, rows)
        return PractiScoreContext(
            match_type=normalized_match_type,
            stage_number=resolved_stage_number,
            competitor_name=_row_name(competitor_row, "First Name", "Last Name"),
            competitor_place=_int_or_none(competitor_row.get("Place")),
        )

    report = _load_hit_factor_report(results_path)
    competitor_row = _select_competitor_row(
        report.competitor_rows,
        clean_name or None,
        competitor_place,
        place_key="Place Overall",
        first_name_key="FirstName",
        last_name_key="LastName",
        reentry_key="Reentry",
    )
    if resolved_stage_number is None:
        resolved_stage_number = _infer_hit_factor_stage_number(report, competitor_row)
    return PractiScoreContext(
        match_type=normalized_match_type,
        stage_number=resolved_stage_number,
        competitor_name=_row_name(competitor_row, "FirstName", "LastName"),
        competitor_place=_int_or_none(competitor_row.get("Place Overall")),
    )


def _infer_match_type(path: Path) -> str:
    if path.suffix.lower() == ".csv":
        rows = _load_idpa_rows(path)
        headers = [str(header or "").strip().lower() for header in (rows[0].keys() if rows else [])]
        if headers and (
            "idpa id" in headers
            or "hits on non-threat" in headers
            or any(header.startswith("stage 1 ") for header in headers)
        ):
            return "idpa"

    text = path.read_text(encoding="utf-8", errors="replace")
    region_match = re.search(r"^\$INFO\s+Region:(?P<region>\w+)", text, re.MULTILINE)
    if region_match:
        region = region_match.group("region").strip().lower()
        if region in {"uspsa", "ipsc", "idpa"}:
            return region
    if "place overall" in text.lower() and "power factor" in text.lower():
        return "uspsa"
    raise ValueError("Could not infer the PractiScore match type from the selected file.")


def _load_idpa_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_hit_factor_report(path: Path) -> _HitFactorReport:
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

    return _HitFactorReport(
        competitor_rows=competitor_rows,
        stage_rows=stage_rows,
        stage_results=stage_results,
    )


def _select_competitor_row(
    rows: list[dict[str, str]],
    competitor_name: str | None,
    competitor_place: int | None,
    *,
    place_key: str,
    first_name_key: str,
    last_name_key: str,
    reentry_key: str | None = None,
) -> dict[str, str]:
    clean_name = (competitor_name or "").strip()
    if clean_name:
        return _find_competitor_row(
            rows,
            clean_name,
            competitor_place,
            place_key=place_key,
            first_name_key=first_name_key,
            last_name_key=last_name_key,
        )
    if competitor_place is not None:
        candidates = [row for row in rows if _int_or_none(row.get(place_key)) == competitor_place]
        if candidates:
            return _prefer_non_reentry(candidates, reentry_key)
        raise ValueError(f"Could not find place {competitor_place} in the results file.")
    return _default_competitor_row(
        rows,
        place_key=place_key,
        first_name_key=first_name_key,
        last_name_key=last_name_key,
    )


def _default_competitor_row(
    rows: list[dict[str, str]],
    *,
    place_key: str,
    first_name_key: str,
    last_name_key: str,
) -> dict[str, str]:
    if not rows:
        raise ValueError("No competitor results were found in the PractiScore export.")
    candidates = sorted(
        rows,
        key=lambda row: (
            _int_or_none(row.get(place_key)) is None,
            _int_or_none(row.get(place_key)) or 0,
            _normalize_name(_row_name(row, first_name_key, last_name_key)),
        ),
    )
    return candidates[0]


def _prefer_non_reentry(rows: list[dict[str, str]], reentry_key: str | None) -> dict[str, str]:
    if reentry_key is None:
        return rows[0]
    non_reentries = [row for row in rows if str(row.get(reentry_key, "No")).strip().lower() != "yes"]
    return non_reentries[0] if non_reentries else rows[0]


def _idpa_stage_numbers(rows: list[dict[str, str]]) -> list[int]:
    if not rows:
        raise ValueError("No competitor results were found in the PractiScore export.")
    stage_numbers = sorted(
        {
            int(match.group(1))
            for key in rows[0].keys()
            if (match := re.match(r"Stage (\d+) ", key))
        }
    )
    if not stage_numbers:
        raise ValueError("No stage columns were found in the PractiScore export.")
    return stage_numbers


def _infer_idpa_stage_number(row: dict[str, str], rows: list[dict[str, str]]) -> int:
    stage_numbers = _idpa_stage_numbers(rows)
    for stage_number in stage_numbers:
        if str(row.get(f"Stage {stage_number} Time", "")).strip():
            return stage_number
    for stage_number in stage_numbers:
        prefix = f"Stage {stage_number} "
        if any(str(value).strip() for key, value in row.items() if key.startswith(prefix)):
            return stage_number
    return stage_numbers[0]


def _infer_hit_factor_stage_number(report: _HitFactorReport, competitor_row: dict[str, str]) -> int:
    competitor_id = str(competitor_row.get("Comp", "")).strip()
    if competitor_id:
        stage_numbers = sorted(
            {
                int(stage)
                for row in report.stage_results
                if str(row.get("Comp", "")).strip() == competitor_id
                and _int_or_none(row.get("Stage")) is not None
                for stage in [row.get("Stage")]
            }
        )
        if stage_numbers:
            return stage_numbers[0]
    stage_numbers = sorted(
        {
            int(stage)
            for stage in report.stage_rows.keys()
            if _int_or_none(stage) is not None
        }
    )
    if stage_numbers:
        return stage_numbers[0]
    stage_numbers = sorted(
        {
            int(stage)
            for row in report.stage_results
            if _int_or_none(row.get("Stage")) is not None
            for stage in [row.get("Stage")]
        }
    )
    if stage_numbers:
        return stage_numbers[0]
    raise ValueError("No stage results were found in the PractiScore export.")


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
    rows = _load_idpa_rows(path)
    row = _find_competitor_row(
        rows,
        competitor_name,
        competitor_place,
        place_key="Place",
        first_name_key="First Name",
        last_name_key="Last Name",
    )
    stage_prefix = f"Stage {stage_number}"
    final_time = _required_float(row.get(f"{stage_prefix} Time"), f"{stage_prefix} Time")
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
    other_penalties = sum(
        IDPA_PENALTY_SECONDS[key] * value
        for key, value in penalty_counts.items()
    )
    raw_seconds = max(0.0, final_time - points_down - other_penalties)
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
    report = _load_hit_factor_report(path)
    competitor_rows = report.competitor_rows
    stage_rows = report.stage_rows
    stage_results = report.stage_results

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
    return float(str(value).strip().replace(",", ""))


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