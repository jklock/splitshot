# B06 — Dev workflow

## Status: Complete

## Changes

- `electron/package.json`:
  - Added `dev` script: `electron .` — launches directly without bundling
  - Added `check` script: bundles Python and verifies integrity
  - `dev` skips bundling entirely — uses `uv run splitshot --headless --no-open` at runtime

## Verification

```bash
# Fast dev startup (no bundling needed)
npm --prefix electron run dev

# Bundle + check
npm --prefix electron run check
```
