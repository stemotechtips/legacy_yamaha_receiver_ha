"""Config flow for the legacy Yamaha receiver integration."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.components.ssdp import (
    async_get_discovery_info_by_st,
    async_get_discovery_info_by_udn,
)
from homeassistant.helpers.selector import SelectSelector, TextSelector

from legacy_yamaha_receiver.receiver_system import get_receiver_details

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_MANUAL_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


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
    _ssdp_devices: dict[str, dict[str, str]]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the setup method menu."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["manual", "auto_detect"],
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual host entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input[CONF_HOST].strip():
                errors["base"] = "host_required"
            else:
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
            step_id="manual",
            data_schema=STEP_MANUAL_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_auto_detect(
        self, user_input: None = None
    ) -> ConfigFlowResult:
        """Search for Yamaha receivers advertised over SSDP."""
        self._ssdp_devices = await self._async_find_ssdp_devices()
        if not self._ssdp_devices:
            return self.async_show_form(
                step_id="manual",
                data_schema=STEP_MANUAL_DATA_SCHEMA,
                errors={"base": "no_receivers_found"},
            )
        return await self.async_step_ssdp()

    async def _async_find_ssdp_devices(self) -> dict[str, dict[str, str]]:
        """Return cached SSDP devices advertised by Yamaha."""
        devices: dict[str, dict[str, str]] = {}
        root_devices = await async_get_discovery_info_by_st(
            self.hass, "upnp:rootdevice"
        )
        for root_info in root_devices:
            if not root_info.ssdp_udn:
                continue

            for info in await async_get_discovery_info_by_udn(
                self.hass, root_info.ssdp_udn
            ):
                manufacturer = str(info.upnp.get("manufacturer", "")).strip()
                if manufacturer != "YAMAHA CORPORATION":
                    continue

                search_target = str(info.ssdp_st or "")
                if "yamaharemotecontrol" not in search_target.lower():
                    continue

                presentation_url = str(info.upnp.get("presentationURL", "")).strip()
                hostname = urlsplit(presentation_url).hostname
                if not hostname:
                    continue

                devices[info.ssdp_udn] = {
                    "model_name": str(info.upnp.get("modelName", "Unknown model")),
                    "serial_number": str(
                        info.upnp.get("serialNumber", "Unknown serial number")
                    ),
                    "presentation_url": presentation_url,
                    "host": hostname,
                }
        return devices

    async def async_step_ssdp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user select a Yamaha receiver found over SSDP."""
        if user_input is not None:
            device = self._ssdp_devices[user_input["device"]]
            try:
                info = await validate_input(
                    self.hass, {CONF_HOST: device["host"]}
                )
            except InvalidConfiguration:
                return self.async_show_form(
                    step_id="ssdp",
                    data_schema=self._ssdp_schema(),
                    errors={"base": "invalid_configuration"},
                )

            self._receiver_data = {
                **device,
                **info,
                "ssdp": True,
            }
            return await self.async_step_confirm()

        return self.async_show_form(
            step_id="ssdp",
            data_schema=self._ssdp_schema(),
        )

    def _ssdp_schema(self) -> vol.Schema:
        """Return the selector for discovered Yamaha receivers."""
        options = [
            {
                "value": identifier,
                "label": (
                    f"{device['model_name']} | {device['serial_number']} | "
                    f"{device['presentation_url']}"
                ),
            }
            for identifier, device in self._ssdp_devices.items()
        ]
        return vol.Schema(
            {vol.Required("device"): SelectSelector({"options": options})}
        )

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user to confirm the detected receiver details."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._receiver_data["title"],
                data={CONF_HOST: self._receiver_data[CONF_HOST]},
            )

        return self.async_show_form(
            step_id="confirm",
            data_schema=self._confirmation_schema(),
        )

    def _confirmation_schema(self) -> vol.Schema:
        """Return read-only fields for the detected receiver."""
        if self._receiver_data.get("ssdp"):
            return vol.Schema(
                {
                    vol.Required(
                        "model_name", default=self._receiver_data["model_name"]
                    ): TextSelector({"read_only": True}),
                    vol.Required(
                        "serial_number", default=self._receiver_data["serial_number"]
                    ): TextSelector({"read_only": True}),
                    vol.Required(
                        "presentation_url",
                        default=self._receiver_data["presentation_url"],
                    ): TextSelector({"read_only": True}),
                    vol.Required(
                        "system_id", default=self._receiver_data["system_id"]
                    ): TextSelector({"read_only": True}),
                    vol.Required(
                        "firmware_version",
                        default=self._receiver_data["firmware_version"],
                    ): TextSelector({"read_only": True}),
                }
            )
        return vol.Schema(
            {
                vol.Required(
                    "model_name", default=self._receiver_data["model_name"]
                ): TextSelector({"read_only": True}),
                vol.Required(
                    "system_id", default=self._receiver_data["system_id"]
                ): TextSelector({"read_only": True}),
                vol.Required(
                    "firmware_version",
                    default=self._receiver_data["firmware_version"],
                ): TextSelector({"read_only": True}),
            }
        )


class InvalidConfiguration(Exception):
    """Error to indicate the receiver could not be configured."""
