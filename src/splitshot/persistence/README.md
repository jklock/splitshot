# Persistence

This package owns `.ssproj` bundle save, load, normalization, and deletion behavior.

## Purpose

Use it when the change affects saved project format, bundle directory layout, project-path handling, or browser-session media preservation inside saved bundles.

## Read This First

- [projects.py](projects.py)

## Main Files

- [projects.py](projects.py): bundle save/load/delete helpers and project-path normalization

## Runtime Flow

1. Normalize the target bundle path.
2. Save or load `project.json`.
3. Copy transient browser-session media into the bundle when needed.
4. Return a fully reconstructed `Project`.

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
