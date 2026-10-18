"""Tests for the machine and door state machines."""

from __future__ import annotations

import pytest

from custom_components.makerlink.controller import (
    STATUS_ACTIVE,
    STATUS_ADMIN,
    STATUS_COOLDOWN,
    STATUS_IDLE,
    STATUS_INTERLOCK_OPEN,
    DoorController,
    MachineController,
)
from custom_components.makerlink.mars_format import (
    DoorResult,
    MarsConnectionError,
    MarsHttpError,
    MarsResult,
)

CARD = "F4-96-D2-03"
RFID = "0xf4 0x96 0xd2 0x3"


class FakeApi:
    def __init__(self):
        self.calls = []
        self.start_result = MarsResult(ok=True, key=42, name="Max", msg="Aktiviert")
        self.stop_result = MarsResult(ok=True, msg="Gestoppt", cost=-2.5, balance=10.0)
        self.door_result = DoorResult(allowed=True, reason="Super User")
        self.fail = False
        self.stop_error = None

    async def start(self, rfid, unit_id, machine_type, min_balance):
        self.calls.append(("start", rfid, unit_id, machine_type, min_balance))
        if self.fail:
            raise MarsConnectionError("down")
        return self.start_result

    async def stop(self, key, unit_id, machine_type, end=None):
        self.calls.append(("stop", key, unit_id, machine_type, end))
        if self.fail:
            raise MarsConnectionError("down")
        if self.stop_error:
            raise self.stop_error
        return self.stop_result

    async def door_check(self, rfid):
        self.calls.append(("door_check", rfid))
        return self.door_result

    async def log_door(self, rfid, allowed, unit_id):
        self.calls.append(("log_door", rfid, allowed, unit_id))


class FakeHw:
    def __init__(self, power=False, interlock=True):
        self.power = power
        self.interlock = interlock
        self.lines = None
        self.switches = []

    def power_state(self):
        return self.power

    async def set_power(self, on):
        self.switches.append(on)
        self.power = on

    def interlock_closed(self):
        return self.interlock

    async def show(self, l1, l2):
        self.lines = (l1, l2)


async def no_sleep(_s):
    return None


def make_machine(shutdown_time=0, **hw_kwargs):
    api, hw, events = FakeApi(), FakeHw(**hw_kwargs), []
    ctrl = MachineController(
        name="P1P",
        unit_id=1720,
        api=api,
        hardware=hw,
        machine_type="3dprint",
        settings={"shutdown_time": shutdown_time},
        fire_event=lambda e, d: events.append((e, d)),
        clock=lambda: 1000.0,
        sleep=no_sleep,
    )
    return ctrl, api, hw, events


async def ticks(ctrl, n):
    for _ in range(n):
        await ctrl.tick()


async def test_start_and_stop_without_cooldown():
    ctrl, api, hw, events = make_machine()
    await ctrl.async_start()
    await ctrl.on_card(CARD)
    assert api.calls[0] == ("start", RFID, 1720, "3dprint", 5.0)
    assert ctrl.status == STATUS_ACTIVE and hw.power is True
    assert hw.lines == ("EIN:", "Max")

    await ticks(ctrl, 5)  # card cooldown
    await ctrl.on_card(CARD)
    assert api.calls[1][:4] == ("stop", 42, 1720, "3dprint")
    assert hw.power is False and ctrl.status == STATUS_IDLE
    assert ctrl.last_balance == 10.0
    assert [e for e, _ in events] == ["makerlink_session_started", "makerlink_session_stopped"]


async def test_cooldown_keeps_power_then_switches_off():
    ctrl, api, hw, _ = make_machine(shutdown_time=3)
    await ctrl.async_start()
    await ctrl.on_card(CARD)
    await ticks(ctrl, 5)
    await ctrl.on_card(CARD)
    assert ctrl.status == STATUS_COOLDOWN and hw.power is True
    assert hw.lines[0] == "STOPPT:"
    await ticks(ctrl, 3)
    assert hw.power is False and ctrl.status == STATUS_IDLE


async def test_card_cooldown_ignores_double_scan():
    ctrl, api, hw, _ = make_machine()
    await ctrl.async_start()
    await ctrl.on_card(CARD)
    await ctrl.on_card(CARD)
    assert [c[0] for c in api.calls] == ["start"]


async def test_rejected_start_shows_message():
    ctrl, api, hw, events = make_machine()
    api.start_result = MarsResult(ok=False, msg="Keine Schulung fuer diese Maschine")
    await ctrl.async_start()
    await ctrl.on_card(CARD)
    assert hw.power is False
    assert hw.lines == ("ABGELEHNT", "Keine Schulung f")
    assert events[-1][0] == "makerlink_card_rejected"
    await ticks(ctrl, 3)
    assert hw.lines == ("-MakerAustria-", "Karte bitte")


async def test_out_of_order_rejects():
    ctrl, api, hw, _ = make_machine()
    await ctrl.async_start()
    await ctrl.set_setting("out_of_order", True)
    await ctrl.on_card(CARD)
    assert api.calls == [] and hw.power is False


async def test_interlock_blocks_start():
    ctrl, api, hw, _ = make_machine(interlock=False)
    await ctrl.async_start()
    assert ctrl.status == STATUS_INTERLOCK_OPEN
    await ctrl.on_card(CARD)
    assert api.calls == [] and hw.power is False


async def test_interlock_open_during_session_stops_immediately():
    ctrl, api, hw, events = make_machine(shutdown_time=60)
    await ctrl.async_start()
    await ctrl.on_card(CARD)
    hw.interlock = False
    await ctrl.on_interlock_changed()
    assert hw.power is False and ctrl.shutdown_counter == 0
    assert api.calls[-1][0] == "stop"
    assert events[-1][1]["reason"] == "interlock"


