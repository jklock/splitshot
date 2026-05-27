# Feature Inventory

This document inventories every feature required for SplitShot v2, derived from:

- competitor screenshot analysis
- existing SplitShot capabilities
- user requirements for layman-friendly UX
- Performance Library as a killer feature

## Decision Vocabulary

- `adopt` — implement in SplitShot because it fits the product directly
- `reframe` — keep the user outcome but fit it to SplitShot's identity
- `defer` — valuable, but not for the first delivery wave
- `reject` — not aligned with SplitShot's product direction

## Feature Categories

### 1. Landing Page

| Feature | Source | Decision | SplitShot Home | Notes |
|---------|--------|----------|----------------|-------|
| Three large entry cards | User requirement | adopt | Landing Page | Stage Edit, Match Edit, Library |
| Recent activity list | User requirement | adopt | Landing Page | Show last 5-10 opened items |
| Quick-start shortcuts | User requirement | adopt | Landing Page | "New Stage", "New Match" |
| Activity thumbnails | User requirement | adopt | Landing Page | Proxy thumbnails for recent items |
| Welcome state for first launch | User requirement | adopt | Landing Page | Friendly onboarding message |

### 2. Stage Video Edit

| Feature | Source | Decision | SplitShot Home | Notes |
|---------|--------|----------|----------------|-------|
| Primary video import | Existing | preserve | Stage Video Edit | Already core |
| Beep and shot detection | Existing | preserve | Stage Video Edit | Already core |
| Manual timing correction | Existing | preserve | Stage Video Edit | Already core |
| Scoring and PracticeScore context | Existing | preserve | Stage Video Edit | Already core |
| Overlays, review text, markers | Existing | preserve | Stage Video Edit | Already core |
| Metrics computation and display | Existing | preserve | Stage Video Edit | Already core |
| ShotML detection pipeline | Existing | preserve | Stage Video Edit | Already core |
| Waveform editor with shot markers | Existing | preserve | Stage Video Edit | Already core |
| PiP / secondary video | Existing | preserve | Stage Video Edit | Already core |
| Auto Trim (trim dead time) | Competitor | reframe | Stage Video Edit | Rename to "Trim Dead Time" |
| Performance subtitles / metric captions | Competitor | reframe | Stage Video Edit | Rename to "Shot Data Overlay" |
| Export ratios / frame profiles | Competitor | reframe | Stage Video Edit | Rename to "Video Shape" |
| Portrait tracking / subject track crop | Competitor | reframe | Stage Video Edit | Rename to "Keep Shooter in Frame" |
| Intro title cards | Competitor | reframe | Stage Video Edit | Rename to "Opening Title" |
| Custom watermarks / brand mark | Competitor | reframe | Stage Video Edit | Rename to "Your Logo" |
| Run Window (trim with padding) | Existing plan | adopt | Stage Video Edit | Keep SplitShot name |
| Output profile manager | Existing plan | adopt | Stage Video Edit | Keep SplitShot name |
| Retained review source selection | Existing plan | adopt | Stage Video Edit | Keep SplitShot name |
| One-run many-output variants | Existing plan | adopt | Stage Video Edit | Keep SplitShot name |
| Stage Mix (multi-angle auto-cut) | Competitor | reframe | Stage Video Edit | Rename to "Smart Angle Switching" |
| Split Sync (angle alignment) | Competitor | reframe | Stage Video Edit | Rename to "Line Up Angles" |
| Camera role labeling | Competitor | reframe | Stage Video Edit | Rename to "Camera Jobs" |
| Per-clip audio control | Competitor | reframe | Stage Video Edit | Rename to "Audio Balance" |
| Auto-cut override flow | Competitor | reframe | Stage Video Edit | Rename to "Override Smart Cuts" |

### 3. Match Video Edit

