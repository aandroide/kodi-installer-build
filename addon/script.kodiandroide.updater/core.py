# -*- coding: utf-8 -*-
"""
Logica pura dell'aggiornatore, senza dipendenze da Kodi, cosi si puo provare da sola.
"""
import hashlib
import re

DEFAULT_URL = ('https://raw.githubusercontent.com/aandroide/kodi-installer-build/'
               'master/apk/version.json')


def parse_version(text):
    """Estrae la versione numerica iniziale. Esempi: '21.3' o '21.3 (21.3.0) Git:2026'
    danno (21, 3). Ritorna una tupla vuota se non trova numeri."""
    match = re.search(r'(\d+(?:\.\d+)*)', str(text or ''))
    if not match:
        return ()
    return tuple(int(part) for part in match.group(1).split('.'))


def format_version(version):
    return '.'.join(str(part) for part in version)


def is_newer(remote, local):
    """True se la versione remota e piu alta di quella installata. Le tuple vengono
    allineate con zeri, quindi 21.3 e 21.3.0 risultano uguali."""
    if not remote or not local:
        return False
    size = max(len(remote), len(local))
    pad = lambda v: tuple(v) + (0,) * (size - len(v))
    return pad(remote) > pad(local)


def detect_arch(pointer_bits, machine=''):
    """Architettura del Kodi in esecuzione. Conta la dimensione dei puntatori del processo
    e non il processore: una Fire Stick con processore a 64 bit ma sistema a 32 bit
    esegue Kodi a 32 bit e deve ricevere l'APK armeabi-v7a."""
    machine = (machine or '').lower()
    if 'x86' in machine or 'i686' in machine or 'i386' in machine:
        return None
    return 'arm64-v8a' if pointer_bits == 64 else 'armeabi-v7a'


def pick_build(manifest, arch):
    """Voce del file version.json per l'architettura indicata, o None."""
    builds = (manifest or {}).get('builds') or {}
    build = builds.get(arch)
    if not isinstance(build, dict) or not build.get('url') or not build.get('version'):
        return None
    return build


def package_from_path(real_path):
    """Ricava il nome del pacchetto Android dai percorsi che Kodi usa per i suoi dati."""
    for pattern in (r'/Android/data/([A-Za-z0-9_.]+)/',
                    r'/data/(?:data|user/\d+)/([A-Za-z0-9_.]+)/'):
        match = re.search(pattern, real_path or '')
        if match:
            return match.group(1)
    return None


def sha256_file(path, chunk=1 << 20):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(chunk), b''):
            digest.update(block)
    return digest.hexdigest()


def install_uri(package, path):
    """Indirizzo content:// del provider interno di Kodi. Android rifiuta file:// quando
    esce dall'app, quindi il file si passa attraverso il provider di Kodi."""
    try:
        from urllib.parse import quote
    except ImportError:
        from urllib import quote
    return 'content://%s.file#%s' % (package, quote(path, safe='/'))


def should_remind(state, version, now, every):
    """False se l'utente ha gia rimandato proprio questa versione da meno di 'every' secondi."""
    if state.get('declined_version') != version:
        return True
    return (now - float(state.get('declined_at', 0))) >= every
