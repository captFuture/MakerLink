"""Number settings for MakerLink units."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MakerLinkConfigEntry
from .controller import DoorController, MachineController, UnitController
from .entity import MakerLinkEntity, add_unit_entities


@dataclass(frozen=True, kw_only=True)
class MakerLinkNumberDescription(NumberEntityDescription):
    kind: type[UnitController]


NUMBERS: tuple[MakerLinkNumberDescription, ...] = (
    MakerLinkNumberDescription(
        key="min_balance",
        kind=MachineController,
        native_min_value=-100,
        native_max_value=1000,
        native_step=0.5,
        native_unit_of_measurement="EUR",
        mode=NumberMode.BOX,
    ),
    MakerLinkNumberDescription(
        key="shutdown_time",
        kind=MachineController,
        native_min_value=0,
        native_max_value=3600,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        mode=NumberMode.BOX,
    ),
    MakerLinkNumberDescription(
        key="pulse_time",
        kind=DoorController,
        native_min_value=0.5,
        native_max_value=30,
        native_step=0.5,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        mode=NumberMode.BOX,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MakerLinkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    def factory(unit: UnitController, subentry_id: str) -> Iterable[NumberEntity]:
        return [
            MakerLinkNumber(unit, subentry_id, desc)
            for desc in NUMBERS
            if isinstance(unit, desc.kind)
        ]

    add_unit_entities(entry, async_add_entities, factory)


class MakerLinkNumber(MakerLinkEntity, NumberEntity):
    entity_description: MakerLinkNumberDescription
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, unit: UnitController, subentry_id: str, desc: MakerLinkNumberDescription
    ) -> None:
        super().__init__(unit, subentry_id, desc.key)
        self.entity_description = desc

    @property
    def native_value(self) -> float:
        return float(self.unit.settings[self.entity_description.key])

    async def async_set_native_value(self, value: float) -> None:
        await self.unit.set_setting(self.entity_description.key, value)
