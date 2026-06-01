---
description: "Sequential setup: run electron-env-fixer, then bundle-rebuilder (if fix succeeds), then smoke-diagnoser (if bundle succeeds)."
subtask: true
---

# /electron-setup

Orchestrate the full Electron environment setup, bundle rebuild, and smoke test.

## Sequence

1. **electron-env-fixer** — `npm install` in `electron/`, verify node_modules
2. **bundle-rebuilder** — `node scripts/bundle-python.js`, rebuild `electron/bundle/`
3. **smoke-diagnoser** — `node electron/tests/smoke.test.js`, capture result

## Rules

- Stop at first failure. Report which step failed and the error.
- Do NOT retry failed steps without user direction.
- After step 1 success: run step 2.
- After step 2 success: run step 3.
- After step 3: report pass/fail with diagnostics.

## Output format

```
ELECTRON SETUP RESULT: pass/fail
Step 1 (npm install): pass/fail — <version info or error>
Step 2 (bundle rebuild): pass/fail — <status or error>
Step 3 (smoke test): pass/fail — <diagnosis or error>
```

## Guardrails

- Do NOT modify any source/test/config files.
- Do NOT skip steps.
- Do NOT change timeouts.
