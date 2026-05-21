# SplitShot Naming Contract

This document defines the SplitShot-native naming for all features.

## Product Surfaces

| External Name | Internal Name |
|---------------|---------------|
| Landing Page | `landing_page` |
| Stage Video Edit | `stage_video_edit` |
| Match Video Edit | `match_video_edit` |
| Performance Library | `performance_library` |

## Stage Video Edit Features

| Competitor Name | SplitShot Name |
|-----------------|----------------|
| Auto Trim | `Trim Dead Time` |
| Performance Subtitles | `Shot Data Overlay` |
| Export Ratios | `Video Shape` |
| Portrait Tracking | `Keep Shooter in Frame` |
| Intro Title Cards | `Opening Title` |
| Custom Watermarks | `Your Logo` |
| Stage Mix | `Smart Angle Switching` |
| Split Sync | `Line Up Angles` |
| Camera Roles | `Camera Jobs` |
| Audio Mix Lanes | `Audio Balance` |
| Cut Override Plan | `Override Smart Cuts` |
| Run Window | `Trim Dead Time` |
| Metric Captions | `Shot Data Overlay` |
| Frame Profiles | `Video Shape` |
| Subject Track Crop | `Keep Shooter in Frame` |
| Lead-In Card | `Opening Title` |
| Brand Mark | `Your Logo` |
| Angle Director | `Smart Angle Switching` |
| Angle Align | `Line Up Angles` |
| Angle Roles | `Camera Jobs` |
| Result Cards | `Result Cards` (keep) |

## Match Video Edit Features

| Competitor Name | SplitShot Name |
|-----------------|----------------|
| Merge (many stages) | `Match Recap` |
| Merge (same stage, many clips) | `Stage Composite` |
| Setup on first video | `Setup Once, Apply Everywhere` |

## Performance Library Features

| Competitor Name | SplitShot Name |
|-----------------|----------------|
| Album | `Performance Library` |
| Smart Album | `Filtered Library View` |

## Implementation Labels

In code, use these exact strings:

- `trim_dead_time`
- `shot_data_overlay`
- `video_shape`
- `keep_shooter_in_frame`
- `opening_title`
- `your_logo`
- `smart_angle_switching`
- `line_up_angles`
- `camera_jobs`
- `audio_balance`
- `override_smart_cuts`
- `match_recap`
- `stage_composite`
- `setup_once_apply_everywhere`
- `result_cards`
- `multi_track_waveform`
- `color_coded_segments`

## UI Labels

In the user interface, use these exact labels:

- "Trim Dead Time"
- "Shot Data on Screen"
- "Video Shape"
- "Keep Shooter in Frame"
- "Opening Title"
- "Your Logo"
- "Smart Angle Switching"
- "Line Up Angles"
- "Camera Jobs"
- "Audio Balance"
- "Override Smart Cuts"
- "Match Recap"
- "Stage Composite"
- "Setup Once, Apply Everywhere"

## Forbidden Names

Do not use these in implementation, UI, or documentation:

- "Run Window"
- "Metric Captions"
- "Frame Profiles"
- "Subject Track Crop"
- "Lead-In Card"
- "Brand Mark"
- "Angle Director"
- "Angle Align"
- "Angle Roles"
- "Audio Mix Lanes"
- "Cut Override Plan"
- "Stage Mix"
- "Split Sync"
- "Auto Trim"
- "Portrait Tracking"

## Enforcement

- lint rule: grep for forbidden names in source code
- review checklist: verify UI labels match contract
- test: verify no forbidden names in rendered HTML
