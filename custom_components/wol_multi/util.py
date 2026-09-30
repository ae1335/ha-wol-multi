"""Helper utilities for WoL Multi."""
from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import DEFAULT_BROADCAST_ADDRESS

_HEX_RE = re.compile(r"^[0-9A-Fa-f]{12}$")
_MAGIC_HEADER = b"\xff" * 6
_PACKET_REPEATS = 3
_REPEAT_DELAY = 0.05


def normalize_mac(mac: str) -> str:
    """Normalize a MAC address to uppercase colon-separated form.

    Raises ValueError when the input is not a valid MAC address.
    """
    cleaned = mac.strip().replace(":", "").replace("-", "").replace(".", "")
    if not _HEX_RE.match(cleaned):
        raise ValueError(f"Invalid MAC address: {mac}")
    return ":".join(cleaned[i : i + 2] for i in range(0, 12, 2)).upper()


def is_valid_mac(mac: str) -> bool:
    """Return True when the MAC address is well-formed."""
    try:
        normalize_mac(mac)
    except ValueError:
        return False
    return True


def build_magic_packet(mac: str) -> bytes:
    """Build a WoL magic packet: 6 x 0xFF followed by the MAC repeated 16 times."""
    return _MAGIC_HEADER + bytes.fromhex(mac.replace(":", "")) * 16


def derive_broadcast_address(host: str) -> str | None:
    """Derive the /24 directed broadcast address from an IPv4 literal.

    Returns None when the host is not a valid IPv4 address (e.g. a hostname).
    """
    try:
        network = ipaddress.ip_network(f"{host}/24", strict=False)
    except ValueError:
        return None
    return str(network.broadcast_address)


async def async_send_magic_packet(
    mac: str,
    broadcast_address: str = DEFAULT_BROADCAST_ADDRESS,
    broadcast_port: int = 9,
) -> None:
    """Send a WoL magic packet via UDP broadcast, repeated for reliability."""
    packet = build_magic_packet(mac)
    target = (broadcast_address, int(broadcast_port))

    def _send() -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for _ in range(_PACKET_REPEATS):
                sock.sendto(packet, target)
                time.sleep(_REPEAT_DELAY)

    await asyncio.get_running_loop().run_in_executor(None, _send)


def resolve_option(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Resolve a value with entry.options taking precedence over entry.data."""
    if key in entry.options:
        return entry.options[key]
    if key in entry.data:
        return entry.data[key]
    return default
