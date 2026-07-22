# Project Pane

The Project pane owns project metadata, PractiScore import, competitor identity selectors, and the compact imported summary. It does not own stage media intake, stage file rows, primary designation, or queue controls.

<img src="../../screenshots/ProjectPane.png" alt="Project pane with project-folder controls, project metadata, PractiScore import, and competitor selection" width="960">

## Use This Pane For

- Creating or opening a project folder.
- Naming the project and storing notes.
- Importing a PractiScore CSV/TXT source.
- Selecting the imported stage for context lookup.
- Choosing the competitor name and competitor place.
- Checking the compact imported match summary (name, place, match time, division).

## Key Controls

| Control | What it does |
| --- | --- |
| `Project folder` | Shows the current project directory. |
| `Select Project` | Selects a directory. It opens the project when `project.json` exists or offers to initialize the directory when it does not. |
| `Create Project` | Selects a directory, initializes a blank project there, and resets the current session. If a project already exists there, SplitShot asks before replacing it. |
| `Open Project Folder` | Opens the active directory in the operating system's file manager. |
| `Delete Project` | Deletes the saved project metadata without deleting the surrounding folder. |
| `Project name` | Sets the saved project name. |
| `Project description` | Stores project notes. |
| `Open PractiScore Dashboard` | Opens PractiScore in your system browser. |
| `Select PractiScore File` | Opens in the project `CSV/` folder and imports a project-managed CSV/TXT file. Files selected elsewhere are copied into `CSV/`. |
| `Match type` | Chooses the active scoring family. |
| Stage selector | Chooses the imported stage for context lookup. |
| Competitor name selector | Selects the imported competitor by name. |
| Competitor place selector | Selects the imported competitor by place. |
| `PractiScore summary` | Shows the imported name, place, match time, and division. |

## Workflow

1. Create or open the project first.
   Creating a project also creates `Input/`, `CSV/`, `Markers/`, and `Output/`.
2. Set `Project name` and `Project description`.
3. Import the PractiScore CSV/TXT file if stage results are needed.
4. Select the imported stage, competitor name, and competitor place.
5. Confirm the compact imported summary.
6. Move to [media.md](media.md) to pair stage media and manage files per stage.

The selected directory is the root for the rest of the workflow. Media pickers start in `Input/`, PractiScore starts in `CSV/`, marker images start in `Markers/`, and output selection starts in `Output/`. A supported file selected elsewhere is copied into its owned project subfolder before it is attached. SplitShot then saves a project-relative path in `project.json`, so the project does not depend on the source file's Windows, macOS, or Linux absolute path.

## Downstream Effects

- Imported PractiScore data seeds stage-local scoring context and the project summary.
- Stage media intake, file rows, primary designation, file removal, and active-stage selection live in Media.
- Queue and export processing live downstream in Queue, not here.
- Autosave updates `project.json`; it does not copy or relocate project files.

## Related Guides

Next: [media.md](media.md)
