---
description: "Run npm install in electron/, verify node_modules/ has electron, playwright, electron-builder."
subtask: true
---

# /fix-electron-env

Delegates to agent `electron-env-fixer`. Run this if electron/node_modules/ is missing or stale.

Runs `npm install` in the electron directory and verifies all required packages.
