"""Non-invasive discovery of local Huawei HiLink API devices.

Device information usually requires login; radio signal and session-token
endpoints are frequently readable anonymously. They permit identifying a
compatible *API*, not necessarily a confirmed hardware model.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv4Interface, ip_address
from pathlib import Path
from socket import AF_INET
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import xml.etree.ElementTree as ET

DEFAULT_HOST = "192.168.8.1"
MAX_CANDIDATES = 32
MAX_RESPONSE_BYTES = 16384
_SIGNAL_FIELDS = frozenset({
    "rsrp", "rsrq", "sinr", "rssi", "pci", "cell_id", "cellid", "earfcn",
    "dl_earfcn", "band", "mode", "rscp", "ecio",
})
_ENDPOINTS = (
    "api/device/information",
    "api/device/signal",
    "api/webserver/SesTokInfo",
)


@dataclass(frozen=True)
class DiscoveredPocket:
    host: str
    model: str
    name: str
    manufacturer: str
    identity: str | None = None
    detection: str = "identified"  # "identified" or "compatible_api"

    @property
    def url(self) -> str:
        return f"http://{self.host}/"


@dataclass(frozen=True)
class DiscoveryReport:
    candidates: tuple[str, ...]
    devices: tuple[DiscoveredPocket, ...]
    diagnostics: tuple[str, ...]


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _local_ip(host: str) -> str | None:
    try:
        ip = ip_address(host)
        if isinstance(ip, IPv4Address) and (ip.is_private or ip.is_link_local) and not ip.is_loopback:
            return str(ip)
    except (ValueError, TypeError):
        pass
    return None


def _gateway_candidates() -> list[str]:
    """Read kernel default gateways on Linux; no commands or privileges.

    Other OSs still receive interface-based .1/.254 candidates, saved hosts
    and manual IP. Only private IPv4 gateways are eligible.
    """
    import sys

    if not sys.platform.startswith("linux"):
        return []
    gateways = []
    try:
        lines = Path("/proc/net/route").read_text(encoding="ascii").splitlines()[1:]
        for line in lines:
            parts = line.split()
            if len(parts) < 4 or parts[1] != "00000000":
                continue
            flags = int(parts[3], 16)
            if not flags & 0x2:
                continue
            addr = str(IPv4Address(int.from_bytes(
                bytes.fromhex(parts[2]), byteorder="little"
            )))
            if _local_ip(addr):
                gateways.append(addr)
    except (ValueError, OSError):
        pass
    return gateways


def candidates_from_interfaces(
    addresses: list[tuple[str, str]],
    manual_hosts: tuple[str, ...] = (),
    gateways: tuple[str, ...] = (),
) -> list[str]:
    """Build a small bounded probe set; don't sweep local subnets.

    Priority: user-supplied/saved hosts, Huawei default, actual gateway,
    then likely .1/.254 gateway addresses from local /24s. Priority is
    preserved when candidate count exceeds the safety cap.
    """
    hosts: dict[str, None] = {}

    def add(host: str) -> None:
        validated = _local_ip(host)
        if validated is not None:
            hosts.setdefault(validated, None)

    for candidate in manual_hosts:
        add(candidate)
    add(DEFAULT_HOST)
    for gateway in gateways:
        add(gateway)

    for address, netmask in addresses:
        try:
            interface = IPv4Interface(f"{address}/{netmask}")
            if not _local_ip(str(interface.ip)):
                continue
            # Even for a /16 or larger LAN, probe only likely gateway IPs
            # within this interface's own /24.
            local = IPv4Interface(f"{interface.ip}/24").network
            for suffix in (1, 254):
                addr = str(local.network_address + suffix)
                if addr != str(interface.ip):
                    add(addr)
        except (ValueError, TypeError):
            continue
    return list(hosts)[:MAX_CANDIDATES]


def host_candidates(manual_hosts: tuple[str, ...] = ()) -> list[str]:
    """Local interface probing is portable; gateway optimization is Linux."""
    try:
        import psutil
        pairs = [
            (entry.address, entry.netmask)
            for values in psutil.net_if_addrs().values()
            for entry in values
            if entry.family == AF_INET and entry.netmask
        ]
    except (ImportError, OSError):
        pairs = []
    return candidates_from_interfaces(
        pairs, manual_hosts, tuple(_gateway_candidates())
    )


def _xml_fields(payload: bytes) -> dict[str, str] | None:
    if not payload or len(payload) > MAX_RESPONSE_BYTES:
        return None
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return None
    if root.tag.lower() != "response":
        return None
    return {
        element.tag.lower(): (element.text or "").strip()
        for element in root
        if len(element) == 0
    }


def parse_device_information(payload: bytes, host: str) -> DiscoveredPocket | None:
    fields = _xml_fields(payload)
    if fields is None:
        return None
    manufacturer = fields.get("manufacturer", "")
    model = fields.get("devicename", "") or fields.get("model", "")
    name = fields.get("devicename", "") or model
    if not ("huawei" in manufacturer.lower()
            or model.upper().startswith(("E5577", "E5"))):
        return None
    return DiscoveredPocket(
        host=host,
        model=model or "Huawei (modello non disponibile)",
        name=name or "Huawei Pocket",
        manufacturer=manufacturer or "Huawei",
    )


def parse_compatible_endpoint(payload: bytes, host: str, endpoint: str) -> DiscoveredPocket | None:
    fields = _xml_fields(payload)
    if fields is None:
        return None
    compatible = False
    if endpoint == "api/device/signal":
        compatible = bool(_SIGNAL_FIELDS.intersection(fields))
    elif endpoint == "api/webserver/SesTokInfo":
        # Huawei HiLink session/token pair; never retain or log the values.
        compatible = "sesinfo" in fields and "tokinfo" in fields
    if not compatible:
        return None
    return DiscoveredPocket(
        host=host,
        model="Da verificare dopo login",
        name="Pocket API Huawei compatibile",
        manufacturer="Huawei API compatibile (non identificato)",
        detection="compatible_api",
    )


def _fetch_api(host: str, endpoint: str, timeout: float) -> tuple[bytes | None, str]:
    """A bounded anonymous GET, direct to local address, no redirects/proxy."""
    try:
        opener = build_opener(ProxyHandler({}), _NoRedirect)
        req = Request(
            f"http://{host}/{endpoint}",
            headers={"Accept": "application/xml,text/xml", "User-Agent": "PocketRadioManager/0.1"},
        )
        with opener.open(req, timeout=timeout) as response:
            status = response.status
            if status != 200:
                return None, f"HTTP {status}"
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            if len(payload) > MAX_RESPONSE_BYTES:
                return None, "Risposta XML troppo grande"
            return payload, "HTTP 200"
    except HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except (URLError, OSError, TimeoutError) as exc:
        # Don't expose token, response body or secret values in diagnostics.
        return None, type(exc).__name__


def probe_detailed(host: str, timeout: float = 1.5) -> tuple[DiscoveredPocket | None, tuple[str, ...]]:
    validated = _local_ip(host)
    if validated is None:
        return None, (f"{host}: IP locale non valido",)
    checks: list[str] = []
    for endpoint in _ENDPOINTS:
        payload, status = _fetch_api(validated, endpoint, timeout)
        if payload is None:
            checks.append(f"{endpoint}: {status}")
            continue
        if endpoint == "api/device/information":
            device = parse_device_information(payload, validated)
        else:
            device = parse_compatible_endpoint(payload, validated, endpoint)
        if device is not None:
            result = "identificato" if device.detection == "identified" else "API compatibile (modello da verificare)"
            checks.append(f"{endpoint}: {result}")
            return device, (f"{validated}: " + "; ".join(checks),)
        checks.append(f"{endpoint}: risposta non identificante")
    return None, (f"{validated}: " + "; ".join(checks),)


def probe(host: str, timeout: float = 1.5) -> DiscoveredPocket | None:
    return probe_detailed(host, timeout)[0]


def discover_report(manual_hosts: tuple[str, ...] = (), timeout: float = 1.5,
                    workers: int = 6) -> DiscoveryReport:
    hosts = host_candidates(manual_hosts)
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 8))) as executor:
        outcomes = list(executor.map(lambda host: probe_detailed(host, timeout), hosts))
    devices = tuple(item[0] for item in outcomes if item[0] is not None)
    diagnostics = tuple(line for item in outcomes for line in item[1])
    return DiscoveryReport(tuple(hosts), devices, diagnostics)


def discover(manual_hosts: tuple[str, ...] = (), timeout: float = 1.5,
             workers: int = 6) -> list[DiscoveredPocket]:
    return list(discover_report(manual_hosts, timeout, workers).devices)


if __name__ == "__main__":
    report = discover_report()
    print("Pocket discovery — sola lettura, nessuna credenziale")
    print(f"IP interrogati: {len(report.candidates)}")
    for item in report.diagnostics:
        print(item)
    print(f"Compatibili: {len(report.devices)}")
