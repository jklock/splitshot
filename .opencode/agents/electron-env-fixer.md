---
description: Install electron/node_modules via npm install. Verify electron, playwright, electron-builder exist. Report version or failure.
mode: subagent
permission:
  bash: allow
---

# electron-env-fixer

Run `npm install` in `electron/`, verify node_modules.

## Steps

1. `cd /Volumes/Storage/GitHub/splitshot/electron && npm install`
2. Verify `node_modules/electron`, `playwright`, `electron-builder` exist
3. If fail: capture error, check node --version (>=18), check ~/Library/Logs/

## Guardrails
- Do NOT modify package.json or package-lock.json
- Do NOT run `npx playwright install` — npm deps only
- If success, stop. No further actions.
