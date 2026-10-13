# Pocket Radio Manager — desktop packages Linux e Windows

Il packaging è attivato dalla workflow GitHub Actions:
https://github.com/matteodurso88/workshop/actions/workflows/pocket-radio-manager-desktop.yml

La branch di sviluppo è work/pocket-manager-radio-v01; main non viene modificato
né utilizzato come target di pubblicazione automatica.

## Matrice delle build candidate

| Sistema | Runner nativo | Archivio |
| --- | --- | --- |
| Linux x86-64 | Ubuntu 24.04 | pocket-radio-manager-v0.1.0-linux-x86_64.tar.gz |
| Windows x86-64 | Windows Server 2022 | pocket-radio-manager-v0.1.0-windows-x86_64.zip |

Sono PACCHETTI PORTABILI e NON installer .deb, .msi, AppImage o installer
firmati. Non contengono alcun profilo, dispositivo associato, password o SMS.

La versione Linux richiede una distribuzione desktop x86-64 sufficientemente
recente; il suo riferimento di build è Ubuntu 24.04. ARM64 e distribuzioni
Linux con vecchie librerie glibc sono fuori dall'attuale matrice.
Su Windows l'eseguibile non firmato può generare avvisi SmartScreen.

## Scaricamento degli artifact GitHub

1. Apri GitHub → Actions → Pocket Radio Manager | Linux + Windows desktop packages.
2. Seleziona una esecuzione della branch work/pocket-manager-radio-v01.
3. Scarica il relativo artifact solo se entrambi i job risultano riusciti.
4. Estrai il primo ZIP di GitHub Actions, poi l'archivio relativo al tuo OS.
5. Confronta l'hash SHA-256 dell'archivio con SHA256SUMS.txt presente
   nell'artifact.
6. Esegui PocketRadioManager (Linux) o PocketRadioManager.exe (Windows)
   dalla cartella estratta PocketRadioManager, NON dall'archivio compresso.

Gli artifact restano disponibili per 14 giorni e non equivalgono a una
GitHub Release permanente. Una Release necessita della validazione reale
dell'owner su Linux e Windows e di autorizzazione separata.

## Gate della pipeline

La workflow installa Python 3.12, il progetto dal pyproject.toml e
PyInstaller 6.16.0. Ogni job:

1. Esegue il gate Python/Qt locale scripts/local_gate.py.
2. Compila con scripts/build_desktop.py, nativamente sull'OS target.
3. Esegue --version e --self-check sul BINARY CONGELATO.
4. Archivia solo la cartella eseguibile congelata, aggiunge
   README-FIRST.txt e BUILD-MANIFEST.json con commit GitHub e versioni delle
   dipendenze, calcola SHA256SUMS.txt.
5. Carica come artifact la coppia archivio/checksum per 14 giorni.

Il self-check importa PySide6, la libreria Huawei, keyring e il codice
applicativo senza creare QApplication, aprire connessioni al pocket, leggere
credenziali né effettuare modifiche radio. L'esito positivo NON prova
l'avvio manuale della GUI, la connettività o il keyring su ciascun PC.

I vincoli versione delle dipendenze runtime sono dichiarati come intervalli
nel pyproject.toml: il manifest conserva le versioni effettive impacchettate.
Non si garantisce riproducibilità bit-per-bit.

## Compilazione manuale

Da pocket-manager/ su Linux x86-64 o Windows x64 con Python 3.12:

~~~shell
python -m pip install -e . "pyinstaller==6.16.0"
python scripts/local_gate.py
python scripts/build_desktop.py
~~~

Le build generate si trovano in dist/packages/, ignorata da Git.
L'interruttore dati mobili, il blocco bande e la casella SMS non sono
automaticamente esercitati da alcuna fase di packaging.

## Accettazione

Prima di promuovere gli archivi a release, verificare su entrambe le
piattaforme: avvio e chiusura della GUI, discovery del pocket, login,
lettura SMS, keyring OS se configurato, Home, modalità avanzata, e
controllo dello stato mobile. Comandi di modifica radio/connessione solo
su decisione esplicita e in sessione controllata; il build gate non
autorizza interventi sul modem.
