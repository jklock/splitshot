# User Guide

SplitShot is a local-first stage review tool. The browser interface is the default way to use it, and it walks through the whole flow from source video to export.

## Normal Workflow

1. Launch the app with `uv run splitshot`.
2. Load the primary stage video from the Project page.
3. Let SplitShot detect the timer beep and shot events.
4. Use Splits to refine shot timing and add timing events.
5. Use Score, Overlay, and Review to set scoring and on-video presentation.
6. Add merge media if you have a second angle or extra images.
7. Configure Export and render the final file.
8. Save the project as a `.ssproj` bundle when you want to return later.

## Screen Layout

The browser screen is split into four major parts:

- The left rail contains the page buttons.
- The top status strip shows draw time, raw time, shot count, and average split.
- The center review area shows playback, the waveform editor, and split cards.
- The right inspector changes with the selected page.

The video stage, waveform panel, and inspector each have a lock button and resize handles. Unlock a section before resizing it.

## Left Rail Pages

| Page | What it controls |
| --- | --- |
| Project | Project metadata, primary video, bundle path, save/open/new/delete |
| Splits | Detection threshold, shot timing, timing events, shot deletion, manual nudging |
| Score | Scoring preset, score letters, penalties, and selected-shot scoring |
| Overlay | Badge style, placement, custom review box, and score colors |
| Merge | Secondary media, merge layout, sync offset, and dual-angle swap |
| Review | Preview-only overlay visibility and custom review box controls |
| Export | Output framing, codecs, bitrate, audio, color, and final render |

## Project Page

| Control | What it does |
| --- | --- |
| Project name | Changes the saved project name |
| Project description | Stores notes with the project bundle |
| Primary Video | Shows the current primary video path |
| Upload Primary Video | Opens a local file picker for the source stage video |
| Project bundle path | Sets the `.ssproj` bundle directory |
| Browse | Chooses the project bundle path with a native dialog |
| Save Project | Saves the current project bundle |
| Open Project | Loads an existing `.ssproj` bundle |
| New Project | Clears the current project and starts fresh |
| Delete Project | Deletes the current saved bundle directory |

Loading a new primary video immediately starts automatic analysis and resets media-bound state from the previous project.

## Splits Page

| Control | What it does |
| --- | --- |
| Expand | Opens the full timing workbench |
| Detection threshold | Adjusts shot detection sensitivity and re-runs local analysis |
| Selected Shot panel | Shows the currently selected shot |
| -10 ms / -1 ms / +1 ms / +10 ms | Nudges the selected shot by the chosen amount |
| Delete Selected Shot | Removes the selected shot |
| Timing table | Lists detected shots, split times, scores, confidence, and source |

When the workbench is expanded, you also get these controls:

| Control | What it does |
| --- | --- |
| Collapse | Hides the expanded timing workbench |
| Event | Chooses the timing event type: Reload, Malfunction, or Note |
| After shot | Anchors the event after a specific shot or after any shot |
| Before shot | Anchors the event before a specific shot or before any shot |
| Add Event | Adds the timing event to the project |
| Lock / Unlock row | Makes a shot row editable or read-only |

## Score Page

| Control | What it does |
| --- | --- |
| Enable scoring | Turns scoring calculations on or off |
| Preset | Chooses the active ruleset |
| Score for selected shot | Sets the score letter for the selected shot |
| Score color | Changes the color for the selected shot’s score badge |
| Penalty points | Adds manual penalty points to the scoring summary |
| Penalty grid | Shows preset-specific penalty counters and score penalties |
| Scoring shot list | Shows the shots that can be scored from this page |

The available score letters and penalty fields change with the selected preset.

## Overlay Page

| Control | What it does |
| --- | --- |
| Badge size | Changes the on-video badge size |
| Badge style | Chooses square, bubble, or rounded bubble styling |
| Spacing | Controls the space inside badges |
| Margin | Controls the spacing between badges and frame edges |
| Shots shown | Limits how many split badges stay visible |
| Quadrant | Chooses where the badges begin |
| Direction | Chooses the badge flow direction |
| Custom X / Custom Y | Positions the badges when Custom quadrant is selected |
| Bubble width / Bubble height | Forces badge dimensions when you want a fixed badge size |
| Font | Chooses the badge font family |
| Font size | Sets the overlay font size |
| Bold / Italic | Toggles the font style |
| Custom Box Style | Controls the custom review box colors and opacity |
| Score Colors | Controls the colors used for score letters |

