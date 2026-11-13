# Unitree Network Tool

[中文](README.md) | **English**

**Windows Network Configuration Tool for Unitree Robots**

Unitree Network Tool is a Windows desktop application independently developed by JazzZhou for configuring robot connection parameters and managing Wi-Fi on supported devices. The software is permanently free and is distributed as a single-file EXE, with no Python installation required.

> **Current version: v2.1.0**
>
> **Supported robots: G1 series, H2 series, R1 series**

## Highlights

- Single-file Windows EXE, portable, no installation required.
- Unified SSH connection interface with editable address, username and password; passwords are shown in plain text.
- Manual update check within the app.
- The Wi-Fi page provides status detection, scanning and connection operations.
- Saved Wi-Fi profiles are loaded automatically the first time you open the page; saved passwords are shown in plain text, and multiple profiles can be collapsed.
- Connection checks and confirmations are performed before network changes; unsupported or unverifiable configurations are rejected.

## Supported Robots

| Series | Models | Notes |
|---|---|---|
| G1 series | G1 / G1+ / G1D / G1E | SSH connection and applicable Wi-Fi configuration; PC4 hotspot management is offered only when compatibility is clearly confirmed by detection |
| H2 series | H2 / H2D | Selectable PC2, optional PC3 or optional PC4; supports `192.168.123.x` and `192.168.124.x` network segments |
| R1 series | R1 / R1D | Uses the G1 series connection preset; connection parameters can be edited manually |

H2 defaults to PC2. The default PC2 password is `Unitree0408`, with an in-app shortcut for the early password `Unitree#24226`. PC3 and PC4 are optional units — confirm that they are actually installed and verify the parameters before connecting. For all robots, the SSH address, username and password can be edited manually; the software never tries passwords in rotation automatically.

**PC4 hotspot management applies only to G1 series environments whose compatibility is clearly confirmed by detection; it is not enabled by default for H2 or R1 just because the device has a PC4.** G1 PC1 is not supported by this tool. Robot firmware and network configurations may vary; rely on the software's detection results and the actual device.

## Download & Run

| Channel | Address | Best for |
| --- | --- | --- |
| GitHub Releases (international) | [Download the latest version](https://github.com/27daiwu/unitree-network-tool/releases/latest) | Overseas networks, or whenever GitHub is reachable |
| Gitee Releases (China mirror) | [Download the latest version](https://gitee.com/daiwu27/unitree-network-tool/releases/latest) | Mainland China networks, faster downloads |

Both channels publish exactly the same versions. The Gitee repository and its attachments are synced automatically from GitHub after each Release is published, and the attachments are SHA256-verified to match GitHub; if one channel is unreachable, simply use the other. For previous versions, visit the [Releases page](https://github.com/27daiwu/unitree-network-tool/releases) of either channel.

v2.1.0 file name: `Unitree-Network-Tool-v2.1.0.exe`

1. Download the EXE from Releases.
2. Close any older version that is still running.
3. Double-click to run the new version.

No installation or Python environment is required. This repository only distributes the packaged Windows EXE; source code is not published. The software does not carry a commercial code-signing certificate, so Windows may show an unknown-publisher or security warning; verify the download source before running.

## Before You Start

1. Connect your computer to the robot's wired network port with an Ethernet cable, and make sure the target compute unit is powered on.
2. Configure the computer's wired adapter to the network segment that matches the target device. For H2, choose `192.168.123.x` or `192.168.124.x` according to the device configuration; for other devices, verify the actual address.
3. In the software, select the robot series and compute unit, then verify the SSH address, username and password. H2's PC3/PC4 are optional and may not be present.
4. Before making network changes, record the device's original network configuration and keep a reliable wired management connection.

Changing the robot's network may affect Wi-Fi or remote access. PC4 hotspot operations first check the wireless state and the SSH management link and require confirmation; no change is made when compatibility cannot be clearly determined. SSH credentials and readable saved Wi-Fi passwords are displayed in plain text in the UI — use the software only in trusted environments, and never disclose them or post them to Issues.

## Changelog

### v2.1.0 — 2026-11-11

- Added instant Chinese / English UI language switching.
- Automatic Wi-Fi scanning after switching PC4 to Wi-Fi mode.
- Network diagnostics now support dynamic NIC identification (eth0, eth10, enP*, etc.).
- Improved UI layout and styling.
- Fixed an issue where the only unbound AP profile could not be restored after reconnection.

### v2.0.0 — 2026-11-09

- Unified G1 and G1+ into the G1 series; added H2 and R1 connection presets.
- H2 supports PC2, optional PC3/PC4, dual network segments and an early PC2 password shortcut.
- Added hotspot / Wi-Fi client mode switching for applicable G1 series PC4 environments.
- Improved Wi-Fi status detection, scanning, saved-network loading and page layout.
- Fixed the busy mouse cursor that remained after the SSH connection was established; improved startup speed and reduced the EXE size.
- Kept the manual update check feature.

### v1.0.0 — 2026-11-05

First public release, providing a Windows GUI for G1 network configuration, a single-file EXE and manual version checking.

See [GitHub Releases](https://github.com/27daiwu/unitree-network-tool/releases) for the complete version history.

## Feedback

Bug reports and feature suggestions are welcome via [GitHub Issues](https://github.com/27daiwu/unitree-network-tool/issues). Please include the software version, robot model, OS version, steps to reproduce and the error message. **Do not post SSH passwords, Wi-Fi passwords or any other sensitive information in Issues.**

## License & Copyright

Unitree Network Tool is free closed-source software. Without the developer's authorization, the software may not be modified, repackaged, redistributed or resold, and no one may impersonate the developer or claim that the software is an official Unitree product. See the `LICENSE` file in this repository for the specific terms of use.

This software is independently developed by a third party. It is not official Unitree software and does not represent an endorsement or warranty by Unitree Robotics. Robot and product names and trademarks belong to their respective owners.

---

**Developer:** JazzZhou  
**GitHub:** https://github.com/27daiwu/unitree-network-tool  
**Gitee:** https://gitee.com/daiwu27/unitree-network-tool  
**Copyright © 2026 JazzZhou. All rights reserved.**
