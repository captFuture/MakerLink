"""WebSocket API for the MakerLink sidebar panel.

makerlink/units      -> {"units": [...], "readers": [...], ...}  one-shot snapshot
makerlink/subscribe  -> event messages with the same snapshot     on every change
makerlink/action     -> run an action on one unit (stop_session, open_door,
                        out_of_order, admin)

Onboarding (admin only):
makerlink/options     -> hardware list, switch entities, suggested device name
makerlink/reader_yaml -> device YAML for /config/esphome/
makerlink/identify    -> show a marker text on a reader's display for 10 s
makerlink/unit_add / unit_update / unit_remove -> manage machines and doors (subentries)
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from types import MappingProxyType
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry, ConfigEntryState, ConfigSubentry
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_call_later

from . import discovery
from .config_flow import POWER_DOMAINS, _unit_unique_id
from .const import (
    CONF_DISPLAY_LINE1,
    CONF_DISPLAY_LINE2,
    CONF_KIND,
    CONF_READER_DEVICE,
    CONF_UNIT_ID,
    DOMAIN,
    KINDS,
    MACHINE_TYPES,
    SIGNAL_UPDATE,
    SUBENTRY_UNIT,
    TEST_UNIT_ID,
)
from .controller import DoorController, MachineController, UnitController
from .hub import MakerLinkHub
from .readers import (
    HARDWARE,
    UnitFormError,
    build_unit_data,
    generate_yaml,
    suggest_devicename,
    valid_devicename,
)

ACTIONS = ["stop_session", "open_door", "out_of_order", "admin"]
IDENTIFY_SECONDS = 10


@callback
def async_setup(hass: HomeAssistant) -> None:
    """Register the websocket commands (once per HA start)."""
    for command in (
        ws_units,
        ws_subscribe,
        ws_action,
        ws_options,
        ws_reader_yaml,
        ws_identify,
        ws_unit_add,
        ws_unit_update,
        ws_unit_remove,
    ):
        websocket_api.async_register_command(hass, command)


def _hubs(hass: HomeAssistant) -> list[MakerLinkHub]:
    return [
        entry.runtime_data
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]


def _snapshot(hass: HomeAssistant) -> dict[str, Any]:
    units = [hub.unit_snapshot(sub_id) for hub in _hubs(hass) for sub_id in list(hub.units)]
    units.sort(key=lambda u: (u["kind"], u["name"].lower()))
    entries = hass.config_entries.async_entries(DOMAIN)
    return {
        "units": units,
        "configured": bool(entries),
        # Onboarding: readers without a unit, and ESPHome devices still waiting for the
        # "Add" confirmation in the ESPHome integration.
        "readers": discovery.find_readers(hass, entries),
        "esphome_pending": discovery.pending_esphome(hass),
    }


def _find_unit(hass: HomeAssistant, sub_id: str) -> UnitController | None:
    for hub in _hubs(hass):
        if sub_id in hub.units:
            return hub.units[sub_id]
    return None


@websocket_api.websocket_command({vol.Required("type"): "makerlink/units"})
@callback
def ws_units(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    connection.send_result(msg["id"], _snapshot(hass))


@websocket_api.websocket_command({vol.Required("type"): "makerlink/subscribe"})
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    @callback
    def forward(*_args: Any) -> None:
        connection.send_message(websocket_api.event_message(msg["id"], _snapshot(hass)))

    # A new ESPHome device (and its entities) shows up in the registries.
    unsubs: list[Callable[[], None]] = [
        async_dispatcher_connect(hass, SIGNAL_UPDATE, forward),
        hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, forward),
        hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, forward),
    ]

    @callback
    def unsubscribe() -> None:
        for unsub in unsubs:
            unsub()

    connection.subscriptions[msg["id"]] = unsubscribe
    connection.send_result(msg["id"])
    forward()


@websocket_api.websocket_command(
    {
        vol.Required("type"): "makerlink/action",
        vol.Required("unit"): str,
        vol.Required("action"): vol.In(ACTIONS),
        vol.Optional("value"): bool,
    }
)
@websocket_api.async_response
async def ws_action(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    unit = _find_unit(hass, msg["unit"])
    if unit is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Unit not found")
        return

    action = msg["action"]
    value = msg.get("value", True)
    if action == "out_of_order":
        await unit.set_setting("out_of_order", value)
    elif action == "stop_session" and isinstance(unit, MachineController):
        await unit.stop_session("panel")
    elif action == "admin" and isinstance(unit, MachineController):
        await unit.set_admin(value)
    elif action == "open_door" and isinstance(unit, DoorController):
        await unit.open_door()
    else:
        connection.send_error(
            msg["id"], websocket_api.ERR_NOT_SUPPORTED, f"{action} not supported for {unit.kind}"
        )
        return
    connection.send_result(msg["id"])


# ----- onboarding ---------------------------------------------------------------------


def _loaded_entry(hass: HomeAssistant) -> ConfigEntry | None:
    hubs = _hubs(hass)
    return hubs[0].entry if hubs else None


def _find_subentry(hass: HomeAssistant, sub_id: str) -> tuple[ConfigEntry, ConfigSubentry] | None:
    for hub in _hubs(hass):
        if sub := hub.entry.subentries.get(sub_id):
            return hub.entry, sub
    return None


def _check_unique(entry: ConfigEntry, data: dict[str, Any], except_id: str | None) -> str | None:
    others = [
        s
        for s in entry.subentries.values()
        if s.subentry_type == SUBENTRY_UNIT and s.subentry_id != except_id
    ]
    unit_id = data[CONF_UNIT_ID]
    if unit_id != TEST_UNIT_ID and any(int(s.data[CONF_UNIT_ID]) == unit_id for s in others):
        return "unit_exists"
    if any(s.data.get(CONF_READER_DEVICE) == data[CONF_READER_DEVICE] for s in others):
        return "reader_in_use"
    return None


_UNIT_FIELDS = {
    vol.Optional("power_entity"): vol.Any(None, str),
    vol.Optional("machine_type"): vol.In(MACHINE_TYPES),
    vol.Optional("min_balance"): vol.Any(None, vol.Coerce(float)),
    vol.Optional("shutdown_time"): vol.Any(None, "", vol.Coerce(float)),
    vol.Optional("pulse_time"): vol.Any(None, vol.Coerce(float)),
    vol.Optional("interlocks"): vol.All(vol.Coerce(int), vol.Range(min=0, max=2)),
}


def _form(msg: dict[str, Any]) -> dict[str, Any]:
    skip = {"id", "type", "name", "unit"}
    return {k: v for k, v in msg.items() if k not in skip and v is not None}


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "makerlink/options"})
@callback
def ws_options(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    switches = [
        {"entity_id": s.entity_id, "name": s.name}
        for domain in POWER_DOMAINS
        for s in hass.states.async_all(domain)
        if s.state != STATE_UNAVAILABLE
    ]
    switches.sort(key=lambda s: s["name"].lower())
    connection.send_result(
        msg["id"],
        {
            "hardware": [{"id": k, "label": v["label"]} for k, v in HARDWARE.items()],
            "machine_types": MACHINE_TYPES,
            "suggested_devicename": suggest_devicename(discovery.esphome_device_names(hass)),
            "test_unit_id": TEST_UNIT_ID,
            "switches": switches,
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "makerlink/reader_yaml",
        vol.Required("hardware"): vol.In(list(HARDWARE)),
        vol.Required("devicename"): str,
        vol.Optional("friendly_name"): str,
    }
)
@callback
def ws_reader_yaml(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    name = msg["devicename"].strip()
    if not valid_devicename(name):
        connection.send_error(msg["id"], "invalid_devicename", "invalid device name")
        return
    if name in discovery.esphome_device_names(hass):
        connection.send_error(msg["id"], "devicename_exists", "device name already used")
        return
    connection.send_result(
        msg["id"],
        {
            "filename": f"{name}.yaml",
            "yaml": generate_yaml(msg["hardware"], name, msg.get("friendly_name")),
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "makerlink/identify", vol.Required("reader_device"): str}
)
@websocket_api.async_response
async def ws_identify(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Show a marker on the display so the person at the bench knows which reader this is."""
    device_id = msg["reader_device"]
    device = dr.async_get(hass).async_get(device_id)
    detected = discovery.detect(hass, device_id)
    lines = [detected.get(CONF_DISPLAY_LINE1), detected.get(CONF_DISPLAY_LINE2)]
    if device is None or not all(lines):
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Reader has no display")
        return

    running: dict[str, Any] = hass.data.setdefault(f"{DOMAIN}_identify", {})
    if job := running.pop(device_id, None):
        job["cancel"]()
        originals = job["originals"]
    else:
        originals = [s.state if (s := hass.states.get(e)) else "" for e in lines]

    async def show(values: list[str]) -> None:
        for entity_id, value in zip(lines, values, strict=True):
            await hass.services.async_call(
                "text", "set_value", {"entity_id": entity_id, "value": value[:16]}, blocking=True
            )

    async def restore(_now: datetime) -> None:
        running.pop(device_id, None)
        await show(originals)

    await show(["HIER BIN ICH", device.name_by_user or device.name or ""])
    running[device_id] = {
        "originals": originals,
        "cancel": async_call_later(hass, IDENTIFY_SECONDS, restore),
    }
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "makerlink/unit_add",
        vol.Required("name"): vol.All(str, vol.Strip, vol.Length(min=1, max=64)),
        vol.Required("reader_device"): str,
        vol.Required("kind"): vol.In(KINDS),
        vol.Required("unit_id"): vol.Coerce(int),
        **_UNIT_FIELDS,
    }
)
@callback
def ws_unit_add(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    entry = _loaded_entry(hass)
    if entry is None:
        connection.send_error(msg["id"], "not_configured", "MakerLink is not set up")
        return
    try:
        data = build_unit_data(_form(msg), None, discovery.detect(hass, msg["reader_device"]))
    except UnitFormError as err:
        connection.send_error(msg["id"], err.key, err.key)
        return
    if error := _check_unique(entry, data, None):
        connection.send_error(msg["id"], error, error)
        return
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data=MappingProxyType(data),
            subentry_type=SUBENTRY_UNIT,
            title=msg["name"],
            unique_id=_unit_unique_id(data[CONF_UNIT_ID]),
        ),
    )
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "makerlink/unit_update",
        vol.Required("unit"): str,
        vol.Optional("name"): vol.All(str, vol.Strip, vol.Length(min=1, max=64)),
        vol.Optional("kind"): vol.In(KINDS),
        vol.Optional("unit_id"): vol.Coerce(int),
        **_UNIT_FIELDS,
    }
)
@websocket_api.async_response
async def ws_unit_update(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    found = _find_subentry(hass, msg["unit"])
    if found is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Unit not found")
        return
    entry, subentry = found
    unit = _find_unit(hass, subentry.subentry_id)
    form = _form(msg)
    if form.get("kind", subentry.data[CONF_KIND]) != subentry.data[CONF_KIND]:
        if unit is not None and (
            getattr(unit, "session_active", False) or getattr(unit, "pending_stops", None)
        ):
            connection.send_error(msg["id"], "unit_busy", "unit_busy")
            return
    elif "machine_type" in form and isinstance(unit, MachineController):
        # Runtime setting (stored, wins over the entry data): change it like the select entity.
        await unit.set_setting("machine_type", form.pop("machine_type"))
    try:
        data = build_unit_data(
            form,
            subentry.data,
            discovery.detect(hass, subentry.data[CONF_READER_DEVICE]),
        )
    except UnitFormError as err:
        connection.send_error(msg["id"], err.key, err.key)
        return
    if error := _check_unique(entry, data, subentry.subentry_id):
        connection.send_error(msg["id"], error, error)
        return
    hass.config_entries.async_update_subentry(
        entry,
        subentry,
        data=data,
        title=msg.get("name", subentry.title),
        unique_id=_unit_unique_id(data[CONF_UNIT_ID]),
    )
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {vol.Required("type"): "makerlink/unit_remove", vol.Required("unit"): str}
)
@callback
def ws_unit_remove(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    found = _find_subentry(hass, msg["unit"])
    if found is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Unit not found")
        return
    hass.config_entries.async_remove_subentry(found[0], msg["unit"])
    connection.send_result(msg["id"])
