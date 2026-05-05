# B07 — Build pipeline (icons, bundling, CI) — all 3 platforms

## Metadata

| Field | Value |
|-------|-------|
| task-id | `B07` |
| track | `B — Electron Packaging` |
| status | `pending` |
| depends-on | `B01`, `B06` |
| risk | `high` |
| touches-files | `scripts/bundle-python.js`, `.github/workflows/build-electron.yml`, `electron/package.json`, `electron/assets/` |
| proof-file | `activedev/electroncleanup/proof/PROOF-B07-runN.md` |

## Goal

A clean, fast, reliable build pipeline for **all three platforms** that:
- Generates platform-specific icons (`.icns` macOS, `.ico` Windows, `.png` Linux)
- Bundles Python + FFmpeg deterministically
- Builds `.dmg` / `.exe` / `.AppImage` installers
- Runs in CI on tag pushes — one job per platform in parallel
- Never runs bundling twice
- Verifies each platform's bundle produces working artifacts

## Background

Current problems:
- CI duplicates bundling logic inline (Q1) — **especially bad for Linux:
  the inline steps may differ from macOS/Windows**
- CI runs bundling twice per platform (Q2)
- Icons sit in build output dir (B01 fixes this)
- No Windows `.ico` (Q4)
- FFmpeg bundling uses `which ffmpeg` (Q5) — **fails on Linux CI runners
  that don't have ffmpeg pre-installed**
- Bundle script hardcodes Python 3.12 paths (Q6, Q7) — **Linux has
  different lib/python3.12 paths than macOS**

## Implementation

### 1. `scripts/bundle-python.js` — refactor for all platforms

#### a. Python binary path (platform-aware)

```javascript
function getPythonBin(venvDir) {
  const binDir = process.platform === 'win32' ? 'Scripts' : 'bin';
  const ext = process.platform === 'win32' ? '.exe' : '';
  return path.join(venvDir, binDir, `python${ext}`);
}

function getPipBin(venvDir) {
  const binDir = process.platform === 'win32' ? 'Scripts' : 'bin';
  const ext = process.platform === 'win32' ? '.exe' : '';
  return path.join(venvDir, binDir, `pip${ext}`);
}
```

#### b. Python version detection (dynamic, not hardcoded)

```javascript
function getPythonVersion(pythonBin) {
  const version = execSync(`"${pythonBin}" --version`, { encoding: 'utf8' }).trim();
  const match = version.match(/Python (\d+\.\d+)/);
  if (!match) throw new Error(`Could not detect Python version from: ${version}`);
  return match[1];
}
```

Use for site-packages path:
```javascript
const pyVersion = getPythonVersion(pythonBin);
const SITE = path.join(VENV_DIR, 'lib', `python${pyVersion}`, 'site-packages');
```

#### c. FFmpeg bundling (platform-agnostic)

Replace `which ffmpeg` with `static_ffmpeg` pip package that works
on all three platforms:

```javascript
console.log('[bundle] Bundling FFmpeg via static_ffmpeg...');
execSync(`"${pythonBin}" -c "import static_ffmpeg; static_ffmpeg.add_paths()"`, {
  cwd: BUNDLE_DIR,
});
```

If `static_ffmpeg` is not available in the dependency tree, add it
to the bundle's pip install explicitly:
```javascript
execSync(`"${pipBin}" install static_ffmpeg`);
```

#### d. Symlink resolution (macOS only)

```javascript
if (process.platform === 'darwin') {
  // uv creates symlinks to ~/.local/share/uv/python/... on macOS
  // Resolve them so the bundle works on machines without uv
  for (const name of ['python', 'python3', `python${pyVersion}`]) {
    const p = path.join(VENV_DIR, 'bin', name);
    if (fs.existsSync(p)) {
      const real = fs.realpathSync(p);
      rmrf(p);
      fs.copyFileSync(real, p);
      fs.chmodSync(p, 0o755);
    }
  }
  // Also copy libpython dylib
  const realPython = fs.realpathSync(pythonBin);
  const libSrc = path.join(path.dirname(path.dirname(realPython)), 'lib', `libpython${pyVersion}.dylib`);
  if (fs.existsSync(libSrc)) {
    fs.copyFileSync(libSrc, path.join(VENV_DIR, 'lib', `libpython${pyVersion}.dylib`));
  }
}
// Windows and Linux: no symlink resolution needed
```

