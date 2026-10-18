"""Sensors for MakerLink units."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import MakerLinkConfigEntry
from .controller import STATUSES, MachineController, UnitController
from .entity import MakerLinkEntity, add_unit_entities


@dataclass(frozen=True, kw_only=True)
class MakerLinkSensorDescription(SensorEntityDescription):
    value_fn: Callable[[Any], Any]
    machine_only: bool = False


def _ts(value: float | None) -> datetime | None:
    return datetime.fromtimestamp(value, UTC) if value else None


def _display(unit: UnitController) -> str | None:
    return " | ".join(unit.display_lines) if unit.display_lines else None


SENSORS: tuple[MakerLinkSensorDescription, ...] = (
    MakerLinkSensorDescription(
        key="status",
        device_class=SensorDeviceClass.ENUM,
        options=STATUSES,
        value_fn=lambda u: u.status,
    ),
    MakerLinkSensorDescription(
        key="user", machine_only=True, value_fn=lambda u: u.last_user or None
    ),
    MakerLinkSensorDescription(
        key="session_start",
        machine_only=True,
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda u: _ts(u.session_start),
    ),
    MakerLinkSensorDescription(
        key="last_cost",
        machine_only=True,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="EUR",
        value_fn=lambda u: u.last_cost,
    ),
    MakerLinkSensorDescription(
        key="last_balance",
        machine_only=True,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="EUR",
        value_fn=lambda u: u.last_balance,
    ),
    MakerLinkSensorDescription(
        key="pending_bookings",
        machine_only=True,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda u: len(u.pending_stops),
    ),
    MakerLinkSensorDescription(
        key="display",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_display,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MakerLinkConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    def factory(unit: UnitController, subentry_id: str) -> Iterable[SensorEntity]:
        is_machine = isinstance(unit, MachineController)
        return [
            MakerLinkSensor(unit, subentry_id, desc)
            for desc in SENSORS
            if is_machine or not desc.machine_only
        ]

    add_unit_entities(entry, async_add_entities, factory)


class MakerLinkSensor(MakerLinkEntity, SensorEntity):
    entity_description: MakerLinkSensorDescription

    def __init__(
        self, unit: UnitController, subentry_id: str, desc: MakerLinkSensorDescription
    ) -> None:
        super().__init__(unit, subentry_id, desc.key)
        self.entity_description = desc

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.unit)
