# 发布记录 v0.46.0

2026-11-26 MINOR，公开工具数 111。上一版本：0.45.2（`v0.45.2`，提交 `77aaa85ed318208fef0e6628773a1cefd31ab4f7`）。

## 验收范围

归档 0.45.1 外部反馈原件至 [feedback-0.45.1-2026-11-26](feedback-0.45.1-2026-11-26/SOURCE_MANIFEST.json)（SHA256 `98ebb66c3ccc0716f775bbb37dda1f70b2ba2469982c07b9031acfc1750bcbc9`）。

本机 Windows x64 / Python 3.12.10 / Creo Parametric 10.0.0.0（`release_numeric=42`）及匹配 SDK 完成原生执行器编译（`bridge.py build`）与实机验收：
- [BUG-192](../work-items/BUG-192.md)：`tools/test_draft_direction.py` 8/8 用例全部通过并保存重载验证，确认 `surface` 底面（`flip=false` 去料 `material_effect="removed"`）与 `datum_plane` XY（`flip=false` 加料 `material_effect="added"`）的实测朝向差异及 compact/full `material_effect` 一致。
- [FEAT-090](../work-items/FEAT-090.md)：40 段异心圆弧（10 闭合轮廓、`8.215e-7 mm` 间隙）开启 `snap_endpoints=True` 后拉伸 2 mm，作业 `5ced5a2ea83a40049ebe5499299853b9` 成功，实测体积 `1047.002224 mm³`（解析 `1047.002218 mm³`），保存重载通过。
- [BUG-193](../work-items/BUG-193.md) 与 [DEV-102](../work-items/DEV-102.md)：本机实机核验 `callback_status` 持久化与 `creo_capabilities` compact 的 `runtime_ready` 披露；`not_loaded` 下的 before-job 拦截、操作列表字段与 `region.interior_point_yz_mm` 契约由离线单元测试与 `tools/test_mcp.py --offline` 覆盖。

发布门禁要求候选工作树全量单测通过，候选源码执行 `tools/dev_check.py --work-item BUG-192`，打包时核对本轮 `tools/test_unit.py` 报告与发布提交的源码指纹。发布后远端核对见 [发布后核对记录](../development/RELEASE-POSTCHECK-2026-11-07.md) 和 Release 正文。

未测范围：Creo 9 / Creo 12.4 实机、外部原始 `gear10.json` 文件、未加载 callback 实机会话下的 before-job 拦截（离线单测已覆盖）以及 WorkBuddy 黑盒验收。

## 逐 ID 状态核对

[主台账](../BACKLOG.md) · [开发入口](../DEVELOPMENT.md) · [版本说明](../release-notes/RELEASE_NOTES_0.46.0.md)

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-192](../work-items/BUG-192.md) | 0.46.0 | v0.46.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | Creo 10 实机 8/8 通过；Creo 9/12.4 与 WorkBuddy 黑盒待验收。 |
| [FEAT-090](../work-items/FEAT-090.md) | 0.46.0 | v0.46.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | Creo 10 40 弧微间隙夹具实机通过；外部原件 gear10.json、Creo 9/12.4 与 WorkBuddy 黑盒待验收。 |
| [BUG-193](../work-items/BUG-193.md) | 0.46.0 | v0.46.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 离线单测与本机 ready 态实机通过；未加载态实机、Creo 9/12.4 与 WorkBuddy 黑盒待验收。 |
| [DEV-102](../work-items/DEV-102.md) | 0.46.0 | v0.46.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 离线契约与单测通过；WorkBuddy 黑盒待验收。 |

## 附件与远端核对

- `MCP_CREO_MechDog-0.46.0-source.zip`
- `MCP_CREO_MechDog-0.46.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.46.0-seed-library.zip`
- `MCP_CREO_MechDog-0.46.0-seed-library.zip.sha256`

种子包 SHA256 为 `7ccae6e93dd1d7ed413c796a605d1488901e42abe93e8edbeb4e0fb190446384`。两份同名 sidecar 分别记录各自 ZIP 的摘要。远端校验发布后执行，当前未验证。 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.46.0)
