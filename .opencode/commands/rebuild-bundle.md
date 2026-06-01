---
description: "Rebuild electron/bundle/ via node scripts/bundle-python.js. Verify src/, runtime-manifest.json, ffmpeg."
subtask: true
---

# /rebuild-bundle

Delegates to agent `bundle-rebuilder`. Run this after electron-env-fixer completes.

Rebuilds the Electron Python bundle from scratch, replacing any existing bundle contents.
