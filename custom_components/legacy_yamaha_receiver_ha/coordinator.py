"""Coordinator for the legacy Yamaha receiver integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class YamahaUpdateCoordinator(DataUpdateCoordinator[None]):
    """Coordinate Yamaha receiver zone state updates."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, config_entry: ConfigEntry, receiver
    ) -> None:
        """Initialize the coordinator."""
        self.receiver = receiver
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name="YamahaReceiverTest",
            update_interval=timedelta(seconds=5),
            always_update=True,
        )

    async def _async_update_data(self) -> None:
        """Refresh the Yamaha receiver zone state."""
        await self.receiver.update_zones_statuses()
