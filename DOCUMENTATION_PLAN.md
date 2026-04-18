# SplitShot User-Facing Documentation Plan

Date: 2026-04-18

## Goal

Create first-class user-facing documentation for SplitShot that explains the application, not the repository internals. The finished documentation should let a new user install SplitShot, understand the browser app workflow, learn every left-rail pane, and find the right guide from the root README.

## Current Observations

- The active app panes are Project, Score, Splits, PiP, Overlay, Review, Export, and Metrics.
- `docs/userfacing/` exists and is currently empty.
- `docs/userfacing/USER_GUIDE.md` should be the root-level user guide for the app's user-facing documentation.
- The pane-specific guides should live underneath that root user guide in a child pane-guide folder.
- `docs/screenshots/` contains the pane screenshots to use in the user-facing pages.
- Each screenshot is 3134 x 1956, so Markdown pages should size them with HTML `<img>` tags instead of allowing full-width raw images.
- The current root README is already trimmed down, but it still needs a product-first rewrite and it references `docs/assets/browser-shell.png`, which is not present.
- `docs/USER_GUIDE.md` already contains useful control inventories that can be reused, but the final user docs should move the active root guide to `docs/userfacing/USER_GUIDE.md` and split exhaustive pane details into dedicated child guides.
- `docs/LEFT_PANE_AUDIT.md` is a useful source for the pane inventory and cross-pane behavior, but the new pages should avoid developer-facing implementation details.

## Deliverables

1. Rewrite [README.md](README.md) as the main user-facing entry point.
2. Create the root-level user-facing guide at `docs/userfacing/USER_GUIDE.md`.
3. Create one exhaustive guide for each app pane under `docs/userfacing/panes/`.
4. Use the matching screenshots from `docs/screenshots/` in each pane guide.
5. Update `docs/README.md` so user docs are easy to find before technical docs.
6. Update the legacy `docs/USER_GUIDE.md` to point users to `docs/userfacing/USER_GUIDE.md`, or keep it as a short compatibility landing page.
7. Verify all links and image paths from the repository root, from `docs/userfacing/USER_GUIDE.md`, and from `docs/userfacing/panes/`.

## Proposed User-Facing File Layout

```text
docs/userfacing/
  USER_GUIDE.md
  workflow.md
  troubleshooting.md
  panes/
    project.md
    splits.md
    score.md
    pip.md
    overlay.md
    review.md
    export.md
    metrics.md
```

The eight pane files are required and must be linked from `docs/userfacing/USER_GUIDE.md`. `workflow.md` and `troubleshooting.md` are recommended supporting pages so pane guides can stay focused while still giving users a complete end-to-end path.

## Screenshot Usage Standard

Use HTML image tags for every large screenshot:

```html
<img src="../../screenshots/ProjectPane.png" alt="Project pane with project metadata, PractiScore import, primary video selection, and project folder controls" width="960">
```

Guidelines:

- Use `width="960"` for the main screenshot in pane pages.
- Use `width="760"` or `width="840"` for secondary detail screenshots on the same page.
- Use a concise, descriptive `alt` value that names the pane and the visible purpose.
- Do not duplicate the same screenshot across unrelated pages unless it explains shared layout.
- Keep the full-resolution PNG files in `docs/screenshots/`; do not create resized duplicates unless load time becomes a problem.
- From root README, reference screenshots as `docs/screenshots/...`.
- From `docs/userfacing/USER_GUIDE.md`, `workflow.md`, and `troubleshooting.md`, reference screenshots as `../screenshots/...`.
- From `docs/userfacing/panes/*.md`, reference screenshots as `../../screenshots/...`.

## Screenshot-To-Guide Map

| Guide | Screenshot Assets | Purpose |
| --- | --- | --- |
| `docs/userfacing/panes/project.md` | `ProjectPane.png` | Project setup, source video, PractiScore import, project folder lifecycle |
| `docs/userfacing/panes/splits.md` | `SplitsPane.png`, `SplitsExpanded.png`, `WaveFormExpanded.png` | Timing review, threshold, selected-shot edits, waveform editing, expanded timing workbench |
| `docs/userfacing/panes/score.md` | `ScoringPane.png` | Scoring enablement, presets, per-shot score values, penalties, imported context |
| `docs/userfacing/panes/pip.md` | `PiPPane.png` | Added media, secondary angle preview, PiP placement, sync, export enablement |
| `docs/userfacing/panes/overlay.md` | `OverlayPane.png`, `OverlayPane2.png` | Shot badge stack, timer/draw/score badges, placement, style, fonts, score colors |
| `docs/userfacing/panes/review.md` | `ReviewPane.png` | Preview toggles, review text boxes, imported summary boxes, custom text overlays |
| `docs/userfacing/panes/export.md` | `ExportPane.png` | Presets, frame settings, codecs, audio, output path, export log, local render workflow |
| `docs/userfacing/panes/metrics.md` | `MetricsPane.png`, `MetricsPane2.png`, `MetricsCSV.png` | Stage dashboard, scoring context, trend snapshot, CSV/text export |
| `docs/userfacing/workflow.md` | Use one representative overview screenshot only if needed | End-to-end path from import to export |

