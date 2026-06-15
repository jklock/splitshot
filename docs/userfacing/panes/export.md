# Export Pane

The Export pane configures export settings for the active stage. In the multi-stage workflow, its primary action is `Add To Queue`.

## Use This Pane For

- Setting the output path and render settings for the active stage.
- Saving stage-local export settings before queueing.
- Adding the active stage to the queue.

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
| `Output path` | Sets the destination file path for the active stage output. |
| `Browse` | Opens the save dialog for the output path. |
| `Add To Queue` | Queues the active stage instead of rendering immediately. |
| `Export Video` | Runs an immediate single-stage export. |

## Workflow

1. Finish Compose, Trim, scoring, overlay, review, and metrics checks for the active stage.
2. Set the output path and any export profile choices.
3. Click `Add To Queue`.
4. Move to [queue.md](queue.md) to process one or more queued stages.

## Notes

- Export settings are stage-local.
- `Add To Queue` is the batch workflow entry point.
- `Export Video` is still available when you want an immediate single-stage render.

## Related Guides

Previous: [review.md](review.md)
Next: [queue.md](queue.md)
