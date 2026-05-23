> **Note:** Historical first-pass UI package. Do not execute directly. Current work starts in `docs/automate3` and `docs/automate3-ui`.


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

- Backend contract and audited status: [../automate/14-truth-audit-matrix.md](../automate/14-truth-audit-matrix.md)
- UI build spec: [spec.md](spec.md)
- PiP blocker track: [tracks/01-pip-performance-and-merge-editor.md](tracks/01-pip-performance-and-merge-editor.md)
- Released baseline floor: `main` at `v1.0.5` after the 2026-05-20 merge

## Standing Rule

PiP preview smoothness is blocker number one.

If PiP preview remains jumpy or reseek-heavy, the UI is not considered usable even if the rest of the shell is wired.
