"""WebSocket API for the MakerLink sidebar panel.

makerlink/units      -> {"units": [...]}                     one-shot snapshot
makerlink/subscribe  -> event messages {"units": [...]}      on every change
makerlink/action     -> run an action on one unit (stop_session, open_door,
                        out_of_order, admin)
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_UPDATE
from .controller import DoorController, MachineController, UnitController
from .hub import MakerLinkHub

ACTIONS = ["stop_session", "open_door", "out_of_order", "admin"]


@callback
def async_setup(hass: HomeAssistant) -> None:
    """Register the websocket commands (once per HA start)."""
    websocket_api.async_register_command(hass, ws_units)
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_action)


def _hubs(hass: HomeAssistant) -> list[MakerLinkHub]:
    return [
        entry.runtime_data
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]


def _snapshot(hass: HomeAssistant) -> dict[str, Any]:
    units = [hub.unit_snapshot(sub_id) for hub in _hubs(hass) for sub_id in list(hub.units)]
    units.sort(key=lambda u: (u["kind"], u["name"].lower()))
    return {"units": units, "configured": bool(hass.config_entries.async_entries(DOMAIN))}


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
    def forward() -> None:
        connection.send_message(websocket_api.event_message(msg["id"], _snapshot(hass)))

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(hass, SIGNAL_UPDATE, forward)
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
