# Project Pane

The Project pane owns project metadata, PractiScore import, competitor identity selectors, and the compact imported summary. It does not own stage media intake, stage file rows, primary designation, or queue controls.

## Use This Pane For

- Creating or opening a project bundle.
- Naming the project and storing notes.
- Importing a PractiScore CSV/TXT source.
- Selecting the imported stage for context lookup.
- Choosing the competitor name and competitor place.
- Checking the compact imported match summary (name, place, match time, division).

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
| Stage selector | Chooses the imported stage for context lookup. |
| Competitor name selector | Selects the imported competitor by name. |
| Competitor place selector | Selects the imported competitor by place. |
| `PractiScore summary` | Shows the imported name, place, match time, and division. |

## Workflow

1. Create or open the project first.
2. Set `Project name` and `Project description`.
3. Import the PractiScore CSV/TXT file if stage results are needed.
4. Select the imported stage, competitor name, and competitor place.
5. Confirm the compact imported summary.
6. Move to [media.md](media.md) to pair stage media and manage files per stage.

## Downstream Effects

- Imported PractiScore data seeds stage-local scoring context and the four-row project summary.
- Stage media intake, file rows, primary designation, file removal, and Edit Stage live in Media.
- Queue and export processing live downstream in Queue, not here.

## Related Guides

Next: [media.md](media.md)
