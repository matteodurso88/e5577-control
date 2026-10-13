"""Radio models and Huawei LTE-band masks (hex strings, never decimal)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# E5577Cs-321 bands observed in historical user script. Fallback, NOT an API guarantee.
FALLBACK_BANDS = (1, 3, 5, 7, 8, 20)
FREQUENCIES = {1: 2100, 3: 1800, 5: 850, 7: 2600, 8: 900, 20: 800}
MODES = {"Automatico": "00", "Solo LTE": "03"}
PRESETS = {
    "B1": (1,), "B3": (3,), "B7": (7,), "B20": (20,),
    "B1+B3": (1, 3), "B3+B7": (3, 7), "B1+B3+B7": (1, 3, 7),
    "Tutte E5577 (storico)": FALLBACK_BANDS,
}


def parse_mask(value: str | int) -> int:
    if isinstance(value, int):
        if value < 0:
            raise ValueError("Maschera negativa")
        return value
    value = str(value).strip().lower().removeprefix("0x")
    if not re.fullmatch(r"[0-9a-f]+", value):
        raise ValueError("Maschera LTE esadecimale non valida")
    return int(value, 16)


def normalized_mask(value: str | int) -> str:
    return f"{parse_mask(value):x}"


def mask_hex(bands) -> str:
    bands = list(bands)
    if not bands:
        raise ValueError("Selezionare almeno una banda")
    total = 0
    for band in bands:
        if not isinstance(band, int) or not 1 <= band <= 64:
            raise ValueError("Banda LTE fuori intervallo")
        total |= 1 << (band - 1)
    return f"{total:x}"


def bands_from_mask(value: str | int, known=FALLBACK_BANDS) -> tuple[int, ...]:
    mask = parse_mask(value)
    return tuple(b for b in known if mask & (1 << (b - 1)))


def _values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [result for element in value for result in _values(element)]
    if isinstance(value, dict):
        found = [str(value["Value"])] if "Value" in value else []
        for k, item in value.items():
            if k != "Value":
                found.extend(_values(item))
        return found
    return []


def supported_bands(payload: dict | None) -> tuple[int, ...]:
    """Accept only non-sentinel masks explicitly exposed by net-mode-list."""
    if not isinstance(payload, dict):
        return ()
    advertised = 0
    for text in _values(payload.get("LTEBandList", {})):
        try:
            value = parse_mask(text)
        except ValueError:
            continue
        if value and value < 0x7FFFFFFFFFFFFFFF:
            advertised |= value
    return bands_from_mask(advertised)


def numeric_metric(value: Any) -> float | None:
    if value is None:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", str(value).replace("−", "-"))
    return float(m.group(0)) if m else None


def has_radio_measurements(signal: Any) -> bool:
    """An API signal object with mode/psatt but blank LTE readings is NOT a measurement."""
    if not isinstance(signal, dict) or "__error__" in signal:
        return False
    metrics = {str(k).lower(): v for k, v in signal.items()}
    return any(numeric_metric(metrics.get(key)) is not None
               for key in ("rsrp", "rsrq", "sinr", "rssi"))


def network_overview(status: Any, plmn: Any, signal: Any) -> dict[str, str]:
    """Interpret documented Huawei status fields, never infer missing RF values.

    ConnectionStatus=901 reports an active Huawei data session; it does not
    prove end-to-end Internet access from the host workstation.
    SignalIcon/maxsignal is a coarse firmware bar indicator, NOT dBm.
    """
    state = status if isinstance(status, dict) and "__error__" not in status else {}
    operator = plmn if isinstance(plmn, dict) and "__error__" not in plmn else {}

    connection_codes = {
        "900": "Connessione in corso",
        "901": "Connessa (secondo firmware)",
        "902": "Disconnessa",
        "903": "Disconnessione in corso",
        "904": "Connessione fallita",
    }
    connection = connection_codes.get(str(state.get("ConnectionStatus", "")), "Non disponibile")
    networks = {
        "19": "4G LTE", "101": "4G LTE",
        "4": "3G WCDMA", "7": "3G HSPA",
        "9": "HSPA+", "0": "Nessuna rete",
    }
    network = networks.get(
        str(state.get("CurrentNetworkType", "")),
        "Non disponibile",
    )
    sim = {
        "1": "Pronta",
        "0": "Non pronta / sconosciuta",
    }.get(str(state.get("SimStatus", "")), "Non disponibile")

    bars = "Non disponibile"
    try:
        count = int(state.get("SignalIcon", ""))
        maximum = int(state.get("maxsignal", ""))
        if 0 <= count <= maximum <= 10 and maximum > 0:
            bars = f"{count}/{maximum} tacche (indicatore firmware)"
    except (ValueError, TypeError):
        pass

    return {
        "connection": connection,
        "network": network,
        "sim": sim,
        "operator": str(operator.get("FullName") or operator.get("ShortName") or "Non disponibile")[:72],
        "bars": bars,
        "rf": ("Misure avanzate disponibili" if has_radio_measurements(signal)
               else "Misure RSRP/RSRQ/SINR/RSSI indisponibili"),
    }


_SECRET_FIELD = re.compile(
    r"password|cookie|token|secret|imsi|imei|iccid|serial|"
    r"macaddress|ssid|msisdn|phonenumber|ipaddress|phonebook",
    re.IGNORECASE,
)


def safe_json_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): safe_json_data(v) for k, v in value.items()
                if not _SECRET_FIELD.search(str(k))}
    if isinstance(value, (list, tuple)):
        return [safe_json_data(v) for v in value]
    return value


@dataclass(frozen=True)
class RadioConfig:
    lte_band: str
    network_band: str
    network_mode: str

    @classmethod
    def from_api(cls, obj: dict) -> "RadioConfig":
        return cls(str(obj["LTEBand"]), str(obj["NetworkBand"]), str(obj["NetworkMode"]))

    def matches(self, other: "RadioConfig") -> bool:
        return (normalized_mask(self.lte_band) == normalized_mask(other.lte_band)
                and self.network_mode == other.network_mode
                and normalized_mask(self.network_band) == normalized_mask(other.network_band))
