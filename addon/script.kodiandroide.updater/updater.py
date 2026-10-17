# -*- coding: utf-8 -*-
"""
Aggiornatore di Kodi Androide.

Legge version.json da GitHub, confronta la versione di Kodi in esecuzione con l'ultima
pubblicata per la stessa architettura, scarica l'APK, ne controlla l'impronta sha256 e
avvia l'installer di Android. Android chiede sempre la conferma dell'utente.
"""
import json
import os
import platform
import struct
import time
from urllib.request import Request, urlopen

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

import core

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
TITLE = ADDON.getAddonInfo('name')
UA = 'Mozilla/5.0 (Linux; Android 14) KodiAndroideUpdater'

CHECK_EVERY = 24 * 3600
REMIND_EVERY = 3 * 24 * 3600


def log(msg):
    xbmc.log('[%s] %s' % (ADDON_ID, msg), xbmc.LOGINFO)


# ------------------------------------------------------------------ stato

def _state_file():
    folder = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
    if not os.path.isdir(folder):
        os.makedirs(folder)
    return os.path.join(folder, 'state.json')


def load_state():
    try:
        with open(_state_file(), 'r') as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_state(state):
    try:
        with open(_state_file(), 'w') as handle:
            json.dump(state, handle)
    except Exception as err:
        log('Impossibile salvare lo stato: %r' % err)


def last_check_age():
    """Secondi trascorsi dall'ultimo controllo riuscito."""
    return time.time() - float(load_state().get('last_check', 0))


# ------------------------------------------------------------ informazioni

def is_android():
    return xbmc.getCondVisibility('System.Platform.Android')


def kodi_package():
    for spec in ('special://home/', 'special://xbmc/', 'special://profile/'):
        try:
            package = core.package_from_path(xbmcvfs.translatePath(spec))
        except Exception:
            continue
        if package:
            return package
    return 'org.xbmc.kodi'


def installed_version():
    return core.parse_version(xbmc.getInfoLabel('System.BuildVersion'))


def manifest_url():
    return (ADDON.getSetting('version_url') or '').strip() or core.DEFAULT_URL


def fetch_manifest():
    request = Request(manifest_url(), headers={'User-Agent': UA, 'Cache-Control': 'no-cache'})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode('utf-8'))


# ---------------------------------------------------------------- download

def _download_dir():
    folder = os.path.join(xbmcvfs.translatePath('special://temp/'), 'androide_update')
    if not os.path.isdir(folder):
        os.makedirs(folder)
    return folder


def _clean_dir(folder):
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        try:
            if os.path.isfile(path):
                os.remove(path)
        except Exception as err:
            log('Pulizia fallita %s: %r' % (path, err))


def _free_bytes(folder):
    try:
        stat = os.statvfs(folder)
        return stat.f_bavail * stat.f_frsize
    except Exception:
        return None


