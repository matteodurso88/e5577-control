# Pocket Radio Manager — v0.1 (WORKSHOP)

GUI radio-only per **Huawei E5577Cs-321**. Non sostituisce la Web UI: si concentra su funzioni LTE avanzate escluse o nascoste dall'interfaccia Huawei.

> **Stato GitHub (2026-10-13):** i sorgenti GUI PySide6, adapter Huawei, scanner, discovery, profili salvati e suite di test sono sul branch `work/pocket-manager-radio-v01`. **L'owner ha confermato i collaudi UX su Dell. Il gate dell'ultimo commit e le nuove build Linux/Windows richiedono verifica sulle rispettive piattaforme; non sono release certificate.** Lo ZIP sperimentale precedente non è fonte canonica.

## Build desktop Linux e Windows

**Packaging candidato** su GitHub Actions per Linux x86-64 (tar.gz portabile) e Windows x64 (zip con PocketRadioManager.exe). Il workflow compila sui runner nativi, esegue il gate test Python/Qt, lo smoke offline del programma congelato e allega checksum SHA-256. Nessun pacchetto viene incluso nel repository, e gli archivi restano unsigned/non-installer finché non sono collaudati.

Procedura per scaricare gli artifact, limitazioni, controlli di sicurezza e istruzioni di compilazione manuale: **[DESKTOP_BUILDS.md](docs/DESKTOP_BUILDS.md)**. Workflow: **[pocket-radio-manager-desktop.yml](../.github/workflows/pocket-radio-manager-desktop.yml)**.
## Workflow canonico

- Codice/versionamento: `matteodurso88/workshop/pocket-manager/` su `work/*`.
- Test, CI-equivalent e preview su Dell Ubuntu, con output verificato sul commit esatto; PR/integrazione in GitHub dopo acceptance.
- Target desktop: Linux, Windows, macOS. Verifica OS-specifica da eseguire; nessun PASS implicito.
- Perimetro v0.1 da completare nella sessione notturna; future estensioni Web UI fuori scope.

## Local gate — three regressions and Qt teardown (2026-10-13)

Dell owner ran the complete 72-test local gate after the graphical dashboard iteration. Evidence: **69 passed, 3 failed**, then Python's Qt test process terminated with **signal 11 / SIGSEGV**. The app GUI otherwise launched; none of the failures concern LTE write semantics.

Corrections on branch `work/pocket-manager-radio-v01`: 
- The route-success text test now compares case-insensitively (`Puoi procedere` vs `puoi procedere`). The user-facing Italian message stays unchanged.
- Qt `_set_advanced` navigates to `Stato connessione` **before** hiding an active advanced tab. Previously Qt automatically switched to tab 3 before the final guard checked the selected index.
- The offscreen test selects `Confronta bande` before asserting `benchmark_btn.isVisible()`: a widget inside an inactive tab is not globally visible despite its tab being available.
- UI test fixture now uses `WA_DontShowOnScreen`, explicit `deleteLater()` processing and deterministic `QApplication` teardown to address process SIGSEGV after unittest summary. This is a candidate crash fix, **not a verified repair until the owner reruns the Dell gate**.
- `scripts/local_gate.py` now explicitly reports native process-signal failures and calls out Qt offscreen smoke as part of the suite. It never claims hardware/benchmark acceptance.

Next owner gate: `git pull --ff-only` and `.venv/bin/python scripts/local_gate.py`; only if all 72 pass and the process exits zero, run `.venv/bin/python -m pocket_manager` for a brief basic/advanced toggle smoke. No modem writes or WAN benchmark required.
## UX Home cards-only e SMS doppio clic — iterazione 13 ottobre 2026

