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
from .discovery import discover
from .profiles import PocketProfile, ProfileStore, CredentialStoreError
from .radio import FALLBACK_BANDS, FREQUENCIES, MODES, PRESETS, mask_hex, supported_bands, bands_from_mask, safe_json_data


class DiscoveryWorker(QThread):
    completed = Signal(list)
    failed = Signal(str)

    def __init__(self, saved_hosts: tuple[str, ...]):
        super().__init__()
        self.saved_hosts = saved_hosts

    def run(self):
        try:
            self.completed.emit(discover(self.saved_hosts))
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
                self.reading.emit(first)
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
                    elif command in ("apply", "restore", "scan"):
                        try:
                            if command == "apply":
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
                                message = "Scansione terminata; baseline ripristinata"
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
        self.available: tuple[int, ...] = ()
        self.setWindowTitle("Pocket Radio Manager " + __version__)
        self.resize(1120, 770)
        self._build()
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
        self.discover_btn = QPushButton("Cerca pocket")
        self.discover_btn.clicked.connect(self._discover)
        save = QPushButton("Salva / aggiorna")
        save.clicked.connect(self._save)
        delete = QPushButton("Rimuovi")
        delete.clicked.connect(self._delete)
        for widget in (QLabel("Dispositivi"), self.saved, self.discover_btn, save, delete):
            devices.addWidget(widget)
        outer.addLayout(devices)

        connection = QHBoxLayout()
        self.host = QLineEdit("192.168.8.1")
        self.host.setMaximumWidth(165)
        self.alias = QLineEdit("Il mio pocket")
        self.alias.setMaximumWidth(175)
        self.username = QLineEdit("admin")
        self.username.setMaximumWidth(115)
        self.password = QLineEdit()
        self.password.setMaximumWidth(180)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Password admin")
        self.remember = QCheckBox("Ricorda nel keyring")
        self.connect_btn = QPushButton("Connetti")
        self.connect_btn.clicked.connect(self._connect)
        self.disconnect_btn = QPushButton("Disconnetti")
        self.disconnect_btn.clicked.connect(self._disconnect)
        for item in (QLabel("IP"), self.host, QLabel("Alias"), self.alias,
                     QLabel("Utente"), self.username, QLabel("Password"),
                     self.password, self.remember, self.connect_btn, self.disconnect_btn):
            connection.addWidget(item)
        outer.addLayout(connection)

        self.status = QLabel("● Disconnesso — nessuna modifica radio effettuata")
        outer.addWidget(self.status)
        tabs = QTabWidget()
        tabs.addTab(self._monitor_tab(), "Monitor LTE")
        tabs.addTab(self._bands_tab(), "Bande / Scanner")
        tabs.addTab(self._diagnostics_tab(), "Dati API")
        outer.addWidget(tabs, 1)
        outer.addWidget(QLabel("Registro operazioni"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(125)
        outer.addWidget(self.log)
        self.setStyleSheet(
            "QWidget {font-size: 13px;} QPushButton {padding: 6px 10px;}"
            "QGroupBox {font-weight: bold; margin-top: 10px; padding-top: 9px;}"
            "QGroupBox::title {subcontrol-origin: margin; left: 8px;}"
        )

    def _monitor_tab(self):
        w = QWidget()
        box = QVBoxLayout(w)
        group = QGroupBox("Serving cell / Qualità segnale")
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
        self.signals.setHorizontalHeaderLabels(["Campo firmware", "Valore"])
        self.signals.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        box.addWidget(self.signals, 1)
        return w

    def _bands_tab(self):
        w = QWidget()
        box = QVBoxLayout(w)
        note = QLabel("Solo radio LTE. Le maschere possono interrompere la WAN; alcune configurazioni sono bloccate dal firmware.")
        note.setWordWrap(True)
        box.addWidget(note)
        self.support = QLabel("Bande E5577 da script storico (non ancora verificate)")
        box.addWidget(self.support)
        checks = QHBoxLayout()
        self.band_checks = {}
        for band in FALLBACK_BANDS:
            label = f"B{band} ({FREQUENCIES[band]} MHz)"
            check = QCheckBox(label)
            check.setChecked(True)
            check.stateChanged.connect(self._mask)
            checks.addWidget(check)
            self.band_checks[band] = check
        box.addLayout(checks)
        row = QHBoxLayout()
        self.preset = QComboBox()
        self.preset.addItems(PRESETS.keys())
        self.preset.currentTextChanged.connect(self._preset)
        self.mode = QComboBox()
        for name, value in MODES.items():
            self.mode.addItem(name, value)
        self.mask_label = QLabel("Mask: —")
        row.addWidget(QLabel("Preset"))
        row.addWidget(self.preset)
        row.addWidget(QLabel("NetworkMode"))
        row.addWidget(self.mode)
        row.addWidget(self.mask_label)
        box.addLayout(row)
        actions = QHBoxLayout()
        self.apply_btn = QPushButton("Applica bande")
        self.apply_btn.clicked.connect(self._apply)
        self.restore_btn = QPushButton("Ripristina precedente")
        self.restore_btn.clicked.connect(self._restore)
        self.scan_btn = QPushButton("Scansiona selezionate")
        self.scan_btn.clicked.connect(self._scan)
        self.cancel_btn = QPushButton("Interrompi scan")
        self.cancel_btn.clicked.connect(self._cancel)
        for btn in (self.apply_btn, self.restore_btn, self.scan_btn, self.cancel_btn):
            actions.addWidget(btn)
        box.addLayout(actions)
        self.current_label = QLabel("Stato attuale: —")
        self.scan_status = QLabel("Scanner inattivo")
        box.addWidget(self.current_label)
        box.addWidget(self.scan_status)
        self.scan_table = QTableWidget(0, 7)
        self.scan_table.setHorizontalHeaderLabels(["Banda", "RSRP", "RSRQ", "SINR", "RSSI", "PCI", "Stato"])
        self.scan_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        box.addWidget(self.scan_table, 1)
        self._mask()
        return w

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
        for widget in (self.apply_btn, self.restore_btn, self.scan_btn, self.refresh_btn):
            widget.setEnabled(online and not self.busy)
        self.cancel_btn.setEnabled(online and self.busy)

    def _reload_profiles(self, chosen: str | None = None):
        self.saved.blockSignals(True)
        self.saved.clear()
        self.saved.addItem("— Scegli pocket salvato —", None)
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
        hosts = tuple(p.host for p in self.store.list())
        self.discover_btn.setEnabled(False)
        self._log("Discovery locale in corso (solo lettura)...")
        self.discovery_worker = DiscoveryWorker(hosts)
        self.discovery_worker.completed.connect(self._discovery_done)
        self.discovery_worker.failed.connect(lambda message: self._log("Discovery: " + message))
        self.discovery_worker.finished.connect(lambda: self.discover_btn.setEnabled(True))
        self.discovery_worker.start()

    def _discovery_done(self, devices: list):
        if not devices:
            self._log("Nessun Huawei confermato. Puoi inserire l'IP manualmente.")
            QMessageBox.information(self, "Discovery", "Nessun pocket identificato. Inserisci l'IP manualmente.")
            return
        labels = [f"{d.name} · {d.host} · {d.model}" for d in devices]
        label, ok = QInputDialog.getItem(self, "Pocket rilevati", "Scegli il dispositivo:", labels, 0, False)
        if ok and label in labels:
            found = devices[labels.index(label)]
            self.saved.setCurrentIndex(0)
            self.host.setText(found.host)
            self.alias.setText(found.name)
            self.password.clear()
            self.remember.setChecked(False)
            self._log(f"Dispositivo Huawei identificato: {found.model} · {found.host}")

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
        self.password.clear()
        self.status.setText("● Pocket collegato · monitor LTE attivo")
        self._log("Sessione radio attiva")
        self.available = supported_bands(snapshot.get("mode_list"))
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
        bands = PRESETS.get(name, ())
        for band, check in self.band_checks.items():
            check.setChecked(band in bands and (not self.available or band in self.available))
        self._mask()

    def _mask(self):
        selected = [band for band, check in self.band_checks.items() if check.isChecked()]
        self.mask_label.setText("LTEBand=" + (mask_hex(selected) if selected else "—"))

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

    def _cancel(self):
        if self.radio_worker:
            self.radio_worker.cancel.set()
            self.scan_status.setText("Stop richiesto · rollback in corso/non appena possibile")
            self.cancel_btn.setEnabled(False)

    def _progress(self, item):
        self.scan_status.setText(
            f"{item.get('status','')} · B{item.get('band','—')} "
            f"{item.get('step','')}/{item.get('total','')}"
        )

    def _job_done(self, command, ok, message, data):
        self._busy(False)
        self._log(("OK: " if ok else "ERRORE: ") + message)
        if command == "scan":
            self.scan_results = data if isinstance(data, list) else []
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
               "scan": safe_json_data(self.scan_results)}
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
