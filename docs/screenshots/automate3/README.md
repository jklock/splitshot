# SplitShot Automate3 Screenshot Index

Generated: 2026-05-22
Viewport: 1440x900
Capture scripts:

- `scripts/docs/capture_automate3_views.py`
- `scripts/docs/capture_loaded_views.py`

## Empty States

| File | View | Bytes | Proof |
|---|---|---:|---|
| `empty-landing.png` | Landing Page | 71,167 | `proof-results.json` |
| `empty-stage.png` | Stage Video Edit | 124,623 | `proof-results.json` |
| `empty-match.png` | Match Video Edit | 15,109 | `proof-results.json` |
| `empty-library.png` | Performance Library | 73,104 | `proof-results.json` |

## Loaded States

| File | View | Bytes | Required Content Verified |
|---|---|---:|---|
| `loaded-stage.png` | Stage with media | 150,259 | primary media, 3 shots, waveform samples, rail visible |
| `loaded-match.png` | Match with stages | 69,768 | 2 stage cards, Match active, rail hidden |
| `loaded-library.png` | Library with records | 73,222 | 4 rendered rows, isolated proof library, rail hidden |

## Contact Sheets

| File | Description | Bytes |
|---|---|---:|
| `contact-sheet.png` | Empty-state contact sheet | 118,862 |
| `contact-sheet-final.png` | Loaded-state contact sheet | 66,693 |

## Machine Proof

| File | Description |
|---|---|
| `proof-results.json` | Empty-state assertions and hashes |
| `loaded-proof-results.json` | Loaded-state assertions, hashes, and setup path |

## Current Limitations

- These screenshots prove nonblank content-bearing states, not final product-quality approval.
- PiP/multi-angle, export progress, export complete, and returning-user landing screenshots are still open.
- Loaded Library uses proof-seeded records under a temporary `SPLITSHOT_LIBRARY_ROOT` so screenshot capture has deterministic content without writing to the default local library.
