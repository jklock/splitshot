# PiP Pane

The PiP pane manages added media. It can place a second angle or image as picture-in-picture, side-by-side, or above/below content, then lets each item keep its own size, opacity, position, and sync offset.

<img src="../../screenshots/PiPPane.png" alt="PiP pane with picture-in-picture defaults, an expanded media card, per-item opacity, size, placement, and sync controls" width="960">

## When To Use This Pane

- Add a second camera angle.
- Add a still image or support graphic.
- Sync secondary media against the primary run.
- Decide whether added media appears in the final export.

## Key Controls

| Control | What it does |
| --- | --- |
| `Add PiP Media` | Adds one or more video or image files. |
| `Enable added media export` | Includes added media in the rendered export. |
| `Layout` | Chooses `Side by side`, `Above / below`, or `Picture in picture`. |
| `Default PiP size` | Sets the size for newly added PiP items. |
| `Default PiP X` / `Default PiP Y` | Set default normalized placement for new PiP items. |
| Media card chevron | Expands or collapses per-item controls. |
| `Remove` | Deletes that added media item. |
| Per-item `PiP size` | Sets one item's size. |
| `PiP opacity` | Sets one item's transparency. |
| Per-item `PiP X` / `PiP Y` | Set one item's normalized placement. |
| `Sync` and nudge buttons | Move that item's sync offset by milliseconds. |

## How To Use It

1. Click `Add PiP Media`.
2. Choose `Layout`.
3. Turn on `Enable added media export` when the added media should render into the final file.
4. Set defaults before adding several similar items.
5. Expand each media card and adjust item-specific `PiP size`, `PiP opacity`, `PiP X`, and `PiP Y`.
6. Use the sync nudge buttons until the secondary motion lines up with the primary video.
7. In `Picture in picture` layout, drag the rendered inset in the preview for direct placement.

## Layout Notes

- `Picture in picture` uses X/Y placement and size as a floating inset.
- `Side by side` and `Above / below` are layout-wide compositions, but the same item list and sync controls remain available.
- Defaults apply to new items. Existing media cards keep their own saved values.
- Each item keeps its own size, opacity, position, and sync.

## Common Fixes

| Problem | Fix |
| --- | --- |
| Added media appears in preview but not export. | Turn on `Enable added media export`. |
| Changing defaults did not move an existing card. | Edit the expanded media card. |
| A secondary video is late or early. | Use that card's sync nudge buttons. |
| The inset is in the wrong place. | Use `Picture in picture`, then adjust X/Y or drag the inset. |
| A still image shows sync controls. | That is normal; sync matters mainly for video, while placement and opacity still matter for images. |

## Related Guides

Previous: [score.md](score.md)
Next: [overlay.md](overlay.md)

**Last updated:** 2026-04-22
**Referenced files last updated:** 2026-04-22
