# UI

<!-- Documentation reviewed: 2026-08-11 -->

This package owns the shared controller layer that mutates the canonical project state.

## Purpose

Use it when the change affects project mutation rules, settings persistence, import flows, analysis dispatch, merge or overlay state management, or saved-project lifecycle behavior.

## Read This First

- [controller.py](controller.py)

## Main Files

- [controller.py](controller.py): `ProjectController` and project mutation helpers

## Ownership Boundaries

- The controller is the main mutation boundary for project state.
- Browser routes should delegate business-state changes here instead of duplicating logic.
- Persistence, analysis, scoring, merge, and export integrations flow through the controller.

## Key Extension Points

- `ProjectController`
- media import and project lifecycle helpers
- settings load/save hooks

## Related Tests

- [../../../tests/browser/test_browser_control.py](../../../tests/browser/test_browser_control.py)
- [../../../tests/persistence/](../../../tests/persistence/)

## Related Docs

- [../../../docs/project/ARCHITECTURE.md](../../../docs/project/ARCHITECTURE.md)
- [../domain/README.md](../domain/README.md)
