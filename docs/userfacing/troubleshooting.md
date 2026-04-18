# Troubleshooting

This page covers the most common SplitShot problems you can solve from the user-facing workflow.

## No Video Selected

If the status bar still says `No Video Selected`, SplitShot does not have a usable primary video yet.

- Go back to [panes/project.md](panes/project.md).
- Use `Select Primary Video`, or paste a full local path into `Primary Video` and press Enter.
- Wait for the status message to confirm that local analysis started.

## Large Video Import Guidance

Very large files are usually easier to open by direct path than by browser upload.

- Paste the full absolute path into the `Primary Video` field in the Project pane.
- Press Enter to import it directly from disk.
- Use the file picker for normal-sized files when convenience matters more than avoiding browser upload overhead.

## Browser Preview Audio Is Missing

Some browsers are stricter about unusual source audio formats.

- Try Chromium first if you are currently on a different browser.
- Confirm the video itself still plays outside SplitShot.
- If the source video uses an uncommon audio combination, re-encode the source audio to a more browser-friendly format before the session.

## Missing Or Extra Shots

Shot detection problems nearly always start in [panes/splits.md](panes/splits.md).

- Lower `Detection threshold` if quiet shots were missed.
- Raise `Detection threshold` if background noise or echoes became shots.
- Use waveform `Select` mode to drag a shot marker into place.
- Use `Add Shot` for a missed shot, or `Delete Selected Shot` for a false detection.

## PractiScore Import Does Not Match The Expected Competitor Or Stage

The staged file may have multiple stages or multiple competitors.

- Recheck `Match type`, `Stage #`, `Competitor name`, and `Place` in [panes/project.md](panes/project.md).
- If the file is correct but the wrong stage is still selected, choose the correct stage first and then recheck the competitor and place fields.
- If you loaded the wrong source file, use `Select PractiScore File` again and restage the right one.

## Overlay Looks Right In Preview But Not In Export

Preview and export use the same settings, but the final render is still a separate local render pass.

- Confirm the settings in [panes/overlay.md](panes/overlay.md) and [panes/review.md](panes/review.md) are still enabled.
- Scrub near the final shot and confirm the badges and text boxes appear when expected.
- If a review box is locked to the overlay stack, unlock it before expecting custom X and Y placement.
- If a PractiScore summary box is empty, recheck the imported stage in the Project pane.

## PiP Media Is Not Included In Export

PiP media must be both added and enabled for export.

- Open [panes/pip.md](panes/pip.md).
- Confirm the media item still exists in the card list.
- Turn on `Enable added media export`.
- Recheck the chosen `Layout` and the per-item size and position values.

## Export Fails Because FFmpeg Or ffprobe Is Missing

SplitShot renders locally, so FFmpeg tools must be available on the machine.

- Install `ffmpeg` and `ffprobe`.
- Relaunch SplitShot after installation.
- Run `uv run splitshot --check` from the repository root if you want a quick toolchain check before trying the export again.

## Output Path Or Container Problems

The output file extension decides the container.

- Use `.mp4`, `.m4v`, `.mov`, or `.mkv`.
- Do not export over the original source file.
- Choose a writable destination folder.
- If the export button opens a log with an immediate path error, change the destination and try again.

## Project Folder Confusion

The Project pane uses a chosen project folder as the saved bundle location.

- Use `Choose Project` to open an existing project folder or create a new one for the current session.
- Keep using the same folder if you want SplitShot to preserve the session state across launches.
- Use `New Project` only when you want to clear the current project and start fresh.
- Use `Delete Project` only when you want to remove the saved bundle from disk.

## If You Still Need Help

- Recheck the relevant pane guide from [USER_GUIDE.md](USER_GUIDE.md).
- Review [panes/export.md](panes/export.md) for export-specific issues.
- Review [../project/LIMITATIONS.md](../project/LIMITATIONS.md) if you suspect the problem is a current product limitation rather than a workflow mistake.

**Last updated:** 2026-04-18
**Referenced files last updated:** 2026-04-18