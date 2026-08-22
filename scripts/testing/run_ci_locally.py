"""Run CI-shaped local validation groups so the main jobs can be reproduced without GitHub Actions."""

from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "local-ci"
NON_BROWSER_SUITE_ARGS = (
    "--suite analysis",
    "--suite cli",
    "--suite export",
    "--suite media",
    "--suite persistence",
    "--suite presentation",
    "--suite scoring",
    "--suite benchmarks",
    "--suite scripts",
)


@dataclass(frozen=True, slots=True)
class LocalJob:
    name: str
    commands: tuple[str, ...]
    env: dict[str, str]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run SplitShot local-first quality gates before any GitHub Actions workflow.",
    )
    parser.add_argument(
        "--job",
        action="append",
        choices=("source-local", "browser-local", "electron-release-local"),
        dest="jobs",
        help="Local gate to run. Defaults to all supported local jobs.",
    )
    return parser


def local_jobs() -> dict[str, LocalJob]:
    common_env = {
        "QT_QPA_PLATFORM": "offscreen",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    }
    return {
        "source-local": LocalJob(
            name="source-local",
            env=common_env,
            commands=(
                "uv sync --frozen --extra dev",
                "uv run splitshot --check",
                "uv run python scripts/testing/run_test_suite.py --mode all-together --format table --raw-output artifacts/local-ci/source-local.raw.txt "
                + " ".join(NON_BROWSER_SUITE_ARGS),
            ),
        ),
        "browser-local": LocalJob(
            name="browser-local",
            env=common_env,
            commands=(
                "uv sync --frozen --extra dev",
                "uv run python -m playwright install chromium firefox webkit",
                "uv run pytest tests/browser -q",
            ),
        ),
        "electron-release-local": LocalJob(
            name="electron-release-local",
            env=common_env,
            commands=(
                "uv sync --frozen --extra dev",
                "uv run python scripts/testing/run_electron_preflight.py",
            ),
        ),
    }


def run_logged(command: str, *, env: dict[str, str]) -> None:
    print(f"$ {command}", flush=True)
    subprocess.run(command, cwd=ROOT, env=env, shell=True, check=True)


def run_job(job: LocalJob) -> None:
    print(f"== {job.name} ==", flush=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(job.env)
    for command in job.commands:
        run_logged(command, env=env)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    jobs = local_jobs()
    selected = args.jobs or ["source-local", "browser-local", "electron-release-local"]
    for job_name in selected:
        run_job(jobs[job_name])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
