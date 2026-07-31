# In / Out Pane

The In / Out pane owns optional match-opening and match-closing videos. In the packaged app, selection uses the native video picker; browser mode uses the local path picker. A successful selection is copied into the project `IntroOutro/` folder, shown in the main preview immediately, persisted with the project, and made available to Queue. In and Out keep independent text overlay configurations.

Use the Intro and Outro buttons to switch which clip is shown in the main preview. `Add Text Box` creates custom copy. `Add Match Results` creates an automatically populated box whose selectable fields include the combined match result, raw time, stage and shot totals, points, penalties, competitor, division, class, and overall place.

These boxes use the same overlay data model and frame renderer as stage Review boxes, so color, opacity, typography, size, and placement are burned into the combined output as previewed. Match values are resolved again when Queue processes the file so late scoring changes are included.

Queue has separate `Include In` and `Include Out` choices. A selected file is not part of individual stage outputs. In `Process as One File`, enabled clips are placed outside the stage sequence and receive the configured fade-in and fade-out.
