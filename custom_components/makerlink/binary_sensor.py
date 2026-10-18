"""Binary sensors for MakerLink units."""

from __future__ import annotations

from collections.abc import Iterable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MakerLinkConfigEntry
from .controller import MachineController, UnitController
from .entity import MakerLinkEntity, add_unit_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MakerLinkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    def factory(unit: UnitController, subentry_id: str) -> Iterable[BinarySensorEntity]:
        if not isinstance(unit, MachineController):
            return []
        entities: list[BinarySensorEntity] = [SessionActiveSensor(unit, subentry_id)]
        if unit.hw.interlocks:
            entities.append(InterlockSensor(unit, subentry_id))
        return entities

    add_unit_entities(entry, async_add_entities, factory)


class SessionActiveSensor(MakerLinkEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, unit: MachineController, subentry_id: str) -> None:
        super().__init__(unit, subentry_id, "session_active")

    @property
    def is_on(self) -> bool:
        return self.unit.session_active


class InterlockSensor(MakerLinkEntity, BinarySensorEntity):
    """On = at least one interlock switch is open (machine blocked)."""

    _attr_device_class = BinarySensorDeviceClass.OPENING

    def __init__(self, unit: MachineController, subentry_id: str) -> None:
        super().__init__(unit, subentry_id, "interlock")

    @property
    def is_on(self) -> bool:
        return not self.unit.hw.interlock_closed()
