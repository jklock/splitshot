> **Note:** Automate2 is a historical feature-inventory package. Current implementation status lives in `docs/automate3/14-truth-audit-matrix.md`.


# Roadmap and Task Plan

This document defines the implementation order and task breakdown for SplitShot v2.

## Phase 1: Foundation (Weeks 1-2)

### Landing Page
- [ ] Design landing page layout
- [ ] Implement recent activity API
- [ ] Implement landing page UI
- [ ] Wire entry points to editors

### Data Model Updates
- [ ] Add `first_stage_snapshot` to workspace model
- [ ] Add `archive_id` to output profile
- [ ] Add `inherited_from_first` to stage entry
- [ ] Add analytics models
- [ ] Add tag and note models

### API Routes
- [ ] Add `/api/landing/recent`
- [ ] Add `/api/workspace/apply-from-first`
- [ ] Add `/api/workspace/apply-from-first/preview`
- [ ] Add library analytics routes
- [ ] Add library export routes
- [ ] Add library backup/restore routes

## Phase 2: Stage Video Edit Enhancements (Weeks 3-4)

### Output Profile Manager
- [ ] Implement profile CRUD UI
- [ ] Implement profile preview (trim, crop, title, watermark)
- [ ] Implement retained review source selection

### Waveform Enhancements
- [ ] Implement multi-track waveform
- [ ] Implement color-coded segments
- [ ] Implement auto-cut visualization

### Multi-Angle Features
- [ ] Implement Camera Jobs (angle roles)
- [ ] Implement Line Up Angles (sync)
- [ ] Implement Audio Balance (mix lanes)
- [ ] Implement Smart Angle Switching (auto-cut)
- [ ] Implement Override Smart Cuts (cut override)

## Phase 3: Match Video Edit (Weeks 5-6)

### Stage Grid
- [ ] Implement stage grid with status badges
- [ ] Implement drag-and-drop reordering
- [ ] Implement batch export with progress

### Setup Once, Apply Everywhere
- [ ] Implement first-stage snapshot
- [ ] Implement apply preview
- [ ] Implement apply execution
- [ ] Implement reset to shared

### Match Outputs
- [ ] Implement Match Recap builder
- [ ] Implement Stage Composite builder
- [ ] Implement result cards

## Phase 4: Performance Library (Weeks 7-8)

### Browsing and Playback
- [ ] Implement summary tiles
- [ ] Implement record table
- [ ] Implement proxy playback
- [ ] Implement jump to editor

### Analytics
- [ ] Implement trend charts
- [ ] Implement personal best tracking
- [ ] Implement outlier detection
- [ ] Implement stage-to-stage comparison

### Data Management
- [ ] Implement tagging
- [ ] Implement notes
- [ ] PracticeScore archiving
- [ ] Compressed video archiving
- [ ] Export to CSV/JSON
- [ ] Backup and restore

## Phase 5: Polish and Integration (Weeks 9-10)

### UI/UX Polish
- [ ] Implement onboarding hints
- [ ] Implement tooltips and help
- [ ] Implement loading/empty/error states
- [ ] Implement responsive layout refinements

### Performance
- [ ] Optimize library queries
- [ ] Optimize waveform rendering
- [ ] Optimize proxy generation
- [ ] Optimize analytics computation

### Testing
- [ ] Run full test suite
- [ ] Run browser E2E tests
- [ ] Run performance benchmarks
- [ ] Fix regressions

## Phase 6: Release (Week 11)

### Documentation
- [ ] Update user guide
- [ ] Update troubleshooting
- [ ] Write release notes

### Release
- [ ] Version bump
- [ ] Changelog update
- [ ] Release notes extraction
- [ ] Tag and push

## Task Dependencies

```
Landing Page
  -> recent activity API
  -> entry point wiring

Data Model
  -> first_stage_snapshot
  -> archive_id
  -> analytics models

Stage Video Edit
  -> output profiles
  -> waveform enhancements
  -> multi-angle features

Match Video Edit
  -> stage grid
  -> Setup Once Apply Everywhere
  -> match outputs
  -> depends on Stage Video Edit output profiles

Performance Library
  -> browsing
  -> analytics
  -> data management
  -> depends on all editor features

Polish
  -> UI/UX
  -> performance
  -> testing
  -> depends on all features
```

## Risk Mitigation

- **Multi-angle sync accuracy**: fallback to manual sync if auto-sync fails
- **Performance on large libraries**: implement pagination and lazy loading
- **Archive storage size**: allow user to set retention policy
- **Browser compatibility**: test on Electron, Chrome, Firefox, Safari

## Acceptance Gates

Each phase must pass before the next begins:

1. Foundation: all API routes respond correctly, data models serialize
2. Stage Video Edit: all new features have UI and backend proof
3. Match Video Edit: workspace flows end-to-end, batch export works
4. Performance Library: library records are queryable, analytics render
5. Polish: test suite passes, no P0 bugs
6. Release: all docs updated, release notes written
