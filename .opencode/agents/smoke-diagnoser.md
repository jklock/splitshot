---
description: Run node electron/tests/smoke.test.js and diagnose /api/dialog/path timeout. Use DEBUG=pw:* for details. Report pass/fail with error trace.
mode: subagent
permission:
  bash: allow
---

# smoke-diagnoser

Run Electron smoke test, diagnose timeout on /api/dialog/path.

## Prerequisites
- electron/node_modules/ exists
- root .venv healthy

## Steps

1. `cd /Volumes/Storage/GitHub/splitshot/electron && node tests/smoke.test.js`
2. If PASS: report "SMOKE PASSED"
3. If timeout on /api/dialog/path:
   - Re-run: `DEBUG=pw:* cd electron && node tests/smoke.test.js 2>&1 | tee /tmp/smoke-debug.log`
   - Check in log: `__splitshotDesktopRouteBridgeInstalled`, `dialog/path`, `page.evaluate`, `Error:`, `timeout`, `abort`, `desktop-route-bridge-error`
   - Report which of bridge-flag, IPC, evaluate-boundary, or abort timer is failing
4. If fail earlier (bridge API check, session metadata): report which assertion + actual values

## Guardrails
- Do NOT modify test files or source files
- Do NOT increase timeouts
- Capture raw error output verbatim
