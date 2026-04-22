# Project Pane

The Project pane is the setup surface for a SplitShot run. It names the project, imports the primary video, stages PractiScore context, and chooses the folder that stores the project bundle.

<img src="../../screenshots/ProjectPane.png" alt="Project pane with project name, description, PractiScore import, primary video path, and project folder controls" width="960">

## When To Use This Pane

- Start a new run.
- Load or replace the primary stage video.
- Import official stage context from PractiScore.
- Choose, reopen, or delete the saved project bundle.

## Key Controls

| Control | What it does |
| --- | --- |
| `Project name` | Sets the saved name shown in the app and metrics/export filenames. |
| `Project description` | Stores project notes, stage reminders, or edit plans. |
| `PractiScore Import` | Groups match-context controls and shows whether stage data is imported. |
| `Match type` | Chooses the scoring family for the staged file, such as IDPA, USPSA, or IPSC. |
| `Stage #` | Selects the stage from the imported match file. |
| `Competitor name` | Selects the competitor record from the staged data. |
| `Place` | Selects the matching place entry when duplicate competitor rows exist. |
| `Select PractiScore File` | Loads a PractiScore CSV or TXT file. |
| Imported summary rows | Show source file, match type, official raw time, SplitShot raw time, raw delta, final value, and official final value. |
| `Primary Video` | Shows the current primary path and accepts a pasted local path. Press Enter after pasting. |
| `Select Primary Video` | Opens the file picker for the primary video. |
| `Project folder` | Shows the bundle folder for the current project. |
| `Choose Project` | Opens an existing bundle or chooses a folder for the current run. |
| `New Project` | Clears the current session and starts a blank project. |
| `Delete Project` | Removes the saved project bundle and resets the current session. |

## How To Use It

1. Enter `Project name` and `Project description` before deeper editing so screenshots, exports, and metrics have meaningful labels.
2. Click `Select Primary Video`, or paste the absolute path into `Primary Video` and press Enter.
3. Wait for local analysis to finish. The waveform, shot list, metrics, score rows, and overlays depend on that analysis.
4. If you want official match context, click `Select PractiScore File`, then confirm `Match type`, `Stage #`, `Competitor name`, and `Place`.
5. Use `Choose Project` when you want SplitShot to save the current work as a reusable bundle.
6. Use `New Project` for a clean session and `Delete Project` only when the saved bundle should be removed from disk.

## Downstream Effects

- Primary video import creates the waveform, detected shots, beep marker, and timing rows.
- PractiScore context feeds Score, Review summary boxes, Overlay final results, Export, and Metrics.
- Replacing the primary video resets media-bound state such as timing, PiP media, and export logs.
- The project folder is the persistent home for the current bundle.

## Common Fixes

| Problem | Fix |
| --- | --- |
| The video path changed but nothing imported. | Press Enter in `Primary Video`, or use `Select Primary Video`. |
| A large file imports slowly through the browser picker. | Paste the direct local path instead. |
| The imported result is for the wrong run. | Recheck `Match type`, `Stage #`, `Competitor name`, and `Place`. |
| A previous project reopened unexpectedly. | Confirm the `Project folder` before using `Choose Project`. |
| The app looks empty after `New Project`. | Import a primary video again. |

## Related Guides

Previous: [../USER_GUIDE.md](../USER_GUIDE.md)
Next: [shotml.md](shotml.md)

**Last updated:** 2026-04-22
**Referenced files last updated:** 2026-04-22
