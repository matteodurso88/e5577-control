# Sicurezza e privacy — IT

[English](../en/SECURITY.md) · [Home](../../README.md)

## Confine locale

E5577 Control dialoga con il modem Huawei tramite API HTTP nella rete locale, usando indirizzi IPv4 privati o link-local. Non serve alcun server in ingresso o cloud specifico dell'app. Soltanto un benchmark avviato esplicitamente genera traffico Internet esterno lungo la route WAN selezionata.

Nel JSON dei profili vengono conservati alias, indirizzi IP, nomi utente ed eventualmente informazioni sul modello, **mai le password**. Il salvataggio delle credenziali è facoltativo e si appoggia solo ai portachiavi OS protetti (Secret Service/KWallet su Linux, Windows Credential Manager o portachiavi supportato su macOS). Backend non protetti o in chiaro vengono rifiutati. I vecchi identificatori `pocket-radio-manager` e `io.matt88.pocket-radio-manager` restano invariati per non perdere i dati salvati.

## Salvaguardie

- La ricerca dei dispositivi verifica un insieme limitato di candidati locali: non è uno scanner della rete pubblica.
- Non esporre password, cookie/token Huawei, IMEI, seriali o contenuti SMS nei log e nel supporto.
- Gli SMS sono **testo semplice non attendibile** anche nel lettore integrale: non vengono inviati, eliminati, segnati come letti o esportati automaticamente.
- Ogni scrittura radio richiede un'azione esplicita, con tentativo di conferma; il firmware può rifiutare la maschera, ignorarla o rendersi irraggiungibile prima del ripristino.
- Il confronto bande verifica la route IPv4 verso l'endpoint del test prima di modificare le bande. Può consumare dati mobili e interrompere Internet: mantenere una connessione alternativa.
- L'interfaccia distingue misure RF assenti da zero e maschere consentite da bande effettivamente rilevate.

## Build e distribuzione

I pacchetti **non sono firmati**; gli asset di release devono avere checksum SHA-256. Non considerare sicuro un eseguibile solo perché è possibile superare un avviso del sistema operativo. Compilare dal sorgente taggato con i due job Linux/Windows, smoke `--self-check` PyInstaller e inclusione degli SVG canonici matt88.it. La pipeline di release non deve usare artefatti di commit diversi né sovrascrivere release esistenti.

La cronologia del repository può essere pubblica. Non committare credenziali reali, dump del modem, SMS, profili utente o chiavi private. Gitleaks non ha trovato segreti nei 124 commit storici importati; ciò non equivale a garanzia assoluta.

## Segnalazioni

Segnalare vulnerabilità in forma privata al manutentore, senza aprire issue con credenziali attive, log sensibili o dati personali. Per bug non sensibili usare le [GitHub Issues](https://github.com/matteodurso88/e5577-control/issues).

Provenienza storica: [WORKSHOP_PROVENANCE.md](../WORKSHOP_PROVENANCE.md).

## Licenze

Il codice di E5577 Control è distribuito con GPL-3.0-or-later, testo integrale in `LICENSE`. Qt/PySide6 può essere distribuito in regime LGPLv3/GPL secondo il modulo; consultare `LICENSES/LGPL-3.0-only.txt` e `THIRD_PARTY_NOTICES.md`. Il brand grafico matt88.it resta separatamente tutelato in `NOTICE`, senza limitare i diritti sul sorgente. Occorre verificare le dipendenze e gli obblighi LGPL per ciascuna versione distribuita.
