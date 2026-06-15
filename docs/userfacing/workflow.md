# SplitShot Workflow

This is the recommended multi-stage workflow.

## End-To-End Flow

1. Open [panes/project.md](panes/project.md).
2. Create or open the project bundle.
3. Import the PractiScore CSV/TXT source if stage records are needed.
4. Open [panes/media.md](panes/media.md).
5. Pair one primary video and any added media for each stage.
6. Select the stage you want to edit first.
7. Open [panes/pip.md](panes/pip.md) and configure the active stage composition.
8. Open Trim, Score, Splits, Markers, Overlay, Review, and Metrics as needed for the active stage.
9. Open [panes/export.md](panes/export.md), configure the active stage output, and click `Add To Queue`.
10. Open [panes/queue.md](panes/queue.md).
11. Use `Apply Settings To All` if the other stages should inherit the active stage template.
12. Re-enter any stage that still needs changes.
13. Click `Process` for one file per stage, or `Process Into 1 File` for a stitched output.

## Practical Order

- Import PractiScore before Media when stage records should drive the project.
- Pair media before Compose.
- Finish timing before final overlay and review layout.
- Queue only after the active stage looks correct in preview.
- Use Queue as the batch export surface rather than exporting each stage manually.

## Related Guides

- [panes/project.md](panes/project.md)
- [panes/media.md](panes/media.md)
- [panes/export.md](panes/export.md)
- [panes/queue.md](panes/queue.md)
- [troubleshooting.md](troubleshooting.md)
