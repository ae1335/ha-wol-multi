"""The WoL Multi integration.

Multi-device Wake-on-LAN with UI configuration and ICMP-based state tracking.
One config entry per device creates one switch entity: turning it on sends a
magic packet, and its state reflects real ping-based liveness.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_MAC,
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
    DEFAULT_BROADCAST_ADDRESS,
    DEFAULT_BROADCAST_PORT,
    DOMAIN,
    SERVICE_SEND_MAGIC_PACKET,
)
from .coordinator import WolMultiCoordinator
from .util import async_send_magic_packet, normalize_mac

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH]

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MAC): cv.string,
        vol.Optional(CONF_BROADCAST_ADDRESS): cv.string,
        vol.Optional(
            CONF_BROADCAST_PORT, default=DEFAULT_BROADCAST_PORT
        ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
    }
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up WoL Multi (UI-configured; YAML is not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WoL Multi from a config entry."""
    domain_data = hass.data.setdefault(DOMAIN, {})

    # The domain-level service is registered once and survives entry reloads.
    if not domain_data.get("_services_registered"):

        async def _async_handle_send(call: ServiceCall) -> None:
            try:
                mac = normalize_mac(call.data[ATTR_MAC])
            except ValueError as err:
                raise HomeAssistantError(
                    f"Invalid MAC address: {call.data[ATTR_MAC]}"
                ) from err
            broadcast = (
                call.data.get(CONF_BROADCAST_ADDRESS) or DEFAULT_BROADCAST_ADDRESS
            )
            port = call.data.get(CONF_BROADCAST_PORT, DEFAULT_BROADCAST_PORT)
            await async_send_magic_packet(mac, broadcast, port)

        hass.services.async_register(
            DOMAIN,
            SERVICE_SEND_MAGIC_PACKET,
            _async_handle_send,
            schema=SERVICE_SCHEMA,
        )
        domain_data["_services_registered"] = True

    coordinator = WolMultiCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    domain_data[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
