# Track 07: Performance Library

## Goal

Build Performance Library as the canonical historical analytics frontend.

## Required UI

- summary tiles
- filters/search/sort
- record table
- selected detail
- retained proxy player
- proxy/archive status
- analytics charts
- personal bests
- outliers
- discipline breakdown
- comparison tool
- tags
- notes
- export actions
- reopen actions.
- compact refresh/export action bar; no oversized title/header strip
- full-width workspace body that uses the available viewport instead of a centered narrow column.

Visible emoji are forbidden in this view. Use text, styled badges, or the existing icon system.

## Required Behaviors

- Stage/Match completions update history automatically
- user remains in current view after history update
- filters and search update record table
- selecting a record updates detail
- tags and notes persist
- proxy/archive actions report progress/errors
- reopen Stage/Match is intentional.

## Proof

- Library empty screenshot
- Library loaded screenshot
- tests for filter/select/detail
- tests for tag/note persistence
- tests for reopen actions
- tests for export actions.
