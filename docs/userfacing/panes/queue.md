# Queue Pane

The Queue pane is the multi-stage export surface. It shows queue status, lets you jump back into a stage via Media, applies settings across stages, and processes one or many outputs.

## Use This Pane For

- Reviewing queue status across stages.
- Selecting a stage from the queue without leaving Queue.
- Jumping back into a stage for edits via Media.
- Applying one stage template to the rest of the project.
- Processing individual outputs or a combined output.

## Key Controls

| Control | What it does |
| --- | --- |
| `Queue` / `Requeue` | Queues the active stage. |
| `Apply Current Stage Template To All` | Copies the active stage template to the other stages. |
| Queue row | Selects that stage as active without leaving Queue. |
| `Edit Stage` | Makes that stage active and jumps back into Media for edits. |
| `Remove` | Removes the stage from the queue. |
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
2. Queue it.
3. Use `Apply Current Stage Template To All` when the other stages should inherit the same template.
4. Review the queue rows, select stages in place, and re-enter any stage that still needs edits.
5. Click `Process Many` for one file per stage, or `Process Into 1 File` for a stitched output.

## Notes

- `Edit Stage` navigates to Media for file and stage-level editing.
- `Apply Settings To All` copies stage-local editing settings but excludes markers.
- Queue rows always point back to the underlying stage, not a detached export preset.
- Queue processing preserves queue order for combined output.

## Related Guides

Previous: [export.md](export.md)
Next: [metrics.md](metrics.md)
