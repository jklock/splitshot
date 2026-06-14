# Compose Pane

The Compose pane manages added media. It can place a second angle or image as an inset, side-by-side, or above/below content, then lets each item keep its own size, opacity, position, and layout mode.

<img src="../../screenshots/PiPPane.png" alt="Compose pane with defaults, an expanded media card, per-item opacity, size, placement controls" width="960">

## When To Use This Pane

- Add a second camera angle.
- Add a still image or support graphic.
- Decide whether added media appears in the final export.
- Configure per-item size, opacity, position, and layout.

## Key Controls

| Control | What it does |
| --- | --- |
| `Add Media` | Adds one or more video or image files. |
| `Enable added media export` | Includes added media in the rendered export. |
| `Layout` | Chooses `Side by side`, `Above / below`, or `Inset`. |
| `Default size` | Sets the size for newly added items. |
| `Default Position X` / `Default Position Y` | Set default normalized placement for new items. |
| Media card `>` / `v` | Expands or collapses per-item controls. |
| `Remove` | Deletes that added media item. |
| Per-item `Size` | Sets one item's size. |
| `Opacity` | Sets one item's transparency. |
| Per-item `Position X` / `Position Y` | Set one item's normalized placement. |
| Per-item `Layout` | Controls how this item is placed in the output. |

## How To Use It

1. Click `Add Media`.
2. Choose `Layout`.
3. Turn on `Enable added media export` when the added media should render into the final file.
4. Set defaults before adding several similar items.
5. Expand each media card and adjust item-specific `Size`, `Opacity`, `Position X`, and `Position Y`.
6. In inset layout, drag the rendered added media in the preview for direct placement. The per-item X/Y fields update to match the drag result.
7. Use the [Trim pane](#) to time-shift media or trim dead time.

## Trim and Sync

Trimming and manual sync are managed in the dedicated **Trim** left-rail pane. Open that pane to adjust sync offset per source, nudge timing, run beep-sync analysis, and trim added videos.

## Layout Notes

- Inset layout uses X/Y placement and size as a floating layer.
- `Side by side` and `Above / below` are layout-wide compositions, but the same item list remains available.
- Defaults apply to new items. Existing media cards keep their own saved values.
- Each item keeps its own size, opacity, position, and layout mode.
- Preview dragging is clamped to the live video frame so the inset stays fully visible.
- Defaults are set in [Settings](settings.md), not per-source.

## Common Fixes

| Problem | Fix |
| --- | --- |
| Added media appears in preview but not export. | Turn on `Enable added media export`. |
| Changing defaults did not move an existing card. | Edit the expanded media card. |
| A secondary video is late or early. | Use the Trim pane to adjust its offset. |
| The inset is in the wrong place. | Use inset layout, then adjust X/Y or drag the layer. |

## Related Guides

Previous: [score.md](score.md)
Next: [overlay.md](overlay.md)
