"""WoL Multi 数据更新协调器。"""
from __future__ import annotations

from datetime import timedelta
import logging

import icmplib
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .util import resolve_option

_LOGGER = logging.getLogger(__name__)


class WolMultiCoordinator(DataUpdateCoordinator[bool]):
    """通过 ICMP 轮询目标主机，判定设备是否在线。"""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """从配置项初始化协调器。"""
        interval = int(
            resolve_option(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=max(interval, MIN_SCAN_INTERVAL)),
        )
        self.entry = entry
        self.host: str = resolve_option(entry, CONF_HOST, "")

    async def _async_update_data(self) -> bool:
        """ping 目标主机；返回 True 表示设备应答在线。"""
        last_error: Exception | None = None
        # HA 容器内优先使用特权（raw socket）ping，无权限时自动回退非特权模式
        for privileged in (True, False):
            try:
                result = await icmplib.async_ping(
                    self.host, count=1, timeout=2, privileged=privileged
                )
            except icmplib.NameLookupError:
                _LOGGER.debug("主机 %s 无法解析", self.host)
                return False
            except OSError as err:
                last_error = err
                continue
            return bool(result.is_alive)
        _LOGGER.warning("对 %s 的 ping 失败：%s", self.host, last_error)
        return False
