# Scripts

SplitShot scripts are organized by purpose so users can find setup, validation, analysis, and export helpers without scanning one flat directory.

## Layout

- `scripts/setup/`: workstation bootstrap for macOS, Linux, and Windows PowerShell.
- `scripts/testing/`: master test runner and related testing helpers.
- `scripts/audits/browser/`: real browser validation scripts for UI surface, AV playback, interaction flows, and export matrices.
- `scripts/analysis/`: ShotML and analysis helpers, including preflight split/confidence inspection.
- `scripts/export/`: export-oriented utilities such as benchmark CSV generation.
- `scripts/tooling/`: local environment and toolchain validation.

## Common Commands

```bash
uv run python scripts/testing/run_test_suite.py --list
uv run python scripts/testing/run_test_suite.py --mode one-by-one --format table --raw-output artifacts/test-run.raw.txt
uv run python scripts/testing/run_test_suite.py --mode all-together --format json --json-output artifacts/test-run.json
uv run python scripts/analysis/analyze_video_shots.py /path/to/stage.mp4 --format table --json-output artifacts/shot-preview.json
uv run python scripts/audits/browser/run_browser_ui_surface_audit.py
uv run python scripts/audits/browser/run_browser_interaction_audit.py
uv run python scripts/tooling/validate_toolchain.py
```

## Notes

- The master test runner supports per-suite execution, one-file-at-a-time runs, combined runs, and raw or JSON output artifacts.
- The video preflight analysis helper uses the same ShotML detection path as the application and is intended to help choose a starting sensitivity slider value before import.
- Browser audit scripts are the real validation layer for route-backed UI behavior. By default they use the bundled repo-local media in `tests/artifacts/test_video/` plus `example_data/IDPA/IDPA.csv`, so a fresh clone can run them without private stage files.

**Last updated:** 2026-04-18
**Referenced files last updated:** 2026-04-18