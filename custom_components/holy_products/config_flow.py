"""Config flow for HOLY Products integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_PRODUCT_TYPES,
    CONF_SCAN_INTERVAL,
    CONF_TAGS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


def _build_schema(
    defaults: dict[str, Any] | None = None,
) -> vol.Schema:
    """Build the data schema with optional defaults."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL // 60),
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional(
                CONF_PRODUCT_TYPES,
                default=defaults.get(CONF_PRODUCT_TYPES, ""),
            ): str,
            vol.Optional(
                CONF_TAGS,
                default=defaults.get(CONF_TAGS, ""),
            ): str,
        }
    )


class HolyProductsConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for HOLY Products."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            # Convert minutes to seconds for storage
            user_input[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL] * 60
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="HOLY Products",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow handler."""
        return HolyProductsOptionsFlow(config_entry)


class HolyProductsOptionsFlow(OptionsFlow):
    """Handle options flow for HOLY Products."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            user_input[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL] * 60
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.options or self._config_entry.data
        defaults = {
            CONF_SCAN_INTERVAL: current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL) // 60,
            CONF_PRODUCT_TYPES: current.get(CONF_PRODUCT_TYPES, ""),
            CONF_TAGS: current.get(CONF_TAGS, ""),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(defaults),
        )
