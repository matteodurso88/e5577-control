"""Controlled LTE allowed-band benchmark; real WAN egress is mandatory.

This is NOT a cell/PCI scanner: each single-band mask restricts *allowed*
LTE bands; firmware does not expose a verified serving band on E5577Cs-321.
Never attempt HTTP traffic unless Linux confirms a route via the pocket.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from ipaddress import IPv4Address, ip_address
from statistics import median
import http.client
import json
import socket
import ssl
import subprocess
import threading
import time
from typing import Callable

from .radio import RadioConfig, mask_hex, supported_bands

BENCHMARK_HOST = "speed.cloudflare.com"
DOWNLOAD_PATH = "/__down?bytes="
DEFAULT_BYTES = 1_048_576
DEFAULT_REPEATS = 2
MAX_BYTES = 4_194_304
MAX_REPEATS = 3


class BenchmarkError(RuntimeError):
    pass


@dataclass(frozen=True)
class Egress:
    destination: str
    gateway: str
    interface: str
    source: str


@dataclass(frozen=True)
class DownloadSample:
    mbps: float
    ttfb_ms: float
    bytes_received: int


def check_route(pocket_ip: str, destination: str, *,
                run: Callable = subprocess.run) -> Egress:
    """Fail closed: on Dell Linux benchmark traffic must exit via pocket IP."""
    from sys import platform

    if not platform.startswith("linux"):
        raise BenchmarkError("Routing verificabile solo su Linux in questa versione")
    for address in (pocket_ip, destination):
        parsed = ip_address(address)
        if not isinstance(parsed, IPv4Address):
            raise BenchmarkError("Il benchmark richiede IPv4")
    try:
        command = run(["ip", "-j", "-4", "route", "get", destination],
                      capture_output=True, text=True, timeout=3, check=True)
        paths = json.loads(command.stdout)
        route = paths[0]
    except (OSError, ValueError, IndexError, KeyError, subprocess.SubprocessError) as exc:
        raise BenchmarkError("Impossibile verificare la route di uscita dal Dell") from exc
    gateway = str(route.get("gateway") or route.get("via") or "")
    interface = str(route.get("dev") or "")
    source = str(route.get("prefsrc") or route.get("src") or "")
    if gateway != pocket_ip:
        raise BenchmarkError(
            f"Route NON attraverso il pocket: gateway={gateway or 'diretta'}, "
            f"interfaccia={interface or '?'}; richiesto gateway={pocket_ip}. "
            "Collegare il Dell al Wi-Fi/USB del pocket prima del benchmark."
        )
    try:
        src = ip_address(source)
        if not isinstance(src, IPv4Address) or src.is_loopback or not interface:
            raise ValueError("IP locale o interfaccia non validi")
    except ValueError as exc:
        raise BenchmarkError("Il routing non fornisce una sorgente IPv4 sicura") from exc
    return Egress(destination=destination, gateway=gateway,
                  interface=interface, source=source)


def resolve_endpoint(host: str = BENCHMARK_HOST) -> str:
    """Resolve one IPv4 once, pin that address across all band comparisons."""
    try:
        entries = socket.getaddrinfo(host, 443, family=socket.AF_INET,
                                     type=socket.SOCK_STREAM)
    except OSError as exc:
        raise BenchmarkError("DNS endpoint test non disponibile") from exc
    ips = sorted({entry[4][0] for entry in entries})
    if not ips:
        raise BenchmarkError("L'endpoint di test non ha un IPv4")
    return ips[0]


def https_download(egress: Egress, *, bytes_requested: int = DEFAULT_BYTES,
                   host: str = BENCHMARK_HOST, timeout: float = 15.0) -> DownloadSample:
    """HTTPS GET pinned to validated IPv4 and source, no HTTP proxy/redirects.

    Data cap is fixed; there is no upload. TTFB covers TCP/TLS/HTTP and is
    not equivalent to ICMP ping. Mbps is a short-sample estimate.
    """
    if not 16_384 <= bytes_requested <= MAX_BYTES:
        raise ValueError("Budget per prova fuori limiti (16 KiB .. 4 MiB)")
    started = time.monotonic()
    raw = None
    tls = None
    response = None
    try:
        raw = socket.create_connection((egress.destination, 443),
                                       timeout=timeout,
                                       source_address=(egress.source, 0))
        context = ssl.create_default_context()
        tls = context.wrap_socket(raw, server_hostname=host)
        raw = None
        request = (
            f"GET {DOWNLOAD_PATH}{bytes_requested} HTTP/1.1\r\n"
            f"Host: {host}\r\nAccept: application/octet-stream\r\n"
            "Connection: close\r\nUser-Agent: PocketRadioManager/0.1\r\n\r\n"
        ).encode("ascii")
        tls.sendall(request)
        response = http.client.HTTPResponse(tls)
        response.begin()
        ttfb = (time.monotonic() - started) * 1000.0
        if response.status != 200:
            raise BenchmarkError(f"Server test non disponibile (HTTP {response.status})")
        received = 0
        while received < bytes_requested:
            remaining_time = timeout - (time.monotonic() - started)
            if remaining_time <= 0:
                raise BenchmarkError("Timeout trasferimento benchmark")
            tls.settimeout(max(0.5, min(remaining_time, 5)))
            chunk = response.read(min(65_536, bytes_requested - received))
            if not chunk:
                break
            received += len(chunk)
        elapsed = time.monotonic() - started
        if received != bytes_requested:
            raise BenchmarkError("Trasferimento benchmark incompleto")
        return DownloadSample(
            mbps=round(8 * received / max(elapsed, 0.001) / 1_000_000, 3),
            ttfb_ms=round(ttfb, 1),
            bytes_received=received,
        )
    except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
        raise BenchmarkError("Trasferimento HTTPS non riuscito: " + type(exc).__name__) from exc
    finally:
        if response is not None:
            response.close()
        if tls is not None:
            tls.close()
        if raw is not None:
            raw.close()


def lte_connected(status: dict, plmn: dict) -> bool:
    """Registration per firmware; only 4G, not fallback 3G in AUTO mode."""
    return (isinstance(status, dict) and isinstance(plmn, dict)
            and str(status.get("ConnectionStatus")) == "901"
            and str(status.get("CurrentNetworkType")) in ("19", "101")
            and str(plmn.get("Rat")) == "7")


def _wait_lte(radio, cancel: threading.Event, seconds: float,
              *, sleeper=time.sleep, clock=time.monotonic) -> bool:
    deadline = clock() + seconds
    while clock() < deadline:
        if cancel.is_set():
            return False
        snapshot = radio.snapshot()
        if lte_connected(snapshot.get("monitoring_status"),
                         snapshot.get("plmn")):
            return True
        sleeper(2)
    return False


@dataclass(frozen=True)
class BandResult:
    band: int
    mask: str
    status: str
    med_mbps: float | None = None
    med_ttfb_ms: float | None = None
    completed_samples: int = 0
    error: str = ""

    def safe_dict(self):
        return asdict(self)


def run_band_benchmark(radio, bands: list[int], cancel: threading.Event,
                       progress: Callable[[str], None], *,
                       repeats: int = DEFAULT_REPEATS,
                       bytes_per_sample: int = DEFAULT_BYTES,
                       settle_seconds: float = 30.0,
                       route_checker=check_route,
                       resolver=resolve_endpoint,
                       downloader=https_download,
                       sleeper=time.sleep) -> list[BandResult]:
    """Explicit user-triggered benchmark, baseline always restored or fatal error.

    Caller must confirm traffic cost, WAN disruption and use a direct pocket
    gateway. The route is checked BEFORE the first LTE write and again before
    each download. No apparent winner is selected from failed/partial samples.
    """
    if not 1 <= repeats <= MAX_REPEATS or not 16_384 <= bytes_per_sample <= MAX_BYTES:
        raise ValueError("Budget benchmark non valido")
    if not bands or len(bands) != len(set(bands)) or len(bands) > 6:
        raise ValueError("Selezione bande non valida")
    total_budget = len(bands) * repeats * bytes_per_sample
    if total_budget > 80_000_000:
        raise ValueError("Limite traffico del benchmark superato")
    endpoint = resolver()
    route = route_checker(radio.host, endpoint)  # PRE-WRITE safety gate
    baseline = radio.config()
    mode_list = radio._read(radio.client.net, "net_mode_list")
    advertised = set(supported_bands(mode_list))
    if not advertised or not set(bands).issubset(advertised):
        raise BenchmarkError("Le bande richieste non risultano supportate dalle API")
    progress(f"Route verificata: {route.interface} via {route.gateway}; "
             f"limite download {total_budget / 1_000_000:.1f} MB")
    results: list[BandResult] = []
    changed = False
    rollback_error = None
    try:
        for band in bands:
            if cancel.is_set():
                break
            target = RadioConfig(mask_hex([band]), baseline.network_band,
                                 baseline.network_mode)
            progress(f"B{band}: applicazione maschera {target.lte_band}")
            try:
                if not radio.config().matches(target):
                    changed = True
                    radio._write_verified(target, cancel=cancel)
                if cancel.is_set():
                    break
                progress(f"B{band}: attesa riconnessione 4G")
                if not _wait_lte(radio, cancel, settle_seconds, sleeper=sleeper):
                    if cancel.is_set():
                        break
                    results.append(BandResult(band, target.lte_band,
                                              "Nessuna connessione LTE"))
                    continue
                samples = []
                for rep in range(repeats):
                    if cancel.is_set():
                        break
                    current_route = route_checker(radio.host, endpoint)
                    if current_route != route:
                        raise BenchmarkError("Route cambiata durante benchmark; test interrotto")
                    progress(f"B{band}: download prova {rep + 1}/{repeats}")
                    samples.append(downloader(route, bytes_requested=bytes_per_sample))
                if cancel.is_set():
                    break
                results.append(BandResult(
                    band, target.lte_band, "OK",
                    round(median(sample.mbps for sample in samples), 3),
                    round(median(sample.ttfb_ms for sample in samples), 1),
                    len(samples),
                ))
            except Exception as exc:
                if cancel.is_set():
                    break
                progress(f"B{band}: test fallito ({type(exc).__name__})")
                results.append(BandResult(band, target.lte_band, "Errore",
                                          error=str(exc)[:180]))
                # If route is no longer verifiable, further writes/tests are unsafe.
                try:
                    if route_checker(radio.host, endpoint) != route:
                        break
                except Exception:
                    break
    finally:
        progress("Ripristino della configurazione originale (non cancellabile)")
        try:
            if changed and not baseline.matches(radio.config()):
                radio._write_verified(baseline, retries=18)
            if not baseline.matches(radio.config()):
                raise BenchmarkError("Read-back baseline differente")
            progress("Baseline ripristinata e verificata")
        except Exception as exc:
            rollback_error = str(exc)
    if rollback_error:
        raise BenchmarkError(
            "ATTENZIONE: baseline NON ripristinata/verificata: " + rollback_error
            + ". Ripristinare manualmente prima di nuove prove."
        )
    return results


def ranking(results: list[BandResult]) -> list[BandResult]:
    """Rank only completed identical-budget, same-session samples by median down."""
    valid = [r for r in results if r.status == "OK" and r.med_mbps is not None
             and r.completed_samples > 0]
    if valid and len({r.completed_samples for r in valid}) != 1:
        return []
    return sorted(valid, key=lambda row: (-row.med_mbps, row.med_ttfb_ms or 1e6))
