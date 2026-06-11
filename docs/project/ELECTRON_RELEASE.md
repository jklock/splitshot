# Electron Release and Signing

This is the supported path for SplitShot Electron packaging and release work, with macOS signing and notarization as the most specialized platform-specific flow.

## Secrets

Required for macOS signing:

- `MAC_CERT_BASE64`: base64-encoded Developer ID Application `.p12`
- `MAC_CERT_PASSWORD`: password for that `.p12`

Preferred notarization credentials:

- `APPLE_API_KEY` (the `.p8` key contents stored as a GitHub secret)
- `APPLE_API_KEY_ID`
- `APPLE_API_ISSUER`

Fallback notarization credentials:

- `APPLE_ID`
- `APPLE_APP_SPECIFIC_PASSWORD`
- `APPLE_TEAM_ID`

The workflow prefers the API key set. If any API key variable is set, all three must be set. The Apple ID fallback is only used when the API key set is absent.
In GitHub Actions, `APPLE_API_KEY` is written to a temporary `AuthKey_<id>.p8` file and that file path is what `electron-builder` receives for notarization.

## Export the Developer ID `.p12`

On macOS:

1. Open Keychain Access.
2. Select the `login` keychain.
3. Find `Developer ID Application: John Klockenkemper (7DJ75AWV5R)`.
4. Expand the certificate and confirm the private key is present.
5. Right-click the certificate and choose `Export`.
6. Save it as a `.p12` file and assign a password.

Encode the exported file for GitHub Actions:

```bash
base64 -i /path/to/DeveloperID.p12 | tr -d '\n'
```

Set that output as `MAC_CERT_BASE64`, and set the matching password as `MAC_CERT_PASSWORD`.

## Verify the `.p12` Before Updating Secrets

Run the local verifier on macOS:

```bash
scripts/release/verify_macos_cert.sh /path/to/DeveloperID.p12 'your-password'
```

The script checks:

- the `.p12` password
- certificate subject, issuer, serial, and validity dates
- import into a temporary keychain
- visible codesigning identities after import

If this script fails, do not rotate the GitHub secrets yet.
An OpenSSL-only pass is not enough. The `.p12` must also pass macOS `security import`, because that is the same import path used by GitHub Actions and `electron-builder`.

If you need to rebuild a `.p12` from a matching certificate and private key outside Keychain Access, use PKCS#12 settings that macOS accepts:

```bash
openssl pkcs12 -export \
  -inkey /path/to/devid-key.pem \
  -in /path/to/developerID_application.pem \
  -name 'Developer ID Application: John Klockenkemper (7DJ75AWV5R)' \
  -keypbe PBE-SHA1-3DES \
  -certpbe PBE-SHA1-3DES \
  -macalg sha1 \
  -out /path/to/developer-id-compatible.p12
```

The resulting file must still pass `scripts/release/verify_macos_cert.sh` before you upload it to GitHub Actions.

## Local-First Release Gate

Before any GitHub Actions Electron run, complete the local preflight on the target platform:

```bash
uv run python scripts/testing/run_electron_preflight.py
```

That script is the source-of-truth gate for:

- runtime check
- Python bundle generation and verification
- Electron launch-intent unit tests
- headless backend tests
- parity audit
- source Electron smoke
- current-platform smoke packaging
- packaged-app launch verification

Do not use GitHub Actions as the first place to discover source-level or parity failures.

For `v1.0.6`, preflight alone is not enough. The release gate also requires:

- source proof bundle under `artifacts/v106-release-proof/source/`
- local packaged macOS release-proof bundle under `artifacts/v106-release-proof/packaged-local-mac/`
- GitHub packaged validation review bundles under `artifacts/v106-release-proof/github-review/{macos,windows,linux}/`

Launch-only proof, package-only proof, or build-only proof is insufficient.

## GitHub Actions Workflows

Electron packaging and release work is split across dedicated workflows:

- `.github/workflows/build-macos.yml`
- `.github/workflows/build-windows.yml`
- `.github/workflows/build-linux.yml`
- `.github/workflows/release.yml`
- platform smoke/test coverage in `.github/workflows/test-macos.yml`, `test-windows.yml`, and `test-linux.yml`

The three `build-*` workflows are manual packaging helpers. They package one platform target each and upload artifacts for inspection, but they do not publish GitHub releases. `release.yml` is the only publisher. It runs on semver tags like `v1.0.1`, builds all three platforms, extracts the matching release notes from [../../CHANGELOG.md](../../CHANGELOG.md) through `scripts/release/extract_release_notes.py`, and publishes the GitHub release with all three platform artifacts.

