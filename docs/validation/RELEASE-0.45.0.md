# 发布记录 v0.45.0

2026-11-25，MINOR，公开工具数 111。上一版本：0.44.1（`v0.44.1`，提交 `5e04dcd8204759cd2eaed13aeadbb80661e307cc`）。

## 验收范围

Windows x64、Python 3.12.10、Creo 10.0.0.0（release 42）、匹配 Toolkit SDK 和 MSVC x64。专项回归使用版本为 0.45.0 的同一组运行时源码，冻结于开发提交 `25bfca9c543b26e10ea8db7fe015ff835bff57bb`。前三个启动报告在源码提交前执行，使用相同的 0.45.0 源文件。执行器源码指纹 `bb54c3f1c8637997bc08f22d5e3239a541f6656c0fdecd7d957926a2ebfdabf4`，SHA256 `3a09da5e9570715cb0ef629bb45ba988a60c70af42a5d306e9e0151254609213`。完整机器证据保存在 `build/release-0.45.0/creo10/`。

六项回归按 Toolkit 单通道串行执行。几何作业用独立临时模型，核对实际几何、保存重载与适用的失败回滚。启动包含自然冷启动与保留现有进程的受控重复查找。Creo 9/12 实机、WorkBuddy 黑盒及六项之外的全项目原生回归待验。原报告的完整摆杆输入、直接放样加料路径实机、历史长链漂移、旧倒角/圆角夹具以及两个历史 MCP 版本在同一有向轴下的对跑仍待验证。

| 条目与命令 | 本轮结果 | 机器证据及 SHA256 |
| --- | --- | --- |
| BUG-191 `tools/test_add_volume_guard.py` | 8 个作业，净体积 2004 → 206 mm³ 的作业 `bf96847dbc0a4616a9d5d87f9d90ff2b` 按预期拒绝，整单回滚，revision 仍为 2，重载恢复 2003 mm³。正常增长和零净增量通过。 | `add-volume.json` `63c59fe48e55e39a17880e7f14f4423e248a0810acec02dbe5e0d57ed36da282` |
| FEAT-078 `tools/test_solid_bounding_box.py` | 19 个作业通过。覆盖切齿、贯穿槽、回转壳、无实体曲面、直接与嵌套旋转装配以及保存重载复查。嵌套装配作业 `f0d10f43d0e5499dad2788fbf800af07`。 | `solid-bbox.json` `5cc3a9dcb928aacad72fa2bba77ec63e8dd62897db191d87549ab885a27cf179` |
| BUG-108 `tools/test_auto_sketch_position.py` | 9 个作业。R12 圆心 `(0, −0.092)` 保持原坐标，替换及重载通过。创建和替换的两个紧容差反例拒绝且回滚。只读回滚复查为 `685f5b0c73b74ed4bc6dc5d070a9884e`。 | `auto-sketch.json` `cec7eee59bf2c005d3b03aa74eb8f76c7794887fa456c7198acce0581096fe49` |
| BUG-102 `tools/test_draft_direction.py` | 6 组共 18 个作业通过。默认底面引用正 11° 向内，反转角度或 `flip` 后向外。重载两种自由端半径为 2.416859 与 3.583141 mm，显式基准轴两向也通过。默认正角作业为 `5c0ab9cf059b470ca229773f1d348cd1`。 | `draft.json` `5e4d53a4ceab8cf018b7d36d5fe322de74426abb61b180837e6b20b9e20a2b04` |
| BUG-094 `build/bug094_datum_angle_probe.py` | 3 个作业通过。RIGHT 绕实测 ±Z 的 ±54° 法向、纯旋转过轴及 `−8.65981 mm` 偏移位置已核对。只读重载作业 `bb2eb955b5c0435a80dd7a9c006f8940`。 | `datum-angle.json` `ccfc55e624f73769ace20d629386889858e3bf78d257f0e7fdb1d7d2b9cdf3c9` |
| BUG-170 `build/bug170_startup_live.py` | 自然冷启动一次拉起，前 7 次返回 `-4`，第 8 次连上。受控短暂失联第 2 次连上，持续失联保持原生 `-4` 证据，10 s 用例以 `startup_timeout` 结束。 | `startup-natural.json` `eaddd389c71ba07df88d3626ea132f2389416ebb3d7a06a6bb8023e73dd399f0`，`startup-delayed.json` `04f100e4a6e5ec8924d595f201a56adddc7fa46945ec6ecf484c9b09b1891f3b`，`startup-unreachable.json` `9b189fa752598f0d395fe23fd6cd3a72f7533554f4f8b5bbb723dd7e4a1e0314`，`startup-timeout.json` `0baf32c8b0acad3e49d35c43dbd01ea9079a626124b3f5f162b79b6abfbd70fd` |

