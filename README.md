# WoL Multi

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

为 Home Assistant 打造的**多设备网络唤醒（Wake-on-LAN）自定义集成**：每台设备一个开关实体，打开即发魔术包，状态来自真实 ICMP 探测——而不是"假设上次动作后的状态"。

## 与内置 `wake_on_lan` 的差异

| 能力 | 内置集成 | WoL Multi |
|---|---|---|
| UI 添加设备 | 仅 button（无状态） | ✅ 每设备一个 switch，全程 UI |
| 真实在线状态 | 需 YAML 写 host + ping 依赖 | ✅ 内置 ICMP 轮询（DataUpdateCoordinator） |
| 关机联动 | YAML `turn_off` + shell_command | ✅ UI 里直接选一个 script 实体 |
| 修改参数 | 改 YAML 重启 | ✅ Options flow（IP / 广播 / 间隔 / 关机脚本） |
| 批量设备 | 重复 YAML 条目 | ✅ 添加集成多次即可，自动按 MAC 去重 |
| 中文界面 | 部分 | ✅ zh-Hans 完整翻译 |

## 功能特性

- 🔌 **每设备一个 switch 实体**：`on` = 已唤醒（ping 通），`off` = 离线
- 📡 **真实状态跟踪**：ICMP ping 轮询（默认 30 秒，可调），特权/非特权模式自动回退
- 🎯 **广播地址自动推导**：留空则按目标 IP 推导 `/24` 定向广播，跨交换机更可靠
- 🔁 **魔术包连发 3 次**：对抗丢包，唤醒成功率更高
- 🛑 **关机联动**：turn_off 绑定任意 script 实体（SSH 关机命令放进 script 即可）
- 🧰 **全局服务** `wol_multi.send_magic_packet`：不建实体也能发包
- 🧩 **HACS 就绪**：hacs.json + hassfest/HACS CI 校验

## 安装（HACS）

> 仓库地址以实际发布为准（占位 `https://github.com/ae1335/ha-wol-multi`）。

1. HACS → 右上角 ⋮ → **自定义存储库** → 填入仓库地址，类别选 **集成（Integration）**
2. 搜索 **WoL Multi** → 下载
3. **重启 Home Assistant**

### 手动安装

把 `custom_components/wol_multi/` 整个目录复制到 HA 的 `config/custom_components/` 下，重启。

## 配置

设置 → 设备与服务 → **添加集成** → 搜索 **WoL Multi**，按提示填：

| 字段 | 说明 |
|---|---|
| 设备名称 | 显示名，也是实体 id（如 `Family Server` → `switch.family_server`） |
| MAC 地址 | 目标设备网卡 MAC（`AA:BB:CC:DD:EE:FF` 或 `-` 分隔均可） |
| IP / 主机名 | 用于 ping 状态检测 |
| 广播地址 | 留空 = 自动推导 |
| 广播端口 | 默认 9 |
| 检测间隔 | 默认 30 秒（10-3600） |
| 关机脚本 | 可选，选一个 `script.*` 实体，关闭开关时触发 |

多台设备：**重复添加集成**即可，同一 MAC 自动拒绝重复。

## 用法示例

关机联动：先建一个 script（如 `script.shutdown_nas`，内容为调用 shell_command 的 SSH 关机命令），再在设备选项里选中它。

自动化示例——NAS 离线 5 分钟自动尝试唤醒：

```yaml
automation:
  - alias: "NAS 掉线自动唤醒"
    trigger:
      - platform: state
        entity_id: switch.family_server
        to: "off"
        for: "00:05:00"
    action:
      - action: switch.turn_on
        target:
          entity_id: switch.family_server
```

服务调用（无需实体）：

```yaml
action: wol_multi.send_magic_packet
data:
  mac: "AA:BB:CC:DD:EE:FF"
```

## 前提与排障

WoL 只能开机不能关机；魔术包是二层广播、不跨网段。目标设备需：

1. **BIOS** 开启 Wake on LAN / PCI-E Wake
2. **网卡驱动**允许魔术包唤醒
3. Windows 关闭「快速启动」（否则关机后网卡断电）
4. 允许 ICMP 回显（否则状态永远是 off）

| 症状 | 处理 |
|---|---|
| 发包后不亮 | 查 BIOS WoL 开关 |
| 关机后不亮、重启能亮 | Windows 关快速启动 |
| 状态一直 off | 放行 ICMP（Windows 防火墙：文件和打印机共享-回显请求-In） |
| 广播收不到 | 把广播地址填成目标网段定向广播（如 `192.168.2.255`） |

## License

[MIT](LICENSE)
