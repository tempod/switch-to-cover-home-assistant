"""Platform for cover integration."""
import asyncio
from typing import Any
from datetime import timedelta

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
    ATTR_POSITION,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant, callback, State
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

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
        
        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
            | CoverEntityFeature.STOP
        )

        self._open_switch_entity_id = self._config[CONF_OPEN_SWITCH]
        self._close_switch_entity_id = self._config[CONF_CLOSE_SWITCH]
        self._opening_time = float(self._config[CONF_OPENING_TIME])
        self._closing_time = float(self._config[CONF_CLOSING_TIME])
        self._delay_start = float(self._config[CONF_DELAY_START])
        self._delay_stop = float(self._config[CONF_DELAY_STOP])

        self._attr_is_opening = False
        self._attr_is_closing = False
        
        self._current_position = 0
        self._target_position = 0
        self._last_update_time = dt_util.utcnow()
        
        self._cancel_timer = None
        self._update_unsub = None # Per il timer di aggiornamento periodico

    @callback
    def _async_switch_state_changed(self, event) -> None:
        """Handle switch state changes."""
        new_state = event.data.get("new_state")
        entity_id = event.data.get("entity_id")
        
        if new_state is None:
            return

        if new_state.state == STATE_ON:
            if (entity_id == self._open_switch_entity_id and self._attr_is_opening) or \
               (entity_id == self._close_switch_entity_id and self._attr_is_closing):
                return
            
            if entity_id == self._open_switch_entity_id:
                self.hass.async_create_task(self.async_open_cover())
            elif entity_id == self._close_switch_entity_id:
                self.hass.async_create_task(self.async_close_cover())

        elif new_state.state == STATE_OFF:
            if (entity_id == self._open_switch_entity_id and self._attr_is_opening) or \
               (entity_id == self._close_switch_entity_id and self._attr_is_closing):
                self.hass.async_create_task(self.async_stop_cover())

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._open_switch_entity_id, self._close_switch_entity_id],
                self._async_switch_state_changed,
            )
        )
    
    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        return self._current_position <= 0

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover."""
        if self._attr_is_opening or self._attr_is_closing:
            elapsed_time = (dt_util.utcnow() - self._last_update_time).total_seconds()
            
            if self._attr_is_opening:
                pos_change = (elapsed_time / self._opening_time) * 100
                new_pos = self._start_position + pos_change
                return min(100, int(new_pos))
                
            if self._attr_is_closing:
                pos_change = (elapsed_time / self._closing_time) * 100
                new_pos = self._start_position - pos_change
                return max(0, int(new_pos))

        return self._current_position

    async def _call_switch_service(self, service: str, entity_id: str) -> None:
        """Call a service for a switch or input_boolean."""
        domain = entity_id.split('.')[0]
        await self.hass.services.async_call(
            domain, service, {"entity_id": entity_id}, blocking=False
        )

    # ## MODIFICA: Aggiunto un callback per forzare l'aggiornamento ##
    @callback
    def _async_update_position_callback(self, now=None) -> None:
        """Callback to force a position update in the UI."""
        self.async_write_ha_state()

    async def _start_movement(self, direction: str, duration: float):
        """Handle the start of a movement."""
        await self.async_stop_cover() # Ferma qualsiasi movimento precedente

        self._current_position = self.current_cover_position

        self._attr_is_opening = (direction == "open")
        self._attr_is_closing = (direction == "close")
        self._last_update_time = dt_util.utcnow()
        self._start_position = self._current_position
        self.async_write_ha_state()

        opposite_switch = self._close_switch_entity_id if direction == "open" else self._open_switch_entity_id
        await self._call_switch_service(SERVICE_TURN_OFF, opposite_switch)
        
        await asyncio.sleep(self._delay_start)

        active_switch = self._open_switch_entity_id if direction == "open" else self._close_switch_entity_id
        await self._call_switch_service(SERVICE_TURN_ON, active_switch)

        self._cancel_timer = async_call_later(
            self.hass, duration, self._async_movement_finished
        )
        # ## MODIFICA: Avvia il timer di aggiornamento periodico ##
        self._update_unsub = async_track_time_interval(
            self.hass, self._async_update_position_callback, timedelta(seconds=1)
        )


    @callback
    def _async_movement_finished(self, *args) -> None:
        """Callback when movement is finished."""
        # ## MODIFICA: Ferma il timer di aggiornamento periodico ##
        if self._update_unsub:
            self._update_unsub()
            self._update_unsub = None
        
        async def finish_movement():
            active_switch = self._open_switch_entity_id if self._attr_is_opening else self._close_switch_entity_id
            
            await asyncio.sleep(self._delay_stop)
            await self._call_switch_service(SERVICE_TURN_OFF, active_switch)
            
            self._current_position = self._target_position
            self._attr_is_opening = False
            self._attr_is_closing = False
            self._cancel_timer = None
            self.async_write_ha_state()

        self.hass.async_create_task(finish_movement())

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        if self._attr_is_opening: return
        self._target_position = 100
        current_pos = self.current_cover_position
        travel_time = self._opening_time * (100 - current_pos) / 100
        if travel_time > 0.1:
            await self._start_movement("open", travel_time)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close cover."""
        if self._attr_is_closing: return
        self._target_position = 0
        current_pos = self.current_cover_position
        travel_time = self._closing_time * current_pos / 100
        if travel_time > 0.1:
            await self._start_movement("close", travel_time)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        target_position = kwargs[ATTR_POSITION]
        current_position = self.current_cover_position
        
        travel_time = 0
        direction = ""

        if target_position > current_position:
            direction = "open"
            self._target_position = target_position
            travel_percentage = (target_position - current_position) / 100.0
            travel_time = self._opening_time * travel_percentage
        elif target_position < current_position:
            direction = "close"
            self._target_position = target_position
            travel_percentage = (current_position - target_position) / 100.0
            travel_time = self._closing_time * travel_percentage
        
        if travel_time > 0.1:
            await self._start_movement(direction, travel_time)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        if not self._attr_is_opening and not self._attr_is_closing:
            return
            
        # ## MODIFICA: Ferma tutti i timer ##
        if self._cancel_timer:
            self._cancel_timer()
            self._cancel_timer = None
        if self._update_unsub:
            self._update_unsub()
            self._update_unsub = None

        self._current_position = self.current_cover_position
        
        await self._call_switch_service(SERVICE_TURN_OFF, self._open_switch_entity_id)
        await self._call_switch_service(SERVICE_TURN_OFF, self._close_switch_entity_id)
        
        self._attr_is_opening = False
        self._attr_is_closing = False
        self.async_write_ha_state()
