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

## GitHub Actions Workflows

Electron packaging and release work is split across dedicated workflows:

- `.github/workflows/build-macos.yml`
- `.github/workflows/build-windows.yml`
- `.github/workflows/build-linux.yml`
- `.github/workflows/release.yml`
- platform smoke/test coverage in `.github/workflows/test-macos.yml`, `test-windows.yml`, and `test-linux.yml`

The three `build-*` workflows are manual packaging helpers. They package one platform target each and upload artifacts for inspection, but they do not publish GitHub releases. `release.yml` is the only publisher. It runs on semver tags like `v1.0.1`, builds all three platforms, extracts the matching release notes from [../../CHANGELOG.md](../../CHANGELOG.md) through `scripts/release/extract_release_notes.py`, and publishes the GitHub release with all three platform artifacts.

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

## Smoke Builds

Use the platform-specific build workflows and test workflows for packaging smoke checks.

- Choose the target branch in the Actions UI.
- Run the matching `build-macos.yml`, `build-windows.yml`, or `build-linux.yml` workflow when you want a packaging artifact for that platform without cutting a release.
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

## Troubleshooting

- `MAC verification failed during PKCS12 import`: the `.p12` payload and `MAC_CERT_PASSWORD` do not match, or the export is malformed or incompatible with macOS `security import`. Re-export it from Keychain Access with the private key included.
- Missing identity after import: the exported `.p12` does not include the private key, or it is not the expected Developer ID Application certificate.
- Notarization credential failure: set the full API key triple, or set the full Apple ID fallback triple. Do not mix partial sets. For the API key path, store the `.p8` file contents in the `APPLE_API_KEY` secret so the workflow can materialize it to a temporary file for `electron-builder`.

## Read This Next

- [GOVERNANCE.md](GOVERNANCE.md)
- [../../CHANGELOG.md](../../CHANGELOG.md)
