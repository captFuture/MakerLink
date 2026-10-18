"""Select settings for MakerLink units."""

from __future__ import annotations

from collections.abc import Iterable

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MakerLinkConfigEntry
from .const import MACHINE_TYPES
from .controller import MachineController, UnitController
from .entity import MakerLinkEntity, add_unit_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MakerLinkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    def factory(unit: UnitController, subentry_id: str) -> Iterable[SelectEntity]:
        if isinstance(unit, MachineController):
            return [MachineTypeSelect(unit, subentry_id)]
        return []

    add_unit_entities(entry, async_add_entities, factory)


class MachineTypeSelect(MakerLinkEntity, SelectEntity):
    """Billing type sent to the backend (machine|laser|3dprint|dtf|kiln)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = MACHINE_TYPES

    def __init__(self, unit: MachineController, subentry_id: str) -> None:
        super().__init__(unit, subentry_id, "machine_type")

    @property
    def current_option(self) -> str:
        return self.unit.settings["machine_type"]

    async def async_select_option(self, option: str) -> None:
        await self.unit.set_setting("machine_type", option)
