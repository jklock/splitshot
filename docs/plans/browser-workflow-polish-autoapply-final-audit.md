# Browser Workflow Polish And Auto-Apply Final Audit

## User-Facing Changes

| Request | Result |
| --- | --- |
| Project should be at the top of the rail. | Project is now the first rail tool. |
| Clarify/remove Edit mode. | Edit mode was removed because it duplicated waveform/timing editing. |
| Selected Shot should not appear on every page. | Nudge/delete selected-shot controls now appear only in Timing. |
| Waveform should start at the top of its box. | The waveform canvas is now the first row in the waveform panel. |
| Clarify scoring. | Score letters are explicitly tied to the selected shot; score placement appears only in Score mode. |
| Color boxes are too large. | Overlay badge and score color controls are compact right-inspector controls. |
| Remove `No video open` overlay text. | Floating video status text was removed. |
| Add import processing status. | A thin processing/status bar appears for imports and API work. |
| Settings should auto-apply. | Threshold, scoring, overlay, merge, and layout controls auto-apply with debounce. |
| Path fields need file browser buttons. | Project and export path fields now have Browse buttons backed by local chooser endpoints. |
| Do not require `uv --python 3.12`. | README documents `uv run splitshot`, using `.python-version` for Python 3.12. |

## Scoring Behavior

Scoring is per shot. The user selects a shot from the waveform, split cards, or timing table, then the Score pane edits that selected shot. Changing the score letter immediately saves it to the selected shot. `Place Score` only appears in Score mode and stores the selected shot's on-video coordinate for playback/export score animation. The scoring preset, scoring enabled state, and penalties feed the score summary/hit-factor calculation.

## Validation

| Check | Result |
| --- | --- |
| JavaScript syntax | `node --check src/splitshot/browser/static/app.js` passed. |
| Targeted browser tests | `uv run pytest tests/test_browser_static_ui.py tests/test_browser_control.py` passed with 18 tests. |
| Full suite | `uv run pytest` passed with 49 tests. |
| Runtime check | `uv run splitshot --check` found `ffmpeg`, `ffprobe`, and browser static assets. |
| Launch config | `uv run splitshot --help` works without `--python 3.12`. |
| Activity smoke | `logs/splitshot-browser-20260411-201936-5070292a.log` logged 35 button clicks and 2 dialog path selections. |

## Residual Risk

Native file dialogs are OS-mediated. On macOS, SplitShot uses `osascript`; on other platforms it falls back to Tk. If the app is launched in a constrained/headless session, the chooser endpoint returns a logged error rather than silently failing.
