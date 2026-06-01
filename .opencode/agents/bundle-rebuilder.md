---
description: Rebuild electron/bundle/ by running node scripts/bundle-python.js. Verify src/, pyproject.toml, runtime-manifest.json, ffmpeg exist.
mode: subagent
permission:
  bash: allow
---

# bundle-rebuilder

Rebuild the Electron Python bundle from scratch.

## Prerequisites
- electron/node_modules/ exists (run electron-env-fixer first)
- root .venv healthy, curl available

## Steps

1. `cd /Volumes/Storage/GitHub/splitshot && node scripts/bundle-python.js`
2. If success: verify `electron/bundle/src/` non-empty, `runtime-manifest.json` valid JSON, `.venv/bin/python` executable, ffmpeg under `resources/ffmpeg/<platform>/`
3. If fail: identify which step (uv pip install, copyDirectory, bundleFfmpeg, generateIcons, writeRuntimeManifest) and report exact error
4. If bundle already exists: `node scripts/bundle-python.js check` first

## Guardrails
- Do NOT modify scripts/bundle-python.js or source files
- Do NOT manually create files in electron/bundle/
