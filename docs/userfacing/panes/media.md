# Media Pane

The Media pane is the stage media workspace. It makes one stage active at a time, names that stage, and shows the primary and added media that belong to it.

## Use This Pane For

- Reviewing the active stage workspace and collapsing or expanding the file inventory.
- Selecting the active stage.
- Naming the active stage and saving that label.
- Viewing and managing file rows for primary and added media.
- Setting the primary video from any attached file.
- Adding more media files to a stage.
- Removing files from a stage.
- Creating or deleting stages.

## Key Controls

| Control | What it does |
| --- | --- |
| `Stage #` | Chooses which stage is active across the rest of the app. |
| `Stage Name` | Renames the active stage. |
| `Save Stage` | Saves the current stage label. |
| `Delete Stage` | Removes the active stage. |
| File row | Shows one attached file with its filename, type, duration, and dimensions. |
| `Add Primary` / `Replace` | Imports or replaces the primary file for the active stage. |
| `Set Primary` | Promotes an added file into the primary slot. |
| `Remove` | Removes that file from the stage. |
| `Add Media` | Adds additional media files to the active stage. |
| `Add Stage` | Creates another stage and makes it active. |

## Workflow

1. Import PractiScore data in [project.md](project.md) first when stage records are available.
2. Open Media.
3. Choose the stage you want to work on.
4. Import a primary video for that stage.
5. Add more files with Add Media.
6. Set the primary designation on the file row you want.
7. Remove any files that do not belong.
8. Leave that stage selected so Compose, Trim, Score, Splits, Markers, Overlay, Review, Export, and Queue all use it.
9. Repeat for every stage in the project.
10. Move to [pip.md](pip.md) to configure the active stage composition.

## Notes

- One stage is active at a time across Compose, Trim, Score, Splits, Markers, Overlay, Review, Export, and Queue.
- Stage media is stage-local. Switching stages swaps the full editing context.
- The stage selector and summary token show which stage the rest of the app is editing.
- Competitor identity selectors live in Project, not here. Media owns stage selection, stage naming, and stage files.

## Related Guides

Previous: [project.md](project.md)
Next: [pip.md](pip.md)
