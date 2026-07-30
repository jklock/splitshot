# Queue Pane

The Queue pane is the multi-stage export surface. It shows queue status, selects which stage Queue is acting on, applies settings across stages, and processes one or many outputs.

<img src="../../screenshots/QueuePane.png" alt="Queue pane with active-stage selection, queue status rows, settings propagation, and processing actions" width="960">

## Use This Pane For

- Reviewing queue status across stages.
- Selecting the active stage from Queue without leaving Queue.
- Applying one stage's settings to the rest of the queued stages.
- Processing individual outputs or a combined output.

## Key Controls

| Control | What it does |
| --- | --- |
| `Queue` / `Requeue` | Queues the active stage. |
| `Unqueue` | Removes the active stage from the queue. |
| `Apply Active Stage Settings to Queued` | Copies the active stage settings to the queued stages. |
| `Stage` | Chooses which stage Queue is acting on. |
| Queue row | Shows one queued stage with its current queue status. |
| `Fade in` / `Fade out` | Sets project-level video and audio fades in 0.1-second steps. `0` disables that boundary. |
| `Show Output Folder` | Opens the configured project output directory. |
| `Process Many` | Exports one output file per queued stage. |
| `Process Into 1 File` | Renders all queued stages, then concatenates them into one file. |

## Status Meanings

| Status | Meaning |
| --- | --- |
| `Not Queued` | The stage is not queued. |
| `Queued` | The stage is ready to process. |
| `Processing` | The stage is currently exporting. |
| `Complete` | The stage finished processing. |
| `Failed` | The last queue attempt failed. |
| `Needs requeue` | The stage was queued, then changed and should be queued again. |

## Workflow

1. Configure one stage fully.
2. Select that stage in Queue and click `Queue`.
3. Use `Apply Active Stage Settings to Queued` when the other queued stages should inherit the same settings.
4. Review the queue rows and switch the active stage there when another stage needs attention.
5. Click `Process Many` for one file per stage, or `Process Into 1 File` for a stitched output.

## Notes

- Queue does not replace Media. If stage media needs to change, go back to Media after selecting the right stage.
- Queue executes the ffmpeg settings saved in Export; changing settings in Export does not render a file until Queue processing starts.
- `Apply Active Stage Settings to Queued` copies stage-local editing settings but excludes markers.
- Queue rows always point back to the underlying stage, not a detached export preset.
- Queue rows are compact and always visible; they do not have a collapsed state.
- Queue processing preserves queue order for combined output.
- The green processing bar tracks the whole queue and reaches 100% only after every stage has been attempted and any combined file has been faded and validated.
- Individual mode fades each stage output. One-file mode fades only the outer boundaries of the combined file. Short clips automatically scale overlapping fade requests.

## Related Guides

Previous: [export.md](export.md)
Next: [metrics.md](metrics.md)
