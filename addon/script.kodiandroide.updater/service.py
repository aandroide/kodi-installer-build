# -*- coding: utf-8 -*-
"""Servizio in background: controlla gli aggiornamenti a ogni avvio di Kodi e poi una volta al giorno."""
import xbmc
import xbmcaddon

import updater


def main():
    monitor = xbmc.Monitor()
    # lascia finire l'avvio di Kodi prima di mostrare eventuali finestre
    if monitor.waitForAbort(30):
        return
    first = True
    while not monitor.abortRequested():
        settings = xbmcaddon.Addon()
        # al primo giro (avvio di Kodi) controlla sempre, poi al massimo una volta al giorno
        if settings.getSetting('auto_check') != 'false' and (first or updater.last_check_age() >= updater.CHECK_EVERY):
            try:
                updater.check(manual=False, startup=first)
            except Exception as err:
                updater.log('Errore nel controllo automatico: %r' % err)
        first = False
        if monitor.waitForAbort(6 * 3600):
            break


if __name__ == '__main__':
    main()
