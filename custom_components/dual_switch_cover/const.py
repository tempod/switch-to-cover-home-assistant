"""Constants for the Dual Switch Cover integration."""

from __future__ import annotations

DOMAIN = "dual_switch_cover"

# Configuration keys
CONF_NAME = "name"
CONF_OPEN_SWITCH = "open_switch_entity_id"
CONF_CLOSE_SWITCH = "close_switch_entity_id"
CONF_OPENING_TIME = "opening_time"
CONF_CLOSING_TIME = "closing_time"
CONF_DELAY_START = "delay_start"
CONF_DELAY_STOP = "delay_stop"
CONF_DEVICE_CLASS = "device_class"
CONF_FULL_TRAVEL = "full_travel_on_limits"

# Defaults
DEFAULT_NAME = "Tenda"
DEFAULT_OPENING_TIME = 25.0
DEFAULT_CLOSING_TIME = 25.0
DEFAULT_DELAY_START = 0.0
DEFAULT_DELAY_STOP = 0.0
DEFAULT_DEVICE_CLASS = "shutter"
DEFAULT_FULL_TRAVEL = True

# Device classes proposte nel config flow
DEVICE_CLASS_OPTIONS = [
    "shutter",
    "blind",
    "curtain",
    "awning",
    "shade",
    "window",
    "garage",
    "gate",
    "damper",
    "door",
]

# Intervallo di aggiornamento della posizione durante il movimento
POSITION_UPDATE_INTERVAL = 1  # secondi

# Sotto questa durata non vale la pena avviare il motore
MIN_TRAVEL_TIME = 0.1  # secondi
