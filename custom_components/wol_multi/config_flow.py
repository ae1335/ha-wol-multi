"""Config flow to set up WoL Multi devices."""
from __future__ import annotations

import socket
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
    CONF_SCAN_INTERVAL,
    CONF_TURN_OFF_SCRIPT,
    DEFAULT_BROADCAST_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .util import normalize_mac, resolve_option


def _can_resolve(host: str) -> bool:
    """Return True when the host can be resolved via DNS/hosts."""
    try:
        socket.gethostbyname(host)
    except OSError:
        return False
    return True


_NUM_PORT = vol.All(
    NumberSelector(
        NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
    ),
    vol.Coerce(int),
)
_NUM_INTERVAL = vol.All(
    NumberSelector(
        NumberSelectorConfig(min=10, max=3600, mode=NumberSelectorMode.BOX)
    ),
    vol.Coerce(int),
)
_SCRIPT_SELECTOR = EntitySelector(EntitySelectorConfig(domain="script"))

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        ),
        vol.Required(CONF_MAC): str,
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_BROADCAST_ADDRESS, default=""): str,
        vol.Optional(CONF_BROADCAST_PORT, default=DEFAULT_BROADCAST_PORT): _NUM_PORT,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): _NUM_INTERVAL,
        vol.Optional(CONF_TURN_OFF_SCRIPT): _SCRIPT_SELECTOR,
    }
)


class WolMultiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the WoL Multi config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step: one device per entry."""
        errors: dict[str, str] = {}
        mac = ""
        if user_input is not None:
            try:
                mac = normalize_mac(user_input[CONF_MAC])
            except ValueError:
                errors[CONF_MAC] = "invalid_mac"
            if not errors and not await self.hass.async_add_executor_job(
                _can_resolve, user_input[CONF_HOST]
            ):
                errors[CONF_HOST] = "invalid_host"
            if not errors:
                user_input[CONF_MAC] = mac
                await self.async_set_unique_id(mac)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )
        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> WolMultiOptionsFlow:
        """Create the options flow handler."""
        return WolMultiOptionsFlow()


class WolMultiOptionsFlow(config_entries.OptionsFlow):
    """Handle options for an existing WoL Multi device."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the device options (name and MAC are fixed at creation)."""
        errors: dict[str, str] = {}
        entry = self.config_entry
        if user_input is not None:
            if not await self.hass.async_add_executor_job(
                _can_resolve, user_input[CONF_HOST]
            ):
                errors[CONF_HOST] = "invalid_host"
            else:
                # The selector omits the key when left empty; keep the
                # previously configured script so users cannot lose it by
                # accident (clear it by re-adding the device if ever needed).
                if CONF_TURN_OFF_SCRIPT not in user_input:
                    previous = resolve_option(entry, CONF_TURN_OFF_SCRIPT)
                    if previous:
                        user_input[CONF_TURN_OFF_SCRIPT] = previous
                return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST, default=resolve_option(entry, CONF_HOST, "")
                ): str,
                vol.Optional(
                    CONF_BROADCAST_ADDRESS,
                    default=resolve_option(entry, CONF_BROADCAST_ADDRESS, ""),
                ): str,
                vol.Optional(
                    CONF_BROADCAST_PORT,
                    default=resolve_option(
                        entry, CONF_BROADCAST_PORT, DEFAULT_BROADCAST_PORT
                    ),
                ): _NUM_PORT,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=resolve_option(
                        entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): _NUM_INTERVAL,
                vol.Optional(
                    CONF_TURN_OFF_SCRIPT,
                    description={
                        "suggested_value": resolve_option(entry, CONF_TURN_OFF_SCRIPT)
                    },
                ): _SCRIPT_SELECTOR,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)
