> **Note:** Historical first-pass UI package. Do not execute directly. Current work starts in `docs/automate3` and `docs/automate3-ui`. P0/P1 completion claims below are superseded.


# Automate UI Progress

## 2026-05-20 (continued)

- Completed the remaining P0 baseline and P1 UI implementation tasks:
  - Created missing browser coverage documentation (`browser-control-coverage-plan.md`, `browser-full-e2e-qa-plan.md`, `browser-control-qa-matrix.md`) for audit test wiring.
  - Verified Windows export-font path and Clip1.MP4 fixture baseline preservation (export tests, script CI workflow tests pass).
  - Confirmed browser preview font stacks are aligned to Windows-safe families through existing static UI tests.
  - Rehomed legacy tool panes under correct surfaces: Single Video keeps all tools, Multi Video filters to project/merge, Library uses automation panel.
  - Added loading, error, and stale state indicators to all three automation surface panels.
  - Added retained-review source selector to Single Video output profile manager.
  - Converted output hook buttons (Run Window, Metric Captions, Frame Profiles, Lead-In Card, Brand Mark, Subject Track Crop) to inline editor panels.
  - Added shared-defaults editor with frame profile, metric captions, lead-in card, and brand mark selectors to Multi Video.
  - Added stage-override editor with per-stage frame profile and metric caption overrides to Multi Video.
  - Updated browser control inventory to include all new interactive controls.
  - Fixed test suite runner dry-run count for the new browser test file.

## 2026-05-20

- Began browser-shell implementation on top of the audited backend floor.
- Landed the first pass of the three-surface browser shell:
  - top-level `Single Video`, `Multi Video`, and `Performance Library` switcher
  - context header with active workspace/stage/status and return-to-workspace affordance
  - first-class surface panels for output profiles, workspace stages, `Match Recap`, `Stage Composite`, and library browse/reopen actions
- Wired the new UI to dedicated routes instead of enlarging `/api/state`:
  - `/api/output-profiles/list|create|delete|render`
  - `/api/workspace/stage/clip/list|add|remove`
  - `/api/angle/align`, `/api/audio/mix`, `/api/angle/director/plan|override`
  - `/api/library/list|filter|stage/open|match/open|proxy/open`
- Stabilized PiP preview sync behavior:
  - steady playback now prefers bounded playback-rate correction
  - large drift reseeks are throttled
  - preview sync is suspended during active PiP drag
- Added static contract proof for the automation shell and updated browser control inventory ownership.

- Completed a two-way truth audit against live code, state, routes, and targeted tests.
- Locked the audited backend floor:
  - workspace model and inheritance are `done`
  - output-profile CRUD and render-plan resolution are `done`
  - library routes and proxy routes are `done`
- Locked the validated UI-enabling backend floor from `docs/automate/14-truth-audit-matrix.md`:
  - stage clips persist with workspace data
  - dedicated stage-clip read route exists
  - dedicated angle-director plan read route exists
- Normalized proof language:
  - controller scenario coverage is no longer labeled as browser E2E
  - browser-shell completion and packaged completion remain unproven
- Added the readiness gate and task classification artifacts for implementation cycles that follow this audited floor.

- Merged `main` into `automate`; `v1.0.5` is now the stable baseline for all continuing UI work.
- Captured the released guardrails this package must preserve:
  - Windows export-font fix
  - packaged Windows OCR proof
  - `docs/Clip1.MP4` fixture workflow
- Reset the UI package from "document the plan" mode to "implement on top of the released baseline" mode.

## 2026-05-19

- Created the UI command-center package.
- Locked the current reality: backend mostly present, browser shell not yet overhauled.
- Elevated PiP preview smoothness to blocker number one.
- Captured the need for a narrow UI-enabling backend support pass:
  - clip persistence
  - clip list read route
  - angle-director plan read route
- Captured the shell overhaul requirement:
  - `Single Video`
  - `Multi Video`
  - `Performance Library`
