"""Tests for reader onboarding helpers."""

import re
from pathlib import Path

import pytest

from custom_components.makerlink.readers import (
    HARDWARE,
    UnitFormError,
    build_unit_data,
    classify_entities,
    generate_yaml,
    suggest_devicename,
    valid_devicename,
)

ESPHOME = Path(__file__).resolve().parents[1] / "esphome"

@pytest.mark.parametrize("hardware", HARDWARE)
def test_tocopy_files_match_generator(hardware):
    """esphome/tocopy-*.yaml are generated output (any names): change readers.py, not the files."""
    text = (ESPHOME / HARDWARE[hardware]["file"]).read_text(encoding="utf-8")
    name = re.search(r"^  devicename: (.+)$", text, re.MULTILINE).group(1).strip()
    friendly = re.search(r"^  friendly_name: (.+)$", text, re.MULTILINE).group(1).strip()
    assert text == generate_yaml(hardware, name, friendly)


def test_generate_yaml_names_and_quoting():
    text = generate_yaml("esp32s3-xiao", "maker-17", "Kiln: \"Ofen\" 1")
    assert "devicename: maker-17" in text
    assert 'friendly_name: "Kiln: \\"Ofen\\" 1"' in text
    assert "@@" not in text
    assert "friendly_name: MakerLink Reader maker-17" in generate_yaml("esp32s3-xiao", "maker-17")


def test_generate_yaml_rejects_bad_input():
    with pytest.raises(ValueError):
        generate_yaml("nope", "maker-1")
    with pytest.raises(ValueError):
        generate_yaml("esp32s3-xiao", "Maker 1")


@pytest.mark.parametrize(
    ("name", "ok"),
    [("maker9998", True), ("a", True), ("makerlink-01", True), ("Maker", False),
     ("-x", False), ("x-", False), ("a_b", False), ("", False), ("x" * 32, False)],
)
def test_valid_devicename(name, ok):
    assert valid_devicename(name) is ok


def test_suggest_devicename():
    assert suggest_devicename([]) == "makerlink-01"
    assert suggest_devicename(["makerlink-01", None, "makerlink-02", "other"]) == "makerlink-03"


ENTITIES = [
    ("text.r_display_zeile_2", "Display Zeile 2"),
    ("text.r_display_zeile_1", "Display Zeile 1"),
    ("switch.r_relais", "Relais"),
    ("binary_sensor.r_sicherheitsschalter_1", "Sicherheitsschalter 1"),
    ("binary_sensor.r_sicherheitsschalter_2", "Sicherheitsschalter 2"),
    ("binary_sensor.r_pn532", "PN532 bereit"),
    ("sensor.r_wlan", "WLAN Signal"),
]


def test_classify_entities():
    assert classify_entities(ENTITIES) == {
        "display_line1": "text.r_display_zeile_1",
        "display_line2": "text.r_display_zeile_2",
        "power_entity": "switch.r_relais",
        "interlock_1": "binary_sensor.r_sicherheitsschalter_1",
        "interlock_2": "binary_sensor.r_sicherheitsschalter_2",
    }


def test_classify_entities_fallback_and_legacy_without_switches():
    found = classify_entities([("text.a", "Foo"), ("text.b", "Bar"), ("switch.x", "Whatever")])
    assert found == {"display_line1": "text.a", "display_line2": "text.b", "power_entity": "switch.x"}
    assert "power_entity" not in classify_entities([("text.a", "Display Zeile 1")])


DETECTED = classify_entities(ENTITIES)


def test_add_machine_uses_detected_entities_and_defaults():
    data = build_unit_data({"kind": "machine", "unit_id": "12", "reader_device": "dev1"}, None, DETECTED)
    assert data["power_entity"] == "switch.r_relais"
    assert "interlock_1" not in data and "interlock_2" not in data  # unwired inputs read "open"
    assert data["machine_type"] == "machine"
    assert data["min_balance"] == 5.0
    assert data["unit_id"] == 12
    assert "shutdown_time" not in data and "pulse_time" not in data


