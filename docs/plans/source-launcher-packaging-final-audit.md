# Source Launcher Packaging Final Audit

## Scope

This pass made SplitShot browser-first for source/package use and made raw time explicit in benchmark output.

Out of scope:

- `.dmg` production.
- `.exe` production.
- Code signing and notarization.

## Launch Contract

Primary command:

```bash
uv run --python 3.12 splitshot
```

Behavior:

- Starts the local browser control server.
- Binds to `127.0.0.1:8765` by default.
- Opens the browser unless `--no-open` is provided.

Secondary command:

```bash
uv run --python 3.12 splitshot --desktop
```

Behavior:

- Starts the PySide desktop UI.

Runtime check:

```bash
uv run --python 3.12 splitshot --check
```

Compatibility aliases:

- `uv run splitshot-web`
- `uv run splitshot-desktop`

## Raw Time Benchmark

The screenshot `Raw` column is the benchmark metric. SplitShot now exports the same concept as `raw_time_ms` and `raw_time_s`.

Generated file:

- `artifacts/stage_suite_analysis.csv`

Reference comparison:

| Stage | Reference Raw | SplitShot Raw | Delta |
|---|---:|---:|---:|
| Stage1 | 13.55 | 13.552 | +0.002 |
| Stage2 | 19.83 | 19.826 | -0.004 |
| Stage3 | 13.62 | 13.624 | +0.004 |
| Stage4 | 17.01 | 17.013 | +0.003 |

`stage_time_*` remains in the CSV as a compatibility alias for the same beep-to-final-shot duration.

## Validation

Commands run:

```bash
uv run splitshot --help
uv run splitshot --check
uv run python -m splitshot --help
uv run splitshot-desktop --help
uv run splitshot-benchmark-csv --output artifacts/stage_suite_analysis.csv Stage1.MP4 Stage2.MP4 Stage3.MP4 Stage4.MP4
uv run pytest
```

Results:

- CLI help documents browser mode as default.
- Runtime check resolved FFmpeg and FFprobe and found browser assets.
- Stage CSV regenerated with `raw_time_*` columns.
- Full suite passed: `31 passed`.
- Desktop smoke passed: `app-smoke-ok`.

## Feature Coverage

Validated by tests:

- `splitshot` dispatches to browser mode by default.
- `splitshot --desktop` dispatches to desktop mode.
- `splitshot --check` validates runtime dependencies.
- Browser API ingest/edit/score behavior still works.
- Stage1-4 raw times match screenshot references within benchmark tolerance.
- Existing analysis, export, scoring, merge, persistence, and UI tests still pass.

## Remaining Risks

- Users still need `uv` and FFmpeg/FFprobe available unless binaries are bundled and `SPLITSHOT_FFMPEG_DIR` is set.
- Browser and desktop are separate process modes that share project files and backend logic, not one simultaneously mirrored session.
- Real-world detector accuracy still needs more videos and Shot Streamer comparison data.
