#!/bin/bash
# MANUAL ONLY: sign locally after explicit approval. Never uploads anything.
set -euo pipefail
if [ "${NOYOUPUB_RELEASE_APPROVED:-}" != "YES" ]; then
  echo 'No action taken. Explicit signing and license approval are required.' >&2
  exit 2
fi
: "${DEVELOPER_ID_APPLICATION:?Use a real Developer ID Application identity already present in Keychain}"
: "${NOTARY_KEYCHAIN_PROFILE:?Use an existing notarytool Keychain profile name}"
: "${APP_PATH:?Set the reviewed app path}"
: "${SIGNING_INVENTORY:?Set the reviewed list of nested code in inside-out order}"
while IFS= read -r relative; do
  [ -n "$relative" ] || continue
  case "$relative" in /*|*..*) echo 'Invalid signing inventory path' >&2; exit 2;; esac
  codesign --force --options runtime --timestamp --sign "$DEVELOPER_ID_APPLICATION" "$APP_PATH/$relative"
done < "$SIGNING_INVENTORY"
# Signing changes Mach-O bytes. Seal those exact signed bytes in the app's
# protected resource manifest before signing the containing bundle.
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
python3 "$SCRIPT_DIR/seal_runtime.py" --resources "$APP_PATH/Contents/Resources"
python3 "$SCRIPT_DIR/audit_runtime.py" --vendor "$APP_PATH/Contents/Resources"
codesign --force --options runtime --timestamp --sign "$DEVELOPER_ID_APPLICATION" "$APP_PATH"
codesign --verify --deep --strict "$APP_PATH"
echo 'App signed locally. No upload performed. Follow docs/RELEASE.md to notarize a ZIP, staple the app, then build and notarize the final DMG.'
