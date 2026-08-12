#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 /path/to/developer-id.p12 <password>" >&2
  exit 64
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This verifier requires macOS for keychain import checks." >&2
  exit 69
fi

cert_file="$1"
cert_password="$2"

if [[ ! -f "${cert_file}" ]]; then
  echo "Certificate file not found: ${cert_file}" >&2
  exit 66
fi

tmp_dir="$(mktemp -d)"
keychain_file="${tmp_dir}/splitshot-cert-check.keychain-db"
keychain_password="$(openssl rand -base64 24 | tr -d '\n')"

cleanup() {
  security delete-keychain "${keychain_file}" >/dev/null 2>&1 || true
  rm -rf "${tmp_dir}"
}
trap cleanup EXIT

echo "Validating PKCS#12 password..."
openssl pkcs12 -legacy -in "${cert_file}" -info -noout -passin "pass:${cert_password}" >/dev/null

echo "Certificate:"
openssl pkcs12 -legacy -in "${cert_file}" -clcerts -nokeys -passin "pass:${cert_password}" 2>/dev/null | \
  openssl x509 -noout -subject -issuer -serial -dates

echo "Importing into a temporary keychain..."
security create-keychain -p "${keychain_password}" "${keychain_file}" >/dev/null
security unlock-keychain -p "${keychain_password}" "${keychain_file}" >/dev/null
security set-keychain-settings "${keychain_file}" >/dev/null
security list-keychains -d user -s "${keychain_file}" $(security list-keychains -d user | tr -d '"') >/dev/null
if ! security import "${cert_file}" -k "${keychain_file}" -T /usr/bin/codesign -T /usr/bin/productbuild -P "${cert_password}" >/dev/null; then
  echo "macOS rejected the .p12 during security import." >&2
  echo "Re-export the Developer ID Application certificate from Keychain Access and confirm the private key is included." >&2
  exit 1
fi

echo "Available codesigning identities:"
security find-identity -v -p codesigning "${keychain_file}"

echo "Verification passed."
