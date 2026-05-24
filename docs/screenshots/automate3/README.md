# SplitShot Automate3 Screenshot Index

Generated: 2026-05-24
Viewport: 1440x900 primary sets; responsive proof at 1280x900 and 900x900
Capture scripts:

- `scripts/docs/capture_automate3_views.py`
- `scripts/docs/capture_loaded_views.py`
- `scripts/docs/capture_additional_screenshots.py`
- `scripts/docs/capture_stage_responsive_views.py`

## Empty States

| File | View | Bytes | Proof |
| --- | --- | ---: | --- |
| `empty-landing.png` | Landing Page | 71,167 | `proof-results.json` |
| `empty-stage.png` | Stage Video Edit | 124,623 | `proof-results.json` |
| `empty-match.png` | Match Video Edit | 15,109 | `proof-results.json` |
| `empty-library.png` | Performance Library | 73,104 | `proof-results.json` |

## Loaded States

| File | View | Bytes | Required Content Verified |
| --- | --- | ---: | --- |
| `loaded-stage.png` | Stage with media | 150,259 | primary media, 3 shots, waveform samples, rail visible |
| `loaded-match.png` | Match with stages | 69,768 | 2 stage cards, Match active, rail hidden |
| `loaded-library.png` | Library with records | 73,222 | 4 rendered rows, isolated proof library, rail hidden |

## Feature And Responsive States

| File | View | Bytes | Required Content Verified |
| --- | --- | ---: | --- |
| `pip-multi-angle-loaded.png` | PiP tool with added media | 779,949 | PiP media visible, stage active, inspector visible |
| `export-progress.png` | Export progress state | 479,130 | processing bar visible, stage active |
| `export-complete.png` | Export complete state | 491,806 | completion status visible, stage active |
| `returning-user-landing.png` | Returning-user landing | 78,976 | recent activity visible |
| `responsive-stage-1280.png` | Stage at 1280px | 613,680 | project pane visible, rail visible, no horizontal overflow |
| `responsive-stage-900.png` | Stage at 900px | 330,096 | settings pane visible, rail visible, no horizontal overflow |

## Contact Sheets

| File | Description | Bytes |
| --- | --- | ---: |
| `contact-sheet.png` | Empty-state contact sheet | 118,862 |
| `contact-sheet-final.png` | Loaded-state contact sheet | 66,693 |

## Machine Proof

| File | Description |
| --- | --- |
| `proof-results.json` | Empty-state assertions and hashes |
| `loaded-proof-results.json` | Loaded-state assertions, hashes, and setup path |
| `additional-proof-results.json` | Feature-state assertions and hashes |
| `responsive-proof-results.json` | Responsive Stage assertions and hashes |

## Current Limitations

- These screenshots prove nonblank content-bearing states, feature states, and responsive layout, not broader release-governance approval by themselves.
- Loaded Library uses proof-seeded records under a temporary `SPLITSHOT_LIBRARY_ROOT` so screenshot capture has deterministic content without writing to the default local library.
