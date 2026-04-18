# Export Pane

The Export pane renders the finished local video. Use it to choose a preset or custom frame settings, pick the codec and bitrate, set the output path, watch the live FFmpeg log, and produce the final file that includes your timing, overlays, review boxes, score summary, and enabled PiP media.

<img src="../../screenshots/ExportPane.png" alt="Export pane showing custom render settings, FFmpeg renderer note, output path, and Export Video or Show Log buttons" width="960">

## When To Use This Pane

- After timing, scoring, overlay, review, and PiP are ready.
- When you want to switch between quick drafts and higher-quality finals.
- When you need a specific size, frame rate, codec, or output container.
- When you want to watch the render log while FFmpeg runs.

## Before You Start

- Recheck the last few shots in the live preview first.
- Make sure the output path is not the same file as the original source video.
- Turn on PiP media export in [pip.md](pip.md) if you want the extra media in the final file.

## Key Controls

| Control | What it does |
| --- | --- |
| `Preset` | Chooses a built-in export profile or `Custom`. |
| Preset description line | Explains the selected preset, or confirms that you are using custom settings. |
| `FFmpeg Renderer` note | Reminds you that SplitShot renders locally on the current machine. |
| `Quality` | Chooses the general quality target. |
| `Aspect ratio` | Chooses `Original`, `16:9`, `9:16`, `1:1`, or `4:5`. When the aspect ratio changes, SplitShot crops the frame to fit that output shape. |
| `Output Width` and `Output Height` | Override the final render size. |
| `Frame rate` | Chooses `Source`, `30 fps`, or `60 fps`. |
| `Video codec` | Chooses `H.264` or `HEVC`. |
| `Video bitrate (Mbps)` | Sets the video bitrate target. |
| `Audio codec` | Uses `AAC` in the current pane. |
| `Audio Sample Rate (Hz)` | Sets the AAC sample rate. |
| `Audio kbps` | Sets the AAC bitrate. |
| `Color` | Uses `Rec.709 SDR` in the current pane. |
| `FFmpeg preset` | Trades speed for compression efficiency. Faster presets render sooner; slower presets spend more time compressing. |
| `2-pass` | Enables two-pass encoding for steadier bitrate allocation at the cost of extra render time. |
| `Output path` | Chooses the destination filename and folder. The file extension selects the container. |
| `Browse` | Opens a native save dialog for the output file. |
| `Export Video` | Starts the local render. |
| `Show Log` | Opens the live export log modal. |

## How To Use It

1. Start with a built-in `Preset` if you want a safe default for common delivery targets.
2. Switch to `Custom` when you need exact dimensions, codecs, or bitrate values.
3. Pick `Aspect ratio`, then set `Output Width` and `Output Height` if the preset values are not what you need.
4. Choose `H.264` when you want the broadest compatibility. Choose `HEVC` when you want smaller files and your playback target supports it.
5. Keep `AAC`, a sensible sample rate, and an appropriate audio bitrate for the delivery target.
6. Use a faster `FFmpeg preset` for quick drafts. Use a slower one when final compression efficiency matters more than render time.
7. Turn on `2-pass` only when you are willing to spend more time rendering for more even bitrate control.
8. Set the `Output path` to a new filename with one of the supported container extensions: `.mp4`, `.m4v`, `.mov`, or `.mkv`.
9. Click `Export Video`, then use `Show Log` if you want to follow the render in real time.

## What The Export Includes

- The current primary video timing.
- The live overlay state from [overlay.md](overlay.md).
- The final score summary and score-token colors from [score.md](score.md).
- Enabled review text boxes from [review.md](review.md).
- Enabled PiP media from [pip.md](pip.md).

## How It Affects The Rest Of SplitShot

- Export snapshots the current project state at the moment you click `Export Video`.
- The log modal gives you the last local render output without leaving the pane.
- The output path is saved with the project so you can rerender to the same target later if you want.

## Common Mistakes And Fixes

| Problem | Fix |
| --- | --- |
| The render failed immediately. | Check the `Output path`, container extension, and whether the destination folder is writable. |
| The output file did not contain PiP media. | Turn on `Enable added media export` in [pip.md](pip.md). |
| The render log says FFmpeg is missing. | Install `ffmpeg` and `ffprobe`, then relaunch SplitShot. |
| The video would not export over the source file. | Choose a different output filename. SplitShot should write a new file, not overwrite the source in place. |
| The output is larger than expected. | Lower the bitrate, use a slower `FFmpeg preset`, or choose a different preset or codec. |

## Related Guides

Previous: [review.md](review.md)
Next: [metrics.md](metrics.md)

**Last updated:** 2026-04-18
**Referenced files last updated:** 2026-04-18