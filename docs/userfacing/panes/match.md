# Match Pane

The Match pane is the multi-stage workspace for building one saved match bundle. It keeps stage membership, shared defaults, per-stage overrides, recap rendering, stage-composite prep, batch export, and Match-only settings inside the same shared shell used by Stage and Performance.

In the current shell, the stage tiles stay in the main area, each saved stage can show a live preview tile when SplitShot can resolve its source project, the selected stage stays visible in the lower pane, and the right-hand inspector swaps between Match workflow controls such as `Defaults`, `Overrides`, `Recap`, and `Match Settings`.

![Match empty state with new/open/save workspace actions](../../../artifacts/match-proof-20260524/screenshots/match-empty.png)

![Match loaded state with saved stage cards and the shared shell rail](../../../artifacts/match-proof-20260524/screenshots/match-loaded.png)

![Match recap section with selected stages and render status](../../../artifacts/match-proof-20260524/screenshots/match-recap.png)

![Match export section with queue controls and batch results](../../../artifacts/match-proof-20260524/screenshots/match-export.png)

## When To Use This Pane

- Build or reopen a saved multi-stage workspace.
- Add, remove, and reorder the stage list you want in one match bundle.
- Apply shared defaults across every stage before using per-stage overrides.
- Open one stage back in `Stage Video Edit`, then return to the same Match context.
- Render a `Match Recap` or queue a `Batch Export` across saved stages.
- Manage Match-only settings without changing the Stage or Performance defaults.

## Key Controls

| Control | What it does |
| --- | --- |
| `New Workspace` | Starts a fresh Match workspace in the current shell. |
| `Open Workspace` | Loads an existing saved Match workspace from disk. |
| `Save Workspace` | Writes the current Match workspace folder and metadata to disk. |
| `Stages` | Keeps the stage list in the main area and refreshes the lower pane with truthful information for the selected stage. |
| Preview tile video | Shows live stage media inside a Match tile when the saved stage project can be resolved locally. |
| `Defaults` | Uses the right-hand inspector to set shared Match defaults such as `Aspect Ratio / Framing`, `Overlay Data`, `Opening Title`, and `Your Logo`. |
| `Overrides` | Uses the right-hand inspector to apply stage-specific overrides for the selected stage without changing the shared defaults. |
| `Recap` | Uses the right-hand inspector to build a `Match Recap` from selected workspace stages, including transition (`Cut`, `Fade`, `Dissolve`) and result-card placement (`None`, `At End`, `Per Stage`). |
| `Composite` | Switches the lower pane into Stage Composite clip work for the selected stage while keeping the selected-stage summary pinned above it. |
| `Export` | Switches the lower pane into the Batch Export queue for the workspace while keeping the selected-stage summary pinned above it. |
| `Match Settings` | Stores Match-only preferences such as score badges in the stage list and whether stage selection is remembered. |
| `Add Stage` | Adds a new stage card to the current workspace. |
| `Apply to All` | Copies Stage 1 shared defaults and reusable output-profile settings to sibling stages when the setup-once banner is shown. |
| Stage-card `Open` | Opens that stage in `Stage Video Edit`. |
| Stage-card `Reset` | Removes stage-specific overrides so the stage returns to inherited defaults. |
| `Select All` / `Select None` | Quickly toggle the Batch Export queue. |
| `Export Selected` | Runs the queued batch export for the checked stages and selected recipe. |

## How To Use It

1. Open `Match Video Edit` from the landing surface.
2. Use `New Workspace` for a fresh match or `Open Workspace` to reload a saved one.
3. Add stages in `Stages` until the match list is complete, then click a stage card so the lower pane stays focused on that stage while you move through the rest of the Match workflow. When a stage has a resolvable saved project, its tile can show a live preview video instead of a static placeholder.
4. Configure Stage 1, then use `Apply to All` when shared defaults and reusable output-profile behavior should flow to the rest of the match.
5. Open `Defaults` to set the shared cross-stage baseline.
6. Open `Overrides` after selecting a stage card when one stage needs different framing or overlay-data settings.
7. Use the stage-card `Open` action when deeper timing, scoring, Compose, Review, or Export work must happen in the Stage editor, then click `Return to Match` in the shell header to come back.
8. Open `Recap` when you want one stitched highlight reel from selected stages; the recap controls live in the right-hand inspector and let you choose transitions plus per-stage or end-of-recap result cards.
9. Open `Composite` when a stage needs clip-level angle prep before export; the lower pane keeps the selected-stage truth pinned above the composite clip work so you can reorder clips, edit sync/audio state, and apply or clear cut overrides without losing context.
10. Open `Export` to batch render `Stage Output` or `Stage Composite` across the workspace; the queue and controls stay in the lower pane beneath the pinned selected-stage summary.
11. Open `Match Settings` for Match-only UI preferences such as score-badge visibility and selection memory.
12. Save the workspace again before closing the browser surface.

## What Saves Here

The Match workspace owns the multi-stage bundle state:

- `New Workspace`, `Open Workspace`, and `Save Workspace` manage the saved workspace folder.
- Shared defaults and stage overrides are saved with that workspace.
- Stage membership lives in the workspace, not in the Stage editor alone.
- When SplitShot can identify the owning Match workspace for a saved or reopened stage project, it now auto-attaches that stage back into Match membership so the workspace stays in sync.
- `Match Settings` are local browser settings only. They do not change the Stage or Performance defaults.
- `Match Recap` and `Batch Export` render output files, but they do not replace the source Stage projects.

## Common Fixes

| Problem | Fix |
| --- | --- |
| The match opens empty. | Use `Open Workspace` on the correct saved workspace folder, or add stages again and `Save Workspace`. |
| `Overrides` looks blank. | Select a stage card first, then reopen `Overrides`. |
| `Apply to All` is missing. | The setup-once banner appears only after Stage 1 is configured and at least one sibling stage can inherit from it. |
| `Return to Match` is missing after opening a stage. | Open the stage from a Match stage card instead of reopening the project independently. |
| Batch export has nothing to do. | Add stages to the workspace first, then make sure the stages you want are checked in the queue. |
| A Match setting changed the Stage editor unexpectedly. | It should not. Reopen `Match Settings` and verify the change was made there, not in Stage `Settings`. |
| The recap or batch status looks stale. | Save the workspace, then rerun `Match Recap` or `Export Selected`. Errors are reported in-line in the current section. |

## Related Guides

Return to [../USER_GUIDE.md](../USER_GUIDE.md), then pair this pane with [project.md](project.md) for source setup, [export.md](export.md) for Stage-owned output behavior, and [../workflow.md](../workflow.md) for the full Stage-to-Match flow.
