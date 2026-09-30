"""Data update coordinator for WoL Multi."""
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
    """Poll the host over ICMP to determine whether the device is awake."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator from a config entry."""
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
        """Ping the host; True means the device answered and is awake."""
        last_error: Exception | None = None
        # Prefer privileged (raw socket) ping inside the HA container, and
        # gracefully fall back to the unprivileged variant when not permitted.
        for privileged in (True, False):
            try:
                result = await icmplib.async_ping(
                    self.host, count=1, timeout=2, privileged=privileged
                )
            except icmplib.NameLookupError:
                _LOGGER.debug("Host %s could not be resolved", self.host)
                return False
            except OSError as err:
                last_error = err
                continue
            return bool(result.is_alive)
        _LOGGER.warning("Ping to %s failed: %s", self.host, last_error)
        return False
