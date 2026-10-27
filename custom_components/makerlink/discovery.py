"""Finds MakerLink readers among the ESPHome devices of Home Assistant.

The firmware sets `esphome: project: name: makeraustria.makerlink_reader`; the ESPHome
integration shows that as manufacturer `makeraustria` and model `makerlink_reader`.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import CONF_READER_DEVICE, ESPHOME_PROJECT_NAME, SUBENTRY_UNIT
from .readers import classify_entities

ESPHOME_DOMAIN = "esphome"


def _is_reader(hass: HomeAssistant, device: dr.DeviceEntry) -> bool:
    on_esphome = any(
        (entry := hass.config_entries.async_get_entry(entry_id)) is not None
        and entry.domain == ESPHOME_DOMAIN
        for entry_id in device.config_entries
    )
    if not on_esphome:
        return False
    project = f"{device.manufacturer or ''}.{device.model or ''}".lower()
    return project.startswith(ESPHOME_PROJECT_NAME)


def device_entities(hass: HomeAssistant, device_id: str) -> list[tuple[str, str | None]]:
    """(entity_id, name) of all enabled entities of a device."""
    return [
        (entry.entity_id, entry.original_name or entry.name)
        for entry in er.async_entries_for_device(er.async_get(hass), device_id)
    ]


def detect(hass: HomeAssistant, device_id: str) -> dict[str, str]:
    return classify_entities(device_entities(hass, device_id))


def assigned_readers(entries: list[ConfigEntry]) -> set[str]:
    return {
        sub.data.get(CONF_READER_DEVICE)
        for entry in entries
        for sub in entry.subentries.values()
        if sub.subentry_type == SUBENTRY_UNIT
    }


def find_readers(hass: HomeAssistant, entries: list[ConfigEntry]) -> list[dict[str, Any]]:
    """Readers that do not belong to a unit yet."""
    assigned = assigned_readers(entries)
    readers = []
    for device in dr.async_get(hass).devices.values():
        if device.id in assigned or not _is_reader(hass, device):
            continue
        entities = device_entities(hass, device.id)
        detected = classify_entities(entities)
        readers.append(
            {
                "device_id": device.id,
                "name": device.name_by_user or device.name or device.id,
                "firmware": device.sw_version,
                "online": any(
                    (state := hass.states.get(entity_id)) is not None
                    and state.state != STATE_UNAVAILABLE
                    for entity_id, _ in entities
                ),
                "has_relay": "power_entity" in detected,
                "has_display": "display_line1" in detected,
            }
        )
    readers.sort(key=lambda r: r["name"].lower())
    return readers


def pending_esphome(hass: HomeAssistant) -> list[str]:
    """ESPHome devices that were found on the network but not confirmed yet."""
    names = []
    for flow in hass.config_entries.flow.async_progress_by_handler(ESPHOME_DOMAIN):
        placeholders = flow.get("context", {}).get("title_placeholders") or {}
        if name := placeholders.get("name"):
            names.append(name)
    return sorted(set(names))


def esphome_device_names(hass: HomeAssistant) -> set[str]:
    return {
        entry.data["device_name"]
        for entry in hass.config_entries.async_entries(ESPHOME_DOMAIN)
        if entry.data.get("device_name")
    }