## README Rewrite Plan

The root README should be the user-facing front door. It should not read like a developer architecture index.

Recommended structure:

1. Logo and product name.
2. One-sentence product summary: local-first browser app for competition shooting video analysis, split timing, scoring, overlay review, PiP, metrics, and export.
3. Short "What SplitShot Does" section focused on in-app outcomes:
   - import a stage video;
   - detect beep and shots;
   - review and correct split timing;
   - score the run manually or with PractiScore context;
   - tune on-video badges and summary boxes;
   - add PiP media or a second angle;
   - review metrics;
   - export a finished local video.
4. "Who It Is For" section:
   - shooters reviewing match footage;
   - match video editors preparing stage recaps;
   - users who want local processing instead of cloud upload.
5. "Install Requirements" section:
   - Python 3.12;
   - `uv`;
   - `ffmpeg` and `ffprobe`;
   - desktop browser.
6. "Install And Launch" section:
   - setup script path for macOS/Linux;
   - setup script path for Windows PowerShell;
   - manual `uv sync --extra dev`;
   - launch with `uv run splitshot`;
   - optional `uv run splitshot --no-open` and `uv run splitshot --check`.
7. "Basic Workflow" section with 6 to 8 concrete steps:
   - create or open project;
   - select primary video;
   - wait for analysis;
   - correct timing in Splits;
   - score or import PractiScore;
   - tune overlay and review text boxes;
   - add PiP if needed;
   - export.
8. "App Guides" section linking to every pane guide:
   - Project;
   - Splits;
   - Score;
   - PiP;
   - Overlay;
   - Review;
   - Export;
   - Metrics.
9. "More Documentation" section linking to `docs/userfacing/USER_GUIDE.md`, workflow, troubleshooting, current limitations, and technical docs.
10. License.

README image plan:

- Replace the missing `docs/assets/browser-shell.png` reference.
- Use one representative screenshot from `docs/screenshots/`, sized with HTML:

```html
<img src="docs/screenshots/ProjectPane.png" alt="SplitShot browser app showing the Project pane and video review workspace" width="1000">
```

## Pane Guide Template

Each pane guide should use the same shape so users can learn quickly:

1. Title.
2. One-paragraph purpose statement.
3. Main screenshot.
4. "When To Use This Pane".
5. "Before You Start" prerequisites.
6. "Key Controls" table with user-facing labels and plain-English behavior.
7. "How To Use It" numbered workflow.
8. "How It Affects The Rest Of SplitShot".
9. "Common Mistakes And Fixes".
10. Links to previous and next relevant guides.

Every pane guide must explain every visible feature of that pane exhaustively. That means every control, toggle, button, field, dropdown option, mode, default expectation, downstream effect, screenshot-visible region, common state, and user-facing caveat should be documented. If a control changes behavior depending on project state, scoring preset, imported data, selected shot, or available media, document those state-dependent behaviors.

Avoid implementation terms such as API route names, serializer names, controller classes, test files, or source-module names in user-facing pages.

## Per-Pane Content Plan

### Project Guide

File: `docs/userfacing/panes/project.md`

Must cover:

- project name and description;
- primary video selection through file picker;
- primary video selection through direct local path;
- why direct path is better for very large files;
- what happens after a video is selected;
- PractiScore import flow;
- match type, stage number, competitor name, and place selectors;
- project folder selection;
- new project and delete project;
- saving and reopening project bundles;
- how project choices populate Splits, Score, Overlay, Review, Export, and Metrics.

Screenshot:

- `ProjectPane.png` at `width="960"`.

### Splits Guide

File: `docs/userfacing/panes/splits.md`

Must cover:

- shot and beep detection basics;
- detection threshold and when to raise or lower it;
- compact Splits pane;
- timing summary;
- selected-shot panel;
- nudge buttons;
- deleting a selected shot;
- timing table;
- waveform marker selection;
- waveform drag editing;
- Add Shot mode;
- zoom, amplitude, reset, and expand controls;
- expanded timing workbench;
- custom timing events such as reload, malfunction, and custom label;
- relationship between Splits, scoring, metrics, overlay timing, and export.

