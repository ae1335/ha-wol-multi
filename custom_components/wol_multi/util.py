"""WoL Multi 工具函数集。"""
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
    """将 MAC 地址规范化为大写冒号分隔格式。

    输入不是合法 MAC 时抛出 ValueError。
    """
    cleaned = mac.strip().replace(":", "").replace("-", "").replace(".", "")
    if not _HEX_RE.match(cleaned):
        raise ValueError(f"Invalid MAC address: {mac}")
    return ":".join(cleaned[i : i + 2] for i in range(0, 12, 2)).upper()


def is_valid_mac(mac: str) -> bool:
    """判断 MAC 地址格式是否合法。"""
    try:
        normalize_mac(mac)
    except ValueError:
        return False
    return True


def build_magic_packet(mac: str) -> bytes:
    """构造 WoL 魔术包：6 个 0xFF 后跟重复 16 次的目标 MAC。"""
    return _MAGIC_HEADER + bytes.fromhex(mac.replace(":", "")) * 16


def derive_broadcast_address(host: str) -> str | None:
    """从 IPv4 字面量推导 /24 定向广播地址。

    host 不是合法 IPv4 地址（例如主机名）时返回 None。
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
    """通过 UDP 广播发送 WoL 魔术包，连发多次以对抗丢包。"""
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
    """读取配置值：entry.options 优先于 entry.data。"""
    if key in entry.options:
        return entry.options[key]
    if key in entry.data:
        return entry.data[key]
    return default
