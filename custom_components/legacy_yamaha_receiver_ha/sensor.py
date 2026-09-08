"""Sensor platform for the Yamaha receiver metadata."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import YamahaUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Yamaha receiver metadata sensor."""
    coordinator: YamahaUpdateCoordinator = config_entry.runtime_data
    async_add_entities([YamahaReceiverSensor(coordinator, coordinator.receiver)])


class YamahaReceiverSensor(SensorEntity):
    """Expose Yamaha receiver characteristics as a sensor."""

    _attr_has_entity_name = True
    _attr_name = "Receiver"
    _attr_should_poll = False

    def __init__(self, coordinator: YamahaUpdateCoordinator, receiver) -> None:
        """Initialize the receiver sensor."""
        self.coordinator = coordinator
        self.receiver = receiver
        self._attr_unique_id = (
            f"{receiver.system_ID}_receiver_metadata"
            if receiver.system_ID
            else "yamaha_receiver_metadata"
        )

    @property
    def native_value(self) -> str:
        """Return the receiver model name as the sensor value."""
        return self.receiver.model_name or "Unknown model"

    @property
    def extra_state_attributes(self) -> dict[str, str | bool]:
        """Return the receiver characteristics as attributes."""
        return {
            "model_name": self.receiver.model_name,
            "system_id": self.receiver.system_ID,
            "firmware_version": self.receiver.firmware_version,
            "ip_address": self.receiver.ip_address,
            "valid_setup": self.receiver.valid_setup,
            "zone_count": 3,
            "available_inputs": self.receiver.available_inputs,
        }
