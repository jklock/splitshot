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
    assert comparison["divisionClassification"]["count"] == 2
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
