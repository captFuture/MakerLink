"""Offline whitelist: cards that may be accepted while MARS is unreachable (no HA imports).

The list holds the card UIDs (MARS format) of all active Unlimited members, fetched
with `machineswitch.php?action=whitelist`. It is only consulted when the backend is
down; a reachable backend always decides itself.
"""

from __future__ import annotations

from typing import Any


class Whitelist:
    """Card UIDs plus the time of the last successful sync."""

    def __init__(self) -> None:
        self.cards: frozenset[str] = frozenset()
        self.synced_at: float | None = None
        self.last_error: str | None = None

    def __contains__(self, rfid: str) -> bool:
        return rfid in self.cards

    def __len__(self) -> int:
        return len(self.cards)

    @property
    def loaded(self) -> bool:
        return self.synced_at is not None

    def update(self, cards: list[str], now: float) -> None:
        self.cards = frozenset(c.strip().lower() for c in cards if isinstance(c, str) and c.strip())
        self.synced_at = now
        self.last_error = None

    def as_store(self) -> dict[str, Any]:
        return {"cards": sorted(self.cards), "synced_at": self.synced_at}

    def restore(self, data: dict[str, Any] | None) -> None:
        if not data:
            return
        self.cards = frozenset(data.get("cards") or [])
        self.synced_at = data.get("synced_at")

    def info(self) -> dict[str, Any]:
        return {"count": len(self.cards), "synced_at": self.synced_at, "error": self.last_error}
