"""Config flow for Dual Switch Cover."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

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
    DEVICE_CLASS_OPTIONS,
    DOMAIN,
)

SWITCH_DOMAINS = ["switch", "input_boolean"]


def _time_selector(minimum: float, maximum: float, step: float) -> NumberSelector:
    """Return a number selector expressed in seconds."""
    return NumberSelector(
        NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=step,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement="s",
        )
    )


def _settings_schema(defaults: dict[str, Any]) -> dict:
    """Return the schema fragment shared by config flow and options flow."""
    return {
        vol.Required(
            CONF_OPENING_TIME,
            default=defaults.get(CONF_OPENING_TIME, DEFAULT_OPENING_TIME),
        ): _time_selector(1, 600, 0.5),
        vol.Required(
            CONF_CLOSING_TIME,
            default=defaults.get(CONF_CLOSING_TIME, DEFAULT_CLOSING_TIME),
        ): _time_selector(1, 600, 0.5),
        vol.Required(
            CONF_DELAY_START,
            default=defaults.get(CONF_DELAY_START, DEFAULT_DELAY_START),
        ): _time_selector(0, 30, 0.1),
        vol.Required(
            CONF_DELAY_STOP,
            default=defaults.get(CONF_DELAY_STOP, DEFAULT_DELAY_STOP),
        ): _time_selector(0, 30, 0.1),
        vol.Required(
            CONF_DEVICE_CLASS,
            default=defaults.get(CONF_DEVICE_CLASS, DEFAULT_DEVICE_CLASS),
        ): SelectSelector(
            SelectSelectorConfig(
                options=DEVICE_CLASS_OPTIONS,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="device_class",
            )
        ),
        vol.Required(
            CONF_FULL_TRAVEL,
            default=defaults.get(CONF_FULL_TRAVEL, DEFAULT_FULL_TRAVEL),
        ): BooleanSelector(),
    }


class DualSwitchCoverConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dual Switch Cover."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> DualSwitchCoverOptionsFlow:
        """Return the options flow handler."""
        return DualSwitchCoverOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            open_switch = user_input[CONF_OPEN_SWITCH]
            close_switch = user_input[CONF_CLOSE_SWITCH]

            if open_switch == close_switch:
                errors[CONF_CLOSE_SWITCH] = "same_entity"
            else:
                # Evita due cover diverse sulla stessa coppia di rele'.
                await self.async_set_unique_id(f"{open_switch}|{close_switch}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): TextSelector(),
                vol.Required(CONF_OPEN_SWITCH): EntitySelector(
                    EntitySelectorConfig(domain=SWITCH_DOMAINS)
                ),
                vol.Required(CONF_CLOSE_SWITCH): EntitySelector(
                    EntitySelectorConfig(domain=SWITCH_DOMAINS)
                ),
                **_settings_schema({}),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                data_schema, user_input or {}
            ),
            errors=errors,
        )


class DualSwitchCoverOptionsFlow(OptionsFlow):
    """Handle options for Dual Switch Cover."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        entry = self.config_entry
        current = {**entry.data, **entry.options}

        if user_input is not None:
            # Il nome vive nel titolo dell'entry: aggiorniamolo di conseguenza.
            new_name = user_input.get(CONF_NAME, entry.title)
            if new_name != entry.title:
                self.hass.config_entries.async_update_entry(entry, title=new_name)
            return self.async_create_entry(data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME, default=current.get(CONF_NAME, entry.title)
                ): TextSelector(),
                **_settings_schema(current),
            }
        )

        return self.async_show_form(step_id="init", data_schema=data_schema)
