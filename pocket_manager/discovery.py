"""Non-invasive local Huawei pocket discovery.

A detection is confirmed only when the device-information response identifies
a Huawei device. Discovery never attempts login, brute forcing or band changes.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv4Interface, ip_address
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, build_opener
import xml.etree.ElementTree as ET


DEFAULT_HOST = "192.168.8.1"
MAX_CANDIDATES = 32
MAX_RESPONSE_BYTES = 16384


@dataclass(frozen=True)
class DiscoveredPocket:
    host: str
    model: str
    name: str
    manufacturer: str
    identity: str | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}/"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def candidates_from_interfaces(addresses: list[tuple[str, str]],
                               manual_hosts: tuple[str, ...] = ()) -> list[str]:
    """Accepts (IPv4 address, netmask) pairs; probes only .1/.254 on local /24s.

    This is candidate generation, not identification. Local policy can pass
    explicitly known IPs; no active subnet sweep is performed.
    """
    hosts = {DEFAULT_HOST}
    for host in manual_hosts:
        try:
            ip = ip_address(host)
            if isinstance(ip, IPv4Address) and (ip.is_private or ip.is_link_local):
                hosts.add(str(ip))
        except ValueError:
            continue
    for address, netmask in addresses:
        try:
            interface = IPv4Interface(f"{address}/{netmask}")
            ip = interface.ip
            if not (ip.is_private or ip.is_link_local) or ip.is_loopback:
                continue
            # For large (e.g. /16) networks, restrict discovery to the
            # address's own /24 instead of scanning thousands of addresses.
            local = IPv4Interface(f"{ip}/24").network
            for suffix in (1, 254):
                candidate = str(local.network_address + suffix)
                if candidate != str(ip):
                    hosts.add(candidate)
        except (ValueError, TypeError):
            continue
    return sorted(hosts, key=lambda h: int(IPv4Address(h)))[:MAX_CANDIDATES]


def host_candidates(manual_hosts: tuple[str, ...] = ()) -> list[str]:
    """Enumerate local IPv4 interfaces on Windows, Linux and macOS via psutil."""
    try:
        import psutil
        from socket import AF_INET
        pairs = [
            (entry.address, entry.netmask)
            for values in psutil.net_if_addrs().values()
            for entry in values
            if entry.family == AF_INET and entry.netmask
        ]
    except (ImportError, OSError):
        pairs = []
    return candidates_from_interfaces(pairs, manual_hosts)


def parse_device_information(payload: bytes, host: str) -> DiscoveredPocket | None:
    if len(payload) > MAX_RESPONSE_BYTES:
        return None
    try:
        root = ET.fromstring(payload)
    except ET.ParseError:
        return None
    if root.tag.lower() != "response":
        return None
    fields = {
        element.tag.lower(): (element.text or "").strip()
        for element in root
        if len(element) == 0
    }
    manufacturer = fields.get("manufacturer", "")
    model = (fields.get("devicename", "") or fields.get("model", "")
             or fields.get("productfamily", ""))
    name = fields.get("devicename", "") or model
    # Some firmwares omit Manufacturer but report the E5577 model.
    confirmed = "huawei" in manufacturer.lower() or model.upper().startswith(("E5577", "E5"))
    if not confirmed:
        return None
    return DiscoveredPocket(
        host=host,
        model=model or "Huawei (model unavailable)",
        name=name or "Huawei Pocket",
        manufacturer=manufacturer or "Huawei",
        # Do not store serial, IMEI or MAC from unauthenticated responses:
        # identity reconciliation requires a separate consent-based step.
    )


def probe(host: str, timeout: float = 1.5) -> DiscoveredPocket | None:
    """Read-only Huawei API probe; explicit timeouts and no HTTP redirects."""
    try:
        addr = ip_address(host)
        if not isinstance(addr, IPv4Address) or not (addr.is_private or addr.is_link_local):
            return None
        opener = build_opener(_NoRedirect)
        with opener.open(f"http://{addr}/api/device/information", timeout=timeout) as response:
            if response.status != 200:
                return None
            payload = response.read(MAX_RESPONSE_BYTES + 1)
        return parse_device_information(payload, str(addr))
    except (HTTPError, URLError, ValueError, OSError, TimeoutError):
        return None


def discover(manual_hosts: tuple[str, ...] = (), timeout: float = 1.5,
             workers: int = 6) -> list[DiscoveredPocket]:
    hosts = host_candidates(manual_hosts)
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 8))) as executor:
        results = list(executor.map(lambda host: probe(host, timeout), hosts))
    return [result for result in results if result is not None]
