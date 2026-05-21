# Remediation and Completion Plan

This document tracks known gaps and the plan to close them.

## Known Gaps from v1.0.5

### Backend

1. Stage clip persistence is mutation-only
   - **Status**: partial
   - **Fix**: Add stage clip read route and persistence
   - **Owner**: Backend

2. Angle director plan read route missing
   - **Status**: missing
   - **Fix**: Add dedicated route
   - **Owner**: Backend

3. Library analytics not implemented
   - **Status**: missing
   - **Fix**: Add analytics models and computation
   - **Owner**: Backend

4. Archive pipeline not implemented
   - **Status**: missing
   - **Fix**: Add compressed video generation
   - **Owner**: Backend

### UI

1. Landing Page not implemented
   - **Status**: missing
   - **Fix**: Implement landing page UI
   - **Owner**: UI

2. Setup Once Apply Everywhere not implemented
   - **Status**: missing
   - **Fix**: Implement workflow UI
   - **Owner**: UI

3. Multi-track waveform not implemented
   - **Status**: missing
   - **Fix**: Extend waveform component
   - **Owner**: UI

4. Color-coded segments not implemented
   - **Status**: missing
   - **Fix**: Add segment detection and rendering
   - **Owner**: UI

5. Performance Library analytics UI not implemented
   - **Status**: missing
   - **Fix**: Add charts and dashboards
   - **Owner**: UI

### Proof

1. Packaged automation proof deferred
   - **Status**: deferred
   - **Fix**: Run packaged proof scripts
   - **Owner**: QA

2. PiP playback proof not packaged
   - **Status**: deferred
   - **Fix**: Add packaged playback tests
   - **Owner**: QA

## Remediation Order

1. Close backend gaps (persistence, routes, analytics)
2. Close UI gaps (landing page, workflow, waveform)
3. Implement new v2 features
4. Run full proof suite
5. Fix regressions
6. Release

## Completion Criteria

All gaps closed when:
- every `missing` item has implementation and proof
- every `partial` item is `done`
- every `deferred` item is either done or explicitly rejected
- full test suite passes
- no P0 bugs
