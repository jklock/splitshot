# Persistence

The persistence package stores and restores SplitShot project bundles.

## Files

- [projects.py](projects.py) implements `.ssproj` bundle save, load, and delete operations.

## Bundle Format

- `PROJECT_FILENAME` is `project.json`.
- `MEDIA_DIRNAME` is `media`.
- `save_project` writes a bundle directory with the project JSON and any copied media.
- `load_project` reconstructs a `Project` from the saved JSON.
- `delete_project` removes the bundle directory.

## Media Copying Rules

`_copy_project_media_if_needed` clones the project and copies media into the bundle when the source path belongs to a browser session directory. That keeps temporary uploads alive after the browser session ends.

## Notes

- `ensure_project_suffix` normalizes the bundle path to `.ssproj`.
- The saved bundle is a directory, not a single archive file.
- The controller tracks recently opened bundles in app settings.