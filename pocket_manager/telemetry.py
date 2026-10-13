"""Read-only, bounded Huawei LTE monitoring history.

Stores only a whitelist of derived non-sensitive status/traffic fields in RAM.
No login credentials, response headers, tokens, cell identifiers or raw payloads.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
import re
import time
from typing import Any

from .radio import network_overview


def _nonnegative_int(value: Any) -> int | None:
    """Counters and rates are bytes, never infer a number from a malformed value."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value.strip()):
        return int(value.strip())
    return None


def format_rate(value: int | None) -> str:
    if value is None:
        return "—"
    units = ("B/s", "KiB/s", "MiB/s", "GiB/s")
    result = float(value)
    for index, unit in enumerate(units):
        if result < 1024 or index == len(units) - 1:
            return f"{result:.1f} {unit}" if index else f"{value} {unit}"
        result /= 1024
    return "—"


def traffic_rates(data: Any) -> tuple[int | None, int | None]:
    """CurrentDownloadRate/CurrentUploadRate from monitoring/traffic-statistics.

    Huawei reports bytes/second on supported models; no guessed fallback
    from lifetime totals as polling timestamps and counter resets vary.
    """
    if not isinstance(data, dict) or "__error__" in data:
        return None, None
    return (_nonnegative_int(data.get("CurrentDownloadRate")),
            _nonnegative_int(data.get("CurrentUploadRate")))


@dataclass(frozen=True)
class TelemetryPoint:
    timestamp: str
    connection: str
    network: str
    sim: str
    operator: str
    bars: str
    rf: str
    down_bps: int | None
    up_bps: int | None
    change: str

    def safe_dict(self) -> dict:
        return asdict(self)


class TelemetryTimeline:
    def __init__(self, limit: int = 120):
        if not 1 <= limit <= 3600:
            raise ValueError("Limite osservazioni fuori intervallo")
        self._items: deque[TelemetryPoint] = deque(maxlen=limit)

    def clear(self) -> None:
        self._items.clear()

    def observe(self, snapshot: dict, *, now: datetime | None = None) -> TelemetryPoint:
        if not isinstance(snapshot, dict):
            raise TypeError("Snapshot radio non valido")
        overview = network_overview(
            snapshot.get("monitoring_status"),
            snapshot.get("plmn"),
            snapshot.get("signal"),
        )
        down, up = traffic_rates(snapshot.get("traffic_statistics"))
        previous = self._items[-1] if self._items else None
        fields = ("connection", "network", "sim", "operator", "bars", "rf")
        if previous is None:
            changed = "Inizio osservazione"
        else:
            changed = ", ".join(field for field in fields
                                if getattr(previous, field) != overview[field])
        instant = now or datetime.now().astimezone()
        if instant.tzinfo is None:
            raise ValueError("Timestamp timezone-aware richiesto")
        point = TelemetryPoint(
            timestamp=instant.isoformat(timespec="seconds"),
            connection=overview["connection"],
            network=overview["network"],
            sim=overview["sim"],
            operator=overview["operator"],
            bars=overview["bars"],
            rf=overview["rf"],
            down_bps=down,
            up_bps=up,
            change=changed,
        )
        self._items.append(point)
        return point

    def points(self) -> tuple[TelemetryPoint, ...]:
        return tuple(self._items)

    def export(self) -> list[dict]:
        return [point.safe_dict() for point in self._items]
