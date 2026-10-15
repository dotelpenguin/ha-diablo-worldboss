"""Diablo IV world event integration."""
from homeassistant.const import Platform
from .coordinator import EventCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]


async def async_setup_entry(hass, entry):
    coordinator = EventCoordinator(hass, entry)
    entry.runtime_data = coordinator
    entry.async_on_unload(coordinator.cancel_boundary)
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload))
    return True


async def async_reload(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