- La scheda **Stato connessione** è ora **composta esclusivamente da quattro card**: `🌐 Rete mobile` a larghezza piena, seguita da `📶 Segnale`, `📡 Banda LTE` e `✉️ SMS` in riga. Nessun paragrafo, tabella diagnostica o testo di traffico rimane fuori dalle card.
- La card **Rete mobile** contiene operatore e tecnologia, i valori live `↓ Scaricamento / ↑ Invio` e il pulsante con stato **Attiva/Disattiva dati mobili**. Le operazioni di rete restano inalterate e soggette a conferma e read-back; il valore di traffico è quello riferito dal modem, non uno speed test.
- I vecchi widget **Dettagli connessione**, **Misure radio** e **Parametro radio / Valore** non sono stati rimossi: si trovano nella scheda avanzata **Dettagli tecnici → Misure radio**; il JSON diagnostico rimane disponibile nella sottoscheda **API ed esportazione**.
- Nella scheda **Messaggi**, un clic seleziona l'SMS e mostra l'anteprima; **doppio clic sulla riga** apre una finestra di lettura completa (mittente, data, testo scorrevole, pulsante Chiudi). Il corpo è sempre `QPlainTextEdit.setPlainText`, i dati non sono renderizzati come HTML e non vengono scritti nei log/JSON. La finestra SMS aperta viene chiusa quando il dispositivo si scollega.
- I messaggi restano in sola lettura: nessun invio, eliminazione, cambio dello stato letto/non letto, backup o memorizzazione automatica.

Gate locale aggiornato: **92 test attesi**, compresi smoke Qt che verificano Home composta solo da card, trasferimento e interruttore dentro la card Rete mobile, dialog SMS al doppio clic, contenuti in testo puro, pulizia allo scollegamento e disponibilità dei dati tecnici. Non ancora eseguito sul Dell sul commit più recente.

```bash
cd ~/progetti/workshop/pocket-manager
git pull --ff-only
.venv/bin/python scripts/local_gate.py
.venv/bin/python -m pocket_manager
```

Verifica manuale: Home senza testi sparsi; dati di traffico e switch dentro Rete mobile; `Messaggi` mostra anteprima con singolo clic e apre finestra completa al doppio clic; `Mostra strumenti avanzati` consente ancora accesso a misure radio e JSON.
## Estensione v0.1 — SMS e interruttore dati mobili (13 ottobre 2026)

### SMS in Home e lettura dedicata

- In **Stato connessione** compare la card **✉️ SMS**, che espone il numero di messaggi ricevuti/non letti ricavato da `sms/sms-count`. Il contatore viene aggiornato al login e ogni circa 30 secondi durante il normale polling, senza scaricare il testo dei messaggi.
- Il pulsante **Apri messaggi** conduce alla scheda **Messaggi**. Si possono leggere i messaggi ricevuti (mittente, data, stato letto/non letto e corpo in puro testo) con paginazione di 20 SMS e controllo precedente/successivo. I messaggi sono caricati *solo su richiesta esplicita* tramite `sms/sms-list` (huawei-lte-api `get_sms_list`). Nessun invio, cancellazione, marcatura come letto o salvataggio automatico.
- **Privacy:** il testo e i numeri di telefono esistono solo nella memoria della pagina SMS finché il dispositivo è collegato; vengono rimossi dalla vista allo scollegamento. **Mai** nei log, nella telemetria periodica, nel JSON diagnostico o su GitHub. La pagina usa `setPlainText`, senza HTML interpretato. Non condividere screenshot degli SMS senza redigere numeri/OTP.
- Se il firmware non supporta il contatore o la lista, il programma mostra `Non disponibile` o un errore leggibile, senza inventare uno zero.

### Attivazione/disattivazione dati mobili

- Nella Home un comando **Attiva/Disattiva dati mobili** agisce sul toggle **`dialup/mobile-dataswitch`** della SIM, **non** sul Wi-Fi, sul collegamento locale della GUI, su `NetworkMode`, o sulle bande LTE. La GUI distingue `dati abilitati` da `Internet realmente connesso`, che è monitorato separatamente.
- L'interruttore resta disabilitato se la lettura del firmware è assente/sconosciuta o durante altre operazioni; non presume lo stato da `monitoring/status`.
- **Disattivazione con conferma esplicita:** avviso dell'interruzione del servizio Internet per tutti gli utenti del pocket. La riattivazione è disponibile quando il modem risponde.
- Dopo ogni modifica, `set_mobile_dataswitch(0/1)` deve essere confermato dal read-back `mobile_dataswitch()`; se lo stato non si aggiorna, compare un errore e **non** viene annunciato successo. Il polling mantiene l'indicazione di stato aggiornata. Non è stato eseguito alcun comando reale sul dispositivo durante lo sviluppo.

