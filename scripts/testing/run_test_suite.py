"""Canonical grouped pytest runner for SplitShot suite-level local validation."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class SuiteDefinition:
    name: str
    label: str
    description: str
    targets: tuple[str, ...]
    include_in_default: bool = True


@dataclass(frozen=True, slots=True)
class PlannedRun:
    run_id: str
    suite_names: tuple[str, ...]
    suite_labels: tuple[str, ...]
    targets: tuple[str, ...]
    command: tuple[str, ...]


@dataclass(slots=True)
class RunResult:
    run_id: str
    suite_names: list[str]
    suite_labels: list[str]
    targets: list[str]
    command: list[str]
    status: str
    return_code: int | None
    duration_seconds: float
    stdout: str
    stderr: str


PANE_PROJECT_TARGETS: tuple[str, ...] = (
    "tests/browser/test_landing_page.py",
    "tests/browser/test_landing_backend_routes.py",
    "tests/browser/test_project_lifecycle_contracts.py",
    "tests/browser/test_practiscore_session_api.py",
    "tests/browser/test_practiscore_sync_controller.py",
    "tests/browser/test_browser_interactions.py::test_project_pane_practiscore_dashboard_button_opens_system_browser",
    "tests/browser/test_browser_interactions.py::test_project_pane_practiscore_and_primary_controls_enable_after_project_create",
    "tests/browser/test_browser_interactions.py::test_project_pane_manual_practiscore_file_import_remains_functional_with_active_project",
    "tests/browser/test_browser_interactions.py::test_project_pane_steel_challenge_import_uses_formatted_status_label",
    "tests/browser/test_browser_interactions.py::test_project_pane_practiscore_connect_route_updates_browser_state",
    "tests/browser/test_browser_interactions.py::test_project_pane_practiscore_remote_match_list_and_import_routes_update_browser_state",
    "tests/browser/test_browser_interactions.py::test_project_pane_practiscore_expired_match_list_updates_browser_state",
    "tests/browser/test_browser_interactions.py::test_project_pane_delete_project_confirmation_can_cancel",
    "tests/browser/test_browser_interactions.py::test_project_pane_keyboard_tab_order_advances_through_primary_controls",
    "tests/browser/test_browser_interactions.py::test_project_pane_output_hook_save_updates_selected_output_profile",
    "tests/browser/test_browser_interactions.py::test_project_pane_output_hook_close_hides_editor",
    "tests/browser/test_browser_interactions.py::test_project_pane_select_project_missing_dirs_shows_notice_and_creates_only_missing",
    "tests/browser/test_browser_interactions.py::test_landing_and_stage_empty_primary_import_buttons_work_without_saved_project",
    "tests/browser/test_browser_interactions.py::test_landing_recent_stage_rows_switch_surface_without_auto_open",
)

PANE_MATCH_TARGETS: tuple[str, ...] = (
    "tests/browser/test_workspace_flows.py",
    "tests/browser/test_workspace_export_and_recap.py",
    "tests/browser/test_browser_interactions.py::test_match_workspace_setup_once_uses_preview_before_apply",
    "tests/browser/test_browser_interactions.py::test_match_workspace_setup_once_dismiss_hides_banner",
    "tests/browser/test_browser_interactions.py::test_match_workspace_open_button_uses_picker_and_loads_saved_workspace",
    "tests/browser/test_browser_interactions.py::test_match_workspace_open_shows_loading_and_error_state_on_failure",
    "tests/browser/test_browser_interactions.py::test_match_workspace_new_from_empty_and_stage_add_select_remove_flow",
    "tests/browser/test_browser_interactions.py::test_match_workspace_save_button_uses_picker_for_first_save",
    "tests/browser/test_browser_interactions.py::test_match_workspace_save_shows_loading_and_error_state_on_failure",
    "tests/browser/test_browser_interactions.py::test_match_workspace_override_apply_and_reset_update_selected_stage",
    "tests/browser/test_browser_interactions.py::test_match_workspace_shared_defaults_apply_and_reset",
    "tests/browser/test_browser_interactions.py::test_match_workspace_stage_open_and_shell_return_restore_match_context",
    "tests/browser/test_browser_interactions.py::test_match_workspace_shell_keeps_selected_stage_detail_and_workflow_visible",
    "tests/browser/test_browser_interactions.py::test_match_workspace_preview_tiles_render_live_media_and_export_keeps_selected_stage_detail",
    "tests/browser/test_browser_interactions.py::test_match_workspace_recap_reports_success_and_error_states",
    "tests/browser/test_browser_interactions.py::test_match_workspace_batch_export_queue_select_all_none_and_start",
    "tests/browser/test_browser_interactions.py::test_match_workspace_batch_export_reports_errors_truthfully",
    "tests/browser/test_browser_interactions.py::test_match_settings_persist_locally_and_control_match_return_selection",
    "tests/browser/test_browser_interactions.py::test_match_stage_composite_controls_update_composite_state",
    "tests/browser/test_browser_interactions.py::test_match_stage_composite_cut_override_editor_updates_plan_detail",
)

PANE_PERFORMANCE_TARGETS: tuple[str, ...] = (
    "tests/browser/test_library_backend_contracts.py",
    "tests/browser/test_browser_interactions.py::test_performance_library_can_reopen_stage_and_workspace_from_selected_record",
    "tests/browser/test_browser_interactions.py::test_performance_library_settings_persist_and_manual_refresh_loads_records",
    "tests/browser/test_browser_interactions.py::test_performance_library_shows_loading_and_recovers_from_route_failure",
    "tests/browser/test_browser_interactions.py::test_performance_library_summary_tiles_and_personal_bests_follow_loaded_records",
    "tests/browser/test_browser_interactions.py::test_performance_library_search_filters_records_and_keeps_lower_detail_truth",
    "tests/browser/test_browser_interactions.py::test_performance_library_detail_ui_persists_tag_add_remove_and_notes",
    "tests/browser/test_browser_interactions.py::test_performance_library_compat_selected_record_and_render_rerender_detail_truth",
    "tests/browser/test_browser_interactions.py::test_performance_library_settings_remain_isolated_from_match_settings",
)

PANE_SETTINGS_TARGETS: tuple[str, ...] = (
    "tests/browser/test_settings_e2e.py",
    "tests/browser/test_settings_defaults_truth_gate.py",
)

PANE_METRICS_TARGETS: tuple[str, ...] = (
    "tests/browser/test_metrics_e2e.py",
    "tests/browser/test_scoring_metrics_contracts.py",
)

SUITES: tuple[SuiteDefinition, ...] = (
    SuiteDefinition(
        name="analysis",
        label="Analysis",
        description="Shot detection, PractiScore import, and timing analysis tests.",
        targets=("tests/analysis",),
    ),
    SuiteDefinition(
        name="browser",
        label="Browser",
        description="Browser API, static shell, and browser-first workflow tests.",
        targets=("tests/browser",),
    ),
    SuiteDefinition(
        name="cli",
        label="CLI",
        description="Runtime entrypoint and command-line behavior tests.",
        targets=("tests/cli",),
    ),
    SuiteDefinition(
        name="export",
        label="Export",
        description="Overlay rendering and FFmpeg export pipeline tests.",
        targets=("tests/export",),
    ),
    SuiteDefinition(
        name="media",
        label="Media",
        description="Media toolchain and FFmpeg resolver tests.",
        targets=("tests/media",),
    ),
    SuiteDefinition(
        name="persistence",
        label="Persistence",
        description="Project bundle, save, and load tests.",
        targets=("tests/persistence",),
    ),
    SuiteDefinition(
        name="presentation",
        label="Presentation",
        description="Stage presentation and timing display tests.",
        targets=("tests/presentation",),
    ),
    SuiteDefinition(
        name="scoring",
        label="Scoring",
        description="Scoring logic, merge, and overlay-scoring integration tests.",
        targets=("tests/scoring",),
    ),
    SuiteDefinition(
        name="benchmarks",
        label="Benchmarks",
        description="Stage benchmark and CSV export tests.",
        targets=("tests/benchmarks",),
    ),
    SuiteDefinition(
        name="scripts",
        label="Scripts",
        description="Helper-script and test-runner coverage tests.",
        targets=("tests/scripts",),
    ),
    SuiteDefinition(
        name="pane-project",
        label="Pane Project",
        description="Opt-in browser pane lane for Project, landing, and PractiScore workflows.",
        targets=PANE_PROJECT_TARGETS,
        include_in_default=False,
    ),
    SuiteDefinition(
        name="pane-match",
        label="Pane Match",
        description="Opt-in browser pane lane for Match workspace, recap, composite, and export workflows.",
        targets=PANE_MATCH_TARGETS,
        include_in_default=False,
    ),
    SuiteDefinition(
        name="pane-performance",
        label="Pane Performance",
        description="Opt-in browser pane lane for Performance Library workflows and contracts.",
        targets=PANE_PERFORMANCE_TARGETS,
        include_in_default=False,
    ),
    SuiteDefinition(
        name="pane-settings",
        label="Pane Settings",
        description="Opt-in browser pane lane for Settings defaults and section workflows.",
        targets=PANE_SETTINGS_TARGETS,
        include_in_default=False,
    ),
    SuiteDefinition(
        name="pane-metrics",
        label="Pane Metrics",
        description="Opt-in browser pane lane for Metrics pane workflows and scoring/metrics contracts.",
        targets=PANE_METRICS_TARGETS,
        include_in_default=False,
    ),
)

SUITE_BY_NAME = {suite.name: suite for suite in SUITES}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run SplitShot test suites one by one or all together with table, raw, and JSON output options.",
    )
    parser.add_argument(
        "--suite",
        action="append",
        dest="suites",
        choices=sorted(SUITE_BY_NAME),
        help="Suite name to run. Repeat to run multiple suites. Defaults to all suites.",
    )
    parser.add_argument(
        "--mode",
        choices=("one-by-one", "all-together"),
        default="one-by-one",
        help="Run each test file individually or run the selected suites in a single pytest invocation.",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json", "raw"),
        default="table",
        help="Console output format.",
    )
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=None,
        help="Optional file where the raw command output log will be written.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional file where the structured JSON result will be written.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the execution plan without invoking pytest.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the available test suites and exit.",
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop after the first failed run.",
    )
    parser.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        help="Additional argument to pass through to pytest. Repeat for multiple arguments.",
    )
    return parser


def relative_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def target_path(target: str) -> Path:
    file_target, _, _ = target.partition("::")
    return (ROOT / file_target).resolve()


def suite_files(suite: SuiteDefinition) -> list[str]:
    files: list[str] = []
    for target in suite.targets:
        path = target_path(target)
        if "::" in target:
            files.append(target)
        elif path.is_dir():
            files.extend(relative_path(candidate) for candidate in sorted(path.rglob("test_*.py")))
        elif path.is_file():
            files.append(target)
    return files


def suite_catalog_files(suite: SuiteDefinition) -> list[str]:
    files: list[str] = []
    seen: set[str] = set()
    for target in suite.targets:
        path = target_path(target)
        if "::" in target:
            file_target = relative_path(path)
            if file_target not in seen:
                files.append(file_target)
                seen.add(file_target)
            continue
        if path.is_dir():
            for candidate in sorted(path.rglob("test_*.py")):
                relative_candidate = relative_path(candidate)
                if relative_candidate not in seen:
                    files.append(relative_candidate)
                    seen.add(relative_candidate)
            continue
        if path.is_file():
            file_target = relative_path(path)
            if file_target not in seen:
                files.append(file_target)
                seen.add(file_target)
    return files


def selected_suites(names: list[str] | None) -> list[SuiteDefinition]:
    if not names:
        return [suite for suite in SUITES if suite.include_in_default]
    return [SUITE_BY_NAME[name] for name in names]


def planned_runs(
    suites: list[SuiteDefinition], mode: str, pytest_args: list[str]
) -> list[PlannedRun]:
    python_cmd = sys.executable
    runs: list[PlannedRun] = []
    if mode == "all-together":
        combined_targets: list[str] = []
        for suite in suites:
            combined_targets.extend(suite.targets)
        runs.append(
            PlannedRun(
                run_id="run-001",
                suite_names=tuple(suite.name for suite in suites),
                suite_labels=tuple(suite.label for suite in suites),
                targets=tuple(combined_targets),
                command=tuple([python_cmd, "-m", "pytest", *combined_targets, *pytest_args]),
            )
        )
        return runs

    run_number = 1
    for suite in suites:
        for target in suite_files(suite):
            runs.append(
                PlannedRun(
                    run_id=f"run-{run_number:03d}",
                    suite_names=(suite.name,),
                    suite_labels=(suite.label,),
                    targets=(target,),
                    command=tuple([python_cmd, "-m", "pytest", target, *pytest_args]),
                )
            )
            run_number += 1
    return runs


def execute_runs(runs: list[PlannedRun], dry_run: bool, stop_on_failure: bool) -> list[RunResult]:
    results: list[RunResult] = []
    for run in runs:
        if dry_run:
            results.append(
                RunResult(
                    run_id=run.run_id,
                    suite_names=list(run.suite_names),
                    suite_labels=list(run.suite_labels),
                    targets=list(run.targets),
                    command=list(run.command),
                    status="planned",
                    return_code=None,
                    duration_seconds=0.0,
                    stdout="",
                    stderr="",
                )
            )
            continue

        started = time.perf_counter()
        completed = subprocess.run(
            list(run.command),
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        duration = time.perf_counter() - started
        passed = completed.returncode == 0
        result = RunResult(
            run_id=run.run_id,
            suite_names=list(run.suite_names),
            suite_labels=list(run.suite_labels),
            targets=list(run.targets),
            command=list(run.command),
            status="passed" if passed else "failed",
            return_code=completed.returncode,
            duration_seconds=duration,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        results.append(result)
        if stop_on_failure and not passed:
            break
    return results


def suite_catalog_payload() -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for suite in SUITES:
        files = suite_catalog_files(suite)
        payload.append(
            {
                "name": suite.name,
                "label": suite.label,
                "description": suite.description,
                "targets": list(suite.targets),
                "default_selected": suite.include_in_default,
                "file_count": len(files),
                "files": files,
            }
        )
    return payload


def summary_payload(results: list[RunResult], dry_run: bool) -> dict[str, int | bool]:
    return {
        "dry_run": dry_run,
        "total_runs": len(results),
        "passed": sum(1 for result in results if result.status == "passed"),
        "failed": sum(1 for result in results if result.status == "failed"),
        "planned": sum(1 for result in results if result.status == "planned"),
    }


def render_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    rendered: list[str] = []
    for row_index, row in enumerate(rows):
        rendered.append(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
        if row_index == 0:
            rendered.append("-+-".join("-" * width for width in widths))
    return "\n".join(rendered)


def format_catalog(format_name: str) -> str:
    payload = suite_catalog_payload()
    if format_name == "json":
        return json.dumps({"suites": payload}, indent=2)
    if format_name == "raw":
        lines = []
        for suite in payload:
            lines.append(f"[{suite['name']}] {suite['label']}")
            lines.append(f"description: {suite['description']}")
            lines.append(f"targets: {', '.join(suite['targets'])}")
            lines.append(f"file_count: {suite['file_count']}")
            lines.append("")
        return "\n".join(lines).rstrip()
    rows = [["Suite", "Files", "Targets", "Description"]]
    for suite in payload:
        rows.append(
            [
                str(suite["name"]),
                str(suite["file_count"]),
                ", ".join(suite["targets"]),
                str(suite["description"]),
            ]
        )
    return render_table(rows)


def format_results(results: list[RunResult], dry_run: bool, format_name: str) -> str:
    payload = {
        "summary": summary_payload(results, dry_run),
        "runs": [asdict(result) for result in results],
    }
    if format_name == "json":
        return json.dumps(payload, indent=2)
    if format_name == "raw":
        return raw_report(results, dry_run)

    rows = [["Run", "Status", "Suites", "Targets", "Seconds", "Return"]]
    for result in results:
        rows.append(
            [
                result.run_id,
                result.status.upper(),
                ", ".join(result.suite_names),
                ", ".join(result.targets),
                f"{result.duration_seconds:.2f}",
                "-" if result.return_code is None else str(result.return_code),
            ]
        )
    summary = payload["summary"]
    return (
        render_table(rows)
        + "\n\n"
        + f"Total runs: {summary['total_runs']} | Passed: {summary['passed']} | Failed: {summary['failed']} | Planned: {summary['planned']}"
    )


def raw_report(results: list[RunResult], dry_run: bool) -> str:
    sections: list[str] = []
    sections.append(f"dry_run={str(dry_run).lower()} total_runs={len(results)}")
    for result in results:
        sections.append(f"=== {result.run_id} {result.status.upper()} ===")
        sections.append(f"suites: {', '.join(result.suite_names)}")
        sections.append(f"targets: {', '.join(result.targets)}")
        sections.append(f"command: {shlex.join(result.command)}")
        sections.append(f"seconds: {result.duration_seconds:.2f}")
        sections.append(f"return_code: {'-' if result.return_code is None else result.return_code}")
        if result.stdout:
            sections.append("stdout:")
            sections.append(result.stdout.rstrip())
        if result.stderr:
            sections.append("stderr:")
            sections.append(result.stderr.rstrip())
        sections.append("")
    return "\n".join(sections).rstrip()


def write_output(path: Path | None, content: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + "\n", encoding="utf-8")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list:
        print(format_catalog(args.format))
        return 0

    suites = selected_suites(args.suites)
    runs = planned_runs(suites, args.mode, list(args.pytest_arg))
    results = execute_runs(runs, dry_run=args.dry_run, stop_on_failure=args.stop_on_failure)
    rendered = format_results(results, args.dry_run, args.format)
    print(rendered)

    write_output(args.raw_output, raw_report(results, args.dry_run))
    write_output(
        args.json_output,
        json.dumps(
            {
                "summary": summary_payload(results, args.dry_run),
                "runs": [asdict(result) for result in results],
            },
            indent=2,
        ),
    )

    if args.dry_run:
        return 0
    return 1 if any(result.status == "failed" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
