# Scoring And Export Presets Plan

## Direction Review

The app must keep the local Shot Streamer-style workflow, but scoring and export can no longer be generic placeholders.

- Scoring must support USPSA, IDPA, Steel Challenge, IPSC, and GPA rules.
- Per-shot scoring must still attach to the selected shot and drive overlay/export score animation.
- Rule-specific penalties must be editable, not hidden in one generic field.
- Export must use FFmpeg and expose the actual variables that control the encode.
- Export presets must cover universal vertical, short-form vertical, and YouTube long-form workflows.
- Export must show a visible status bar and retain FFmpeg log output in the app.

## Research Notes

- YouTube's official upload guidance recommends MP4, H.264, AAC-compatible audio, same recorded frame rate, 4:2:0, SDR BT.709, and recommended bitrates by resolution: https://support.google.com/youtube/answer/1722171
- TikTok's official business help content emphasizes vertical 9:16 video, `.mp4`/`.mov` formats, and at least 540x960 vertical dimensions for in-feed auction ads: https://ads.tiktok.com/help/article/video-ads-specifications
- Meta's public Reels page was behind a login/block during research, but the requested 9:16 Reels behavior is consistent with the user's supplied comparison spec and the accessible Meta page title/context.

## Scoring Plan

- Replace the current simple point-map presets with rule definitions that include score choices, score values, per-score penalties, and dynamic penalty fields.
- Keep the existing `penalties` number as a compatibility/manual-extra penalty field.
- Add dynamic `penalty_counts` to project scoring state so each ruleset can expose fields like non-threat, procedural error, FTDR, FP, steel stop failure, and GPA steel not down.
- Calculate USPSA/IPSC as hit factor: `(points - score penalties - field penalties - manual penalties) / raw time`.
- Calculate IDPA/GPA/Steel as time-plus: `raw time + score seconds + field penalties + manual penalties`.
- Render score-letter options from the active scoring preset instead of hardcoding one list.
- Render rule-specific penalty inputs in the Score pane and auto-apply them.

## Export Plan

- Add explicit export settings for preset, target width/height, frame rate, video codec, bitrate, audio codec, audio sample rate, audio bitrate, SDR color, two-pass flag, FFmpeg preset, quality, aspect ratio, and crop center.
- Add export preset definitions:
  - Source/original H.264 MP4.
  - Universal vertical master: MP4 H.264 1080x1920 9:16, source frame rate, 20 Mbps, AAC 48 kHz 320 kbps, SDR BT.709.
  - Short-form vertical: 1080x1920 9:16, source frame rate, 15 Mbps, AAC 48 kHz 320 kbps, SDR BT.709.
  - YouTube long-form 1080p: 1920x1080 16:9, source frame rate, 15 Mbps.
  - YouTube long-form 4K: 3840x2160 16:9, source frame rate, 56 Mbps.
  - Custom: manual values.
- Update FFmpeg export to crop, scale to target dimensions when set, encode using exposed codec/bitrate/audio/color settings, and store command/log output.
- Add browser controls for export preset and all exposed export variables.
- Add an export log panel under the export button.

## Test Plan

- Unit-test scoring formulas for USPSA minor/major, IPSC, IDPA, Steel Challenge, and GPA.
- Unit-test export preset application and concrete FFmpeg output dimensions/metadata.
- Browser control tests verify export settings endpoints mutate project state and expose presets.
- Static browser tests verify the Score pane uses dynamic controls and Export pane exposes preset/encoding fields and log output.
- Run JavaScript syntax check, targeted tests, full test suite, runtime check, and diff validation.

## Completion Status

- Scoring definitions now cover USPSA minor/major, IPSC minor/major, IDPA Time Plus, Steel Challenge, and GPA 0.5 scoring.
- Score options are no longer hardcoded in the browser; they render from the active scoring preset.
- Penalty inputs are dynamic and persisted as `penalty_counts`.
- Export presets now write directly into project export variables.
- FFmpeg export now honors target dimensions, frame rate, video codec, bitrate, audio settings, Rec.709 SDR flags, FFmpeg preset, and two-pass.
- Export command and log output are stored on the project and shown in the browser Export pane.
- README documents FFmpeg export behavior and exposed variables.
