"""WoL Multi 设备配置流。"""
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
    """测试主机名 / IP 能否被 DNS 或 hosts 解析。"""
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
    """处理 WoL Multi 配置流。"""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """处理初始步骤：每个配置项对应一台设备。"""
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
        """创建选项流处理器。"""
        return WolMultiOptionsFlow()


class WolMultiOptionsFlow(config_entries.OptionsFlow):
    """管理既有 WoL Multi 设备的选项。"""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """管理设备选项（名称与 MAC 在创建时固定，不可修改）。"""
        errors: dict[str, str] = {}
        entry = self.config_entry
        if user_input is not None:
            if not await self.hass.async_add_executor_job(
                _can_resolve, user_input[CONF_HOST]
            ):
                errors[CONF_HOST] = "invalid_host"
            else:
                # 选择器留空时会省略该键；此时保留原有关机脚本，避免误清空
                # （如确需清空，可删除设备后重新添加）
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
