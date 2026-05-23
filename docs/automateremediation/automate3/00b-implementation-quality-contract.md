# Implementation Quality Contract

Automate3 is only successful if the result looks and behaves like a professional user-facing product.

## UI Quality Bar

Required:

- no placeholder-feeling panels
- no half-wired controls
- no duplicated controls for the same behavior
- no permanent global automation strip
- no hidden route model exposed as the product model
- clear hierarchy for preview, timeline, inspector, and view-specific controls
- consistent spacing, density, typography, and control treatment across views
- stable dimensions for rails, headers, cards, tables, timelines, and toolbars
- no overlapping text or controls at supported viewport sizes.

## Interaction Quality Bar

Required:

- every visible command either works or is disabled with a clear reason
- keyboard focus is visible and logical
- destructive operations require confirmation
- long operations show progress
- errors are recoverable
- users can cancel or reset complex workflows
- PiP drag/playback does not spam routes or reseek continuously.

## Proof Discipline

Validation order:

1. targeted test for changed behavior
2. relevant module or browser suite
3. screenshot proof for affected views
4. canonical grouped runner before completion/release.

Completion claims must include commands, pass/fail status, failing test names if any, and screenshot artifact paths.