### Gate da eseguire sul Dell

Le nuove feature sono implementate su branch `work/pocket-manager-radio-v01`, senza merge su `main`. Il nuovo gate comprende **88 test** (72 preesistenti, 13 test puri delle nuove funzionalità e 3 smoke GUI), non ancora attestati dal Dell.

```bash
cd ~/progetti/workshop/pocket-manager
git pull --ff-only
.venv/bin/python scripts/local_gate.py
.venv/bin/python -m pocket_manager
```

Smoke consigliato: card SMS con contatore, pagina Messaggi, selezione del singolo SMS, paginazione (se più di 20), chiusura/reapertura e controllo privacy; verificare stato dell'interruttore dati. **Prima** eseguire le letture senza modifiche. Per la prima disattivazione attiva occorre verificare localmente che si possa raggiungere il modem anche senza dati cellulari e che l'utente possa ripristinare il servizio.

## Dashboard grafica e identificazione banda LTE — iterazione 13 ottobre 2026

La schermata **Stato connessione** offre ora tre riquadri leggibili: **🌐 Rete mobile** (operatore/stato), **📶 Segnale** (tacche e barra Qt, indicatore approssimativo) e **📡 Banda LTE**. Le schede hanno icone native Qt, senza dipendenze da font esterni; le emoji nei titoli sono soltanto elementi decorativi, il testo rimane autonomo.

**Attenzione alla provenienza della banda:**

- **B7 · rilevata**: mostrata solo se un endpoint radio restituisce esplicitamente un valore `lte_bandinfo` interpretabile e compatibile con la maschera abilitata, mentre la rete LTE è connessa.
- **B7 · dedotta**: solo se il firmware dichiara connessione 4G (`ConnectionStatus=901`, `CurrentNetworkType=19/101`, `plmn.Rat=7`) e la maschera restituita da `net_mode.LTEBand` contiene **un singolo bit** (esempio `40` esadecimale = solo B7). In questo caso la banda unica è una **deduzione dalla configurazione consentita**, non una misura della serving cell; non attesta che il firmware stia applicando il vincolo correttamente.
- **Non rilevabile**: quando sono abilitate più bande e `lte_bandinfo` è nullo/non interpretabile, quando la rete LTE non risulta connessa o mancano i dati. Mostriamo comunque l'elenco delle bande consentite e la motivazione, senza inventare PCI, EARFCN o bande effettive.

Questa distinzione è importante sul firmware Huawei E5577Cs-321 `21.328.62.00.55`: nel payload reale dell'owner `signal.lte_bandinfo=null`, `cell_info` non è supportato (`100002`), ma con connessione LTE e maschera `LTEBand=40` la GUI può segnalare prudentemente `B7 · dedotta`.

I campi dettagliati della rete e le metriche radio originali rimangono accessibili tramite **Mostra strumenti avanzati**. Nessun cambio banda o interrogazione aggiuntiva viene attivato dalla dashboard.

Nuovi test automatici: cinque casi puri per provenienza banda/maschera/LTE + tre smoke Qt per i riquadri e l'indicatore a tacche. Totale **72 test attesi**, esecuzione sul Dell ancora da verificare sul commit più recente.

```bash
cd ~/progetti/workshop/pocket-manager
git pull --ff-only
.venv/bin/python scripts/local_gate.py
.venv/bin/python -m pocket_manager
```

Smoke manuale di sola lettura: confermare `B7 · dedotta`, `Bande consentite: B7`, segnale 1/5 e corretto comportamento della modalità avanzata. Quando sono abilitate più bande, la scheda non deve dedurre arbitrariamente quella attiva.
## Interfaccia semplice e strumenti avanzati — UX pass (13 ottobre 2026)

Il design ha due livelli **senza duplicare logica radio e senza perdere controlli**:

