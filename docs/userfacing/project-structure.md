# Project Structure

SplitShot stores a project as a `.ssproj` bundle.

## Expected Layout

```text
My Project.ssproj/
  project.splitshot.json
  CSV/
  Input/
  Output/
```

## What Lives Here

| Path | Purpose |
| --- | --- |
| `project.splitshot.json` | Saved project metadata, stage records, queue state, and export settings. |
| `CSV/` | PractiScore source files staged for the project. |
| `Input/` | Imported media copied or staged for project use. |
| `Output/` | Rendered exports. |

## Multi-Stage Notes

- Stage media, stage-local settings, and queue status are stored inside the project metadata.
- Each stage can keep one primary video and any number of added media items.
- Queue processing writes outputs into the project output area.

## Related Guides

- [panes/project.md](panes/project.md)
- [panes/media.md](panes/media.md)
- [panes/queue.md](panes/queue.md)
