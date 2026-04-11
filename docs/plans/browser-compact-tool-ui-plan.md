# Browser Compact Tool UI Plan

## Problem

The review cockpit workflow is better, but the UI still reads like a landing page:

- top copy repeats what the app is for
- empty-state text is too verbose
- left rail consumes too much width
- typography is too large for a precision video tool
- action labels are longer than needed

## Goal

Make the browser UI feel like a compact native utility:

- smaller Apple-style system typography
- slim left rail
- one-word tool labels with an apple marker
- no descriptive marketing text
- one compact toolbar for file actions
- dense metrics and inspector controls

## Changes

- Replace the rail logo block with a compact wordmark.
- Shrink the rail width and tool rows.
- Replace two-letter tool codes with `🍎` plus a single tool word.
- Replace topbar heading copy with project name and status only.
- Remove the duplicate empty-state paragraphs.
- Make empty state a simple centered action: open a stage video.
- Reduce headline, metric, split-card, button, and inspector font sizes.
- Keep the persistent cockpit workflow, file pickers, video, waveform, inspector, and all APIs intact.

## Acceptance

- Browser shell remains review-first and hard-edged.
- Left rail is compact.
- UI copy no longer contains duplicate instructional text.
- Static tests protect compact-tool workflow details.
- Browser and full test suites pass.

