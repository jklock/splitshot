<!-- markdownlint-disable MD012 -->

# Compose Pane

The Compose pane manages added media. It can place a second angle or image as picture-in-picture, side-by-side, above/below content, full-screen portrait focus, or the paired HUD layouts, then lets each item keep its own angle role, layer size, opacity, position, and sync offset.

<!-- markdownlint-disable MD033 -->

<img src="../../screenshots/PiPPane.png" alt="Compose pane with composition defaults and expanded media cards for per-item source roles, opacity, size, placement, and sync controls" width="960">

<!-- markdownlint-enable MD033 -->

## When To Use This Pane

- Add a second camera angle.
- Add a still image or support graphic.
- Sync secondary media against the primary run.
- Decide whether added media appears in the final export.
- Tag each added source as a follow angle, static reference, or detail/graphic item.

## Key Controls

| Control | What it does |
| --- | --- |
| `Add Media` | Adds one or more video or image files. |
| `Enable added media export` | Includes added media in the rendered export. |
| `Layout` | Chooses `Side by side`, `Above / below`, `Picture in picture`, `Full-screen portrait`, `Dual center HUD`, or `Dual top HUD`. |
| `Default layer size` | Sets the floating-layer size for newly added media. |
| `Default Layer X` / `Default Layer Y` | Set default normalized placement for new added-media layers. |
| Media card `>` / `v` | Expands or collapses per-item controls. |
| `Remove` | Deletes that added media item. |
| Per-item `Angle role` | Tags that item as `Follow`, `Static`, or `Detail` so secondary sources stay organized in the editing flow. |
| Per-item `Layer size` | Sets one item's floating-layer size. |
| `Layer opacity` | Sets one item's transparency. |
| Per-item `Layer X` / `Layer Y` | Set one item's normalized placement. |
| `Sync` and nudge buttons | Move that item's sync offset by milliseconds. |

## How To Use It

1. Click `Add Media`.
2. Choose `Layout`.
3. Turn on `Enable added media export` when the added media should render into the final file.
4. Set defaults before adding several similar items.
5. Expand each media card and adjust item-specific `Angle role`, `Layer size`, `Layer opacity`, `Layer X`, and `Layer Y`.
6. Use the sync nudge buttons until the secondary motion lines up with the primary video.
7. In `Picture in picture` or `Full-screen portrait` layout, drag the rendered inset in the preview for direct placement. The per-item X/Y fields update to match the drag result.

## Layout Notes

- `Picture in picture` and `Full-screen portrait` use X/Y placement and size as a floating layer.
- `Side by side`, `Above / below`, `Dual center HUD`, and `Dual top HUD` are layout-wide compositions, but the same item list and sync controls remain available.
- Defaults apply to new items. Existing media cards keep their own saved values.
- Each item keeps its own angle role, size, opacity, position, and sync.
- Preview dragging is clamped to the live video frame so the inset stays fully visible.
- Source roles live inside each media card instead of behind a separate helper launcher.
- The current composition model uses one stage-wide layout at a time. Nested combinations such as floating a layer over a side-by-side base are future work.

## Common Fixes

| Problem | Fix |
| --- | --- |
| Added media appears in preview but not export. | Turn on `Enable added media export`. |
| Changing defaults did not move an existing card. | Edit the expanded media card. |
| It is hard to tell which added source is for what. | Expand that card and set its `Angle role` to `Follow`, `Static`, or `Detail`. |
| A secondary video is late or early. | Use that card's sync nudge buttons. |
| The inset is in the wrong place. | Use `Picture in picture` or `Full-screen portrait`, then adjust X/Y or drag the inset. |
| A still image shows sync controls. | That is normal; sync matters mainly for video, while placement and opacity still matter for images. |

## Related Guides

Previous: [score.md](score.md)
Next: [overlay.md](overlay.md) <!-- pip-pane-guide-eof -->

