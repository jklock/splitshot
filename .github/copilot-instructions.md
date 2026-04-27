# PractiScore Sync Parity Rules

- When the Project-pane PractiScore workflow or any related UI state changes, update the owned browser tests in the same change. That includes the static UI contract, browser interaction flow coverage, and the control inventory or QA-matrix checks when control IDs or coverage claims change.
- When a Project-pane control, route, or user-visible PractiScore workflow changes, update the user-facing Project-pane guide and the browser QA matrix in the same change.
- Keep the manual `Select PractiScore File` fallback path and the local `Match type`, `Stage #`, `Competitor name`, and `Place` controls unless product direction explicitly removes them.
- Treat `practiscore_session`, `practiscore_sync`, and `practiscore_options` as the browser contract for Project-pane PractiScore behavior.