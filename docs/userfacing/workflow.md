# SplitShot Workflow

This is the recommended multi-stage workflow.

## End-To-End Flow

1. Open [panes/project.md](panes/project.md).
2. Create or open the project bundle.
3. Import the PractiScore CSV/TXT source if stage records are needed.
4. Select the imported stage, competitor name, and competitor place.
5. Open [panes/media.md](panes/media.md).
6. Pair one primary video and any added media for each stage using Set Primary, Add More, and file removal.
7. Click Edit Stage to make the stage live for editing.
8. Open [panes/pip.md](panes/pip.md) and configure the active stage composition.
9. Open Trim, Score, Splits, Markers, Overlay, Review, and Metrics as needed for the active stage.
10. Open [panes/export.md](panes/export.md), configure the active stage output, and queue it.
11. Open [panes/queue.md](panes/queue.md).
12. Use `Apply Settings To All` if the other stages should inherit the active stage template.
13. Re-enter any stage that still needs changes via Edit Stage.
14. Click `Process Many` for one file per stage, or `Process Into 1 File` for a stitched output.

## Practical Order

- Import PractiScore before Media when stage records should drive the project.
- Pair media in Media before Compose.
- Finish timing before final overlay and review layout.
- Queue only after the active stage looks correct in preview.
- Use Queue as the batch export surface rather than exporting each stage manually.
- Edit Stage routes you into Media, not Compose.

## Related Guides

- [panes/project.md](panes/project.md)
- [panes/media.md](panes/media.md)
- [panes/export.md](panes/export.md)
- [panes/queue.md](panes/queue.md)
- [troubleshooting.md](troubleshooting.md)