#### e. Icon generation (all 3 platforms)

Icons go into `electron/assets/` (after B01):

```javascript
const ASSETS_DIR = path.join(ROOT, 'electron', 'assets');
const logoPath = path.join(ROOT, 'src', 'splitshot', 'browser', 'static', 'logo.png');
fs.mkdirSync(ASSETS_DIR, { recursive: true });

// macOS .icns
if (process.platform === 'darwin') {
  const iconset = path.join(ASSETS_DIR, 'icons.iconset');
  fs.mkdirSync(iconset, { recursive: true });
  for (const size of [16, 32, 64, 128, 256, 512, 1024]) {
    execSync(`sips -z ${size} ${size} "${logoPath}" --out "${iconset}/icon_${size}x${size}.png"`);
    if (size <= 512) {
      execSync(`sips -z ${size*2} ${size*2} "${logoPath}" --out "${iconset}/icon_${size}x${size}@2x.png"`);
    }
  }
  execSync(`iconutil -c icns "${iconset}" -o "${path.join(ASSETS_DIR, 'icon.icns')}"`);
}

// Linux .png (256x256 minimum for electron-builder)
const linuxPngPath = path.join(ASSETS_DIR, 'icon.png');
if (!fs.existsSync(linuxPngPath)) {
  fs.copyFileSync(logoPath, linuxPngPath);
}

// Windows .ico (use ImageMagick if available, otherwise skip for CI)
const icoPath = path.join(ASSETS_DIR, 'icon.ico');
if (process.platform === 'win32') {
  execSync(`magick "${logoPath}" -define icon:auto-resize=256,64,48,32,16 "${icoPath}"`);
} else if (process.platform === 'darwin' && fs.existsSync('/opt/homebrew/bin/magick')) {
  execSync(`magick "${logoPath}" -define icon:auto-resize=256,64,48,32,16 "${icoPath}"`);
} else {
  console.log('[bundle] .ico not generated locally — CI generates it on Windows');
}
```

### 2. `electron/package.json` — electron-builder config (all platforms)

```json
{
  "mac": {
    "category": "public.app-category.sports",
    "target": ["dmg"],
    "icon": "assets/icon.icns",
    "hardenedRuntime": true,
    "gatekeeperAssess": false,
    "extendInfo": {
      "CFBundleDocumentTypes": [
        {
          "CFBundleTypeName": "SplitShot Project",
          "CFBundleTypeRole": "Editor",
          "LSHandlerRank": "Owner",
          "LSItemContentTypes": ["studio.splitshot.ssproj"]
        }
      ]
    }
  },
  "win": {
    "target": ["nsis"],
    "icon": "assets/icon.ico"
  },
  "linux": {
    "target": ["AppImage"],
    "icon": "assets/icon.png",
    "category": "Sports",
    "mimeTypes": ["application/x-studio.splitshot.ssproj"]
  }
}
```

Note on Linux target format:
- **AppImage**: Portable, works on all distros. Best default.
- **deb** and **rpm**: Can be added later, but AppImage is sufficient
  for v1. The `mimeTypes` field registers the MIME type in the generated
  `.desktop` file.

### 3. CI workflow — rewrite (one job per platform, no duplication)

