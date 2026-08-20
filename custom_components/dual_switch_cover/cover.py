"""Platform for the Dual Switch Cover integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.start import async_at_started
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CLOSE_SWITCH,
    CONF_CLOSING_TIME,
    CONF_DELAY_START,
    CONF_DELAY_STOP,
    CONF_DEVICE_CLASS,
    CONF_FULL_TRAVEL,
    CONF_NAME,
    CONF_OPEN_SWITCH,
    CONF_OPENING_TIME,
    DEFAULT_CLOSING_TIME,
    DEFAULT_DELAY_START,
    DEFAULT_DELAY_STOP,
    DEFAULT_DEVICE_CLASS,
    DEFAULT_FULL_TRAVEL,
    DEFAULT_NAME,
    DEFAULT_OPENING_TIME,
    DOMAIN,
    MIN_TRAVEL_TIME,
    POSITION_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

DIRECTION_OPEN = "open"
DIRECTION_CLOSE = "close"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the cover platform."""
    async_add_entities([DualSwitchCover(config_entry)])


class DualSwitchCover(CoverEntity, RestoreEntity):
    """A cover driven by two switches (open / close)."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the cover."""
        config = {**config_entry.data, **config_entry.options}

        self._attr_unique_id = config_entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config.get(CONF_NAME, config_entry.title or DEFAULT_NAME),
            manufacturer="Dual Switch Cover",
            model="Cover da due interruttori",
        )

        try:
            self._attr_device_class = CoverDeviceClass(
                config.get(CONF_DEVICE_CLASS, DEFAULT_DEVICE_CLASS)
            )
        except ValueError:
            self._attr_device_class = CoverDeviceClass.SHUTTER

        self._open_switch: str = config[CONF_OPEN_SWITCH]
        self._close_switch: str = config[CONF_CLOSE_SWITCH]

        # I tempi non possono essere zero: eviterebbero una divisione per zero
        # nel calcolo della posizione.
        self._opening_time = max(
            0.5, float(config.get(CONF_OPENING_TIME, DEFAULT_OPENING_TIME))
        )
        self._closing_time = max(
            0.5, float(config.get(CONF_CLOSING_TIME, DEFAULT_CLOSING_TIME))
        )
        self._delay_start = float(config.get(CONF_DELAY_START, DEFAULT_DELAY_START))
        self._delay_stop = float(config.get(CONF_DELAY_STOP, DEFAULT_DELAY_STOP))
        self._full_travel = bool(config.get(CONF_FULL_TRAVEL, DEFAULT_FULL_TRAVEL))

        self._attr_is_opening = False
        self._attr_is_closing = False

        self._current_position: int = 0
        self._start_position: int = 0
        self._target_position: int = 0
        self._move_start_time = None

        # Handle dei timer e del task in corso, tutti cancellabili.
        self._cancel_finish = None
        self._cancel_updates = None
        self._action_task: asyncio.Task | None = None

        # Stato che ci aspettiamo dai due rele' in base ai comandi che abbiamo
        # inviato noi: serve a distinguere l'eco dei nostri comandi dai comandi
        # impartiti fisicamente dall'utente.
        self._expected_states: dict[str, str] = {
            self._open_switch: STATE_OFF,
            self._close_switch: STATE_OFF,
        }

    # ------------------------------------------------------------------
    # Ciclo di vita
    # ------------------------------------------------------------------

    async def async_added_to_hass(self) -> None:
        """Restore the last known position and start listening."""
        await super().async_added_to_hass()

        if (last_state := await self.async_get_last_state()) is not None:
            last_position = last_state.attributes.get(ATTR_CURRENT_POSITION)
            if last_position is not None:
                try:
                    self._current_position = max(0, min(100, int(float(last_position))))
                except (TypeError, ValueError):
                    _LOGGER.debug("Posizione ripristinata non valida: %s", last_position)

        self._start_position = self._current_position
        self._target_position = self._current_position

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._open_switch, self._close_switch],
                self._async_switch_state_changed,
            )
        )

        # Il controllo di sicurezza va fatto quando tutte le altre integrazioni
        # sono pronte, altrimenti gli switch potrebbero non esistere ancora.
        self.async_on_remove(async_at_started(self.hass, self._async_ha_started))

    @callback
    def _async_ha_started(self, _hass: HomeAssistant) -> None:
        """Home Assistant has finished starting up."""
        self.hass.async_create_task(self._async_sync_switches())

    async def _async_sync_switches(self) -> None:
        """Align the expected relay states with reality after a restart."""
        active: list[str] = []

        for entity_id in (self._open_switch, self._close_switch):
            state = self.hass.states.get(entity_id)
            if state is None:
                _LOGGER.warning(
                    "L'entita' %s non esiste: la cover %s non potra' funzionare",
                    entity_id,
                    self.entity_id,
                )
                self._expected_states[entity_id] = STATE_OFF
                continue

            self._expected_states[entity_id] = state.state
            if state.state == STATE_ON:
                active.append(entity_id)

        if not active:
            return

        # Un rele' acceso all'avvio significa che Home Assistant si e' riavviato
        # durante una corsa: la posizione salvata non e' piu' attendibile.
        _LOGGER.warning(
            "%s: %s risultava attivo all'avvio, i rele' vengono spenti. "
            "La posizione potrebbe essere imprecisa finche' non si esegue "
            "un'apertura o una chiusura completa",
            self.entity_id,
            ", ".join(active),
        )
        for entity_id in active:
            await self._async_call_switch(SERVICE_TURN_OFF, entity_id)

    async def async_will_remove_from_hass(self) -> None:
        """Cancel every pending timer before the entity goes away."""
        self._cancel_timers()
        if self._action_task and not self._action_task.done():
            self._action_task.cancel()
        self._action_task = None
        await super().async_will_remove_from_hass()

    # ------------------------------------------------------------------
    # Proprieta'
    # ------------------------------------------------------------------

    @property
    def current_cover_position(self) -> int:
        """Return the current position, extrapolated while moving."""
        if self._move_start_time is None:
            return self._current_position

        elapsed = (dt_util.utcnow() - self._move_start_time).total_seconds()

        if self._attr_is_opening:
            position = self._start_position + (elapsed / self._opening_time) * 100
        elif self._attr_is_closing:
            position = self._start_position - (elapsed / self._closing_time) * 100
        else:
            return self._current_position

        return max(0, min(100, round(position)))

    @property
    def is_closed(self) -> bool:
        """Return True if the cover is fully closed."""
        return self.current_cover_position <= 0

    # ------------------------------------------------------------------
    # Comandi provenienti da Home Assistant
    # ------------------------------------------------------------------

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self._async_move_to(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        await self._async_move_to(0)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        await self._async_move_to(int(kwargs[ATTR_POSITION]))

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self._async_abort_movement(
            switches_off=[self._open_switch, self._close_switch]
        )
        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Comandi provenienti dai pulsanti fisici
    # ------------------------------------------------------------------

    @callback
    def _async_switch_state_changed(self, event: Event[EventStateChangedData]) -> None:
        """React to a switch changing state."""
        entity_id = event.data["entity_id"]
        new_state = event.data["new_state"]

        if new_state is None or new_state.state not in (STATE_ON, STATE_OFF):
            return

        expected = self._expected_states.get(entity_id)
        self._expected_states[entity_id] = new_state.state

        # Se il nuovo stato e' quello che avevamo richiesto noi, si tratta
        # dell'eco del nostro stesso comando: va ignorato.
        if new_state.state == expected:
            return

        if new_state.state == STATE_ON:
            direction = (
                DIRECTION_OPEN if entity_id == self._open_switch else DIRECTION_CLOSE
            )
            self.hass.async_create_task(self._async_physical_command(direction))
            return

        # STATE_OFF: il comando fisico e' cessato, fermiamo la corsa.
        moving_switch = self._open_switch if self._attr_is_opening else (
            self._close_switch if self._attr_is_closing else None
        )
        if entity_id == moving_switch:
            self.hass.async_create_task(self.async_stop_cover())

    async def _async_physical_command(self, direction: str) -> None:
        """Track a movement started by a physical switch, without actuating it."""
        target = 100 if direction == DIRECTION_OPEN else 0
        full_time = (
            self._opening_time if direction == DIRECTION_OPEN else self._closing_time
        )

        duration = self._travel_time(self._current_position, target)
        # Se siamo gia' a fine corsa il calcolo darebbe zero, ma il rele' e'
        # comunque acceso: programmiamo comunque lo spegnimento.
        if duration < MIN_TRAVEL_TIME:
            duration = full_time

        await self._async_start_movement(direction, target, duration, actuate=False)

    # ------------------------------------------------------------------
    # Motore del movimento
    # ------------------------------------------------------------------

    def _travel_time(self, current: int, target: int) -> float:
        """Return how long the motor must run to go from current to target."""
        if target > current:
            full_time = self._opening_time
            if target >= 100 and self._full_travel:
                # Corsa piena a fine corsa: ri-sincronizza la posizione reale
                # e azzera la deriva accumulata.
                return full_time
            return full_time * (target - current) / 100

        if target < current:
            full_time = self._closing_time
            if target <= 0 and self._full_travel:
                return full_time
            return full_time * (current - target) / 100

        return 0.0

    async def _async_move_to(self, target: int) -> None:
        """Move the cover towards a target position."""
        target = max(0, min(100, target))
        current = self.current_cover_position
        duration = self._travel_time(current, target)

        if duration < MIN_TRAVEL_TIME:
            # Nulla da fare, ma assicuriamoci di non lasciare rele' attivi.
            await self.async_stop_cover()
            return

        direction = DIRECTION_OPEN if target > current else DIRECTION_CLOSE
        await self._async_start_movement(direction, target, duration, actuate=True)

    async def _async_start_movement(
        self, direction: str, target: int, duration: float, *, actuate: bool
    ) -> None:
        """Set up the state machine and launch the movement task."""
        if actuate:
            switches_off = [self._open_switch, self._close_switch]
        else:
            # Comando fisico: spegniamo solo il rele' opposto (interblocco),
            # quello premuto dall'utente deve restare attivo.
            switches_off = [
                self._close_switch
                if direction == DIRECTION_OPEN
                else self._open_switch
            ]

        await self._async_abort_movement(switches_off=switches_off)

        self._start_position = self._current_position
        self._target_position = target
        self._attr_is_opening = direction == DIRECTION_OPEN
        self._attr_is_closing = direction == DIRECTION_CLOSE
        self._move_start_time = None
        self.async_write_ha_state()

        self._action_task = self.hass.async_create_task(
            self._async_run_movement(direction, duration, actuate)
        )

    async def _async_run_movement(
        self, direction: str, duration: float, actuate: bool
    ) -> None:
        """Wait for the start delay, energise the relay and arm the timers."""
        active_switch = (
            self._open_switch if direction == DIRECTION_OPEN else self._close_switch
        )

        if actuate:
            if self._delay_start > 0:
                await asyncio.sleep(self._delay_start)
            await self._async_call_switch(SERVICE_TURN_ON, active_switch)

        # Il cronometro parte solo ora: contarlo dal ritardo di partenza
        # falserebbe la percentuale mostrata durante la corsa.
        self._move_start_time = dt_util.utcnow()
        self.async_write_ha_state()

        self._cancel_finish = async_call_later(
            self.hass, duration, self._async_movement_finished
        )
        self._cancel_updates = async_track_time_interval(
            self.hass,
            self._async_refresh_position,
            timedelta(seconds=POSITION_UPDATE_INTERVAL),
        )

    @callback
    def _async_refresh_position(self, _now=None) -> None:
        """Push the interpolated position to the UI while moving."""
        self.async_write_ha_state()

    @callback
    def _async_movement_finished(self, _now=None) -> None:
        """The travel time has elapsed."""
        self._cancel_finish = None
        if self._cancel_updates is not None:
            self._cancel_updates()
            self._cancel_updates = None

        self._action_task = self.hass.async_create_task(self._async_finish_movement())

    async def _async_finish_movement(self) -> None:
        """Settle the final position and release the relay."""
        active_switch = (
            self._open_switch if self._attr_is_opening else self._close_switch
        )

        # Posizione e flag vengono aggiornati PRIMA di toccare il rele': cosi'
        # l'evento di spegnimento non viene scambiato per un comando fisico.
        self._current_position = self._target_position
        self._start_position = self._target_position
        self._attr_is_opening = False
        self._attr_is_closing = False
        self._move_start_time = None

        if self._delay_stop > 0:
            await asyncio.sleep(self._delay_stop)

        await self._async_call_switch(SERVICE_TURN_OFF, active_switch)

        self._action_task = None
        self.async_write_ha_state()

    async def _async_abort_movement(self, *, switches_off: list[str]) -> None:
        """Cancel any movement in progress, freezing the position reached."""
        if self._action_task is not None and not self._action_task.done():
            self._action_task.cancel()
        self._action_task = None

        self._cancel_timers()

        # L'ordine conta: la posizione va congelata mentre i flag sono ancora
        # validi, e i flag vanno azzerati prima di agire sui rele'.
        self._current_position = self.current_cover_position
        self._start_position = self._current_position
        self._attr_is_opening = False
        self._attr_is_closing = False
        self._move_start_time = None

        for entity_id in switches_off:
            await self._async_call_switch(SERVICE_TURN_OFF, entity_id)

    @callback
    def _cancel_timers(self) -> None:
        """Cancel the finish and refresh timers."""
        if self._cancel_finish is not None:
            self._cancel_finish()
            self._cancel_finish = None
        if self._cancel_updates is not None:
            self._cancel_updates()
            self._cancel_updates = None

    async def _async_call_switch(self, service: str, entity_id: str) -> None:
        """Call turn_on / turn_off on a switch or input_boolean."""
        domain = entity_id.split(".")[0]
        self._expected_states[entity_id] = (
            STATE_ON if service == SERVICE_TURN_ON else STATE_OFF
        )
        await self.hass.services.async_call(
            domain, service, {"entity_id": entity_id}, blocking=False
        )