def test_add_door():
    data = build_unit_data({"kind": "door", "unit_id": 3, "reader_device": "d"}, None, DETECTED)
    assert data["pulse_time"] == 3.0
    assert not {"machine_type", "min_balance", "interlock_1", "interlock_2"} & set(data)


def test_switch_machine_to_door_and_back_keeps_hardware():
    machine = build_unit_data(
        {"kind": "machine", "unit_id": 5, "reader_device": "d", "machine_type": "kiln", "shutdown_time": 30},
        None,
        DETECTED,
    )
    door = build_unit_data({"kind": "door"}, machine, DETECTED)
    assert door["kind"] == "door"
    assert door["power_entity"] == machine["power_entity"]
    assert door["display_line1"] == machine["display_line1"]
    assert "machine_type" not in door and "shutdown_time" not in door
    back = build_unit_data({"kind": "machine", "interlocks": 1}, door, DETECTED)
    assert back["kind"] == "machine"
    assert back["interlock_1"] == "binary_sensor.r_sicherheitsschalter_1"
    assert "interlock_2" not in back
    assert back["machine_type"] == "machine" and "pulse_time" not in back


def test_edit_keeps_unrelated_fields_and_custom_power_target():
    current = {
        "kind": "machine", "unit_id": 5, "reader_device": "d", "machine_type": "3dprint",
        "min_balance": 2.0, "power_entity": "switch.plug", "display_line1": "text.x",
    }
    data = build_unit_data({"unit_id": 6, "min_balance": 0}, current, DETECTED)
    assert data["unit_id"] == 6 and data["min_balance"] == 0.0
    assert data["power_entity"] == "switch.plug" and data["display_line1"] == "text.x"
    assert data["machine_type"] == "3dprint"


def test_empty_shutdown_time_is_removed():
    current = {"kind": "machine", "unit_id": 5, "reader_device": "d", "power_entity": "switch.p", "shutdown_time": 30}
    assert "shutdown_time" not in build_unit_data({"shutdown_time": ""}, current)


@pytest.mark.parametrize(
    ("form", "detected", "key"),
    [
        ({"kind": "boat", "unit_id": 1, "reader_device": "d"}, DETECTED, "invalid_kind"),
        ({"kind": "door", "unit_id": 0, "reader_device": "d"}, DETECTED, "invalid_unit_id"),
        ({"kind": "door", "unit_id": 1}, DETECTED, "no_reader"),
        ({"kind": "door", "unit_id": 1, "reader_device": "d"}, {}, "no_power_target"),
        ({"kind": "machine", "unit_id": 1, "reader_device": "d", "machine_type": "x"}, DETECTED, "invalid_machine_type"),
    ],
)
def test_form_errors(form, detected, key):
    with pytest.raises(UnitFormError) as err:
        build_unit_data(form, None, detected)
    assert err.value.key == key


def test_interlock_count_add_change_and_keep():
    base = {"kind": "machine", "unit_id": 1, "reader_device": "d"}
    two = build_unit_data({**base, "interlocks": 2}, None, DETECTED)
    assert two["interlock_1"].endswith("_1") and two["interlock_2"].endswith("_2")
    one = build_unit_data({"interlocks": 1}, two, DETECTED)
    assert "interlock_1" in one and "interlock_2" not in one
    none = build_unit_data({"interlocks": 0}, one, DETECTED)
    assert "interlock_1" not in none
    # not given: keep as is, also custom entities from the manual flow
    custom = {**two, "interlock_1": "binary_sensor.custom"}
    assert build_unit_data({}, custom, DETECTED)["interlock_1"] == "binary_sensor.custom"
    assert build_unit_data({"interlocks": 2}, custom, DETECTED)["interlock_1"] == "binary_sensor.custom"


def test_interlock_errors():
    base = {"kind": "machine", "unit_id": 1, "reader_device": "d"}
    with pytest.raises(UnitFormError) as err:
        build_unit_data({**base, "interlocks": 3}, None, DETECTED)
    assert err.value.key == "invalid_interlocks"
    without = {k: v for k, v in DETECTED.items() if k != "interlock_2"}
    with pytest.raises(UnitFormError) as err:
        build_unit_data({**base, "interlocks": 2}, None, without)
    assert err.value.key == "no_interlock_entity"
