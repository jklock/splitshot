# Gap Analysis

## Starting State

The repository started with only `Directions.md` and no executable project, dependencies, code, tests, or documentation beyond the spec.

## Gaps To Close

### Application Shell

- Missing Python project metadata
- Missing dependency management
- Missing desktop UI bootstrap

### Media Pipeline

- Missing FFmpeg probe wrappers
- Missing audio extraction
- Missing thumbnail generation
- Missing export pipeline

### Feature Logic

- Missing detection logic
- Missing timing calculations
- Missing merge layout calculations
- Missing scoring and hit-factor logic
- Missing overlay rendering

### Interaction Layer

- Missing waveform editor
- Missing preview overlay layer
- Missing project controls
- Missing dialogs and background workers

### Persistence

- Missing project bundle format
- Missing settings storage
- Missing recent/saved project handling

### Validation

- Missing synthetic media fixtures
- Missing unit tests
- Missing UI interaction tests
- Missing parity audit

## Closure Status

1. Package layout, dependency manifest, and planning docs: complete
2. Domain models and settings with explicit defaults: complete
3. FFmpeg wrappers and deterministic analysis: complete
4. Waveform editing and split computation: complete
5. Project save/load and unsaved-state tracking: complete
6. Merge, overlay, and scoring behavior: complete
7. MP4 export with crop and layout handling: complete
8. Feature-focused tests and synthetic fixtures: complete
9. Parity audit: complete

## Current Tradeoffs

- The detector is deterministic and pluggable rather than model-backed. This preserves the required automatic workflow and manual correction path while keeping the implementation local and simple.
- Export and analysis run synchronously with progress feedback. This keeps the feature path correct and auditable; worker-thread execution can be added later without changing behavior.
