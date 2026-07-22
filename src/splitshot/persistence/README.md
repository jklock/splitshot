# Persistence

This package owns project-folder save, load, normalization, and metadata deletion behavior. A project is identified by `project.json`; the folder name does not require a special suffix.

## Purpose

Use it when the change affects saved project format, project directory layout, project-path handling, or imported-asset ownership.

## Read This First

- [projects.py](projects.py)

## Main Files

- [projects.py](projects.py): bundle save/load/delete helpers and project-path normalization

## Runtime Flow

1. Normalize the selected project directory.
2. Ensure `Input`, `CSV`, `Markers`, and `Output` exist beside `project.json`.
3. Copy media, PractiScore files, and marker images into their owned project subdirectories during import.
4. Save in-project paths relative to the project root and resolve them when loading.
5. Return a fully reconstructed `Project`.

## Key Extension Points

- `save_project`
- `load_project`
- `delete_project`
- `ensure_project_suffix`

## Related Tests

- [../../../tests/persistence/](../../../tests/persistence/)
- [../../../tests/browser/test_project_lifecycle_contracts.py](../../../tests/browser/test_project_lifecycle_contracts.py)

## Related Docs

- [../../../docs/project/ARCHITECTURE.md](../../../docs/project/ARCHITECTURE.md)
- [../../../docs/userfacing/panes/project.md](../../../docs/userfacing/panes/project.md)
