"""Config flow for Dual Switch Cover."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_OPEN_SWITCH,
    CONF_CLOSE_SWITCH,
    CONF_OPENING_TIME,
    CONF_CLOSING_TIME,
    CONF_DELAY_START,
    CONF_DELAY_STOP,
)


class DualSwitchCoverConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dual Switch Cover."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # You can add validation here if needed
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Tenda Soggiorno"): str,
                vol.Required(CONF_OPEN_SWITCH): EntitySelector(
                    EntitySelectorConfig(domain=["switch", "input_boolean"])
                ),
                vol.Required(CONF_CLOSE_SWITCH): EntitySelector(
                    EntitySelectorConfig(domain=["switch", "input_boolean"])
                ),
                vol.Required(CONF_OPENING_TIME, default=25): NumberSelector(
                    NumberSelectorConfig(min=1, max=120, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement="s")
                ),
                vol.Required(CONF_CLOSING_TIME, default=25): NumberSelector(
                    NumberSelectorConfig(min=1, max=120, step=1, mode=NumberSelectorMode.BOX, unit_of_measurement="s")
                ),
                vol.Required(CONF_DELAY_START, default=0): NumberSelector(
                    NumberSelectorConfig(min=0, max=10, step=0.5, mode=NumberSelectorMode.BOX, unit_of_measurement="s")
                ),
                vol.Required(CONF_DELAY_STOP, default=0): NumberSelector(
                    NumberSelectorConfig(min=0, max=10, step=0.5, mode=NumberSelectorMode.BOX, unit_of_measurement="s")
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )