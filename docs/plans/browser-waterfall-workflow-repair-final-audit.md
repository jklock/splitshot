# Browser Waterfall Workflow Repair Final Audit

## Feature Audit

- Project now uses `Add Second Video` and a full-width red `Delete Project` action.
- Splits is the timing-edit page and Review moved near the end of the workflow for preview-artifact controls.
- Status bar now overlays only active import/export work instead of reserving permanent vertical space.
- Secondary video preview renders in the main video stage with side-by-side, above/below, and PiP classes and playback sync.
- Waveform now renders a time scale with three-decimal-second labels plus horizontal zoom, amplitude zoom, and reset controls.
- Expanded waveform/splits modes collapse on page navigation, and layout unlock appears only in expanded mode.
- Scoring shot list now shows each shot’s cumulative time and score state.
- Overlay preview/export now puts shot score text inside shot split badges and no longer paints large floating score letters.
- Overlay settings now support visible shot count, quadrant, direction, custom X/Y, bubble width/height, font family, font size, bold, italic, artifact toggles, score colors, and custom review box settings.
- Layout now has consolidated mirrored controls for splits threshold, scoring enabled/preset, overlay placement/display, merge enable/layout/PiP, and export frame settings.
- FFmpeg export still writes H.264 MP4 and stores logs in project state.

## Testing Audit

- Full test suite: `uv run pytest` passed with 60 tests.
- Static UI tests now assert waterfall ownership, secondary-video preview markup, status hidden behavior, waveform zoom controls, project destructive action, and no floating score CSS.
- Browser control tests now assert advanced overlay state round-trips through the API.
- Persistence tests now assert advanced overlay/review settings survive save/load.
- Export tests now assert score text is embedded in the shot badge model and export still burns visible overlay pixels.
- Generated Stage1 all-options output:
  - MP4: `artifacts/stage1-all-options.mp4`
  - Preview: `artifacts/stage1-all-options-preview.png`
  - Video stream: H.264, 720x1280, 30 fps, 31.4 seconds.

## Residual Risk

- The app still does not run real browser automation through Playwright/Selenium, so drag/resize behavior is covered by static wiring and state/API tests rather than a real DOM browser driver.
- The dedicated workflow panes still exist for focused editing, but Layout now provides the main consolidated control surface for the cross-cutting composition settings.
