# Unitree Network Tool

**宇树机器人 Windows 网络配置工具**

Unitree Network Tool 是 JazzZhou 独立开发的 Windows 桌面工具，用于配置机器人连接参数及管理适用设备的 Wi-Fi。软件永久免费，作为单文件 EXE 发布，无需安装 Python。

> **当前版本：v2.0.0**
>
> **支持机型：Unitree G1 系列、H2、R1**
>
> **软件性质：永久免费 · 闭源软件 · 第三方独立开发**

## 软件特点

- Windows 单文件 EXE，绿色免安装。
- 统一 SSH 连接界面，可手动修改地址、用户名和密码；密码明文显示。
- 支持在软件内手动检查更新。
- Wi-Fi 页面提供状态检测、扫描和连接操作。
- 首次进入已保存 Wi-Fi 页面时自动读取一次；已保存密码在界面明文显示，多个配置可折叠查看。
- 修改网络前进行必要的连接检查与确认；不支持或无法确认的配置会拒绝操作。

## 支持机型

| 机型 | 支持说明 |
|---|---|
| G1 系列（包括 G1、G1+） | SSH 连接与适用的 Wi-Fi 配置；PC4 热点管理仅在检测结果明确兼容时提供 |
| H2 | 可选择 PC2、选配 PC3 或选配 PC4；支持 `192.168.123.x` 与 `192.168.124.x` 网段配置 |
| R1 | 使用 G1 系列连接预设；可手动修改连接参数 |

H2 默认选择 PC2。PC2 默认密码为 `Unitree0408`，界面提供早期密码 `Unitree#24226` 的快捷切换。PC3、PC4 为选配单元，连接前请确认设备实际安装并核对参数。所有机型的 SSH 地址、用户名和密码均可手动编辑；软件不会自动轮流尝试密码。

**PC4 热点管理仅针对检测结果明确兼容的 G1 系列环境，不会因设备具有 PC4 而对 H2 或 R1 默认启用。** G1 PC1 不在本工具支持范围内。机器人固件和网络配置可能存在差异，请以软件检测结果和设备实际情况为准。

## 下载与运行

| 下载渠道 | 地址 | 适用场景 |
| --- | --- | --- |
| GitHub Releases（国际源） | [下载最新版本](https://github.com/27daiwu/unitree-network-tool/releases/latest) | 海外网络，或可正常访问 GitHub 时 |
| Gitee Releases（国内镜像） | [下载最新版本](https://gitee.com/daiwu27/unitree-network-tool/releases/latest) | 中国大陆网络，下载更快 |

两个渠道发布完全相同的版本。Gitee 仓库与附件由 GitHub 在每次 Release 发布后自动同步，附件经 SHA256 校验与 GitHub 一致；任一渠道无法访问时可改用另一个。历史版本请前往对应渠道的 [Releases 页面](https://github.com/27daiwu/unitree-network-tool/releases)下载。

v2.0.0 文件名：`Unitree-Network-Tool-v2.0.0.exe`

1. 从 Releases 下载 EXE。
2. 关闭正在运行的旧版本。
3. 双击运行新版本。

软件无需安装，也无需 Python 环境。本仓库仅提供打包后的 Windows EXE，不发布源代码。软件未声明具备商业代码签名证书，Windows 可能显示未知发布者或安全提示；请确认下载来源后再运行。

## 使用前准备

1. 使用网线连接电脑与机器人对应的有线网络接口，并确认目标计算单元已开机。
2. 将电脑有线网卡配置到与目标设备相匹配的网段。H2 可根据设备配置选择 `192.168.123.x` 或 `192.168.124.x`；其他设备请核对实际地址。
3. 在软件中选择机型及计算单元，核对 SSH 地址、用户名和密码。H2 的 PC3/PC4 为选配，不保证设备存在。
4. 执行网络修改前，记录设备原有网络配置，并保持可靠的有线管理连接。

修改机器人网络可能影响 Wi-Fi 或远程访问。PC4 热点操作会先检查无线状态和 SSH 管理链路，并要求确认；无法明确判断兼容性时不会执行修改。SSH 凭据及可读取的已保存 Wi-Fi 密码会在界面明文显示，请仅在可信环境使用，不要公开或提交到 Issues。

## 更新日志

### v2.0.0

- G1 与 G1+ 统一为 G1 系列，新增 H2、R1 连接配置。
- H2 支持 PC2、选配 PC3/PC4、双网段切换及 PC2 早期密码快捷选项。
- 为适用的 G1 系列 PC4 环境增加热点与 Wi-Fi 客户端模式切换。
- 改进 Wi-Fi 状态检测、扫描、已保存网络读取及页面布局。
- 修复 SSH 连接完成后鼠标仍显示忙碌状态的问题，并优化启动速度和 EXE 体积。
- 保留手动检查更新功能。

### v1.0.0 — 2026-11-05

首个公开版本，提供 G1 的 Windows 图形化网络配置界面、单文件 EXE 和手动版本检查。

完整版本历史请查看 [GitHub Releases](https://github.com/27daiwu/unitree-network-tool/releases)。

## 问题反馈

欢迎通过 [GitHub Issues](https://github.com/27daiwu/unitree-network-tool/issues) 提交 Bug 或功能建议。反馈时请提供软件版本、机型、系统版本、操作步骤和错误提示。**请勿在 Issues 中公开 SSH 密码、Wi-Fi 密码或其他敏感信息。**

## 授权与版权

Unitree Network Tool 为永久免费闭源软件。未经开发者授权，不得修改、重新打包、重新分发或转售软件。不得冒用开发者身份或宣称本软件为宇树官方产品。具体使用条件以仓库中的 `LICENSE` 文件为准。

本软件由第三方独立开发，并非宇树科技官方软件，也不代表宇树科技对本项目的认可或担保。机器人及相关产品名称、商标归各自权利人所有。

---

**Developer:** JazzZhou  
**GitHub:** https://github.com/27daiwu/unitree-network-tool  
**Gitee:** https://gitee.com/daiwu27/unitree-network-tool  
**Copyright © 2026 JazzZhou. All rights reserved.**
