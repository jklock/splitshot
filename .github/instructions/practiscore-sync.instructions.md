---
applyTo:
  - "src/splitshot/browser/static/index.html"
  - "src/splitshot/browser/static/app.js"
  - "src/splitshot/browser/static/styles.css"
  - "tests/browser/test_browser_interactions.py"
  - "tests/browser/test_browser_static_ui.py"
  - "tests/browser/test_browser_control_inventory_audit.py"
  - "tests/browser/test_browser_control_coverage_matrix.py"
  - "docs/userfacing/panes/project.md"
  - "docs/project/browser-control-qa-matrix.md"
---

# PractiScore Sync Feature Guidance

- Keep the Project pane aligned with the browser payload contract: `practiscore_session`, `practiscore_sync`, and `practiscore_options`.
- Update source, tests, and docs together whenever the remote connect flow, remote match list, selected-match import flow, or session and sync state rendering changes.
- Preserve the local `Select PractiScore File` fallback path and the existing `Match type`, `Stage #`, `Competitor name`, and `Place` controls unless product direction explicitly removes them.
- Treat session start, status, and clear routes as lightweight status endpoints. If selected-match import changes imported summaries or scoring output, refresh the full `/api/state` payload before rendering final success.
- Maintain explicit browser coverage for connect, match-list load, selected-match import, expired or error rendering, and manual fallback parity.