The three `test-*` workflows are the branch-validation path. On pull requests they run the non-Electron Python suites. On `workflow_dispatch` they also run that platform's Electron package and validate jobs, which is the right branch-level GitHub smoke path when you want packaged proof without cutting a semver tag.

## GitHub Pipeline Runbook

Use this decision tree when another agent needs packaged Electron proof from GitHub:

1. Run the source proof bundle first:

```bash
uv run python scripts/testing/run_v106_source_release_proof.py --artifact-root artifacts/v106-release-proof/source
```

2. Run the broader local gates:

```bash
uv run pytest tests/browser/
uv run pytest tests/export/
uv run splitshot --check
uv run python scripts/testing/run_test_suite.py --mode all-together --format table
```

3. Run the local preflight:

```bash
uv run python scripts/testing/run_electron_preflight.py
```

4. Run the local packaged macOS release-proof lane:

```bash
uv run python scripts/testing/test_packaged_artifact.py \
  --artifact electron/build/SplitShot-1.0.6-arm64.dmg \
  --script scripts/testing/test_packaged_app_e2e.py \
  --script-arg=--scope \
  --script-arg=release-proof \
  --script-arg=--artifact-root \
  --script-arg=artifacts/v106-release-proof/packaged-local-mac \
  --script-arg=--primary-video \
  --script-arg=docs/Clip1.MP4
```

5. For one-platform packaging on the current branch without the broader test workflow, run one of:
   - `Build macOS`
   - `Build Windows`
   - `Build Linux`
6. For branch-level validation that also exercises packaged artifact validation, run one of:
   - `Test macOS`
   - `Test Windows`
   - `Test Linux`
7. In the Actions UI, choose `Run workflow`, pick the target branch/ref, and wait for both the package and validate jobs to finish on that platform.
8. Download artifacts from the successful run:
   - `splitshot-macos` for `.dmg`
   - `splitshot-windows` for `.exe`
   - `splitshot-linux` for `.AppImage`
   - `e2e-artifacts-*` for packaged validation logs, screenshots, timings, summaries, and export proof
9. Review the packaged validation bundles under:
   - `artifacts/v106-release-proof/github-review/macos/`
   - `artifacts/v106-release-proof/github-review/windows/`
   - `artifacts/v106-release-proof/github-review/linux/`
10. For a coordinated publish, use only `Release`. Either:
   - push a semver tag such as `v1.0.6`, or
   - run `Release` manually with `release_ref=<commit-or-branch>` and `release_tag=v1.0.6`
11. `Release` must be the only workflow that creates or edits the GitHub release body and uploads the three platform artifacts to the release.

Do not use `build-*` runs as release proof by themselves. They package artifacts, but they do not perform the clean-runner packaged validation that the `test-*` workflow-dispatch path and `release.yml` do.

## Agent Checklist

When handing this flow to another agent, require this exact order:

1. Prove the source app locally:
   - targeted Stage/browser truth tests
   - `uv run python scripts/testing/run_v106_source_release_proof.py --artifact-root artifacts/v106-release-proof/source`
   - `uv run pytest tests/browser/`
   - `uv run pytest tests/export/`
   - `uv run splitshot --check`
   - `uv run python scripts/testing/run_test_suite.py --mode all-together --format table`
2. Run local Electron preflight:

```bash
uv run python scripts/testing/run_electron_preflight.py
```

3. Run the local packaged macOS proof bundle:

```bash
uv run python scripts/testing/test_packaged_artifact.py \
  --artifact electron/build/SplitShot-1.0.6-arm64.dmg \
  --script scripts/testing/test_packaged_app_e2e.py \
  --script-arg=--scope \
  --script-arg=release-proof \
  --script-arg=--artifact-root \
  --script-arg=artifacts/v106-release-proof/packaged-local-mac \
  --script-arg=--primary-video \
  --script-arg=docs/Clip1.MP4
```

4. On the intended release ref, run:
   - `Test macOS`
   - `Test Windows`
   - `Test Linux`
5. Save both the platform package artifacts and the `e2e-artifacts-*` validation bundles from those runs.
6. Review the uploaded packaged validation artifacts for screenshots, summary JSON, timings, export proof, and logs.
7. Only after those three packaged validation lanes are green, use `Release` to publish or to perform the final release dry run with `release_ref` and `release_tag`.

