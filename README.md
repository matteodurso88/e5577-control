# Pocket Radio Manager — v0.1 (WORKSHOP)

GUI radio-only per **Huawei E5577Cs-321**. Non sostituisce la Web UI: si concentra su funzioni LTE avanzate escluse o nascoste dall'interfaccia Huawei.

> **Stato GitHub (2026-10-13):** i sorgenti GUI PySide6, adapter Huawei, scanner, discovery, profili salvati e suite di test sono sul branch `work/pocket-manager-radio-v01`. **Non è ancora attestato il gate locale sul Dell né il collaudo hardware**. Lo ZIP sperimentale precedente non è fonte canonica.

## Workflow canonico

- Codice/versionamento: `matteodurso88/workshop/pocket-manager/` su `work/*`.
- Test, CI-equivalent e preview su Dell Ubuntu, con output verificato sul commit esatto; PR/integrazione in GitHub dopo acceptance.
- Target desktop: Linux, Windows, macOS. Verifica OS-specifica da eseguire; nessun PASS implicito.
- Perimetro v0.1 da completare nella sessione notturna; future estensioni Web UI fuori scope.

## Discovery: riconoscimento anonimo e diagnostica

Il discovery evita la richiesta di `device/information` come prerequisito: alcuni firmware la proteggono con login. La ricerca tenta sequenzialmente `api/device/information`, `api/device/signal` (lettura radio anonima quando consentita) e `api/webserver/SesTokInfo` (struttura di sessione Huawei, senza conservare cookie/token). La risposta del secondo o terzo endpoint permette di qualificare **un'API compatibile**, non di certificare il modello: quest'ultimo è da verificare dopo autenticazione.

I candidati vengono generati senza uno sweep indiscriminato: IP manuale, dispositivi già salvati, indirizzo storico `192.168.8.1`, gateway IPv4 attivi rilevati su Linux e possibili gateway `.1`/`.254` sulle /24 locali. L'elenco è limitato a 32 IP, con timeout esplicito e bypass dei proxy HTTP.

Dalla GUI, premendo **Cerca pocket**, il registro mostra gli IP provati e gli esiti `HTTP 403`, `URLError`, `risposta non identificante` oppure `API compatibile`. Non vengono stampati token di sessione, password o identificativi device.

Per una diagnosi fuori dalla GUI:

```bash
cd ~/progetti/workshop/pocket-manager
git pull --ff-only
source .venv/bin/activate
python scripts/local_gate.py
python -m pocket_manager.discovery
ip -br -4 addr
ip -4 route
```

Il pocket deve essere effettivamente **raggiungibile dal Dell**, ad esempio tramite Wi-Fi del pocket o tethering USB. Con due reti attive il gateway predefinito può riferirsi al router domestico e non al pocket. Il discovery può trovare un candidato ma non completare l'identificazione finché il login non viene effettuato.

## Dell smoke autenticato — 13 ottobre 2026

Evidenze dalle schermate owner:
- Sessione Huawei autenticata dopo un primo login respinto `108006`. GUI PySide6 avviata e monitor poll attivo.
- `api/device/signal` restituisce `mode=7` e `psatt=1`, ma **nessuna** misura RSRP/RSRQ/SINR/RSSI, PCI o cell ID. Non dedurre da questi due codici un aggancio LTE.
- `net_mode` read-back: `LTEBand=40` (maschera LTE B7) e `NetworkMode=00`. La maschera indica le bande LTE consentite, NON la banda di cella effettivamente in uso.
- Uno scan B7 è stato riportato `OK` benché tutte le misure fossero vuote; dopo scan, registro `baseline ripristinata`. Il firmware non ha ancora fornito prove di serving cell/qualità radio.
- Correzioni successive: monitor indica separatamente sessione API e presenza di RF metrics; scanner disabilitato se tutte le misure sono assenti; un sample vuoto non è più classificato `OK`; progress e preset sono sincronizzati; il read-only snapshot completo aggiunge `monitoring/status` e `device/information` per diagnosticare connessione e modello dopo login.
- **Nuovi test e GUI da ricollaudare sul Dell**, nessuna ulteriore scansione o scrittura a bande finché stato rete mobile e baseline non sono confermati.

Prossimo controllo in sola lettura: `git pull --ff-only`, `python scripts/local_gate.py`, `python -m pocket_manager`, login, scheda `Dati API` e `Aggiorna dati API`. Per supporto condividere solo sezioni redatte di `signal`, `monitoring_status`, `net_mode` e `plmn`; evitare credenziali, token, IMEI e seriali. Verificare sulla Web UI Huawei che SIM, registrazione rete e dati mobili siano attivi.

## LTE status fallback — real E5577Cs-321 payload (2026-10-13)

Owner data from firmware 21.328.62.00.55 confirms:
- Huawei reports ConnectionStatus=901 (data session connected), CurrentNetworkType=19 (4G LTE), SIM=1 (ready), operator WINDTRE.
- SignalIcon=1 and maxsignal=5: coarse firmware indicator 1/5 bars, NOT a dBm measurement.
- API signal has mode=7, psatt=1, but all LTE RF metrics RSRP/RSRQ/SINR/RSSI/PCI/cell id are null; do not treat as zero or claim no mobile connection.
- cell_info reports 100002 No support. LTEBand=40 is a B7 permission mask, NOT verified serving-cell band.
- Live GUI monitoring_status is now polled alongside signal. Connection, SIM, operator, technology and coarse bars are separate from engineering RF.
- Keep scanner disabled while RF is absent; do not change radio bands until baseline/recovery validated.

