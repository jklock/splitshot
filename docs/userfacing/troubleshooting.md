# Troubleshooting

This page covers the most common user-facing problems and where to fix them.

## Launch And Setup

| Problem | Fix |
| --- | --- |
| `splitshot` command not found | Confirm `uv sync` completed and you are running from the project root. Use `uv run splitshot`. |
| Browser does not open automatically | Retry with `uv run splitshot --no-open` and open the URL shown in the terminal manually. |
| FFmpeg or FFprobe not found | Source builds require `ffmpeg` and `ffprobe` on `PATH`. Packaged app builds should carry their own copies. Run `uv run splitshot --check` to validate. |
| Port 8765 already in use | Stop the other process, or SplitShot will auto-select the next available port when running in headless mode. |
| Qt/PySide6 import error | Install PySide6 via `uv sync --extra dev`. The export pipeline and PractiScore session require Qt. |
| Headless mode fails to bind | Headless mode will auto-select a free port. Check firewall or use `--host 0.0.0.0` cautiously. |

## Importing Media

| Problem | Fix |
| --- | --- |
| Large file (over 8 GiB) rejected by browser picker | Paste the direct local path into the `Primary Video` input and press Enter. |
| Video imported but nothing plays | Check the format is supported by your browser (MP4/H.264 is safest). Run `uv run splitshot --check` to validate FFmpeg. |
| Secondary media sync is wrong | Use the sync nudge buttons in the PiP pane for that media item. |
| Still image not appearing in PiP | Confirm the file is a common image format (PNG, JPG). Still images are detected by `QImage` probe. |

## Analysis And Detection

| Problem | Fix |
| --- | --- |
| No shots detected | Lower `Detection threshold` in the ShotML pane, then click `Re-run ShotML`. |
| Too many false detections | Raise `Detection threshold` and rerun. Enable false-positive suppression in ShotML. |
| Beep marker is in the wrong place | Tune beep detection settings in the ShotML pane, then rerun. |
| Shot markers are consistently early or late | Adjust `Onset fraction` in ShotML `Shot Refinement`. Lower = earlier, higher = later. |
| ShotML proposals list is empty | Rerun ShotML first, then click `Generate Proposals`. |
| Analysis fails on import | Check the video has an audio track. ShotML requires audio for beep and shot detection. Run `ffprobe <file>` to inspect streams. |

## Scoring And PractiScore

| Problem | Fix |
| --- | --- |
| PractiScore dashboard does not open | Click `Open PractiScore Dashboard` again. If blocked, open `https://practiscore.com/dashboard/home` manually. |
| Imported PractiScore file shows wrong stage | Recheck `Match type`, `Stage #`, `Competitor name`, and `Place` in the Project pane. |
| Score labels look wrong | Check the `Preset` in the Score pane. Different presets use different score letters. |
| Restored shot does not reappear in Score | Confirm the shot exists in the Splits pane. Score rows follow the shot list. |

## Overlay And Export

| Problem | Fix |
| --- | --- |
| No badges appear in preview | Turn on `Show overlay` in the Overlay pane and confirm Review visibility toggles are on. |
| A badge is hidden but Overlay is configured | Recheck the Review pane badge visibility toggles. |
| PiP missing from export | Turn on `Enable added media export` in the PiP pane. |
| Review boxes missing from export | Confirm the box enable checkbox is on in the Review pane. |
| Export fails immediately | Check output path, extension, and folder permissions. Run `uv run splitshot --check`. |
| Export log shows FFmpeg errors | Open the Export Log modal in the Export pane. Common fixes: lower bitrate, change codec, or verify source file. |

## Project Persistence

| Problem | Fix |
| --- | --- |
| Project does not reopen correctly | Check that the `.ssproj` bundle directory is intact and contains `project.json`. |
| Media missing after reopening bundle | Browser-session media is copied into the bundle. If the original file moved, re-import from the new location. |
| Settings lost after update | App settings are stored in `~/.splitshot/settings.json`. If corrupt, delete the file and restart. |

## General

| Problem | Fix |
| --- | --- |
| Activity log is too noisy | Launch with `--log-level off` (default). Use `--log-level warning` or `--log-level error` for quieter terminal output. |
| Browser page shows error on reload | The server session resets. Re-import media and reconfigure overlays. Save the project first to preserve work. |
| Color picker does not apply | Click outside the modal or press Enter to commit the hex/HSL value. |
| Export log modal stuck | Click outside the modal or press the `Close` button to dismiss. |
