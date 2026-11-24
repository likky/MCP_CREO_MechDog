# 发布记录 v0.43.2

日期为 2026-11-24，版本类型为 PATCH，公开工具数 111。

上一版本：0.43.1（`v0.43.1`，提交 `f8a07c0513a0abbf7b1e30ca454cb9a1ed4215a0`）。

## 验收范围

BUG-175 让普通启动与显式强制启动的单测共用可控时钟和模拟等待。测试分别确认陈旧会话诊断和强制启动一次后就绪，并隔离 Toolkit 锁和运行目录。[BUG-175](../work-items/BUG-175.md)

反馈中的 v0.43.0 官方源码包已核对 SHA256。首次模拟探测延迟 1.1 秒时，旧强制启动测试从预期的 `ready` 变为 `timeout`。补修版解包后，目标用例连续通过 120/120 次，注入同一延迟后通过 3/3 次。工作卡保存受测源码身份和复现结果。

## 单测与离线检查

验证环境为 Windows 11 x64（10.0.26200）和 Python 3.12.10。

`PYTHONUTF8=1 python tools/dev_check.py --work-item BUG-175` 通过。工作树全量单测通过，执行 4,495 项，0 失败、0 错误、7 跳过，耗时 374.39 秒。Ruff 与 clang-format 按项目基线检查无新增问题。更新检查、模型恢复及 MCP stdio 三项离线门禁通过，MCP 服务报告 0.43.2 和 111 个工具。

单测 `run_id=7f11e1bdcca64b3fa249c29754a09f1f`。受测提交 `7c8ab025dccebfb4bfcb525e5f280a4038c5ad7d`，`dirty=false`，受测源码指纹 `f679a74d861befa54ef28cad50ab6fe26a695f3437ff053cc5014e57d9ff4f41`，共 682 个 Git 跟踪的 Python 和原生源文件。

## 种子包

先运行 `tools/package_seeds.py --allow-record-mismatch` 取得摘要并回填 `docs/seed_package.json`，再用默认校验重建。种子包含 24 个文件和 9 个种子，SHA256 为 `fece0e88c0c55828f9776944ad2196215e43077fcd1b3c7e62103e9d16891c52`。

## 原生与注册基线

对照 v0.43.1 已发布源码 ZIP 的 SHA256 后，核对 189 个可执行源码、第三方库、种子模型、安装和配置模板文件，字节逐一一致。固定相同 ABI 输入，用 `sha256-repo-lf-v1` 对比 callback 和 loader 的源码依赖，两组指纹一致。本机已有 loader、callback、worker 和 `blend_callback_protk.dat` 的原字节 SHA256 在候选检查前后相同，验证过程中未重新构建或注册。

## 未测范围

本补丁涉及离线测试夹具与发布元数据。Creo 9/10/12 原生安装、连接、建模和几何重载，以及报告方的外部环境复测均未执行。

## 附件

- `MCP_CREO_MechDog-0.43.2-source.zip`
- `MCP_CREO_MechDog-0.43.2-source.zip.sha256`
- `MCP_CREO_MechDog-0.43.2-seed-library.zip`
- `MCP_CREO_MechDog-0.43.2-seed-library.zip.sha256`

种子包 SHA256 为 `fece0e88c0c55828f9776944ad2196215e43077fcd1b3c7e62103e9d16891c52`。源码包摘要记录在同名 sidecar 中。两份同名 sidecar 分别记录对应 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.43.2)

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-175](../work-items/BUG-175.md) | 0.43.2 | v0.43.2 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 待报告方复测公开源码包 |

## 远端核对

发布后执行，当前未验证。源包解压后的独立门禁和发布后远端证据将记录在[发布后附件核对记录](../development/RELEASE-POSTCHECK-2026-11-07.md)。
