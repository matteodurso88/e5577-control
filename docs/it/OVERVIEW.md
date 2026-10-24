# E5577 Control — Panoramica

[English](../en/OVERVIEW.md) · [Home](../../README.md)

E5577 Control è un'applicazione desktop locale **PySide6 / Qt 6**, progettata principalmente per il modem LTE **Huawei E5577Cs-321**. Affianca, ma non sostituisce, l'interfaccia Web Huawei. Altri modelli e firmware non sono certificati.

## Funzioni

- **Dashboard connessione:** operatore, tecnologia mobile, tacche segnale comunicate dal modem, stato dati mobili e velocità istantanea di traffico, quando disponibili. Il traffico non rappresenta uno speed test.
- **SMS:** contatore, paginazione, anteprima e lettura completa in testo semplice con doppio clic. Nessun invio, cancellazione o modifica dello stato letto.
- **Ricerca e profili:** individuazione degli endpoint locali compatibili, salvataggio di alias/indirizzi e memorizzazione opzionale della password nel portachiavi protetto del sistema.
- **Monitoraggio:** cronologia live e cambiamenti di stato; diagnostica API avanzata ed esportazione con minimizzazione degli identificatori.
- **Bande LTE:** consultazione delle bande consentite, applicazione di una maschera con lettura di conferma e tentativo di ripristino. Le operazioni possono interrompere Internet o essere rifiutate dal firmware.
- **Confronto bande:** benchmark subordinato alla verifica che il traffico Internet passi davvero dal modem. Può consumare dati mobili.

## Come interpretare la banda LTE

La **maschera delle bande consentite** non misura la banda della cella agganciata. L'interfaccia distingue una banda **rilevata**, **dedotta** o **non disponibile**. Il firmware Huawei provato può non fornire RSRP/RSRQ/SINR, PCI, cell ID né la banda di servizio: questi valori non vengono inventati. Una sola banda consentita può permettere una deduzione qualificata, non una misura radio.

## Piattaforme e limiti

Linux x86-64 (Debian e tarball portabile) e Windows x86-64 (installer Inno Setup e ZIP portabile). Le build non sono firmate. Pacchetti macOS e compatibilità generica con tutti i modem Huawei non sono certificati per questa release.

Nel footer compare il **logo SVG canonico completo matt88.it**; la finestra **Informazioni** contiene versione e credito testuale.

Approfondimenti: [Utilizzo](USAGE.md), [Sicurezza](SECURITY.md), [Architettura](ARCHITECTURE.md) e [Rilascio](RELEASE.md).
