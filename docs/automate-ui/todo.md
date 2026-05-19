# Automate UI Todo

## P0 Today

- [ ] Write the PiP sync/performance track and keep it first in execution order
- [ ] Document the shell overhaul from flat rail to three product surfaces
- [ ] Document the Single Video output-profile UI
- [ ] Document the Multi Video workspace, Match Recap, and Stage Composite UI
- [ ] Document the Performance Library UI
- [ ] Document the UI-enabling backend support pass
- [ ] Document proof, regression, and release closure

## P1 UI-Enabling Support Work

- [ ] Persist stage clips and clip-local angle/audio/cut state
- [ ] Add `POST /api/workspace/stage/clips/list`
- [ ] Add `POST /api/angle/director/plan`
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

- [ ] Define targeted UI suites
- [ ] Define PiP performance truth gate
- [ ] Define browser E2E flows
- [ ] Define packaged proof flows
- [ ] Define release-note/changelog checks
