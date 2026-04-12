# Browser Functional Button Trace Gap Analysis

## Evidence From Logs

- `logs/splitshot-browser-20260412-024400-9648b725.log` shows the user selected `Stage1.MP4` through `browse-primary-path`.
- The app only filled the path input and required a second `import-primary-path` click to actually analyze the file.
- Repeated `Import Path` clicks without a path produced status errors, which made the controls feel broken.
- Overlay auto-apply reached `/api/overlay`, but export rendering did not yet honor `style_type`, `spacing`, or `margin`.

## Root Causes

- The project page exposed three competing primary/secondary actions instead of one obvious local action.
- Tests asserted that buttons existed and were logged, but did not assert that clicking the workflow action changed project state.
- Export was covered at the pipeline level, but not through the browser API route.
- Overlay preview and overlay export used different style logic.
- The floating score placement button was attached to the video surface and read as a stray/shadow control.

## Closure

- Make file browser selection auto-import for primary and secondary videos.
- Remove visible primary/secondary upload-style buttons and separate import buttons.
- Add typed-path Enter handling for users who paste a path.
- Add browser export API test.
- Add overlay output pixel test and renderer style test.
- Move score placement into Scoring pane and stabilize timer badge widths.
