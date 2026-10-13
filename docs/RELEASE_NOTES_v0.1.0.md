# Pocket Radio Manager v0.1.0

Prima release installabile del progetto **Pocket Radio Manager** in WORKSHOP.
Sorgente canonica: https://github.com/matteodurso88/workshop/tree/main/pocket-manager

## Novità

- Interfaccia Qt con Home a card, icona originale, stato LTE, segnale e banda consentita.
- Monitoraggio traffico e andamento live con storico temporaneo.
- Ricerca e salvataggio pocket, credenziali protette nel keyring OS.
- Lettura SMS con anteprima e finestra completa a doppio clic (solo lettura).
- Attivazione/disattivazione dati mobili con conferma e verifica del read-back.
- Controlli radio avanzati e benchmark LTE con guardie di routing/rollback.
- Installer Linux .deb con voce nel menu applicazioni e icona.
- Installer Windows .exe (Inno Setup) con voce nel menu Start, disinstallazione e collegamento desktop opzionale.
- Archivi Linux .tar.gz e Windows .zip portabili per chi non vuole installare.
- SHA256SUMS.txt per verificare integrità dei quattro archivi.

## Scegli il pacchetto

| Sistema | File |
| --- | --- |
| Ubuntu/Debian x86-64 | pocket-radio-manager-v0.1.0-linux-x86_64.deb |
| Windows 10/11 x64 | pocket-radio-manager-v0.1.0-windows-x86_64-setup.exe |
| Linux portabile | pocket-radio-manager-v0.1.0-linux-x86_64.tar.gz |
| Windows portabile | pocket-radio-manager-v0.1.0-windows-x86_64.zip |

**I pacchetti sono unsigned.** Windows può mostrare un avviso SmartScreen e Linux può richiedere conferma per binari non firmati. Installare soltanto dalla release ufficiale, controllando i checksum SHA-256.

Il programma è stato compilato e sottoposto a test automatizzati su Linux x86-64 e Windows x64. Le funzioni che modificano la radio o la connessione cellulare possono interrompere temporaneamente il servizio; usarle con prudenza.
Il dispositivo di riferimento è Huawei E5577Cs-321: alcune misure radio non sono disponibili nel firmware. Le bande dedotte sono indicate come tali e non vanno confuse con una lettura della serving cell.

## Monorepo WORKSHOP

Questa è una release specifica del sottoprogetto pocket-manager/ dentro matteodurso88/workshop. Il tag è pocket-radio-manager/v0.1.0 e non modifica versioni, tag o artefatti degli altri progetti Workshop.

Una release Workshop non equivale alla promozione a Product, che richiede una decisione distinta e un repository canonico autonomo.
