# Track 06: Match Video Edit

## Goal

Build Match as a first-class workspace frontend.

## Required UI

- compact match action bar; no oversized title/header strip
- editable match metadata
- stage grid with thumbnails, status, scoring, settings badges
- drag reorder
- shared defaults
- stage overrides
- Setup Once Apply Everywhere
- PractiScore import
- Match Recap
- Stage Composite
- batch export queue.
- full-width workspace body that uses the available viewport instead of a centered narrow column.

Visible emoji are forbidden in this view. Use text, styled badges, or the existing icon system.

## Required Behaviors

- create/open/save Match
- add/remove/reorder stages
- open Stage and return
- preview/apply Stage 1 settings to other stages
- override/reset individual stages
- import PractiScore data
- preview/render recap
- preview/render composite
- batch export with progress.

## Proof

- Match empty screenshot
- Match loaded screenshot
- E2E for open Stage and return
- E2E for apply-from-first preview/apply
- E2E for batch export progress.
