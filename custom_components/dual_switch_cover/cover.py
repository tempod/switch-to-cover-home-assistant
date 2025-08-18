"""Platform for cover integration."""
import asyncio
from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_CLOSE_SWITCH,
    CONF_CLOSING_TIME,
    CONF_DELAY_START,
    CONF_DELAY_STOP,
    CONF_NAME,
    CONF_OPEN_SWITCH,
    CONF_OPENING_TIME,
    DOMAIN,
)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the cover platform."""
    async_add_entities([DualSwitchCover(hass, config_entry)])


class DualSwitchCover(CoverEntity):
    """Representation of a Dual Switch Cover."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the cover."""
        self.hass = hass
        self._config = config_entry.data
        self._attr_unique_id = config_entry.entry_id
        self._attr_name = self._config[CONF_NAME]
        self._attr_device_class = CoverDeviceClass.SHUTTER
        self._attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

        self._open_switch_entity_id = self._config[CONF_OPEN_SWITCH]
        self._close_switch_entity_id = self._config[CONF_CLOSE_SWITCH]
        self._opening_time = self._config[CONF_OPENING_TIME]
        self._closing_time = self._config[CONF_CLOSING_TIME]
        self._delay_start = self._config[CONF_DELAY_START]
        self._delay_stop = self._config[CONF_DELAY_STOP]

        self._attr_is_opening = False
        self._attr_is_closing = False
        self._attr_is_closed = True  # Assume it's closed on startup
        
        self._cancel_timer = None


    async def _call_switch_service(self, service: str, entity_id: str) -> None:
        """Call a service for a switch or input_boolean."""
        domain = entity_id.split('.')[0]
        await self.hass.services.async_call(
            domain, service, {"entity_id": entity_id}, blocking=True
        )

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        if self._attr_is_opening or self._attr_is_closing:
            return
        
        if self._cancel_timer:
            self._cancel_timer()

        self._attr_is_opening = True
        self.async_write_ha_state()

        # Safety: ensure close switch is off
        await self._call_switch_service(SERVICE_TURN_OFF, self._close_switch_entity_id)
        
        # Start delay
        await asyncio.sleep(self._delay_start)

        await self._call_switch_service(SERVICE_TURN_ON, self._open_switch_entity_id)

        self._cancel_timer = self.hass.async_call_later(self._opening_time, self._async_open_finished)

    @callback
    def _async_open_finished(self, *args) -> None:
        """Callback when opening is finished."""
        async def finish_open():
            # Stop delay
            await asyncio.sleep(self._delay_stop)
            await self._call_switch_service(SERVICE_TURN_OFF, self._open_switch_entity_id)
            self._attr_is_opening = False
            self._attr_is_closed = False
            self.async_write_ha_state()
        
        self.hass.async_create_task(finish_open())

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        if self._attr_is_closing or self._attr_is_opening:
            return

        if self._cancel_timer:
            self._cancel_timer()
        
        self._attr_is_closing = True
        self.async_write_ha_state()

        # Safety: ensure open switch is off
        await self._call_switch_service(SERVICE_TURN_OFF, self._open_switch_entity_id)
        
        # Start delay
        await asyncio.sleep(self._delay_start)
        
        await self._call_switch_service(SERVICE_TURN_ON, self._close_switch_entity_id)

        self._cancel_timer = self.hass.async_call_later(self._closing_time, self._async_close_finished)
    
    @callback
    def _async_close_finished(self, *args) -> None:
        """Callback when closing is finished."""
        async def finish_close():
            # Stop delay
            await asyncio.sleep(self._delay_stop)
            await self._call_switch_service(SERVICE_TURN_OFF, self._close_switch_entity_id)
            self._attr_is_closing = False
            self._attr_is_closed = True
            self.async_write_ha_state()

        self.hass.async_create_task(finish_close())

    # This integration does not support the stop command as per the request.
    # Therefore, async_stop_cover is not implemented.