# SplitShot Visual Remediation

This is the active recovery command center for the browser UI.

Use this package first. The older `automate*` generations are archived under `docs/.archive/automate-legacy/` and are no longer the active source of truth.

## Read Order

1. [00-current-failure-audit.md](00-current-failure-audit.md)
2. [01-design-contract.md](01-design-contract.md)
3. [02-code-remediation-plan.md](02-code-remediation-plan.md)
4. [03-surface-rebuild-order.md](03-surface-rebuild-order.md)
5. [04-doc-migration-matrix.md](04-doc-migration-matrix.md)

## Current State

- Stage Editor is restored to a rail + preview/timeline + inspector layout without the top automation strip.
- Match Video Edit and Performance Library now use persistent left sidebars with `Home` and view-local `Settings`.
- The shell-level Stage/Match/Library bar is removed.
- Match and Library rendering moved out of root `app.js` into dedicated view modules.
- Screenshot proof is refreshed in [../screenshots/automate3/](../screenshots/automate3/).

## Recovery Rule

Do not treat any archived automate package as complete. If a historical document is still useful, copy it forward into `automatecomplete/` or `automateremediation/` and reference it from the migration matrix.
