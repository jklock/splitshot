# Scoring And Export Presets Final Audit

## Scoring Result

| Discipline | Implemented behavior |
| --- | --- |
| USPSA | Hit Factor = adjusted points / raw time. A=5, C/D are major/minor-specific, misses and no-shoots apply -10 style penalties, procedural fields apply -10 each. |
| IPSC | Hit Factor = adjusted points / raw time. Major/minor presets mirror A/C/D values and miss/no-shoot penalties. |
| IDPA | Time Plus = raw time + per-shot points down + penalty seconds. -0, -1, -3, miss, non-threat, PE, FP, FTDR, and finger PE are represented. |
| Steel Challenge | Time-only plus adders for plate miss and stop plate failure. Multi-string best-count aggregation remains a later feature because the app does not yet model separate strings. |
| GPA | Time Plus style with 0.5 scoring for +1/+3/+10 values, plus non-threat and steel-not-down penalties. |

Scoring remains selected-shot based: selecting a shot drives the score dropdown, score animation position, overlay preview, and export animation.

## Export Result

SplitShot exports through local FFmpeg. The exporter composites frames locally, renders overlays and scoring into those frames, then pipes raw RGBA frames to FFmpeg for MP4 encoding.

| Export area | Implemented behavior |
| --- | --- |
| Presets | Source MP4, Universal Vertical Master, Short-Form Vertical, YouTube Long-Form 1080p, YouTube Long-Form 4K, and Custom. |
| Video variables | Aspect, crop center, target width/height, source/30/60 fps, H.264/HEVC, bitrate, FFmpeg preset, and two-pass. |
| Audio variables | AAC, sample rate, and bitrate. |
| Color | Rec.709 SDR flags are emitted. |
| Logging | The Export pane shows the last FFmpeg command/log output and stores errors on the project. |
| Status | Export uses the browser processing bar with FFmpeg-specific status text and activity-log progress records. |

## Validation

| Check | Result |
| --- | --- |
| JavaScript syntax | `node --check src/splitshot/browser/static/app.js` passed. |
| Python compile | `uv run python -m py_compile ...` passed for changed Python modules. |
| Targeted feature tests | Scoring, export, browser static/control, and persistence tests passed with 32 tests. |
| Full suite | `uv run pytest` passed with 56 tests. |
| Runtime check | `uv run splitshot --check` found FFmpeg, FFprobe, and browser static assets. |
| Diff check | `git diff --check` passed. |

## Residual Risk

Steel Challenge best-4-of-5 and Outer Limits best-3-of-4 need true multi-string modeling. Current scoring handles a raw analyzed string/stage plus explicit penalty adders.
