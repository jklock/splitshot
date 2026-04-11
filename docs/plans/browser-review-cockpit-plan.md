# Browser Review Cockpit Plan

## Problem

The previous browser UI exposed the right features but forced users through page modes. That makes common review/edit/scoring/overlay work too slow because the video and timeline disappear when users change tools.

## Goal

Build a review-first workflow where the video, live overlay preview, timeline, waveform, and selected-shot context stay visible while tools change around them.

## Workflow

1. User starts on a compact local library/start panel.
2. `Open Stage Video` opens a file picker and immediately starts local analysis.
3. After analysis, the app lands in the same persistent cockpit.
4. Video remains in the center at all times.
5. Timeline and waveform remain under the video at all times.
6. The right inspector changes based on selected tool and selected shot.
7. Timing, scoring, overlay, merge, layout, export, and project management become tool drawers rather than separate pages.

## Cockpit Layout

- Top bar:
  - project name
  - status
  - primary file picker
  - secondary file picker
  - export readiness
- Center:
  - metric strip
  - playable video with live overlay and score placement
  - marker strip
  - waveform editor
  - split cards
- Right inspector:
  - selected shot controls
  - tool-specific controls
  - detailed timing table when Timing is active

## Acceptance

- Only one persistent main workspace exists after startup.
- Video, waveform, timeline, split cards, and inspector are visible together.
- Tool selection changes the inspector/drawer, not the entire workspace.
- File picker, overlay, scoring, merge, layout, project, and export controls remain available.
- Feature tests validate the cockpit workflow contract.

