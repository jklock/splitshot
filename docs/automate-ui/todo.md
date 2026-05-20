# Automate UI Todo

## P0 Baseline Guardrails

- [ ] Re-prove the `v1.0.5` Windows export-font path stays intact
- [ ] Re-prove packaged/test flows still validate `docs/Clip1.MP4`
- [ ] Keep browser preview font stacks aligned to the released Windows-safe families

## P0 UI Blockers

- [ ] Fix PiP playback smoothness first
- [ ] Replace the flat shell rail with the three-surface model
- [ ] Keep legacy stage-edit behavior stable while the shell changes

## P1 UI-Enabling Support Work

- [ ] Persist stage clips and clip-local angle/audio/cut state
- [ ] Add dedicated stage-clip read route
- [ ] Add dedicated angle-director plan read route
- [ ] Keep `/api/state` summary-oriented and move heavy reads to dedicated calls

## P1 Shell And Navigation

- [ ] Add top-level surface switcher
- [ ] Add persistent context header
- [ ] Rehome legacy tool panes under the correct surface
- [ ] Define empty/loading/error/stale/unresolved states

## P1 Single Video

- [ ] Add output-profile manager
- [ ] Add profile CRUD UX
- [ ] Add retained-review source selection
- [ ] Add Run Window, Metric Captions, Frame Profiles, Lead-In Card, Brand Mark, Subject Track Crop editors
- [ ] Add render-plan and render-result state

## P1 Multi Video

- [ ] Add workspace lifecycle UI
- [ ] Add stage grid and status UX
- [ ] Add shared-default editor
- [ ] Add stage-override editor
- [ ] Add stage open/return UX
- [ ] Add Match Recap UI
- [ ] Add Stage Composite UI

## P1 Performance Library

- [ ] Add summary tiles
- [ ] Add record list with filter/search/sort
- [ ] Add selected-record detail panel
- [ ] Add proxy actions
- [ ] Add reopen actions for stage/workspace

## P1 Proof

- [ ] Run targeted UI suites
- [ ] Prove PiP performance truth gate
- [ ] Prove browser E2E flows
- [ ] Prove packaged automation flows
- [ ] Re-check release-note/changelog wording only if shipping
