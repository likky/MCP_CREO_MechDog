# 发布记录 v0.44.1

日期为 2026-11-25，版本类型为 PATCH，公开工具数 111。上一版本：0.44.0（`v0.44.0`，提交 `08c88a77d87dd58dc0552536bfc10999874c3f8d`）。

## 验收范围

[BUG-036](../work-items/BUG-036.md) 交付平面配合回读、位姿检查和拒绝回滚。覆盖独立工具、计划更新和带约束装入。Creo 10 旧逻辑在冲突组三个约束回读成功后仍保留初始位置。本版检查在写入、总装再生和保存重载后执行。

Windows x64 / Python 3.12.10 / Creo 10.0.0.0（release 42）/ 匹配 Toolkit SDK 和 MSVC x64。实施验证用 `python -m tools.test_feedback037_modeling --cases constraint_offsets,constraint_guard` 完成 23 个实际作业（21 成功、2 个按预期失败），成功写作业保存重载，失败均验证回滚。冲突样本最大误差 30 mm 和 180°，翻转一侧的合法重试成功。T09 六类回放与基座移动 10 mm 后的随动通过。实施证据以工作卡的作业 ID、基线与受测源码指纹为准。

## 单测与离线检查

实施验证执行 `tools/dev_check.py --work-item BUG-036`，语言、离线 MCP 契约和工作树全量单测通过（4,525 项、7 跳过）。发布候选以 `tools/dev_check.py --work-item BUG-036 --skip-unit` 核对语言与离线门禁，并以 `tools/test_unit.py` 的新报告及运行状态核对干净候选提交、版本和受测源码指纹。打包门禁复核报告，完整实测结果与独立解包证据记录在[发布后附件核对记录](../development/RELEASE-POSTCHECK-2026-11-07.md)。

## 兼容与未测范围

外部 Creo 9 原案及 Creo 9/12 的本次安装与实机建模、WorkBuddy 黑盒、全项目原生回归均未执行。发布范围为本卡的平面配合验证与失败回滚。

## 附件

- `MCP_CREO_MechDog-0.44.1-source.zip`
- `MCP_CREO_MechDog-0.44.1-source.zip.sha256`
- `MCP_CREO_MechDog-0.44.1-seed-library.zip`
- `MCP_CREO_MechDog-0.44.1-seed-library.zip.sha256`

`tools/package_seeds.py` 先构建回填摘要，再用默认校验重复构建。种子包有 24 个文件和 9 个种子，SHA256 为 `491a80535bec356b99610e5805c9006cb5bf1633f150cd91c99b61768f6a1474`。源码包摘要记录在同名 sidecar 中。两份同名 sidecar 分别记录对应 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.44.1)

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-036](../work-items/BUG-036.md) | 0.44.1 | v0.44.1 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 本机 Creo 10 的位置、法向、保存重载与回滚已验。Creo 9 原案、Creo 12.4、WorkBuddy 待验。 |

## 远端核对

发布后执行，当前未验证。远端附件、前版对照和解包实测见[发布后附件核对记录](../development/RELEASE-POSTCHECK-2026-11-07.md)。
