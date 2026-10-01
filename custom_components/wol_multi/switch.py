"""WoL Multi 开关平台。"""
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
    """从配置项初始化 WoL Multi 开关实体。"""
    coordinator: WolMultiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WolMultiSwitch(coordinator, entry)])


class WolMultiSwitch(CoordinatorEntity[WolMultiCoordinator], SwitchEntity):
    """通过 WoL 唤醒设备、并以 ping 跟踪在线状态的开关。"""

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
            model="网络唤醒设备",
        )

    def _current_mac(self) -> str:
        """返回规范化后的 MAC 地址。"""
        raw = resolve_option(self._entry, CONF_MAC, "")
        if not raw:
            return ""
        return normalize_mac(raw)

    @property
    def is_on(self) -> bool | None:
        """上次 ping 结果显示设备在线时返回 True。"""
        return bool(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """暴露寻址信息（MAC / host），便于排障。"""
        return {
            "mac": self._current_mac(),
            "host": resolve_option(self._entry, CONF_HOST, ""),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """发送魔术包唤醒设备。"""
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
        """执行已配置的关机脚本（如有）。"""
        script = resolve_option(self._entry, CONF_TURN_OFF_SCRIPT)
        if script:
            await self.hass.services.async_call(
                "script",
                "turn_on",
                {"entity_id": script},
                blocking=True,
            )