Screenshots:

- `SplitsPane.png` at `width="960"`.
- `SplitsExpanded.png` at `width="840"`.
- `WaveFormExpanded.png` at `width="840"`.

### Score Guide

File: `docs/userfacing/panes/score.md`

Must cover:

- enabling or disabling scoring;
- choosing a scoring preset;
- scoring selected shots;
- score letters and what shorthand such as M, NS, PE, FP, FTDR, and FPE means;
- per-shot score list;
- manual penalty points and preset penalty fields;
- imported PractiScore context;
- restoring original score values when available;
- how scoring changes affect Metrics, Review, Overlay, and Export.

Screenshot:

- `ScoringPane.png` at `width="960"`.

### PiP Guide

File: `docs/userfacing/panes/pip.md`

Must cover:

- adding PiP media;
- supported extra media types at a user level: videos and images;
- enabling added media export;
- layout choices: side by side, above/below, and picture in picture;
- default PiP size and normalized X/Y placement;
- per-item PiP cards;
- sync offset and millisecond nudges;
- swapping or comparing angles if available in the UI;
- difference between preview setup and final export inclusion;
- what happens with multiple added media items.

Screenshot:

- `PiPPane.png` at `width="960"`.

### Overlay Guide

File: `docs/userfacing/panes/overlay.md`

Must cover:

- what overlay badges are;
- shot badge stack behavior;
- badge size and style;
- shot gap and frame padding;
- shots shown;
- quadrant and shot flow;
- custom X/Y coordinates;
- timer, draw, and score badge placement;
- lock-to-stack behavior;
- bubble width and height;
- font family, font size, bold, italic;
- badge style colors;
- score text colors;
- live preview expectations;
- how overlay settings feed Review and Export.

Screenshots:

- `OverlayPane.png` at `width="960"`.
- `OverlayPane2.png` at `width="840"`.

### Review Guide

File: `docs/userfacing/panes/review.md`

Must cover:

- preview-only visibility toggles;
- timer badge, draw badge, split badges, and scoring summary visibility;
- review text boxes;
- adding a custom box;
- adding a PractiScore summary box;
- enabling and disabling individual boxes;
- content source;
- placement options;
- custom X/Y placement;
- width and height;
- background color, text color, opacity;
- duplicate and remove;
- drag-to-place behavior if verified;
- lock review text boxes to overlay stack;
- when summary boxes appear relative to final shot.

Screenshot:

- `ReviewPane.png` at `width="960"`.

### Export Guide

File: `docs/userfacing/panes/export.md`

Must cover:

- export presets;
- quality setting;
- aspect ratio and crop behavior;
- output width and height;
- frame rate;
- H.264 and HEVC;
- video bitrate;
- AAC audio settings;
- sample rate and audio bitrate;
- Rec.709 SDR color setting;
- FFmpeg preset tradeoff in user terms;
- two-pass encoding;
- output path and supported containers;
- Browse button;
- Show Log;
- Export Video;
- what is included in an export: timing, overlays, score summary, review boxes, and enabled PiP media;
- troubleshooting export failures at a user level.

Screenshot:

- `ExportPane.png` at `width="960"`.

### Metrics Guide

File: `docs/userfacing/panes/metrics.md`

Must cover:

- what Metrics summarizes;
- summary cards;
- draw time;
- raw time;
- shots;
- average split;
- beep timing;
- scoring result;
- trend snapshot;
- split progression;
- confidence context;
- scoring context;
- imported-stage context;
- Export CSV;
- Export Text;
- how exported metrics can be used in spreadsheets or notes;
- why metrics change after editing Splits or Score.

Screenshots:

- `MetricsPane.png` at `width="960"`.
- `MetricsPane2.png` at `width="840"`.
- `MetricsCSV.png` at `width="760"`.

## Supporting User Pages

### Root User Guide

File: `docs/userfacing/USER_GUIDE.md`

Must include:

- a short app overview;
- "Start Here" path for new users;
- a guide list for each pane under `docs/userfacing/panes/`;
- "Common workflows" links;
- "Troubleshooting" link;
- "Technical docs" link back to `../README.md` for users who need repository details.
- a clear note that the pane pages are the exhaustive references for every visible pane feature.

### Workflow Guide

File: `docs/userfacing/workflow.md`

Must include:

