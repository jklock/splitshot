# Performance Pane

The Performance pane is the history and analytics surface for saved stage and match records. It lets you browse prior results, reopen the linked Stage or Match workspace, keep lightweight notes and tags with each record, export the library as CSV or JSON, and create or restore a library backup without reopening the original edit session first.

In the current shared shell, summary tiles, record lists, and analytics stay in the main area, the selected record stays visible in the lower pane, and the right-hand inspector owns filters, reopen actions, notes/tags, backup/export, and Performance-only settings.

![Performance overview with summary tiles and top-level export and refresh actions](../../../artifacts/performance-bundle-20260524/screenshots/overview.png)

![Performance detail view with the selected record payload, reopen actions, tags, and notes editors](../../../artifacts/performance-bundle-20260524/screenshots/detail.png)

![Performance analytics section with score trend, discipline breakdown, and outlier messaging](../../../artifacts/performance-bundle-20260524/screenshots/analytics.png)

## When To Use This Pane

- Review finished stage and match history in one place.
- Reopen a saved stage or workspace from a library record.
- Add coaching notes or lightweight tags that travel with the stored record.
- Export the library for spreadsheet work, scripting, or backup review.
- Check score trend and discipline breakdown without opening the original editor again.
- Create or restore a library backup before cleanup, migration, or troubleshooting.

## Key Controls

| Control | What it does |
| --- | --- |
| `Overview` | Keeps the summary tiles and personal-best list in the main area while the right-hand inspector summarizes the current dataset. |
| `Records` | Keeps the saved stage and match rows in the main area while the right-hand inspector owns search, sort, discipline filter, refresh, and export actions. |
| `Detail` | Keeps the selected record payload in the lower pane and opens the right-hand inspector section for reopen, tags, and notes actions. |
| `Analytics` | Keeps score trend, discipline breakdown, and outlier messaging in the main area while the right-hand inspector reports the current analytics scope. |
| `Backup` | Opens the library backup and restore entry points for saved history records. |
| `Settings` | Stores Performance-only defaults such as the default sort order and whether the library refreshes automatically when it opens. |
| `Update Library` | Reloads the current library records from disk. Use this when auto-refresh is turned off or after new records are saved elsewhere. |
| `Export CSV` | Downloads the normalized library rows as CSV. |
| `Export JSON` | Downloads the normalized library payload as JSON. |
| `Open Stage` | Reopens the selected stage record in Stage Video Edit when that record has a saved editor target. |
| `Open Workspace` | Reopens the selected match record in Match Video Edit when that record has a saved workspace target. |
| `Add` / `Save Notes` | Saves Performance tags or notes for the selected record. |

## How To Use It

1. Open `Performance Library` from the landing surface.
2. Start in `Overview` for a quick read on how many records are loaded and what the current library looks like.
3. Move to `Records` when you need to search by name/date, sort the library, or narrow the list by discipline; those controls live in the right-hand inspector while the rows stay in the main area.
4. Click a row to refresh the lower selected-record pane, then open `Detail` when you want reopen actions, tags, or notes for that record.
5. Open `Analytics` when you want the trend and discipline roll-up view. If SplitShot does not have enough data yet, trust the hint text — it is intentionally conservative.
6. Use `Export CSV` or `Export JSON` when you need a portable copy of the current library data.
7. Open `Backup` before a migration or cleanup pass so you can create a restorable library snapshot.
8. Open `Settings` if you want a different default sort or if you prefer manual refresh over automatic refresh on open.

## What Saves Here

Performance is mostly read-only for the record truth it shows, but it does own a few lightweight edits:

- `Add` and `Save Notes` update the stored library record, not the live timing or scoring editors.
- `Open Stage` and `Open Workspace` jump back to the original editor target when that path still exists.
- `Default Sort` and `Refresh records when the library opens` are local Performance settings only. They do not change the Stage or Match defaults.

If you need to change timing, scores, markers, overlays, or exports themselves, reopen the source editor and make the change there.

## Common Fixes

| Problem | Fix |
| --- | --- |
| The library looks empty. | Save a stage project or match workspace first, then reopen Performance or click `Update Library`. |
| The stale banner is visible. | Auto-refresh is off. Click `Update Library`, or re-enable `Refresh records when the library opens` in `Settings`. |
| `Open Stage` or `Open Workspace` is disabled or does nothing useful. | The selected record may not have a valid saved editor target anymore. Resave the source project or workspace to refresh the library target. |
| The analytics section is mostly hints. | That is expected with limited history. Add more scored records to unlock the trend and breakdown views. |
| CSV/JSON export does not reflect the latest save. | Refresh the library first, then export again. |
| Tags or notes are missing on another machine. | Restore the relevant library backup or move the updated library record set with the backup manifest. |

## Related Guides

Return to [../USER_GUIDE.md](../USER_GUIDE.md), then pair this pane with [project.md](project.md) for source setup, [metrics.md](metrics.md) for current-run read-only metrics, and [../workflow.md](../workflow.md) for the full import-to-export flow.
