# Troubleshooting

This page covers common SplitShot problems and the pane that owns the fix.

## No Video Selected

- Open [panes/project.md](panes/project.md).
- Use `Select Primary Video`, or paste an absolute path into `Primary Video` and press Enter.
- Wait for analysis to finish before judging Splits, Score, Metrics, or Export.

## Large Video Import Is Slow

- Prefer the direct path field in Project for very large local files.
- Paste the full path into `Primary Video`.
- Press Enter.

## Missing Or Extra Shots

- Open [panes/shotml.md](panes/shotml.md) before detailed manual edits.
- Lower `Detection threshold` for missed quiet shots.
- Raise `Detection threshold` for extra noise or echoes.
- Click `Re-run ShotML`.
- Finish remaining marker fixes in [panes/splits.md](panes/splits.md) with nudges, drag, `Add Shot`, or `Delete Selected Shot`.

## Beep Or All Shot Times Are Shifted

- Tune Beep Detection in [panes/shotml.md](panes/shotml.md).
- Rerun ShotML.
- Confirm the orange beep marker and first-shot draw time in Splits.

## PractiScore Does Not Match The Expected Stage

- Reopen [panes/project.md](panes/project.md).
- Confirm `Match type`, `Stage #`, `Competitor name`, and `Place`.
- If the wrong file was loaded, click `Select PractiScore File` again.

## Score Or Marker Text Looks Wrong

- Open [panes/score.md](panes/score.md).
- Confirm `Enable scoring` and `Preset`.
- Expand the relevant shot card and check score plus penalties.
- Shot-linked marker text follows this score state.

## Overlay Or Review Boxes Are Missing

- Check [panes/overlay.md](panes/overlay.md) for overall overlay visibility and style.
- Check [panes/review.md](panes/review.md) for `Show timer badge`, `Show draw badge`, `Show split badges`, `Show scoring summary`, and each text-box enable checkbox.
- If a summary box is empty, import PractiScore in Project.
- If X/Y fields are disabled, use `Custom` placement and turn off shot-stack locking for that box or badge.

## Markers Are Missing Or At The Wrong Time

- Open [panes/popup.md](panes/popup.md).
- Confirm the marker is `On`.
- Check `Start mode`, `Shot`, `Start (seconds)`, and `Duration (seconds)`.
- For moving callouts, enable `Follow motion path` and set the path points.
- For image markers, confirm the image path still resolves or save the project so the image is bundled into the project folder.

## PiP Media Is Missing From Export

- Open [panes/pip.md](panes/pip.md).
- Confirm the media item still exists.
- Turn on `Enable added media export`.
- Recheck layout, opacity, size, position, and sync.

## Export Fails

- Open [panes/export.md](panes/export.md).
- Confirm the output path is writable and does not point to the source video.
- Use `.mp4`, `.m4v`, `.mov`, or `.mkv`.
- Install `ffmpeg` and `ffprobe` if the log reports missing tools.
- Use `Show Log` for the exact local FFmpeg error.

## Metrics Looks Wrong

Metrics is read-only. Fix the source pane:

- Project for imported PractiScore context.
- ShotML for detector confidence and automatic split context.
- Splits for timing.
- Score for score and penalties.

## SplitShot Does Not Open In Your Browser

- Some Windows browser configurations can prevent automatic localhost launches.
- Run `uv run splitshot --no-open` instead.
- Open `http://127.0.0.1:8765/` manually in a browser such as Edge or Firefox.
- If your default browser is a privacy-focused or hardened browser, try a standard browser for the first launch.

## Project Folder Confusion

- `Choose Project` opens an existing bundle or chooses a bundle location.
- `New Project` clears the current session.
- `Delete Project` removes the saved bundle from disk.

## If You Still Need Help

- Start from [USER_GUIDE.md](USER_GUIDE.md).
- Use the pane guide for the active rail tool.
- Review [../project/LIMITATIONS.md](../project/LIMITATIONS.md) if the issue may be a current product limitation.

**Last updated:** 2026-04-23
**Referenced files last updated:** 2026-04-23