If steps 3 through 6 are not green, the branch is not release-ready regardless of local build success.

Runner targets:

- macOS packaging: GitHub-hosted `macos-14`
- Windows packaging: GitHub-hosted `windows-latest`
- Linux packaging: GitHub-hosted `ubuntu-latest`

The macOS packaging job:

1. Decodes `MAC_CERT_BASE64` to a temporary `.p12`.
2. Validates it with OpenSSL.
3. Imports it into a temporary keychain.
4. Verifies the codesigning identity.
5. Passes the temp `.p12` path to `electron-builder` via `CSC_LINK`.
6. Uses `CSC_KEY_PASSWORD` for signing.
7. Lets `electron-builder` notarize with API key credentials when available, or Apple ID credentials as fallback.

The release and macOS packaging workflows now fail when notarization secrets are missing or incomplete. They no longer silently ship a signed-but-not-notarized macOS artifact.

## Hard Rules From The v1.0.4 Failure Chain

These rules exist because the release path broke repeatedly when they were not enforced.

- Treat the exact failed GitHub Actions lane as the source of truth. Download or inspect that specific job log before changing workflows, retagging, or blaming another platform.
- Packaged validators must be self-contained. Do not rely on gitignored/local-only fixtures, host `PATH` ffmpeg/ffprobe, or nested child-process calls to bare `uv`/`python` executables when the running script can do the work directly.
- A green package build is not enough. The clean-runner validate job must prove the built artifact actually launches, imports media, analyzes, and exports.
- App notarization is not the same thing as DMG stapling. Verify the signed/notarized `.app`, then validate the installed DMG/app path in the macOS validate lane. Do not add DMG stapling steps unless the DMG itself is the notarized ticket target.
- Do not retag until the exact failing lane is understood and the fix is tied to that lane's failure mode.

## Smoke Builds

Use the platform-specific build workflows and test workflows for packaging smoke checks.

- Choose the target branch in the Actions UI.
- Run `Build macOS`, `Build Windows`, or `Build Linux` when you want a packaging artifact for one platform without the broader validation ladder.
- Run `Test macOS`, `Test Windows`, or `Test Linux` from `workflow_dispatch` when you want branch-level packaged validation on a clean runner.
- Run the local Electron preflight first.
- Confirm the `Prepare macOS signing certificate` step passes before looking at the builder output.
- Confirm the `Prepare macOS notarization credentials` step passes and that `Verify notarization` validates the built app.
- Use these runs to validate packaging, secret rotation, cert export, signing, notarization, and packaged-app launch.

Do not create fake release tags for smoke testing.

## Real Releases

Use the semver tag flow when you want a coordinated three-platform release. The existing first-release baseline is `v1.0.0`. Use the next patch tag, such as `v1.0.1`, for the next normal release.

1. Update the versioned files in the repo.
2. Finalize the matching release notes section in [../../CHANGELOG.md](../../CHANGELOG.md).
3. Merge the release-ready state into `main`.
4. Extract the exact release body:

```bash
uv run python scripts/release/extract_release_notes.py v1.0.1 --output artifacts/release-notes.md
```

5. Create and push the release tag:

```bash
git tag -a v1.0.1 -m "SplitShot v1.0.1"
git push origin v1.0.1
```

6. Let `release.yml` publish the GitHub release with macOS, Linux, and Windows artifacts attached.

If you need to prove the release workflow before pushing the final tag, use the manual `Release` dispatch with:

- `release_ref`: the exact branch or commit to build
- `release_tag`: the semver tag the workflow should publish or update

Use that only when the branch already matches the intended release contents. Do not point `release_tag` at a moving alias.

## Troubleshooting

- `MAC verification failed during PKCS12 import`: the `.p12` payload and `MAC_CERT_PASSWORD` do not match, or the export is malformed or incompatible with macOS `security import`. Re-export it from Keychain Access with the private key included.
- Missing identity after import: the exported `.p12` does not include the private key, or it is not the expected Developer ID Application certificate.
- Notarization credential failure: set the full API key triple, or set the full Apple ID fallback triple. Do not mix partial sets. For the API key path, store the `.p8` file contents in the `APPLE_API_KEY` secret so the workflow can materialize it to a temporary file for `electron-builder`.

## Read This Next

- [GOVERNANCE.md](GOVERNANCE.md)
- [../../CHANGELOG.md](../../CHANGELOG.md)
