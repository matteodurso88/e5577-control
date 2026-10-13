# Pocket Radio Manager — installer Linux e Windows

Repository WORKSHOP: https://github.com/matteodurso88/workshop
Release scoping tramite tag specifico **pocket-radio-manager/v0.1.0**.
Workflow: https://github.com/matteodurso88/workshop/actions/workflows/pocket-radio-manager-desktop.yml

## Pacchetti

| Sistema | Installer raccomandato | Portabile |
| --- | --- | --- |
| Linux Ubuntu/Debian amd64 | pocket-radio-manager-v0.1.0-linux-x86_64.deb | pocket-radio-manager-v0.1.0-linux-x86_64.tar.gz |
| Windows 10/11 x64 | pocket-radio-manager-v0.1.0-windows-x86_64-setup.exe | pocket-radio-manager-v0.1.0-windows-x86_64.zip |

La sorgente dell'icona è **assets/pocket-radio-manager-icon.svg**: vettoriale nativa, comune alle due piattaforme. Lo script scripts/generate_icons.py crea il PNG 256px usato da Linux e l'ICO multi-risoluzione Windows.

### Linux — pacchetto Debian

Il pacchetto installa l'applicazione in /opt/pocket-radio-manager/, l'icona in /usr/share/icons/hicolor/256x256/apps/ e la voce menu in /usr/share/applications/io.matt88.PocketRadioManager.desktop, categorie Network/Utility. L'installazione/rimozione avviene con apt o dal gestore pacchetti.

~~~bash
sudo apt install ./pocket-radio-manager-v0.1.0-linux-x86_64.deb
~~~

La GUI sarà ricercabile nel menu delle applicazioni come **Pocket Radio Manager**. Per disinstallare: sudo apt remove pocket-radio-manager. Configurazioni personali e credenziali gestite da keyring OS non sono incluse negli installer.

### Windows — installer Inno Setup

L'installer integra una voce **Pocket Radio Manager** nel menu Start, supporta disinstallazione e offre un collegamento desktop opzionale. L'installazione predefinita è per utente in LocalAppData/Programs e non richiede privilegi amministrativi. Il setup è **unsigned**: Windows SmartScreen può segnalarlo; la scelta di eseguirlo spetta all'utente dopo aver verificato origine e SHA-256.

## Scoping monorepo e release

Il repository canonico è sempre matteodurso88/workshop, branch main. I tag GitHub sono globali ma hanno un prefisso specifico per ciascuna applicazione. Questo progetto usa **pocket-radio-manager/v0.1.0**; gli altri sottoprogetti possono usare tag propri.

Il job GitHub Actions di release si avvia solo quando il codice viene integrato in main e passa i gate nativi Linux/Windows; crea la release una sola volta per il tag, includendo i quattro pacchetti e SHA256SUMS.txt. La pubblicazione di un prototipo Workshop non è promozione a Product.

## Gate e controlli

La CI installa Python 3.12, PyInstaller 6.16.0, Pillow 11.3.0; su Windows include Inno Setup 6. Entrambi i job eseguono il gate Python/Qt e i controlli --version / --self-check dell'eseguibile congelato, senza rete o modem. Un risultato verde CI non sostituisce un collaudo manuale post-installazione.

Le build sono native (no cross-compilazione). Linux è mirato a distribuzioni x86-64 compatibili con Ubuntu 24.04; Windows a x64. Non sono prodotti installer ARM64, macOS, AppImage o MSI.

## Compilazione locale

~~~shell
python -m pip install -e . "pyinstaller==6.16.0" "pillow==11.3.0"
python scripts/local_gate.py
python scripts/build_desktop.py
~~~

Su Windows è richiesto Inno Setup 6 con ISCC.exe. Su Linux servono dpkg-deb e le librerie Qt del desktop. Tutti i pacchetti compaiono in dist/packages/ (ignorato da Git). Nessun profilo locale, password, dato SMS o token viene copiato negli archivi.

## Verifica

Scarica i pacchetti dalla release GitHub ufficiale e confronta l'SHA-256 con SHA256SUMS.txt. Dopo l'installazione, verifica avvio dal menu applicazioni/Start, icona, collegamento al pocket, stato LTE, lettura SMS, chiusura, disinstallazione e keyring dove disponibile. Il build gate non esegue comandi radio reali.
