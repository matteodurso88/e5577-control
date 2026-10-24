# E5577 Control v1.0.0

**First standalone Product release** for Huawei E5577Cs-321, from the historical Pocket Radio Manager WORKSHOP project.

## What's included
- Dedicated public repository with **124 preserved subtree commits**, native CI on Linux/Windows.
- E5577 Control product identity in the title, executable and Linux/Windows installers.
- Always-visible version, **About / Informazioni** panel and compact complete **matt88.it** canonical SVG wordmark in the footer, clickable and theme-aware.
- Connection/network monitoring, mobile data status and consent-based switching, modem-reported signal, LTE-band controls with caveats, recent telemetry, local saved profiles, read-only SMS and guarded LTE band benchmark.
- Preservation of legacy saved-device directories and protected OS keyring service identifiers.

## Downloads

Linux x86-64: Debian `.deb` installer or portable `.tar.gz`.
Windows x86-64: Inno Setup `.exe` installer or portable `.zip`.
`SHA256SUMS.txt` is provided for all four packages. **Binaries are unsigned.**

## Limits and safety

Compatibility focus is Huawei E5577Cs-321; not every device/firmware exposes LTE RF metrics or supports write operations. Allowed LTE bands are not necessarily the connected band's RF measurement. LTE modifications and benchmarks can interrupt connectivity or use mobile data. Back up the original configuration and keep alternative access. Tests and packaging CI are not a substitute for hardware validation.

Documentation: [English](https://github.com/matteodurso88/e5577-control/blob/v1.0.0/docs/en/OVERVIEW.md) · [Italiano](https://github.com/matteodurso88/e5577-control/blob/v1.0.0/docs/it/OVERVIEW.md) · [Provenance](https://github.com/matteodurso88/e5577-control/blob/v1.0.0/docs/WORKSHOP_PROVENANCE.md).

---

# E5577 Control v1.0.0 — Italiano

**Prima release Product autonoma**, sviluppata a partire da Pocket Radio Manager (WORKSHOP) per Huawei E5577Cs-321.

## Novità
- Repository pubblico indipendente con **124 commit preservati** e CI nativa Linux/Windows.
- Identità E5577 Control nella finestra, negli eseguibili e negli installer.
- Versione sempre visibile, finestra **Informazioni** e **logo SVG canonico completo matt88.it** nel footer compatto, cliccabile e sensibile al tema.
- Stato rete/connessione e dati mobili, segnale indicativo, controlli LTE con avvertenze, cronologia, profili locali, lettura SMS e benchmark bande protetto.
- Percorsi dei profili e portachiavi OS preesistenti mantenuti compatibili.

## Download

Linux x86-64: installer `.deb` e portabile `.tar.gz`.
Windows x86-64: installer Inno Setup `.exe` e portabile `.zip`.
Manifesto `SHA256SUMS.txt` per tutti i pacchetti. **Binari non firmati.**

## Limiti e sicurezza

Il riferimento hardware è Huawei E5577Cs-321: il firmware può non mostrare le misure RF o rifiutare i comandi. Le bande consentite non coincidono automaticamente con la banda radio realmente agganciata. Modifiche LTE e benchmark possono interrompere Internet o consumare dati mobili. Salvare la configurazione e predisporre un collegamento alternativo. La CI non sostituisce il collaudo hardware.

Documentazione: [English](https://github.com/matteodurso88/e5577-control/blob/v1.0.0/docs/en/OVERVIEW.md) · [Italiano](https://github.com/matteodurso88/e5577-control/blob/v1.0.0/docs/it/OVERVIEW.md).
