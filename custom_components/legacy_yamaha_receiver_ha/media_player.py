"""Media player entities for each Yamaha receiver zone."""

from __future__ import annotations

import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from legacy_yamaha_receiver import Audio_Setting_Type, Input_Type, Zone
from legacy_yamaha_receiver.helper_functions import round_to_nearest_five

from .coordinator import YamahaUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one HA media player per Yamaha zone."""
    coordinator: YamahaUpdateCoordinator = config_entry.runtime_data
    async_add_entities(
        [YamahaZoneEntity(coordinator, zone) for zone in coordinator.receiver.zones]
    )

class YamahaZoneEntity(CoordinatorEntity[YamahaUpdateCoordinator], MediaPlayerEntity):
    """Represent a Yamaha receiver zone as a Home Assistant media player."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_supported_features = (
        MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOURCE
        #| MediaPlayerEntityFeature.SELECT_SOUND_MODE
    )

    def __init__(self, coordinator: YamahaUpdateCoordinator, zone: Zone) -> None:
        """Initialize the zone entity."""
        super().__init__(coordinator)
        self._zone = zone
        self._attr_name = zone.zone_name.replace("_", " ")
        self._attr_unique_id = zone.zone_id
        if zone.zone_name == "Main_Zone":
            self._attr_supported_features = self._attr_supported_features | MediaPlayerEntityFeature.SELECT_SOUND_MODE

    @property
    def zone(self) -> Zone:
        """Return the underlying Yamaha zone."""
        return self._zone

    @property
    def receiver_ip(self) -> str:
        """Return the Yamaha receiver IP address from the coordinator-owned receiver."""
        return self.coordinator.receiver.ip_address

    @property
    def receiver(self):
        """Return the coordinator-owned Yamaha receiver."""
        return self.coordinator.receiver

    @property
    def state(self) -> MediaPlayerState:
        """Return the zone's power state."""
        return (
            MediaPlayerState.ON
            if getattr(self.zone, "is_on", False)
            else MediaPlayerState.OFF
        )

    @property
    def available(self) -> bool:
        """Return whether this zone is available."""
        return bool(getattr(self.zone, "exists", False))

    @property
    def source(self) -> str | None:
        """Return the current source/input for the zone."""
        input_status = getattr(self.zone, "input_status", None)
        if input_status is None:
            return None
        return getattr(input_status, "selected_input_title", None) or getattr(
            input_status, "selected_input", None
        )

    @property
    def sound_mode(self) -> str | None:
        """Return the current audio program for the zone."""
        audio_program = getattr(self.zone, "audio_program", None)
        if audio_program is None:
            return None
        return getattr(audio_program, "selected_audio_program", None)

    @property
    def volume_level(self) -> float | None:
        """Return the current volume as a normalized 0..1 value."""
        volume_status = getattr(self.zone, "volume_status", None)
        if volume_status is None:
            return None

        current = getattr(volume_status, "volume_level", None)
        if current is None:
            return None

        min_volume = -805
        max_volume = 165
        normalized = (current - min_volume) / (max_volume - min_volume)
        return max(0.0, min(1.0, normalized))

    @property
    def is_volume_muted(self) -> bool:
        """Return whether the zone is muted."""
        volume_status = getattr(self.zone, "volume_status", None)
        if volume_status is None:
            return False
        return bool(getattr(volume_status, "is_mute", False))

    @property
    def source_list(self) -> list[str] | None:
        """Return list of available input sources."""
        available_inputs = getattr(self.zone, "available_inputs", None)
        if available_inputs is None:
            return None
        return [input.value for input in available_inputs]

    @property
    def sound_mode_list(self) -> list[str] | None:
        """Return list of available audio settings."""
        audio_programs = getattr(self.zone, "available_audio_programs", None)
        if audio_programs is None:
            return None
        return [program.value for program in audio_programs]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        """Turn on the zone."""
        receiver = self.receiver
        if receiver is not None:
            await receiver.change_zone_power(self.zone, True)
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn off the zone."""
        receiver = self.receiver
        if receiver is not None:
            await receiver.change_zone_power(self.zone, False)
            await self.coordinator.async_request_refresh()

    async def async_set_volume_level(self, **kwargs) -> None:
        """Set the zone volume."""
        receiver = self.receiver
        if receiver is None:
            return

        min_volume = -805
        max_volume = 165
        new_volume = round(min_volume + (max_volume - min_volume) * kwargs.get("volume", 0))
        new_volume = round_to_nearest_five(new_volume)
        #We have to do this because the Yamaha receiver only accepts volume levels in increments of 5
        await receiver.change_zone_volume(self.zone, new_volume)
        await self.coordinator.async_request_refresh()

    async def async_set_volume_mute(self, mute: bool) -> None:
        """Mute or unmute the zone."""
        receiver = self.receiver
        zone = self.zone
        if receiver is not None and zone is not None:
            try:
                await receiver.change_zone_mute(zone, mute)
                await self.coordinator.async_request_refresh()
            except Exception as err:
                _LOGGER.error("Failed to set mute: %s", err)
        else:
            _LOGGER.warning("Cannot mute: receiver or zone is None")

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute the zone (service handler)."""
        # Home Assistant calls this with the desired mute state
        await self.async_set_volume_mute(mute)

    def mute_volume(self, mute: bool = True) -> None:
        """Mute or unmute the zone (sync version for service compatibility).

        This method exists to satisfy Home Assistant's MediaPlayerEntity interface.
        The actual implementation is in async_mute_volume.
        """

    async def async_select_source(self, source: str) -> None:
        """Select an input source for the zone."""
        receiver = self.receiver
        if receiver is None:
            return

        # Find the Input_Type enum value that matches the source name
        #available_inputs = getattr(self.zone, "available_inputs", [])
        #selected_input = None
        #for input_type in available_inputs:
        #    if input_type.name == source:
        #        selected_input = input_type
        #        break

        if Input_Type(source) is not None:
            await receiver.change_zone_input(self.zone, Input_Type(source))
            await self.coordinator.async_request_refresh()
        else:
            print(f"Source {source} not found in available inputs")

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        """Select an audio program for the zone."""
        receiver = self.receiver
        if receiver is None:
            return

        # Find the Audio_Program enum value that matches the audio program name
        #available_sound_modes = getattr(self.zone, "available_audio_programs", [])
        #selected_program = None
        #for program in available_sound_modes:
        #    if program.name == sound_mode:
        #        selected_program = program
        #        break

        try:
            Audio_Setting_Type(sound_mode)

            if Audio_Setting_Type(sound_mode) is not None:
                await receiver.change_zone_audio_setting(
                    self.zone, Audio_Setting_Type(sound_mode)
                )
                await self.coordinator.async_request_refresh()
            else:
                print(f"Sound mode {sound_mode} not found in available programs")
        except:
            print(f"Sound mode {sound_mode} not found in available programs")


    @property
    def unique_id(self) -> str:
        """Return a unique ID for the zone entity."""
        return self._attr_unique_id
