"""The Dual Switch Cover integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [Platform.COVER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dual Switch Cover from a config entry."""
    # Quando l'utente modifica le opzioni, ricarichiamo l'entry cosi' i nuovi
    # tempi vengono applicati senza dover riavviare Home Assistant.
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # async_forward_entry_unload() accetta UNA sola piattaforma ed e' deprecata:
    # per una lista si usa async_unload_platforms().
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
