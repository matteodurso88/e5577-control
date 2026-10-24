# Sviluppo e verifiche — IT

[English](../en/DEVELOPMENT.md) · [Architettura](ARCHITECTURE.md)

## Setup Local-First

Su Linux con Python 3.12 e `uv`:

```bash
git clone https://github.com/matteodurso88/e5577-control.git
cd e5577-control
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e .
QT_QPA_PLATFORM=offscreen .venv/bin/python scripts/local_gate.py
.venv/bin/python -m pocket_manager
```

Sviluppare sui branch `work/*`, eseguire test e preview grafica in locale, quindi aprire una PR verso `main`. I test automatici non devono modificare configurazioni LTE reali. Le verifiche con il modem sono gate manuali autorizzati separatamente. Le cartelle locali `.venv/`, `build/`, `dist/` e i profili utente non sono materiale sorgente di release.

## Gate di qualità e build

`scripts/local_gate.py` compila il pacchetto Python ed esegue `unittest discover -s tests -v`, inclusi smoke Qt offscreen. È necessario l'exit code zero: non basta stampare OK prima di un crash nativo. La CI esegue gli stessi test su Linux e Windows e genera pacchetti PyInstaller onedir, installer nativi e portabili. Linux richiede librerie Qt di sistema e `dpkg-deb`; Windows usa Inno Setup 6. In CI le dipendenze di packaging sono fissate a `pyinstaller==6.16.0` e `pillow==11.3.0`.

```bash
python -m pip install -e . "pyinstaller==6.16.0" "pillow==11.3.0"
QT_QPA_PLATFORM=offscreen python scripts/local_gate.py
QT_QPA_PLATFORM=offscreen python scripts/build_desktop.py
```

La build esegue `--version` e `--self-check` sull'eseguibile: il secondo verifica import runtime **e presenza dei due SVG matt88.it**, senza comunicare col modem o aprire la GUI.

## Principi

- Nuovi widget: `objectName` stabile, nomi accessibili/tooltip, test offscreen, nessun accesso Internet o al modem accidentale.
- Scritture LTE: simulazioni nei test, read-back e avvisi sul rollback, fail-closed quando la route o il supporto hardware non sono dimostrabili.
- Preservare la compatibilità dei profili e del portachiavi fino a migrazioni esplicitamente testate.
- Non inserire segreti, acquisizioni API private, messaggi o identificatori dispositivo non oscurati.
- Gli asset di brand devono provenire dai sorgenti canonici di matt88.it, non da una ricostruzione arbitraria.

## Rilascio

Non pubblicare dalla PR, da vecchi artefatti CI o da un working tree non verificato. Seguire il [runbook di rilascio](RELEASE.md) e la [sicurezza](SECURITY.md).
