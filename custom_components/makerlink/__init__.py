"""The MakerLink integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .hub import MakerLinkHub

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type MakerLinkConfigEntry = ConfigEntry[MakerLinkHub]


async def async_setup_entry(hass: HomeAssistant, entry: MakerLinkConfigEntry) -> bool:
    """Set up MakerLink from a config entry."""
    hub = MakerLinkHub(hass, entry)
    await hub.async_setup()
    entry.runtime_data = hub
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await hub.async_start()
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MakerLinkConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_unload()
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: MakerLinkConfigEntry) -> None:
    """Reload when units (subentries) are added, changed or removed."""
    await hass.config_entries.async_reload(entry.entry_id)
