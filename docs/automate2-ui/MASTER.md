# MASTER

`docs/automate2-ui/spec.md` is the single exhaustive UI build spec for this work.

Use the rest of the package as execution support:

- [todo.md](todo.md) for the implementation checklist
- [execution-order.md](execution-order.md) for the same-day sequence
- [outcomes.md](outcomes.md) for completion gates
- [progress.md](progress.md) for the running ledger
- `tracks/` for subsystem-specific requirements
- `artifacts/` for audit and proof matrices

## Truth Sources

- Backend contract and audited status: [../automate/14-truth-audit-matrix.md](../automate/14-truth-audit-matrix.md) and [../automate2/14-truth-audit-matrix.md](../automate2/14-truth-audit-matrix.md)
- UI build spec: [spec.md](spec.md)
- Released baseline floor: `main` at `v1.0.5` after the 2026-05-20 merge

## Standing Rules

1. **Landing Page is the front door.** If the landing page is confusing, nothing else matters.
2. **PiP preview smoothness is blocker number one.** If PiP preview remains jumpy, the UI is not usable.
3. **Setup Once, Apply Everywhere must feel magical.** If it feels like a script, it failed.
4. **Performance Library must feel like a killer feature.** If it feels like a file browser, it failed.
5. **Every label must be layman-friendly.** No jargon in the UI.

## Design Principles

1. **Clarity over density.** Better to scroll than to confuse.
2. **Preview over describe.** Show the user what will happen, don't just tell them.
3. **Progress over perfection.** Show loading states, progress bars, and completion.
4. **Forgiveness over friction.** Undo, reset, and cancel must always be available.
5. **Delight over utility.** Add small moments of polish: animations, sound effects, celebrations.
