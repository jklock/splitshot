# B06 — Dev workflow (skip bundle, fast startup)

## Metadata

| Field | Value |
|-------|-------|
| task-id | `B06` |
| track | `B — Electron Packaging` |
| status | `pending` |
| depends-on | `B02` |
| risk | `low` |
| touches-files | `electron/package.json`, `electron/main.js` |
| proof-file | `activedev/electroncleanup/proof/PROOF-B06-runN.md` |

## Goal

Developers can run the Electron app without waiting 60s+ for Python
bundling. A dev mode uses the system Python/uv directly, same as
`uv run splitshot`.

## Background

Current `npm start` always runs `node scripts/bundle-python.js && electron .`.
Bundling takes 60s+ and is only needed for production builds. For day-to-day
development, we should use the existing `uv`-managed environment.

## Implementation

### 1. `electron/package.json` — add dev script

```json
"scripts": {
  "dev": "SPLITSHOT_DEV=1 electron .",
  "start": "node ../scripts/bundle-python.js && electron .",
  "bundle": "node ../scripts/bundle-python.js",
  "build": "node ../scripts/bundle-python.js && electron-builder",
  "build:mac": "electron-builder --mac",
  "build:win": "electron-builder --win",
  "build:linux": "electron-builder --linux"
}
```

Key changes:
- New `dev` script sets `SPLITSHOT_DEV=1` and skips bundling
- Platform-specific builds no longer run bundling (run `npm run bundle`
  first manually, or CI handles it separately)
- New `bundle` script for manual bundling
- `start` still bundles (safe for non-devs who run `npm start`)

### 2. `electron/main.js` — detect dev mode

In `startPythonBackend()`, detect dev mode and use `uv run`:

```javascript
function startPythonBackend() {
  let python;
  let args;
  let env;

  if (process.env.SPLITSHOT_DEV) {
    // Dev mode: use uv-managed Python directly
    python = 'uv';
    args = [
      'run', 'splitshot',
      '--headless',
      '--no-open',
      '--host', '127.0.0.1',
      '--port', String(PORT),
    ];
    env = {
      ...process.env,
      SPLITSHOT_ELECTRON: '1',
    };
  } else {
    // Production: use bundled Python
    python = getPythonBinary();
    args = [
      '-m', 'splitshot',
      '--headless',
      '--no-open',
      '--host', '127.0.0.1',
      '--port', String(PORT),
    ];
    env = {
      ...process.env,
      PYTHONPATH: getSplitshotModule(),
      SPLITSHOT_ELECTRON: '1',
      SPLITSHOT_BUNDLE_DIR: getBundlePath(),
    };
  }

  pythonProcess = spawn(python, args, {
    cwd: getBundlePath(),
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  // ... rest unchanged
}
```

### 3. Auto-detect missing bundle in non-dev mode

If `SPLITSHOT_DEV` is not set but the bundle doesn't exist, show a
helpful error:

```javascript
function getPythonBinary() {
  const python = path.join(getBundlePath(), '.venv', 'bin', 'python');
  if (!fs.existsSync(python)) {
    if (app.isPackaged) {
      throw new Error('Python runtime not found in bundle');
    }
    // In development but bundle missing — suggest dev mode
    console.error(
      'Python bundle not found. Run with SPLITSHOT_DEV=1 to use system Python:\n' +
      '  SPLITSHOT_DEV=1 npm --prefix electron run dev\n' +
      'Or create the bundle:\n' +
      '  npm --prefix electron run bundle'
    );
    process.exit(1);
  }
  return python;
}
```

### 4. Auto-detect if running from repo root

In dev mode, detect the project root for `uv run`:
```javascript
if (process.env.SPLITSHOT_DEV) {
  // Find project root (where pyproject.toml lives)
  const projectRoot = findProjectRoot();
  if (projectRoot) {
    env.SPLITSHOT_PROJECT_ROOT = projectRoot;
    // Use --directory flag for uv
    args.unshift('--directory', projectRoot);
  } else {
    console.error('Could not find project root (pyproject.toml)');
    console.error('Run from the repository root or set SPLITSHOT_DEV=0');
    process.exit(1);
  }
}
```

## Validation

```bash
# Dev mode (fast, uses uv)
time npm --prefix electron run dev
# Expected: starts in <5s, no bundling output

# Production mode (bundling required)
time npm --prefix electron run bundle
time npm --prefix electron run build:mac
# Expected: bundling runs once, build produces .dmg

# Auto-detect missing bundle
SPLITSHOT_DEV=0 npm --prefix electron run dev
# Expected: helpful error message about missing bundle
```

## Done criteria

- [ ] `npm run dev` starts Electron in <5s using `uv run splitshot`
- [ ] `npm run start` still bundles for non-devs
- [ ] `npm run bundle` creates bundle without building
- [ ] Platform build scripts don't re-bundle
- [ ] Missing bundle shows helpful error with fix instructions
- [ ] Proof written, progress updated
