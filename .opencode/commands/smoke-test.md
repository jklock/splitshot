---
description: "Run electron/tests/smoke.test.js with DEBUG=pw:* logging to diagnose /api/dialog/path timeout."
subtask: true
---

# /smoke-test

Delegates to agent `smoke-diagnoser`. Run this after bundle rebuild completes.

Runs the Electron smoke test and captures the exact failure details on the `/api/dialog/path` route.
