# Troubleshooting

## Project And Stage Setup

| Problem | Fix |
| --- | --- |
| The project opens but no stages appear. | Import the PractiScore CSV/TXT file again in Project, or confirm the project was saved after stage generation. |
| The wrong stage is active. | Select the correct stage in Media. Edit Stage makes the stage live. |
| A stage has no media. | Open Media, expand the stage card, and import the primary video with Set Primary. |
| Added media is attached to the wrong stage. | Select the correct stage in Media, remove the wrong file from the file list, then re-import on the correct stage with Add More. |

## Compose, Trim, And Review

| Problem | Fix |
| --- | --- |
| Changes seem to affect the wrong stage. | Confirm the active stage in Media before editing. |
| Added media is missing from preview or export. | Turn on `Enable added media export` in Compose for the active stage. |
| The stage looks right but queue output is stale. | Requeue the stage from Queue after editing it again. |
| `Apply Settings To All` copied something unexpected. | It copies stage-local settings and excludes markers. Re-enter the affected stage and adjust as needed. |

## Export And Queue

| Problem | Fix |
| --- | --- |
| `Add To Queue` does nothing. | Confirm the active stage has a primary video and a valid output path. |
| `Process` skips a stage. | Check whether the row is `Queued`, `Stale`, or `Failed`. |
| Combined output order is wrong. | Review the queue order before running `Process Into 1 File`. |
| A stage was complete, then changed back to stale. | That is expected after copying settings or editing a queued stage. Requeue it. |
| Edit Stage takes you to the wrong pane. | It navigates to Media. If you need Compose or Trim, use the rail after selecting the stage. |

## Files And Project Bundle

| Problem | Fix |
| --- | --- |
| The bundle reopens but output paths are wrong. | Recheck the stage output path in Export, then save the project again. |
| PractiScore context is missing after reopen. | Confirm the staged CSV/TXT file still exists in the project bundle and re-import if needed. |
| Output files are hard to find. | Check the project `Output/` folder described in [project-structure.md](project-structure.md). |

## Related Guides

- [workflow.md](workflow.md)
- [project-structure.md](project-structure.md)
