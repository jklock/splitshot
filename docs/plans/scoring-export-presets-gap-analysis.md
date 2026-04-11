# Scoring And Export Presets Gap Analysis

## Current Gaps

- Scoring presets only approximate hit factor and time-plus behavior.
- Miss and no-shoot penalties are not automatically included in USPSA/IPSC hit factor.
- IDPA, Steel Challenge, and GPA do not expose their specific penalty controls.
- The score-letter dropdown is hardcoded instead of being ruleset-specific.
- Export quality is only High/Medium/Low CRF plus aspect ratio/crop.
- The export UI does not expose resolution, frame rate, codec, bitrate, audio, color, or two-pass variables.
- Export uses FFmpeg internally but the browser UI does not show the FFmpeg command/log output.
- The export action has no export-specific status/log panel for failures.

## Closure Plan

- Add richer scoring preset definitions and dynamic scoring penalty counts.
- Update scoring summary math to use per-score values, per-score penalties, rule penalty fields, and manual extra penalties.
- Render score choices and penalty controls from the active preset.
- Add export preset definitions that map directly to export settings.
- Update export settings persistence and browser state serialization.
- Update FFmpeg encode to honor target resolution, frame rate, bitrate, audio, color, codec, and preset variables.
- Capture FFmpeg command and stderr log output on the project and render it in the browser Export pane.
- Add tests that exercise scoring formulas, export preset mapping, exported video dimensions, browser settings endpoints, and static UI affordances.

## Residual Risk

- Steel Challenge multi-string scoring requires real string segmentation to be exact. This pass exposes and calculates the available raw-string/time-plus penalty controls; true best-4-of-5 aggregation should be a later feature once multi-string stage modeling exists.

## Closure Status

- USPSA/IPSC major and minor now calculate hit factor with scored points, miss/no-shoot penalties, procedural penalties, and manual extra penalties.
- IDPA, Steel Challenge, and GPA now calculate time-plus summaries with ruleset-specific score choices and penalty fields.
- Browser scoring options and penalty inputs are dynamic per scoring preset.
- Export presets now map directly to persisted FFmpeg variables.
- Browser export settings expose resolution, frame rate, video codec, bitrate, audio settings, color, FFmpeg preset, and two-pass.
- FFmpeg command/log output is captured and rendered in the Export pane.