| Feature | Source | Decision | SplitShot Home | Notes |
|---------|--------|----------|----------------|-------|
| Match workspace creation | Existing plan | adopt | Match Video Edit | Keep SplitShot name |
| Stage addition and ordering | Existing plan | adopt | Match Video Edit | Keep SplitShot name |
| Shared settings across stages | Existing plan | adopt | Match Video Edit | Keep SplitShot name |
| Stage-local overrides | Existing plan | adopt | Match Video Edit | Keep SplitShot name |
| Stage open/return to workspace | Existing plan | adopt | Match Video Edit | Keep SplitShot name |
| Match Recap (many-stage output) | Existing plan | adopt | Match Video Edit | Keep SplitShot name |
| Stage Composite (one-stage multi-clip) | Existing plan | adopt | Match Video Edit | Keep SplitShot name |
| **Setup on first video, apply to rest** | User requirement | adopt | Match Video Edit | NEW: core workflow |
| Match status dashboard | User requirement | adopt | Match Video Edit | Visual overview of all stages |
| Per-stage completeness indicators | User requirement | adopt | Match Video Edit | Icons for ready/review/missing |
| Batch export with progress | User requirement | adopt | Match Video Edit | Export all stages at once |
| Stage reordering via drag-and-drop | User requirement | adopt | Match Video Edit | Intuitive match building |
| Match-level scoring summary | User requirement | adopt | Match Video Edit | Total match stats |
| PracticeScore import for entire match | User requirement | adopt | Match Video Edit | Import once, apply to stages |
| Duplicate stage detection | User requirement | adopt | Match Video Edit | Warn if same video added twice |
| Auto-naming from stage metadata | User requirement | adopt | Match Video Edit | Derive names from PracticeScore |
| Match preview / recap preview | User requirement | adopt | Match Video Edit | Preview before rendering |
| Result cards between stages | Existing plan | adopt | Match Video Edit | Keep SplitShot name |
| Audio Mix Lanes | Existing plan | adopt | Match Video Edit | Keep SplitShot name |

### 4. Performance Library

| Feature | Source | Decision | SplitShot Home | Notes |
|---------|--------|----------|----------------|-------|
| Historical metric browsing | Existing plan | adopt | Performance Library | Keep SplitShot name |
| Cross-match comparisons | Existing plan | adopt | Performance Library | Keep SplitShot name |
| Search and filtering | Existing plan | adopt | Performance Library | Keep SplitShot name |
| Retained proxy playback | Existing plan | adopt | Performance Library | Keep SplitShot name |
| Jump to editor | Existing plan | adopt | Performance Library | Keep SplitShot name |
| **PracticeScore output archive** | User requirement | adopt | Performance Library | NEW: store CSVs |
| **Compressed video archive** | User requirement | adopt | Performance Library | NEW: small review videos |
| **Performance trends and charts** | User requirement | adopt | Performance Library | NEW: visual analytics |
| **Stage-to-stage comparison** | User requirement | adopt | Performance Library | NEW: side-by-side metrics |
| **Match leaderboard view** | User requirement | adopt | Performance Library | NEW: how did I rank? |
| **Personal bests tracking** | User requirement | adopt | Performance Library | NEW: highlight PBs |
| **Discipline filtering** | User requirement | adopt | Performance Library | USPSA vs IPSC vs IDPA |
| **Date range filtering** | User requirement | adopt | Performance Library | Time-based search |
| **Export library data** | User requirement | adopt | Performance Library | CSV, JSON, PDF reports |
| **Tagging and notes** | User requirement | adopt | Performance Library | User-added metadata |
| **Proxy regeneration** | Existing plan | adopt | Performance Library | Keep SplitShot name |
| **Offline availability** | User requirement | adopt | Performance Library | All data local |
| **Backup and restore** | User requirement | adopt | Performance Library | Export/import library bundle |

### 5. Export and Output

| Feature | Source | Decision | SplitShot Home | Notes |
|---------|--------|----------|----------------|-------|
| Single stage export | Existing | preserve | Stage Video Edit | Already core |
| Batch stage export | Existing plan | adopt | Match Video Edit | Export all stages |
| Match recap export | Existing plan | adopt | Match Video Edit | One video for whole match |
| Stage composite export | Existing plan | adopt | Match Video Edit | Multi-angle for one stage |
| Social ratios (9:16, 1:1, etc.) | Competitor | reframe | Both editors | Rename to "Video Shape" |
| Title cards | Competitor | reframe | Both editors | Rename to "Opening Title" |
| Watermarks | Competitor | reframe | Both editors | Rename to "Your Logo" |
| Metric overlays | Competitor | reframe | Both editors | Rename to "Shot Data on Screen" |
| Tracked crop for portrait | Competitor | reframe | Both editors | Rename to "Keep Shooter in Frame" |
| Export progress and queue | User requirement | adopt | Both editors | Show what's rendering |
| Export presets / recipes | User requirement | adopt | Both editors | Save favorite settings |
| Direct file output (no cloud) | User requirement | adopt | Both editors | Local-first |

### 6. Waveform and Timeline

