# Acceptance and Proof

This document defines the acceptance criteria and proof requirements for SplitShot v2.

## Proof Levels

- `unit` — pytest tests for backend logic
- `browser` — pytest-browser tests for UI behavior
- `e2e` — end-to-end tests for full workflows
- `manual` — human-verified behavior
- `benchmark` — performance measurements

## Landing Page

| Criterion | Proof | Owner |
|-----------|-------|-------|
| Shows three entry points | browser | UI |
| Shows recent activity | browser | UI |
| Quick-start shortcuts work | e2e | QA |
| Responsive layout | browser | UI |
| Empty state for first launch | browser | UI |

## Stage Video Edit

| Criterion | Proof | Owner |
|-----------|-------|-------|
| All existing features preserved | unit + browser | Backend + UI |
| Trim Dead Time works | unit + browser | Backend + UI |
| Shot Data Overlay renders | unit + browser | Backend + UI |
| Output Profile CRUD | unit + browser | Backend + UI |
| Video Shape applies | unit + browser | Backend + UI |
| Opening Title renders | unit + browser | Backend + UI |
| Your Logo renders | unit + browser | Backend + UI |
| Keep Shooter in Frame (placeholder) | browser | UI |
| Multi-track waveform | browser | UI |
| Color-coded segments | unit + browser | Backend + UI |
| Line Up Angles sync | unit + e2e | Backend |
| Smart Angle Switching suggestions | unit | Backend |
| Camera Jobs assignment | browser | UI |
| Audio Balance controls | browser | UI |
| Override Smart Cuts | browser | UI |
| Retained proxy generation | unit + e2e | Backend |

## Match Video Edit

| Criterion | Proof | Owner |
|-----------|-------|-------|
| Workspace create/open/save | unit + browser | Backend + UI |
| Stage grid shows status | browser | UI |
| Drag-and-drop reordering | browser | UI |
| Shared defaults apply | unit + browser | Backend + UI |
| Stage overrides work | unit + browser | Backend + UI |
| Setup Once Apply Everywhere | e2e | QA |
| Apply preview shows correctly | browser | UI |
| Batch export with progress | e2e | QA |
| Match Recap render | unit + e2e | Backend |
| Stage Composite render | unit + e2e | Backend |
| Result cards render | unit | Backend |
| PracticeScore match import | e2e | QA |

## Performance Library

| Criterion | Proof | Owner |
|-----------|-------|-------|
| Library record creation | unit | Backend |
| Filter and search | unit + browser | Backend + UI |
| Proxy playback | browser | UI |
| Jump to editor | e2e | QA |
| Trend charts render | browser | UI |
| Personal bests tracked | unit | Backend |
| Outlier detection | unit | Backend |
| Stage-to-stage comparison | browser | UI |
| Tagging and notes | unit + browser | Backend + UI |
| CSV export | unit + e2e | Backend |
| JSON export | unit | Backend |
| Backup and restore | e2e | QA |
| PracticeScore archive | unit | Backend |
| Compressed video archive | unit | Backend |

## Cross-Cutting

| Criterion | Proof | Owner |
|-----------|-------|-------|
| Inheritance resolution (6 layers) | unit | Backend |
| Legacy project compatibility | e2e | QA |
| Windows export font policy | e2e | QA |
| PiP playback smoothness | benchmark | UI |
| Waveform rendering 60fps | benchmark | UI |
| Library query <500ms | benchmark | Backend |
| Analytics render <1s | benchmark | UI |

## Proof Artifacts

Each proof owner must produce:

- test code in `tests/`
- test results in `artifacts/test-run.json`
- coverage report in `artifacts/coverage.json`
- benchmark results in `artifacts/benchmarks.json`

## Sign-Off

Before release, the following must sign off:

- [ ] Backend lead: all unit tests pass
- [ ] UI lead: all browser tests pass
- [ ] QA lead: all e2e tests pass
- [ ] Performance lead: all benchmarks pass
- [ ] Product lead: all acceptance criteria met

## Rejection Criteria

Any of the following blocks release:

- regression in legacy project opening
- regression in Windows export font rendering
- data loss in library records
- crash during batch export
- incorrect inheritance application
- missing PracticeScore data after import
