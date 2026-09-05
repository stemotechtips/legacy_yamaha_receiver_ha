"""The legacy Yamaha receiver integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import YamahaUpdateCoordinator
from legacy_yamaha_receiver import Receiver
from homeassistant.helpers.aiohttp_client import async_get_clientsession


PLATFORMS = [Platform.MEDIA_PLAYER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the legacy Yamaha receiver integration from a config entry."""
    receiver_url = f"http://{entry.data['host']}/YamahaRemoteControl/ctrl"
    session = async_get_clientsession(hass)

    receiver = await Receiver.async_create(session, receiver_url)
    coordinator = YamahaUpdateCoordinator(hass, entry, receiver)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
