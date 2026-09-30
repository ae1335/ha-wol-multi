"""Switch platform for WoL Multi."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_BROADCAST_ADDRESS,
    CONF_BROADCAST_PORT,
    CONF_TURN_OFF_SCRIPT,
    DEFAULT_BROADCAST_ADDRESS,
    DEFAULT_BROADCAST_PORT,
    DOMAIN,
)
from .coordinator import WolMultiCoordinator
from .util import (
    async_send_magic_packet,
    derive_broadcast_address,
    normalize_mac,
    resolve_option,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the WoL Multi switch from a config entry."""
    coordinator: WolMultiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WolMultiSwitch(coordinator, entry)])


class WolMultiSwitch(CoordinatorEntity[WolMultiCoordinator], SwitchEntity):
    """A switch that wakes a device via WoL and tracks liveness via ping."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: WolMultiCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        mac = self._current_mac()
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data[CONF_NAME],
            connections={(CONNECTION_NETWORK_MAC, mac.lower())},
            manufacturer="WoL Multi",
            model="Wake-on-LAN Device",
        )

    def _current_mac(self) -> str:
        """Return the normalized MAC address."""
        raw = resolve_option(self._entry, CONF_MAC, "")
        if not raw:
            return ""
        return normalize_mac(raw)

    @property
    def is_on(self) -> bool | None:
        """Return True when the last ping reported the device awake."""
        return bool(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Expose addressing details for debugging."""
        return {
            "mac": self._current_mac(),
            "host": resolve_option(self._entry, CONF_HOST, ""),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Send a magic packet to wake the device."""
        host = resolve_option(self._entry, CONF_HOST, "")
        broadcast = (
            resolve_option(self._entry, CONF_BROADCAST_ADDRESS, "")
            or derive_broadcast_address(host)
            or DEFAULT_BROADCAST_ADDRESS
        )
        port = int(
            resolve_option(self._entry, CONF_BROADCAST_PORT, DEFAULT_BROADCAST_PORT)
        )
        await async_send_magic_packet(self._current_mac(), broadcast, port)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Run the configured shutdown script (if any)."""
        script = resolve_option(self._entry, CONF_TURN_OFF_SCRIPT)
        if script:
            await self.hass.services.async_call(
                "script",
                "turn_on",
                {"entity_id": script},
                blocking=True,
            )
