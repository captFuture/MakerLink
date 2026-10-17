"""Sensor platform for MakerLink (Platzhalter)."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_HOST


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up MakerLink sensors."""
    async_add_entities([MakerLinkHostSensor(entry)])


class MakerLinkHostSensor(SensorEntity):
    """Zeigt den konfigurierten Host an."""

    _attr_has_entity_name = True
    _attr_name = "Host"

    def __init__(self, entry: ConfigEntry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_host"
        self._attr_native_value = entry.data[CONF_HOST]
