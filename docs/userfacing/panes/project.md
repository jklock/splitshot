# Project Pane

The Project pane is the setup surface for a SplitShot run. It chooses the project folder, stores project details, stages PractiScore context from a local CSV/TXT export, offers a quick browser shortcut to PractiScore, and imports the primary video.

<img src="../../screenshots/ProjectPane.png" alt="Project pane with project name, PractiScore browser opener, import controls, primary video path, and project folder controls" width="960">

## When To Use This Pane

- Start a new run.
- Load or replace the primary stage video.
- Open PractiScore in your browser when you need to log in or download results.
- Import official stage context from a local PractiScore CSV or TXT file.
- Create, select, or delete the saved project metadata for a bundle.

## Key Controls

| Control | What it does |
| --- | --- |
| `Project folder` | Shows the current project folder name. Before a project exists it stays blank and prompts you to create or select one. |
| `Select Project` | Opens an existing project bundle or adopts a folder for the current run. |
| `Create Project` | Clears the current session and saves a new project into the selected folder. |
| `Delete Project` | Removes only `project.json`, resets the current session, and leaves the project folders and files on disk. |
| `Project name` | Sets the saved name shown in the app and metrics/export filenames. |
| `Project description` | Stores project notes, stage reminders, or edit plans. |
| `PractiScore Import` | Groups the browser shortcut, local file import, and staged match-context controls while showing whether stage data is imported. |
| `Open PractiScore Dashboard` | Opens `https://practiscore.com/dashboard/home` in your system browser so you can log in or download results. Disabled until a project is active. |
| `Select PractiScore File` | Imports a local PractiScore CSV/TXT file as the active staged source. Disabled until a project is active. |
| `Match type` | Chooses the scoring family for the staged file, such as IDPA, USPSA, or IPSC. |
| `Stage #` | Selects the stage from the imported match file. |
| `Competitor name` | Selects the competitor record from the staged data. |
| `Place` | Selects the matching place entry when duplicate competitor rows exist. `Competitor name` and `Place` stay synchronized. |
| Imported summary rows | Show source file, match type, official raw time, SplitShot raw time, raw delta, final value, and official final value. |
| `Primary Video` | Shows the current primary path and accepts a pasted local path. Press Enter after pasting. Disabled until a project is active. |
| `Select Primary Video` | Opens the file picker for the primary video. Disabled until a project is active. |

## How To Use It

1. Click `Create Project` or `Select Project` first. The PractiScore and primary-video buttons stay disabled until a project is active.
2. Enter `Project name` and `Project description` before deeper editing so screenshots, exports, and metrics have meaningful labels.
3. If you need a PractiScore export, click `Open PractiScore Dashboard`, use your browser to download the relevant CSV/TXT result, then return to SplitShot.
4. Click `Select PractiScore File` and choose the exported CSV/TXT file.
5. Confirm `Match type`, `Stage #`, `Competitor name`, and `Place`.
6. When a competitor name is unique, selecting it also selects the matching `Place`. Selecting a duplicate `Place` backfills the matching competitor row.
7. Click `Select Primary Video`, or paste the absolute path into `Primary Video` and press Enter.
8. Wait for local analysis to finish. The waveform, shot list, metrics, score rows, and overlays depend on that analysis.
9. Use `Create Project` for a clean session and `Delete Project` when the saved metadata should be removed without deleting the folder contents.

## Downstream Effects

- Primary video import creates the waveform, detected shots, beep marker, and timing rows.
- PractiScore context from the imported local CSV/TXT file feeds Score, Review summary boxes, Overlay final results, Export, and Metrics.
- Replacing the primary video resets media-bound state such as timing, PiP media, and export logs.
- The project folder is the persistent home for the current bundle.

## Common Fixes

| Problem | Fix |
| --- | --- |
| The video path changed but nothing imported. | Press Enter in `Primary Video`, or use `Select Primary Video`. |
| A large file imports slowly through the browser picker. | Paste the direct local path instead. |
| PractiScore dashboard does not open. | Click `Open PractiScore Dashboard` again. If your browser blocks the launch, open `https://practiscore.com/dashboard/home` manually. |
| The imported result is for the wrong run. | Click `Select PractiScore File` again with the correct CSV/TXT export. |
| The imported stage is right but the competitor row is wrong. | Recheck `Match type`, `Stage #`, `Competitor name`, and `Place`. |
| A previous project reopened unexpectedly. | Confirm the `Project folder` before using `Select Project`. |
| The app looks empty after `Create Project`. | Import a primary video again. |

## Related Guides

Previous: [../USER_GUIDE.md](../USER_GUIDE.md)
Next: [shotml.md](shotml.md)

**Last updated:** 2026-04-27
**Referenced files last updated:** 2026-04-27
