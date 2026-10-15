"""UI setup and interval options."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, NAME, CONF_INTERVAL, DEFAULT_INTERVAL


def schema(default):
    return vol.Schema({vol.Required(CONF_INTERVAL, default=default): vol.All(vol.Coerce(int), vol.Range(min=5, max=120))})


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title=NAME, data=schema(DEFAULT_INTERVAL)(user_input))
        return self.async_show_form(step_id="user", data_schema=schema(DEFAULT_INTERVAL))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        default = self.config_entry.options.get(CONF_INTERVAL, self.config_entry.data.get(CONF_INTERVAL, DEFAULT_INTERVAL))
        if user_input is not None:
            return self.async_create_entry(title="", data=schema(default)(user_input))
        return self.async_show_form(step_id="init", data_schema=schema(default))
