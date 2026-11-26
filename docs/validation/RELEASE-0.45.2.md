# 发布记录 v0.45.2

2026-11-26 PATCH，公开工具数 111。上一版本：0.45.1（`v0.45.1`，提交 `0177e227dd42587541e3e01628647deda53e4dea`）。

## 验收范围

开发证据覆盖 `204d37c9` 的实现包化、`cb6f0848` 的新配置以及 `96e06609` 的兼容文案。Windows x64 / Python 3.12.10 已核对新旧入口的离线 stdio、安装器生成的参数和独立解包安装。111 个工具描述及输入 schema 的清单 SHA256 为 `a4099247dbdd4a9124ad2d74cbb501b67bcbf37bf0575cce28d883119c7aa0bf`。开发阶段源指纹、命令、结果与失败复测见 [DEV-002](../work-items/DEV-002.md)。

候选源码执行 `tools/dev_check.py --work-item DEV-002`，正式源码 ZIP 在独立解包环境运行开发检查与新旧入口契约。发布门禁要求候选工作树全量单测通过，打包时核对本轮 `tools/test_unit.py` 报告与发布提交的源码指纹。验收基于无 Creo 配置的 Windows 环境。编译器依赖夹具按用例条件跳过，安装器配置由测试夹具核对。完整发布候选与解包的结果、实际提交、附件摘要及远端核对见 [发布后核对记录](../development/RELEASE-POSTCHECK-2026-11-07.md) 和 Release 正文。

本版无原生源码变化。验收未覆盖 Creo 实机几何、参数编辑、保存重载、原生回滚或 WorkBuddy 黑盒。Creo 9 的实机编译及建模仍未验收。

## 逐 ID 状态核对

[主台账](../BACKLOG.md) · [开发入口](../DEVELOPMENT.md) · [版本说明](../RELEASE_NOTES_0.45.2.md)

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [DEV-002](../work-items/DEV-002.md) | 0.45.2 | v0.45.2 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 第四、五批包化与离线兼容完成，第三批 T5 实机和其余测试布局继续开放。 |

## 附件与远端核对

- `MCP_CREO_MechDog-0.45.2-source.zip`
- `MCP_CREO_MechDog-0.45.2-source.zip.sha256`
- `MCP_CREO_MechDog-0.45.2-seed-library.zip`
- `MCP_CREO_MechDog-0.45.2-seed-library.zip.sha256`

种子包 SHA256 为 `ae0c8928d9febbd001524bc821d709a499d4235452bac64bea365e1304c336fc`。两份同名 sidecar 分别记录各自 ZIP 的摘要。远端校验发布后执行，当前未验证。 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.45.2)
