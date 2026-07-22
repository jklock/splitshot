# SplitShot Workflow

This is the recommended multi-stage workflow.

## End-To-End Flow

1. Open [panes/project.md](panes/project.md).
2. Create or open the project folder.
   SplitShot creates `Input/`, `CSV/`, `Markers/`, and `Output/`; subsequent pickers start in the matching project folder.
3. Import the PractiScore CSV/TXT source if stage records are needed.
4. Select the imported stage, competitor name, and competitor place.
5. Open [panes/media.md](panes/media.md).
6. Pair one primary video and any added media for each stage using Add Primary, Add Media, Set Primary, and file removal.
7. Leave the correct stage selected in Media so the rest of the app edits that stage.
8. Open [panes/compose.md](panes/compose.md) and configure the active stage composition.
9. Open [panes/trim.md](panes/trim.md), [panes/score.md](panes/score.md), [panes/splits.md](panes/splits.md), [panes/markers.md](panes/markers.md), [panes/overlay.md](panes/overlay.md), [panes/review.md](panes/review.md), and [panes/metrics.md](panes/metrics.md) as needed for the active stage.
10. Open [panes/export.md](panes/export.md) and configure the active stage output settings.
11. Open [panes/queue.md](panes/queue.md).
12. Use `Apply Active Stage Settings to Queued` if the other queued stages should inherit the active stage settings.
13. Re-select any stage that still needs changes from Media or Queue.
14. Click `Process Many` for one file per stage, or `Process Into 1 File` for a stitched output.

## Practical Order

- Import PractiScore before Media when stage records should drive the project.
- Files selected outside the project are copied into the appropriate project folder during import, so the complete project folder stays portable.
- Pair media in Media before Compose.
- Finish timing before final overlay and review layout.
- Queue only after the active stage looks correct in preview.
- Use Queue as the batch export surface rather than exporting each stage manually.
- Export is settings only. Queue is where processing starts.

## Related Guides

- [panes/project.md](panes/project.md)
- [panes/media.md](panes/media.md)
- [panes/compose.md](panes/compose.md)
- [panes/trim.md](panes/trim.md)
- [panes/export.md](panes/export.md)
- [panes/queue.md](panes/queue.md)
- [troubleshooting.md](troubleshooting.md)
