"""Home Assistant glue: wires controllers to entities, events and storage."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store

from .api import MarsApiClient
from .const import (
    CONF_API_KEY,
    CONF_API_URL,
    CONF_DISPLAY_LINE1,
    CONF_DISPLAY_LINE2,
    CONF_INTERLOCK_1,
    CONF_INTERLOCK_2,
    CONF_KIND,
    CONF_MACHINE_TYPE,
    CONF_MIN_BALANCE,
    CONF_POWER_ENTITY,
    CONF_PULSE_TIME,
    CONF_READER_DEVICE,
    CONF_SHUTDOWN_TIME,
    CONF_UNIT_ID,
    CONF_VERIFY_SSL,
    DEFAULT_MIN_BALANCE,
    DEFAULT_PULSE_TIME,
    DEFAULT_SHUTDOWN_TIME,
    DEFAULT_SHUTDOWN_TIME_BY_TYPE,
    EVENT_READER_TAG,
    EVENT_TAG_SCANNED,
    KIND_DOOR,
    STORAGE_KEY,
    STORAGE_VERSION,
    SUBENTRY_UNIT,
)
from .controller import DoorController, MachineController, UnitController

_LOGGER = logging.getLogger(__name__)

TICK = timedelta(seconds=1)


class HassHardware:
    """Reader/actuator access through Home Assistant entities."""

    def __init__(self, hass: HomeAssistant, data: Mapping[str, Any]) -> None:
        self.hass = hass
        self.power_entity: str = data[CONF_POWER_ENTITY]
        self.lines: list[str | None] = [data.get(CONF_DISPLAY_LINE1), data.get(CONF_DISPLAY_LINE2)]
        self.interlocks: list[str] = [
            e for e in (data.get(CONF_INTERLOCK_1), data.get(CONF_INTERLOCK_2)) if e
        ]

    def power_state(self) -> bool | None:
        state = self.hass.states.get(self.power_entity)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        return state.state == STATE_ON

    async def set_power(self, on: bool) -> None:
        try:
            await self.hass.services.async_call(
                "homeassistant",
                "turn_on" if on else "turn_off",
                {ATTR_ENTITY_ID: self.power_entity},
                blocking=True,
            )
        except HomeAssistantError as err:
            _LOGGER.error("Switching %s failed: %s", self.power_entity, err)

    def interlock_closed(self) -> bool:
        # binary_sensor convention (device_class door/opening): off = closed.
        # Unknown/unavailable counts as open (fail safe).
        for entity_id in self.interlocks:
            state = self.hass.states.get(entity_id)
            if state is None or state.state != STATE_OFF:
                return False
        return True

    async def show(self, line1: str, line2: str) -> None:
        for entity_id, value in zip(self.lines, (line1, line2), strict=True):
            if not entity_id:
                continue
            state = self.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE or state.state == value:
                continue
            await self.hass.services.async_call(
                "text", "set_value", {ATTR_ENTITY_ID: entity_id, "value": value}, blocking=True
            )


class MakerLinkHub:
    """Runtime data of the MakerLink config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.api = MarsApiClient(
            async_get_clientsession(hass, verify_ssl=entry.data.get(CONF_VERIFY_SSL, True)),
            entry.data[CONF_API_URL],
            entry.data[CONF_API_KEY],
            entry.data.get(CONF_VERIFY_SSL, True),
        )
        self.units: dict[str, UnitController] = {}
        self._readers: dict[str, UnitController] = {}
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY}.{entry.entry_id}"
        )
        self._unsubs: list[Callable[[], None]] = []
        self._ticking: set[str] = set()

    async def async_setup(self) -> None:
        stored = await self._store.async_load() or {}
        for subentry in self.entry.subentries.values():
            if subentry.subentry_type == SUBENTRY_UNIT:
                self._setup_unit(subentry, stored.get(subentry.subentry_id) or {})

        bus = self.hass.bus
        self._unsubs.append(bus.async_listen(EVENT_READER_TAG, self._handle_reader_tag))
        self._unsubs.append(bus.async_listen(EVENT_TAG_SCANNED, self._handle_tag_scanned))
        self._unsubs.append(async_track_time_interval(self.hass, self._handle_tick, TICK))

    async def async_start(self) -> None:
        """Reconcile controllers with current entity states (after platforms are set up)."""
        for unit in self.units.values():
            await unit.async_start()

    async def async_unload(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        await self._store.async_save(self._data_to_save())

    # ----- units -------------------------------------------------------------------

    def _setup_unit(self, subentry: ConfigSubentry, stored: dict[str, Any]) -> None:
        data = subentry.data
        hardware = HassHardware(self.hass, data)
        common: dict[str, Any] = {
            "name": subentry.title,
            "unit_id": int(data[CONF_UNIT_ID]),
            "api": self.api,
            "hardware": hardware,
            "fire_event": self._fire_event,
            "save": self._schedule_save,
        }
        unit: UnitController
        if data[CONF_KIND] == KIND_DOOR:
            unit = DoorController(
                settings={"pulse_time": data.get(CONF_PULSE_TIME, DEFAULT_PULSE_TIME)}, **common
            )
            unit.settings.update(stored.get("settings") or {})
        else:
            unit = MachineController(
                machine_type=data[CONF_MACHINE_TYPE],
                settings={
                    "min_balance": data.get(CONF_MIN_BALANCE, DEFAULT_MIN_BALANCE),
                    "shutdown_time": data.get(
                        CONF_SHUTDOWN_TIME,
                        DEFAULT_SHUTDOWN_TIME_BY_TYPE.get(
                            data[CONF_MACHINE_TYPE], DEFAULT_SHUTDOWN_TIME
                        ),
                    ),
                },
                **common,
            )
            unit.restore(stored)

        self.units[subentry.subentry_id] = unit
        self._readers[data[CONF_READER_DEVICE]] = unit

        @callback
        def _power_changed(event: Event[EventStateChangedData]) -> None:
            self.hass.async_create_task(unit.on_power_changed(hardware.power_state()))

        @callback
        def _interlock_changed(event: Event[EventStateChangedData]) -> None:
            self.hass.async_create_task(unit.on_interlock_changed())

        if unit.kind != KIND_DOOR:
            self._unsubs.append(
                async_track_state_change_event(self.hass, hardware.power_entity, _power_changed)
            )
        if hardware.interlocks:
            self._unsubs.append(
                async_track_state_change_event(self.hass, hardware.interlocks, _interlock_changed)
            )

    # ----- events ------------------------------------------------------------------

    @callback
    def _handle_reader_tag(self, event: Event) -> None:
        self._dispatch_card(event.data.get("device_id"), event.data.get("uid"))

    @callback
    def _handle_tag_scanned(self, event: Event) -> None:
        self._dispatch_card(event.data.get("device_id"), event.data.get("tag_id"))

    @callback
    def _dispatch_card(self, device_id: str | None, uid: Any) -> None:
        if not device_id or not isinstance(uid, str):
            return
        if unit := self._readers.get(device_id):
            self.hass.async_create_task(unit.on_card(uid))

    async def _handle_tick(self, _now: Any) -> None:
        for sub_id, unit in self.units.items():
            if sub_id in self._ticking:
                continue  # previous tick still busy (e.g. slow backend)
            self._ticking.add(sub_id)
            self.hass.async_create_task(self._tick_unit(sub_id, unit))

    async def _tick_unit(self, sub_id: str, unit: UnitController) -> None:
        try:
            await unit.tick()
        except Exception:
            _LOGGER.exception("%s: tick failed", unit.name)
        finally:
            self._ticking.discard(sub_id)

    @callback
    def _fire_event(self, event_type: str, data: dict[str, Any]) -> None:
        self.hass.bus.async_fire(event_type, data)

    # ----- storage -----------------------------------------------------------------

    @callback
    def _schedule_save(self) -> None:
        self._store.async_delay_save(self._data_to_save, 1)

    def _data_to_save(self) -> dict[str, Any]:
        return {sub_id: unit.as_store() for sub_id, unit in self.units.items()}
