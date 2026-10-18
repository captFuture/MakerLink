"""Diagnostics for MakerLink."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import MakerLinkConfigEntry
from .const import CONF_API_KEY

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MakerLinkConfigEntry
) -> dict[str, Any]:
    """Return hub config (redacted) and the state of every unit."""
    hub = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "units": {
            sub_id: {
                "title": entry.subentries[sub_id].title,
                "config": dict(entry.subentries[sub_id].data),
                "status": unit.status,
                "display": unit.display_lines,
                "state": unit.as_store(),
            }
            for sub_id, unit in hub.units.items()
        },
    }
