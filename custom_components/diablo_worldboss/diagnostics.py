"""Event diagnostics contain no credentials or user configuration."""
async def async_get_config_entry_diagnostics(hass, entry):
    return entry.runtime_data.data
