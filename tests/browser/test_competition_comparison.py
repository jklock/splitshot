from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


MODULE_URI = (Path("src/splitshot/browser/static/lib/competition-comparison.js").resolve()).as_uri()


def _compare(payload: dict) -> dict:
    script = f"""
      import {{ buildCompetitionComparison }} from {json.dumps(MODULE_URI)};
      console.log(JSON.stringify(buildCompetitionComparison({json.dumps(payload)})));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _standings(payload: dict) -> dict:
    script = f"""
      import {{ buildFinalStandingsComparison }} from {json.dumps(MODULE_URI)};
      console.log(JSON.stringify(buildFinalStandingsComparison({json.dumps(payload)})));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _identity_labels(payload: dict) -> dict:
    script = f"""
      import {{ competitionIdentityLabels }} from {json.dumps(MODULE_URI)};
      console.log(JSON.stringify(competitionIdentityLabels({json.dumps(payload)})));
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


@pytest.mark.parametrize(
    ("match_type", "result_key", "selected_result", "leader_result"),
    [
        (
            "idpa",
            "final_time",
            {"final_time": 12.5, "hit_factor": 9.0},
            {"final_time": 10.0, "hit_factor": 1.0},
        ),
        (
            "uspsa",
            "hit_factor",
            {"final_time": 8.0, "hit_factor": 5.0},
            {"final_time": 20.0, "hit_factor": 7.0},
        ),
    ],
)
def test_competition_comparison_uses_sport_result_and_dynamic_cohorts(
    match_type: str,
    result_key: str,
    selected_result: dict,
    leader_result: dict,
) -> None:
    comparison = _compare(
        {
            "scoring": {
                "match_type": match_type,
                "competitor_name": "Selected Shooter",
                "division": " Carry Optics ",
                "classification": "Expert",
            },
            "importedStage": {
                "competitor_name": "Selected Shooter",
                "division": "stale division",
                "classification": "stale class",
                **selected_result,
            },
            "competitors": [
                {
                    "name": "Leader",
                    "division": "carry optics",
                    "classification": "EXPERT",
                    **leader_result,
                },
                {
                    "name": "Other Division",
                    "division": "Limited",
                    "classification": "Expert",
                    **leader_result,
                },
                {
                    "name": "Other Class",
                    "division": "Carry Optics",
                    "classification": "Master",
                    **leader_result,
                },
                {"name": "No Result", "division": "Carry Optics", "classification": "Expert"},
            ],
        }
    )

    assert comparison["resultKey"] == result_key
    assert comparison["identity"]["division"] == "Carry Optics"
    assert comparison["identity"]["classification"] == "Expert"
    assert comparison["overall"]["count"] == 4
    assert comparison["division"]["count"] == 3
    assert comparison["classification"]["count"] == 3
    assert comparison["overall"]["rank"] == 4


def test_competition_comparison_uses_competition_tie_ranking() -> None:
    comparison = _compare(
        {
            "scoring": {"match_type": "idpa", "competitor_name": "Selected"},
            "importedStage": {"competitor_name": "Selected", "final_time": 12.0},
            "competitors": [
                {"name": "First A", "final_time": 10.0},
                {"name": "First B", "final_time": 10.0},
            ],
        }
    )
    assert comparison["overall"]["rank"] == 3
    assert comparison["overall"]["count"] == 3


def test_final_standings_uses_match_places_for_all_review_cohorts() -> None:
    comparison = _standings(
        {
            "scoring": {
                "competitor_name": "Selected",
                "division": "Carry Optics",
                "classification": "A",
            },
            "importedStage": {"competitor_name": "Selected", "competitor_place": 8},
            "competitors": [
                {"name": "Overall Leader", "place": 1, "division": "Limited", "classification": "M"},
                {"name": "Cohort Leader", "place": 3, "division": "carry optics", "classification": "a"},
                {"name": "Division Only", "place": 5, "division": "Carry Optics", "classification": "B"},
                {"name": "Class Only", "place": 6, "division": "Limited", "classification": "A"},
                {"name": "Tie", "place": 8, "division": "Carry Optics", "classification": "A"},
                {"name": "No Place", "division": "Carry Optics", "classification": "A"},
                {"name": " selected ", "place": 99, "division": "Limited", "classification": "M"},
            ],
        }
    )
    assert (comparison["overall"]["place"], comparison["overall"]["count"]) == (5, 6)
    assert (comparison["division"]["place"], comparison["division"]["count"]) == (3, 4)
    assert (comparison["classification"]["place"], comparison["classification"]["count"]) == (3, 4)


def test_final_standings_hides_selected_competitor_without_valid_place() -> None:
    comparison = _standings(
        {
            "scoring": {"competitor_name": "Selected", "division": "CO", "classification": "A"},
            "importedStage": {"competitor_name": "Selected", "competitor_place": 0},
            "competitors": [{"name": "Valid", "place": 1, "division": "CO", "classification": "A"}],
        }
    )
    assert comparison["overall"]["place"] is None
    assert comparison["division"]["place"] is None


@pytest.mark.parametrize(
    ("match_type", "division", "classification", "expected_division", "expected_class"),
    [
        ("idpa", "Stock Service Pistol", "Sharpshooter", "SSP", "SS"),
        ("idpa", "Carry Optics", "Novice", "CO", "NV"),
        ("uspsa", "Carry Optics", "Grand Master", "CO", "GM"),
        ("uspsa", "Single Stack", "Master", "SS", "M"),
    ],
)
def test_competition_identity_labels_use_sport_codes(
    match_type: str,
    division: str,
    classification: str,
    expected_division: str,
    expected_class: str,
) -> None:
    labels = _identity_labels(
        {
            "scoring": {
                "match_type": match_type,
                "division": division,
                "classification": classification,
            }
        }
    )
    assert labels["division"] == expected_division
    assert labels["classification"] == expected_class


def test_final_standings_matches_uspsa_division_codes_to_full_names() -> None:
    comparison = _standings(
        {
            "scoring": {
                "match_type": "uspsa",
                "competitor_name": "Selected",
                "division": "CO",
                "classification": "M",
            },
            "importedStage": {"competitor_name": "Selected", "competitor_place": 2},
            "competitors": [
                {
                    "name": "Division Peer",
                    "place": 1,
                    "division": "Carry Optics",
                    "classification": "Master",
                },
                {
                    "name": "Other Division",
                    "place": 3,
                    "division": "Limited",
                    "classification": "M",
                },
            ],
        }
    )
    assert (comparison["division"]["place"], comparison["division"]["count"]) == (2, 2)
    assert (comparison["classification"]["place"], comparison["classification"]["count"]) == (2, 3)
