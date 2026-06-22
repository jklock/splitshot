# Export Pane

The Export pane configures export settings for the active stage. It no longer renders a file directly.

## Use This Pane For

- Setting the output path template and render settings for the active stage.
- Saving stage-local export settings before queueing.
- Checking the export log for the most recent processing run.

## Key Controls

| Control | What it does |
| --- | --- |
| Output Profiles selector | Loads or saves export framing presets for the active stage. |
| `Profile name` | Names the selected output profile. |
| `Type` | Chooses the stage output type. |
| `Frame profile` | Chooses the output framing override. |
| `Preset` | Chooses a built-in export preset or `Custom`. |
| `Aspect ratio` / `Output Width` / `Output Height` | Set the output frame. |
| `Frame rate` / `Video codec` / `Audio codec` | Set render codecs and playback rate. |
| `Multi-Track` | Includes all loaded tracks in the rendered export when enabled. |
| `Output path template` | Sets the destination file path template for the active stage output. |
| `Browse` | Opens the save dialog for the output path. |
| `Show Log` | Opens the export log from the latest queue processing run. |

## Workflow

1. Finish Compose, Trim, scoring, overlay, review, and metrics checks for the active stage.
2. Set the output path template and any export profile choices.
3. Move to [queue.md](queue.md) to queue the stage and process one or more outputs.

## Notes

- Export settings are stage-local.
- Queue is the only export execution surface.
- Review the stage here, then queue and process it downstream.

## Related Guides

Previous: [review.md](review.md)
Next: [queue.md](queue.md)
