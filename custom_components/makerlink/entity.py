"""Base entity for MakerLink units."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, KIND_DOOR
from .controller import UnitController


class MakerLinkEntity(Entity):
    """An entity belonging to one unit (one device per subentry)."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, unit: UnitController, subentry_id: str, key: str) -> None:
        self.unit = unit
        self._attr_translation_key = key
        self._attr_unique_id = f"{subentry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, subentry_id)},
            name=unit.name,
            manufacturer="MakerAustria",
            model="MakerLink Tür" if unit.kind == KIND_DOOR else "MakerLink Maschine",
            serial_number=str(unit.unit_id),
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.unit.add_listener(self.async_write_ha_state))


def add_unit_entities(
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    factory: Callable[[UnitController, str], Iterable[Entity]],
) -> None:
    """Create entities per unit and attach them to the unit's subentry."""
    for subentry_id, unit in entry.runtime_data.units.items():
        if entities := list(factory(unit, subentry_id)):
            async_add_entities(entities, config_subentry_id=subentry_id)
