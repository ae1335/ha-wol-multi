"""WoL Multi 集成常量定义。"""
from __future__ import annotations

DOMAIN = "wol_multi"

CONF_BROADCAST_ADDRESS = "broadcast_address"
CONF_BROADCAST_PORT = "broadcast_port"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_TURN_OFF_SCRIPT = "turn_off_script"

DEFAULT_BROADCAST_ADDRESS = "255.255.255.255"
DEFAULT_BROADCAST_PORT = 9
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 10

SERVICE_SEND_MAGIC_PACKET = "send_magic_packet"

ATTR_MAC = "mac"