Next Dell gate: git pull --ff-only, .venv/bin/python scripts/local_gate.py, .venv/bin/python -m pocket_manager. Expected 32 tests; new gate not yet attested.

## Discovery / Pocket salvati — requisiti v0.1

1. Individuare pocket raggiungibili tramite probe non invasivi sulle interfacce locali, controllando identità modello via API Huawei. Supportare IP manuale.
2. Mostrare più dispositivi con nome/modello/IP/stato; consentire salvataggio con alias, scelta, modifica e rimozione.
3. Conservare metadati non sensibili del profilo localmente. **Credenziali salvate solo su richiesta in OS keyring** (Secret Service/KWallet compatibile su Linux, Windows Credential Manager, macOS Keychain), mai nel JSON, nei log, negli export o nel repository. Se il vault non è disponibile: richiedere la password, nessun fallback in chiaro.
4. Riconnessione rapida ai salvati, aggiornamento credenziali e rilocalizzazione con conferma quando l'IP cambia. Identificazione stabile soltanto se una API la dimostra.


## Funzioni

- Connessione amministrativa tramite `huawei-lte-api`, con opzione **Ricorda credenziali** nel portachiavi sicuro del sistema operativo.
- Monitor LTE live: RSRP, RSRQ, SINR, RSSI, banda, PCI, Cell ID, EARFCN *se esposti dal firmware* e tutti i campi di `api/device/signal`.
- Consultazione di `net/net-mode`, `net/net-mode-list`, `net/cell-info`, `net/current-plmn`.
- Band locking LTE, maschera esadecimale verificata, preset, switch `NetworkMode` automatico / 4G only.
- Read-back della configurazione dopo ogni scrittura, con pulsante per ripristinare la configurazione precedente.
- Band scanner sequenziale (RSSI/RSRP/RSRQ/SINR; non è un test di velocità) con tentativo di rollback anche dopo errore/cancellazione.
- Export JSON diagnostica radio (maschera identificatori/credenziali conosciuti).

**Limitazioni:** non è garantito l'accesso firmware ai set radio. Errore Huawei `100003` può indicare restrizioni. Cell lock, selezione PCI/EARFCN e forzatura della carrier aggregation NON sono implementati: nessun endpoint affidabile è stato dimostrato sul modem. Il band scanner può interrompere Internet; il restore non è garantito se la Web API diventa irraggiungibile. L'ordine di preferenza delle bande non è bloccabile tramite le maschere.

## Installazione prevista su Ubuntu (Dell) — Python >=3.10

**Nota:** il codice è sul branch GitHub. Eseguire i test sul commit esatto prima dell'utilizzo sul pocket reale. Non usare lo ZIP sperimentale come sorgente.

Per i test core:

```bash
cd pocket-manager
uv venv --python 3.12.15 .venv
source .venv/bin/activate
uv pip install -e .
python scripts/local_gate.py
```


```bash
cd pocket-manager
source .venv/bin/activate
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

Le scritture sono serializzate su un worker dedicato; Qt rimane reattivo. La password rimane in RAM durante la sessione e, **solo su consenso esplicito**, nel portachiavi del sistema operativo; la configurazione precedente resta in RAM. Il profilo del dispositivo può essere persistente ma non contiene segreti. Nessuna modifica di modem/Wi-Fi/APN/DHCP/SMS, nessun server/cloud.

## Test locali

```bash
python -m unittest discover -s tests -v
python -m compileall -q pocket_manager
```

La compatibilità eseguibile Linux/Windows/macOS richiede smoke test sulle rispettive piattaforme; non è sufficiente la sola importazione Python.

### Gate locale prima di PR

```bash
cd ~/progetti/workshop/pocket-manager
source .venv/bin/activate
git pull --ff-only
python scripts/local_gate.py
python -m pocket_manager
```

Per un primo smoke senza scritture: **Cerca pocket → Salva profilo → Ricorda nel keyring → Connetti → verifica segnale**. Eseguire band locking e restore soltanto dopo aver registrato la configurazione iniziale e con connessione alternativa. In Linux il portachiavi desktop deve essere sbloccato e disponibile; nessun fallback non cifrato.


## Origine e governance

- Workstream WORKSHOP: `project.md.workshop.pocket-manager` (registrazione Context da completare)
- GitHub issue: `matteodurso88/workshop#17`
- Branch iniziale: `work/pocket-manager-radio-v01`
- Input: script locali `band.py`, `band.sh`, `info.sh`, `test-login.py` forniti dall'owner. **Non importare** `test-login.py` in repository perché contiene una password hard-coded.

## Non-obiettivi v0.1

Gestione DHCP, APN, Wi-Fi, SMS, profili dial-up e replica delle altre pagine della Web UI; provisioning generico multi-modem; firmware hack; CI/distribuzione production.