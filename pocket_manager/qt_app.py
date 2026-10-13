"""Desktop Qt UI. Discovery and Huawei sessions never block the event loop."""

from __future__ import annotations

from datetime import datetime
import json
from ipaddress import IPv4Address, ip_address
from pathlib import Path
import queue
import sys
import threading
import time

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from . import __version__
from .backend import HuaweiRadioBackend
from .discovery import discover_report
from .profiles import PocketProfile, ProfileStore, CredentialStoreError
from .radio import FALLBACK_BANDS, FREQUENCIES, MODES, PRESETS, mask_hex, supported_bands, bands_from_mask, safe_json_data, has_radio_measurements, network_overview
from .telemetry import TelemetryTimeline, format_rate, traffic_rates
from .band_benchmark import (run_band_benchmark, resolve_endpoint,
                             check_route, ranking)
from .presentation import (friendly_connection, friendly_signal,
                           friendly_rf, friendly_route,
                           friendly_benchmark_result, friendly_band_status)


class DiscoveryWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, saved_hosts: tuple[str, ...]):
        super().__init__()
        self.saved_hosts = saved_hosts

    def run(self):
        try:
            self.completed.emit(discover_report(self.saved_hosts))
        except Exception as exc:
            self.failed.emit(type(exc).__name__)


class RadioWorker(QThread):
    ready = Signal(dict)
    reading = Signal(dict)
    failed = Signal(str)
    finished_job = Signal(str, bool, str, object)
    progress = Signal(dict)

    def __init__(self, host: str, username: str, password: str):
        super().__init__()
        self.host, self.username, self.password = host, username, password
        self.jobs: queue.Queue = queue.Queue()
        self.stop = threading.Event()
        self.cancel = threading.Event()

    def submit(self, command: str, **params):
        self.jobs.put((command, params))

    def shutdown(self):
        self.stop.set()
        self.cancel.set()
        self.jobs.put(("quit", {}))

    def run(self):
        original_secret = self.password
        try:
            with HuaweiRadioBackend(self.host, self.username, original_secret) as radio:
                self.password = ""
                first = radio.snapshot(full=True)
                self.ready.emit(first)
                # _ready() already renders the initial read. Avoid a second,
                # duplicate history sample with the same timestamp.
                due = time.monotonic() + 3
                while not self.stop.is_set():
                    try:
                        command, opts = self.jobs.get(timeout=max(0.05, due - time.monotonic()))
                    except queue.Empty:
                        command, opts = "poll", {}
                    if command == "quit":
                        break
                    if command == "poll":
                        self.reading.emit(radio.snapshot())
                    elif command == "refresh":
                        self.reading.emit(radio.snapshot(full=True))
                    elif command in ("apply", "restore", "scan", "route_check", "benchmark"):
                        try:
                            if command == "route_check":
                                dest = resolve_endpoint()
                                path = check_route(radio.host, dest)
                                message = f"Uscita verificata: {path.interface} via {path.gateway}"
                                data = {"interface": path.interface, "gateway": path.gateway}
                            elif command == "benchmark":
                                self.cancel.clear()
                                data = run_band_benchmark(
                                    radio, opts["bands"], self.cancel,
                                    lambda message: self.progress.emit({"status": message}),
                                    repeats=opts["repeats"],
                                    bytes_per_sample=opts["bytes_per_sample"],
                                )
                                completed = len([r for r in data if r.status == "OK"])
                                message = (f"Benchmark concluso: {completed}/{len(data)} "
                                           "bande misurate. Baseline ripristinata.")
                            elif command == "apply":
                                result = radio.apply(opts["mask"], opts["mode"])
                                message = "Confermato: LTEBand=" + result.lte_band
                                data = {}
                            elif command == "restore":
                                result = radio.restore()
                                message = "Ripristinato: LTEBand=" + result.lte_band
                                data = {}
                            else:
                                self.cancel.clear()
                                data = radio.scan(opts["bands"], self.cancel, self.progress.emit)
                                no_measurements = bool(data) and not any(
                                    row.get("status") == "OK" for row in data
                                )
                                message = (
                                    "Scansione senza misure LTE utilizzabili; baseline ripristinata"
                                    if no_measurements else
                                    "Scansione terminata; baseline ripristinata"
                                )
                            self.finished_job.emit(command, True, message, data)
                        except Exception as exc:
                            self.finished_job.emit(command, False, str(exc).replace(original_secret, "[redacted]") if original_secret else str(exc), {})
                        self.reading.emit(radio.snapshot(full=True))
                    due = time.monotonic() + 3
        except Exception as exc:
            err = str(exc)
            if original_secret:
                err = err.replace(original_secret, "[redacted]")
            self.failed.emit(type(exc).__name__ + ": " + err)
        finally:
            self.password = ""
            original_secret = ""


def _show(value) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(safe_json_data(value), ensure_ascii=False)
    return str(value)


