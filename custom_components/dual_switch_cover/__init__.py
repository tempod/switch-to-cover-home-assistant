"""The Dual Switch Cover integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS = ["cover"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dual Switch Cover from a config entry."""
    # Questa è la riga corretta per le versioni recenti di Home Assistant
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Anche la funzione di unload è cambiata in modo simile
    return await hass.config_entries.async_forward_entry_unload(entry, PLATFORMS)