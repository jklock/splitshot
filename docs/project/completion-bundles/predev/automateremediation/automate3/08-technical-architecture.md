# Technical Architecture

Automate3 keeps the browser app stack but restructures the frontend into explicit views.

## Frontend Pieces

- **Shared shell**: app frame, logo/home, global context, global notifications, shared status.
- **View controller**: owns `active_view`, view mounting/unmounting, local view state retention, and navigation events.
- **View modules**: Landing, Stage, Match, Library.
- **Shared API client**: typed wrappers around existing JSON routes.
- **Shared state adapter**: converts `/api/state` summaries into view-ready context.
- **Shared visual system**: colors, density, typography, controls, tables, cards, modals, empty states.
- **Stage pane preservation layer**: keeps existing Stage tool panes usable while they are regrouped inside Stage Video Edit.

## Required Separation

Do not put every product workflow into a global strip. Each view owns its layout:

- Landing owns entry and recent work.
- Stage owns editor panes, preview, timeline, output profiles, multi-angle controls.
- Match owns workspace grid, defaults, overrides, recap, composite, batch export.
- Library owns history, analytics, detail, tags, notes, proxy/archive, comparison.

## Data Flow

1. App polls or fetches `/api/state` for high-level context.
2. View controller decides which view is active.
3. Active view fetches dedicated detail routes as needed.
4. Mutations update backend through dedicated routes.
5. Successful mutations refresh only the affected summaries/details.
6. Library history updates from Stage/Match events without navigation hijack.

## Likely Files To Change

- `src/splitshot/browser/static/index.html`
- `src/splitshot/browser/static/app.js`
- `src/splitshot/browser/static/styles/*.css`
- `src/splitshot/browser/static/panes/*.js`
- `src/splitshot/browser/static/components/*.js`
- `src/splitshot/browser/server.py`
- `src/splitshot/ui/controller.py`
- browser and controller tests under `tests/browser/`.

For exact per-file changes, see `../automate3-ui/artifacts/file-change-map.md`.

## Guardrails

- Preserve existing Stage editor behavior before refactoring visible structure.
- Move controls to owning views; do not duplicate them.
- Keep route commits out of pointermove/playback loops.
- Add tests before claiming any view complete.
