# Project Pane

The Project pane is where a SplitShot session starts. Use it to name the run, load the primary video, import PractiScore context, and choose the project folder that keeps the session bundled for later reopening.

<img src="../../screenshots/ProjectPane.png" alt="Project pane with project metadata, PractiScore import, primary video selection, and project folder controls" width="960">

## When To Use This Pane

- When you are starting a brand-new run.
- When you want to switch to a different primary video.
- When you want to import or change PractiScore stage context.
- When you want to create, reopen, or replace the current project bundle.

## Before You Start

- Keep the primary stage video on a local drive.
- If you want match context, keep the PractiScore CSV or TXT file ready.
- Decide where you want the saved project bundle to live if you plan to revisit the run later.

## Key Controls

| Control | What it does |
| --- | --- |
| `Project name` | Sets the saved name shown for the current run. |
| `Project description` | Stores notes about the run, stage, or edit plan inside the bundle. |
| `PractiScore Import` | Groups the match-context controls and shows whether stage results are already imported. |
| `Match type` | Chooses the ruleset family for the staged PractiScore file, such as USPSA, IPSC, or IDPA. |
| `Stage #` | Chooses which stage from the staged results file should drive the imported stage summary. |
| `Competitor name` | Chooses the competitor from the staged results file. |
| `Place` | Chooses the competitor's place entry from the staged results file. |
| `Select PractiScore File` | Loads a PractiScore CSV or TXT file and stages it for the current project. |
| Imported summary rows | Show the staged source file, match type, stage, competitor, division, raw time, and final result that were imported. |
| `Primary Video` | Shows the current primary-video path and also accepts a pasted local path. Press Enter to import the pasted path. |
| `Select Primary Video` | Opens the file chooser for the primary stage video. |
| `Project folder` | Shows the folder used for the current project bundle. |
| `Choose Project` | Opens an existing project folder or creates a new bundle location for the current project. |
| `New Project` | Clears the current project and starts a fresh session. |
| `Delete Project` | Deletes the saved project bundle from disk and resets SplitShot to an empty project. |

## How To Use It

1. Enter a clear `Project name` and an optional `Project description` so the run is easy to recognize when you reopen it later.
2. If you want official stage context, click `Select PractiScore File`, then choose the correct `Match type`, `Stage #`, `Competitor name`, and `Place` from the populated lists.
3. Import the primary video with `Select Primary Video`, or paste the full path into `Primary Video` and press Enter.
4. Prefer the direct path workflow for very large files. It lets SplitShot read the video from disk directly instead of pushing the file through a browser upload flow.
5. Wait for the status bar to confirm local analysis. SplitShot will detect the beep, shots, and waveform before the timing and scoring panes can be trusted.
6. Set `Project folder` with `Choose Project` if you want the run saved as a reusable bundle. Opening an existing bundle restores the project state; choosing an empty folder lets SplitShot create a new one for the current run.
7. Use `New Project` only when you want a clean session. Use `Delete Project` only when you want to remove the saved bundle from disk.

## How It Affects The Rest Of SplitShot

- The primary video creates the waveform, shot list, and status messages used by Splits.
- Imported PractiScore context feeds Score, Review, Overlay, Export, and Metrics.
- The chosen project folder is where SplitShot keeps the session bundle for later reopening.
- Replacing the primary video resets media-bound state such as detected shots, PiP media, and prior export logs.

## Common Mistakes And Fixes

| Problem | Fix |
| --- | --- |
| The primary video field changed but nothing imported. | Press Enter after pasting a path, or use `Select Primary Video` for the file picker flow. |
| A huge file feels slow to load through the browser picker. | Paste the direct local path into `Primary Video` and press Enter. |
| PractiScore imported the wrong run. | Recheck `Stage #`, `Competitor name`, and `Place` after staging the file. |
| A previous project reopened instead of saving the current one. | Confirm the `Project folder` field before clicking `Choose Project`. |
| SplitShot looks empty after `New Project`. | That is expected. Import the primary video again for the new session. |

## Related Guides

Previous: [../USER_GUIDE.md](../USER_GUIDE.md)
Next: [splits.md](splits.md)

**Last updated:** 2026-04-18
**Referenced files last updated:** 2026-04-18