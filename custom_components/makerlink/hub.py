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
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
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
    DOMAIN,
    EVENT_READER_TAG,
    EVENT_TAG_SCANNED,
    KIND_DOOR,
    SIGNAL_UPDATE,
    STORAGE_KEY,
    STORAGE_VERSION,
    SUBENTRY_UNIT,
)
from .controller import DoorController, MachineController, UnitController

_LOGGER = logging.getLogger(__name__)

TICK = timedelta(seconds=1)
# Minimum seconds between two display resends of one unit (no loop if a reader rejects a text).
DISPLAY_RESEND_MIN = 2.0


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
        self._hardware: dict[str, HassHardware] = {}
        self._reader_entities: dict[str, list[str]] = {}
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
                saved = stored.get(subentry.subentry_id) or {}
                # Switched between machine and door: the old runtime settings do not apply.
                if saved.get("kind", subentry.data[CONF_KIND]) != subentry.data[CONF_KIND]:
                    saved = {}
                self._setup_unit(subentry, saved)

        bus = self.hass.bus
        self._unsubs.append(bus.async_listen(EVENT_READER_TAG, self._handle_reader_tag))
        self._unsubs.append(bus.async_listen(EVENT_TAG_SCANNED, self._handle_tag_scanned))
        self._unsubs.append(async_track_time_interval(self.hass, self._handle_tick, TICK))

    async def async_start(self) -> None:
        """Reconcile controllers with current entity states (after platforms are set up)."""
        for unit in self.units.values():
            await unit.async_start()
        self._signal_update()

    async def async_unload(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        await self._store.async_save(self._data_to_save())
        self.units.clear()
        self._signal_update()

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

        sub_id = subentry.subentry_id
        self.units[sub_id] = unit
        self._hardware[sub_id] = hardware
        self._readers[data[CONF_READER_DEVICE]] = unit
        self._reader_entities[sub_id] = [
            e.entity_id
            for e in er.async_entries_for_device(
                er.async_get(self.hass), data[CONF_READER_DEVICE], include_disabled_entities=False
            )
        ]
        self._unsubs.append(unit.add_listener(self._signal_update))

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
        display_entities = [e for e in hardware.lines if e]
        if display_entities:
            last_resend = 0.0

            @callback
            def _display_changed(event: Event[EventStateChangedData]) -> None:
                # After a reboot/reconnect the reader shows its start text ("Verbinde...")
                # while our desired lines are unchanged, so _refresh() would never resend.
                nonlocal last_resend
                new_state = event.data["new_state"]
                desired = unit.display_lines
                if (
                    desired is None
                    or new_state is None
                    or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)
                ):
                    return
                index = hardware.lines.index(event.data["entity_id"])
                now = self.hass.loop.time()
                if new_state.state != desired[index] and now - last_resend >= DISPLAY_RESEND_MIN:
                    last_resend = now
                    self.hass.async_create_task(unit.resend_display())

            self._unsubs.append(
                async_track_state_change_event(self.hass, display_entities, _display_changed)
            )
        # Panel: power/interlock/reader availability are shown live as well.
        watched = {hardware.power_entity, *hardware.interlocks, *self._reader_entities[sub_id]}
        self._unsubs.append(
            async_track_state_change_event(self.hass, list(watched), self._handle_watched_state)
        )

    # ----- panel -------------------------------------------------------------------

    @callback
    def _signal_update(self) -> None:
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    @callback
    def _handle_watched_state(self, _event: Event[EventStateChangedData]) -> None:
        self._signal_update()

    def _reader_online(self, sub_id: str) -> bool | None:
        """True if any entity of the reader device is available (None: no entities)."""
        entity_ids = self._reader_entities.get(sub_id) or []
        if not entity_ids:
            return None
        return any(
            (state := self.hass.states.get(e)) is not None and state.state != STATE_UNAVAILABLE
            for e in entity_ids
        )

    def unit_snapshot(self, sub_id: str) -> dict[str, Any]:
        """Everything the sidebar panel shows for one unit."""
        unit = self.units[sub_id]
        hardware = self._hardware[sub_id]
        subentry = self.entry.subentries[sub_id]
        device = dr.async_get(self.hass).async_get_device(identifiers={(DOMAIN, sub_id)})
        interlocks = []
        for entity_id in hardware.interlocks:
            state = self.hass.states.get(entity_id)
            interlocks.append(
                {
                    "entity_id": entity_id,
                    "name": state.name if state else entity_id,
                    "closed": state is not None and state.state == STATE_OFF,
                }
            )
        snapshot: dict[str, Any] = {
            "id": sub_id,
            "entry_id": self.entry.entry_id,
            "name": unit.name,
            "kind": unit.kind,
            "unit_id": unit.unit_id,
            "status": unit.status,
            "display": list(unit.display_lines or ("", "")),
            "out_of_order": unit.out_of_order,
            "settings": dict(unit.settings),
            "power": hardware.power_state(),
            "power_entity": hardware.power_entity,
            "interlocks": interlocks,
            "reader_online": self._reader_online(sub_id),
            "reader_device_id": subentry.data[CONF_READER_DEVICE],
            "device_id": device.id if device else None,
        }
        if isinstance(unit, MachineController):
            snapshot.update(
                {
                    "machine_type": unit.machine_type,
                    "admin": unit.admin,
                    "session_active": unit.session_active,
                    "session_start": unit.session_start,
                    "user": unit.last_user or None,
                    "shutdown_remaining": unit.shutdown_counter,
                    "last_cost": unit.last_cost,
                    "last_balance": unit.last_balance,
                    "pending_bookings": len(unit.pending_stops),
                }
            )
        elif isinstance(unit, DoorController):
            snapshot["last_allowed"] = unit.last_allowed
        return snapshot

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
        return {sub_id: {**unit.as_store(), "kind": unit.kind} for sub_id, unit in self.units.items()}
