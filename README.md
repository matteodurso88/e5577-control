# Pocket Radio Manager — v0.1 (WORKSHOP)

GUI radio-only per **Huawei E5577Cs-321**. Non sostituisce la Web UI: si concentra su funzioni LTE avanzate escluse o nascoste dall'interfaccia Huawei.

## Funzioni

- Connessione amministrativa tramite `huawei-lte-api`, senza password salvate su disco.
- Monitor LTE live: RSRP, RSRQ, SINR, RSSI, banda, PCI, Cell ID, EARFCN *se esposti dal firmware* e tutti i campi di `api/device/signal`.
- Consultazione di `net/net-mode`, `net/net-mode-list`, `net/cell-info`, `net/current-plmn`.
- Band locking LTE, maschera esadecimale verificata, preset, switch `NetworkMode` automatico / 4G only.
- Read-back della configurazione dopo ogni scrittura, con pulsante per ripristinare la configurazione precedente.
- Band scanner sequenziale (RSSI/RSRP/RSRQ/SINR; non è un test di velocità) con tentativo di rollback anche dopo errore/cancellazione.
- Export JSON diagnostica radio (maschera identificatori/credenziali conosciuti).

**Limitazioni:** non è garantito l'accesso firmware ai set radio. Errore Huawei `100003` può indicare restrizioni. Cell lock, selezione PCI/EARFCN e forzatura della carrier aggregation NON sono implementati: nessun endpoint affidabile è stato dimostrato sul modem. Il band scanner può interrompere Internet; il restore non è garantito se la Web API diventa irraggiungibile. L'ordine di preferenza delle bande non è bloccabile tramite le maschere.

## Installazione su Ubuntu (Dell) — Python >=3.10

```bash
cd pocket-manager
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pocket_manager
```

Su Windows: `py -m venv .venv`, `.venv\\Scripts\\activate`, `python -m pip install -e .`, `python -m pocket_manager`. Su macOS usare Python >=3.10 e comandi simili a Ubuntu. Non richiede server HTTP locale o privilegi root. Per packaging/distribuzione binaria occorre build specifica per ciascun OS.

## Verifica operativa — gate hardware

1. Collega il PC alla rete del pocket; apri la sua Web UI per verificare indirizzo e password; chiudi eventuali altre sessioni admin in caso di conflitto.
2. Avvia Pocket Manager, inserisci password e premi **Connetti**. Connessione solo quando richiesta.
3. Controlla `Monitor radio` e `Dati API`: accertati che `net_mode` e `signal` siano popolati. Identifica bande realmente supportate.
4. Fai screenshot/export diagnostico prima delle modifiche.
5. Con connessione di riserva, applica **una sola banda**; attendi read-back. Verifica RSRP, RSRQ, SINR, cella e band. Prova poi **Ripristina precedente**.
6. Solo dopo la prova di ripristino, valuta una scansione automatica. Se fallisce il rollback usa la Web UI o il tuo script precedente per tornare alla configurazione originaria.
7. Il test è PASS solo se lettura live, scrittura supportata e recovery sono dimostrati sul dispositivo reale. I test mock non certificano il firmware.

## API e convenzioni

Maschere LTE esadecimali: `B1=1`, `B3=4`, `B7=40`, `B20=80000`; `B1+B3+B7=45`. La maschera `800d5` proviene dal vecchio `band.py` e rappresenta B1/B3/B5/B7/B8/B20 per la variante provata storicamente. La disponibilità di una banda viene prima cercata in `net-mode-list` e non dedotta indiscriminatamente dal valore `ALL=7FFFFFFFFFFFFFFF`.

Le scritture sono serializzate su un worker dedicato; Qt rimane reattivo. L'app conserva **solo in memoria** password e configurazione precedente. Nessuna modifica di modem/Wi-Fi/APN/DHCP/SMS, nessun server/cloud.

## Test locali

```bash
python -m unittest discover -s tests -v
python -m compileall -q pocket_manager
```

La compatibilità eseguibile Linux/Windows/macOS richiede smoke test sulle rispettive piattaforme; non è sufficiente la sola importazione Python.

## Origine e governance

- Workstream WORKSHOP: `project.md.workshop.pocket-manager` (registrazione Context da completare)
- GitHub issue: `matteodurso88/workshop#17`
- Branch iniziale: `work/pocket-manager-radio-v01`
- Input: script locali `band.py`, `band.sh`, `info.sh`, `test-login.py` forniti dall'owner. **Non importare** `test-login.py` in repository perché contiene una password hard-coded.

## Non-obiettivi v0.1

Gestione DHCP, APN, Wi-Fi, SMS, profili dial-up e replica delle altre pagine della Web UI; provisioning generico multi-modem; firmware hack; CI/distribuzione production.