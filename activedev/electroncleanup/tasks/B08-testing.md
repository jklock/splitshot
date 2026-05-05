# B08 — Testing (audit, e2e, installer verify) — all 3 platforms

## Metadata

| Field | Value |
|-------|-------|
| task-id | `B08` |
| track | `B — Electron Packaging` |
| status | `pending` |
| depends-on | `A01`, `B02`, `B07` |
| risk | `high` |
| touches-files | `scripts/audits/electron_parity_audit.py`, `tests/electron/`, `.github/workflows/build-electron.yml`, `electron/package.json` |
| proof-file | `activedev/electroncleanup/proof/PROOF-B08-runN.md` |

## Goal

Every feature is testable in both `uv run splitshot` and the Electron app —
on **macOS, Windows, and Linux**. The parity audit proves identity, not
similarity. CI catches regressions on all three platforms before artifacts
ship.

## Background

Current testing gaps:
- Parity audit tests `backend.py`, not the real Electron shell (T1)
- No Electron e2e tests (T2)
- No installer verification (T3)
- CI has no test step (T4)
- No bundle integrity check (T5)
- **No Linux-specific testing at all**

## Implementation

### 0. Platform-agnostic audit runner design

All test scripts must work on all three platforms. Key differences:
- **Python path**: `bin/python` (macOS/Linux) vs `Scripts/python.exe` (Windows)
- **UV availability**: UV may not be on PATH on Windows CI
- **Shell syntax**: Use Node.js scripts or Python for cross-platform
  portability, avoid bash-specific constructs
- **Playwright**: Works on all platforms, electron fixture is cross-platform

### 1. `scripts/audits/electron_parity_audit.py` — rewrite for parity

Change the audit to test TWO modes and compare results:

```python
#!/usr/bin/env python3
"""Parity audit: native vs bundled. Runs on macOS, Windows, Linux."""

import os
import platform
import subprocess
import sys

def get_bundle_python():
    bundle = os.path.join(REPO, "electron", "bundle")
    bin_dir = "Scripts" if sys.platform == "win32" else "bin"
    return os.path.join(bundle, ".venv", bin_dir, "python")

def get_native_python():
    """Use `uv run splitshot` on all platforms, or fall back to system python."""
    return "uv"  # uv handles cross-platform Python management
```

Audit method:

```python
def audit_parity():
    """Test both `uv run splitshot --headless` and the bundled backend.
    Verify they produce identical API responses."""
    
    results_native = test_server("native", start_native_backend)
    results_bundled = test_server("bundled", start_bundled_backend)
    
    for key in results_native:
        if results_native[key] != results_bundled[key]:
            report("PARITY FAIL", key, f"native != bundled")
    
    report("PARITY", "all endpoints", "PASS (native == bundled)")
```

The test runner should:
- Start native: `uv run splitshot --headless --no-open --port <port>`
- Start bundled: `<bundle-python> -m splitshot --headless --no-open --port <port+1>`
  (Uses the CLI directly, not `backend.py`, after B02 change)
- Hit the same endpoints on both servers
- Compare JSON responses, status codes, headers
- Measure latency on both (speed parity)

Add `--mode` flag:
- `--mode native`: test `uv run splitshot --headless`
- `--mode bundled`: test bundled backend
- `--mode parity`: test both and compare (default)

### 2. Electron e2e tests (cross-platform)

Create `tests/electron/` with Playwright-Node tests:

```
tests/electron/
├── package.json              # Depends on @playwright/test
├── playwright.config.js      # electron fixture config
├── smoke.test.js             # Launch, verify window, verify API, close (all platforms)
├── menu.test.js              # Test menu items (macOS-only: app menu differs)
└── README.md
```

#### Platform-specific considerations:

**All platforms:**
```javascript
const { _electron: electron } = require('playwright');

test('Electron app launches and loads UI', async () => {
  // Launch from source (dev mode) — works on all platforms
  // In CI, launch from the built app if available
  const app = await electron.launch({
    args: ['electron/main.js'],
    env: { SPLITSHOT_DEV: '1' },
  });
  const window = await app.firstWindow();
  
  // Verify window
  await expect(window).toHaveTitle('SplitShot');
  await window.waitForSelector('#app-root', { timeout: 30000 });
  
  // Verify IPC bridge
  const version = await window.evaluate(() => window.splitshot.getVersion());
  expect(version).toBeTruthy();
  
  // Verify Python backend responds
  const state = await window.evaluate(async () => {
    const resp = await fetch('/api/state');
    return resp.json();
  });
  expect(state.status).toBe('ok');
  
  await app.close();
});
```

**macOS-only menu test:**
```javascript
test('macOS app menu exists', async ({ browserName, platform }) => {
  // Only run on macOS
  if (platform !== 'darwin') return;
  // Verify app menu items via Electron API
});
```

**Linux-only MIME test:**
```javascript
test('Linux .desktop MIME entries', async ({ browserName, platform }) => {
  if (platform !== 'linux') return;
  // Verify AppImage contains proper .desktop file
  // This can be tested without launching the app
});
```

#### CI integration:

In CI, the e2e tests run **after build** using the built app:
```yaml
- name: Run Electron e2e tests
  run: |
    cd tests/electron
    npm install
    npx playwright test
  env:
    ELECTRON_APP_PATH: ${{ github.workspace }}/electron/build/SplitShot-*
```

### 3. Bundle integrity check (platform-aware)