- first launch;
- import primary video;
- wait for local analysis;
- validate splits;
- optionally import PractiScore;
- score or adjust score context;
- tune overlays;
- add PiP media;
- review final state;
- export final video;
- save project bundle.

### Troubleshooting Guide

File: `docs/userfacing/troubleshooting.md`

Must include:

- no video selected;
- large video import path guidance;
- browser preview audio missing;
- missing or extra shots;
- PractiScore import does not match expected competitor or stage;
- overlay appears in preview but not as expected in export;
- PiP media not included in export;
- export fails because FFmpeg or ffprobe is missing;
- output path or container problems;
- project folder confusion.

## Docs Hub Updates

Update `docs/README.md` so the order is:

1. User Docs.
2. Current Limitations.
3. Technical Docs.
4. Development Docs.
5. Repository Files.

The top of `docs/README.md` should link directly to:

- `userfacing/USER_GUIDE.md`;
- all eight pane guides;
- `LIMITATIONS.md`.

Keep source package READMEs available, but do not make them the first thing a user sees.

## Existing `docs/USER_GUIDE.md` Decision

Choose one of these during implementation:

1. Rewrite it as a concise compatibility page that links immediately to `docs/userfacing/USER_GUIDE.md`.
2. Move its detailed pane content into `docs/userfacing/panes/` and leave `docs/USER_GUIDE.md` as a compatibility index.

Recommended choice: option 1. This preserves the existing link target while making `docs/userfacing/USER_GUIDE.md` the canonical root-level user guide.

## Documentation Quality Bar

Every user-facing page should:

- explain what the user can accomplish;
- name visible controls exactly as they appear in the UI;
- document every visible pane feature exhaustively on pane pages;
- include the relevant screenshot near the top;
- describe prerequisites and downstream effects;
- include recovery steps for common confusion;
- avoid code, tests, internal modules, and implementation details;
- use relative links that work on GitHub;
- keep tables readable on GitHub by avoiding overly long cells.

## Implementation Sequence

1. Confirm the pane list and control labels against `src/splitshot/browser/static/index.html`.
2. Create `docs/userfacing/USER_GUIDE.md`.
3. Create the eight exhaustive pane guides under `docs/userfacing/panes/` using the screenshot map above.
4. Create `docs/userfacing/workflow.md`.
5. Create `docs/userfacing/troubleshooting.md`.
6. Rewrite root `README.md` as the user-facing product entry point.
7. Update `docs/README.md`.
8. Rewrite `docs/USER_GUIDE.md` as a compatibility page pointing to `docs/userfacing/USER_GUIDE.md`.
9. Run the validation checklist below.

## Validation Checklist

Run these checks after writing the documentation:

```bash
rg -n "docs/assets/browser-shell|TODO|TBD|FIXME" README.md docs
find docs/userfacing -maxdepth 1 -type f -name "*.md" | sort
find docs/userfacing/panes -maxdepth 1 -type f -name "*.md" | sort
find docs/screenshots -maxdepth 1 -type f -name "*.png" | sort
```

Manual checks:

- Open root `README.md` on GitHub or in a Markdown preview and confirm the top image renders at a reasonable size.
- Open `docs/userfacing/USER_GUIDE.md`, every `docs/userfacing/panes/*.md` page, and each supporting page, then confirm every screenshot renders.
- Click every guide link from root `README.md`.
- Click every guide link from `docs/README.md`.
- Confirm every pane guide has "When To Use", "Key Controls", "How To Use", and "Common Mistakes And Fixes".
- Confirm every pane guide documents every screenshot-visible feature and every visible control in the corresponding app pane.
- Confirm the documentation uses `PiP` consistently instead of mixing `Merge` for user-facing labels.
- Confirm no user-facing page refers to source files, routes, controller names, serializer names, test files, or internal package names unless the page is intentionally technical.

## Definition Of Done

The documentation pass is complete when:

- a new user can start at `README.md` and reach a complete guide for every app pane;
- every pane guide includes the correct screenshot at an appropriate displayed width;
- install and launch instructions are accurate for macOS/Linux, Windows, and manual setup;
- the README describes app features and user workflows rather than repository internals;
- `docs/userfacing/USER_GUIDE.md` is the root-level user documentation hub;
- every pane guide lives underneath it in `docs/userfacing/panes/` and is linked from `docs/userfacing/USER_GUIDE.md`;
- every pane guide explains every visible pane feature exhaustively and includes the associated screenshot or screenshots;
- `docs/README.md` clearly separates user docs from technical docs;
- all links and screenshot paths resolve from GitHub Markdown.
