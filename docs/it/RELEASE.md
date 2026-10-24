# Procedura di rilascio v1.0.1 — IT

[English](../en/RELEASE.md) · [Sviluppo](DEVELOPMENT.md)

## Contratto di pubblicazione

**Un tag Git annotato e immutabile, una CI su due piattaforme, quattro binari e un manifesto SHA-256.** Non ripubblicare vecchi artefatti della PR attribuendoli alla versione finale. La pipeline ricompila dal commit esatto taggato `v1.0.1` su Ubuntu 24.04 e Windows 2022, esegue tutti i test offline e gli smoke `--version` / `--self-check`, poi pubblica solo quando entrambe le build passano.

Asset previsti:
- `e5577-control-v1.0.1-linux-x86_64.deb`
- `e5577-control-v1.0.1-linux-x86_64.tar.gz`
- `e5577-control-v1.0.1-windows-x86_64-setup.exe`
- `e5577-control-v1.0.1-windows-x86_64.zip`
- `SHA256SUMS.txt` calcolato sui quattro binari della nuova esecuzione.

## Verifiche prima del tag

1. Mergiare la PR `work/v1.0.1-product-ui` in `main`, con entrambi i job CI verdi.
2. Verificare il commit effettivamente mergiato e la relativa CI.
3. Collaudare GUI, logo SVG nel footer, Informazioni, test offline e inclusione degli SVG nei due eseguibili congelati.
4. Convalidare la documentazione `docs/en/` e `docs/it/`, le note di release, i limiti hardware e gli avvisi sulle build non firmate.
5. Taggare esattamente il `main` approvato; non spostare e non forzare il tag.

## Creazione della release

**Percorso approvato per la pubblicazione v1.0.1:** mergiare la PR Product verificata su `main` usando come titolo esatto del commit di merge `release: E5577 Control v1.0.1`. La CI di quel preciso commit esegue prima le build native su Linux e Windows; solo se entrambe passano, il job di rilascio crea o verifica il tag annotato `v1.0.1`, ne confronta il commit, assembla i quattro binari appena generati, calcola `SHA256SUMS.txt` e crea la GitHub Release pubblica. In presenza di tag/release preesistenti incoerenti si arresta. I normali push su `main` **non** pubblicano release. Il titolo speciale del merge rappresenta l'autorizzazione una tantum dell'owner.

**Alternativa manuale** (solo recupero, quando non esiste ancora il tag): da una copia locale pulita di `main` con GitHub CLI autenticata:

```bash
git fetch origin main --tags
git switch main
git pull --ff-only origin main
git status --short
git tag -a v1.0.1 -m "E5577 Control v1.0.1"
git push origin refs/tags/v1.0.1
```

Eseguire solo dopo aver verificato che non ci siano modifiche tracciate e che il tag `v1.0.1` non esista già. Il push del tag avvia `.github/workflows/e5577-control-desktop.yml`: build native fresche su Linux/Windows e pubblicazione protetta. Il workflow si ferma senza sovrascrivere una release già esistente. Controllare l'URL della release e i log: creare il tag **non equivale** a pubblicare correttamente una release.

## Verifica dopo la pubblicazione

Scaricare gli asset dalla [release v1.0.1](https://github.com/matteodurso88/e5577-control/releases/tag/v1.0.1). In Linux verificare `sha256sum -c SHA256SUMS.txt`; in Windows confrontare i valori di `Get-FileHash`. Testare versione, installazione, avvio da menu, portabili e disinstallazione. Registrare separatamente eventuali gate hardware o Windows GUI ancora aperti: i test CI non sostituiscono la prova sul modem. Non modificare più il tag pubblicato.

La release WORKSHOP v0.1.0 originale e l'intera storia precedente restano preservate.

## Ritiro della precedente release

L'owner ha autorizzato il ritiro della precedente **GitHub Release v1.0.0** e dei suoi binari non firmati solo dopo la pubblicazione verificata della v1.0.1. La pipeline controlla tutti e cinque i nuovi asset, verifica l'ID della release precedente (`422924008`) e cancella **soltanto** quella release. Il tag Git annotato `v1.0.0` resta intenzionalmente conservato per tracciabilità; nessun artefatto vecchio sarà rinominato o riutilizzato. I nuovi pacchetti includono `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md` e testo LGPLv3. Vedere gli [avvisi di licenza e dipendenze](../../THIRD_PARTY_NOTICES.md).
