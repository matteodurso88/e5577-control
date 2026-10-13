"""Friendly Italian UI text only; radio data and protocol stay untouched."""

from __future__ import annotations

import re
from typing import Any


def friendly_connection(text: str) -> str:
    if text.startswith("Connessa (secondo firmware)"):
        return "Connessa"
    if text == "Disconnessa":
        return "Non connessa"
    if text == "Non disponibile":
        return "Stato non disponibile"
    return text


def friendly_signal(text: str) -> str:
    match = re.fullmatch(r"(\d+)/(\d+) tacche \(indicatore firmware\)", text)
    if match:
        return f"{match.group(1)} su {match.group(2)} tacche"
    if text == "Non disponibile":
        return "Non disponibile"
    return text


def friendly_rf(text: str) -> str:
    if "indisponibili" in text.lower():
        return "Non fornite dal dispositivo"
    if "disponibili" in text.lower():
        return "Disponibili"
    return text


def friendly_route(ok: bool, message: str) -> str:
    if ok:
        return "Il computer usa la connessione del pocket. Puoi procedere al confronto."
    if "Route NON attraverso il pocket" in message:
        return (
            "Il computer naviga tramite un'altra rete. Per confrontare le bande, "
            "collegalo direttamente al Wi-Fi o USB del pocket e riprova."
        )
    if "Routing verificabile solo su Linux" in message:
        return "Il controllo automatico della connessione è disponibile soltanto su Linux."
    return "Non è possibile verificare l'uscita Internet: " + message


def friendly_benchmark_result(result: Any) -> str:
    if not result:
        return "Nessun risultato misurabile. Verifica la connessione del pocket."
    return (
        f"B{result.band} è stata la più veloce in questa prova: "
        f"{result.med_mbps:.1f} Mbps in download, "
        f"tempo di risposta {result.med_ttfb_ms:.0f} ms. "
        "Il risultato può cambiare con l'orario e il traffico della rete."
    )


def friendly_band_status(status: str) -> str:
    return {
        "OK": "Completata",
        "Errore": "Non riuscita",
        "Nessuna connessione LTE": "Senza connessione 4G",
        "Nessuna misura": "Dati non disponibili",
    }.get(status, status)


def friendly_changes(changes: str) -> str:
    if not changes:
        return "Nessuna variazione"
    if changes == "Inizio osservazione":
        return "Inizio registrazione"
    names = {
        "connection": "Connessione",
        "network": "Tipo di rete",
        "sim": "SIM",
        "operator": "Operatore",
        "bars": "Segnale",
        "rf": "Misure avanzate",
    }
    return ", ".join(names.get(part.strip(), part.strip())
                     for part in changes.split(",") if part.strip())


def friendly_error(message: str) -> str:
    if "108006" in message or "Username and Password wrong" in message:
        return "Password o nome utente non corretti. Riprova."
    if "ROLLBACK NON" in message or "baseline NON ripristinata" in message:
        return ("ATTENZIONE: il ripristino automatico non è stato verificato. "
                "Controlla subito le impostazioni originali del dispositivo.")
    if "100002" in message and "No support" in message:
        return "Questa funzione non è supportata dal firmware del pocket."
    return message
