# E02 — Python Bundling

## Metadata

| Field | Value |
| --- | --- |
| task-id | `E02` |
| status | `pending` |
| depends-on | `E01` |
| risk | `medium` |
| touches-files | `scripts/bundle-python.js`, `electron/package.json`, `.gitignore`, `activedev/electron/progress.md` |
| forbidden-files | `src/`, `pyproject.toml` (must not be modified — only copied) |
| proof-file | `activedev/electron/proof/PROOF-E02-runN.md` |

## Goal

Create the bundling script that produces a self-contained Python runtime inside `electron/bundle/` for distribution.

## Implementation

### `scripts/bundle-python.js`

Node.js script that:

1. Creates `electron/bundle/` directory
2. Runs `python3 -m venv bundle/.venv` to create an isolated Python environment
3. Installs the project and its dependencies: `bundle/.venv/bin/pip install .`
4. Runs `bundle/.venv/bin/python -c "import static_ffmpeg; static_ffmpeg.add_paths()"` to embed FFmpeg/FFprobe
5. Copies `src/` into `bundle/src/`
6. Copies `pyproject.toml` into `bundle/`
7. Prunes unnecessary files:
   - `__pycache__/` and `*.pyc`
   - Test directories (`tests/`)
   - Documentation
   - `.venv/share/` (man pages, doc files)
   - `pip` cache
8. Verifies the bundle works: `bundle/.venv/bin/python -m splitshot --check`

Output: `electron/bundle/` is ~150MB and completely self-contained.

### `electron/package.json` update

Add the build script to invoke bundling before electron-builder:

```json
"build": "node scripts/bundle-python.js && electron-builder"
```

## Validation

```bash
node scripts/bundle-python.js
ls -lh electron/bundle/.venv/bin/python
electron/bundle/.venv/bin/python -m splitshot --check
```

Expected: Python check passes, FFmpeg/FFprobe found, all static assets present.

## Done criteria

- [ ] `scripts/bundle-python.js` exists and produces a working bundle
- [ ] `electron/bundle/` contains self-contained Python + FFmpeg + SplitShot
- [ ] `bundle/.venv/bin/python -m splitshot --check` passes
- [ ] Bundle is pruned (no __pycache__, tests, docs)
- [ ] `.gitignore` excludes `electron/bundle/`
- [ ] Proof written, progress updated
