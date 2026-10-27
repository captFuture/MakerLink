"""Reader onboarding helpers (no Home Assistant imports, see CLAUDE.md).

- generate_yaml: device YAML for a hardware variant (replaces copy and rename of tocopy-*.yaml)
- classify_entities: finds display lines, relay and safety switches of a MakerLink reader
- build_unit_data: unit (subentry) data for add and for kind switch (machine <-> door)
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from .const import (
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
    DEFAULT_MIN_BALANCE,
    DEFAULT_PULSE_TIME,
    KIND_DOOR,
    KIND_MACHINE,
    MACHINE_TYPES,
)

DEVICENAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,29}[a-z0-9])?$")
NAME_PLACEHOLDER = "@@DEVICENAME@@"
FRIENDLY_PLACEHOLDER = "@@FRIENDLY@@"

_S3_HEADER = """\
# MakerLink Reader: {title} + PN532 (HSU) + LCD 16x2 und/oder OLED 128x32
# Beide Displays sind einkompiliert (je ein eigener I2C-Bus), es steckt, was gebaut wurde.
# Details zur Hardware: common/{board}.yaml, common/esp32s3-pn532-hsu.yaml, Displays: common/display-dual.yaml

substitutions:
  devicename: @@DEVICENAME@@
  friendly_name: @@FRIENDLY@@
  # display_i2c_address: "0x3F"   # LCD, Standard 0x27
  # oled_i2c_address: "0x3D"      # OLED, Standard 0x3C

esphome:
  name: ${{devicename}}

packages:
  base: !include common/makerlink-reader-base.yaml
  board: !include common/{board}.yaml
  hardware: !include common/esp32s3-pn532-hsu.yaml
  display: !include common/display-dual.yaml
"""

_ESP8266 = """\
# MakerLink Reader: ESP8266 D1 Mini + RC522 (SPI) + LCD 16x2 (PCF8574)
# Übergangsvariante für bestehende Reader-Hardware: gleiche Pins wie die
# bisherige Firmware, aber ohne Business-Logik.

substitutions:
  devicename: @@DEVICENAME@@
  friendly_name: @@FRIENDLY@@
  p_relay: GPIO16
  p_sda: GPIO4
  p_scl: GPIO5
  p_rfid_rst: GPIO0
  p_rfid_ss: GPIO15

esphome:
  name: ${devicename}

packages:
  base: !include common/makerlink-reader-base.yaml
  display: !include common/display-lcd1602.yaml

esp8266:
  board: d1_mini

i2c:
  sda: ${p_sda}
  scl: ${p_scl}
  frequency: 100kHz

spi:
  clk_pin: GPIO14
  mosi_pin: GPIO13
  miso_pin: GPIO12

rc522_spi:
  cs_pin: ${p_rfid_ss}
  reset_pin: ${p_rfid_rst}
  update_interval: 1s
  on_tag:
    then:
      - script.execute:
          id: card_scanned
          uid: !lambda "return x;"

switch:
  - platform: gpio
    id: relay
    name: "Relais"
    pin: ${p_relay}
    restore_mode: ALWAYS_OFF
