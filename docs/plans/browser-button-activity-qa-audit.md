# Browser Button Activity QA Audit

## Scope

This audit covers the browser control UI. Every button click is logged through the capture-phase `button.click` browser event, then the specific handler logs the resulting API, waveform, timing, or tool event.

## Global Logging

| Control surface | Log event | Expected effect |
| --- | --- | --- |
| Any `<button>` | `browser.activity` with `button.click` | Records id, visible text, tool target, waveform mode, nudge value, sync value, and secondary-file intent. |
| Any input, select, or textarea change | `browser.activity` with `control.change` | Records control id, name, type, and new value or selected file names. |
| Any API call | `api.start`, `api.success`, or `api.error` | Records the route payload and resulting controller status. |
| File import | `api.files.primary.*` or `api.files.secondary.*` | Records temp media path, analysis status, and shot count where applicable. |
| Media playback fetch | `media.start`, `media.complete`, or `media.client_disconnect` | Records range requests without printing expected browser disconnect tracebacks. |

## Button QA Matrix

| Button | Location | Expected app effect | QA evidence |
| --- | --- | --- | --- |
| Project | Left rail | Activates primary, secondary, project save, open, and delete controls. | `button.click`, `ui.tool.click`, `ui.tool.active`. |
| Review | Left rail | Activates review inspector pane without changing the loaded session. | `button.click`, `ui.tool.click`, `ui.tool.active`. |
| Timing | Left rail | Activates timing pane with timing table and expand control. | `button.click`, `ui.tool.click`, `ui.tool.active`. |
| Score | Left rail | Activates scoring controls for ruleset, penalties, and selected shot score. | `button.click`, `ui.tool.click`, `ui.tool.active`. |
| Overlay | Left rail | Activates overlay position, badge size, badge color, and score color controls. | `button.click`, `ui.tool.click`, `ui.tool.active`. |
| Merge | Left rail | Activates second-angle, merge layout, sync, and swap controls. | `button.click`, `ui.tool.click`, `ui.tool.active`. |
| Layout | Left rail | Activates export layout quality, aspect, and crop controls. | `button.click`, `ui.tool.click`, `ui.tool.active`. |
| Export | Left rail | Activates local MP4 export controls. | `button.click`, `ui.tool.click`, `ui.tool.active`. |
| Place Score | Video stage in Score mode | Places scoring coordinates for the selected shot on the video preview. | `button.click`, `score.place.*`, `api.start /api/scoring/position`, `api.success`. |
| Select | Waveform | Sets waveform editor to select and drag shot markers. | `button.click`, `waveform.mode`. |
| Add Shot | Waveform | Sets waveform editor to click-to-add manual shot mode. | `button.click`, `waveform.mode`, then `api.start /api/shots/add` on waveform click. |
| Move Beep | Waveform | Sets waveform editor to click-to-place timer beep mode. | `button.click`, `waveform.mode`, then `api.start /api/beep` on waveform click. |
| Expand | Waveform | Makes waveform the primary work surface, hides video and inspector, and exposes the shot list. | `button.click`, `waveform.expand`. |
| Collapse | Waveform | Restores video, waveform, and inspector workspace. | `button.click`, `waveform.expand`. |
| Collapse | Timing workbench | Restores normal workspace after timing expansion. | `button.click`, `timing.expand`. |
| -10 ms | Selected shot | Moves selected shot 10 ms earlier. | `button.click`, `shot.button_nudge`, `api.start /api/shots/move`. |
| -1 ms | Selected shot | Moves selected shot 1 ms earlier. | `button.click`, `shot.button_nudge`, `api.start /api/shots/move`. |
| +1 ms | Selected shot | Moves selected shot 1 ms later. | `button.click`, `shot.button_nudge`, `api.start /api/shots/move`. |
| +10 ms | Selected shot | Moves selected shot 10 ms later. | `button.click`, `shot.button_nudge`, `api.start /api/shots/move`. |
| Delete Selected Shot | Selected shot | Deletes the selected shot and recalculates timing. | `button.click`, `api.start /api/shots/delete`. |
| Expand | Timing pane | Opens the expanded timing workbench and hides video, compact waveform, and inspector. | `button.click`, `timing.expand`. |
| Choose Secondary Video | Merge pane | Opens the local browser file picker for a second angle. | `button.click`, `control.change`, `api.files.secondary.*`. |
| -10 ms | Merge pane | Moves secondary sync offset 10 ms earlier. | `button.click`, `api.start /api/sync`. |
| -1 ms | Merge pane | Moves secondary sync offset 1 ms earlier. | `button.click`, `api.start /api/sync`. |
| +1 ms | Merge pane | Moves secondary sync offset 1 ms later. | `button.click`, `api.start /api/sync`. |
| +10 ms | Merge pane | Moves secondary sync offset 10 ms later. | `button.click`, `api.start /api/sync`. |
| Swap Angles | Merge pane | Swaps primary and secondary video assignments. | `button.click`, `api.start /api/swap`. |
| Browse | Export pane | Opens a native local path chooser for the MP4 output path. | `button.click`, `api.dialog.path.*`. |
| Export MP4 | Export pane | Runs local export to the selected output path. | `button.click`, `api.start /api/export`. |
| Primary Video | Project pane | Opens the local browser file picker for the primary stage video. | `button.click`, `control.change`, `api.files.primary.*`. |
| Second Angle | Project pane | Opens the local browser file picker for the secondary angle. | `button.click`, `control.change`, `api.files.secondary.*`. |
| New Project | Project pane | Clears the in-memory project. | `button.click`, `api.start /api/project/new`. |
| Browse | Project pane | Opens a native local path chooser for the project bundle path. | `button.click`, `api.dialog.path.*`. |
| Save | Project pane | Saves the current project bundle path. | `button.click`, `api.start /api/project/save`. |
| Open | Project pane | Opens the project bundle path. | `button.click`, `api.start /api/project/open`. |
| Delete | Project pane | Deletes the current project bundle. | `button.click`, `api.start /api/project/delete`. |

## Auto-Apply QA Matrix

| Control | Location | Expected app effect | QA evidence |
| --- | --- | --- | --- |
| Detection threshold | Review pane | Debounced re-run of shot detection threshold against the current primary video. | `control.change`, `auto_apply.threshold`, `api.start /api/analysis/threshold`. |
| Scoring enabled / preset / penalties | Scoring pane | Debounced scoring profile and penalty updates. | `control.change`, `auto_apply.scoring`, `api.start /api/scoring/profile`, `api.start /api/scoring`. |
| Score for selected shot | Scoring pane | Saves the chosen score letter to the selected shot. | `control.change`, `api.start /api/scoring/score`. |
| Overlay position / badge size / colors | Overlay pane | Debounced overlay preview/export settings update. | `control.change`, `auto_apply.overlay`, `api.start /api/overlay`. |
| Merge enabled / layout / PiP size | Merge pane | Debounced merge settings update. | `control.change`, `auto_apply.merge`, `api.start /api/merge`. |
| Layout quality / aspect / crop | Layout pane | Debounced export layout settings update. | `control.change`, `auto_apply.layout`, `api.start /api/layout`. |

## Validation Commands

```bash
node --check src/splitshot/browser/static/app.js
uv run pytest tests/test_browser_static_ui.py tests/test_browser_control.py
uv run pytest
uv run splitshot --check
```

## Audit Result

The browser UI now has a complete button inventory, global button click logging, route-level effect logging, and feature tests that prevent inert or unlogged buttons from entering the main browser cockpit.
