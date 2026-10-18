# -*- coding: utf-8 -*-
"""Servizio in background: controlla gli aggiornamenti all'avvio di Kodi e poi ogni ora circa.
Su Fire TV e telefono Kodi spesso resta in background senza chiudersi, quindi il controllo
periodico serve a non perdere gli aggiornamenti. Non disturba mentre si guarda qualcosa."""
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
        due = first or updater.last_check_age() >= updater.CHECK_EVERY
        if settings.getSetting('auto_check') != 'false' and due:
            if xbmc.Player().isPlaying():
                updater.log('Riproduzione in corso: controllo rimandato')
            else:
                try:
                    updater.check(manual=False, startup=first)
                except Exception as err:
                    updater.log('Errore nel controllo automatico: %r' % err)
                first = False
        elif first and settings.getSetting('auto_check') == 'false':
            first = False
        if monitor.waitForAbort(900):
            break


if __name__ == '__main__':
    main()
