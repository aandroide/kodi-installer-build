#!/usr/bin/env bash
# Uso: patch_kodi.sh <apk_originale> <apk_non_firmato_output>
#
# Variabili opzionali:
#   APKTOOL       percorso di apktool.jar          (default: apktool.jar)
#   NEW_PACKAGE   nuovo nome pacchetto, 13 caratteri (default: it.andro.kodi)
#   APP_LABEL     nome mostrato nel launcher        (default: Kodi Androide)
#
# Cosa fa:
#  1. aggiunge REQUEST_INSTALL_PACKAGES al manifest
#  2. cambia il nome pacchetto (manifest, provider, codice Java, libreria nativa)
#     cosi l'APK convive con il Kodi originale
#  3. cambia il nome mostrato nel launcher
set -euo pipefail

IN="$1"
OUT="$2"
APKTOOL="${APKTOOL:-apktool.jar}"
OLD_PACKAGE="org.xbmc.kodi"
NEW_PACKAGE="${NEW_PACKAGE:-it.andro.kodi}"
APP_LABEL="${APP_LABEL:-Kodi Androide}"
WORK="$(mktemp -d)"

# La stringa nella libreria nativa si sostituisce solo con una della stessa lunghezza
if [ "${#NEW_PACKAGE}" -ne "${#OLD_PACKAGE}" ]; then
  echo "NEW_PACKAGE deve avere ${#OLD_PACKAGE} caratteri come ${OLD_PACKAGE} (esempio: it.andro.kodi)"
  exit 1
fi
if ! [[ "$NEW_PACKAGE" =~ ^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$ ]]; then
  echo "NEW_PACKAGE non valido: $NEW_PACKAGE"
  exit 1
fi

echo "== Decodifica (con codice smali)"
java -jar "$APKTOOL" d -f -o "$WORK/dec" "$IN"
D="$WORK/dec"
M="$D/AndroidManifest.xml"

echo "== Permesso REQUEST_INSTALL_PACKAGES"
if ! grep -q "REQUEST_INSTALL_PACKAGES" "$M"; then
  sed -i '0,/<uses-permission /s//<uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES"\/>\n    <uses-permission /' "$M"
fi
grep -q "REQUEST_INSTALL_PACKAGES" "$M" || { echo "Inserimento permesso fallito"; exit 1; }

echo "== Nome pacchetto: $OLD_PACKAGE diventa $NEW_PACKAGE"
# manifest: attributo package e authorities dei provider
sed -i "s|package=\"${OLD_PACKAGE}\"|package=\"${NEW_PACKAGE}\"|" "$M"
sed -i "s|android:authorities=\"${OLD_PACKAGE}\.|android:authorities=\"${NEW_PACKAGE}.|g" "$M"
grep -q "package=\"${NEW_PACKAGE}\"" "$M" || { echo "Cambio package fallito"; exit 1; }

# codice Java (smali): solo le stringhe che indicano il pacchetto o le authorities,
# non i nomi delle classi
find "$D" -type d -name 'smali*' -prune -print0 | while IFS= read -r -d '' dir; do
  grep -rlZ --include='*.smali' "org\.xbmc\.kodi" "$dir" | xargs -0 -r sed -i \
    -e "s|\"${OLD_PACKAGE//./\\.}\"|\"${NEW_PACKAGE}\"|g" \
    -e "s#\"${OLD_PACKAGE//./\\.}\.file\"#\"${NEW_PACKAGE}.file\"#g" \
    -e "s#\"${OLD_PACKAGE//./\\.}\.media\"#\"${NEW_PACKAGE}.media\"#g" \
    -e "s#\"${OLD_PACKAGE//./\\.}\.ytdl\"#\"${NEW_PACKAGE}.ytdl\"#g" \
    -e "s|content://${OLD_PACKAGE//./\\.}\.media|content://${NEW_PACKAGE}.media|g" \
    -e "s|ComponentInfo{${OLD_PACKAGE//./\\.}/|ComponentInfo{${NEW_PACKAGE}/|g"
done

# risorse xml che citano le authorities (ricerca globale Android TV)
grep -rlZ "${OLD_PACKAGE//./\\.}\.media" "$D/res" 2>/dev/null | xargs -0 -r sed -i \
  "s|${OLD_PACKAGE//./\\.}\.media|${NEW_PACKAGE}.media|g"

# librerie native: stringa del pacchetto, stessa lunghezza
python3 -I - "$D" "$OLD_PACKAGE" "$NEW_PACKAGE" <<'PY'
import sys, pathlib
root, old, new = sys.argv[1], sys.argv[2].encode(), sys.argv[3].encode()
tot = 0
for so in pathlib.Path(root, "lib").rglob("*.so"):
    data = so.read_bytes()
    n = data.count(old + b"\x00")
    if n:
        so.write_bytes(data.replace(old + b"\x00", new + b"\x00"))
        print(f"  {so.relative_to(root)}: {n} occorrenze")
        tot += n
print(f"  totale stringhe native sostituite: {tot}")
PY

echo "== Nome app: $APP_LABEL"
for f in "$D"/res/values*/strings.xml; do
  sed -i "s|<string name=\"app_name\">Kodi</string>|<string name=\"app_name\">${APP_LABEL}</string>|" "$f"
done

echo "== Ricompilazione"
java -jar "$APKTOOL" b "$D" -o "$OUT"
rm -rf "$WORK"
echo "Creato $OUT"
