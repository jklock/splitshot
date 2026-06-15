# Project Pane

The Project pane owns project metadata and PractiScore import. It does not own media selection.

## Use This Pane For

- Creating or opening a project bundle.
- Naming the project and storing notes.
- Importing a PractiScore CSV/TXT source.
- Choosing the active match type, stage, competitor, and place context.

## Key Controls

| Control | What it does |
| --- | --- |
| `Project folder` | Shows the current project bundle location. |
| `Select Project` | Opens an existing `.ssproj` bundle. |
| `Create Project` | Creates a new project bundle and resets the current session. |
| `Delete Project` | Deletes the saved project metadata without deleting the surrounding folder. |
| `Project name` | Sets the saved project name. |
| `Project description` | Stores project notes. |
| `Open PractiScore Dashboard` | Opens PractiScore in your system browser. |
| `Select PractiScore File` | Imports a local PractiScore CSV/TXT file. |
| `Match type` | Chooses the active scoring family. |
| `Stage #` | Chooses the active imported stage context. |
| `Competitor name` | Chooses the competitor row. |
| `Place` | Chooses the matching place entry when duplicates exist. |

## Workflow

1. Create or open the project first.
2. Set `Project name` and `Project description`.
3. Import the PractiScore CSV/TXT file if stage results are needed.
4. Confirm `Match type`, `Stage #`, `Competitor name`, and `Place`.
5. Move to [media.md](media.md) to pair stage media.

## Downstream Effects

- Imported PractiScore data sets the scoring context for the active stage.
- Imported stage numbers drive the multi-stage workflow when available.
- Media import, pairing, and stage switching live in the Media and Queue panes, not here.

## Related Guides

Next: [media.md](media.md)
