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

## Aggiornamenti automatici

A ogni build la action scrive `apk/version.json` con versione, indirizzo, dimensione e impronta
sha256 di ogni architettura. L'addon `addon/script.kodiandroide.updater` lo legge, confronta la
versione di Kodi in esecuzione con l'ultima pubblicata e, se serve, scarica l'APK giusto,
ne controlla l'impronta e avvia l'installazione. Android chiede sempre una conferma.

Per pubblicare una versione nuova di Kodi basta rilanciare il workflow indicando la nuova
versione, con l'opzione "Salva anche gli APK nella cartella apk/" attiva.
Il controllo funziona solo con il Kodi Androide, firmato sempre con la stessa chiave.

## Addon incluso nell'APK

Il workflow ha l'opzione `bundle_addons` (attiva di default): gli addon nella cartella `addon/` della repo
(oggi `script.kodiandroide.updater`) vengono inseriti dentro l'APK come addon di sistema disattivabili.
Quindi non serve più installare lo zip a mano. Per aggiornare l'addon incluso bisogna rigenerare l'APK.

## Avviso quando esce una nuova versione di Kodi

Il workflow "Controlla nuova versione di Kodi" gira ogni giorno e confronta l'ultima versione stabile di Kodi
con quella in `apk/version.json`. Se Kodi e piu avanti apre una segnalazione (issue) nella repo e GitHub ti avvisa
con la notifica dell'app e con la mail del tuo account. Non costruisce nulla da solo: la build la lanci tu.
Per provarlo: Actions, "Controlla nuova versione di Kodi", Run workflow, campo prova con per esempio `99.0-Prova`.
