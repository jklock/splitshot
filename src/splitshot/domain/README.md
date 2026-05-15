# Domain

This package owns the canonical SplitShot project schema, enums, nested dataclasses, and serialization helpers.

## Purpose

Use it when a change affects saved project shape, API payload shape, overlay or scoring settings, merge state, export settings, or any contract that multiple layers share.

## Read This First

- [models.py](models.py)

## Main Files

- [models.py](models.py): enums, dataclasses, conversion helpers, and `Project`

## Ownership Boundaries

- `Project` is the shared application contract.
- Browser, controller, analysis, persistence, and export code should read and write this model rather than maintain parallel schemas.
- Serialization helpers are the source of truth for saved-project and JSON-safe conversion logic.

## Key Extension Points

- `Project`
- `project_to_dict`
- `project_from_dict`

## Related Tests

- [../../../tests/persistence/](../../../tests/persistence/)
- [../../../tests/browser/test_browser_control.py](../../../tests/browser/test_browser_control.py)

## Related Docs

- [../../../docs/project/ARCHITECTURE.md](../../../docs/project/ARCHITECTURE.md)
- [../ui/README.md](../ui/README.md)
