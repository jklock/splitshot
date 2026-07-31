# Troubleshooting

## Project And Stage Setup

| Problem | Fix |
| --- | --- |
| The project opens but no stages appear. | Import the PractiScore CSV/TXT file again in Project, or confirm the project was saved after stage generation. |
| The wrong stage is active. | Select the correct stage in Media. Queue membership does not change the live editing stage. |
| A stage has no media. | Open Media, choose the correct stage, and import the primary video with Add Primary or Replace. |
| Added media is attached to the wrong stage. | Select the correct stage in Media, remove the wrong file from the file list, then re-import on the correct stage with Add Media. |

## Compose, Trim, And Review

| Problem | Fix |
| --- | --- |
| Changes seem to affect the wrong stage. | Confirm the active stage in Media before editing. |
| Added media is missing from preview or export. | Turn on `Enable added media export` in Compose for the active stage. |
| The stage looks right but queue output is stale. | Requeue the stage from Queue after editing it again. |

## Export And Queue

| Problem | Fix |
| --- | --- |
| `Queue` does nothing. | Confirm the selected stage has a primary video and valid export settings. |
| `Process Queue` skips a stage. | Check whether the row is `Queued`, `Stale`, or `Failed`. |
| Combined output order is wrong. | Review the match-stage order before running `Process as One File`. |
| A stage was complete, then changed back to stale. | That is expected after copying settings or editing a queued stage. Requeue it. |
| I changed export settings but nothing processed yet. | That is expected. Export only saves settings; Queue starts processing. |

## Files And Project Folder

| Problem | Fix |
| --- | --- |
| The project reopens but exported files land in the wrong place. | Recheck the project output root in `Project`, then process again from `Queue`. |
| PractiScore context is missing after reopen. | Confirm the staged CSV/TXT file still exists in the project `CSV/` folder and re-import if needed. |
| Output files are hard to find. | Check the project `Output/` folder described in [project-structure.md](project-structure.md). |
| A picker opened outside the project. | Confirm a project is active. Project content pickers use the active project as their starting location; a file chosen elsewhere is copied into the matching project subfolder. |

## Related Guides

- [workflow.md](workflow.md)
- [project-structure.md](project-structure.md)
