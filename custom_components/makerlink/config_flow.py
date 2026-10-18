"""Config flow for MakerLink: hub (backend) + units (machines/doors) as subentries."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
    DOMAIN,
    KIND_MACHINE,
    KINDS,
    MACHINE_TYPES,
    SUBENTRY_UNIT,
)
from .mars_format import MarsAuthError, MarsError

_LOGGER = logging.getLogger(__name__)

POWER_DOMAINS = ["switch", "light", "input_boolean"]
OPTIONAL_HW_FIELDS = (
    CONF_DISPLAY_LINE1,
    CONF_DISPLAY_LINE2,
    CONF_INTERLOCK_1,
    CONF_INTERLOCK_2,
)


async def _validate(hass, data: dict[str, Any]) -> dict[str, str]:
    api = MarsApiClient(
        async_get_clientsession(hass, verify_ssl=data[CONF_VERIFY_SSL]),
        data[CONF_API_URL],
        data[CONF_API_KEY],
        data[CONF_VERIFY_SSL],
    )
    try:
        await api.validate()
    except MarsAuthError:
        return {"base": "invalid_auth"}
    except MarsError as err:
        _LOGGER.warning("MARS backend check failed: %s", err)
        return {"base": "cannot_connect"}
    return {}


def _hub_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_API_URL, default=defaults.get(CONF_API_URL, "")): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
            ),
            vol.Required(CONF_API_KEY, default=defaults.get(CONF_API_KEY, "")): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Required(CONF_VERIFY_SSL, default=defaults.get(CONF_VERIFY_SSL, True)): bool,
        }
    )


class MakerLinkConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up the connection to the MARS backend."""

    VERSION = 1

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {SUBENTRY_UNIT: UnitSubentryFlow}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match({CONF_API_URL: user_input[CONF_API_URL]})
            errors = await _validate(self.hass, user_input)
            if not errors:
                return self.async_create_entry(title="MakerLink", data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=_hub_schema(user_input or {}), errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await _validate(self.hass, user_input)
            if not errors:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_hub_schema(user_input or dict(entry.data)),
            errors=errors,
        )


def _entity(domain: str | list[str]) -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=domain))


def _number(
    min_v: float, max_v: float, step: float, unit: str | None = None
) -> selector.NumberSelector:
    config = selector.NumberSelectorConfig(
        min=min_v, max=max_v, step=step, mode=selector.NumberSelectorMode.BOX
    )
    if unit:
        config["unit_of_measurement"] = unit
    return selector.NumberSelector(config)


class UnitSubentryFlow(ConfigSubentryFlow):
    """Add or reconfigure a machine or door."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    # ----- step 1: what ------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_UNIT_ID] = int(user_input[CONF_UNIT_ID])
            if self._unit_id_taken(user_input[CONF_UNIT_ID]):
                errors[CONF_UNIT_ID] = "unit_exists"
            else:
                self._data = user_input
                return await self.async_step_hardware()

        schema = vol.Schema(
            {
                vol.Required("name"): str,
                vol.Required(CONF_KIND, default=KIND_MACHINE): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=KINDS, translation_key="kind")
                ),
                vol.Required(CONF_UNIT_ID): _number(1, 99999, 1),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )

    # ----- step 2: which hardware --------------------------------------------------

    async def async_step_hardware(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        is_reconfigure = self.source == SOURCE_RECONFIGURE
        errors: dict[str, str] = {}
        if user_input is not None:
            # Optional fields left empty are missing from user_input: drop old values.
            base = {k: v for k, v in self._data.items() if k not in OPTIONAL_HW_FIELDS}
            data = {**base, **user_input}
            title = data.pop("name")
            if self._reader_taken(data[CONF_READER_DEVICE]):
                errors[CONF_READER_DEVICE] = "reader_in_use"
            elif is_reconfigure:
                return self.async_update_and_abort(
                    self._get_entry(), self._get_reconfigure_subentry(), title=title, data=data
                )
            else:
                return self.async_create_entry(
                    title=title, data=data, unique_id=f"unit_{data[CONF_UNIT_ID]}"
                )

        kind = self._data[CONF_KIND]
        fields: dict[Any, Any] = {
            vol.Required(CONF_READER_DEVICE): selector.DeviceSelector(),
            vol.Optional(CONF_DISPLAY_LINE1): _entity("text"),
            vol.Optional(CONF_DISPLAY_LINE2): _entity("text"),
            vol.Required(CONF_POWER_ENTITY): _entity(POWER_DOMAINS),
        }
        suggested: dict[str, Any] = dict(user_input or self._data)
        if kind == KIND_MACHINE:
            fields[vol.Optional(CONF_INTERLOCK_1)] = _entity("binary_sensor")
            fields[vol.Optional(CONF_INTERLOCK_2)] = _entity("binary_sensor")
            if not is_reconfigure:
                fields[vol.Required(CONF_MACHINE_TYPE, default="machine")] = selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=MACHINE_TYPES, translation_key="machine_type"
                    )
                )
                fields[vol.Required(CONF_MIN_BALANCE, default=DEFAULT_MIN_BALANCE)] = _number(
                    -100, 1000, 0.5, "EUR"
                )
                fields[vol.Optional(CONF_SHUTDOWN_TIME)] = _number(0, 3600, 1, "s")
        elif not is_reconfigure:
            fields[vol.Required(CONF_PULSE_TIME, default=DEFAULT_PULSE_TIME)] = _number(
                0.5, 30, 0.5, "s"
            )

        return self.async_show_form(
            step_id="hardware",
            data_schema=self.add_suggested_values_to_schema(vol.Schema(fields), suggested),
            errors=errors,
            description_placeholders={"name": self._data.get("name", "")},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        subentry = self._get_reconfigure_subentry()
        self._data = {**subentry.data, "name": subentry.title}
        return await self.async_step_hardware()

    # ----- helpers -----------------------------------------------------------------

    def _others(self):
        current = (
            self._get_reconfigure_subentry().subentry_id
            if self.source == SOURCE_RECONFIGURE
            else None
        )
        return [
            s
            for s in self._get_entry().subentries.values()
            if s.subentry_type == SUBENTRY_UNIT and s.subentry_id != current
        ]

    def _unit_id_taken(self, unit_id: int) -> bool:
        return any(int(s.data[CONF_UNIT_ID]) == unit_id for s in self._others())

    def _reader_taken(self, device_id: str) -> bool:
        return any(s.data.get(CONF_READER_DEVICE) == device_id for s in self._others())

