# MASTER

`docs/automate3-ui/spec.md` is the single exhaustive UI build authority for Automate3.

## Standing Rules

1. Views must be separate frontends.
2. The app must feel integrated.
3. Stage Video Edit remains the deep editor.
4. Match Video Edit is a first-class workspace frontend.
5. Performance Library is a first-class historical analytics frontend.
6. Shotcut informs quality and information architecture, not branding.
7. Visual proof is mandatory.
8. Empty and loaded states are both required.
9. No placeholder-complete claims.
10. Do not modify `flutter_app/`. It is isolated to its own branch/worktree and must be treated as ignored branch-local work on `main`.
11. Follow `artifacts/dom-restructure-plan.md`, `artifacts/file-change-map.md`, `artifacts/visual-design-contract.md`, and `artifacts/test-preservation-contract.md` before editing UI code.

## Design Principles

- Professional density, not clutter.
- Preview/timeline/inspector hierarchy must be obvious.
- Navigation must be predictable.
- Complex workflows need preview, confirmation, progress, and recovery.
- UI labels must be SplitShot-native and user-facing.
- Controls must be wired, disabled with a reason, or absent.

## Current Status

Automate3 UI is planned, not implemented. Phase 0 must regenerate screenshot proof for the active branch before implementation begins.
