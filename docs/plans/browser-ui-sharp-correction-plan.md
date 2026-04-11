# Browser UI Sharp Correction Plan

## Problem

The browser redesign restored useful workflow features, but visually regressed into rounded, separated cards. That reads as bubbles and does not match the requested hard-edged local tool surface.

## Requirements

- Keep the Shot Streamer-style left workflow rail.
- Keep all interactive browser features from the previous pass:
  - local video file picker
  - playable video
  - live overlay preview
  - waveform timing edits
  - merge/sync controls
  - scoring presets
  - overlay color controls
  - export/layout controls
- Remove rounded/bubble treatment from panels, cards, buttons, badges, rails, and controls.
- Remove spacing between major workspace panels so sections read as connected squares.
- Keep internal padding for usability.

## Acceptance

- Browser UI uses a contiguous hard-edged shell.
- No rounded panel/card/button/badge treatment remains in the browser CSS.
- Existing browser behavior tests continue to pass.
- Full test suite continues to pass.