async def test_power_unavailable_blocks_start():
    ctrl, api, hw, _ = make_machine()
    hw.power = None
    await ctrl.on_card(CARD)
    assert api.calls == [] and hw.lines == ("FEHLER", "Schalter offline")


async def test_external_on_is_admin_and_off_ends_it():
    ctrl, api, hw, _ = make_machine()
    await ctrl.async_start()
    hw.power = True
    await ctrl.on_power_changed(True)
    assert ctrl.status == STATUS_ADMIN
    hw.power = False
    await ctrl.on_power_changed(False)
    assert ctrl.status == STATUS_IDLE


async def test_external_off_during_session_stops():
    ctrl, api, hw, events = make_machine()
    await ctrl.async_start()
    await ctrl.on_card(CARD)
    hw.power = False
    await ctrl.on_power_changed(False)
    assert not ctrl.session_active
    assert events[-1][1]["reason"] == "power_off"


async def test_own_switching_is_not_external():
    ctrl, api, hw, _ = make_machine()
    await ctrl.async_start()
    await ctrl.on_card(CARD)
    await ctrl.on_power_changed(True)  # echo of our own turn_on
    assert ctrl.status == STATUS_ACTIVE


async def test_stop_while_backend_down_is_queued_and_retried():
    ctrl, api, hw, events = make_machine()
    await ctrl.async_start()
    await ctrl.on_card(CARD)
    api.fail = True
    await ticks(ctrl, 5)
    await ctrl.on_card(CARD)
    assert hw.power is False and len(ctrl.pending_stops) == 1
    assert events[-1][1]["billed"] is False
    api.fail = False
    await ticks(ctrl, 60)
    assert ctrl.pending_stops == []
    assert api.calls[-1] == ("stop", 42, 1720, "3dprint", 1000)


async def test_restore_running_session_with_power_on():
    ctrl, api, hw, _ = make_machine(power=True)
    ctrl.restore({"session_key": 7, "session_start": 900.0, "user": "Max"})
    await ctrl.async_start()
    assert ctrl.status == STATUS_ACTIVE and api.calls == []


async def test_restore_session_with_power_off_closes_it():
    ctrl, api, hw, _ = make_machine(power=False)
    ctrl.restore({"session_key": 7, "session_start": 900.0, "user": "Max"})
    await ctrl.async_start()
    assert not ctrl.session_active
    assert api.calls[0][:2] == ("stop", 7)


async def test_coffee_style_booking_without_session():
    ctrl, api, hw, _ = make_machine()
    api.start_result = MarsResult(ok=True, key=None, name="Max", msg="Kaffee verrechnet", balance=9.5)
    await ctrl.async_start()
    await ctrl.on_card(CARD)
    assert not ctrl.session_active and hw.power is False
    assert hw.lines == ("Kaffee verrechnet"[:16], "Gut: 9.50 EUR")


async def test_admin_switch():
    ctrl, api, hw, _ = make_machine()
    await ctrl.async_start()
    await ctrl.set_admin(True)
    assert hw.power is True and ctrl.status == STATUS_ADMIN
    await ctrl.set_admin(False)
    assert hw.power is False


@pytest.mark.parametrize("allowed", [True, False])
async def test_door(allowed):
    api, hw = FakeApi(), FakeHw()
    api.door_result = DoorResult(allowed=allowed, reason="Wrong Time" if not allowed else "OK")
    ctrl = DoorController(
        name="Eingang", unit_id=1, api=api, hardware=hw, sleep=no_sleep,
        settings={"pulse_time": 2},
    )
    await ctrl.async_start()
    await ctrl.on_card(CARD)
    # let the delayed log task run
    import asyncio

    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert ("log_door", RFID, allowed, 1) in api.calls
    assert hw.switches == ([True, False] if allowed else [])
    assert hw.power is False


async def test_permanent_stop_error_is_not_queued():
    ctrl, api, hw, events = make_machine()
    await ctrl.async_start()
    await ctrl.on_card(CARD)
    api.stop_error = MarsHttpError(400, "Parameter key fehlt")
    await ticks(ctrl, 5)
    await ctrl.on_card(CARD)
    assert hw.power is False and ctrl.pending_stops == []
    assert hw.lines == ("FEHLER", "Stop abgelehnt")


async def test_server_error_is_queued_and_retried_with_end():
    ctrl, api, hw, events = make_machine()
    await ctrl.async_start()
    await ctrl.on_card(CARD)
    api.stop_error = MarsHttpError(500, "DB Fehler")
    await ticks(ctrl, 5)
    await ctrl.on_card(CARD)
    assert len(ctrl.pending_stops) == 1
    api.stop_error = None
    await ticks(ctrl, 60)
    assert ctrl.pending_stops == []
    assert api.calls[-1] == ("stop", 42, 1720, "3dprint", 1000)


async def test_queued_stop_dropped_on_permanent_error():
    ctrl, api, hw, events = make_machine()
    ctrl.pending_stops = [{"key": 9, "unit_id": 1720, "type": "3dprint", "end": 900}]
    api.stop_error = MarsHttpError(400, "bad")
    await ctrl.retry_pending()
    assert ctrl.pending_stops == []


async def test_queued_stop_already_booked_counts_as_done():
    ctrl, api, hw, events = make_machine()
    ctrl.pending_stops = [{"key": 9, "unit_id": 1720, "type": "3dprint", "end": 900}]
    api.stop_result = MarsResult(ok=True, msg="Bereits gestoppt")
    await ctrl.retry_pending()
    assert ctrl.pending_stops == []
