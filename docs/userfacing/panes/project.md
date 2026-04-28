# Project Pane

The Project pane is the setup surface for a SplitShot run. It names the project, imports the primary video, stages PractiScore context, runs the background PractiScore sync flow when you need official match data, preserves manual CSV/TXT import as fallback, and chooses the folder that stores the project bundle.

<img src="../../screenshots/ProjectPane.png" alt="Project pane with project name, PractiScore browser opener, import controls, primary video path, and project folder controls" width="960">

## When To Use This Pane

- Start a new run.
- Load or replace the primary stage video.
- Connect to PractiScore and let SplitShot import the selected remote match in the background.
- Import official stage context from a local PractiScore CSV or TXT file when remote sync is unavailable.
- Choose, reopen, or delete the saved project bundle.

## Key Controls

| Control | What it does |
| --- | --- |
| `Project name` | Sets the saved name shown in the app and metrics/export filenames. |
| `Project description` | Stores project notes, stage reminders, or edit plans. |
| `PractiScore Import` | Groups the remote session controls, background import flow, manual fallback import, and staged match-context controls while showing whether stage data is imported. |
| `Connect PractiScore` | Reuses an authenticated PractiScore session from a supported browser when one already exists. If no session is available, SplitShot opens PractiScore in your browser so background sync can continue after login. |
| `Clear PractiScore Session` | Clears the cached PractiScore session so the next connect starts from a fresh login. |
| `Remote match` | Lists the remote PractiScore matches available for the authenticated session. |
| `Import Selected Match` | Downloads the selected remote PractiScore match in the background and stages it as the current source. |
| Session and sync status | Shows whether PractiScore is connected, whether matches are loading, and whether the selected remote import succeeded or failed. |
| `Match type` | Chooses the scoring family for the staged file, such as IDPA, USPSA, or IPSC. |
| `Stage #` | Selects the stage from the imported match file. |
| `Competitor name` | Selects the competitor record from the staged data. |
| `Place` | Selects the matching place entry when duplicate competitor rows exist. `Competitor name` and `Place` stay synchronized. |
| `Select PractiScore File` | Imports a local PractiScore CSV/TXT file as the manual fallback or replacement path. |
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
4. If you want official match context from PractiScore.com, click `Connect PractiScore`.
5. If you are already logged into PractiScore in a supported browser, SplitShot reuses that session immediately. Otherwise finish the login or challenge in your browser.
6. Wait for SplitShot to load the remote match list. If only one remote match is available and nothing is staged yet, SplitShot imports it automatically.
7. If multiple remote matches are available, choose the correct one in `Remote match`, then click `Import Selected Match`.
8. Confirm `Match type`, `Stage #`, `Competitor name`, and `Place`.
9. When a competitor name is unique, selecting it also selects the matching `Place`. Selecting a duplicate `Place` backfills the matching competitor row.
10. Use `Select PractiScore File` only when remote sync is unavailable or when you want to replace the staged source with a local CSV/TXT file.
11. Use `Choose Project` when you want SplitShot to save the current work as a reusable bundle.
12. Use `New Project` for a clean session and `Delete Project` only when the saved bundle should be removed from disk.

## Downstream Effects

- Primary video import creates the waveform, detected shots, beep marker, and timing rows.
- PractiScore context from the background remote import or manual CSV/TXT fallback feeds Score, Review summary boxes, Overlay final results, Export, and Metrics.
- Replacing the primary video resets media-bound state such as timing, PiP media, and export logs.
- The project folder is the persistent home for the current bundle.

## Common Fixes

| Problem | Fix |
| --- | --- |
| The video path changed but nothing imported. | Press Enter in `Primary Video`, or use `Select Primary Video`. |
| A large file imports slowly through the browser picker. | Paste the direct local path instead. |
| PractiScore does not connect. | Click `Connect PractiScore` again. If the browser session looks wrong, use `Clear PractiScore Session` first, then reconnect so SplitShot reimports the browser session. |
| SplitShot never sees my PractiScore login. | Stay logged in to PractiScore in a **supported system browser** (Chrome, Edge, Firefox, Safari, and several Chromium variants). On some systems the browser’s cookie database is locked while the browser is open—try quitting that browser once, then connect again. If you use several browsers, SplitShot picks the session with the most PractiScore cookies; use `Clear PractiScore Session` and log in only in the browser you want to use, then reconnect. |
| The imported result is for the wrong run. | Pick the correct `Remote match` and click `Import Selected Match` again, or use `Select PractiScore File` to replace the staged source manually. |
| The imported stage is right but the competitor row is wrong. | Recheck `Match type`, `Stage #`, `Competitor name`, and `Place`. |
| A previous project reopened unexpectedly. | Confirm the `Project folder` before using `Choose Project`. |
| The app looks empty after `New Project`. | Import a primary video again. |

## Related Guides

Previous: [../USER_GUIDE.md](../USER_GUIDE.md)
Next: [shotml.md](shotml.md)

**Last updated:** 2026-04-27
**Referenced files last updated:** 2026-04-27
