# Timing Exposure and UI Parity Final Audit

## Scope

This pass completed two requirements:

- Expose all timing data from timer beep through final shot, split-by-split.
- Move the browser and desktop apps onto the same timing/presentation contract so they operate the same way.

## Timing Data Exposed

The shared presentation layer now exposes:

- `draw_ms`: beep to first shot.
- `raw_time_ms`: beep to final shot.
- `stage_time_ms`: compatibility alias for raw time.
- `beep_ms`: detected timer beep timestamp.
- `final_shot_ms`: final shot timestamp.
- `timing_segments`: one row per shot.
- Each timing segment includes segment duration, cumulative beep-to-shot duration, absolute video timestamp, confidence, source, score, and card display fields.

CSV output now includes:

- `split_1_ms` / `split_1_s`: draw.
- `split_2_ms` onward: shot-to-shot splits.
- `beep_to_shot_1_ms` onward: cumulative beep-to-each-shot timing.
- `beep_to_shot_N` equals `raw_time` for the final shot.

Generated file:

- `artifacts/stage_suite_analysis.csv`

Current summary:

| Stage | Raw | Split 1 / Draw | Final Cumulative |
|---|---:|---:|---:|
| Stage1 | 13.552 | 2.026 | 13.552 |
| Stage2 | 19.826 | 2.112 | 19.826 |
| Stage3 | 13.624 | 1.754 | 13.624 |
| Stage4 | 17.013 | 1.938 | 17.013 |

## UI Parity

Shared implementation:

- `splitshot.presentation.stage.build_stage_presentation()` is now the source of truth for timing metrics and split-card data.
- Browser API state exposes the same `metrics` and `timing_segments`.
- Desktop split cards render from the same `timing_segments`.
- Browser split cards render from `timing_segments`.

Aligned labels:

- Draw Time.
- Raw Time.
- Total Shots.
- Avg Split.
- Split card labels: Draw, Shot 2, Shot 3, etc.
- Split card metadata includes cumulative beep-to-shot time and absolute video timestamp.

Aligned operations:

- Browser and desktop both support manage, upload, merge, overlay, scoring, layout, swap, and export workflow sections.
- Browser API now includes project delete and video swap actions to match desktop functionality.

## Validation

Commands run:

```bash
uv run splitshot-benchmark-csv --output artifacts/stage_suite_analysis.csv Stage1.MP4 Stage2.MP4 Stage3.MP4 Stage4.MP4
uv run pytest
```

Results:

- Full suite passed: `33 passed`.
- Desktop smoke passed: `app-smoke-ok`.

Feature tests added/updated:

- Shared presentation exposes full beep-to-final timing.
- Browser state includes timing segments.
- Browser API supports secondary sync and video swap.
- Desktop split cards use shared timing segment data.
- CSV includes `split_1` and `beep_to_shot_*`.

## Remaining Risk

The browser and desktop now share data and workflow semantics. Pixel-perfect visual parity is still limited by using different rendering technologies: HTML/CSS in browser and Qt widgets in desktop. The next parity step would be extracting shared design tokens and adding visual snapshot checks.
