"""Constants for MakerLink (no Home Assistant imports, see CLAUDE.md)."""

from __future__ import annotations

DOMAIN = "makerlink"

# Hub (config entry)
CONF_API_URL = "api_url"
CONF_API_KEY = "api_key"
CONF_VERIFY_SSL = "verify_ssl"

# Unit (config subentry)
SUBENTRY_UNIT = "unit"
CONF_KIND = "kind"
CONF_UNIT_ID = "unit_id"
CONF_MACHINE_TYPE = "machine_type"
CONF_READER_DEVICE = "reader_device"
CONF_DISPLAY_LINE1 = "display_line1"
CONF_DISPLAY_LINE2 = "display_line2"
CONF_POWER_ENTITY = "power_entity"
CONF_INTERLOCK_1 = "interlock_1"
CONF_INTERLOCK_2 = "interlock_2"
CONF_MIN_BALANCE = "min_balance"
CONF_SHUTDOWN_TIME = "shutdown_time"
CONF_PULSE_TIME = "pulse_time"

KIND_MACHINE = "machine"
KIND_DOOR = "door"
KINDS = [KIND_MACHINE, KIND_DOOR]

MACHINE_TYPES = ["machine", "laser", "3dprint", "dtf", "kiln"]

DEFAULT_MIN_BALANCE = 5.0
DEFAULT_SHUTDOWN_TIME = 0
DEFAULT_SHUTDOWN_TIME_BY_TYPE = {"3dprint": 60}
DEFAULT_PULSE_TIME = 3.0

# Timings (seconds), taken over from the legacy firmware
CARD_COOLDOWN = 5
MESSAGE_TIME = 3
STOP_SCREEN_TIME = 5
DOOR_LOG_DELAY = 2.0

# Events
EVENT_READER_TAG = "esphome.makerlink_tag"
EVENT_TAG_SCANNED = "tag_scanned"
EVENT_SESSION_STARTED = f"{DOMAIN}_session_started"
EVENT_SESSION_STOPPED = f"{DOMAIN}_session_stopped"
EVENT_CARD_REJECTED = f"{DOMAIN}_card_rejected"
EVENT_DOOR_ACCESS = f"{DOMAIN}_door_access"

STORAGE_VERSION = 1
STORAGE_KEY = DOMAIN

ESPHOME_PROJECT_NAME = "makeraustria.makerlink_reader"
