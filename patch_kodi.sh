#!/usr/bin/env bash
# Uso: patch_kodi.sh <apk_originale> <apk_non_firmato_output>
# Aggiunge REQUEST_INSTALL_PACKAGES al manifest di Kodi e ricompila.
set -euo pipefail

IN="$1"
OUT="$2"
APKTOOL="${APKTOOL:-apktool.jar}"
WORK="$(mktemp -d)"

java -jar "$APKTOOL" d --no-src -f -o "$WORK/dec" "$IN"

MANIFEST="$WORK/dec/AndroidManifest.xml"
if grep -q "REQUEST_INSTALL_PACKAGES" "$MANIFEST"; then
  echo "Permesso gia presente, nulla da aggiungere"
else
  # inserisce subito dopo il primo uses-permission
  sed -i '0,/<uses-permission /s//<uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES"\/>\n    <uses-permission /' "$MANIFEST"
fi
grep -q "REQUEST_INSTALL_PACKAGES" "$MANIFEST" || { echo "Inserimento fallito"; exit 1; }

java -jar "$APKTOOL" b "$WORK/dec" -o "$OUT"
rm -rf "$WORK"
echo "Creato $OUT"
