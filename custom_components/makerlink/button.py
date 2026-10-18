"""Buttons for MakerLink units."""

from __future__ import annotations

from collections.abc import Iterable

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MakerLinkConfigEntry
from .controller import DoorController, MachineController, UnitController
from .entity import MakerLinkEntity, add_unit_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MakerLinkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    def factory(unit: UnitController, subentry_id: str) -> Iterable[ButtonEntity]:
        if isinstance(unit, MachineController):
            return [StopSessionButton(unit, subentry_id)]
        if isinstance(unit, DoorController):
            return [OpenDoorButton(unit, subentry_id)]
        return []

    add_unit_entities(entry, async_add_entities, factory)


class StopSessionButton(MakerLinkEntity, ButtonEntity):
    """Stop the running session (with billing), or end cooldown/admin mode."""

    def __init__(self, unit: MachineController, subentry_id: str) -> None:
        super().__init__(unit, subentry_id, "stop_session")

    async def async_press(self) -> None:
        await self.unit.stop_session("manual")


class OpenDoorButton(MakerLinkEntity, ButtonEntity):
    """Pulse the door opener without a card."""

    def __init__(self, unit: DoorController, subentry_id: str) -> None:
        super().__init__(unit, subentry_id, "open_door")

    async def async_press(self) -> None:
        await self.unit.open_door()