def download_apk(build):
    """Scarica l'APK e ne verifica la dimensione e l'impronta. Ritorna il percorso del file
    oppure None se l'utente annulla o il file non e valido."""
    dialog = xbmcgui.Dialog()
    folder = _download_dir()
    _clean_dir(folder)
    size = int(build.get('size') or 0)
    free = _free_bytes(folder)
    if size and free is not None and free < size * 2 + 50 * 1048576:
        dialog.ok(TITLE, 'Spazio libero insufficiente. Servono circa %d MB, '
                         'ne sono disponibili %d MB.' % ((size * 2) // 1048576 + 50, free // 1048576))
        return None

    dest = os.path.join(folder, str(build.get('file') or 'kodi-androide-update.apk'))
    progress = xbmcgui.DialogProgress()
    progress.create(TITLE, 'Download di Kodi %s' % build.get('version'))
    try:
        request = Request(build['url'], headers={'User-Agent': UA})
        with urlopen(request, timeout=30) as response, open(dest, 'wb') as handle:
            total = int(response.headers.get('Content-Length') or size or 0)
            done = 0
            while True:
                chunk = response.read(262144)
                if not chunk:
                    break
                handle.write(chunk)
                done += len(chunk)
                if total:
                    progress.update(int(done * 100 / total),
                                    'Scaricati %d di %d MB' % (done // 1048576, total // 1048576))
                if progress.iscanceled():
                    raise RuntimeError('annullato')
    except Exception as err:
        progress.close()
        log('Download fallito: %r' % err)
        _clean_dir(folder)
        if str(err) != 'annullato':
            dialog.ok(TITLE, 'Download fallito: %s' % err)
        return None
    progress.close()

    if size and os.path.getsize(dest) != size:
        dialog.ok(TITLE, 'Il file scaricato e incompleto. Riprova piu tardi.')
        _clean_dir(folder)
        return None
    expected = str(build.get('sha256') or '').lower()
    if expected and core.sha256_file(dest) != expected:
        log('Impronta sha256 diversa da quella attesa')
        dialog.ok(TITLE, 'Il file scaricato non corrisponde a quello pubblicato. '
                         'Non lo installo.')
        _clean_dir(folder)
        return None
    return dest


# ------------------------------------------------------------ installazione

def start_install(path):
    uri = core.install_uri(kodi_package(), path)
    log('Installazione: %s' % uri)
    xbmc.executebuiltin('StartAndroidActivity("","android.intent.action.VIEW",'
                        '"application/vnd.android.package-archive","%s")' % uri)


def update_now(build):
    dialog = xbmcgui.Dialog()
    path = download_apk(build)
    if not path:
        return False
    dialog.ok(TITLE, 'Download completato. Ora Android ti chiede di confermare '
                     'l\'aggiornamento: tocca Installa. Kodi si chiude durante l\'installazione '
                     'e i tuoi dati restano al loro posto. Se Android chiede il permesso '
                     'di installare da questa app, concedilo e ripeti l\'aggiornamento.')
    start_install(path)
    return True


# ---------------------------------------------------------------- controllo

def check(manual=False):
    """Controlla se c'e una versione nuova. Con manual=False non mostra nulla se non c'e
    niente da fare. Ritorna True se ha proposto o avviato un aggiornamento."""
    dialog = xbmcgui.Dialog()
    if not is_android():
        if manual:
            dialog.ok(TITLE, 'L\'aggiornamento funziona solo su Android.')
        return False

    try:
        manifest = fetch_manifest()
    except Exception as err:
        log('Lettura di version.json fallita: %r' % err)
        if manual:
            dialog.ok(TITLE, 'Non riesco a leggere le informazioni sugli aggiornamenti: %s' % err)
        return False

    state = load_state()
    state['last_check'] = time.time()
    save_state(state)

    package = kodi_package()
    wanted = manifest.get('package')
    if wanted and package != wanted:
        log('Pacchetto in uso %s diverso da %s: nessun aggiornamento proposto' % (package, wanted))
        if manual:
            dialog.ok(TITLE, 'Questo non e il Kodi Androide (pacchetto %s invece di %s), '
                             'quindi non posso aggiornarlo da qui.' % (package, wanted))
        return False

    arch = core.detect_arch(struct.calcsize('P') * 8, platform.machine())
    build = core.pick_build(manifest, arch)
    if not build:
        log('Nessuna build pubblicata per %s' % arch)
        if manual:
            dialog.ok(TITLE, 'Non c\'e ancora una versione pubblicata per questo dispositivo (%s).'
                      % arch)
        return False

    local = installed_version()
    remote = core.parse_version(build.get('version'))
    log('Installata %s, pubblicata %s (%s)' % (core.format_version(local),
                                               core.format_version(remote), arch))
    if not core.is_newer(remote, local):
        if manual:
            dialog.ok(TITLE, 'Kodi e gia aggiornato, versione %s.' % core.format_version(local))
        return False

    if not manual and not core.should_remind(state, build['version'], time.time(), REMIND_EVERY):
        return False

    megabytes = int(build.get('size') or 0) // 1048576
    question = ('E disponibile Kodi %s, hai la %s.\nScarico e installo adesso? '
                'Il file pesa circa %d MB.'
                % (core.format_version(remote), core.format_version(local), megabytes))
    if dialog.yesno(TITLE, question, nolabel='Piu tardi', yeslabel='Aggiorna'):
        update_now(build)
    else:
        state = load_state()
        state['declined_version'] = build['version']
        state['declined_at'] = time.time()
        save_state(state)
    return True