## 开发检查与打包

候选的 `bridge.py build` 和 `tools/dev_check.py --work-item BUG-191 --skip-unit` 已通过。离线 stdio 契约验证 111 个工具，开发检查源码指纹为 `954816bb3112563c83d5e7c390f32658e2ea289436d70ad1b26deaa747e9b265`。干净候选的全量单测执行 `tools/test_unit.py`，通过后由 `tools/package.py --unit-report` 同时校验提交、版本、运行状态和源码指纹；源码 ZIP 生成后按 2448 个文件与工作树逐字节比对（`build/release-0.45.0/source-tree-check.json`）。解包后的独立安装复验未执行：本机安全策略禁止 `reg.exe`，MSVC/Windows SDK 预检在临时目录内失败，属环境限制，不计为通过。候选结果见[发布后附件核对记录](../development/RELEASE-POSTCHECK-2026-11-07.md)。

## 逐 ID 状态核对

主台账的状态保留各工作卡历史余项，交付版本对应下表的本次范围。 [主台账](../BACKLOG.md) · [开发入口](../DEVELOPMENT.md) · [版本说明](../RELEASE_NOTES_0.45.0.md)

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-191](../work-items/BUG-191.md) | 0.45.0 | v0.45.0 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 加料体积保护、整单回滚和重载已验，摆杆原案定因待验。 |
| [FEAT-078](../work-items/FEAT-078.md) | 0.45.0 | v0.45.0 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 实体面包围盒及旋转装配已验，外部原计划和其他环境待验。 |
| [BUG-108](../work-items/BUG-108.md) | 0.45.0 | v0.45.0 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 默认草图创建、替换、拒绝和重载已验，历史长链漂移与显式坐标刚体放行待验。 |
| [BUG-102](../work-items/BUG-102.md) | 0.45.0 | v0.45.0 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 拔模方向和回执已验，历史带倒角、圆角原夹具 `-1` 待验。 |
| [BUG-094](../work-items/BUG-094.md) | 0.45.0 | v0.45.0 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 已验当前有向轴角度和重载，历史版本在同一有向轴下的对跑待验。 |
| [BUG-170](../work-items/BUG-170.md) | 0.45.0 | v0.45.0 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 部分交付，剩余待验收 | 冷启动、持续不可达和超时已验，旧 Creo 9 升级现场及 Explorer 实际复核 worker 待验。 |

## 附件

- `MCP_CREO_MechDog-0.45.0-source.zip`
- `MCP_CREO_MechDog-0.45.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.45.0-seed-library.zip`
- `MCP_CREO_MechDog-0.45.0-seed-library.zip.sha256`

`tools/package_seeds.py` 两次构建同一内容。默认记录校验通过，种子包含 24 个文件和 9 个种子。种子包 SHA256 为 `1ab6d9892f764a019642a1595f59c4f8de64f04933f6657da8597abab80fa73f`。两份同名 sidecar 分别记录各自 ZIP 的实际摘要。 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.45.0)

## 远端核对

发布后执行，当前未验证。下载、标签、前版身份比较和解包实测记录见[发布后附件核对记录](../development/RELEASE-POSTCHECK-2026-11-07.md)。
