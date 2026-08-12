# Electron Release Runbook

<!-- Documentation reviewed: 2026-08-11 -->

This is the durable packaging and publishing runbook for SplitShot v1.0.7. The release is feature-frozen; complete validation and defect fixes only, then publish the same release-ready commit on all three platforms.

The approved implementation contract for complete installed-package validation is [Exhaustive Packaged Release Validation Plan](EXHAUSTIVE_PACKAGED_RELEASE_VALIDATION_PLAN.md). Until that plan's zero-gap gates are implemented and passing, the compact proof below describes the current release coverage and must not be represented as exhaustive feature validation.

## Toolchain

Install these tools before source or packaging work:

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/)
- FFmpeg and FFprobe on `PATH` for source development and export checks
- Node.js 22 with npm

From a fresh clone, install locked dependencies:

```bash
uv sync --frozen --extra dev --python 3.12
cd electron
npm ci
cd ..
```

Confirm the source runtime before packaging:

```bash
uv run splitshot --check
```

Electron bundles its Python runtime and media tools. Packaged validation must not rely on host-installed FFmpeg/FFprobe, local-only files, or an existing build directory.

## Local Preflight And Proof

Use the current platform's local preflight before requesting CI packaging:

```bash
uv run python scripts/testing/run_electron_preflight.py
```

The preflight checks the runtime, creates and verifies the Python bundle, runs Electron launch and backend checks, audits source/package parity, launches the source app, builds the current platform's unpacked application, and verifies that application launches.

Create the v1.0.7 source proof bundle with the compact tracked fixture:

```bash
uv run python scripts/testing/verify_e2e_fixture.py \
  tests/fixtures/media/e2e-stage.mp4 --min-shots 1 --min-duration 5
uv run python scripts/testing/run_source_release_proof.py \
  --artifact-root artifacts/v107-release-proof/source
```

Proof output belongs under the ignored `artifacts/v107-release-proof/` tree. The tracked `tests/fixtures/media/e2e-stage.mp4` is the canonical media input for source export, packaged E2E, shot detection, FFprobe, and OCR gates.

## Platform Packages

Package on the matching operating system or use its GitHub Actions workflow. Electron Builder produces:

| Platform | Command | Release artifact |
| --- | --- | --- |
| macOS | `npm --prefix electron run build:mac` | DMG |
| Windows | `npm --prefix electron run build:win` | NSIS `.exe` installer |
| Linux | `npm --prefix electron run build:linux` | AppImage |

Outputs are written below `electron/build/`. The Windows and Linux configurations also create unpacked directory targets for smoke validation; those directories are not release downloads.

For ordinary macOS iteration, avoid rebuilding the DMG:

```bash
npm --prefix electron run build:app:mac
uv run python scripts/testing/run_electron_iterate.py \
  --tier unpacked --scenario launch --build-if-needed
```

For a local macOS release package, the supported helper exports the active Developer ID identity to a temporary credential, verifies it, builds the DMG, and installs the application for validation:

```bash
npm --prefix electron run build:mac:local
```

If local notarization credentials are unavailable, that helper explicitly disables notarization. Such a build is suitable for local validation, not publication.

## macOS Signing And Notarization

The publishing workflow requires a Developer ID Application certificate including its private key:

- `MAC_CERT_BASE64`: base64-encoded `.p12`
- `MAC_CERT_PASSWORD`: `.p12` password

Verify the export before changing secrets:

```bash
scripts/release/verify_macos_cert.sh /path/to/DeveloperID.p12 'password'
```

Prefer App Store Connect API-key notarization credentials:

- `APPLE_API_KEY`: contents of the `.p8` key
- `APPLE_API_KEY_ID`
- `APPLE_API_ISSUER`

The supported fallback is the complete Apple ID set:

- `APPLE_ID`
- `APPLE_APP_SPECIFIC_PASSWORD`
- `APPLE_TEAM_ID`

Do not mix incomplete credential sets. The publishing workflows import the certificate into a temporary keychain, materialize the API key only for the job, sign and notarize the application, verify the signed app, and delete temporary credentials during cleanup.

## CI Validation

Use these GitHub Actions workflows on the intended release commit:

- **Test macOS**: source tests plus packaged DMG validation on `macos-14`
- **Test Windows**: source tests plus packaged NSIS validation on `windows-latest`
- **Test Linux**: source tests plus packaged AppImage validation on `ubuntu-latest`

The Test macOS workflow signs its validation DMG but explicitly disables notarization. This keeps ordinary clean-runner package proof independent of Apple agreement availability. The Build macOS and Release workflows retain mandatory notarization; publication is still blocked when Apple credentials or agreements are invalid.

Run each with `workflow_dispatch`, then inspect both its package and `e2e-artifacts-*` uploads. Copy the validation bundles into:

```text
artifacts/v107-release-proof/github-review/macos/
artifacts/v107-release-proof/github-review/windows/
artifacts/v107-release-proof/github-review/linux/
```

The **Build macOS**, **Build Windows**, and **Build Linux** workflows are one-platform packaging helpers. A successful build is not release proof: the corresponding clean-runner Test workflow must launch the packaged artifact, import the tracked fixture, analyze it, and export successfully.

For local package-native proof, pass the built artifact and canonical fixture to the packaged harness. On macOS, for example:

```bash
uv run python scripts/testing/test_packaged_artifact.py \
  --artifact electron/build/SplitShot-1.0.7-arm64.dmg \
  --script scripts/testing/test_packaged_app_e2e.py \
  --script-arg=--scope \
  --script-arg=release-proof \
  --script-arg=--artifact-root \
  --script-arg=artifacts/v107-release-proof/packaged-local-mac \
  --script-arg=--primary-video \
  --script-arg=tests/fixtures/media/e2e-stage.mp4
```

Use the artifact filename produced for the host architecture. Package-native proof must be rerun from a clean output location; stale artifacts do not count.

## Publish v1.0.7

The release-ready commit must already contain version `1.0.7` in `pyproject.toml`, `src/splitshot/__init__.py`, `uv.lock`, `electron/package.json`, and `electron/package-lock.json`, plus this changelog entry.

Extract the exact GitHub release body:

```bash
uv run python scripts/release/extract_release_notes.py v1.0.7 \
  --output artifacts/release-notes.md
```

After all three Test workflows pass, merge the release-ready commit to `main`, create the semver tag, and push it:

```bash
git tag -a v1.0.7 -m "SplitShot v1.0.7"
git push origin v1.0.7
```

`.github/workflows/release.yml` is the only publisher. A `v1.0.7` tag builds and validates the macOS DMG, Windows NSIS installer, and Linux AppImage, extracts the matching changelog section, and publishes those artifacts together. The manual **Release** dispatch may build an exact `release_ref` with `release_tag=v1.0.7`; do not use a moving tag or a different commit per platform.

If an existing release body is stale after the validated release commit is published:

```bash
gh release edit v1.0.7 \
  --title "SplitShot 1.0.7" \
  --notes-file artifacts/release-notes.md \
  --latest
```

## Failure Handling

- Inspect the exact failing GitHub Actions job and its uploaded proof before changing code or workflows.
- Fix and rerun that lane before retagging.
- Treat missing packaged FFmpeg/FFprobe, use of local-only fixtures, stale outputs, or child calls to bare `uv`/`python` as release blockers.
- Do not publish when only package creation passed; package-native validation must also pass on macOS, Windows, and Linux.
- Do not create temporary or moving release tags for smoke testing.

## Related Documentation

- [Development setup](DEVELOPING.md)
- [Governance](GOVERNANCE.md)
- [Changelog](../../CHANGELOG.md)
