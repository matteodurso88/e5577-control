"""Huawei SMS and mobile-data presentation models, separate from radio controls.

SMS bodies and phone numbers are private: never put Message objects into
periodic snapshots, log entries or diagnostic JSON exports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class UnsupportedFeature(RuntimeError):
    pass


def mobile_data_state(payload: Any) -> bool | None:
    """Read Huawei dialup/mobile-dataswitch; never infer from ConnectionStatus."""
    if not isinstance(payload, dict) or "__error__" in payload:
        return None
    for name in ("dataswitch", "DataSwitch"):
        value = payload.get(name)
        if isinstance(value, (int, str)) and str(value).strip() in ("0", "1"):
            return str(value).strip() == "1"
    return None


@dataclass(frozen=True)
class SmsSummary:
    inbox: int | None
    unread: int | None
    error: str = ""


@dataclass(frozen=True)
class SmsMessage:
    index: str
    phone: str
    date: str
    content: str
    unread: bool


def _number(value: Any) -> int | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        number = int(str(value))
        return number if 0 <= number <= 1_000_000 else None
    except (ValueError, TypeError):
        return None


def sms_summary(payload: Any) -> SmsSummary:
    if not isinstance(payload, dict):
        return SmsSummary(None, None, "Formato contatore SMS non valido")
    if "__error__" in payload:
        return SmsSummary(None, None, "Contatore SMS non disponibile")
    # HiLink names differ by firmware. Use only named inbox counters.
    return SmsSummary(
        inbox=_number(payload.get("LocalInbox")),
        unread=_number(payload.get("LocalUnread")),
    )


def sms_messages(payload: Any) -> list[SmsMessage]:
    if not isinstance(payload, dict) or "__error__" in payload:
        raise UnsupportedFeature("Elenco SMS non disponibile sul dispositivo")
    messages = payload.get("Messages")
    raw = messages.get("Message", []) if isinstance(messages, dict) else []
    if raw is None:
        raw = []
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        raise UnsupportedFeature("Formato messaggi non riconosciuto")
    result = []
    for message in raw[:50]:
        if not isinstance(message, dict):
            continue
        # No HTML or rich-text rendering anywhere in the GUI.
        result.append(SmsMessage(
            index=str(message.get("Index") or ""),
            phone=str(message.get("Phone") or "Sconosciuto")[:128],
            date=str(message.get("Date") or "")[:80],
            content=str(message.get("Content") or "")[:10_000],
            unread=str(message.get("Smstat", "")) == "0",
        ))
    return result
