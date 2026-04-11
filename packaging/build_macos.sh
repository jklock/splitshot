#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

uv run pyinstaller --noconfirm packaging/splitshot.spec

rm -f dist/SplitShot.dmg
hdiutil create \
  -volname "SplitShot" \
  -srcfolder "dist/SplitShot.app" \
  -ov \
  -format UDZO \
  "dist/SplitShot.dmg"

echo "Built dist/SplitShot.dmg"
