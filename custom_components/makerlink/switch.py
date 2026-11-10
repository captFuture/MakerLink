"""Switches for MakerLink units."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MakerLinkConfigEntry
from .const import SETTING_OFFLINE
from .controller import MachineController, UnitController
from .entity import MakerLinkEntity, add_unit_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MakerLinkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    def factory(unit: UnitController, subentry_id: str) -> Iterable[SwitchEntity]:
        entities: list[SwitchEntity] = [
            OutOfOrderSwitch(unit, subentry_id),
            OfflineAllowedSwitch(unit, subentry_id),
        ]
        if isinstance(unit, MachineController):
            entities.append(AdminSwitch(unit, subentry_id))
        return entities

    add_unit_entities(entry, async_add_entities, factory)


class OutOfOrderSwitch(MakerLinkEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, unit: UnitController, subentry_id: str) -> None:
        super().__init__(unit, subentry_id, "out_of_order")

    @property
    def is_on(self) -> bool:
        return self.unit.out_of_order

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.unit.set_setting("out_of_order", True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.unit.set_setting("out_of_order", False)


class OfflineAllowedSwitch(MakerLinkEntity, SwitchEntity):
    """Accept whitelisted (Unlimited) cards while the MARS backend is down."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, unit: UnitController, subentry_id: str) -> None:
        super().__init__(unit, subentry_id, SETTING_OFFLINE)

    @property
    def is_on(self) -> bool:
        return self.unit.offline_allowed

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.unit.set_setting(SETTING_OFFLINE, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.unit.set_setting(SETTING_OFFLINE, False)


class AdminSwitch(MakerLinkEntity, SwitchEntity):
    """Maintenance mode: power on without a card/session."""

    unit: MachineController

    def __init__(self, unit: MachineController, subentry_id: str) -> None:
        super().__init__(unit, subentry_id, "admin")

    @property
    def is_on(self) -> bool:
        return self.unit.admin

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.unit.set_admin(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.unit.set_admin(False)
