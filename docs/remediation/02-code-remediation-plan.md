# Code Remediation Plan

## Frontend Ownership

- `src/splitshot/browser/static/app.js`
  - bootstrap
  - shared state
  - global coordination only
- `src/splitshot/browser/static/views/match-view.js`
  - Match rendering and Match-local settings
- `src/splitshot/browser/static/views/library-view.js`
  - Library rendering and Library-local settings

## Structural Rules

- Match and Library must not be rendered as Stage subpanels.
- View switching must change whole workspaces, not hide/show fragments of Stage.
- New workspace-specific rendering should not be added back into root `app.js`.
