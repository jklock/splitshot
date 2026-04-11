# Browser Live Control Redesign Plan

## Inputs

- `Directions.md` defines SplitShot as a local Shot Streamer-equivalent workflow: video ingest, automatic analysis, editable timing, merge, overlay, scoring, export, and local project persistence.
- Browser mode is the default user experience; desktop mode remains secondary.
- The current browser UI is not usable enough: it uses path entry as the primary video workflow, a top-tab shell, weak visual hierarchy, and no live video/overlay control surface.
- The comparison app uses a left workflow rail, playable video review, waveform timing edits, split cards, overlay controls, scoring, merge/layout, and export.
- SplitShot must operate locally, so cloud/account/upload language should be replaced by local file/session language.

## Goals

1. Rebuild the browser shell with a Shot Streamer-inspired left workflow rail.
2. Add native browser file selection for primary and secondary videos.
3. Preserve a multipage local session without losing analysis state.
4. Let users watch the primary video in browser mode.
5. Render a live overlay preview on top of the video using the current timer, split, scoring, and badge styles.
6. Expose overlay position, badge size, badge background/text color, opacity, and scoring animation colors.
7. Expose scoring presets for the major practical-shooting scoring modes SplitShot can support locally.
8. Keep all existing local API features: project save/open/delete, timing edits, merge/sync/swap, layout, scoring, and export.
9. Add behavior tests for file-picker ingestion, overlay style updates, scoring presets, and the browser UI contract.

## UI Structure

- Left rail:
  - Manage
  - Open
  - Review
  - Timing
  - Edit
  - Merge
  - Overlay
  - Scoring
  - Layout
  - Export
- Top session bar:
  - project title
  - current local status
  - primary/secondary/session summary
- Main pages:
  - Open: local file chooser buttons, project bundle controls, session facts.
  - Review: metric cards, playable primary video, live overlay preview, selected-shot controls.
  - Timing: full beep-to-final timing table and split cards.
  - Edit: waveform editor, click-to-add, shift-click beep move, selected shot nudge/delete.
  - Merge: secondary file chooser, sync offset, layout, PiP size, swap.
  - Overlay: position, badge size, per-badge color/opacity controls, scoring color controls.
  - Scoring: ruleset preset, penalties, score assignment, hit factor/scoring summary.
  - Layout: aspect ratio and crop controls.
  - Export: quality and output path.

## Backend Changes

- Add local multipart file endpoints:
  - `POST /api/files/primary`
  - `POST /api/files/secondary`
- Store selected browser files in a server-owned local session media directory for the lifetime of the browser server.
- Keep path-based import endpoints for tests, automation, and advanced users.
- Add overlay style updates through `/api/overlay`.
- Add scoring preset updates through `/api/scoring/profile`.
- Add score-position updates through `/api/scoring/position`.
- Add sync-offset adjustments through `/api/sync`.
- Expose scoring presets and scoring summary in `/api/state`.

## Scoring Presets

- USPSA/IPSC minor hit factor.
- USPSA/IPSC major hit factor.
- IDPA time-plus approximation.
- Steel Challenge time-plus approximation.
- 3-Gun / PCSL time-plus approximation.

The app keeps the shared shot timing model and maps score letters to the selected scoring contract. Production scoring must remain editable because match rulebooks vary by division and discipline.

## Tests

- Browser static UI contains the left rail, local video file inputs, video review surface, overlay color inputs, scoring presets, and no cloud upload language.
- Browser multipart file selection imports and analyzes a selected primary video.
- Browser overlay API updates badge colors, text colors, opacity, badge size, and position.
- Browser scoring preset API updates the active scoring rule and point map.
- Hit factor uses raw beep-to-final-shot time when a beep is present.
- Existing path import, edit, merge, export, persistence, and desktop smoke tests remain valid.

