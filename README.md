# Kodi Androide: build con installazione app abilitata

Kodi ufficiale non dichiara il permesso per installare app, quindi Android non mostra
l'interruttore "Installa app sconosciute". Questa repo costruisce un Kodi identico con quel
permesso aggiunto, con un nome di pacchetto diverso (`it.andro.kodi`) per convivere con quello originale.

## Download diretto

Scegli in base al dispositivo. I telefoni e i box recenti sono quasi sempre a 64 bit.

| Dispositivo | Release | File nella cartella `apk/` |
|---|---|---|
| 64 bit (arm64-v8a) | [kodi-androide-arm64-v8a](../../releases/tag/kodi-androide-arm64-v8a) | `apk/kodi-androide-arm64-v8a.apk` |
| 32 bit (armeabi-v7a) | [kodi-androide-armeabi-v7a](../../releases/tag/kodi-androide-armeabi-v7a) | `apk/kodi-androide-armeabi-v7a.apk` |

## Come si costruisce

Da Actions, "Build Kodi APK con installazione abilitata", premi Run workflow e scegli
l'architettura (o `both` per entrambe). Ogni architettura ha una release con un tag fisso,
che viene aggiornata a ogni build, quindi gli indirizzi di download non cambiano.

Per firmare sempre con la stessa chiave aggiungi nei segreti della repo
`KEYSTORE_BASE64`, `KEYSTORE_PASSWORD` e `KEY_ALIAS`. Senza, ogni build usa una chiave nuova
e un APK non si installa sopra quello precedente: va prima disinstallato.