- **Interfaccia quotidiana (default):** Stato connessione, Andamento, Confronta bande. Lingua italiana, connessione/disconnessione e ricerca/salvataggio dei pocket; indicatore di connessione, 4G, operatore, segnale e traffico con descrizioni leggibili. Salvataggio password protetto nel portachiavi di sistema.
- **Mostra strumenti avanzati (checkbox):** espone indirizzo IP, username, controllo manuale delle bande, scanner RF, misure RSRP/RSRQ/SINR/PCI, diagnostica JSON e registro integrale. La commutazione mostra/nasconde le stesse istanze Qt e preserva configurazione e funzioni; non cambia firmware o modalità radio.
- **Confronta bande** mantiene route-check, conferma consapevole del consumo dati, ripetizioni, ripristino e risultati. `TTFB mediano (ms)` è ora visibile come **Tempo di risposta (ms)**, con tooltip che spiega la prima risposta HTTPS inclusi TCP/TLS/tempo server; non è ping e non sono millisecondi radio.
- **Velocità tipica (Mbps)** è la mediana dei test completati e non il massimo osservato. Il risultato più veloce è segnalato come relativo alla sessione e non come scelta valida in ogni ora. Le tacche del modem sono soltanto un indicatore approssimativo: non sostituiscono RSRP/SINR.
- **Andamento** mantiene gli stessi dati originali ma rinomina `bars` in `Segnale`, download/upload in `Scaricamento`/`Invio` e semplifica gli eventi. Le diagnostiche e le informazioni non disponibili rimangono accessibili in modalità avanzata.
- I messaggi di errore comuni vengono tradotti in italiano mentre il dettaglio tecnico resta nel registro avanzato. Gli avvisi di **rollback non verificato** restano espliciti e prioritari.

**Stato verifica:** implementazione UX versionata su branch `work/pocket-manager-radio-v01`, nessun merge a `main`. Il gate corrente include **64 metodi di test** (7 per la semantica delle etichette, 3 smoke Qt offscreen oltre ai 54 preesistenti); **non ancora eseguito sul Dell per questo commit**. Gli smoke UI non sostituiscono validazione manuale e hardware dei comandi radio.

Comandi di verifica:

```bash
cd ~/progetti/workshop/pocket-manager
git pull --ff-only
.venv/bin/python scripts/local_gate.py
.venv/bin/python -m pocket_manager
```

Smoke visuale: la modalità semplice deve presentare tre schede; attivando `Mostra strumenti avanzati` ricompaiono gli strumenti completi e la diagnostica. Verificare `Tempo di risposta` e il relativo tooltip. Il primo test sul dispositivo deve limitarsi a discovery/lettura e al pulsante di verifica connessione, **senza cambiare banda** finché gate e routing non sono validati.
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

## Benchmark delle bande LTE — prototipo sperimentale, gate hardware ancora da eseguire

Scopo: confrontare in momenti diversi la qualità della **connessione con una singola banda LTE consentita**. Sul firmware E5577Cs-321 RSRP/SINR/cell_info non sono disponibili, quindi NON attribuire serving band, PCI o qualità RF non misurata. La maschera read-back vincola le bande consentite; ogni risultato è un test end-to-end della connessione osservata in quel momento.

### Sicurezza e prerequisiti

