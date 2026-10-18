"""MARS data formats (no Home Assistant imports)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

_SEPARATORS = re.compile(r"[-:\s]+")
_HEX = re.compile(r"^[0-9a-fA-F]+$")


class MarsError(Exception):
    """Talking to the MARS backend failed."""

    display = "Server Fehler"
    # Permanent errors (bad request) must not be retried.
    permanent = False


class MarsConnectionError(MarsError):
    """Backend not reachable or timed out."""

    display = "Server offline"


class MarsAuthError(MarsError):
    """Backend rejected the API key (HTTP 401)."""

    display = "API-Key falsch"


class MarsHttpError(MarsError):
    """Backend answered with an unexpected HTTP status."""

    def __init__(self, status: int, msg: str = "") -> None:
        super().__init__(f"HTTP {status}: {msg}")
        self.status = status
        self.display = f"HTTP ERR {status}"
        self.permanent = 400 <= status < 500


def uid_to_mars(raw: str) -> str | None:
    """Convert a reader UID into the MARS key format.

    Port of the RC522 lambda in the legacy firmware:
    "F4-96-D2-03" -> "0xf4 0x96 0xd2 0x3" (lowercase, one leading zero
    per byte stripped, space separated; URL encoding is done by the HTTP client).
    Accepts "-", ":" or whitespace separators, or a plain even-length hex string.
    Returns None if the input is not a hex UID (e.g. a HA tag UUID).
    """
    raw = raw.strip()
    if not raw:
        return None
    if _SEPARATORS.search(raw):
        tokens = [t for t in _SEPARATORS.split(raw) if t]
    else:
        if len(raw) % 2:
            return None
        tokens = [raw[i : i + 2] for i in range(0, len(raw), 2)]
    if not tokens or not all(_HEX.match(t) for t in tokens):
        return None
    out = []
    for token in tokens:
        if len(token) > 1 and token[0] == "0":
            token = token[1:]
        out.append("0x" + token.lower())
    return " ".join(out)


@dataclass(slots=True)
class MarsResult:
    """Parsed response of action=start / action=stop."""

    ok: bool
    key: int | None = None
    name: str | None = None
    msg: str = ""
    cost: float | None = None
    balance: float | None = None
    duration_s: int | None = None

    @classmethod
    def from_json(cls, data: Any) -> MarsResult:
        if not isinstance(data, dict):
            return cls(ok=False, msg="Ungueltige Antwort")
        key = data.get("key")
        try:
            key = int(key) if key not in (None, "", "null") else None
        except (TypeError, ValueError):
            key = None
        return cls(
            ok=bool(data.get("ok")),
            key=key,
            name=data.get("name") or None,
            msg=str(data.get("msg") or ""),
            cost=_float(data.get("cost")),
            balance=_float(data.get("balance")),
            duration_s=_int(data.get("duration_s")),
        )


@dataclass(slots=True)
class DoorResult:
    """Parsed response of action=doorLockCheck (["True", reason, plans])."""

    allowed: bool
    reason: str = ""
    plans: str = ""

    @classmethod
    def from_json(cls, data: Any) -> DoorResult:
        if isinstance(data, list) and data:
            return cls(
                allowed=str(data[0]) == "True",
                reason=str(data[1]) if len(data) > 1 else "",
                plans=str(data[2]) if len(data) > 2 else "",
            )
        if isinstance(data, dict):
            return cls(allowed=False, reason=str(data.get("msg") or ""))
        return cls(allowed=False, reason="Ungueltige Antwort")


def parse_body(body: str) -> Any:
    """Parse a JSON body, returning None on garbage."""
    try:
        return json.loads(body)
    except (ValueError, TypeError):
        return None


def _float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
