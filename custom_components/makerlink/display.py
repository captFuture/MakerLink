"""Display rendering for 16x2 reader displays (no Home Assistant imports).

Port of the LCD lambda in docs/legacy/maker-reader-logic.yaml. The status
characters (WiFi/relay) are left to the reader firmware.
"""

from __future__ import annotations

from dataclasses import dataclass

WIDTH = 16

_TRANSLIT = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss", "€": "EUR"}
)


def fit(text: str) -> str:
    """Make text safe for a HD44780 display: ASCII, max 16 chars."""
    text = (text or "").translate(_TRANSLIT)
    text = text.encode("ascii", "replace").decode("ascii")
    return text[:WIDTH]


@dataclass(slots=True)
class View:
    """Everything the display depends on."""

    kind: str = "machine"
    out_of_order: bool = False
    admin: bool = False
    busy: str = ""
    message: tuple[str, str] | None = None
    shutdown_counter: int = 0
    user_name: str = ""
    session_active: bool = False
    stop_screen: int = 0
    stop_title: str = "Schaltet aus"
    balance: float | None = None
    interlock_open: bool = False


def render(v: View) -> tuple[str, str]:
    """Return the two display lines for the given state (priority as in legacy)."""
    if v.out_of_order:
        lines = ("AUSSER BETRIEB", "!! WARTUNG !!")
    elif v.admin:
        lines = ("ADMIN MODE", "MakerAdmin")
    elif v.busy:
        lines = ("BITTE WARTEN", v.busy)
    elif v.message:
        lines = v.message
    elif v.shutdown_counter > 0:
        lines = ("STOPPT:", f"{fit(v.user_name)[:10]:<10}{v.shutdown_counter:>5}s"[-WIDTH:])
    elif v.session_active:
        lines = ("EIN:", v.user_name)
    elif v.stop_screen > 0:
        bal = f"Gut: {v.balance:.2f} EUR" if v.balance is not None else ""
        lines = (v.stop_title, bal)
    elif v.interlock_open:
        lines = ("TUER OFFEN", "Bitte schliessen")
    else:
        lines = ("-MakerAustria-", "Karte bitte")
    return fit(lines[0]), fit(lines[1])