"""

# id -> label and template. The Zigbee reader is missing on purpose (no ESPHome API).
HARDWARE: dict[str, dict[str, str]] = {
    "esp32s3-xiao": {
        "label": "XIAO ESP32-S3 + PN532 + LCD/OLED",
        "file": "tocopy-makerlink-esp32s3-xiao.yaml",
        "template": _S3_HEADER.format(title="XIAO ESP32-S3", board="esp32s3-xiao"),
    },
    "esp32s3-supermini": {
        "label": "ESP32-S3 Super Mini + PN532 + LCD/OLED",
        "file": "tocopy-makerlink-esp32s3-supermini.yaml",
        "template": _S3_HEADER.format(title="ESP32-S3 Super Mini", board="esp32s3-supermini"),
    },
    "esp8266-rc522-lcd": {
        "label": "Wemos D1 Mini (Bestands-Reader) + RC522 + LCD",
        "file": "tocopy-makerlink-esp8266-rc522-lcd.yaml",
        "template": _ESP8266,
    },
}


def valid_devicename(name: str) -> bool:
    return bool(DEVICENAME_RE.match(name))


def suggest_devicename(existing: Iterable[str | None], prefix: str = "makerlink") -> str:
    """First free `<prefix>-NN` (two digits), so the name needs no thinking."""
    taken = {e for e in existing if e}
    number = 1
    while f"{prefix}-{number:02d}" in taken:
        number += 1
    return f"{prefix}-{number:02d}"


def _yaml_scalar(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]*", value):
        return value
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def generate_yaml(hardware: str, devicename: str, friendly_name: str | None = None) -> str:
    """Device YAML for `/config/esphome/<devicename>.yaml`."""
    if hardware not in HARDWARE:
        raise ValueError(f"unknown hardware: {hardware}")
    if not valid_devicename(devicename):
        raise ValueError(f"invalid device name: {devicename}")
    friendly = (friendly_name or "").strip() or f"MakerLink Reader {devicename}"
    return (
        HARDWARE[hardware]["template"]
        .replace(NAME_PLACEHOLDER, devicename)
        .replace(FRIENDLY_PLACEHOLDER, _yaml_scalar(friendly))
    )


# ----- entity detection --------------------------------------------------------------


def classify_entities(entities: Iterable[tuple[str, str | None]]) -> dict[str, str]:
    """Map the entities of a reader device to unit fields.

    `entities` are (entity_id, name) pairs; names are the ESPHome names from the firmware
    ("Display Zeile 1", "Relais", "Sicherheitsschalter 1").
    """
    found: dict[str, str] = {}
    texts: list[str] = []
    switches: list[str] = []
    for entity_id, name in sorted(entities):
        domain = entity_id.split(".", 1)[0]
        label = (name or "").lower()
        if domain == "text":
            texts.append(entity_id)
            if label.endswith(("1", "eins")):
                found.setdefault(CONF_DISPLAY_LINE1, entity_id)
            elif label.endswith(("2", "zwei")):
                found.setdefault(CONF_DISPLAY_LINE2, entity_id)
        elif domain == "switch":
            switches.append(entity_id)
            if "relais" in label or "relay" in label:
                found.setdefault(CONF_POWER_ENTITY, entity_id)
        elif domain == "binary_sensor" and ("sicherheitsschalter" in label or "interlock" in label):
            key = CONF_INTERLOCK_2 if label.endswith("2") else CONF_INTERLOCK_1
            found.setdefault(key, entity_id)
    # Fallbacks for unusual names: exactly two texts / one switch.
    if CONF_DISPLAY_LINE1 not in found and CONF_DISPLAY_LINE2 not in found and len(texts) == 2:
        found[CONF_DISPLAY_LINE1], found[CONF_DISPLAY_LINE2] = texts
    if CONF_POWER_ENTITY not in found and len(switches) == 1:
        found[CONF_POWER_ENTITY] = switches[0]
    return found


# ----- unit data ---------------------------------------------------------------------

_MACHINE_ONLY = (CONF_MACHINE_TYPE, CONF_MIN_BALANCE, CONF_SHUTDOWN_TIME, CONF_INTERLOCK_1, CONF_INTERLOCK_2)


class UnitFormError(ValueError):
    """Invalid unit form; `key` is a translation key (unit_exists, no_power_target, ...)."""

    def __init__(self, key: str) -> None:
        super().__init__(key)
        self.key = key


def build_unit_data(
    form: Mapping[str, Any],
    current: Mapping[str, Any] | None = None,
    detected: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Merge a panel form into unit data (subentry data without the name).

    `current` is the stored data when editing. `detected` are the reader's entities
    (classify_entities); they fill what is still missing, so switching door -> machine
    brings the safety switches back.
    """
    detected = detected or {}
    data: dict[str, Any] = dict(current or {})
    kind = form.get(CONF_KIND) or data.get(CONF_KIND) or KIND_MACHINE
    if kind not in (KIND_MACHINE, KIND_DOOR):
        raise UnitFormError("invalid_kind")
    data[CONF_KIND] = kind
    data[CONF_UNIT_ID] = int(form.get(CONF_UNIT_ID, data.get(CONF_UNIT_ID)))
    if not 1 <= data[CONF_UNIT_ID] <= 99999:
        raise UnitFormError("invalid_unit_id")
    data[CONF_READER_DEVICE] = form.get(CONF_READER_DEVICE) or data.get(CONF_READER_DEVICE)
    if not data[CONF_READER_DEVICE]:
        raise UnitFormError("no_reader")

    # Hardware: what is set stays, otherwise the detected entity.
    for key in (CONF_DISPLAY_LINE1, CONF_DISPLAY_LINE2):
        if not data.get(key) and detected.get(key):
            data[key] = detected[key]
    power = form.get(CONF_POWER_ENTITY) or data.get(CONF_POWER_ENTITY) or detected.get(CONF_POWER_ENTITY)
    if not power:
        raise UnitFormError("no_power_target")
    data[CONF_POWER_ENTITY] = power

    if kind == KIND_DOOR:
        for key in _MACHINE_ONLY:
            data.pop(key, None)
        data[CONF_PULSE_TIME] = float(form.get(CONF_PULSE_TIME) or data.get(CONF_PULSE_TIME) or DEFAULT_PULSE_TIME)
    else:
        data.pop(CONF_PULSE_TIME, None)
        for key in (CONF_INTERLOCK_1, CONF_INTERLOCK_2):
            if not data.get(key) and detected.get(key):
                data[key] = detected[key]
        machine_type = form.get(CONF_MACHINE_TYPE) or data.get(CONF_MACHINE_TYPE) or "machine"
        if machine_type not in MACHINE_TYPES:
            raise UnitFormError("invalid_machine_type")
        data[CONF_MACHINE_TYPE] = machine_type
        data[CONF_MIN_BALANCE] = float(
            form.get(CONF_MIN_BALANCE) if form.get(CONF_MIN_BALANCE) is not None
            else data.get(CONF_MIN_BALANCE, DEFAULT_MIN_BALANCE)
        )
        # Empty means "default of the machine type" (hub), so it is not stored.
        shutdown = form.get(CONF_SHUTDOWN_TIME, data.get(CONF_SHUTDOWN_TIME))
        if shutdown in (None, ""):
            data.pop(CONF_SHUTDOWN_TIME, None)
        else:
            data[CONF_SHUTDOWN_TIME] = float(shutdown)
    return data
