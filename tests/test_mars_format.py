"""Tests for UID conversion and response parsing."""

import pytest

from custom_components.makerlink.mars_format import DoorResult, MarsResult, uid_to_mars


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Example from the legacy RC522 lambda
        ("F4-96-D2-03", "0xf4 0x96 0xd2 0x3"),
        ("f4:96:d2:03", "0xf4 0x96 0xd2 0x3"),
        ("F496D203", "0xf4 0x96 0xd2 0x3"),
        ("00-0A-B0-01", "0x0 0xa 0xb0 0x1"),
        ("04-A2-1B-7C-55-80", "0x4 0xa2 0x1b 0x7c 0x55 0x80"),
        (" F4 96 D2 03 ", "0xf4 0x96 0xd2 0x3"),
    ],
)
def test_uid_to_mars(raw, expected):
    assert uid_to_mars(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "6f1c2a8e-uuid-tag", "XYZ1"])
def test_uid_to_mars_rejects(raw):
    assert uid_to_mars(raw) is None


def test_start_ok():
    res = MarsResult.from_json({"ok": True, "key": 23212, "name": "Max", "msg": "Aktiviert"})
    assert res.ok and res.key == 23212 and res.name == "Max"


def test_start_fail():
    res = MarsResult.from_json(
        {"ok": False, "key": None, "name": None, "msg": "Keine Schulung fuer diese Maschine"}
    )
    assert not res.ok and res.key is None and res.msg.startswith("Keine Schulung")


def test_stop_ok():
    res = MarsResult.from_json(
        {"ok": True, "key": None, "msg": "Gestoppt", "cost": -2.5, "balance": 12.3, "duration_s": 900}
    )
    assert res.cost == -2.5 and res.balance == 12.3 and res.duration_s == 900


def test_garbage():
    assert MarsResult.from_json(None).ok is False


def test_door():
    assert DoorResult.from_json(["True", "Super User", "Unlimited"]).allowed
    res = DoorResult.from_json(["False", "Wrong Time", "Mon18-22"])
    assert not res.allowed and res.reason == "Wrong Time"
    assert not DoorResult.from_json({"ok": False, "msg": "x"}).allowed
