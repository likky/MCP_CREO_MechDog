# 发布记录 v0.36.0

日期为 2026-11-23，版本类型为 MINOR。

上一版本：0.35.8（`v0.35.8`，提交 `ed8ea5141a0574de91ec0b19d171dd22f55ca68b`）。

## 验收范围

Windows x64 / Python 3.12.10 / Creo 10.0.0.0 release 42 / 匹配 Toolkit SDK / MSVC x64。保存重载、恢复后编辑、切除去料、种子放样的解析体积、同计划选面和 JPEG 实测见[本机验收](feedback-save-loft-2026-11-23.md)。

升版前的开发工作树全量单测通过，执行 4397 项、跳过 7 项，元数据为 0.35.8。0.36.0 使用本轮候选的独立报告作为打包证据。

适用门禁包括 `tools/dev_check.py --work-item BUG-152`、`bridge.py build`、种子包重复构建、`tools/check_release_records.py --version 0.36.0` 以及实际源码包独立解压后的 `tools/test_unit.py`。

## 附件

- `MCP_CREO_MechDog-0.36.0-source.zip`
- `MCP_CREO_MechDog-0.36.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.36.0-seed-library.zip`
- `MCP_CREO_MechDog-0.36.0-seed-library.zip.sha256`

种子包 SHA256 为 `c43228ac6a8764cd7369fc04ee151ceb4c3ee735063c6052839e72d0146bf25f`，包含 24 个文件、9 个种子。两个同名 sidecar 分别记录各自 ZIP 的实际摘要。源码包自校验值随 sidecar 分发。

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-152](../work-items/BUG-152.md) | 0.36.0 | v0.36.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 保存异常的外部原现场缺失 |
| [BUG-153](../work-items/BUG-153.md) | 0.36.0 | v0.36.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 精确样条切除仍有内核限制 |
| [BUG-154](../work-items/BUG-154.md) | 0.36.0 | v0.36.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 外部七截面种子待复测 |
| [FEAT-074](../work-items/FEAT-074.md) | 0.36.0 | v0.36.0 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 装配预览、原弧段和面角色组待复验 |

## 远端核对

发布后执行，当前未验证。见 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.36.0) 和 [发布后核对](../development/RELEASE-POSTCHECK-2026-11-07.md)。

Creo 9/12、外部模型和七截面种子、WorkBuddy 黑盒均未纳入本版实机。Creo 9 SDK 编译与运行时验收仍未完成。
