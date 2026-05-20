# Automate UI Todo

## P0 Baseline Guardrails

- [ ] `[UI-only]` Re-prove the `v1.0.5` Windows export-font path stays intact
- [ ] `[UI-only]` Re-prove packaged/test flows still validate `docs/Clip1.MP4`
- [ ] `[UI-only]` Keep browser preview font stacks aligned to the released Windows-safe families

## P0 UI Blockers

- [x] `[UI-only]` Fix PiP playback smoothness first
- [x] `[UI-only]` Replace the flat shell rail with the three-surface model
- [ ] `[UI-only]` Keep legacy stage-edit behavior stable while the shell changes

## P1 UI-Enabling Support Work

- [x] `[Narrow backend support required]` Persist stage clips and clip-local angle/audio/cut state
- [x] `[Narrow backend support required]` Add dedicated stage-clip read route
- [x] `[Narrow backend support required]` Add dedicated angle-director plan read route
- [ ] `[Narrow backend support required]` Keep `/api/state` summary-oriented and move heavy reads to dedicated calls

## P1 Shell And Navigation

- [x] `[UI-only]` Add top-level surface switcher
- [x] `[UI-only]` Add persistent context header
- [ ] `[UI-only]` Rehome legacy tool panes under the correct surface
- [ ] `[UI-only]` Define empty/loading/error/stale/unresolved states

## P1 Single Video

- [x] `[UI-only]` Add output-profile manager
- [x] `[UI-only]` Add profile CRUD UX
- [ ] `[UI-only]` Add retained-review source selection
- [ ] `[UI-only]` Add Run Window, Metric Captions, Frame Profiles, Lead-In Card, Brand Mark, Subject Track Crop editors
- [x] `[UI-only]` Add render-plan and render-result state

## P1 Multi Video

- [x] `[UI-only]` Add workspace lifecycle UI
- [x] `[UI-only]` Add stage grid and status UX
- [ ] `[UI-only]` Add shared-default editor
- [ ] `[UI-only]` Add stage-override editor
- [x] `[UI-only]` Add stage open/return UX
- [x] `[UI-only]` Add Match Recap UI
- [x] `[UI-only after backend floor validated]` Add Stage Composite UI

## P1 Performance Library

- [x] `[UI-only]` Add summary tiles
- [x] `[UI-only]` Add record list with filter/search/sort
- [x] `[UI-only]` Add selected-record detail panel
- [x] `[UI-only]` Add proxy actions
- [x] `[UI-only]` Add reopen actions for stage/workspace

## P1 Proof

- [x] `[UI-only]` Run targeted UI suites
- [x] `[UI-only]` Prove PiP performance truth gate
- [x] `[UI-only]` Prove browser E2E flows
- [ ] `[Deferred until UI flows exist]` Prove packaged automation flows
- [ ] `[UI-only]` Re-check release-note/changelog wording only if shipping
