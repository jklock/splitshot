# E04 — CI and Release Automation

## Metadata

| Field | Value |
| --- | --- |
| task-id | `E04` |
| status | `pending` |
| depends-on | `E03` |
| risk | `medium` |
| touches-files | `.github/workflows/build-electron.yml`, `electron/package.json`, `activedev/electron/progress.md` |
| forbidden-files | `src/`, `pyproject.toml` |
| proof-file | `activedev/electron/proof/PROOF-E04-runN.md` |

## Goal

Set up GitHub Actions to build Electron installers for macOS, Windows, and Linux on every tag push, then publish them as a GitHub Release.

## Implementation

### `.github/workflows/build-electron.yml`

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
        os: [macos-14, windows-latest, ubuntu-latest]
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

      - name: Bundle Python (macOS)
        if: runner.os == 'macOS'
        run: |
          python3 -m venv electron/bundle/.venv
          electron/bundle/.venv/bin/pip install .
          electron/bundle/.venv/bin/python -c "import static_ffmpeg; static_ffmpeg.add_paths()"
          cp -r src electron/bundle/src
          cp pyproject.toml electron/bundle/

      - name: Bundle Python (Windows)
        if: runner.os == 'Windows'
        run: |
          python -m venv electron/bundle/.venv
          electron/bundle/.venv/Scripts/pip install .
          electron/bundle/.venv/Scripts/python -c "import static_ffmpeg; static_ffmpeg.add_paths()"
          xcopy /E /I src electron/bundle/src
          copy pyproject.toml electron/bundle/

      - name: Bundle Python (Linux)
        if: runner.os == 'Linux'
        run: |
          python3 -m venv electron/bundle/.venv
          electron/bundle/.venv/bin/pip install .
          electron/bundle/.venv/bin/python -c "import static_ffmpeg; static_ffmpeg.add_paths()"
          cp -r src electron/bundle/src
          cp pyproject.toml electron/bundle/

      - name: Install Node dependencies
        run: npm --prefix electron install

      - name: Build Electron app
        run: npm --prefix electron run build
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          APPLE_ID: ${{ secrets.APPLE_ID }}
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
          APPLE_APP_SPECIFIC_PASSWORD: ${{ secrets.APPLE_APP_SPECIFIC_PASSWORD }}
          CSC_LINK: ${{ secrets.MAC_CERT_BASE64 }}
          CSC_KEY_PASSWORD: ${{ secrets.MAC_CERT_PASSWORD }}

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: splitshot-${{ runner.os }}
          path: electron/build/*.{dmg,exe,AppImage}

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

### `electron/package.json` — version sync

Ensure the version in `package.json` stays in sync with the git tag. Add a prebuild script if needed, or rely on the user to bump it manually before tagging.

## Validation

```bash
git tag v1.1.0
git push origin v1.1.0
```

Expected: GitHub Actions builds all three platforms, uploads artifacts, creates a release.

## Done criteria

- [ ] `.github/workflows/build-electron.yml` exists
- [ ] `git push --tags` triggers builds on all 3 platforms
- [ ] macOS `.dmg` is signed and notarized (if Apple credentials configured)
- [ ] Release is created automatically with download links
- [ ] Proof written, progress updated
