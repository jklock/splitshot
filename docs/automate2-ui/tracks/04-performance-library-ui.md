# Track 04: Performance Library UI

## Goal

Make the library a real historical browse-and-reopen surface with analytics, the app's killer feature.

## Required UI

### Dashboard

- summary tiles:
  - Total Stages
  - Total Matches
  - Personal Bests
  - Recent Activity
- click tiles to filter records

### Filter and Search

- search by name
- filter by date range
- filter by discipline
- filter by competitor
- filter by tags
- filter by personal bests
- sort by date, metric, name

### Record Table

- columns: name, date, discipline, competitor, key metric, status
- click to select
- double-click to open
- context menu: Open, Edit Tags, Edit Notes, Export, Delete

### Selected Record Detail

- summary and key metrics
- retained proxy player
- PracticeScore data viewer
- tags and notes editor
- action buttons: Open Editor, Refresh Proxy, Regenerate Archive, Export

### Analytics Dashboard

- trend charts (line charts for metrics over time)
  - first-shot reaction
  - cumulative time
  - reload speed
  - score trend
- personal bests list
- outlier highlights
- discipline breakdown (pie chart or bar chart)

### Comparison Tool

- select two records
- side-by-side metric comparison
- side-by-side proxy playback

### Export Actions

- export selected records to CSV
- export selected records to JSON
- generate PDF report

## Required States

- empty library: friendly message, getting-started tips
- stale proxy: show metrics, mark proxy as stale, offer refresh
- missing proxy: show metrics, mark proxy as missing, offer regenerate
- missing archive: show metrics, mark archive as missing, offer regenerate
- unresolved reopen target: show history, mark reopen unavailable
- ready reopen target: show all data, enable all actions

## Acceptance

- the user can browse, inspect, and reopen historical work without dropping back into a hidden route model
- analytics charts render correctly and quickly
- personal bests are clearly highlighted
- outliers are flagged with explanation
- tags and notes are immediately editable
- library data can be exported
- the surface feels like a killer feature, not a file browser