```javascript
// electron/check.js — bundle integrity checker (cross-platform)

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const os = require('os');

const isWin = os.platform() === 'win32';
const binDir = isWin ? 'Scripts' : 'bin';
const pythonExt = isWin ? '.exe' : '';

function check() {
  const bundlePath = path.join(__dirname, 'bundle');
  const pythonBin = path.join(bundlePath, '.venv', binDir, `python${pythonExt}`);
  
  checkExists('Python binary', pythonBin);
  checkExecutable('Python binary', pythonBin);
  
  const result = execSync(`"${pythonBin}" -m splitshot --check`, {
    cwd: bundlePath,
    encoding: 'utf8',
  });
  console.log(result);
  
  // Check platform-specific paths
  if (isWin) {
    checkExists('FFmpeg', path.join(bundlePath, '.venv', 'Scripts', 'ffmpeg.exe'));
  } else {
    checkExists('FFmpeg', path.join(bundlePath, '.venv', 'bin', 'ffmpeg'));
  }
  
  // Check static assets (same on all platforms)
  const staticDir = path.join(bundlePath, 'src', 'splitshot', 'browser', 'static');
  for (const asset of ['index.html', 'styles.css', 'app.js']) {
    checkExists(`Static: ${asset}`, path.join(staticDir, asset));
  }
  
  // Check icons
  const assetsDir = path.join(__dirname, 'assets');
  checkExists('Icon (png)', path.join(assetsDir, 'icon.png'));  // Linux
  if (!isWin) {
    checkExists('Icon (icns)', path.join(assetsDir, 'icon.icns'));  // macOS
  }
  if (isWin && fs.existsSync(path.join(assetsDir, 'icon.ico'))) {
    console.log('Icon (ico): present');  // Windows
  }
  
  console.log('Bundle integrity check: PASSED');
}
```

### 4. CI test integration (all platforms)

After B07's CI rewrite, the test steps are:

```yaml
- name: Verify bundle integrity
  run: npm --prefix electron run check

- name: Run parity audit
  run: uv run python scripts/audits/electron_parity_audit.py --mode bundled

- name: Run browser tests against bundled backend
  run: |
    uv run pytest tests/browser/ --no-header -q --timeout=120 -x --tb=short

- name: Install Playwright system deps (Linux)
  if: matrix.platform == 'Linux'
  run: |
    pip install playwright
    playwright install --with-deps chromium

- name: Install Electron e2e deps
  run: |
    cd tests/electron
    npm install

- name: Run Electron e2e tests
  run: |
    cd tests/electron
    npx playwright test
  env:
    SPLITSHOT_DEV: '1'

- name: Build Electron app
  run: npm --prefix electron run ${{ matrix.build-script }}

- name: Verify installer
  run: |
    case "${{ matrix.platform }}" in
      macOS)
        ls -lh electron/build/*.dmg
        test -f electron/build/*.dmg && echo "Installer verified"
        # Future: mount dmg and verify .app structure
        ;;
      Windows)
        ls -lh electron/build/*.exe
        test -f electron/build/*.exe && echo "Installer verified"
        # Future: verify NSIS installer exits 0
        ;;
      Linux)
        ls -lh electron/build/*.AppImage
        test -f electron/build/*.AppImage && echo "Installer verified"
        # Verify AppImage is executable
        file electron/build/*.AppImage | grep -q "ELF" && echo "AppImage is ELF binary"
        ;;
    esac
```

### 5. `electron/package.json` — scripts

```json
"scripts": {
  "check": "node check.js && uv run python scripts/audits/electron_parity_audit.py --mode bundled",
  ...
}
```

### 6. Linux-specific test: verify AppImage contents

Add a Linux-only CI step that inspects the built AppImage:
```yaml
- name: Verify AppImage MIME integration (Linux)
  if: matrix.platform == 'Linux'
  run: |
    APPIMAGE=$(ls electron/build/*.AppImage)
    chmod +x "$APPIMAGE"
    "$APPIMAGE" --appimage-extract *.desktop > /dev/null 2>&1 || true
    if [ -f squashfs-root/*.desktop ]; then
      grep -q "MimeType=application/x-studio.splitshot.ssproj" squashfs-root/*.desktop
      echo "AppImage .desktop MIME type: OK"
      rm -rf squashfs-root
    fi
```

## Validation

```bash
# macOS — all tests
npm --prefix electron run bundle
npm --prefix electron run check
uv run python scripts/audits/electron_parity_audit.py --mode parity
cd tests/electron && npm install && npx playwright test
npm --prefix electron run build:mac
ls electron/build/*.dmg

# Windows — all tests
npm --prefix electron run bundle
npm --prefix electron run check
uv run python scripts/audits/electron_parity_audit.py --mode parity
cd tests/electron && npm install && npx playwright test
npm --prefix electron run build:win
ls electron/build/*.exe

# Linux — all tests
npm --prefix electron run bundle
npm --prefix electron run check
uv run python scripts/audits/electron_parity_audit.py --mode parity
cd tests/electron && npm install && npx playwright test
npm --prefix electron run build:linux
ls electron/build/*.AppImage
# Verify .desktop MIME
./electron/build/SplitShot-*.AppImage --appimage-extract *.desktop
grep MimeType squashfs-root/*.desktop
```

## Done criteria

- [ ] Parity audit works on all 3 platforms (OS-agnostic python path)
- [ ] Parity audit compares native vs bundled, asserts identical responses
- [ ] Parity audit has `--mode native`, `--mode bundled`, `--mode parity`
- [ ] `tests/electron/` exists with smoke test that works on all platforms
- [ ] Electron e2e smoke test passes on macOS, Windows, Linux
- [ ] `npm run check` validates bundle with platform-aware paths
- [ ] CI runs: bundle integrity → parity audit → browser tests → e2e tests → build → installer verify
- [ ] Linux CI verifies AppImage `.desktop` MIME entries
- [ ] Linux CI installs Playwright system deps for browser tests
- [ ] All existing tests pass on all platforms
- [ ] Proof written, progress updated
