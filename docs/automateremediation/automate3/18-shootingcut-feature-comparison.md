# ShootingCut Feature Comparison

> **Purpose:** Map every ShootingCut feature to its SplitShot-native equivalent to guide UI implementation priorities.
>
> **Rule:** Do not copy ShootingCut UI names into SplitShot controls unless already accepted in docs.

## Comparison Matrix

| ShootingCut Feature | SplitShot-Native Name | Surface | Status | Required Backend Route | Required UI Control | Required Test | Required Screenshot |
|---|---|---|---|---|---|---|---|
| Smart Audio Analysis | Detection Review (timing/segments) | Stage | implemented | `/api/analysis/shotml-settings` | Detection threshold, event markers | `test_browser_control.py` | loaded-stage.png |
| Auto Trim | Run Window / Trim Dead Time | Stage | wired-needs-proof | `/api/output-profiles/update` | Trim Dead Time hook | `test_output_profile_update_persists_hook_settings` | loaded-stage.png |
| Performance Subtitles | Metric Captions / Shot Data on Screen | Stage | wired-needs-proof | `/api/output-profiles/update` | Shot Data on Screen hook | `test_output_profile_update_persists_hook_settings` | loaded-stage.png |
| Split Sync | Angle Align / PiP sync | Stage | implemented | `/api/angle/align`, `/api/sync` | PiP controls, align button | `test_browser_interactions.py` | pip-multi-angle-loaded.png |
| Stage Mix | Stage Composite / Angle Director | Stage | planned-not-wired | `/api/angle/director/plan`, `/api/workspace/stage/clip/*` | Clip editor, angle preview | `test_browser_control.py` | pip-multi-angle-loaded.png |
| Merge | Match Recap | Match | wired-needs-proof | `/api/workspace/recap/render` | Recap builder | `test_merge_export_contracts.py` | loaded-match.png |
| Portrait Tracking | Subject Track Crop | Stage | wired-needs-proof | `/api/output-profiles/update` | Keep Shooter in Frame hook | `test_output_profile_update_persists_hook_settings` | loaded-stage.png |
| Intro Title Cards | Lead-In Card | Stage | wired-needs-proof | `/api/output-profiles/update` | Opening Title hook | `test_output_profile_update_persists_hook_settings` | loaded-stage.png |
| Custom Watermarks | Brand Mark | Stage | wired-needs-proof | `/api/output-profiles/update` | Your Logo hook | `test_output_profile_update_persists_hook_settings` | loaded-stage.png |
| Multi-platform share | Export profiles/presets | Match | wired-needs-proof | `/api/workspace/export` | Export button, preset selector | `test_merge_export_contracts.py` | export-progress.png |
| - | Shared Defaults | Match | wired-needs-proof | `/api/workspace/defaults` | Defaults editor | `test_workspace_flows.py` | match-loaded.png |
| - | Stage Overrides | Match | wired-needs-proof | `/api/workspace/stage/override` | Override editor | `test_workspace_flows.py` | match-loaded.png |
| - | Setup Once Apply Everywhere | Match | wired-needs-proof | `/api/workspace/apply-from-first`, `/api/workspace/apply-from-first/preview` | Setup Once button, preview panel | `test_browser_control.py` | match-loaded.png |
| - | Batch Export | Match | wired-needs-proof | `/api/workspace/export` | Batch select, progress bar | `test_merge_export_contracts.py` | export-progress.png |
| - | Performance Library | Library | wired-needs-proof | `/api/library/*` | Search, table, detail, tags, notes | `test_library_backend_contracts.py` | library-loaded.png |
| - | Library Analytics | Library | wired-needs-proof | `/api/library/analytics/*` | Trend charts, discipline breakdown | `test_browser_control.py` | library-loaded.png |

## Status Key

- **implemented**: Visible UI control exists, correct registered route exists, controller behavior works, persistence/state update works, behavioral test exists, proof screenshot exists
- **wired-needs-proof**: UI control exists, route exists, but controller behavior, persistence, test, and/or screenshot are incomplete
- **planned-not-wired**: Feature is planned but backend route is missing or UI control is not wired
- **deferred**: Not in current scope
- **rejected**: Not planned

## Routing Gaps

No known ShootingCut-aligned UI call is currently unregistered. The remaining export and recap gaps are behavioral proof gaps:

| Route | SplitShot Feature | Current Status |
|---|---|---|
| `/api/workspace/recap/render` | Match Recap rendering | registered and wired; no rendered recap artifact yet |
| `/api/workspace/export` | Workspace export | registered and wired; no real file-export proof yet |

## Backend Gaps

See `17-backend-gap-implementation-plan.md` for the 6 known backend gaps that block complete UI wiring.

## Visual Proof Requirements

| Screenshot | Shows | Status |
|---|---|---|
| `00-landing-empty.png` | Landing without recent activity | Not captured with state predicates |
| `01-landing-returning.png` | Landing with recent activity | Not captured with state predicates |
| `02-stage-empty.png` | Stage without media | Not captured with state predicates |
| `loaded-stage.png` | Stage with media, waveform, tools | Captured with state predicates |
| `04-stage-workspace-return.png` | Stage opened from match workspace | Not captured with state predicates |
| `05-match-empty.png` | Match without stages | Not captured with state predicates |
| `loaded-match.png` | Match with stages in grid | Captured with state predicates |
| `07-library-empty.png` | Library without records | Not captured with state predicates |
| `loaded-library.png` | Library with records | Captured with state predicates |
| `09-pip-multi-angle-loaded.png` | PiP/multi-angle in stage | Not captured with state predicates |
| `10-export-progress.png` | Export in progress | Not captured with state predicates |
| `11-export-complete.png` | Export completed | Not captured with state predicates |
| `contact-sheet-final.png` | Loaded contact sheet | Captured with state predicates |
| `comparison-sheet-shootingcut.png` | Side-by-side comparison | Not captured with state predicates |
