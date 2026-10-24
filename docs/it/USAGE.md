# Guida utente — IT

[English](../en/USAGE.md) · [Installazione](INSTALL.md)

## Primo avvio e collegamento

1. Avviare **E5577 Control** e verificare il titolo `v1.0.0`, il logo completo **matt88.it** nel footer e il pulsante **Informazioni**.
2. Collegare il computer alla rete del modem Huawei E5577Cs-321 (Wi-Fi o USB). L'indirizzo storico è `192.168.8.1`, ma verificare indirizzo e credenziali effettivi tramite la Web UI Huawei.
3. Usare **Trova dispositivo** oppure un profilo salvato, quindi **Connetti**. La ricerca riconosce endpoint API compatibili: trovare un candidato non certifica il modello fisico.
4. Cominciare con le sole letture di rete, SIM e segnale. Non è necessario cambiare bande o dati mobili per il primo collaudo.

## Schede

| Scheda | Funzione |
| --- | --- |
| `Stato connessione` | Card per rete mobile, tacche segnale indicative, stato bande LTE e SMS; include interruttore dati mobili |
| `Andamento` | Campioni e cambiamenti di stato recenti, mantenuti localmente |
| `Messaggi` | Inbox in sola lettura, pagine e doppio clic per aprire il testo completo |
| `Confronta bande` | Confronto con preflight di routing e consenso al traffico dati |
| `Controllo manuale` | Configurazione avanzata delle maschere LTE, modalità e ripristino |
| `Dettagli tecnici` | Metriche RF avanzate, diagnostica API ed esportazione sanitizzata |

Selezionare **Mostra strumenti avanzati** per esporre schede tecniche e indirizzo IP senza perdere i dati inseriti.

## Avvertenze operative

- Le **tacche di segnale** sono un'indicazione approssimativa del modem, non una misura in dBm. Le bande consentite non attestano quella realmente agganciata.
- L'**interruttore dati mobili** richiede conferma e lettura di verifica: modifica la connessione della SIM, non il Wi-Fi del pocket né il login locale dell'app.
- **Bande e benchmark:** possono interrompere Internet. Predisporre una connessione alternativa, annotare la configurazione originale e verificare che la route WAN esca dal pocket. Un ripristino fallito è un errore critico.
- **SMS:** nessun invio, eliminazione, cambio letto/non letto o archivio persistente.
- **Privacy:** non allegare a issue password, token, IMEI, seriali, messaggi completi o dump API privati.

L'app desktop non richiede un account cloud o un servizio in background. Approfondimenti in [Sicurezza](SECURITY.md).
