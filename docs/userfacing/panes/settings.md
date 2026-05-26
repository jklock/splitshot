# Settings Pane

The Settings pane controls app-wide and folder-scoped defaults for layout, scoring, composition, overlay, markers, export, and ShotML.

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
| `Use Current Project As Defaults` | Copies the current project's settings into the selected scope. |
| `Reset Defaults` | Restores the selected scope to factory defaults. |
| Scope status hint | Shows whether app or folder defaults are active. Folder defaults only apply to new projects in that folder, not retroactively. |

### Layout

| Control | What it does |
| --- | --- |
| `Lock layout by default` | Starts new projects with the layout locked. |
| `Rail width` | Default rail width for new projects. |
| `Inspector width` | Default inspector panel width for new projects. |
| `Waveform height` | Default waveform height for new projects. |
| `Use Current Layout` | Captures the current project's layout as the default. |
| `Release Layout` | Clears saved layout defaults, reverting to built-in defaults. |

### Scoring

| Control | What it does |
| --- | --- |
| `Default sport` | Sets the starting match type for new projects (USPSA, IDPA, or Steel Challenge). An imported file overrides this. |

### Compose

| Control | What it does |
| --- | --- |
| `Composition layout` | Default added-media layout for new Compose items. |
| `Layer size` | Default floating-layer size for new added media. |
| `Layer X` / `Layer Y` | Default normalized position for new added-media layers. |

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
4. Use `Use Current Project As Defaults` to seed defaults from the current project state.
5. Use `Reset Defaults` when you want to start fresh.
6. For layout, use `Use Current Layout` after arranging the workspace exactly as you want new projects to open.
7. Marker template changes apply to newly created markers, not existing ones. Existing markers keep their own state.

## Scope Behavior

- `App Defaults` apply to every new project regardless of folder.
- `Folder Defaults` apply only to new projects created inside the selected folder.
- Folder defaults take priority over app defaults when both exist for the same setting.
- Changing folder defaults does not retroactively apply to existing projects in that folder.

## Related Guides

Previous: [export.md](export.md)
Next: [metrics.md](metrics.md)
<!-- settings-pane-guide-eof -->
