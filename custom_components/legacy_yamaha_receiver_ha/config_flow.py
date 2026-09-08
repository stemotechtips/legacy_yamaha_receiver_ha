"""Config flow for the legacy Yamaha receiver integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from legacy_yamaha_receiver.receiver_system import get_receiver_details

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


async def validate_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Retrieve and validate the receiver details for a host."""
    receiver_url = f"http://{data[CONF_HOST]}/YamahaRemoteControl/ctrl"
    session = async_get_clientsession(hass)

    try:
        details = await get_receiver_details(session, receiver_url)
        assert len(details) == 3 and all(value is not None for value in details)
    except Exception as err:
        raise InvalidConfiguration from err

    model_name, system_id, firmware_version = details
    return {
        "title": f"Yamaha Receiver {data[CONF_HOST]}",
        "model_name": model_name,
        "system_id": system_id,
        "firmware_version": firmware_version,
    }


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the custom Yamaha receiver test."""

    VERSION = 1
    _receiver_data: dict[str, Any]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except InvalidConfiguration:
                errors["base"] = "invalid_configuration"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self._receiver_data = {**user_input, **info}
                return await self.async_step_confirm()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user to confirm the detected receiver details."""
        if user_input is not None:
            if not user_input["confirm"]:
                return self.async_show_form(
                    step_id="confirm",
                    data_schema=self._confirmation_schema(),
                    errors={"base": "confirmation_required"},
                )

            return self.async_create_entry(
                title=self._receiver_data["title"],
                data={CONF_HOST: self._receiver_data[CONF_HOST]},
            )

        return self.async_show_form(
            step_id="confirm",
            data_schema=self._confirmation_schema(),
        )

    def _confirmation_schema(self) -> vol.Schema:
        """Return the form schema containing the detected receiver details."""
        return vol.Schema(
            {
                vol.Required(
                    "model_name", default=self._receiver_data["model_name"]
                ): str,
                vol.Required(
                    "system_id", default=self._receiver_data["system_id"]
                ): str,
                vol.Required(
                    "firmware_version",
                    default=self._receiver_data["firmware_version"],
                ): str,
                vol.Required("confirm", default=False): bool,
            }
        )


class InvalidConfiguration(Exception):
    """Error to indicate the receiver could not be configured."""
