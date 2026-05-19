# MASTER

`docs/automate-ui/spec.md` is the single exhaustive UI build spec for this work.

Use the rest of the package as execution support:

- [todo.md](todo.md) for the implementation checklist
- [execution-order.md](execution-order.md) for the same-day sequence
- [outcomes.md](outcomes.md) for completion gates
- [progress.md](progress.md) for the running ledger
- `tracks/` for subsystem-specific requirements
- `artifacts/` for audit and proof matrices

## Truth Sources

- Backend contract: [../automate/spec equivalents](../automate/00-product-definition.md)
- UI build spec: [spec.md](spec.md)
- PiP blocker track: [tracks/01-pip-performance-and-merge-editor.md](tracks/01-pip-performance-and-merge-editor.md)

## Standing Rule

PiP preview smoothness is blocker number one.

If PiP preview remains jumpy or reseek-heavy, the UI is not considered usable even if the rest of the shell is wired.
