# Developing SplitShot

This project is designed to be run directly from source with `uv` and Python 3.12.

## Environment

- Python version: 3.12
- Package manager / runner: `uv`
- Required media tools: `ffmpeg` and `ffprobe`

The runtime locates media binaries from `PATH` first, then from bundled resources, and it also honors `SPLITSHOT_FFMPEG_DIR`.

## Common Commands

```bash
uv run splitshot
uv run splitshot --desktop
uv run splitshot --no-open
uv run splitshot --check
uv run pytest
uv run splitshot-benchmark-csv --output artifacts/stage_suite_analysis.csv
```

## Working Areas

- Browser UI assets live in [src/splitshot/browser/static](../src/splitshot/browser/static).
- Browser API behavior lives in [src/splitshot/browser/server.py](../src/splitshot/browser/server.py).
- Shared project mutation logic lives in [src/splitshot/ui/controller.py](../src/splitshot/ui/controller.py).
- Analysis and export code live in [src/splitshot/analysis](../src/splitshot/analysis) and [src/splitshot/export](../src/splitshot/export).

## Testing

The repository uses `pytest` with `qt_api = pyside6`.

- Run the full suite with `uv run pytest`.
- Run a subset with `uv run pytest tests/test_export.py` or any other test module.
- Re-run browser-focused tests after changing `src/splitshot/browser/static` or `src/splitshot/browser/server.py`.

## Project State Files

- App settings live in `~/.splitshot/settings.json`.
- Saved projects are `.ssproj` bundle directories containing `project.json` and copied media when needed.
- Browser session uploads may be stored in temporary session directories while the browser server is running.

## Change Discipline

- Keep browser and desktop behavior aligned when the change affects the shared controller or domain model.
- Update both the project bundle load/save path and the browser state serialization when the project schema changes.
- Use the technical docs in `src/splitshot/.../README.md` to locate the owning module before adding new behavior.