## Merge Page

| Control | What it does |
| --- | --- |
| Add Merge Media | Adds extra merge media files, including videos and still images |
| Merge media list | Shows the items that will be part of the merge export |
| Enable merge export | Turns merge output on or off |
| Layout | Chooses side by side, above/below, or picture in picture |
| PiP size | Sets the size of the picture-in-picture inset |
| PiP X / PiP Y | Sets the inset position when PiP is selected |
| -10 ms / -1 ms / +1 ms / +10 ms | Nudges the merge sync offset |
| Swap Primary and First Merge | Swaps the primary and secondary video roles |

If you add more than one merge item, the first item stays in the secondary preview and the extra items export as a grid.

## Review Page

| Control | What it does |
| --- | --- |
| Show timer badge | Shows or hides the timer badge on the preview |
| Show draw badge | Shows or hides the draw badge |
| Show split badges | Shows or hides the split badges |
| Show scoring summary | Shows or hides the final score or hit factor badge |
| Custom review box | Turns the custom on-video review box on or off |
| Custom box text | Sets the text shown in the custom box |
| Box quadrant | Chooses the box anchor quadrant |
| Box X / Box Y | Sets the box position when Custom is used |
| Box width / Box height | Forces the custom box dimensions |
| Background / Text / Opacity | Styles the custom box |

## Export Page

| Control | What it does |
| --- | --- |
| Preset | Chooses an export preset |
| Quality | Chooses high, medium, or low quality |
| Aspect ratio | Chooses original, 16:9, 9:16, 1:1, or 4:5 framing |
| Crop center X / Y | Moves the crop window within the source frame |
| Width / Height | Forces an output size |
| Frame rate | Chooses source, 30 fps, or 60 fps |
| Video codec | Chooses H.264 or HEVC |
| Video bitrate Mbps | Sets the video bitrate |
| Audio codec | Chooses the audio codec |
| Audio kHz | Sets the audio sample rate |
| Audio kbps | Sets the audio bitrate |
| Color | Chooses the export color space |
| FFmpeg preset | Chooses the encoder speed/quality balance |
| 2-pass | Enables two-pass encoding |
| Output path | Sets the destination file path |
| Browse | Opens a native save dialog for the output path |
| Export Video | Starts the local export |
| Export log | Shows the last FFmpeg command and output |

The output file extension controls the container. Use `.mp4`, `.m4v`, `.mov`, or `.mkv`.

## Waveform and Shot Editing

| Action | Result |
| --- | --- |
| Click a shot marker | Selects the shot |
| Drag a shot marker | Moves the shot to a new time |
| Click empty waveform space in Add Shot mode | Adds a manual shot |
| Arrow Left / Arrow Right | Nudges the selected shot by 1 ms |
| Shift + Arrow Left / Arrow Right | Nudges the selected shot by 10 ms |
| Delete or Backspace | Deletes the selected shot |
| Zoom - / Zoom + | Changes the waveform time scale |
| Amp - / Amp + | Changes the selected shot emphasis in the waveform view |
| Reset | Returns the waveform view to its default scale |

The waveform editor also switches between Select and Add Shot mode. Select mode is for moving existing shots; Add Shot mode is for placing new manual detections.

## Layout Locks and Resize Handles

| Control | What it does |
| --- | --- |
| Unlock video layout | Allows the video stage to be resized |
| Unlock waveform layout | Allows the waveform panel to be resized |
| Unlock inspector layout | Allows the inspector to be resized |
| Resize left rail | Changes the rail width |
| Resize waveform | Changes waveform panel height |
| Resize inspector | Changes the inspector width |

## Saving and Reopening

- Use Save Project to keep the current state in a `.ssproj` bundle.
- Use Open Project to reopen a previous bundle.
- Use New Project to clear the current session and start over.
- Use Delete Project only when you want to remove the saved bundle from disk.

## Desktop App

SplitShot also includes a PySide6 desktop window. It uses the same project model and the same analysis and export pipeline, but the browser interface is the main documented workflow.

**Last updated:** 2026-04-13
**Referenced files last updated:** n/a