| Feature | Source | Decision | SplitShot Home | Notes |
|---------|--------|----------|----------------|-------|
| Audio waveform display | Existing | preserve | Stage Video Edit | Already core |
| Shot markers on waveform | Existing | preserve | Stage Video Edit | Already core |
| Beep marker on waveform | Existing | preserve | Stage Video Edit | Already core |
| Drag to move shots | Existing | preserve | Stage Video Edit | Already core |
| Zoom and pan waveform | Existing | preserve | Stage Video Edit | Already core |
| Multi-track waveform (for angles) | Competitor | adopt | Stage Video Edit | One track per angle |
| Color-coded regions (Move/Static/Long) | Competitor | reframe | Stage Video Edit | Auto-labeled segments |
| Auto-cut visualization | Competitor | reframe | Stage Video Edit | Show where cuts will happen |
| Timeline scrubbing | Existing | preserve | Stage Video Edit | Already core |
| Playhead sync across angles | Competitor | adopt | Stage Video Edit | All angles follow playhead |

### 7. Analysis and Detection

| Feature | Source | Decision | SplitShot Home | Notes |
|---------|--------|----------|----------------|-------|
| ShotML shot detection | Existing | preserve | Stage Video Edit | Already core |
| Beep detection | Existing | preserve | Stage Video Edit | Already core |
| Confidence scoring | Existing | preserve | Stage Video Edit | Already core |
| Manual shot addition | Existing | preserve | Stage Video Edit | Already core |
| Shot deletion | Existing | preserve | Stage Video Edit | Already core |
| Timing nudge controls | Existing | preserve | Stage Video Edit | Already core |
| Multi-angle sync by beep | Competitor | reframe | Stage Video Edit | "Line Up by Beep" |
| Multi-angle sync by waveform | Competitor | reframe | Stage Video Edit | "Line Up by Sound" |
| Person detection for tracking | Competitor | defer | Stage Video Edit | Complex; can be manual first |

### 8. UI/UX Polish

| Feature | Source | Decision | SplitShot Home | Notes |
|---------|--------|----------|----------------|-------|
| Dark theme | Existing | preserve | All | SplitShot's identity |
| Resizable panels | Existing | preserve | All | Already core |
| Keyboard shortcuts | Existing | preserve | All | Already core |
| Responsive layout | Existing | preserve | All | Already core |
| Loading states | User requirement | adopt | All | Clear progress indicators |
| Empty states | User requirement | adopt | All | Friendly messages when no data |
| Error states | User requirement | adopt | All | Helpful error recovery |
| Onboarding hints | User requirement | adopt | All | First-time user guidance |
| Tooltips and help | User requirement | adopt | All | Explain what things do |
| Undo/redo | Existing | preserve | All | Already core |
| Autosave | Existing | preserve | All | Already core |

## Out of Scope

These should not steer product architecture:

- Apple-native UX parity (we are cross-platform)
- iCloud/Photos as storage backbone (we are local-first)
- Social-first sharing as core promise (analysis-first)
- Cloud rendering or upload
- Real-time collaboration
- Mobile app
- AI-generated content (beyond detection)

## Implementation Ownership

### Landing Page

- recent activity tiles
- entry point cards
- quick-start shortcuts
- welcome/onboarding state

### Stage Video Edit

- all existing stage editing tools
- output profile manager
- Trim Dead Time
- Shot Data Overlay
- Video Shape
- Keep Shooter in Frame
- Opening Title
- Your Logo
- Smart Angle Switching
- Line Up Angles
- Camera Jobs
- Audio Balance
- Override Smart Cuts

### Match Video Edit

- match workspace lifecycle
- stage grid with status
- shared settings and overrides
- Setup Once, Apply Everywhere workflow
- batch export with progress
- Match Recap builder
- Stage Composite builder
- match-level scoring summary
- PracticeScore match import
- drag-and-drop stage ordering

### Performance Library

- summary tiles and dashboard
- filter/search/sort
- record table and detail view
- proxy playback
- PracticeScore archive
- compressed video archive
- performance trends and charts
- stage-to-stage comparison
- match leaderboard
- personal bests
- tagging and notes
- export library data
- backup and restore

## Required Proof Mapping

Every `adopt` or `reframe` row in this table must map to:

- one owning spec in `docs/automate2`
- one SplitShot-native implementation label
- one test or proof owner in [10-acceptance-and-proof.md](10-acceptance-and-proof.md)

No feature may be marked `done` in the final audit unless that mapping exists.
