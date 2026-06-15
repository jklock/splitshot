# Queue Pane

The Queue pane is the multi-stage export surface. It shows queue status, lets you jump back into a stage, applies settings across stages, and processes the batch.

## Use This Pane For

- Reviewing queue status across stages.
- Jumping back into a stage from the queue.
- Applying one stage template to the rest of the project.
- Processing individual outputs or a combined output.

## Key Controls

| Control | What it does |
| --- | --- |
| `Add To Queue` | Queues the active stage. |
| `Apply Settings To All` | Copies the active stage template to the other stages. |
| Queue row | Selects that stage as active without leaving Queue. |
| `Edit Stage` | Makes that stage active and jumps back into Compose for edits. |
| `Remove` | Removes the stage from the queue. |
| `Requeue` | Requeues a stale stage. |
| `Process` | Exports one output file per queued stage. |
| `Process Into 1 File` | Renders all queued stages, then concatenates them into one file. |

## Status Meanings

| Status | Meaning |
| --- | --- |
| `Not Queued` | The stage is not queued. |
| `Queued` | The stage is ready to process. |
| `Processing` | The stage is currently exporting. |
| `Complete` | The stage finished processing. |
| `Failed` | The last queue attempt failed. |
| `Stale` | The stage was queued, then changed after `Apply Settings To All`. |

## Workflow

1. Configure one stage fully.
2. Add it to the queue.
3. Use `Apply Settings To All` when the other stages should inherit the same template.
4. Review the queue rows and re-enter any stage that still needs edits.
5. Click `Process` for one file per stage, or `Process Into 1 File` for a stitched output.

## Notes

- `Apply Settings To All` copies stage-local editing settings but excludes markers.
- Queue rows always point back to the underlying stage, not a detached export preset.
- Queue processing preserves queue order for combined output.

## Related Guides

Previous: [export.md](export.md)
Next: [metrics.md](metrics.md)