class PocketWindow(QMainWindow):
    METRICS = ("band", "rsrp", "rsrq", "sinr", "rssi", "pci", "cellid", "earfcn")

    def __init__(self):
        super().__init__()
        self.store = ProfileStore()
        self.radio_worker: RadioWorker | None = None
        self.discovery_worker: DiscoveryWorker | None = None
        self.online = False
        self.busy = False
        self.snapshot: dict = {}
        self.scan_results: list[dict] = []
        self.benchmark_results = []
        self.benchmark_runs: list[dict] = []
        self.available: tuple[int, ...] = ()
        self.has_measurements = False
        self.detected_model = ""
        self.timeline = TelemetryTimeline(120)
        self.setWindowTitle("Pocket Radio Manager · " + __version__)
        self.resize(1180, 780)
        self._build()
        self._set_advanced(False)
        self._reload_profiles()
        self._set_online(False)

    def _build(self):
        central = QWidget()
        outer = QVBoxLayout(central)
        self.setCentralWidget(central)

        devices = QHBoxLayout()
        self.saved = QComboBox()
        self.saved.setMinimumWidth(300)
        self.saved.currentIndexChanged.connect(self._select_saved)
        self.discover_btn = QPushButton("Trova dispositivo")
        self.discover_btn.clicked.connect(self._discover)
        save = QPushButton("Salva dispositivo")
        save.clicked.connect(self._save)
        delete = QPushButton("Elimina")
        delete.clicked.connect(self._delete)
        for widget in (QLabel("Dispositivo"), self.saved, self.discover_btn, save, delete):
            devices.addWidget(widget)
        outer.addLayout(devices)

        connection = QHBoxLayout()
        self.host = QLineEdit("192.168.8.1")
        self.host.setMaximumWidth(165)
        self.alias = QLineEdit("Il mio pocket")
        self.alias.setMinimumWidth(230)
        self.alias.setToolTip("Nome a tua scelta per riconoscere questo pocket.")
        self.username = QLineEdit("admin")
        self.username.setMaximumWidth(115)
        self.password = QLineEdit()
        self.password.setMaximumWidth(180)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Password del dispositivo")
        self.remember = QCheckBox("Ricorda la password")
        self.remember.setToolTip(
            "La password è conservata nel portachiavi protetto del sistema. "
            "Non viene salvata in chiaro."
        )
        self.connect_btn = QPushButton("Connetti")
        self.connect_btn.clicked.connect(self._connect)
        self.disconnect_btn = QPushButton("Scollega")
        self.disconnect_btn.clicked.connect(self._disconnect)
        self.host_caption = QLabel("Indirizzo IP")
        self.username_caption = QLabel("Utente")
        for item in (self.host_caption, self.host, QLabel("Nome"), self.alias,
                     self.username_caption, self.username, QLabel("Password"),
                     self.password, self.remember, self.connect_btn, self.disconnect_btn):
            connection.addWidget(item)
        outer.addLayout(connection)

        header = QHBoxLayout()
        self.status = QLabel("● Dispositivo non collegato")
        self.status.setWordWrap(True)
        self.advanced_toggle = QCheckBox("Mostra strumenti avanzati")
        self.advanced_toggle.setToolTip(
            "Mostra configurazione manuale delle bande, parametri radio, "
            "indirizzo IP e dati diagnostici senza rimuovere alcuna funzione."
        )
        self.advanced_toggle.toggled.connect(self._set_advanced)
        header.addWidget(self.status, 1)
        header.addWidget(self.advanced_toggle)
        outer.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._monitor_tab(), "Stato connessione")
        self.tabs.addTab(self._timeline_tab(), "Andamento")
        self.tabs.addTab(self._bands_tab(), "Controllo manuale")
        self.tabs.addTab(self._benchmark_tab(), "Confronta bande")
        self.tabs.addTab(self._diagnostics_tab(), "Dettagli tecnici")
        outer.addWidget(self.tabs, 1)
        outer.addWidget(QLabel("Attività recenti"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(105)
        outer.addWidget(self.log)
        self.setStyleSheet(
            "QWidget {font-size: 13px;} QPushButton {padding: 6px 10px;}"
            "QGroupBox {font-weight: bold; margin-top: 10px; padding-top: 9px;}"
            "QGroupBox::title {subcontrol-origin: margin; left: 8px;}"
        )

    def _set_advanced(self, enabled: bool):
        """Only change visibility: technical widgets and their state remain intact."""
        self.tabs.setTabVisible(2, enabled)
        self.tabs.setTabVisible(4, enabled)
        self.host_caption.setVisible(enabled)
        self.host.setVisible(enabled)
        self.username_caption.setVisible(enabled)
        self.username.setVisible(enabled)
        self.advanced_signal_group.setVisible(enabled)
        self.signals.setVisible(enabled)
        if not enabled and self.tabs.currentIndex() in (2, 4):
            self.tabs.setCurrentIndex(0)

    def _monitor_tab(self):
        w = QWidget()
        box = QVBoxLayout(w)
        network_group = QGroupBox("La tua connessione")
        network_grid = QGridLayout(network_group)
        self.network_labels = {}
        for n, (key, caption) in enumerate((
            ("connection", "Connessione dati"), ("network", "Rete mobile"),
            ("sim", "SIM"), ("operator", "Operatore"),
            ("bars", "Segnale"), ("rf", "Misure approfondite"),
        )):
            row, col = divmod(n, 3)
            network_grid.addWidget(QLabel(caption), row * 2, col)
            label = QLabel("—")
            label.setWordWrap(True)
            label.setStyleSheet("font-weight: bold;")
            network_grid.addWidget(label, row * 2 + 1, col)
            self.network_labels[key] = label
        box.addWidget(network_group)
        self.traffic_label = QLabel("Trasferimento in questo momento:  Scaricamento ↓ —    Invio ↑ —")
        self.traffic_label.setToolTip(
            "Questi dati provengono dal pocket: indicano il traffico corrente "
            "di tutti i dispositivi collegati, non sono uno speed test."
        )
        box.addWidget(self.traffic_label)
        info = QLabel(
            "Il livello del segnale è indicativo. Per scegliere quale banda "
            "funziona meglio, usa «Confronta bande»: misura la connessione Internet."
        )
        info.setWordWrap(True)
        box.addWidget(info)
        group = QGroupBox("Misure radio dettagliate · strumenti avanzati")
        self.advanced_signal_group = group
        grid = QGridLayout(group)
        self.metrics = {}
        for n, key in enumerate(self.METRICS):
            row, col = divmod(n, 4)
            grid.addWidget(QLabel(key.upper()), row * 2, col)
            label = QLabel("—")
            label.setStyleSheet("font-size: 20px; font-weight: bold;")
            grid.addWidget(label, row * 2 + 1, col)
            self.metrics[key] = label
        box.addWidget(group)
        self.signals = QTableWidget(0, 2)
        self.signals.setHorizontalHeaderLabels(["Parametro radio", "Valore"])
        self.signals.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        box.addWidget(self.signals, 1)
        return w

    def _bands_tab(self):
        w = QWidget()
        box = QVBoxLayout(w)
        note = QLabel(
            "Gestione manuale bande LTE. Le maschere possono interrompere la WAN; "
            "alcune configurazioni sono bloccate dal firmware."
        )
        note.setWordWrap(True)
        box.addWidget(note)
        self.support = QLabel("Bande E5577 da script storico (non ancora verificate)")
        box.addWidget(self.support)
        checks = QHBoxLayout()
        self.band_checks = {}
        for band in FALLBACK_BANDS:
            check = QCheckBox(f"B{band} ({FREQUENCIES[band]} MHz)")
            check.setChecked(True)
            check.stateChanged.connect(self._mask)
            checks.addWidget(check)
            self.band_checks[band] = check
        box.addLayout(checks)
        row = QHBoxLayout()
        self.preset = QComboBox()
        self.preset.addItem("Personalizzato")
        self.preset.addItems(PRESETS.keys())
        self.preset.currentTextChanged.connect(self._preset)
        self.mode = QComboBox()
        for name, value in MODES.items():
            self.mode.addItem(name, value)
        self.mask_label = QLabel("Maschera LTE: —")
        for item in (QLabel("Preset"), self.preset, QLabel("NetworkMode"),
                     self.mode, self.mask_label):
            row.addWidget(item)
        box.addLayout(row)
        actions = QHBoxLayout()
        self.apply_btn = QPushButton("Applica bande")
        self.apply_btn.clicked.connect(self._apply)
        self.restore_btn = QPushButton("Ripristina precedente")
        self.restore_btn.clicked.connect(self._restore)
        self.scan_btn = QPushButton("Scansiona misure RF")
        self.scan_btn.clicked.connect(self._scan)
        self.cancel_btn = QPushButton("Interrompi scanner / benchmark")
        self.cancel_btn.clicked.connect(self._cancel)
        for btn in (self.apply_btn, self.restore_btn, self.scan_btn, self.cancel_btn):
            actions.addWidget(btn)
        box.addLayout(actions)
        self.current_label = QLabel("Stato attuale: —")
        self.current_label.setToolTip(
            "LTEBand è la maschera delle bande consentite, non la serving band "
            "effettiva (che questo firmware non sta fornendo)."
        )
        self.scan_status = QLabel("Scanner RF inattivo")
        box.addWidget(self.current_label)
        box.addWidget(self.scan_status)
        self.scan_table = QTableWidget(0, 7)
        self.scan_table.setHorizontalHeaderLabels(
            ["Banda", "RSRP", "RSRQ", "SINR", "RSSI", "PCI", "Stato"]
        )
        self.scan_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        box.addWidget(self.scan_table, 1)
        self._mask()
        return w

    def _benchmark_tab(self):
        w = QWidget()
        box = QVBoxLayout(w)
        selector = QHBoxLayout()
        self.bench_checks = {}
        for band in FALLBACK_BANDS:
            checkbox = QCheckBox(f"B{band} ({FREQUENCIES[band]} MHz)")
            checkbox.setChecked(band in (1, 3, 7, 20))
            selector.addWidget(checkbox)
            self.bench_checks[band] = checkbox
        box.addWidget(QLabel("Scegli le bande da confrontare (una alla volta)"))
        box.addLayout(selector)
        bench_group = QGroupBox("Trova la banda più conveniente per te")
        bench_layout = QVBoxLayout(bench_group)
        warn = QLabel(
            "1. Collega il computer a Internet tramite il pocket. "
            "2. Verifica la connessione. 3. Avvia il confronto. "
            "Durante la prova la rete mobile può interrompersi brevemente; "
            "il programma proverà a ripristinare le impostazioni iniziali. "
            "Le prove utilizzano traffico dati."
        )
        warn.setWordWrap(True)
        bench_layout.addWidget(warn)
        bench_buttons = QHBoxLayout()
        self.test_size = QComboBox()
        self.test_size.addItem("Test rapido · 1 MiB", 1048576)
        self.test_size.addItem("Test completo · 4 MiB", 4194304)
        self.test_size.setToolTip(
            "Dimensione del download eseguito per ciascuna prova. "
            "1 MiB equivale a circa 1,05 MB."
        )
        self.test_repeats = QComboBox()
        self.test_repeats.addItem("1 volta", 1)
        self.test_repeats.addItem("2 volte", 2)
        self.test_repeats.addItem("3 volte", 3)
        self.test_repeats.setToolTip(
            "Ripetere la prova aiuta a ridurre gli effetti delle oscillazioni "
            "momentanee della rete."
        )
        self.test_repeats.setCurrentIndex(1)
        self.route_btn = QPushButton("1. Verifica connessione")
        self.route_btn.clicked.connect(self._route_check)
        self.benchmark_btn = QPushButton("2. Avvia confronto")
        self.benchmark_btn.clicked.connect(self._benchmark)
        self.bench_cancel_btn = QPushButton("Interrompi prova")
        self.bench_cancel_btn.clicked.connect(self._cancel)
        for item in (QLabel("Intensità"), self.test_size,
                     QLabel("Ripetizioni"), self.test_repeats,
                     self.route_btn, self.benchmark_btn, self.bench_cancel_btn):
            bench_buttons.addWidget(item)
        bench_layout.addLayout(bench_buttons)
        self.benchmark_label = QLabel("Pronto: verifica che il computer navighi tramite il pocket.")
        self.benchmark_label.setWordWrap(True)
        bench_layout.addWidget(self.benchmark_label)
        self.benchmark_history_label = QLabel(
            "Confronti effettuati: 0. Puoi ripetere la prova durante la giornata "
            "e salvare i risultati dalle opzioni avanzate."
        )
        self.benchmark_history_label.setWordWrap(True)
        bench_layout.addWidget(self.benchmark_history_label)
        self.benchmark_table = QTableWidget(0, 5)
        self.benchmark_table.setHorizontalHeaderLabels(
            ["Banda provata", "Esito", "Velocità tipica (Mbps)",
             "Tempo di risposta (ms)", "Prove riuscite"]
        )
        self.benchmark_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.benchmark_table.horizontalHeaderItem(2).setToolTip(
            "Velocità di scaricamento mediana delle prove completate, "
            "non la velocità massima."
        )
        self.benchmark_table.horizontalHeaderItem(3).setToolTip(
            "TTFB: tempo per la prima risposta HTTPS del server, "
            "comprende connessione TCP, TLS e risposta iniziale. "
            "Più basso è in genere meglio. Non è un ping ICMP."
        )
        bench_layout.addWidget(self.benchmark_table)
        box.addWidget(bench_group, 1)
        return w

    def _timeline_tab(self):
        w = QWidget()
        box = QVBoxLayout(w)
        row = QHBoxLayout()
        self.history_status = QLabel("Storico in RAM (max 120 campioni, circa 6 min a 3s); nessun salvataggio automatico.")
        self.history_status.setWordWrap(True)
        clear = QPushButton("Azzera storico")
        clear.clicked.connect(self._clear_history)
        row.addWidget(self.history_status, 1)
        row.addWidget(clear)
        box.addLayout(row)
        self.timeline_table = QTableWidget(0, 7)
        self.timeline_table.setHorizontalHeaderLabels(
            ["Ora", "Connessione", "Rete", "Tacche", "Download", "Upload", "Variazioni"]
        )
        self.timeline_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.timeline_table.horizontalHeader().setSectionResizeMode(
            6, QHeaderView.ResizeMode.Stretch
        )
        box.addWidget(self.timeline_table, 1)
        return w

    def _clear_history(self):
        self.timeline.clear()
        self.timeline_table.setRowCount(0)
        self.history_status.setText("Storico azzerato (in RAM).")

    def _append_history(self, data):
        point = self.timeline.observe(data)
        self.timeline_table.insertRow(0)
        columns = (
            point.timestamp[11:19], point.connection, point.network,
            point.bars, format_rate(point.down_bps),
            format_rate(point.up_bps), point.change or "—",
        )
        for col, value in enumerate(columns):
            self.timeline_table.setItem(0, col, QTableWidgetItem(value))
        while self.timeline_table.rowCount() > 120:
            self.timeline_table.removeRow(self.timeline_table.rowCount() - 1)
        self.history_status.setText(
            f"Campioni: {len(self.timeline.points())}/120 · "
            "solo lettura, traffico e tacche dipendono dal firmware"
        )

    def _diagnostics_tab(self):
        w = QWidget()
        box = QVBoxLayout(w)
        buttons = QHBoxLayout()
        self.refresh_btn = QPushButton("Aggiorna dati API")
        self.refresh_btn.clicked.connect(lambda: self.radio_worker and self.radio_worker.submit("refresh"))
        export = QPushButton("Esporta JSON (redatto)")
        export.clicked.connect(self._export)
        buttons.addWidget(self.refresh_btn)
        buttons.addWidget(export)
        box.addLayout(buttons)
        self.raw = QTextEdit()
        self.raw.setReadOnly(True)
        box.addWidget(self.raw)
        return w

    def _log(self, message: str):
        self.log.append(datetime.now().strftime("%H:%M:%S") + "  " + message)

    def _set_online(self, online: bool):
        self.online = online
        self.connect_btn.setEnabled(not online and self.radio_worker is None)
        self.disconnect_btn.setEnabled(self.radio_worker is not None)
        for widget in (self.apply_btn, self.restore_btn, self.scan_btn,
                       self.refresh_btn, self.route_btn, self.benchmark_btn):
            widget.setEnabled(online and not self.busy)
        self.cancel_btn.setEnabled(online and self.busy)
        self.bench_cancel_btn.setEnabled(online and self.busy)
        # Never run a measurement scan while the firmware supplies no RF
        # readings: it would change bands but return misleading empty rows.
        self.scan_btn.setEnabled(online and not self.busy and self.has_measurements)

    def _reload_profiles(self, chosen: str | None = None):
        self.saved.blockSignals(True)
        self.saved.clear()
        self.saved.addItem("— Seleziona un dispositivo salvato —", None)
        try:
            for profile in self.store.list():
                self.saved.addItem(f"{profile.alias} · {profile.host}", profile.id)
                if profile.id == chosen:
                    self.saved.setCurrentIndex(self.saved.count() - 1)
        except Exception as exc:
            self._log("Archivio pocket non leggibile: " + str(exc))
        self.saved.blockSignals(False)

    def _selected_profile(self) -> PocketProfile | None:
        profile_id = self.saved.currentData()
        if not profile_id:
            return None
        return next((p for p in self.store.list() if p.id == profile_id), None)

    def _select_saved(self, index: int):
        try:
            profile = self._selected_profile()
            if not profile:
                return
            self.alias.setText(profile.alias)
            self.host.setText(profile.host)
            self.username.setText(profile.username)
            secret = self.store.credential(profile.id)
            self.password.setText(secret or "")
            self.remember.setChecked(secret is not None)
        except CredentialStoreError:
            self.password.clear()
            self.remember.setChecked(False)
            self._log("Portachiavi non disponibile: inserire la password per questa sessione.")
        except Exception as exc:
            self._log("Profilo non disponibile: " + str(exc))

    def _save(self):
        try:
            addr = str(ip_address(self.host.text().strip()))
            profile = self._selected_profile()
            if profile and profile.host != addr:
                choice = QMessageBox.question(self, "IP modificato",
                    "Aggiornare l'indirizzo IP del pocket salvato? Verificare prima che sia lo stesso dispositivo.")
                if choice != QMessageBox.StandardButton.Yes:
                    return
            new = PocketProfile(
                profile.id if profile else ProfileStore.new_profile(self.alias.text().strip(), addr).id,
                self.alias.text().strip(), addr, self.username.text().strip(),
                profile.model if profile else "",
            )
            self.store.save(new, remember_password=self.remember.isChecked(),
                            password=self.password.text() if self.remember.isChecked() else None)
            if not self.remember.isChecked() and profile:
                self.store.forget_credential(profile.id)
            self._reload_profiles(new.id)
            self._log("Profilo salvato; password solo nel keyring se richiesto.")
        except Exception as exc:
            QMessageBox.warning(self, "Salvataggio pocket", str(exc))

    def _delete(self):
        try:
            profile = self._selected_profile()
            if profile and QMessageBox.question(self, "Elimina pocket",
                   f"Eliminare {profile.alias} e le sue credenziali salvate?") == QMessageBox.StandardButton.Yes:
                self.store.delete(profile.id)
                self._reload_profiles()
                self.password.clear()
        except Exception as exc:
            QMessageBox.warning(self, "Eliminazione", str(exc))

    def _discover(self):
        if self.discovery_worker and self.discovery_worker.isRunning():
            return
        # Include the manually entered address even if it is not saved yet.
        hosts = (self.host.text().strip(),) + tuple(p.host for p in self.store.list())
        self.discover_btn.setEnabled(False)
        self._log("Discovery locale in corso (solo lettura)...")
        self.discovery_worker = DiscoveryWorker(hosts)
        self.discovery_worker.completed.connect(self._discovery_done)
        self.discovery_worker.failed.connect(lambda message: self._log("Discovery: " + message))
        self.discovery_worker.finished.connect(lambda: self.discover_btn.setEnabled(True))
        self.discovery_worker.start()

    def _discovery_done(self, report):
        devices = list(report.devices)
        self._log(f"Discovery completato: {len(report.candidates)} IP controllati, {len(devices)} compatibili.")
        for detail in report.diagnostics:
            self._log(detail)
        if not devices:
            QMessageBox.information(
                self, "Discovery — nessun pocket rilevato",
                "Non è stata riconosciuta un'API Huawei raggiungibile. "
                "Il dispositivo deve essere collegato al Dell tramite Wi-Fi/USB/rete locale.\n\n"
                "Diagnostica probe:\n" + "\n".join(report.diagnostics[:20]),
            )
            return
        labels = [
            f"{d.name} · {d.host} · {d.model} "
            + ("[API compatibile]" if d.detection != "identified" else "[identificato]")
            for d in devices
        ]
        label, ok = QInputDialog.getItem(self, "Pocket rilevati", "Scegli il dispositivo:", labels, 0, False)
        if ok and label in labels:
            found = devices[labels.index(label)]
            self.saved.setCurrentIndex(0)
            self.host.setText(found.host)
            self.alias.setText(found.name)
            self.password.clear()
            self.remember.setChecked(False)
            status = ("identificato" if found.detection == "identified"
                      else "API Huawei compatibile; modello da confermare dopo il login")
            self._log(f"Pocket {status}: {found.model} · {found.host}")

    def _connect(self):
        if self.radio_worker is not None:
            return
        try:
            host = self.host.text().strip()
            addr = ip_address(host)
            if not isinstance(addr, IPv4Address) or not (addr.is_private or addr.is_link_local):
                raise ValueError("Inserire un IP locale valido")
            secret = self.password.text()
            if not secret:
                profile = self._selected_profile()
                if profile:
                    secret = self.store.credential(profile.id) or ""
            if not secret:
                QMessageBox.warning(self, "Connessione", "Inserire la password amministratore")
                return
            self.radio_worker = RadioWorker(host, self.username.text().strip(), secret)
            self.radio_worker.ready.connect(self._ready)
            self.radio_worker.reading.connect(self._reading)
            self.radio_worker.failed.connect(self._failed)
            self.radio_worker.progress.connect(self._progress)
            self.radio_worker.finished_job.connect(self._job_done)
            self.radio_worker.finished.connect(self._worker_finished)
            self.status.setText("● Connessione al pocket...")
            self.radio_worker.start()
            self._set_online(False)
        except Exception as exc:
            QMessageBox.warning(self, "Connessione", str(exc))

    def _ready(self, snapshot):
        self.timeline.clear()
        self.timeline_table.setRowCount(0)
        self.password.clear()
        self.status.setText("● API Huawei autenticata · verifica misure radio...")
        self._log("Sessione API Huawei attiva (non prova aggancio LTE)")
        info = snapshot.get("device_information")
        if isinstance(info, dict):
            model = str(info.get("DeviceName") or info.get("Model") or "").strip()
            if model:
                self.detected_model = model
                self._log("Modello dichiarato dal firmware: " + model[:72])
        self.available = supported_bands(snapshot.get("mode_list"))
        for band, check in self.bench_checks.items():
            check.setEnabled(band in self.available)
            if band not in self.available:
                check.setChecked(False)
        if self.available:
            self.support.setText("Bande annunciate via API: " +
                                 ", ".join("B" + str(b) for b in self.available))
            for band, check in self.band_checks.items():
                check.setEnabled(band in self.available)
                check.setChecked(band in self.available)
        else:
            self.support.setText("Bande da script E5577 (fallback non verificato dal firmware)")
        # Reflect the *actual* radio configuration before the first edit.
        current = snapshot.get("net_mode", {})
        if isinstance(current, dict):
            mode_index = self.mode.findData(str(current.get("NetworkMode", "")))
            if mode_index >= 0:
                self.mode.setCurrentIndex(mode_index)
            try:
                from .radio import bands_from_mask
                active = bands_from_mask(current.get("LTEBand", ""))
                if active:
                    for band, check in self.band_checks.items():
                        check.setChecked(band in active and (not self.available or band in self.available))
            except ValueError:
                self._log("Maschera radio corrente non interpretabile; nessuna selezione applicata.")
        self._mask()
        self._set_online(True)
        self._reading(snapshot)

    def _reading(self, data):
        self.snapshot.update(data)
        signal = self.snapshot.get("signal", {})
        self.has_measurements = has_radio_measurements(signal)
        overview = network_overview(
            self.snapshot.get("monitoring_status"),
            self.snapshot.get("plmn"),
            signal,
        )
        for key, label in self.network_labels.items():
            if key == "connection":
                label.setText(friendly_connection(overview[key]))
            elif key == "bars":
                label.setText(friendly_signal(overview[key]))
            elif key == "rf":
                label.setText(friendly_rf(overview[key]))
            else:
                label.setText(overview[key])
        down, up = traffic_rates(self.snapshot.get("traffic_statistics"))
        self.traffic_label.setText(
            f"Trasferimento in questo momento:  Scaricamento ↓ {format_rate(down)}  "
            f"Invio ↑ {format_rate(up)}"
        )
        self._append_history(self.snapshot)
        if self.online:
            connected = overview["connection"].startswith("Connessa")
            self.status.setText(
                "● " + ("Pocket collegato · " if connected else "Pocket raggiungibile · ")
                + friendly_connection(overview["connection"]) + " · "
                + overview["network"]
            )
            self._set_online(self.online)
        if isinstance(signal, dict):
            lower = {str(k).lower(): v for k, v in signal.items()}
            for key, label in self.metrics.items():
                value = lower.get(key)
                if key == "cellid":
                    value = value or lower.get("cell_id")
                if key == "earfcn":
                    value = value or lower.get("dl_earfcn")
                label.setText(_show(value))
            self.signals.setRowCount(0)
            for key, val in sorted(signal.items()):
                row = self.signals.rowCount()
                self.signals.insertRow(row)
                self.signals.setItem(row, 0, QTableWidgetItem(str(key)))
                self.signals.setItem(row, 1, QTableWidgetItem(_show(val)))
        cfg = self.snapshot.get("net_mode", {})
        if isinstance(cfg, dict) and cfg.get("LTEBand"):
            self.current_label.setText(
                f"Attuale: LTEBand={cfg['LTEBand']} · NetworkMode={cfg.get('NetworkMode','—')}"
            )
        self.raw.setPlainText(json.dumps(safe_json_data(self.snapshot), ensure_ascii=False, indent=2, default=str))

    def _preset(self, name):
        if name not in PRESETS:
            return
        bands = PRESETS[name]
        for band, check in self.band_checks.items():
            check.setChecked(band in bands and (not self.available or band in self.available))
        self._mask()

    def _mask(self):
        selected = [band for band, check in self.band_checks.items() if check.isChecked()]
        self.mask_label.setText("LTEBand=" + (mask_hex(selected) if selected else "—"))
        current = tuple(selected)
        matching = next(
            (name for name, preset in PRESETS.items() if tuple(preset) == current),
            "Personalizzato",
        )
        # Programmatic change must not invoke _preset and overwrite the
        # configuration read back from the connected modem.
        self.preset.blockSignals(True)
        self.preset.setCurrentText(matching)
        self.preset.blockSignals(False)

    def _selection(self):
        selected = [b for b, check in self.band_checks.items() if check.isChecked()]
        if not selected:
            QMessageBox.warning(self, "Bande", "Seleziona almeno una banda")
            return None
        return selected

    def _busy(self, value: bool):
        self.busy = value
        self._set_online(self.online)

    def _apply(self):
        if not self.online or self.busy or self.radio_worker is None:
            return
        bands = self._selection()
        if bands is None:
            return
        mask = mask_hex(bands)
        if QMessageBox.question(self, "Conferma band locking",
                f"Applicare LTEBand={mask} alle bande {bands}?\n"
                "La connessione dati mobile potrebbe interrompersi.") != QMessageBox.StandardButton.Yes:
            return
        self._busy(True)
        self.radio_worker.submit("apply", mask=mask, mode=self.mode.currentData())

    def _restore(self):
        if not self.online or self.busy or self.radio_worker is None:
            return
        if QMessageBox.question(self, "Ripristino", "Ripristinare la configurazione radio precedente?") == QMessageBox.StandardButton.Yes:
            self._busy(True)
            self.radio_worker.submit("restore")

    def _scan(self):
        if not self.online or self.busy or self.radio_worker is None:
            return
        if not self.has_measurements:
            QMessageBox.warning(self, "Misure LTE assenti",
                                "Il firmware non sta fornendo misure RF. "
                                "Controlla SIM, stato rete e segnale prima di avviare lo scanner.")
            return
        bands = self._selection()
        if bands is None:
            return
        if QMessageBox.question(self, "Band scanner",
                f"Misurare B{', B'.join(map(str, bands))}?\n"
                "Interromperà temporaneamente la WAN. Il rollback automatico non è garantito "
                "se le API diventano irraggiungibili.") != QMessageBox.StandardButton.Yes:
            return
        self.scan_results = []
        self.scan_table.setRowCount(0)
        self._busy(True)
        self.radio_worker.submit("scan", bands=bands)

    def _route_check(self):
        if not self.online or self.busy or self.radio_worker is None:
            return
        self._busy(True)
        self.benchmark_label.setText("Controllo della connessione in corso: nessuna impostazione viene modificata...")
        self.radio_worker.submit("route_check")

    def _benchmark(self):
        if not self.online or self.busy or self.radio_worker is None:
            return
        bands = [
            band for band, check in self.bench_checks.items()
            if check.isChecked() and check.isEnabled()
        ]
        if not bands:
            QMessageBox.warning(self, "Benchmark", "Seleziona almeno una banda LTE supportata.")
            return
        repeats = int(self.test_repeats.currentData())
        size = int(self.test_size.currentData())
        total_mib = len(bands) * repeats * size / 1048576
        note = (
            f"Benchmark di {len(bands)} bande singole: " + ", ".join("B" + str(b) for b in bands)
            + f".\\nDownload massimo programmato: {total_mib:g} MiB "
            "(esclusi header/retry).\\n"
            "Verranno modificate le bande LTE e il servizio mobile potrebbe "
            "interrompersi anche per diversi minuti. Il ripristino della "
            "configurazione originale sarà tentato e verificato, "
            "ma non è garantito se l'API diventa irraggiungibile.\\n"
            "Se il Dell non usa direttamente il pocket come gateway, "
            "il benchmark viene bloccato PRIMA di qualsiasi scrittura.\\n"
            "Confermi?"
        )
        if QMessageBox.question(
            self, "Benchmark con traffico reale", note.replace("\\n", "\n")
        ) != QMessageBox.StandardButton.Yes:
            return
        self.benchmark_results = []
        self.benchmark_table.setRowCount(0)
        self.benchmark_label.setText("Benchmark in corso: non scollegare il pocket.")
        self._busy(True)
        self.radio_worker.submit(
            "benchmark", bands=bands, repeats=repeats, bytes_per_sample=size
        )

    def _cancel(self):
        if self.radio_worker:
            self.radio_worker.cancel.set()
            self.scan_status.setText("Stop richiesto · rollback in corso/non appena possibile")
            self.cancel_btn.setEnabled(False)
            self.bench_cancel_btn.setEnabled(False)

    def _progress(self, item):
        details = str(item.get("status", ""))
        if "band" in item:
            details += f" · B{item['band']}"
        if "step" in item and "total" in item:
            details += f" · {item['step']}/{item['total']}"
        self.scan_status.setText(details)
        if self.busy:
            self.benchmark_label.setText(details)


    def _job_done(self, command, ok, message, data):
        self._busy(False)
        self._log(("OK: " if ok else "ERRORE: ") + message)
        if command == "route_check":
            self.benchmark_label.setText(friendly_route(ok, message))
            if not ok:
                self._log("Verifica connessione non riuscita. Dettagli disponibili in Attività recenti.")
        if command == "benchmark":
            self.benchmark_results = data if isinstance(data, list) else []
            if ok and self.benchmark_results:
                self.benchmark_runs.append({
                    "at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "results": [result.safe_dict() for result in self.benchmark_results],
                })
                self.benchmark_runs = self.benchmark_runs[-24:]
            self.benchmark_history_label.setText(
                f"Confronti effettuati: {len(self.benchmark_runs)} (massimo 24). "
                "Puoi esportarli dalle opzioni avanzate."
            )
            self.benchmark_table.setRowCount(0)
            for result in self.benchmark_results:
                idx = self.benchmark_table.rowCount()
                self.benchmark_table.insertRow(idx)
                values = (
                    "B" + str(result.band), friendly_band_status(result.status),
                    _show(result.med_mbps), _show(result.med_ttfb_ms),
                    str(result.completed_samples),
                )
                for col, value in enumerate(values):
                    self.benchmark_table.setItem(idx, col, QTableWidgetItem(value))
            valid = ranking(self.benchmark_results)
            if valid:
                best = valid[0]
                self.benchmark_label.setText(friendly_benchmark_result(best))
            else:
                self.benchmark_label.setText(
                    "Confronto terminato senza risultati utilizzabili. "
                    "Vedi Attività recenti nelle opzioni avanzate."
                    if not ok else "Non sono disponibili prove valide da confrontare."
                )
        if command == "scan":
            self.scan_results = data if isinstance(data, list) else []
            if any(row.get("status") == "Nessuna misura" for row in self.scan_results):
                self._log("ATTENZIONE: scanner senza letture RF su una o più bande. "
                          "Lo stato API non equivale ad aggancio LTE.")

            self.scan_table.setRowCount(0)
            for item in self.scan_results:
                row = self.scan_table.rowCount()
                self.scan_table.insertRow(row)
                for col, key in enumerate(("band", "rsrp", "rsrq", "sinr", "rssi", "pci", "status")):
                    self.scan_table.setItem(row, col, QTableWidgetItem(_show(item.get(key))))
        if not ok:
            QMessageBox.warning(self, "Radio: verifica fallita", message)

    def _export(self):
        if not self.snapshot:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Esporta radio", "pocket-radio.json", "JSON (*.json)")
        if not path:
            return
        doc = {"version": __version__, "timestamp": datetime.now().isoformat(),
               "snapshot": safe_json_data(self.snapshot),
               "scan": safe_json_data(self.scan_results),
               "telemetry": self.timeline.export(),
               "band_benchmark": [row.safe_dict() for row in self.benchmark_results],
               "band_benchmark_runs": self.benchmark_runs}
        try:
            Path(path).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
            self._log("JSON diagnostico esportato con redazione campi sensibili noti")
        except Exception as exc:
            QMessageBox.warning(self, "Export", str(exc))

    def _failed(self, message: str):
        self.status.setText("● Connessione non riuscita")
        self._log("Sessione fallita: " + message)
        QMessageBox.warning(self, "Huawei API", message)

    def _disconnect(self):
        if self.radio_worker:
            self.radio_worker.shutdown()
            self.status.setText("● Chiusura sessione in corso")
        self.password.clear()

    def _worker_finished(self):
        self.radio_worker = None
        self.busy = False
        self._set_online(False)
        self.status.setText("● Disconnesso")
        self._log("Sessione terminata")

    def closeEvent(self, event):
        if self.radio_worker and self.radio_worker.isRunning():
            self.radio_worker.shutdown()
            if not self.radio_worker.wait(1800):
                event.ignore()
                QMessageBox.information(self, "Operazione radio", "Il modem è occupato o il rollback è in corso. Non chiudere fino al termine.")
                return
        if self.discovery_worker and self.discovery_worker.isRunning():
            if not self.discovery_worker.wait(1800):
                event.ignore()
                return
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Pocket Radio Manager")
    window = PocketWindow()
    window.show()
    return app.exec()
