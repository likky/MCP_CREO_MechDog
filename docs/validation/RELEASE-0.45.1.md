# 发布记录 v0.45.1

2026-11-25，PATCH，公开工具数 111。上一版本：0.45.0（`v0.45.0`，提交 `378990cc16d75ea2a86417619c3fefce1ef2a972`）。

## 验收范围

Windows x64、Python 3.12.10、Creo 10.0.0.0（release 42）、匹配 Toolkit SDK 与 MSVC x64。样件为 `frigate_bulb_twostage_gui2`，模型 `900ddd1e757f4783b75397e95f703a0e`，revision 14，原生体积 55,036,350,824.09 mm³。

默认六轮只读导出作业 `ec49b8d46e2b403993253d3c1b8a7ed9` 成功，约 140 秒。受测工作区基于提交 `bc425112ec0f16a1426f0da4e524dc7d510f8b82`，dirty，源码指纹 `854ed33a5b5897038bc27f38d9814e2c32525cff1b959bdaea528887199d532b`。独立 STL 检查无重复面、零面积面、边界边、非流形边或同向共享边。体积差 −0.00373%。4,328 个原生曲面抽样点最大偏差 0.045512 mm，p99 0.021955 mm，失败 0。源件 revision 与 PRT 摘要一致。导出只读，未保存源件。 [详细数据](../work-items/BUG-130.md)

同一零件以 `MECHDOG_STL_REFINE_ROUNDS=12` 对照，作业 `fa21baac61cc48ba8fa650ce99cbf192` 成功，约 215 秒、1,396,654 片、绕序冲突与翻转均为 0，最大采样偏差 0.037125 mm，体积差 −0.00373%。0.45.1 受测工作区基于同一提交，dirty，源码指纹 `715a1325de0cb811bdae1095ff7530d35c067de0b89d87d02c9a597f5ba880b2`。两次导出均通过常规桥接通道逐次提交和轮询。源件 SHA256 为 `1de8201d78c99a28366f660b993b0f0a107646493557dbd7a77f8f58b970da7a`，前后一致。

装配 STL、Creo 9 与 Creo 12.4 的本版编译和实机、WorkBuddy 黑盒、更早的 `bulb_verified_03989988` 夹具和全曲面偏差上界待验证。

## 开发检查

`bridge.py build`、`tools/dev_check.py --work-item BUG-130 --skip-unit` 通过。离线 stdio MCP 契约覆盖 111 个工具。`tools/test_stl_export.py` 用当前 Toolkit 头文件和替代 API 实现覆盖 27 个用例。`tools/bench_stl_write.py` 的 20 万片内存流基准测得 7.11 → 0.85 µs/片。发布门禁要求候选工作树全量 unittest 通过，打包时校验本轮 `tools/test_unit.py` 报告。独立解包目录同样执行全量单测，两套测试结果见[发布后核对记录](../development/RELEASE-POSTCHECK-2026-11-07.md)。

## 逐 ID 状态核对

[主台账](../BACKLOG.md) · [开发入口](../DEVELOPMENT.md) · [版本说明](../RELEASE_NOTES_0.45.1.md)

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-130](../work-items/BUG-130.md) | 0.45.1 | v0.45.1 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 已验当前 14 m 样件的闭合和抽样精度，历史样件、装配及其他 Creo 版本待复验。 |

## 附件

- `MCP_CREO_MechDog-0.45.1-source.zip`
- `MCP_CREO_MechDog-0.45.1-source.zip.sha256`
- `MCP_CREO_MechDog-0.45.1-seed-library.zip`
- `MCP_CREO_MechDog-0.45.1-seed-library.zip.sha256`

`tools/package_seeds.py` 两次生成同一摘要，种子库 9 个种子和 24 个文件。种子包 SHA256 为 `51c41e1e01d712302d639fa9302cf3af871148c7e2bbf8553a27e6d641a0a8f5`。两份同名 sidecar 分别记录各自 ZIP 的实际摘要。

## 远端核对

发布后已从 GitHub 独立下载和校验四件附件。详细时间、标签、附件 SHA256 与解包结果见[发布后核对记录](../development/RELEASE-POSTCHECK-2026-11-07.md)。 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.45.1)
