from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class SuiteDefinition:
    name: str
    label: str
    description: str
    targets: tuple[Path, ...]


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


SUITES: tuple[SuiteDefinition, ...] = (
    SuiteDefinition(
        name="analysis",
        label="Analysis",
        description="Shot detection, PractiScore import, and timing analysis tests.",
        targets=(ROOT / "tests" / "analysis",),
    ),
    SuiteDefinition(
        name="browser",
        label="Browser",
        description="Browser API, static shell, and browser-first workflow tests.",
        targets=(ROOT / "tests" / "browser",),
    ),
    SuiteDefinition(
        name="cli",
        label="CLI",
        description="Runtime entrypoint and command-line behavior tests.",
        targets=(ROOT / "tests" / "cli",),
    ),
    SuiteDefinition(
        name="export",
        label="Export",
        description="Overlay rendering and FFmpeg export pipeline tests.",
        targets=(ROOT / "tests" / "export",),
    ),
    SuiteDefinition(
        name="media",
        label="Media",
        description="Media toolchain and FFmpeg resolver tests.",
        targets=(ROOT / "tests" / "media",),
    ),
    SuiteDefinition(
        name="persistence",
        label="Persistence",
        description="Project bundle, save, and load tests.",
        targets=(ROOT / "tests" / "persistence",),
    ),
    SuiteDefinition(
        name="presentation",
        label="Presentation",
        description="Stage presentation and timing display tests.",
        targets=(ROOT / "tests" / "presentation",),
    ),
    SuiteDefinition(
        name="scoring",
        label="Scoring",
        description="Scoring logic, merge, and overlay-scoring integration tests.",
        targets=(ROOT / "tests" / "scoring",),
    ),
    SuiteDefinition(
        name="benchmarks",
        label="Benchmarks",
        description="Stage benchmark and CSV export tests.",
        targets=(ROOT / "tests" / "benchmarks",),
    ),
    SuiteDefinition(
        name="scripts",
        label="Scripts",
        description="Helper-script and test-runner coverage tests.",
        targets=(ROOT / "tests" / "scripts",),
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


def suite_files(suite: SuiteDefinition) -> list[Path]:
    files: list[Path] = []
    for target in suite.targets:
        if target.is_dir():
            files.extend(sorted(target.rglob("test_*.py")))
        elif target.is_file():
            files.append(target)
    return files


def selected_suites(names: list[str] | None) -> list[SuiteDefinition]:
    if not names:
        return list(SUITES)
    return [SUITE_BY_NAME[name] for name in names]


def planned_runs(suites: list[SuiteDefinition], mode: str, pytest_args: list[str]) -> list[PlannedRun]:
    python_cmd = sys.executable
    runs: list[PlannedRun] = []
    if mode == "all-together":
        combined_targets: list[str] = []
        for suite in suites:
            combined_targets.extend(relative_path(target) for target in suite.targets)
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
        for file_path in suite_files(suite):
            target = relative_path(file_path)
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
        files = suite_files(suite)
        payload.append(
            {
                "name": suite.name,
                "label": suite.label,
                "description": suite.description,
                "targets": [relative_path(target) for target in suite.targets],
                "file_count": len(files),
                "files": [relative_path(path) for path in files],
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