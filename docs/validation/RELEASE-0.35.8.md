# 发布记录 v0.35.8

日期：2026-11-22

版本：0.35.8（PATCH）

上一版本：0.35.7（`v0.35.7`，提交 `a0aa08dd0f9efd64618868d70634718e88d9792d`）。

发布源码为本次主干发布提交，附注标签为 `v0.35.8`。实际提交号、Release 对象与下载核对结论见 [发布后核对](../development/RELEASE-POSTCHECK-2026-11-07.md)。

## 范围与验收

- [BUG-150](../work-items/BUG-150.md) 允许拉伸切除按确切的 `PRO_BODY/-5778` 选取初始活动实体。公开工具数为 111。
- Windows x64 / Python 3.12.10 / Creo 10.0.0.0 release 42 / 匹配 C TOOLKIT SDK / MSVC x64。原生构建执行 `bridge.py build`。实机使用 `tools/test_cut_scope_live.py --live --confirm-session-usable --initial-body` 和正 ID 套件。800 mm³ 的两条路线均通过保存重载，双体隔离、缺失 ID 回滚和保存后的树回读见 [BUG-150 实机记录](../work-items/BUG-150.md#修复后实机验收)。
- 开发检查使用 `tools/dev_check.py --skip-unit --work-item BUG-150`。全量单测通过（4,390 项、0 失败、0 错误、7 跳过）。`tools/test_unit.py` 写入 `build/unit_test_report.json` 与本轮状态，`run_id=ebf3aa8cc5ba4e63bfda6743bb868dc6`，受测提交 `29adc793bef50312228646d2691555ec5610475f`，`dirty=false`，源码指纹 `98ff84c864ea99f67bc568c8b2ebfb24407d1ffc178f5a130abaaaa5ce42923c`。随后只补本段发布记录，打包门禁再次核对源码指纹。
- 源码包独立解压全量单测作为发布门槛，工作树与解压件的实际统计在 [发布后核对](../development/RELEASE-POSTCHECK-2026-11-07.md) 分别记录。

## 四件附件和摘要

- `MCP_CREO_MechDog-0.35.8-source.zip`
- `MCP_CREO_MechDog-0.35.8-source.zip.sha256`
- `MCP_CREO_MechDog-0.35.8-seed-library.zip`
- `MCP_CREO_MechDog-0.35.8-seed-library.zip.sha256`
- 种子包 SHA256：`46afef284f90b01f76ab50152a2f428b16077561e64a3e8159f266721d397b12`（24 个文件、9 个种子，两次构建一致）。
- 源码包由主干发布提交源码构建，摘要见同名 sidecar。每个 sidecar 记录各自 ZIP 的实际 SHA256。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-150](../work-items/BUG-150.md) | 0.35.8 | v0.35.8 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 原护卫舰零去料待原件复现 |

## 发布后远端核对

发布后执行，当前未验证。Release 地址：https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.8。

## 未验

原护卫舰省略 `scope` 的零去料待原模型和完整请求复现。Creo 9/12 与 WorkBuddy 黑盒未纳入本版验收。
