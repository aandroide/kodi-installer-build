# -*- coding: utf-8 -*-
"""Servizio in background: controlla gli aggiornamenti dopo l'avvio e poi una volta al giorno."""
import xbmc
import xbmcaddon

import updater


def main():
    monitor = xbmc.Monitor()
    # lascia finire l'avvio di Kodi prima di mostrare eventuali finestre
    if monitor.waitForAbort(90):
        return
    while not monitor.abortRequested():
        settings = xbmcaddon.Addon()
        if settings.getSetting('auto_check') != 'false' and updater.last_check_age() >= updater.CHECK_EVERY:
            try:
                updater.check(manual=False)
            except Exception as err:
                updater.log('Errore nel controllo automatico: %r' % err)
        if monitor.waitForAbort(6 * 3600):
            break


if __name__ == '__main__':
    main()
