# Performance Library Spec

Performance Library is the canonical historical performance record. It must feel like a core product view, not a file browser.

## Required Layout

Performance Library must have:

- summary tiles
- filter/search/sort row
- record table
- selected-record detail panel
- retained proxy/player area
- analytics dashboard
- tags and notes editor
- comparison tool
- proxy/archive actions
- export actions
- professional empty library state.

## Required Data

Library records must expose enough data for:

- stage and match totals
- recent activity
- personal bests
- trends over time
- outliers
- discipline breakdown
- scoring/PractiScore context
- retained proxy state
- archive state
- reopen targets.

## Required Workflows

- browse records
- search and filter
- sort by date/name/metric/status
- select a record
- edit tags
- edit notes
- open retained proxy
- refresh/regenerate proxy or archive
- compare records
- export CSV/JSON
- reopen Stage or Match when available.

## Automatic Update Rule

Stage and Match completion events update Library history without stealing focus. The user remains in their current view and sees a subtle status/notification only when useful.

## Acceptance

Library is acceptable only when:

- empty, loaded, stale proxy, missing proxy, missing archive, unresolved reopen target, and ready states are designed
- analytics are visible and meaningful
- users can reopen work intentionally
- tags and notes persist
- export actions work or are clearly unavailable
- loaded screenshot proof shows it as a first-class product surface.
