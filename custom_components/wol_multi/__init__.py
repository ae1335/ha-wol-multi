"""WoL Multi 集成入口。

多设备网络唤醒：UI 配置 + 基于 ICMP 的真实状态跟踪。
每台设备一个配置项，对应一个开关实体——打开即发魔术包唤醒，
开关状态反映真实 ping 探测结果。
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

# 仅支持 UI（配置项）配置，无 YAML 参数；声明空 schema 以满足 hassfest 规范
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

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
    """初始化 WoL Multi（仅支持 UI 配置，不使用 YAML）。"""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """从配置项初始化 WoL Multi。"""
    domain_data = hass.data.setdefault(DOMAIN, {})

    # 域级服务只注册一次，条目重载后依然可用
    if not domain_data.get("_services_registered"):

        async def _async_handle_send(call: ServiceCall) -> None:
            try:
                mac = normalize_mac(call.data[ATTR_MAC])
            except ValueError as err:
                raise HomeAssistantError(
                    f"无效的 MAC 地址：{call.data[ATTR_MAC]}"
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
    """选项变更时重载该配置项。"""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载一个配置项。"""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