```yaml
name: Build Electron

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    strategy:
      matrix:
        include:
          - os: macos-14
            platform: macOS
            target: mac
            build-script: build:mac
          - os: windows-latest
            platform: Windows
            target: win
            build-script: build:win
          - os: ubuntu-latest
            platform: Linux
            target: linux
            build-script: build:linux

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '22'

      - name: Install uv
        run: pip install uv

      - name: Install system dependencies (Linux)
        if: matrix.platform == 'Linux'
        run: |
          sudo apt-get update -qq
          sudo apt-get install -y -qq \
            libx11-xcb-dev \
            libnss3 \
            libatk-bridge2.0-0 \
            libgtk-3-0 \
            libdrm2 \
            libgbm1 \
            libasound2

      - name: Install Node dependencies
        run: npm --prefix electron install

      - name: Bundle Python
        run: npm --prefix electron run bundle

      - name: Run parity audit
        run: uv run python scripts/audits/electron_parity_audit.py --mode bundled

      - name: Run browser tests
        run: uv run pytest tests/browser/ --no-header -q --timeout=120 -x --tb=short
        timeout-minutes: 10

      - name: Build Electron app
        run: npm --prefix electron run ${{ matrix.build-script }}
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          APPLE_ID: ${{ secrets.APPLE_ID || '' }}
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID || '' }}
          APPLE_APP_SPECIFIC_PASSWORD: ${{ secrets.APPLE_APP_SPECIFIC_PASSWORD || '' }}
          CSC_LINK: ${{ secrets.MAC_CERT_BASE64 || '' }}
          CSC_KEY_PASSWORD: ${{ secrets.MAC_CERT_PASSWORD || '' }}

      - name: Verify installer
        run: |
          case "${{ matrix.platform }}" in
            macOS)   ls -lh electron/build/*.dmg ;;
            Windows) ls -lh electron/build/*.exe ;;
            Linux)   ls -lh electron/build/*.AppImage ;;
          esac

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: splitshot-${{ matrix.platform }}
          path: |
            electron/build/*.dmg
            electron/build/*.exe
            electron/build/*.AppImage
          if-no-files-found: error

  release:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/download-artifact@v4
      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          files: splitshot-*/*
          generate_release_notes: true
```

Key differences from current CI:
- **matrix.include** with explicit platform labels instead of bare `os`
- **Linux system deps step** — electron-builder on Linux needs these
- **Single bundling call** via `npm run bundle` (no inline steps)
- **Browser tests run on all platforms** (including Linux)
- **Installer verify per platform** with case statement
- **Upload only the platform's artifacts** (cleaner release)
- **`if-no-files-found: error`** — fails CI if build produced nothing

### 4. `electron/package.json` — build scripts

```json
"scripts": {
  "dev": "SPLITSHOT_DEV=1 electron .",
  "start": "npm run bundle && electron .",
  "bundle": "node ../scripts/bundle-python.js",
  "check": "uv run python scripts/audits/electron_parity_audit.py --mode bundled",
  "build:mac": "electron-builder --mac",
  "build:win": "electron-builder --win",
  "build:linux": "electron-builder --linux",
  "build": "electron-builder --mac --win --linux"
}
```

## Validation

### macOS
```bash
npm --prefix electron run bundle
npm --prefix electron run build:mac
ls electron/build/SplitShot-*.dmg
ls electron/assets/icon.icns
```

### Windows
```bash
npm --prefix electron run bundle
npm --prefix electron run build:win
ls electron/build/SplitShot-*.exe
ls electron/assets/icon.ico
```

### Linux
```bash
npm --prefix electron run bundle
npm --prefix electron run build:linux
ls electron/build/SplitShot-*.AppImage

# Verify .desktop MIME entries in the AppImage
./electron/build/SplitShot-*.AppImage --appimage-extract
grep MimeType squashfs-root/*.desktop
# Expected: MimeType=application/x-studio.splitshot.ssproj;
```

### CI
```bash
git tag v1.2.0-test && git push origin v1.2.0-test
# Check Actions tab — 3 parallel builds, all passing
# Release created with 3 artifacts
```

## Done criteria

- [ ] `scripts/bundle-python.js` detects Python version dynamically
- [ ] Python binary path is platform-aware (bin/Scripts)
- [ ] FFmpeg bundled via `static_ffmpeg` on all platforms
- [ ] macOS symlink resolution runs only on macOS, skipped on Win/Linux
- [ ] macOS `.icns` generated in `electron/assets/`
- [ ] Windows `.ico` generated (or documented CI fallback)
- [ ] Linux `.png` generated in `electron/assets/`
- [ ] `electron/package.json` has `linux.mimeTypes` config
- [ ] CI installs Linux system deps for electron-builder
- [ ] CI bundles once, runs parity audit, runs browser tests, builds, verifies
- [ ] CI builds produce `.dmg` / `.exe` / `.AppImage` respectively
- [ ] CI uploads fail if no artifacts found
- [ ] `npm run build:mac` / `build:win` / `build:linux` all documented
- [ ] Proof written, progress updated
