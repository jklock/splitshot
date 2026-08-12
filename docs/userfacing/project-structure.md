# Project Structure

<!-- Documentation reviewed: 2026-08-11 -->

SplitShot stores a project in a user-selected directory containing `project.json`. The directory does not need a `.ssproj` suffix, although CLI-created or older paths may use one.

## Expected Layout

```text
My Project/
  project.json
  Input/
  CSV/
  Markers/
  IntroOutro/
  Output/
```

## What Lives Here

| Path | Purpose |
| --- | --- |
| `project.json` | Saved project metadata, stage records, queue state, and export settings. |
| `Input/` | Project-managed primary and added stage media, plus generated trim derivatives. |
| `CSV/` | Project-managed PractiScore CSV/TXT sources. |
| `Markers/` | Project-managed marker images. |
| `IntroOutro/` | Optional project-managed match intro and outro videos. |
| `Output/` | Rendered exports. |

## File Ownership

- Creating a project creates every folder shown above.
- After a project is selected, Media, PractiScore, marker-image, and output pickers open from the active project or their owned project subfolder instead of an unrelated last-used system location.
- Selecting a file outside the project copies it into the owned subfolder before SplitShot uses it.
- Selecting a file already in the owned subfolder uses it in place.
- `project.json` stores project-local paths relative to the selected project folder for every stage.
- Autosave writes metadata only; it never moves or copies media.
- Removing a file from a stage removes the association, not the project file on disk.

The complete project folder can therefore be moved or archived as one portable unit.

These rules are platform-independent. Windows paths, macOS paths, and Linux paths are normalized when saved; the project metadata stores project-relative paths rather than operating-system-specific absolute paths. `Open Project` selects an existing SplitShot project directory through the platform folder picker.

## Multi-Stage Notes

- Stage media, stage-local settings, and queue status are stored inside the project metadata.
- Each stage can keep one primary video and any number of added media items.
- Every stage follows the same project-relative path rules, including inactive stages.
- Queue processing writes outputs into the project output area.

## Related Guides

- [panes/project.md](panes/project.md)
- [panes/media.md](panes/media.md)
- [panes/queue.md](panes/queue.md)
