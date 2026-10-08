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
#  2. cambia il nome pacchetto (manifest, classi Java, libreria nativa)
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

echo "== Nome pacchetto: $OLD_PACKAGE diventa $NEW_PACKAGE (classi comprese)"
# La libreria nativa costruisce i nomi delle classi Java a partire dal nome del
# pacchetto, quindi vanno rinominate anche le classi, non solo il manifest.
OLD_PATH="${OLD_PACKAGE//./\/}"
NEW_PATH="${NEW_PACKAGE//./\/}"
OLD_RE="${OLD_PACKAGE//./\\.}"

# manifest e risorse xml: ogni occorrenza (package, authorities, nomi classi)
sed -i "s|${OLD_RE}|${NEW_PACKAGE}|g" "$M"
grep -q "package=\"${NEW_PACKAGE}\"" "$M" || { echo "Cambio package fallito"; exit 1; }
grep -rlZ "${OLD_RE}" "$D/res" 2>/dev/null | xargs -0 -r sed -i "s|${OLD_RE}|${NEW_PACKAGE}|g"

# codice smali: sia la forma con punti sia quella con barre, poi si spostano le cartelle
for dir in "$D"/smali*; do
  [ -d "$dir" ] || continue
  grep -rlZ --include='*.smali' -e "${OLD_RE}" -e "${OLD_PATH}" "$dir" | xargs -0 -r sed -i \
    -e "s|${OLD_RE}|${NEW_PACKAGE}|g" \
    -e "s|${OLD_PATH}|${NEW_PATH}|g"
  if [ -d "$dir/$OLD_PATH" ]; then
    mkdir -p "$dir/$(dirname "$NEW_PATH")"
    mv "$dir/$OLD_PATH" "$dir/$NEW_PATH"
  fi
done
if grep -rq -e "${OLD_RE}" -e "${OLD_PATH}" "$D"/smali* "$M" "$D/res" 2>/dev/null; then
  echo "Restano riferimenti al vecchio nome:"
  grep -rl -e "${OLD_RE}" -e "${OLD_PATH}" "$D"/smali* "$M" "$D/res" | head
  exit 1
fi

# librerie native: tutte le forme del nome, stessa lunghezza
python3 -I - "$D" "$OLD_PACKAGE" "$NEW_PACKAGE" <<'PY'
import sys, pathlib
root, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
pairs = [(old, new), (old.replace(".", "/"), new.replace(".", "/")), (old.replace(".", "_"), new.replace(".", "_"))]
tot = 0
for so in pathlib.Path(root, "lib").rglob("*.so"):
    data = so.read_bytes()
    n = 0
    for o, w in pairs:
        o, w = o.encode(), w.encode()
        n += data.count(o)
        data = data.replace(o, w)
    if n:
        so.write_bytes(data)
        print(f"  {so.relative_to(root)}: {n} occorrenze")
        tot += n
print(f"  totale sostituzioni native: {tot}")
PY

echo "== Nome app: $APP_LABEL"
for f in "$D"/res/values*/strings.xml; do
  sed -i "s|<string name=\"app_name\">Kodi</string>|<string name=\"app_name\">${APP_LABEL}</string>|" "$f"
done

echo "== Ricompilazione"
java -jar "$APKTOOL" b "$D" -o "$OUT"
rm -rf "$WORK"
echo "Creato $OUT"
