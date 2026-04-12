# Browser Functional Button Trace Plan

## Goal

Replace shallow button-presence validation with feature-effect validation for the browser cockpit.

## Functional Areas

- Project: opening a primary video must immediately import, analyze, update media state, and switch to review.
- Project/Merge: adding a second angle must immediately import, analyze sync, and enable merge.
- Review/Timing: waveform modes, shot selection, nudges, deletes, and timing expansion must mutate shot/beep state.
- Overlay: changes must auto-apply to live preview and exported video.
- Scoring: selected shot scoring must update the shot, summary, and exported score animation state.
- Merge/Layout: sync, swap, layout, crop, quality, and export variables must update project state.
- Export: browser export must write a valid MP4 and expose FFmpeg log output.

## UI Corrections

- Remove confusing separate Browse / Import / Choose actions for primary and secondary.
- Replace them with single local actions: Open Primary Video and Add Second Angle.
- Keep typed-path fields, but make Enter import immediately.
- Move score placement control into Scoring instead of floating over video.
- Stabilize overlay badge widths so timer text does not shift adjacent badges.
- Make overlay renderer honor square/rounded/bubble style in exports, not only preview.

## Validation

- Add browser API tests that export via `/api/export`.
- Add export tests proving overlay pixels appear in the output video.
- Add tests for overlay layout persistence and renderer style behavior.
- Add static contract tests that prevent reintroducing confusing primary/secondary button names.
