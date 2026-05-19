# Automate UI

This package is the UI completion command center for the automation work already implemented in `docs/automate/`.

Start here:

1. [spec.md](spec.md)
2. [todo.md](todo.md)
3. [execution-order.md](execution-order.md)
4. [outcomes.md](outcomes.md)
5. [tracks/01-pip-performance-and-merge-editor.md](tracks/01-pip-performance-and-merge-editor.md)

## Purpose

`docs/automate/` defines the backend and contract layer.

`docs/automate-ui/` defines the browser-shell and packaged-app completion work required to make that backend usable, coherent, and shippable.

## Package Rules

- `spec.md` is the authoritative UI build spec.
- `todo.md` is the execution checklist.
- `outcomes.md` defines what completion means.
- `progress.md` is the live execution ledger.
- `execution-order.md` is the dependency-respecting work order for today.

## Scope

This package covers:

- browser shell overhaul
- Single Video UI completion
- Multi Video workspace UI
- Performance Library UI
- PiP playback smoothness and merge-editor usability
- UI-targeted proof, regression, and release closure

This package does not redefine the backend contract in `docs/automate/`; it builds the UI needed to expose it correctly.
