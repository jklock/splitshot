# Settings Pane

<!-- Documentation reviewed: 2026-08-11 -->

The Settings pane controls app-wide and folder-scoped defaults for layout, scoring, compose, overlay, markers, export, and ShotML.

<img src="../../screenshots/SettingsPane.png" alt="Settings pane with scope, layout, scoring, Compose, Overlay, Markers, Export, and ShotML defaults" width="960">

<img src="../../screenshots/SettingsPane2.png" alt="Lower Settings pane with expanded marker, export, and ShotML default controls" width="840">

## When To Use This Pane

- Before starting a new project, to set preferred defaults.
- When you want to change the landing pane or reopen-last-tool behavior.
- When you want to capture the current project's layout as the default.
- When you want to tune default marker templates.
- When defaults should apply to a specific project folder instead of globally.

## Key Controls

### Global Template

| Control | What it does |
| --- | --- |
| `Save scope` | Chooses between `App Defaults` (global) and `Folder Defaults` (project-folder scoped). |
| `Landing pane` | Sets which pane opens by default when a new project is created. |
| `Reopen the selected pane on new projects` | Remembers the last-used pane and reopens it on the next project. |
| `Save Current Settings` | Flushes pending edits, then copies every persistent project setting into the selected scope, including Queue/combined-output and Intro/Outro fade and overlay configuration. Media paths, output paths, logs, errors, and include-media choices are excluded. |
| `Reset Defaults` | Restores the selected scope to factory defaults. |
| Scope status hint | Shows whether app or folder defaults are active. Folder defaults only apply to new projects in that folder, not retroactively. |

### Layout

| Control | What it does |
| --- | --- |
| `Lock layout by default` | Starts new projects with the layout locked. |
| `Rail width` | Default rail width for new projects. |
| `Inspector width` | Default inspector panel width for new projects. |
| `Waveform height` | Default waveform height for new projects. |
| `Save Current Settings` | Captures the current project's layout as the default. |
| `Release Layout` | Clears saved layout defaults, reverting to built-in defaults. |

### Scoring

| Control | What it does |
| --- | --- |
| `Default sport` | Sets the starting match type for new projects (USPSA, IPSC, IDPA). An imported file overrides this. |

### Compose

The Compose section is the sole owner of global/folder compose defaults. Per-source controls in the Compose pane do not set defaults — they only affect individual items.

| Control | What it does |
| --- | --- |
| `Layout` | Default layout for new added media. |
| `Size` | Default item size. |
| `X` / `Y` | Default normalized position for new items. |

### Overlay

| Control | What it does |
| --- | --- |
| `Overlay position` | Default overlay anchor. |
| `Badge size` | Default badge scale preset. |
| `Stage box background` / `Stage box text` / `Stage box Opacity` | Default stage-summary box colors and opacity. |
| Timer / Shot / Current Shot / Score badge cards | Default per-badge background, text color, and opacity for new projects. |

### Markers

| Control | What it does |
| --- | --- |
| `Enabled` | Whether new markers start enabled. |
| `Content` | Default marker content type (Text, Image, Text + Image). |
| `Text source` | Default text source for new markers. |
| `Duration (s)` | Default marker duration. |
| `Use shot split duration` | Marker duration follows the shot split instead of a fixed value. |
| `Width` / `Height` | Default marker dimensions (0 = auto). |
| `Enable motion` | Whether new markers start with motion enabled. |
| `Background` / `Text` / `Opacity` | Default marker colors and opacity. |

### Export

| Control | What it does |
| --- | --- |
| `Export quality` | Default export quality preset. |
| `Preset` | Default export preset. |
| `Frame rate` | Default export frame rate. |
| `Video codec` | Default video encoder. |
| `Audio codec` | Default audio encoder. |
| `Color space` | Default color pipeline. |
| `FFmpeg preset` | Default encoder speed/efficiency trade-off. |
| `Use two-pass export` | Default two-pass encoding setting. |

### ShotML

| Control | What it does |
| --- | --- |
| `ShotML threshold` | Default detection threshold for new projects. |

## How To Use It

1. Choose `Save scope` first — `App Defaults` for global settings, `Folder Defaults` for project-folder scoped settings.
2. Expand each section with the chevron to reveal its controls.
3. Adjust the `Landing pane` and `Reopen the selected pane on new projects` before starting a new project.
4. Use `Save Current Settings` in Global Template to capture the current Compose, Overlay and Review, Marker, Export, ShotML, scoring, layout, Queue, combined-output, and Intro/Outro configuration together. Section buttons update only that section.
5. Use `Reset Defaults` when you want to start fresh.
6. For layout, use `Use Current Layout` after arranging the workspace exactly as you want new projects to open.
7. Marker template changes apply to newly created markers, not existing ones. Existing markers keep their own state.

## Scope Behavior

- `App Defaults` are stored outside any project and apply to every new project, including after restarting SplitShot.
- `Folder Defaults` apply only to new projects created inside the selected folder.
- Folder defaults take priority over app defaults when both exist for the same setting.
- Changing folder defaults does not retroactively apply to existing projects in that folder.

## Related Guides

Previous: [shotml.md](shotml.md)
Next: [../workflow.md](../workflow.md)
