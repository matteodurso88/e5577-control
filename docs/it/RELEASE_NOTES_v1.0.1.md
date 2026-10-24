# E5577 Control v1.0.1 — Licenza GPL e distribuzione

La **v1.0.1** sostituisce la v1.0.0, senza modifiche funzionali intenzionali al modem o all'interfaccia approvata.

## Modifiche
- Il sorgente applicativo adotta **GNU GPL-3.0-or-later**, con testo completo nel file `LICENSE` e metadati SPDX in `pyproject.toml`.
- Ogni installer e pacchetto portabile Linux/Windows contiene `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md` e `LICENSES/LGPL-3.0-only.txt`, relativo alle licenze LGPLv3 di Qt/PySide6.
- Lo smoke test dell'eseguibile verifica la presenza degli avvisi legali, oltre ai due SVG canonici matt88.it. Il pacchetto Debian registra un avviso copyright sotto `/usr/share/doc/e5577-control/`.
- `THIRD_PARTY_NOTICES.md` distingue licenza del codice, dipendenze, obblighi Qt/LGPL e marchio visivo **matt88.it**, che resta tutelato separatamente.
- Documentazione di installazione, sicurezza e rilascio allineata in italiano e inglese.
- Dopo la pubblicazione e verifica della nuova versione viene **ritirata la GitHub Release v1.0.0 con i relativi binari**, ma restano il tag Git storico e la cronologia come prova di provenienza.

## Download
- Linux x86-64: `e5577-control-v1.0.1-linux-x86_64.deb` e `.tar.gz`.
- Windows x86-64: `e5577-control-v1.0.1-windows-x86_64-setup.exe` e `.zip`.
- `SHA256SUMS.txt` verifica tutti e quattro i pacchetti.

**Build non firmate.** Hardware prioritario Huawei E5577Cs-321. Le modifiche alle bande LTE e i benchmark possono interrompere la rete; i test CI offline non sostituiscono l'accettazione sul dispositivo.

[Documentazione italiana](https://github.com/matteodurso88/e5577-control/blob/v1.0.1/docs/it/OVERVIEW.md) · [English](https://github.com/matteodurso88/e5577-control/blob/v1.0.1/docs/en/OVERVIEW.md) · [Licenza](https://github.com/matteodurso88/e5577-control/blob/v1.0.1/LICENSE)
