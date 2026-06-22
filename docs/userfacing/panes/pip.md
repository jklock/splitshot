# Compose Pane

The Compose pane controls the active stage composition. It uses the media already paired in the Media pane and is limited to composition of already-attached merge sources. Media intake for new stage files belongs in Media.

## Use This Pane For

- Choosing how the active stage's added media is composed.
- Setting per-source layout, size, opacity, and position.
- Enabling or disabling added media in the render for the active stage.

## Key Controls

| Control | What it does |
| --- | --- |
| `Add Media` | Adds more merge sources to the active stage composition. |
| `Enable added media export` | Includes added media in the rendered output. |
| `Layout` | Sets the overall layout for the active stage. |
| `Default size` | Sets the default inset size for newly added media. |
| `Default Position X` / `Default Position Y` | Set default inset placement for newly added media. |
| Media card toggle | Expands or collapses a source row. |
| `Remove` | Removes that merge source from the active stage. |
| Per-item `Layout` | Sets the layout mode for that specific source. |
| Per-item `Size` | Sets the per-source inset size. |
| Per-item `Opacity` | Sets per-source transparency. |
| Per-item `Position X` / `Position Y` | Sets per-source normalized placement. |

## Workflow

1. Pair media in [media.md](media.md) first.
2. Open Compose on the stage you want to edit.
3. Enable added-media export if the extra media should render.
4. Choose the overall layout.
5. Expand each source card and tune its per-source layout, size, opacity, and position.
6. Open Trim when the active stage still needs sync or trim changes.

## Notes

- Compose edits are stage-local.
- Switching stages changes the entire composition context.
- Default positioning lives here for the active stage composition. Global defaults remain in Settings.
- To add new stage media files, use the Media pane. Compose is for composition of already-attached sources.

## Related Guides

Previous: [media.md](media.md)
Next: [overlay.md](overlay.md)
