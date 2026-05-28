from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "testing" / "run_test_suite.py"
SUITE_TAXONOMY = ROOT / "scripts" / "testing" / "test_suite_taxonomy.json"


def run_runner(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_runner_lists_available_suites_as_json() -> None:
    result = run_runner("--list", "--format", "json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    suite_names = [suite["name"] for suite in payload["suites"]]
    suites_by_name = {suite["name"]: suite for suite in payload["suites"]}
    assert "analysis" in suite_names
    assert "browser" in suite_names
    assert "pane-project" in suite_names
    assert "pane-match" in suite_names
    assert "pane-performance" in suite_names
    assert "pane-settings" in suite_names
    assert "pane-metrics" in suite_names
    assert "scripts" in suite_names
    assert suites_by_name["browser"]["taxonomy_support"] == [
        "TAX-0",
        "TAX-1",
        "TAX-2",
        "TAX-5",
    ]
    assert suites_by_name["browser"]["support_surface_ids"] == [
        "surface.landing",
        "surface.shared_shell",
        "surface.stage.compose",
        "surface.stage.scoring",
        "surface.stage.splits_waveform",
        "surface.stage.markers_review_overlay",
        "surface.stage.export",
        "surface.stage.shotml",
    ]
    assert suites_by_name["browser"]["support_manifest_refs"] == [
        "scripts/testing/pane_feature_manifests.json"
    ]
    assert suites_by_name["pane-project"]["group"] == "pane"
    assert suites_by_name["pane-project"]["taxonomy_support"] == ["TAX-0", "TAX-1"]
    assert suites_by_name["pane-project"]["pane_ids"] == ["pane.project"]
    assert suites_by_name["pane-project"]["pane_manifest_refs"] == [
        "scripts/testing/pane_feature_manifests.json"
    ]
    assert len(suites_by_name["pane-project"]["support_target_exceptions"]) == 4
    assert {
        exception["surface_id"]
        for exception in suites_by_name["pane-project"]["support_target_exceptions"]
    } == {"surface.landing"}
    assert suites_by_name["pane-match"]["pane_ids"] == ["pane.match"]
    assert suites_by_name["pane-performance"]["pane_ids"] == ["pane.performance"]
    assert suites_by_name["pane-settings"]["taxonomy_support"] == ["TAX-0", "TAX-1"]
    assert suites_by_name["pane-settings"]["pane_ids"] == ["pane.settings"]
    assert suites_by_name["pane-settings"]["pane_manifest_refs"] == [
        "scripts/testing/pane_feature_manifests.json"
    ]
    assert suites_by_name["pane-metrics"]["taxonomy_support"] == ["TAX-0", "TAX-1"]
    assert suites_by_name["pane-metrics"]["pane_ids"] == ["pane.metrics"]
    assert suites_by_name["pane-metrics"]["pane_manifest_refs"] == [
        "scripts/testing/pane_feature_manifests.json"
    ]


def test_runner_catalog_matches_machine_readable_suite_taxonomy_targets() -> None:
    result = run_runner("--list", "--format", "json")

    assert result.returncode == 0
    catalog = {suite["name"]: suite for suite in json.loads(result.stdout)["suites"]}
    taxonomy = {
        suite["name"]: suite
        for suite in json.loads(SUITE_TAXONOMY.read_text(encoding="utf-8"))["suites"]
    }

    assert set(catalog) == set(taxonomy)
    for suite_name, taxonomy_suite in taxonomy.items():
        catalog_suite = catalog[suite_name]
        assert catalog_suite["label"] == taxonomy_suite["label"]
        assert catalog_suite["description"] == taxonomy_suite["description"]
        assert catalog_suite["targets"] == taxonomy_suite["targets"]
        assert catalog_suite["default_selected"] == taxonomy_suite["include_in_default"]
        for key in (
            "group",
            "taxonomy_support",
            "pane_ids",
            "pane_manifest_refs",
            "support_surface_ids",
            "support_manifest_refs",
            "support_target_exceptions",
        ):
            if key in taxonomy_suite:
                assert catalog_suite[key] == taxonomy_suite[key]
            else:
                assert key not in catalog_suite


def test_runner_dry_run_supports_opt_in_pane_suite_targets_as_json() -> None:
    result = run_runner(
        "--suite",
        "pane-match",
        "--mode",
        "all-together",
        "--format",
        "json",
        "--dry-run",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["summary"]["planned"] == 1
    assert payload["runs"][0]["suite_names"] == ["pane-match"]
    assert "tests/browser/test_workspace_flows.py" in payload["runs"][0]["targets"]
    assert (
        "tests/browser/test_browser_interactions.py::test_match_workspace_open_button_uses_picker_and_loads_saved_workspace"
        in payload["runs"][0]["targets"]
    )


def test_runner_dry_run_expands_browser_suite_one_by_one_as_json() -> None:
    result = run_runner(
        "--suite", "browser", "--mode", "one-by-one", "--format", "json", "--dry-run"
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    expected_browser_targets = {
        (path.relative_to(ROOT).as_posix(),)
        for path in sorted((ROOT / "tests" / "browser").rglob("test_*.py"))
    }

    assert payload["summary"]["dry_run"] is True
    assert payload["summary"]["planned"] == len(expected_browser_targets)
    assert payload["summary"]["total_runs"] == len(expected_browser_targets)
    assert {run["status"] for run in payload["runs"]} == {"planned"}
    assert {tuple(run["targets"]) for run in payload["runs"]} == expected_browser_targets


def test_runner_dry_run_writes_raw_and_json_output_files(tmp_path: Path) -> None:
    raw_output = tmp_path / "test-plan.raw.txt"
    json_output = tmp_path / "test-plan.json"

    result = run_runner(
        "--suite",
        "cli",
        "--mode",
        "all-together",
        "--dry-run",
        "--raw-output",
        str(raw_output),
        "--json-output",
        str(json_output),
    )

    assert result.returncode == 0
    assert raw_output.is_file()
    assert json_output.is_file()
    assert "tests/cli" in raw_output.read_text(encoding="utf-8")
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["summary"]["planned"] == 1
    assert payload["runs"][0]["targets"] == ["tests/cli"]
