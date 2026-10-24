# Architettura — IT

[English](../en/ARCHITECTURE.md) · [Home](../../README.md)

## Componenti

| Percorso | Responsabilità |
| --- | --- |
| `pocket_manager/qt_app.py` | Finestra PySide6, schede semplici/avanzate, card, Informazioni e footer SVG canonico |
| `pocket_manager/backend.py` | Sessione API Huawei e operazioni protette sul modem |
| `pocket_manager/discovery.py` | Ricerca limitata di endpoint locali |
| `pocket_manager/profiles.py` | Profili JSON locali, portachiavi OS, validazioni, scritture atomiche |
| `pocket_manager/radio.py` | Maschere LTE, modalità, misure e bande con grado di certezza esplicito |
| `pocket_manager/band_benchmark.py` | Preflight del routing, confronti LTE espliciti e tentativi di recovery |
| `pocket_manager/device_features.py` | Funzioni SMS e dati mobili |
| `pocket_manager/telemetry.py` | Campioni recenti limitati in memoria |
| `pocket_manager/presentation.py` | Etichette e messaggi per l'utente |
| `scripts/local_gate.py` | Gate offline sintassi e test unitari Python/Qt |
| `scripts/build_desktop.py` | Packaging nativo Linux/Windows, smoke e checksum |
| `scripts/frozen_entry.py` | Entry point congelato, `--version` e `--self-check` |
| `assets/matt88/` | Loghi SVG canonici light/dark non alterati |

## Esecuzione e flussi dati

Il loop eventi Qt gestisce i widget; worker `QThread` separati effettuano discovery e chiamate API del modem. Le operazioni radio vengono accodate per non bloccare Qt e serializzare le modifiche; segnali Qt riportano risultati e avanzamento. Gli handler della UI non devono eseguire richieste lente direttamente. La cronologia recente resta in memoria; non si archivia automaticamente il contenuto SMS.

Le password entrano nel portachiavi OS soltanto previo consenso. Un errore non può attivare fallback a salvataggio in chiaro. Se il firmware non espone una metrica, l'assenza viene mostrata senza inventare valori. Applicazione bande, scansione e benchmark richiedono verifiche preventive e tentativi di ripristino.

## Distribuzione

- `pyproject.toml`: distribuzione `e5577-control`, versione `1.0.1`, comando `e5577-control` e alias compatibile `pocket-radio-manager`; il modulo Python resta `pocket_manager`.
- PyInstaller onedir: `E5577Control` / `E5577Control.exe`; installer `.deb` / Inno Setup `.exe`, portabili `.tar.gz` / `.zip`.
- Launcher Linux: `packaging/linux/io.matt88.E5577Control.desktop`; installer Windows: `packaging/windows/E5577Control.iss`.
- Identità GUI: `v1.0.1`, finestra Informazioni, logo completo matt88.it alto 18px in un footer alto 22px. Variante scelta in base alla palette Qt e incorporata nell'eseguibile, anche offline.
- Il rilascio deve partire da un tag Git immutabile e verificato; vedi [Rilascio](RELEASE.md).

## Compatibilità storica

Il repository Product contiene 124 commit estratti dal subtree WORKSHOP privato. Repo, PR e release v0.1.0 originali sono conservati nella cronologia; vedi [provenienza](../WORKSHOP_PROVENANCE.md). Il rebranding non ha modificato il servizio portachiavi né lo schema dei profili esistenti.
