# Installazione e aggiornamenti — IT

[English](../en/INSTALL.md) · [Home](../../README.md)

## Requisiti

- **Linux:** desktop Ubuntu/Debian x86-64; il pacchetto `.deb` richiede `libc6`, `libstdc++6`, `libegl1`, `libgl1`, `libxcb-cursor0`, `libxkbcommon-x11-0`.
- **Windows:** Windows 10/11 x86-64, installazione per singolo utente; ZIP portabile alternativo.
- Il modem **Huawei E5577Cs-321**, raggiungibile in rete e con credenziali amministrative, è necessario solo per le funzioni hardware, non per avviare la GUI o i test offline.

## Download e integrità

Scaricare la **v1.0.0** soltanto dalla [pagina Release del Product](https://github.com/matteodurso88/e5577-control/releases/tag/v1.0.0) dopo la sua effettiva pubblicazione. Sono previsti:

| Sistema | Installer consigliato | Alternativa portabile |
| --- | --- | --- |
| Linux x86-64 | `e5577-control-v1.0.0-linux-x86_64.deb` | `e5577-control-v1.0.0-linux-x86_64.tar.gz` |
| Windows x86-64 | `e5577-control-v1.0.0-windows-x86_64-setup.exe` | `e5577-control-v1.0.0-windows-x86_64.zip` |

Verificare `SHA256SUMS.txt` **della stessa release**. Linux: `sha256sum -c SHA256SUMS.txt`; Windows: `Get-FileHash .\e5577-control-v1.0.0-windows-x86_64-setup.exe -Algorithm SHA256` e confronto manuale. Le build **non sono firmate**, quindi SmartScreen può mostrare un avviso. Il checksum verifica l'integrità rispetto al manifesto pubblicato, non l'identità del produttore.

## Linux

```bash
sudo apt install ./e5577-control-v1.0.0-linux-x86_64.deb
```

Aprire **E5577 Control** dal menu Rete/Utility. L'eseguibile è in `/opt/e5577-control/`, il launcher in `/usr/share/applications/`. Disinstallare con `sudo apt remove e5577-control`. Per il portabile estrarre tutto il tarball e avviare `E5577Control` dalla cartella estratta, mantenendo le librerie accanto all'eseguibile.

## Windows

Eseguire `e5577-control-v1.0.0-windows-x86_64-setup.exe` dopo la verifica. L'installazione predefinita è in `AppData\Local\Programs\E5577 Control`, con menu Start e disinstallazione; l'icona desktop è facoltativa. Per la versione portabile estrarre l'intero ZIP e avviare `E5577Control.exe`, non soltanto il file EXE.

## Passaggio da Pocket Radio Manager v0.1.0

Restano invariati la cartella profili `pocket-radio-manager`, il servizio portachiavi `io.matt88.pocket-radio-manager` e il modulo Python `pocket_manager`. In Linux gli ID dei pacchetti sono diversi (`pocket-radio-manager` e `e5577-control`): possono quindi convivere due voci nel menu. Verificare prima la nuova app e poi, eventualmente, rimuovere **solo il vecchio pacchetto**, senza eliminare dati o credenziali. In Windows è conservato l'AppId Inno Setup storico, così può riconoscere l'installazione precedente; verificare il percorso proposto.

Per diagnosi e operazioni sicure: [Utilizzo](USAGE.md) e [Sicurezza](SECURITY.md).
