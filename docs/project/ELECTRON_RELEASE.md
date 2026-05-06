# Electron Release and Signing

This is the supported path for SplitShot Electron macOS signing and notarization.

## Secrets

Required for macOS signing:

- `MAC_CERT_BASE64`: base64-encoded Developer ID Application `.p12`
- `MAC_CERT_PASSWORD`: password for that `.p12`

Preferred notarization credentials:

- `APPLE_API_KEY`
- `APPLE_API_KEY_ID`
- `APPLE_API_ISSUER`

Fallback notarization credentials:

- `APPLE_ID`
- `APPLE_APP_SPECIFIC_PASSWORD`
- `APPLE_TEAM_ID`

The workflow prefers the API key set. If any API key variable is set, all three must be set. The Apple ID fallback is only used when the API key set is absent.

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

## GitHub Actions Workflow

`/.github/workflows/build-electron.yml` has two entry points:

- `workflow_dispatch`: manual smoke build for a selected branch
- `push` on `v*` tags: real release build and GitHub release publishing

The macOS job now:

1. Decodes `MAC_CERT_BASE64` to a temporary `.p12`.
2. Validates it with OpenSSL.
3. Imports it into a temporary keychain.
4. Verifies the codesigning identity.
5. Passes the temp `.p12` path to `electron-builder` via `CSC_LINK`.
6. Uses `CSC_KEY_PASSWORD` for signing.
7. Lets `electron-builder` notarize with API key credentials when available, or Apple ID credentials as fallback.

If no notarization credentials are configured, the workflow signs the app and skips notarization.

## Smoke Builds

Use GitHub Actions `workflow_dispatch` for signing and notarization smoke tests.

- Choose the target branch in the Actions UI.
- Confirm the `Prepare macOS signing certificate` step passes before looking at the builder output.
- Use these runs to validate secret rotation, cert export, and notarization credentials.

Do not create `ci-test` or debug release tags for smoke testing.

## Real Releases

Use a real `v*` tag only when the smoke workflow is already green.

Tag-triggered runs:

- build the signed installers
- upload the build artifacts
- create the GitHub release

## Troubleshooting

- `MAC verification failed during PKCS12 import`: the `.p12` payload and `MAC_CERT_PASSWORD` do not match, or the export is malformed or incompatible with macOS `security import`. Re-export it from Keychain Access with the private key included.
- Missing identity after import: the exported `.p12` does not include the private key, or it is not the expected Developer ID Application certificate.
- Notarization credential failure: set the full API key triple, or set the full Apple ID fallback triple. Do not mix partial sets.
