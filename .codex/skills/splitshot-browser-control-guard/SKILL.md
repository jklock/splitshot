---
name: splitshot-browser-control-guard
description: Guard SplitShot browser UI/control changes by keeping UI controls, tests, routes, controller behavior, inventory audits, and QA matrix documentation aligned.
---
Use this skill when changes touch:
- src/splitshot/browser/static/
- src/splitshot/browser/server.py
- src/splitshot/ui/controller.py
- browser routes or payloads
- overlay, merge, import, export, review, or project controls
- any UI-visible behavior

Core rule:
SplitShot browser controls are an owned surface. Keep the UI, tests, route behavior, inventory audit, and QA matrix truthful.

Inspect:
- Changed browser static files
- server.py routes and payloads
- controller.py project mutations
- docs/project/browser-control-qa-matrix.md
- tests/browser/
- tests/browser/test_browser_control_inventory_audit.py
- scripts/audits/browser/

Required checks:
Run the control inventory audit:

```bash
uv run pytest tests/browser/test_browser_control_inventory_audit.py
```

Run browser tests:

```bash
uv run pytest tests/browser/
```

For behavior changes, run the browser interaction audit:

```bash
uv run python scripts/audits/browser/run_browser_interaction_audit.py
```

Optional headed/debug run:

```bash
uv run python scripts/audits/browser/run_browser_interaction_audit.py --headed --report-json artifacts/browser-interaction-audit.json
```

When controls change:
- Find the owning row in docs/project/browser-control-qa-matrix.md.
- Keep element ids and data attributes intentional.
- Update tests and matrix together when behavior or ownership changes.
- Do not add anonymous or unowned controls.
- Do not bypass inventory failures without documenting ownership.

Debugging:
- If browser audits fail, inspect audit output and browser activity logs.
- Look for server activity events such as api.success and route-level failures.
- Prefer fixing the behavior over weakening the audit.

Done means:
- Inventory audit passes.
- Browser pytest suite passes or the exact failure is explained.
- Interaction audit passes for meaningful UI behavior changes, or the reason it was not run is stated.
- QA matrix remains truthful for changed controls.

Report:
Changed:
Verified:
Result:
Risks:
