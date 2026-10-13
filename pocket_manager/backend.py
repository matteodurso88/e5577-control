"""Huawei radio API adapter. All calls must run in one dedicated worker thread."""

from __future__ import annotations

import statistics
import threading
import time
from collections.abc import Callable

from .radio import RadioConfig, mask_hex, numeric_metric, has_radio_measurements


class RadioError(RuntimeError):
    pass


class HuaweiRadioBackend:
    def __init__(self, host: str, username: str, password: str):
        from ipaddress import IPv4Address, ip_address
        addr = ip_address(host)
        if not isinstance(addr, IPv4Address) or not (addr.is_private or addr.is_link_local):
            raise ValueError("Il pocket deve usare un IPv4 locale")
        self.host, self.username, self.password = host, username, password
        self.connection = None
        self.client = None
        self.previous: RadioConfig | None = None

    def __enter__(self):
        from huawei_lte_api.Client import Client
        from huawei_lte_api.Connection import Connection
        self.connection = Connection(
            f"http://{self.host}/", username=self.username, password=self.password
        )
        try:
            self.connection.__enter__()
            self.client = Client(self.connection)
            self.client.net.net_mode()  # force session/authorization validation
        except BaseException:
            self.connection.__exit__(None, None, None)
            self.connection = None
            raise
        finally:
            self.password = ""
        return self

    def __exit__(self, typ, exc, tb):
        self.client = None
        if self.connection is not None:
            self.connection.__exit__(typ, exc, tb)
            self.connection = None

    def _read(self, group, name: str) -> dict:
        fn = getattr(group, name, None)
        if fn is None:
            return {"__error__": "Endpoint non previsto dalla libreria"}
        try:
            value = fn()
            return value if isinstance(value, dict) else {"value": value}
        except Exception as exc:
            return {"__error__": f"{type(exc).__name__}: {exc}"}

    def snapshot(self, full: bool = False) -> dict:
        if self.client is None:
            raise RadioError("Pocket non connesso")
        result = {
            "signal": self._read(self.client.device, "signal"),
            "net_mode": self._read(self.client.net, "net_mode"),
            "plmn": self._read(self.client.net, "current_plmn"),
        }
        if full:
            result["mode_list"] = self._read(self.client.net, "net_mode_list")
            result["cell_info"] = self._read(self.client.net, "cell_info")
            # These firmware endpoints are optional. Keep auth success
            # distinct from evidence of a registered/connected LTE modem.
            monitoring = getattr(self.client, "monitoring", None)
            if monitoring is not None:
                result["monitoring_status"] = self._read(monitoring, "status")
            result["device_information"] = self._read(self.client.device, "information")
        return result

    def config(self) -> RadioConfig:
        if self.client is None:
            raise RadioError("Pocket non connesso")
        return RadioConfig.from_api(self.client.net.net_mode())

    def _write_verified(self, target: RadioConfig, *, retries: int = 12,
                        cancel: threading.Event | None = None) -> RadioConfig:
        if self.client is None:
            raise RadioError("Pocket non connesso")
        # An interrupted scan must not send a new radio command.
        if cancel is not None and cancel.is_set():
            raise RadioError("Scansione interrotta prima della modifica radio")
        try:
            self.client.net.set_net_mode(
                lteband=target.lte_band,
                networkband=target.network_band,
                networkmode=target.network_mode,
            )
        except Exception as exc:
            raise RadioError(f"Modifica LTE rifiutata dal firmware: {exc}") from exc
        last = ""
        for _ in range(retries):
            if cancel and cancel.is_set():
                raise RadioError("Read-back interrotto: configurazione non verificata")
            time.sleep(1.0)
            try:
                current = self.config()
                if target.matches(current):
                    return current
                last = f"LTEBand={current.lte_band}, NetworkMode={current.network_mode}"
            except Exception as exc:
                last = f"{type(exc).__name__}: {exc}"
        raise RadioError(f"Comando inviato ma read-back NON confermato ({last})")

    def apply(self, mask: str, mode: str) -> RadioConfig:
        from .radio import normalized_mask
        if mode not in ("00", "03"):
            raise ValueError("NetworkMode non autorizzato")
        current = self.config()
        target = RadioConfig(normalized_mask(mask), current.network_band, mode)
        if current.matches(target):
            return current
        self.previous = current
        return self._write_verified(target)

    def restore(self) -> RadioConfig:
        if self.previous is None:
            raise RadioError("Nessuna configurazione precedente")
        current = self.config()
        if current.matches(self.previous):
            return current
        return self._write_verified(self.previous)

    def scan(self, bands: list[int], cancel: threading.Event,
             progress: Callable[[dict], None]) -> list[dict]:
        if not bands:
            raise ValueError("Nessuna banda selezionata")
        baseline = self.config()
        rows: list[dict] = []
        restore_error = None
        scan_error = None
        try:
            for idx, band in enumerate(bands, 1):
                if cancel.is_set():
                    break
                progress({"status": "Configurazione", "band": band,
                          "step": idx, "total": len(bands)})
                # The callback may request cancellation synchronously.
                # Do not change bands or create an error row in this case.
                if cancel.is_set():
                    break
                try:
                    target = RadioConfig(mask_hex([band]), baseline.network_band, "03")
                    self._write_verified(target, cancel=cancel)
                    samples = []
                    for _ in range(4):
                        if cancel.is_set():
                            break
                        time.sleep(1.0)
                        sample = self._read(self.client.device, "signal")
                        if "__error__" not in sample:
                            samples.append(sample)
                    if cancel.is_set():
                        break
                    if not samples:
                        raise RadioError("Nessun campione radio")
                    def median(field: str):
                        vals = [v for s in samples
                                if (v := numeric_metric(s.get(field))) is not None]
                        return statistics.median(vals) if vals else None
                    last = samples[-1]
                    row = {"band": band, "rsrp": median("rsrp"),
                           "rsrq": median("rsrq"), "sinr": median("sinr"),
                           "rssi": median("rssi"), "pci": last.get("pci"),
                           "cellid": last.get("cellid") or last.get("cell_id"),
                           "status": ("OK" if any(has_radio_measurements(s) for s in samples)
                                      else "Nessuna misura")}
                except Exception as exc:
                    # Cancelling mid read-back may already have changed the
                    # modem. Exit without an error row and let finally perform
                    # a non-cancellable restoration of the initial baseline.
                    if cancel.is_set():
                        break
                    row = {"band": band, "status": "Errore", "error": str(exc)}
                rows.append(row)
                progress({"status": row["status"], "band": band,
                          "step": idx, "total": len(bands)})
        except Exception as exc:
            scan_error = str(exc)
        finally:
            # Rollback is deliberately NOT cancellable.
            progress({"status": "Ripristino baseline"})
            try:
                if not baseline.matches(self.config()):
                    self._write_verified(baseline, retries=15)
                progress({"status": "Baseline ripristinata"})
            except Exception as exc:
                self.previous = baseline
                restore_error = str(exc)
                progress({"status": "ATTENZIONE: rollback non verificato"})
        if restore_error:
            raise RadioError(
                "ROLLBACK NON VERIFICATO: " + restore_error
                + ". Usare Web UI/precedente profilo per il ripristino."
            )
        if scan_error:
            raise RadioError("Scanner fallito, baseline ripristinata: " + scan_error)
        return rows
