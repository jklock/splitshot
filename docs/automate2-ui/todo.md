# Automate2 UI Todo

## P0 Baseline Guardrails

- [ ] `[UI-only]` Re-prove the `v1.0.5` Windows export-font path stays intact
- [ ] `[UI-only]` Re-prove packaged/test flows still validate `docs/Clip1.MP4`
- [ ] `[UI-only]` Keep browser preview font stacks aligned to the released Windows-safe families

## P0 UI Blockers

- [ ] `[UI-only]` Fix PiP playback smoothness first
- [ ] `[UI-only]` Implement Landing Page
- [ ] `[UI-only]` Replace the flat shell rail with the four-surface model
- [ ] `[UI-only]` Keep legacy stage-edit behavior stable while the shell changes

## P1 UI-Enabling Support Work

- [ ] `[Narrow backend support required]` Persist stage clips and clip-local angle/audio/cut state
- [ ] `[Narrow backend support required]` Add dedicated stage-clip read route
- [ ] `[Narrow backend support required]` Add dedicated angle-director plan read route
- [ ] `[Narrow backend support required]` Add landing page API routes
- [ ] `[Narrow backend support required]` Add analytics API routes
- [ ] `[Narrow backend support required]` Add archive API routes
- [ ] `[Narrow backend support required]` Keep `/api/state` summary-oriented and move heavy reads to dedicated calls

## P1 Shell And Navigation

- [ ] `[UI-only]` Add top-level surface switcher
- [ ] `[UI-only]` Add persistent context header
- [ ] `[UI-only]` Rehome legacy tool panes under the correct surface
- [ ] `[UI-only]` Define empty/loading/error/stale/unresolved states
- [ ] `[UI-only]` Implement Landing Page
- [ ] `[UI-only]` Implement recent activity on Landing Page
- [ ] `[UI-only]` Implement quick-start shortcuts

## P1 Stage Video Edit

- [ ] `[UI-only]` Add output-profile manager with preview
- [ ] `[UI-only]` Add profile CRUD UX
- [ ] `[UI-only]` Add retained-review source selection
- [ ] `[UI-only]` Add Trim Dead Time, Shot Data on Screen, Video Shape, Opening Title, Your Logo, Keep Shooter in Frame editors
- [ ] `[UI-only]` Add render-plan and render-result state
- [ ] `[UI-only]` Add Smart Angle Switching editor
- [ ] `[UI-only]` Add Line Up Angles controls
- [ ] `[UI-only]` Add Camera Jobs editor
- [ ] `[UI-only]` Add Audio Balance controls
- [ ] `[UI-only]` Add Override Smart Cuts editor
- [ ] `[UI-only]` Add multi-track waveform
- [ ] `[UI-only]` Add color-coded segments

## P1 Match Video Edit

- [ ] `[UI-only]` Add workspace lifecycle UI
- [ ] `[UI-only]` Add stage grid and status UX
- [ ] `[UI-only]` Add drag-and-drop reordering
- [ ] `[UI-only]` Add shared-default editor
- [ ] `[UI-only]` Add stage-override editor
- [ ] `[UI-only]` Add stage open/return UX
- [ ] `[UI-only]` Add Setup Once, Apply Everywhere workflow
- [ ] `[UI-only]` Add batch export queue with progress
- [ ] `[UI-only]` Add Match Recap UI
- [ ] `[UI-only]` Add Stage Composite UI

## P1 Performance Library

- [ ] `[UI-only]` Add summary tiles
- [ ] `[UI-only]` Add record list with filter/search/sort
- [ ] `[UI-only]` Add selected-record detail panel
- [ ] `[UI-only]` Add proxy actions
- [ ] `[UI-only]` Add reopen actions for stage/workspace
- [ ] `[UI-only]` Add analytics dashboard with charts
- [ ] `[UI-only]` Add personal bests display
- [ ] `[UI-only]` Add outlier highlighting
- [ ] `[UI-only]` Add tag editor
- [ ] `[UI-only]` Add notes editor
- [ ] `[UI-only]` Add export library data actions

## P1 Proof

- [ ] `[UI-only]` Run targeted UI suites
- [ ] `[UI-only]` Prove PiP performance truth gate
- [ ] `[UI-only]` Prove browser E2E flows
- [ ] `[Deferred until UI flows exist]` Prove packaged automation flows
- [ ] `[UI-only]` Re-check release-note/changelog wording only if shipping
