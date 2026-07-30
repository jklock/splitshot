# Export Pane

The Export pane configures ffmpeg export settings for the active stage. It does not start processing directly.

<img src="../../screenshots/ExportPane.png" alt="Export pane with output profile, framing, codec, bitrate, and ffmpeg settings for the active stage" width="960">

<img src="../../screenshots/ExportPane2.png" alt="Lower Export pane with advanced frame-rate, codec, bitrate, color, and ffmpeg preset settings" width="840">

<img src="../../screenshots/ExportLogModal.png" alt="Export log modal showing processing output from the latest Queue run" width="840">

## Use This Pane For

- Setting the render settings for the active stage.
- Saving stage-local export settings before queueing.
- Checking the export log for the most recent processing run.

## Key Controls

| Control | What it does |
| --- | --- |
| Output Profiles selector | Loads or switches an output profile for the active stage. |
| `Create` / `Save Profile` / `Delete` | Creates a snapshot of the current Export settings, updates the selected profile, or removes it. |
| `Profile name` | Names the selected output profile. |
| `Type` | Chooses the stage output type. |
| `Frame profile` | Chooses the output framing override. |
| `Preset` | Chooses a built-in export preset or `Custom`. |
| `Quality` / `Aspect ratio` / `Output Width` / `Output Height` | Set the output frame. |
| `Frame rate` / `Video codec` / `Audio codec` | Set render codecs and playback rate. |
| `Video bitrate (Mbps)` / `Audio kbps` | Set target bitrate values. |
| `Color` / `Ffmpeg preset` / `2-pass` | Set encoding behavior for the active stage. |
| `Show Log` | Opens the export log from the latest queue processing run. |

## Workflow

1. Finish Compose, Trim, scoring, overlay, review, and metrics checks for the active stage.
2. Set the output profile and any stage-local export settings.
3. Move to [queue.md](queue.md) to queue the stage and process one or more outputs.

## Notes

- Export settings are stage-local.
- Selecting a saved profile applies its framing and ffmpeg settings to the active stage. If that stage is queued, it changes to `Needs requeue`.
- Profiles never store output paths, logs, or errors.
- Export changes settings only. Queue is the only export execution surface.
- Review the stage here, then queue and process it downstream.

## Related Guides

Previous: [review.md](review.md)
Next: [queue.md](queue.md)