- Benchmark avviato **solo su comando esplicito dell'owner**; il pannello richiede conferma di traffico dati mobile e possibile interruzione WAN. Non parte automaticamente a intervalli né all'apertura della GUI.
- Su Dell Linux usare **Verifica uscita Internet** nella nuova scheda **Benchmark LTE**. L'app risolve IPv4 di speed.cloudflare.com e accetta il test SOLO se la route per quel preciso IP ha come gateway il pocket (esempio 192.168.8.1), con sorgente IPv4 e interfaccia validi. Un percorso verso 192.168.100.1 (rete domestica precedentemente osservata) **fallisce prima di cambiare qualunque banda**.
- Connettere il Dell direttamente al Wi-Fi/USB del pocket se necessario, ma effettuare prima il git pull mentre GitHub è raggiungibile. Il solo raggiungimento della GUI Huawei via router domestico NON significa che la navigazione esterna esca dal pocket.
- L'app verifica anche LTE attivo (ConnectionStatus=901, CurrentNetworkType LTE, PLMN Rat=7), disponibilità API delle bande, poi read-back della maschera dopo ogni cambio. NetworkMode e NetworkBand originali vengono mantenuti invariati.
- I tentativi di ripristino della configurazione originale si eseguono anche dopo errore o cancellazione; non possono garantire recovery se il firmware/API diventa irraggiungibile. Dopo ripristino vengono verificati read-back e servizio LTE. Un fallimento viene segnalato come **grave**.
- Test LTE reali possono interrompere il servizio, consumare traffico a pagamento, far scattare firewall/rate limit del servizio esterno. Tenere pronta la Web UI Huawei con baseline originale (nell'ultima verifica LTEBand=40, NetworkMode=00, NetworkBand=3FFFFFFF). Non usare durante servizi critici.

### Misurazioni disponibili

- Prova HTTPS verso speed.cloudflare.com, endpoint /__down, eseguita su IPv4 risolto e fissato per tutte le bande. Verifica certificato TLS e lega la connessione alla sorgente IPv4 dell'interfaccia controllata: nessun proxy o reindirizzamento HTTP.
- Budget predefinito: **1 MiB x 2 download per banda**; opzione 4 MiB e massimo 3 ripetizioni, massimo totale 80 MB per sessione. Per B1+B3+B7+B20 nel default il payload totale programmato è 8 MiB (oltre overhead e possibili tentativi). Nessun upload attivo in questa fase.
- Si registra mediana Mbps download e **TTFB in millisecondi (non ping ICMP)**. Errore HTTP, 3G fallback, rete scollegata o mancata connessione non vengono spacciati per risultati validi. Download brevi stimano prestazioni limitate e dipendono anche dall'endpoint remoto.
- La scheda **Benchmark LTE**, separata dallo scanner RF, conserva in memoria fino a 24 run con timestamp locale, esportabili volontariamente nel JSON diagnostico. Per conclusioni robuste ripetere gli stessi test in fasce orarie differenti e senza altri client in traffico intenso.
- La classifica è per maggiore download mediano **tra prove complete**, con TTFB mostrato separatamente: non è selezione automatica della banda migliore e non altera la configurazione finale. Nessuna modifica radio permane intenzionalmente dopo una sessione di benchmark.

**Gate attuale:** sorgenti e test mock presenti solo su branch work/pocket-manager-radio-v01; nuovo gate Dell **64 test totali attesi (compresa UI Qt), non ancora eseguiti sul commit corrente**. Verificare inizialmente soltanto l'avvio della GUI e il pulsante Verifica uscita Internet nella scheda Benchmark LTE; NON avviare benchmark che cambi le bande fino a verifica del percorso WAN e approvazione del protocollo operativo.
## Storico live — monitoraggio in sola lettura (work/*)

- Aggiunto monitoraggio autenticato di `monitoring/traffic-statistics`: lettura ogni ~3 s insieme a `device/signal` e `monitoring/status`.
- I campi `CurrentDownloadRate` e `CurrentUploadRate`, quando forniti dal firmware, sono esposti come B/s, KiB/s o MiB/s; se assenti o endpoint non supportato compare `—`, **mai un falso zero**.
- La nuova scheda **Storico live** mostra timestamp, connessione, rete, tacche, download, upload ed eventuali variazioni dello stato Huawei.
- Lo storico è **in RAM**, limitato agli ultimi 120 campioni, e si azzera col pulsante o all'avvio di una nuova sessione.
- Il pulsante di export JSON già esistente include, su scelta dell'utente, una whitelist dello storico: niente credenziali, session token, IMEI, seriali, PCI o payload raw.
- Non ci sono nuove scritture LTE. RSRP/RSRQ/SINR/RSSI rimangono `indisponibili` nel firmware attualmente osservato; il traffico non è un surrogato della qualità del segnale.
- Fonti pubbliche: `huawei-lte-api` (metodo monitoring.traffic_statistics), exporter HiLink che usa `api/monitoring/traffic-statistics` e `api/device/signal`. Disponibilità sul modello E5577Cs-321 da verificare tramite read-back reale.

Gate locale da eseguire sul Dell sulla revisione corrente (39 test attesi, non ancora verificati):

```bash
cd ~/progetti/workshop/pocket-manager
git pull --ff-only
.venv/bin/python scripts/local_gate.py
.venv/bin/python -m pocket_manager
```

Verifica manuale: aprire `Storico live`, attendere almeno 20-30 secondi e confrontare variazione del contatore campioni, operatore, stato e tacche; verificare se `Download`/`Upload` restituiscono valori numerici oppure `—` (API non supportata). Non fare scan né band locking.
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