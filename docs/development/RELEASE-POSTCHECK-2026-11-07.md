# 发布后附件核对记录（2026-11-07）

本文件补记 [DEV-075](../work-items/DEV-075.md) 指出的缺口：`RELEASING.md` 第 7 步要求「发布后用 `gh release view` 或 `tools/check_release_assets.py --tag <tag>` 核对远端恰有四个附件、两个 sidecar 与对应远端 ZIP 摘要一致，核对结果写入发布记录」，但此前只在各版 `RELEASE-*.md` 里记结论，没有可复核的发布后留存。原有小节记录**发布之后**对远端实际对象的重新下载与重算结果；2026-11-08新增小节另标历史索引、外部元数据和未核验事实；发布前的本地打包、CI 与验收结论仍以各版版本说明和发布记录为准。

## v0.43.0（2026-11-24，打包时点）

- [BUG-183](../work-items/BUG-183.md)、[FEAT-082](../work-items/FEAT-082.md)、[BUG-184](../work-items/BUG-184.md)、[FEAT-083](../work-items/FEAT-083.md) 与 [BUG-185](../work-items/BUG-185.md) 交付：原生 `solved_section_area_mm2`、闭合 B 样条草图 `b_spline_cut_risk` 与 `blind`/`symmetric` `cut_volume_check`；JPEG 全正交视图 `right`/`left`/`back`/`bottom` 与 3×3 右手正交 `view_matrix`；草图 `geometry_deviation` 逐点位移向量、`compact` 超阈 `displaced_sample` 与 `autodim` 强拒说明；`ExtrudeOp.region` 曲线感知 `interior_point_yz_mm` 内点选区；`creo_get_job` 参数 schema 前置条件与报错指引；本机 Creo 10 实机 3/3 通过并保存重载。见[版本说明](../RELEASE_NOTES_0.43.0.md)及[发布记录](../validation/RELEASE-0.43.0.md)。
- 附件计划：`MCP_CREO_MechDog-0.43.0-source.zip`、`MCP_CREO_MechDog-0.43.0-source.zip.sha256`、`MCP_CREO_MechDog-0.43.0-seed-library.zip`、`MCP_CREO_MechDog-0.43.0-seed-library.zip.sha256`。种子包 SHA256 为 `b8b8408f614088ce1c3c67a12ea55fefe5dfe4fe19c2297e2024e2e3f0ebcc2f`。两份同名 sidecar 分别记录对应 ZIP 的实际摘要。
- 远端核对发布后执行，当前未验证。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.43.0)
- **发布后远端核对（2026-11-24）**：Release id `456439582`（创建 `2026-11-24T07:39:58Z`、发布 `2026-11-24T07:41:46Z`），附注标签 `v0.43.0`（对象 `6df0d95e8a0585d7bc0388fd4686ef5eda6d4439`）指向 `fc64e3bcb7956d68f0b167f0e0f22c5f987f5831`。`python -X utf8 tools/check_release_assets.py --tag v0.43.0` 返回 exit 0（四附件下载核验、两份 sidecar 与正文自证全部一致）：源码包 `d4f0e993a87c596550cef22cfd7ec5783c5f2432107455407282c9a39cc1e2f4`（12,117,567 字节，sidecar `bb7eafb1058ca9f40fde003515a67d9e4afa35396dcb43850b2a224c816cb70b`），种子包 `b8b8408f614088ce1c3c67a12ea55fefe5dfe4fe19c2297e2024e2e3f0ebcc2f`（493,442 字节，sidecar `07bab14b60c8d701473692e79c6ff92b1eba1044643f2f0dae5a629b44efd8bc`）。

## v0.42.0（2026-11-24，打包时点）

- [BUG-179](../work-items/BUG-179.md)、[BUG-180](../work-items/BUG-180.md)、[FEAT-080](../work-items/FEAT-080.md)、[BUG-181](../work-items/BUG-181.md)、[FEAT-081](../work-items/FEAT-081.md) 与 [BUG-182](../work-items/BUG-182.md) 交付：`ChamferOp.propagate` 与实测倒角长度/面积；单/多边 `round` 失败几何诊断与凹凸 `round_kind`；`ShellOp.body_id` 单实体抽壳、`MirrorOp` 替代指引与 `creo_inspect_model` 分页 `total_count`/`page_count`；`ExtrudeOp.region` 交点分割与精确 Boehm B 样条细分；G2 几何级 `g2_verification` 曲率验证；装配面选择器 `suggested_reference` 与 `assembly_origin_mm`/`nearest_coordinate_space`；本机 Creo 10 实机 5/5 通过并保存重载。见[版本说明](../RELEASE_NOTES_0.42.0.md)及[发布记录](../validation/RELEASE-0.42.0.md)。
- 附件计划：`MCP_CREO_MechDog-0.42.0-source.zip`、`MCP_CREO_MechDog-0.42.0-source.zip.sha256`、`MCP_CREO_MechDog-0.42.0-seed-library.zip`、`MCP_CREO_MechDog-0.42.0-seed-library.zip.sha256`。种子包 SHA256 为 `23ba2e8f0f7599360a9f4ff3cc13c4ab8378335a905de9966f3171a1b975b4f3`。两份同名 sidecar 分别记录对应 ZIP 的实际摘要。
- 远端核对发布后执行，当前未验证。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.42.0)
- **发布后远端核对（2026-11-24）**：Release id `456324195`（创建 `2026-11-24T04:56:52Z`、发布 `2026-11-24T04:57:12Z`），附注标签 `v0.42.0`（对象 `90e775ab289daeb233546ee9d1071e9edff96d89`）指向 `be2d634629f21247de1548992fdcc27fc9ea9db4`。`python -X utf8 tools/check_release_assets.py --tag v0.42.0` 返回 exit 0（四附件下载核验、两份 sidecar 与正文自证全部一致）：源码包 `e1fa32599227ceddc9a75d57dc410eb68dfd993bba2f38554b6daf21ffdef7c6`（12,080,969 字节，sidecar `32f563bfd9a67c6a572bf101cc1027f980582d15330ad31801e7d24f94532b49`），种子包 `23ba2e8f0f7599360a9f4ff3cc13c4ab8378335a905de9966f3171a1b975b4f3`（493,442 字节，sidecar `dd0554e12b3e7abcfba65a6468d649c42ae3575a686e427c2cfaca61f513ed4b`）。

## v0.41.0（2026-11-24，打包时点）

- [BUG-175](../work-items/BUG-175.md)、[BUG-176](../work-items/BUG-176.md)、[FEAT-078](../work-items/FEAT-078.md)、[FEAT-079](../work-items/FEAT-079.md)、[BUG-177](../work-items/BUG-177.md) 与 [BUG-178](../work-items/BUG-178.md) 交付：BUG-170 单测假时钟消抖；整圆棱边选择器 `full_circle:true`、接缝/极值 `point_mm` 消歧与单点选弧；`creo_inspect_model` 总表面积、逐面面积、包围盒与合并计数；多集 `round`/`chamfer` 失败逐集定位；优弧 `sweep_deg`、`spline` 数值面积与基准面文档；`feature_state` 依赖展开、`component_changes` 1e-12 浮点容差与 `creo_execute_plan` 空操作指引；本机 Creo 10 实机 4/4 通过并保存重载。见[版本说明](../RELEASE_NOTES_0.41.0.md)及[发布记录](../validation/RELEASE-0.41.0.md)。
- 附件计划：`MCP_CREO_MechDog-0.41.0-source.zip`、`MCP_CREO_MechDog-0.41.0-source.zip.sha256`、`MCP_CREO_MechDog-0.41.0-seed-library.zip`、`MCP_CREO_MechDog-0.41.0-seed-library.zip.sha256`。种子包 SHA256 为 `af563439edba0e1682f03ea78c1d9459d9bbd872bbcc1b59adcf27b95415df09`。两份同名 sidecar 分别记录对应 ZIP 的实际摘要。
- 远端核对发布后执行，当前未验证。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.41.0)
- **发布后远端核对（2026-11-24）**：Release id `456259150`（创建 `2026-11-24T03:09:13Z`、发布 `2026-11-24T03:09:42Z`），附注标签 `v0.41.0`（对象 `3919b9332f1ddab115f49ea1aa8442e91743f3d6`）指向 `93003cc40ddf3087a4dc2d74200909abe7c63776`。`python -X utf8 tools/check_release_assets.py --tag v0.41.0` 返回 exit 0（四附件下载核验、两份 sidecar 与正文自证全部一致）：源码包 `1ebf7d2aaf23cf3d54bf3eed22561c71b6783e23ffae2f310861dbffb20abefb`（12,021,391 字节，sidecar `ec15fbc6fe4b92ff29e15a64c0132d598c1808e071367967204505e0020b027d`），种子包 `af563439edba0e1682f03ea78c1d9459d9bbd872bbcc1b59adcf27b95415df09`（493,442 字节，sidecar `37c0c9d62b945594e51fd43c5b3499e183ecd5daa25a2587284a3ba1337a58bc`）。

## v0.40.0（2026-11-23，打包时点）

- [BUG-171](../work-items/BUG-171.md)、[BUG-172](../work-items/BUG-172.md)、[BUG-173](../work-items/BUG-173.md) 与 [BUG-174](../work-items/BUG-174.md) 交付：恢复阶段超时写出 `recovery_phase_timeout` 结构化结果、消除 `restore_baseline` 重复二次巡检、恢复预算扩至 1800 s 并按 edges/features/surfaces 自适应、终态 `recovery_pending` 返回 `terminal_unconfirmed` 指引；消除单次作业 10+ 次冗余全量 `inspection()` 与逐半边 `fflush()` 刷盘；单轴倾斜三点基准面草图自动创建正交辅助锚定面并精准归因 `ProSectionSolve` 错误；`dump_plan_operations` 保留显式 `chamfer_type`、盲切新增 `cut_volume_check` 低去料告警、runner 尝试 `CREATE_BREAKAWAY_FROM_JOB` 并披露 `runner_detached_from_job`；本机 Creo 10 实机 4/4 通过并保存重载；归档 0.35.8 三份反馈原件。见[版本说明](../RELEASE_NOTES_0.40.0.md)及[发布记录](../validation/RELEASE-0.40.0.md)。
- 四件附件为 `MCP_CREO_MechDog-0.40.0-source.zip`、`MCP_CREO_MechDog-0.40.0-source.zip.sha256`、`MCP_CREO_MechDog-0.40.0-seed-library.zip`、`MCP_CREO_MechDog-0.40.0-seed-library.zip.sha256`。种子包 SHA256 为 `507bd0019650dd397046b1ed2cfb735a4f840a4174487b45dab55e536e8db77f`。两份同名 sidecar 分别记录对应 ZIP 的实际摘要。
- 远端核对发布后执行，当前未验证。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.40.0)

### 发布后核对

- 2026-11-23 按 `python -X utf8 tools/check_release_assets.py --tag v0.40.0` 重新下载并重算：Release id `455632891`（`created_at=2026-11-23T15:44:41Z`、`published_at=2026-11-23T15:45:26Z`，非 draft、非 prerelease），四件附件齐全，两份 sidecar 与对应 ZIP 摘要及远端 API digest 一致，Release body 自证通过（exit 0）；源码包 `78ebfc8f9d93a6b3edf9fa7eb3079e2550c0ef74d2e5e28c9560a794a40ab56c`（11,971,720 字节，sidecar `aae5ef20a537cefc8426fe26265e1bbf9fc29ddcdaf782182571a772718f56a1`），种子包 `507bd0019650dd397046b1ed2cfb735a4f840a4174487b45dab55e536e8db77f`（493,442 字节，sidecar `b80175c9d34fe426922319d5c20ff644715959f051ec256718c8df66eb4ceb69`）。附注标签 `v0.40.0`（对象 `890b21c31ae7be9177e7ff5b0e2d2da185b05891`）指向 `9b7bdaa84675fef364972240a8f3d7c7677e2361`，核对时远端 `main` 与该提交一致。

## v0.39.0（2026-11-23，打包时点）

- [BUG-170](../work-items/BUG-170.md)、[BUG-166](../work-items/BUG-166.md)、[FEAT-076](../work-items/FEAT-076.md) 与 [FEAT-077](../work-items/FEAT-077.md) 交付：升级/重启后 `-4` 旧会话诊断与 `force_new_session`；跨会话恢复解死锁、新增 `abandon_unknown_recovery`、自适应/可配恢复预算与 `blocking_operation="recovery_pending"`；边选择器 `feature` 过滤与 `creo_inspect_model(near=...)`；零件 JPEG 预览隐藏基准面及更新检查 15 s 默认预算与 `advisory=true`；本机 Creo 10 实机 5/5 通过并保存重载；归档 0.36.0 反馈原件并补录 [BUG-152](../work-items/BUG-152.md) 外部确认。见[版本说明](../RELEASE_NOTES_0.39.0.md)及[发布记录](../validation/RELEASE-0.39.0.md)。
- 四件附件为 `MCP_CREO_MechDog-0.39.0-source.zip`、`MCP_CREO_MechDog-0.39.0-source.zip.sha256`、`MCP_CREO_MechDog-0.39.0-seed-library.zip`、`MCP_CREO_MechDog-0.39.0-seed-library.zip.sha256`。种子包 SHA256 为 `ef3724f92156efa5b7b01df55b9019eb541fd161ea769291793e9a5b83312587`。两份同名 sidecar 分别记录对应 ZIP 的实际摘要。
- 远端核对发布后执行，当前未验证。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.39.0)

### 发布后核对

- 2026-11-23 按 `python -X utf8 tools/check_release_assets.py --tag v0.39.0` 重新下载并重算：Release id `455465647`（`created_at=2026-11-23T13:28:09Z`、`published_at=2026-11-23T13:29:02Z`，非 draft、非 prerelease），四件附件齐全，两份 sidecar 与对应 ZIP 摘要及远端 API digest 一致，Release body 自证通过（exit 0）；源码包 `d5350f3db3e1a9c9fd3270180bd18b48a4ecb9ce1d25d2406fac1b0cf5e6af51`（11,896,705 字节，sidecar `525eae50c63ef4e026ab6ca82d68395ba85f0bea1ad9481d8bc6d230dd256151`），种子包 `ef3724f92156efa5b7b01df55b9019eb541fd161ea769291793e9a5b83312587`（493,442 字节，sidecar `fc4a178d8baac52e84d5413096023cab0bee5d862b62dd96bd56218be417d8bb`）。附注标签 `v0.39.0`（对象 `6a311eedf5b66d9e9f974806a519c46c7b5a9e6c`）指向 `7518f0fa2b60287319d2e78e26f1385c9b9ee34b`，核对时远端 `main` 与该提交一致。

## v0.38.0（2026-11-23，打包时点）

- [BUG-169](../work-items/BUG-169.md) 与 [FEAT-075](../work-items/FEAT-075.md) 交付：`extrude` 等操作全量与 compact 回执统一回填 `feature_id`；`linear_pattern` 双层拒绝草图/基准及零实体面 leader（`LINEAR_PATTERN_NON_SOLID_LEADER`）与别名/原生类型冲突（`LINEAR_PATTERN_LEADER_ALIAS_MISMATCH`）并回执 `leader_kind`/`leader_surface_count`；`extrude mode="cut"` 开放单实体 `scope` 与 `through_all` 组合（含 `symmetric` 与 `-5778`）；本机 Creo 10 实机 8/8 + `test_linear_pattern` 3/3 回归全部通过并保存重载；归档 0.35.8 反馈原件并补录 [BUG-150](../work-items/BUG-150.md) 外部 `frigate_v4` 验证。见[版本说明](../RELEASE_NOTES_0.38.0.md)及[发布记录](../validation/RELEASE-0.38.0.md)。
- 四件附件为 `MCP_CREO_MechDog-0.38.0-source.zip`、`MCP_CREO_MechDog-0.38.0-source.zip.sha256`、`MCP_CREO_MechDog-0.38.0-seed-library.zip`、`MCP_CREO_MechDog-0.38.0-seed-library.zip.sha256`。种子包 SHA256 为 `f01e832b9a8b7ea3eef7f845f53af3502c1b3656e1896a90ab02f76bb6a36223`。两份同名 sidecar 分别记录对应 ZIP 的实际摘要。
- 远端核对发布后执行，当前未验证。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.38.0)

### 发布后核对

- 2026-11-23 按 `python -X utf8 tools/check_release_assets.py --tag v0.38.0` 重新下载并重算：Release id `455370017`（`created_at=2026-11-23T12:05:56Z`、`published_at=2026-11-23T12:06:53Z`，非 draft、非 prerelease），四件附件齐全，两份 sidecar 与对应 ZIP 摘要及远端 API digest 一致，Release body 自证通过（exit 0）；源码包 `c3de65dcccacc0e7879194b7cfcde941b1889e0a4bbd4fd4a467cbbc6d1f0e71`（11,851,768 字节，sidecar `3d785a3e88422747470f5a945e09426e18c0ed487c9de9fb822481a98dacbbd9`），种子包 `f01e832b9a8b7ea3eef7f845f53af3502c1b3656e1896a90ab02f76bb6a36223`（493,442 字节，sidecar `d587e1d0dcd5a6fe16942bd752a9fc910714ea3b92fc6c0eb4e3e65362573bb5`）。附注标签 `v0.38.0`（对象 `b7605e9d4309dbb8bfd3c2f7443898264fa48d7e`）指向 `266f8a014d60856dff598a49cac457fd24791bc7`，核对时远端 `main` 与该提交一致。

## v0.37.1（2026-11-23，打包时点）

- [BUG-151](../work-items/BUG-151.md) 收口：`tools/test_mcp.py` 补齐实机启动等待、`--offline` 纳入 `dev_check` 离线门禁并完成本机 Creo 10 全模式与 `--create` 实机验收，清理其余 9 个 `tools/` 脚本的 `creo_capabilities` 分页契约漂移与 `mcp_readiness` 过渡态，放宽 `test_startup_reboot` 2 s 等待并归档 0.35.8 反馈原件。见[版本说明](../RELEASE_NOTES_0.37.1.md)及[发布记录](../validation/RELEASE-0.37.1.md)。
- 四件附件为 `MCP_CREO_MechDog-0.37.1-source.zip`、`MCP_CREO_MechDog-0.37.1-source.zip.sha256`、`MCP_CREO_MechDog-0.37.1-seed-library.zip`、`MCP_CREO_MechDog-0.37.1-seed-library.zip.sha256`。种子包 SHA256 为 `69e9f82e20b25e1e37bd8b3c2e3de11d60fe7b088efbf551a1e244c2ac0b4d13`。两份同名 sidecar 分别记录对应 ZIP 的实际摘要。
- 远端核对发布后执行，当前未验证。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.37.1)

### 发布后核对

- 2026-11-23 按 `python -X utf8 tools/check_release_assets.py --tag v0.37.1` 重新下载并重算：Release id `455310549`（`created_at=2026-11-23T11:08:18Z`、`published_at=2026-11-23T11:09:11Z`，非 draft、非 prerelease），四件附件齐全，两份 sidecar 与对应 ZIP 摘要及远端 API digest 一致，Release body 自证通过（exit 0）；源码包 `e3bf012b8dfa152baa004681dafa4d0af0d514d1842d24257ef54b9defecb72a`（11,816,427 字节，sidecar `608ad60060c35f730b90f0c3f321366673c2eac5fc41a977eae32355d00d5cb3`），种子包 `69e9f82e20b25e1e37bd8b3c2e3de11d60fe7b088efbf551a1e244c2ac0b4d13`（493,442 字节，sidecar `53fb9a45b89f050a1ed17b2a3e5e18a716c2d04c02cc01fb3f09f9f8fbf493f7`）。附注标签 `v0.37.1`（对象 `b7af69cc3eb01afe0a8c98bc8961f00ffeb49225`）指向 `87cade1e24c91140d97789516b2ff92b49518e86`，核对时远端 `main` 与该提交一致。

## v0.37.0（2026-11-23，打包时点）

- [BUG-155](../work-items/BUG-155.md)、[BUG-156](../work-items/BUG-156.md)、[BUG-157](../work-items/BUG-157.md)、[BUG-158](../work-items/BUG-158.md)、[BUG-159](../work-items/BUG-159.md)、[BUG-160](../work-items/BUG-160.md)、[BUG-161](../work-items/BUG-161.md) 交付 0.35.5 反馈 P0 批次；BUG-159 为部分交付，内核拉伸转 [BUG-165](../work-items/BUG-165.md)。见[版本说明](../RELEASE_NOTES_0.37.0.md)及[发布记录](../validation/RELEASE-0.37.0.md)。
- 四件附件为 `MCP_CREO_MechDog-0.37.0-source.zip`、`MCP_CREO_MechDog-0.37.0-source.zip.sha256`、`MCP_CREO_MechDog-0.37.0-seed-library.zip`、`MCP_CREO_MechDog-0.37.0-seed-library.zip.sha256`。种子包 SHA256 为 `0fe2c5fb197fedfa917843d189a9ba533b3b514af10cbf6324939d0bd33dc67b`。两份同名 sidecar 分别记录对应 ZIP 的实际摘要。
- 打包时远端核对待执行，实际结果见下节。 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.37.0)

### 发布后核对

- 2026-11-23 按 `tools/check_release_assets.py --tag v0.37.0` 重新下载并重算：Release id `455171815`（2026-11-23T08:48:50Z），四件附件齐全，两份 sidecar 与对应 ZIP 摘要一致，Release body 自证通过；源码包 `94f0aa1683c0c4b32d4519669f3215b715d2cd85af40b7b6c135e0fb2ecf5ffc`，种子包 `0fe2c5fb197fedfa917843d189a9ba533b3b514af10cbf6324939d0bd33dc67b`。附注标签 `v0.37.0`（对象 `6180aed4c26c7722e6cbe3789a5d741505c81b8f`）指向 `5932e20d2eba2760325f666ed1ca5b4f9851df83`，远端 `main` 与该提交一致。

## v0.36.1（2026-11-23，打包时点）

- [BUG-151](../work-items/BUG-151.md) 修复自带 stdio 冒烟脚本 `tools/test_mcp.py` 未适配 `creo_capabilities` compact 分页契约导致的必然失败。见[版本说明](../RELEASE_NOTES_0.36.1.md)及[发布记录](../validation/RELEASE-0.36.1.md)。
- 四件附件为 `MCP_CREO_MechDog-0.36.1-source.zip`、`MCP_CREO_MechDog-0.36.1-source.zip.sha256`、`MCP_CREO_MechDog-0.36.1-seed-library.zip`、`MCP_CREO_MechDog-0.36.1-seed-library.zip.sha256`。种子包 SHA256 为 `c37d6c7dba91624f315761e24a86f0e806a8dafec9b44b94dd67fd47087ff630`。两份同名 sidecar 分别记录对应 ZIP 的实际摘要。
- 打包时远端核对待执行，实际结果见下节。 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.36.1)

### 发布后核对

- 本节记录发布之后对远端对象的重新下载与摘要重算结果；打包时点尚无可填内容，故此处只留标题。

#### 核对结果

- [v0.36.1](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.36.1) 已发布为正式版，并作为远端 `latest` 返回。Release id `455098850`，`published_at=2026-11-23T07:21:15Z`，`created_at=2026-11-23T07:34:17Z`，四个附件均在。
- 远端附注标签对象 `094ac5878ae2eb4d61f51562c0fa7f63c5cec92d` 指向 `a9bf80d3036e597258af917f80cffd1f7ca51220`，远端 `main` 在核对时指向同一提交。本地标签对象已按远端逐字节重建为同一 SHA。
- `python -X utf8 tools/check_release_assets.py --tag v0.36.1` 于 `2026-11-23T07:22Z`（`2026-11-23T15:22+08:00`）退出，退出码为 0：四个附件重新下载后实算摘要与各自 sidecar 一致，Release 正文自证通过。首次运行曾因正文缺少“源码包摘要记录在同名 sidecar 中”一句被拒，补该句后复核通过；仓库内的[版本说明](../RELEASE_NOTES_0.36.1.md)同步了同一句，使正文与文件一致。
- 发布通道：本机到 `github.com` 的 git 传输不可用（代理 CONNECT 成功但 TLS 握手超时，SSH 无可用密钥且令牌无 `admin` 无法登记部署密钥）。提交改由 Git Data API 逐对象重建，四个提交的 SHA 与本地逐一断言一致后才移动 `refs/heads/main`；标签对象与 Release 由 REST API 创建，四个附件经 `uploads.github.com` 上传。`api.github.com` 可达，其余流量不受影响。

| 远端附件 | 字节 | 实算 SHA256 / API digest |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.36.1-source.zip` | 11,751,401 | `952a5c4f5bed881307ac0a9206f042f7e85b92c3ec50771b4c680a5831b4193a` |
| `MCP_CREO_MechDog-0.36.1-source.zip.sha256` | 101 | `a3272f0154ff770923fa17a4417b441c917585245a90a99f8b1d533f1f0d1494` |
| `MCP_CREO_MechDog-0.36.1-seed-library.zip` | 493,442 | `c37d6c7dba91624f315761e24a86f0e806a8dafec9b44b94dd67fd47087ff630` |
| `MCP_CREO_MechDog-0.36.1-seed-library.zip.sha256` | 107 | `be1580afed8ffca9681ea4995d216e50bfea3dff8ee7dcdb8dc86fff71959d35` |

- 发布前证据：全量单测 4,403 项，0 失败、0 错误、0 跳过，`run_id=f08e18e7e2a0488590cdbab38f0c7318`，源码指纹 `34b7174012c17d2c0aac901cc9cc3cfd3a2ebe3053a49162da04e3fcfa23aa5b`；`tools/dev_check.py --skip-unit --work-item BUG-151` 通过（Ruff 0 发现、clang-format 0 未格式化）；`tools/test_mcp.py --protocol-only` 退出 0（111 工具、契约通过、2 页）。源码包 2,312 个文件。
- 未验证：Creo 9/12、外部模型、WorkBuddy 黑盒，以及 `tools/test_mcp.py` 的完整模式（`creo_session_status` 与 `--create` 需要已连接会话）。

## v0.36.0（2026-11-23，打包时点）

- 受管零件保存与恢复、样条切除诊断、种子放样和同计划选面见[版本说明](../RELEASE_NOTES_0.36.0.md)及[发布记录](../validation/RELEASE-0.36.0.md)。
- 四件附件为 `MCP_CREO_MechDog-0.36.0-source.zip`、`MCP_CREO_MechDog-0.36.0-source.zip.sha256`、`MCP_CREO_MechDog-0.36.0-seed-library.zip`、`MCP_CREO_MechDog-0.36.0-seed-library.zip.sha256`。种子包 SHA256 为 `c43228ac6a8764cd7369fc04ee151ceb4c3ee735063c6052839e72d0146bf25f`。两份 sidecar 分别核对对应 ZIP。
- 打包时远端核对待执行，实际结果见下节。 [GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.36.0)

### 发布后核对

- [v0.36.0](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.36.0) 已发布为正式版并标记为 Latest。Release id `454924862`，`created_at=2026-11-23T02:35:14Z`，`published_at=2026-11-23T02:35:30Z`。GitHub 正文与发布时的 notes 文件一致。
- 远端附注标签对象 `1e0445e349d3c9f155561a2aa64f0b408e5037b3` 指向 `bc2052e27cb34f03af2e9fcea259cf426bac7d5b`。远端 `main` 在核对时指向同一提交。核对时间 `2026-11-23T02:35:53+00:00`（`2026-11-23T10:35:53+08:00`）。
- `python -X utf8 tools/check_release_assets.py --tag v0.36.0` 于 `2026-11-23T02:37:03Z`（`2026-11-23T10:37:03+08:00`）退出，退出码为 0。首次运行在 Windows 默认 GBK 下读取 `gh` 输出的 UTF-8 正文失败，显式使用 UTF-8 后复核通过。四个附件均重新下载，两个 ZIP 的实算摘要与各自 sidecar 和 Release 正文一致。逐个核对了下载件、上传前文件、API digest 和字节数。

| 远端附件 | 字节 | 实算 SHA256 / API digest |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.36.0-source.zip` | 11,692,084 | `baa6b9f1e76a5250b0dd73176958b773a30ede4dd148e0f560f799cb21d33b13` |
| `MCP_CREO_MechDog-0.36.0-source.zip.sha256` | 101 | `8f5864b9c694f80a6a93b163d31336980648d90c7e2f6c858e5c491337e49316` |
| `MCP_CREO_MechDog-0.36.0-seed-library.zip` | 493,442 | `c43228ac6a8764cd7369fc04ee151ceb4c3ee735063c6052839e72d0146bf25f` |
| `MCP_CREO_MechDog-0.36.0-seed-library.zip.sha256` | 107 | `71b9204b7588570fc637a0578098ebc0c8135aa70e1f6dc876d7d5616e4bffa2` |

- 发布工作树的 Ruff、clang-format 和离线 MCP 验收通过。全量单测 4,397 项，0 失败、0 错误、7 跳过。受测提交 `2f98b62ea0e60aede631211f04d8c33f603c2cf4`，`dirty=false`，源码指纹 `9798cd0a764df946a79ffd99e5d71476a917eccf382c583e1a61615cb2106f8d`。发布提交回填了验收摘要，单测源码指纹不变。
- 源码 ZIP 的 2,293 个文件对照发布提交完成核验。独立目录无 `.git` 和本机配置。安装包内 Python 源码后运行 `tools/test_unit.py`，4,389 项，0 失败、0 错误、14 跳过。受测来源为 `distributed_source`，源码指纹 `522583a8c89194ae786ef03e88a13d2a5faa1856f7a12b1e4d8fde4f4d8232c7`。
- 另一独立解压目录运行 `setup.ps1`，Windows x64 / Creo 10.0.0.0 release 42 / 匹配 Toolkit SDK / MSVC x64 原生构建通过。用该安装的 MCP 服务实测两截面种子放样，三种形状均保存重载。矩形参数更新后 7840.000 mm³，切除后 7745.752 mm³，失败回滚通过。恢复矩阵复测限制、原反馈未复现范围及其他 Creo 版本的未测范围见[发布记录](../validation/RELEASE-0.36.0.md)。
- 正式包的恢复矩阵首次运行在深层临时夹具路径写入测试意图文件时遇到 `WinError 206`。复测命令为 `python -m tools.test_model_reconciliation --data-root build/bug001-feat018-recovery/r`。缩短独立夹具路径后，完整恢复矩阵通过。通过作业为 `restore_baseline` `b33e906d451344b5a3e617615a41fe8c`、`accept_saved` `fe24a9dfe4694738a1faead723ddadbe`、`accept_live` `a157d3a3d23e4d6598aa48243245ce62`、`abandon_new` `61fee1c6f46444a3bfaf5705d6faba37`；恢复后写入和失败回滚的断言均通过。
- 核对 BUG-152、BUG-153、BUG-154 和 FEAT-074 的交付状态与工作卡、主台账一致。标签和附件保留打包时点的记录。

## v0.35.8（2026-11-22，打包时点）

- [BUG-150](../work-items/BUG-150.md) 修复初始实体切除作用域。Creo 10 有无作用域均去料 800 mm³，保存重载通过。原护卫舰零去料待原件复现。[发布记录](../validation/RELEASE-0.35.8.md)
- 四件附件为 `MCP_CREO_MechDog-0.35.8-source.zip`、`MCP_CREO_MechDog-0.35.8-source.zip.sha256`、`MCP_CREO_MechDog-0.35.8-seed-library.zip`、`MCP_CREO_MechDog-0.35.8-seed-library.zip.sha256`。种子包 SHA256 为 `46afef284f90b01f76ab50152a2f428b16077561e64a3e8159f266721d397b12`。两份 sidecar 记录各自 ZIP 的摘要。
- Release 地址：https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.8。远端核对发布后执行，当前未验证。

### 发布后核对

- [v0.35.8](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.8) 已发布，Release id `454418748`，`created_at=2026-11-22T12:04:02Z`，`published_at=2026-11-22T12:04:21Z`，正式版。GitHub 正文与本地 notes 文件内容一致。
- 远端标签对象 `93dd34078edcba6a1ee45f701df68e51e6cad6ab` 指向 `ed8ea5141a0574de91ec0b19d171dd22f55ca68b`，核对时远端 `main` 为同一发布提交。元数据核对时间为 `2026-11-22T12:04:54+00:00`（`2026-11-22T20:04:54+08:00`）。
- `python tools/check_release_assets.py --tag v0.35.8` exit 0。四个远端附件下载校验通过，两份 sidecar 与各自 ZIP 相符，Release 正文包含对应摘要并通过校验。下表的 API digest 与发布文件实算一致。

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.35.8-seed-library.zip` | 493,442 | `46afef284f90b01f76ab50152a2f428b16077561e64a3e8159f266721d397b12` |
| `MCP_CREO_MechDog-0.35.8-seed-library.zip.sha256` | 107 | `1c2e8e6409df01ea585dd1b37a7bb4026842742015ef30ebdbc0139eaa619954` |
| `MCP_CREO_MechDog-0.35.8-source.zip` | 11,659,906 | `88f058ce5b7451f4ee0701fdcd04661d09f68bffb106ccd00d4627555425345d` |
| `MCP_CREO_MechDog-0.35.8-source.zip.sha256` | 101 | `9b4dbb005b348aae458c0c8ce286da64cd30dd0e4bd2ca339f0a2d24532effb8` |

- 发布工作树全量单测 4,390 项，0 失败、0 错误、7 跳过。受测提交 `29adc793bef50312228646d2691555ec5610475f`，`dirty=false`，源码指纹 `98ff84c864ea99f67bc568c8b2ebfb24407d1ffc178f5a130abaaaa5ce42923c`。发布提交只回填发布记录，Python 与原生源码差异为空。开发检查的语言与离线 stdio 门禁通过。
- 发布源码包独立解压 2,284 个文件，在无 `.git` 和本机配置的目录中安装并重跑 `tools/test_unit.py`。4,382 项，0 失败、0 错误、14 跳过。指纹 `13d31eae2b4c18b7bec1776d9a1d6ca893cf0d888a02395c800c69bca32dc57c`，来源为 `distributed_source`。
- Creo 10.0.0.0 / release 42、匹配 Toolkit SDK / MSVC x64。发布候选重编通过，原生源码指纹 `2a9ac48959786ff93ef6e7968e8eda8c7a2e123f125548529b9b87ea68da2a06`，worker SHA256 `ebee5129c0846f528e507bc31028fc1d516e544e8a58b245b18ccf0429a6bb18`。800 mm³ 实机作业 unscoped `8a79ef0ff28d45408bdbbb91fe895501`、scoped `77195eaacc894bb8a1bff586d86fda0d`、scoped_mixed `63c4617f71a244489e5f220278bc8650`。三次保存重载均通过，重载树作业 unscoped `c671cdf1f9bc4d82899233446d83a686`、scoped `108f572ff7c6407e96c7f830b1ece0c0`、scoped_mixed `33a4156508ba4f158040f57a779d840b`，显式作用域仍引用 `PRO_BODY/-5778`。正 ID 回归 20 项均通过。缺失 ID 回滚作业 `e08c87c24bc742f7acc11f7dd3f5fa4e`。双体保留对照补切作业 `94c1503f80744f33b72819b0d5245657` 再去料 80 mm³。原护卫舰无作用域零去料待原件复现。
- 已核对 v0.35.7 正式源码包的 `native/third_party/json.hpp` 和第三方许可证与本版逐字节相同。回调及 loader 源码未变。两轮独立构建的 DLL 字节不同，本次验收限于拉伸切除路径。
- 标签内记录保留打包时点内容。此节记录发布后实证，已发布附件冻结。

## v0.35.7（2026-11-22，打包时点快照；发布后核对追加于此）

- 范围：[BUG-149](../work-items/BUG-149.md) 只读作业不再永久占用模型（只读作业从不写 `pending_job`、`creo_cancel_job` 元数据式释放历史占用并回执 `readonly_release`、inspect 报 `readonly_pending`）；公开工具仍 111，无原生改动。发布记录见 [RELEASE-0.35.7](../validation/RELEASE-0.35.7.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py`（含本轮 `run_id`/源码指纹证据门禁）→ 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `2c925e6138f64102666fe6c679520f8522f6dd7e97b3afbae4ba07f9e24f4da2`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.35.7`）。
- 源码包由发布提交源码构建；源码包摘要见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.7`；四个附件为 `MCP_CREO_MechDog-0.35.7-source.zip`、`MCP_CREO_MechDog-0.35.7-source.zip.sha256`、`MCP_CREO_MechDog-0.35.7-seed-library.zip` 与 `MCP_CREO_MechDog-0.35.7-seed-library.zip.sha256`。
- 标签与提交：`main` 提交 `a0aa08dd0f9efd64618868d70634718e88d9792d`，附注标签 `v0.35.7`（tag 对象 `747567a1eeb994f7a6a7ab311c1ea29f69421b99`）指向该提交（`git rev-parse v0.35.7^{commit}` 同值）；远端 `main` 已推进到同一提交（`e62eb3c..a0aa08d`）。
- 发布对象：Release id `454380011`，非 draft、非 prerelease，`created_at=2026-11-22T10:53:44Z`，`published_at=2026-11-22T10:54:27Z`（18:54 +08:00），target `main`，正文 3,982 字符，含四个附件名与「源码包摘要记录在同名 sidecar 中」。
- 远端核对（2026-11-22 18:55 +08:00）：`tools\check_release_assets.py --tag v0.35.7` exit 0，输出 `v0.35.7: four assets downloaded and verified; both sidecars match; release body self-proof verified`（`gh` 经 `HTTPS_PROXY=http://127.0.0.1:10809` 直连成功，未退回 `--dir` 手工通道）。
- 附件逐个列出（未用通配）；远端 API digest、下载后本地实算与 sidecar 逐一致：

| 附件 | 字节 | 远端 API digest / 本地实算 SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.35.7-source.zip` | 11,640,169 | `2a2735a18f0484bd21c0b775681d87b70c37a67f8eb159e3d153fde161a506fc` |
| `MCP_CREO_MechDog-0.35.7-source.zip.sha256` | 101 | `721815876d1a3714b98a9ae2bc480cb7cccc3b4e6202857f2e0c200d0bebe2e5` |
| `MCP_CREO_MechDog-0.35.7-seed-library.zip` | 493,442 | `2c925e6138f64102666fe6c679520f8522f6dd7e97b3afbae4ba07f9e24f4da2` |
| `MCP_CREO_MechDog-0.35.7-seed-library.zip.sha256` | 107 | `61aea629d5118345349a180df53abaa1cbe01f7cd05cfb6120af82c797979560` |
- 正文比对：`gh release view v0.35.7 --json body` 取回的正文与本地 `--notes-file` 内容除末尾换行外逐字相同（3,982 字符）。
- 源码包解压独立验收（发布前完成，2026-11-22 18:35—18:53 +08:00）：解压到 `%TEMP%\mc-0357-extract`（2,278 文件、无 `.git`、无 `config.json`），独立 venv 安装后运行 `tools/test_unit.py`，4,381 项、0 失败、0 错误、14 跳过，解压受测指纹 `03092ee98eb3f1dbe023d803ea5f9ed36ebe73dc1206bcf0bcbe107f3e7092b4`；较工作树 4,389 项少的 8 项全部转为环境跳过。
- 包内快照与 `main` 的差异：冻结源码包内的本段与发布记录仍是打包时点措辞（`remote_verification=pending`、「发布后执行，当前未验证」），以上实际结果、Release id 与提交号只存在于 `main`，不改写、不重传已发布附件。

## v0.35.6（2026-11-22，打包时点快照；发布后核对追加于此）

- 范围：0.35.0 反馈批收口——[FEAT-057](../work-items/FEAT-057.md) 装配质量属性与 occurrence 扫描、[FEAT-073](../work-items/FEAT-073.md) 批量只读查询（公开工具 110→111）、[FEAT-072](../work-items/FEAT-072.md) 会话候选与进程内选定、[BUG-143](../work-items/BUG-143.md) 固体镜像根因、[BUG-145](../work-items/BUG-145.md) 桌面 worker 路径、[BUG-146](../work-items/BUG-146.md) 停滞恢复出口、[BUG-147](../work-items/BUG-147.md) 材质密度归因、[BUG-148](../work-items/BUG-148.md) 多开放轮廓指引。发布记录见 [RELEASE-0.35.6](../validation/RELEASE-0.35.6.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py`（含本轮 `run_id`/源码指纹证据门禁）→ 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `32ea2d0324e329f46bce7ac9dd41bd3086e2b7f151b1227e035038f0b1bd81fe`（24 个文件、9 个种子、493,442 字节，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.35.6`）。
- 源码包由发布提交源码构建；源码包摘要见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.6`；四个附件为 `MCP_CREO_MechDog-0.35.6-source.zip`、`MCP_CREO_MechDog-0.35.6-source.zip.sha256`、`MCP_CREO_MechDog-0.35.6-seed-library.zip` 与 `MCP_CREO_MechDog-0.35.6-seed-library.zip.sha256`。
- 标签与提交：`main` 提交 `13aa9e163da7569c548949de8c8c3b9b8bf3615a`，附注标签 `v0.35.6` 指向该提交（`git rev-parse v0.35.6^{commit}` 同值）；远端 `main` 已推进到同一提交（`919f575..13aa9e1`）。
- 发布对象：Release id `454230616`，非 draft、非 prerelease，`created_at=2026-11-22T05:40:56Z`，`published_at=2026-11-22T05:41:17Z`（13:41 +08:00），target `main`，正文 2,652 字符，含四个附件名与「源码包摘要记录在同名 sidecar 中」。
- 远端核对（2026-11-22 13:41—13:44 +08:00）：`tools\check_release_assets.py --tag v0.35.6` 首次尝试因本机 `gh release download` 30 s 超时与 GitHub API 直连 502 未取得远端结论（如实记为未核对）；改用 `gh release download v0.35.6` 逐个下载四附件到 `build\release-assets\v0.35.6-remote`，再执行 `tools\check_release_assets.py --tag v0.35.6 --version 0.35.6 --dir build\release-assets\v0.35.6-remote --body-file build\release-assets\v0.35.6-body.md`，exit 0，输出 `local_verified: four assets present; both sidecars match (version 0.35.6); release body self-proof verified`。
- 附件逐个列出（未用通配）；远端 API digest、下载后本地实算与 sidecar 逐一致：

| 附件 | 字节 | 远端 API digest / 本地实算 SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.35.6-source.zip` | 11,618,127 | `4cdd0bb47e1590c3424a2f4f8c911be3ba01687d4a7a6c9a286d48a582b9f041` |
| `MCP_CREO_MechDog-0.35.6-source.zip.sha256` | 101 | `fcbd997b87b9188896ad0068771d0af18cb915f7099adce7efa9d425a1ed76da` |
| `MCP_CREO_MechDog-0.35.6-seed-library.zip` | 493,442 | `32ea2d0324e329f46bce7ac9dd41bd3086e2b7f151b1227e035038f0b1bd81fe` |
| `MCP_CREO_MechDog-0.35.6-seed-library.zip.sha256` | 107 | `d8f54519d30cef2d827dc1b63ba29248e9a597f0c950235fd5751dff905e33b8` |
- 正文比对：`gh release view v0.35.6 --json body` 取回的正文与本地 `--notes-file` 内容除末尾换行外逐字相同（2,652 字符）。
- 源码包解压独立验收（发布后，2026-11-22 13:34—13:54 +08:00）：把发布附件解压到 `%TEMP%\mc-0356-extract`（2,273 文件、无 `.git`、无 `config.json`），独立 venv 安装后运行 `tools/test_unit.py`，4,368 项、0 失败、0 错误、14 跳过，解压受测指纹 `96262512a5d847f927d31ecc08bff4fd7bd12ee470d06c6f2f7d3e9c3803ad91`；较工作树 4,376 项少的 8 项全部转为环境跳过。
- 包内快照与 `main` 的差异：冻结源码包内的本段与发布记录仍是打包时点措辞（`remote_verification=pending`、「发布后执行，当前未验证」），以上实际结果、Release id 与提交号只存在于 `main`，不改写、不重传已发布附件。

## v0.35.5（2026-11-21，发布后已核对）

- 范围：[BUG-144](../work-items/BUG-144.md)、[DEV-099](../work-items/DEV-099.md)、[BUG-142](../work-items/BUG-142.md) 随 0.35.5 交付；公开工具仍 110。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py` → 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `fa98100e05aae1573322ad89d6f19b0192c63e008557168a4150bce358456405`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.35.5`）。
- 源码包由发布提交 `9164248` 源码构建；11,516,770 字节，SHA256 `641ed3d2b36d5cbe3ada52862c44b1444d71dcf10a287e025f6aaf8c810aa4b3`，字节数与摘要另写入同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.5`（Release id `453684723`，发布时间 `2026-11-21T12:43:43Z` / 20:43 +08:00）；四个附件为 `MCP_CREO_MechDog-0.35.5-source.zip`、`MCP_CREO_MechDog-0.35.5-source.zip.sha256`、`MCP_CREO_MechDog-0.35.5-seed-library.zip` 与 `MCP_CREO_MechDog-0.35.5-seed-library.zip.sha256`。
- 远端附件核对（2026-11-21 20:43 +08:00 / 12:43Z）：`tools\check_release_assets.py --tag v0.35.5` exit 0，输出 `v0.35.5: four assets downloaded and verified; both sidecars match; release body self-proof verified`；远端 API digest、本地重算与 sidecar 逐一致（源码包 `641ed3d2…4b3`、种子包 `fa98100e…405`）。

## v0.35.4（2026-11-21，发布后已核对）

- 版本与范围：`0.35.4` PATCH，公开工具仍 110；[BUG-133](../work-items/BUG-133.md) 按 Creo 10.0.0.0 / release 42 实机边界把旋转矩阵准入收紧为 `1e-7`：9/8/7 位小数矩阵（残差 `4.5e-10`/`7.664e-9`/`4.755e-8`）可放置并保存重载，`2.241e-7`/`4.890e-7`/`1.129e-6` 均被 `ProAsmcompAssemble`/`ProAsmcompPositionSet` 以 `-2` 拒绝；`rotation_tolerance` 缺省与上限同为 `1e-7`，六位小数矩阵在提交前拒绝并给出残差，矩阵仍不转置、不正交化、不修复。发布记录见 [RELEASE-0.35.4](../validation/RELEASE-0.35.4.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py` → 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `ba556e79d80f18268c38d9b5044ac15a07afa6cc676153dd8e310cc9c9aec325`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.35.4`）。
- 源码包由发布提交源码构建，字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.4`；四个附件为 `MCP_CREO_MechDog-0.35.4-source.zip`、`MCP_CREO_MechDog-0.35.4-source.zip.sha256`、`MCP_CREO_MechDog-0.35.4-seed-library.zip` 与 `MCP_CREO_MechDog-0.35.4-seed-library.zip.sha256`。
- 发布后核对（2026-11-21）：Release id `453623766`，非 draft、非 prerelease，target `main`，`created_at=2026-11-21T10:52:04Z`，`published_at=2026-11-21T10:53:46Z`，正文 2431 字符，含四个附件名与“源码包摘要记录在同名 sidecar 中”。`v0.35.4` tag object `e6e3c334cf73e8315963f64fb9f7c4c5696cf320`，peeled commit `29f9ed277d6436d9a0c6de4d4a1168fd51942444`；远端 `main` 同为 `29f9ed2`。`gh` 不可用、Python urllib 自动下载被网络重置，改用已认证 GitHub API 下载四附件后执行 `tools\check_release_assets.py --tag v0.35.4 --version 0.35.4 --dir build\release-assets\v0.35.4 --body-file build\release-assets\v0.35.4-body.md`，exit 0，输出“local_verified: four assets present; both sidecars match (version 0.35.4); release body self-proof verified”。远端 API 摘要、本地重算与 sidecar 内容逐一致：`MCP_CREO_MechDog-0.35.4-source.zip`（11490057 字节，`681f1b1f…`）、`MCP_CREO_MechDog-0.35.4-source.zip.sha256`（101 字节，`35542bef…`）、`MCP_CREO_MechDog-0.35.4-seed-library.zip`（493442 字节，`ba556e79…`）、`MCP_CREO_MechDog-0.35.4-seed-library.zip.sha256`（107 字节，`59aa5f58…`）。
- 包内快照与 `main` 的差异：冻结源码包内的本段与发布记录仍是打包时点措辞（`remote_verification=pending`），以上实际结果与 `docs/releases/0.35.4.json` 的 `verified` 只存在于 `main`，不改写、不重发已发布附件。

## v0.35.3（2026-11-21，发布后已核对）

- 版本与范围：`0.35.3` PATCH，公开工具仍 110；[BUG-143](../work-items/BUG-143.md) 以开放圆锥套实机跑通非圆柱 mirror → trim → thicken 跨作业标签链与保存重载（quilt 79→99、保留区 687.2181023230302 mm²、加厚 1500.0989754261154 mm³，rev 1→4），并记录闭合锥面 trim 的 `ProContourAreaEval` 面积测量边界；[BUG-113](../work-items/BUG-113.md) 同机受控对照排除外部文件锁，新增 `save_failure.source_checkpoint_readable`/`candidate_readability` 失败瞬间诊断。发布记录见 [RELEASE-0.35.3](../validation/RELEASE-0.35.3.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py` → 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `182d25706e7868680712c2497148d6287957755554ce7d38fcc4fa6fb33be0f5`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.35.3`）。
- 源码包由发布提交源码构建，字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.3`；四个附件为 `MCP_CREO_MechDog-0.35.3-source.zip`、`MCP_CREO_MechDog-0.35.3-source.zip.sha256`、`MCP_CREO_MechDog-0.35.3-seed-library.zip` 与 `MCP_CREO_MechDog-0.35.3-seed-library.zip.sha256`。
- 发布后核对：2026-11-21 执行 `tools\check_release_assets.py --tag v0.35.3`，exit 0，输出“four assets downloaded and verified; both sidecars match; release body self-proof verified”。Release id `453561911`，正文 2975 字符，含四个附件名与“源码包摘要记录在同名 sidecar 中”，种子摘要与 sidecar 一致。远端四个附件——`MCP_CREO_MechDog-0.35.3-source.zip`（11479965 字节，`ffaabb20…`）、`MCP_CREO_MechDog-0.35.3-source.zip.sha256`（101 字节，`cc58a22a…`）、`MCP_CREO_MechDog-0.35.3-seed-library.zip`（493442 字节，`182d2570…`）、`MCP_CREO_MechDog-0.35.3-seed-library.zip.sha256`（107 字节，`5a94e1e1…`）；两份 sidecar 与 ZIP 摘要一致。`v0.35.3` 标签指向提交 `0fa005dc44ac65c9d118e37e1bf9b58b87474486`。

## v0.35.2（2026-11-21，发布后已核对）

- 版本与范围：`0.35.2` PATCH，公开工具仍 110；[BUG-143](../work-items/BUG-143.md) 为 mirror 曲面 `feature` 引用增加 `PRO_QUILT` 创建前拒绝（实机拒绝且会话存活），并补验 mirror/trim 标签跨作业消费与单计划 trim 保存重载；[DEV-098](../work-items/DEV-098.md) 为面选择器零匹配新增只读 `nearest_surfaces`（≤5 条）并保留装配坐标 `requested_coordinate_space` 溯源。发布记录见 [RELEASE-0.35.2](../validation/RELEASE-0.35.2.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py` → 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `094e25eb0d3aaba39d30105eaa7a9a28cb73ebcfc02622a11a792e411ab3d659`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.35.2`）。
- 源码包由发布提交源码构建，字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.2`；四个附件为 `MCP_CREO_MechDog-0.35.2-source.zip`、`MCP_CREO_MechDog-0.35.2-source.zip.sha256`、`MCP_CREO_MechDog-0.35.2-seed-library.zip` 与 `MCP_CREO_MechDog-0.35.2-seed-library.zip.sha256`。
- 发布后核对：2026-11-21 执行 `tools\check_release_assets.py --tag v0.35.2`，exit 0，输出“four assets downloaded and verified; both sidecars match; release body self-proof verified”。远端四个附件——`MCP_CREO_MechDog-0.35.2-source.zip`（11468150 字节，`9ce2ff6b…`）、`MCP_CREO_MechDog-0.35.2-source.zip.sha256`（101 字节，`44863018…`）、`MCP_CREO_MechDog-0.35.2-seed-library.zip`（493442 字节，`094e25eb…`）、`MCP_CREO_MechDog-0.35.2-seed-library.zip.sha256`（107 字节，`25162479…`）；两份 sidecar 与 ZIP 摘要一致。Release 正文 3317 字符，含四个附件名与“源码包摘要记录在同名 sidecar 中”，种子摘要与 sidecar 一致。

## v0.35.1（2026-11-21，发布后已核对）

- 版本与范围：`0.35.1` PATCH，公开工具仍 110；[BUG-142](../work-items/BUG-142.md) 定位 `0xC0000409` 根因（原生构建缺 `/utf-8` → MSVC 按 CP936 解析窄字面量 → 非法 UTF-8 → 严格 `dump` 抛异常 → abort），`bridge.py` 三条 `cl` 命令加入 `/utf-8` 并把 `NATIVE_BUILD_FLAGS /utf-8-v1` 纳入构建指纹；[DEV-098](../work-items/DEV-098.md) 为通用 `geometry_selector` 零匹配新增只读 `geometry_selector_diagnostic.nearest_edges`（≤5 条、按误差再按 id 排序），本机 Creo 10 实机 `candidate_count=12`、`matched_ids=[]`、候选 ids 54/55/56/59/60。发布记录见 [RELEASE-0.35.1](../validation/RELEASE-0.35.1.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py` → 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `ad1d62bfc15e2dd45b1118464df75d19ee3635a871b179e9eaa590ae8b5c0ed4`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.35.1`）。
- 源码包由发布提交源码构建，字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.1`；四个附件为 `MCP_CREO_MechDog-0.35.1-source.zip`、`MCP_CREO_MechDog-0.35.1-source.zip.sha256`、`MCP_CREO_MechDog-0.35.1-seed-library.zip` 与 `MCP_CREO_MechDog-0.35.1-seed-library.zip.sha256`。
- 本批验证：受控夹具 `strict_dump_crash` 复现退出码 `0xC0000409` 与 0 字节文件，替换 handler 下正常发布；重建后 worker 中弯破折号字节由 `E2 80 3F` 变为 `E2 80 94`；`tools/dev_check.py` 全量 4293 项通过、`success=true`；原生冒烟作业 `bea2d8d6…` 保存重载通过。
- 发布后核对：四个附件已在 `v0.35.1` 远端对象上重新下载并重算——`MCP_CREO_MechDog-0.35.1-source.zip` 11453178 字节、SHA256 `c8aacaec4dc814ca4ccf644b8f3b02d26782b20b4e27f15187d910dd49ac696b`；`MCP_CREO_MechDog-0.35.1-seed-library.zip` 493442 字节、SHA256 `ad1d62bfc15e2dd45b1118464df75d19ee3635a871b179e9eaa590ae8b5c0ed4`；两个 sidecar 各含一行 `<64 位 SHA256>  文件名` 且与对应 ZIP 一致。`tools\check_release_assets.py --tag v0.35.1` exit 0（Release 正文自证、附件集合与 sidecar 摘要均通过）；`v0.35.1` 标签指向提交 `9b933cf5507322f7c8693ea6fd6ae74648866e5b`。

## v0.35.0（2026-11-21，发布后已核对）

- 版本与范围：`0.35.0` MINOR 部分交付，公开工具仍 110；交付桌面 `0.33.0` 三份反馈首批——[BUG-143](../work-items/BUG-143.md) 曲面结果回执给实测 `quilt_id` 且同计划 merge/fill 标签可被 `solidify` 消费；[FEAT-071](../work-items/FEAT-071.md) `d1_d2` 两距离倒角；[BUG-142](../work-items/BUG-142.md) 断连前结果预发布与非 UTF-8 容错；[BUG-140](../work-items/BUG-140.md)/[BUG-141](../work-items/BUG-141.md) 启动链修复；[DEV-098](../work-items/DEV-098.md) 诊断语义与文档契约。发布记录见 [RELEASE-0.35.0](../validation/RELEASE-0.35.0.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py` → 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `8f7c1645d7a324f674de6f486bd83aca0f4ad99e5abd50177843fedc6352f02d`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.35.0`）。
- 源码包由发布提交源码构建，字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.35.0`；四附件为 `MCP_CREO_MechDog-0.35.0-source.zip`、`MCP_CREO_MechDog-0.35.0-source.zip.sha256`、`MCP_CREO_MechDog-0.35.0-seed-library.zip` 与 `MCP_CREO_MechDog-0.35.0-seed-library.zip.sha256`。Release id `453417481`，非 draft、非 prerelease，`created_at=2026-11-21T03:40:21Z`，`published_at=2026-11-21T03:41:33Z`，target `main`。
- 发布后核对（2026-11-21）：`tools\check_release_assets.py --tag v0.35.0` → exit 0，「v0.35.0: four assets downloaded and verified; both sidecars match; release body self-proof verified」。远端 API digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.35.0-source.zip` | 11 439 818 | `45ee6b1c230d32ac44a5f168e0e652d41e66d9408846421db8cd09797072c1fc` |
| `MCP_CREO_MechDog-0.35.0-source.zip.sha256` | 101 | `960a5722e63793e7f9a8a429b42eac65783194b8fc6f3a004fd6a9a003d74d85` |
| `MCP_CREO_MechDog-0.35.0-seed-library.zip` | 493 442 | `8f7c1645d7a324f674de6f486bd83aca0f4ad99e5abd50177843fedc6352f02d` |
| `MCP_CREO_MechDog-0.35.0-seed-library.zip.sha256` | 107 | `e5770a1ee63451015de836442c85a06cbe3aaac94d63b10c6ac64952d8ead32b` |

- 远端引用：`git ls-remote --tags origin v0.35.0` → `56a02b71c03c147bcaab28ae624a31dbb8f7fd48 refs/tags/v0.35.0`（注释标签，指向发布提交 `4e42e1d4b7e801894ab296271398e9bd1bb83012`）；发布时远端 `main` 为同一提交。
- 包内快照与 `main` 的差异：已冻结源码包内的 POSTCHECK/发布记录仍是打包时点措辞（`remote_verification=pending`），本段实际结果与 `docs/releases/0.35.0.json` 的 `verified` 只存在于 `main`，不改写、不重发已发布附件。
- 未验证：发布后未重复执行 Creo 实机与 WorkBuddy 黑盒，实机范围以发布前记录为准。

## v0.34.0（2026-11-21，发布后已核对）

- 版本与范围：`0.34.0` MINOR 部分交付，公开工具 109→110；交付 0.31.1/0.32.0 反馈剩余项 + BUG-120 实体化链路收官——[FEAT-070](../work-items/FEAT-070.md) 新增 `creo_redefine_solidify_body`，以 `strategy=new` 重建失效主体参照、解除 `BOW_BULB_SOLID`（feature 250）自锁；[BUG-137](../work-items/BUG-137.md) 隔离 `subprocess.Popen` 消除全量单测 teardown WinError 32，并加“全量通过”口径须 `success=true` 报告的发布门禁；[BUG-138](../work-items/BUG-138.md) 去除验收脚本硬编码工具数 82/84、改以 `creo_capabilities` 为准，`dev_check` 新增离线验收门禁；[BUG-139](../work-items/BUG-139.md) 启动协调器探测超时可配/循环外成功落地/连接相位/预算分段/准入降级/身份归因/文案修复；[DEV-097](../work-items/DEV-097.md) Release 正文自证门禁（四附件名 + sidecar 指引 + 摘要比对，≥0.34.0 强制执行，历史版本祖父化）。发布记录见 [RELEASE-0.34.0](../validation/RELEASE-0.34.0.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py` → 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `b3bfcab0ad754cb087019fda0f763fd020fa98ac23f38475e3189179df971343`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.34.0`）。
- 源码包由发布提交源码构建，字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.34.0`；四附件为 `MCP_CREO_MechDog-0.34.0-source.zip`、`MCP_CREO_MechDog-0.34.0-source.zip.sha256`、`MCP_CREO_MechDog-0.34.0-seed-library.zip` 与 `MCP_CREO_MechDog-0.34.0-seed-library.zip.sha256`。Release id `RE_kwDOU_ueTM4bAM2T`，非 draft、非 prerelease，`created_at=2026-11-20T18:20:17Z`，`published_at=2026-11-20T18:21:23Z`，target `main`。
- 发布后核对（2026-11-21）：`tools\check_release_assets.py --tag v0.34.0` → exit 0，「v0.34.0: four assets downloaded and verified; both sidecars match; release body self-proof verified」。远端 API digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.34.0-source.zip` | 11 349 952 | `ce6e461e678f0df82f6936f364b9ace0ba63475c08827fa11ae2508bb3e4f5dd` |
| `MCP_CREO_MechDog-0.34.0-source.zip.sha256` | 101 | `77811a2052de8a96edd65d8744ea1fe5bfca8e128a88fae21be97ba64d9b6792` |
| `MCP_CREO_MechDog-0.34.0-seed-library.zip` | 493 442 | `b3bfcab0ad754cb087019fda0f763fd020fa98ac23f38475e3189179df971343` |
| `MCP_CREO_MechDog-0.34.0-seed-library.zip.sha256` | 107 | `855e6e6eec56e2ddd22ae88b5054ed1a2c3af5cdaf7f0832ec2d93b064f68c91` |

- 远端引用：`git ls-remote --tags origin v0.34.0` → `9f03d60c81a067da3ccb038b10bbc3070f8124c9 refs/tags/v0.34.0`（注释标签，指向发布提交 `bbd81cdbaa92f7acdc1988d574dfdab832e01bed`）；`git ls-remote origin refs/heads/main` 在发布时为同一提交。
- 包内快照与 `main` 的差异：已冻结源码包内的 POSTCHECK/发布记录仍是打包时点措辞（`remote_verification=pending`），本段实际结果与 `docs/releases/0.34.0.json` 的 `verified` 只存在于 `main`，不改写、不重发已发布附件。
- 未验证：发布后未重复执行 Creo 实机与 WorkBuddy 黑盒，实机范围以发布前记录为准。

## v0.33.0（2026-11-20，发布前快照）

- 版本与范围：`0.33.0` MINOR 部分交付，公开工具仍 109；交付 0.31.1 反馈批——[BUG-134](../work-items/BUG-134.md) `resident_panel` 在 `ProMdlCurrentGet` 为 -8 时改用 `ProMdlInit` 的 board 并先显示模型、面板块补 `model_name`；[BUG-135](../work-items/BUG-135.md) 显式 `accept_unverified_completion` 旁路；[BUG-136](../work-items/BUG-136.md) 装配约束按实际类型要求平面或圆柱面；[DEV-095](../work-items/DEV-095.md) `host_release` 探针与 `unverified_bindings=["payload_sha256"]` 披露；[DEV-096](../work-items/DEV-096.md) `previous_release_commit` 与“上一版本”行及标签三方交叉校验。发布记录见 [RELEASE-0.33.0](../validation/RELEASE-0.33.0.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py` → 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `d53682cc02d3089490977fcac06afea65113e9369b72f7df4c26bd756215cda7`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.33.0`）。
- 源码包由发布提交源码构建，字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.33.0`；四附件为 `MCP_CREO_MechDog-0.33.0-source.zip`、`MCP_CREO_MechDog-0.33.0-source.zip.sha256`、`MCP_CREO_MechDog-0.33.0-seed-library.zip` 与 `MCP_CREO_MechDog-0.33.0-seed-library.zip.sha256`（2026-11-20 12:38Z 发布，release id `452676477`，非 draft、非 prerelease）。
- 发布后核对（2026-11-20 12:38Z）：`tools\check_release_assets.py --tag v0.33.0` → exit 0，「v0.33.0: four assets downloaded and verified; both sidecars match」。远端 API digest、本地重算与 sidecar 内容逐一致：
  - `MCP_CREO_MechDog-0.33.0-source.zip`：11,280,840 字节，`sha256:30c8b1b0bcd4880f2d8a59281b3fa44d15b1c37a3e207735541cdb2ee50a2825`，sidecar 本身 `sha256:6154cc344869b0fc66c0331c9729724efa88b59f0a3fbc2c8f08a76bc3d2b06b`，其内容为同一摘要；
  - `MCP_CREO_MechDog-0.33.0-seed-library.zip`：493,442 字节，`sha256:d53682cc02d3089490977fcac06afea65113e9369b72f7df4c26bd756215cda7`，sidecar 本身 `sha256:8c067c649ee8baa800b6f7b52cb60bdc0d66ca6e4b120f9b20e8b35298c5fab3`，其内容与 `docs/seed_package.json` 一致。
- 远端引用：`git ls-remote --tags origin v0.33.0` → `629f5db8acc9c09bb68f2bd4486d751a1d45cbca refs/tags/v0.33.0`（注释标签，指向提交 `613cc4bc3424ce066fb255d5781aa157b23f35a3`）；`git ls-remote origin refs/heads/main` 同为 `613cc4b`。
- 未验证：发布后未重复执行 Creo 实机与 WorkBuddy 黑盒，实机范围以发布前记录为准。

## v0.32.0（2026-11-20，发布前快照）

- 版本与范围：`0.32.0` MINOR 部分交付，公开工具仍 109；交付 [DEV-094](../work-items/DEV-094.md) 的 0.27.0 反馈批（反馈原件逐字节归档、回转轴-草图平面关系）、[FEAT-068](../work-items/FEAT-068.md)、[FEAT-023](../work-items/FEAT-023.md)、[BUG-076](../work-items/BUG-076.md)、[BUG-019](../work-items/BUG-019.md)、[FEAT-008](../work-items/FEAT-008.md)、[FEAT-051](../work-items/FEAT-051.md) 与 [FEAT-039](../work-items/FEAT-039.md) 的子项；发布记录见 [RELEASE-0.32.0](../validation/RELEASE-0.32.0.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py` → 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `9d41be87b9501d402faa0e3de5b7dfc92def2a31c57e47fe301b2cf94983c922`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.32.0`）。
- 源码包由发布提交源码构建，字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.32.0`；四附件为 `MCP_CREO_MechDog-0.32.0-source.zip`、`MCP_CREO_MechDog-0.32.0-source.zip.sha256`、`MCP_CREO_MechDog-0.32.0-seed-library.zip` 与 `MCP_CREO_MechDog-0.32.0-seed-library.zip.sha256`。
- 发布后核对（2026-11-20 16:11 +08:00 / 08:11Z）：`tools\check_release_assets.py --tag v0.32.0` → exit 0，「v0.32.0: four assets downloaded and verified; both sidecars match」。远端 API digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.32.0-source.zip` | 11 271 060 | `2996d340c60e118b86fdb9db31b68780907f2d938ff7269609ca16c00af78025` |
| `MCP_CREO_MechDog-0.32.0-source.zip.sha256` | 101 | `87da005f6e15209a2a99822e822ed153c11134f53432d37a026950c7c5747599` |
| `MCP_CREO_MechDog-0.32.0-seed-library.zip` | 493 442 | `9d41be87b9501d402faa0e3de5b7dfc92def2a31c57e47fe301b2cf94983c922` |
| `MCP_CREO_MechDog-0.32.0-seed-library.zip.sha256` | 107 | `15cf53cc4fa0912f0b3b0f5deacb2ec63d9e6dc723e25e30135350a649ae4ede` |

- Release 元数据：id `RE_kwDOU_ueTM4a92Te`，非 draft、非 prerelease，`created_at=2026-11-20T08:11:19Z`，`published_at=2026-11-20T08:11:47Z`，tag `v0.32.0`，target `main`（提交 `539a6b0145d84a9c15e538df6601d9538ecfd035`）。
- 包内快照与 `main` 的差异：已冻结源码包内的 POSTCHECK/发布记录仍是打包时点措辞（`remote_verification=pending`），本段实际结果与 `docs/releases/0.32.0.json` 的 `verified` 只存在于 `main`，不改写、不重发已发布附件。

## v0.31.1（2026-11-19，发布前快照）

- 版本与范围：`0.31.1` PATCH 工程规则，公开工具仍 109；交付 [DEV-093](../work-items/DEV-093.md)——本机实机操作改为 2026-11-19 常设授权（可直接启动/重启 Creo 与 nmsd、结束卡死或异常进程、确认后清理残留 `toolkit.lock` 与保护状态、编译执行器、建模、GUI 操作与实机验收，不再逐次确认），数据与已发布产物仍不可改写，单通道与 revision/保存重载边界不变。发布记录见 [RELEASE-0.31.1](../validation/RELEASE-0.31.1.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py` → 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `ca5a61b5fb45cae7b73c19d1cff9017a2158728ad3fa94171005ea94a15b5b48`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.31.1`）。
- 源码包由发布提交源码构建，字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.31.1`；四附件为 `MCP_CREO_MechDog-0.31.1-source.zip`、`MCP_CREO_MechDog-0.31.1-source.zip.sha256`、`MCP_CREO_MechDog-0.31.1-seed-library.zip` 与 `MCP_CREO_MechDog-0.31.1-seed-library.zip.sha256`。
- 发布后核对（2026-11-19 21:11 +08:00 / 13:11Z）：`gh release download` 取四附件后 `tools\check_release_assets.py --tag v0.31.1 --version 0.31.1 --dir` → exit 0，「four assets present; both sidecars match」。远端 API digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.31.1-source.zip` | 11 114 799 | `6eea649b3b1564d7fe47576f0b162747c6ca28cbc890607f2077aec6ed7fd18d` |
| `MCP_CREO_MechDog-0.31.1-source.zip.sha256` | 101 | `afd0bf98e1fc60c06421d596b4585643c1947a4bf565e721d99c032e55b8a497` |
| `MCP_CREO_MechDog-0.31.1-seed-library.zip` | 493 442 | `ca5a61b5fb45cae7b73c19d1cff9017a2158728ad3fa94171005ea94a15b5b48` |
| `MCP_CREO_MechDog-0.31.1-seed-library.zip.sha256` | 107 | `96aa3c34829fefbc9726d0c78b615829c9dbeaedb315a057968c66743bac4c08` |

- Release 元数据：id `451362319`，非 draft、非 prerelease，`created_at=2026-11-19T13:09:50Z`，`published_at=2026-11-19T13:10:16Z`，target `main`（提交 `665e5860ea5314197b77410769460db4338935c9`，标签对象 `34bb016ebf9182d69cde4bccc2b2b88e4b3a51a0`）。
- 包内快照与 `main` 的差异：已冻结源码包内的 POSTCHECK/发布记录仍是打包时点措辞（`remote_verification=pending`），本段实际结果与 `docs/releases/0.31.1.json` 的 `verified` 只存在于 `main`，不改写、不重发已发布附件。

## v0.31.0（2026-11-19，发布前快照）

- 版本与范围：`0.31.0` MINOR 部分交付，公开工具仍 109；交付 [BUG-120](../work-items/BUG-120.md) 的导线预检（裸标签在建作业前拒绝、开面板前 21 对截面×导线诊断）与建面回执（唯一新增面组关联、保存重载后面积/开闭/边界，`geometry_check.verified` 由证据决定）；任务 5 接缝 G1（6.28°）单独排期；发布记录见 [RELEASE-0.31.0](../validation/RELEASE-0.31.0.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py` → 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `fef385db303722c3279b9fc6525dc8fd06717b6d67f99d6128c587d04a2e8356`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.31.0`）。
- 源码包由发布提交源码构建，字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.31.0`；四附件为 `MCP_CREO_MechDog-0.31.0-source.zip`、`MCP_CREO_MechDog-0.31.0-source.zip.sha256`、`MCP_CREO_MechDog-0.31.0-seed-library.zip` 与 `MCP_CREO_MechDog-0.31.0-seed-library.zip.sha256`。
- 发布后核对（2026-11-19 20:17 +08:00 / 12:17Z）：`tools\check_release_assets.py --tag v0.31.0` 的 gh 自动下载通道在本机代理下 30 秒内未完成，按 [RELEASING](RELEASING.md) 改用 `gh release download` 取四附件，再以 `--dir` 复核 → exit 0，「local_verified: four assets present; both sidecars match (version 0.31.0)」。远端 API digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.31.0-source.zip` | 11 106 825 | `e9d2c2db0be6a1500953e474cad9720146a579b079d7acad49e4a60312c1d31b` |
| `MCP_CREO_MechDog-0.31.0-source.zip.sha256` | 101 | `56e4d7b47d5116f4f6447f5432a21e8dd9dad4fe5e808bb4e75a98aca913ee24` |
| `MCP_CREO_MechDog-0.31.0-seed-library.zip` | 493 442 | `fef385db303722c3279b9fc6525dc8fd06717b6d67f99d6128c587d04a2e8356` |
| `MCP_CREO_MechDog-0.31.0-seed-library.zip.sha256` | 107 | `c9a9f4c7340651ab7ce31d536488ce465fe343040927e6e4215e778b1906c960` |

- Release 元数据：id `451300984`，非 draft、非 prerelease，`created_at=2026-11-19T11:50:11Z`，`published_at=2026-11-19T12:15:20Z`，target `main`（提交 `daadbe71869ae4b394a9298970a8d9ec6608bc91`，标签对象 `d2f8a96c80fc9f91569dc219df409a4ddba49dcb`）。
- 包内快照与 `main` 的差异：已冻结源码包内的 POSTCHECK/发布记录仍是打包时点措辞（`remote_verification=pending`），本段实际结果与 `docs/releases/0.31.0.json` 的 `verified` 只存在于 `main`，不改写、不重发已发布附件。

## v0.30.0（2026-11-19，发布前快照）

- 版本与范围：`0.30.0` MINOR 部分交付，公开工具仍 109；交付 [BUG-133](../work-items/BUG-133.md) 显式容差两层统一、[FEAT-012](../work-items/FEAT-012.md) 列向量约定与 [DEV-092](../work-items/DEV-092.md) 约束组边界与失败诊断；发布记录见 [RELEASE-0.30.0](../validation/RELEASE-0.30.0.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py` → 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `e210ee229590a474c5fc22c5d81a0d39448f09055b55011671e6eac7177c2c13`（24 个文件、9 个种子、493 442 字节，两次构建逐字节一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.30.0`）。
- 源码包由发布提交源码构建，字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.30.0`；四附件为 `MCP_CREO_MechDog-0.30.0-source.zip`、`MCP_CREO_MechDog-0.30.0-source.zip.sha256`、`MCP_CREO_MechDog-0.30.0-seed-library.zip` 与 `MCP_CREO_MechDog-0.30.0-seed-library.zip.sha256`。
- 发布后核对（2026-11-19 13:20 +08:00 / 05:20Z）：`tools\check_release_assets.py --tag v0.30.0` → exit 0，「v0.30.0: four assets downloaded and verified; both sidecars match」。远端 digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.30.0-source.zip` | 11 110 422 | `a52fa49d5d1c089485fddd7997487ac4cb292a84ad8ecc5df907fbf86cf46e67` |
| `MCP_CREO_MechDog-0.30.0-source.zip.sha256` | 101 | `56d1972efd127ffdac42397c5a469665c80ecafb9ff33dbe1db6c7791b063879` |
| `MCP_CREO_MechDog-0.30.0-seed-library.zip` | 493 442 | `e210ee229590a474c5fc22c5d81a0d39448f09055b55011671e6eac7177c2c13` |
| `MCP_CREO_MechDog-0.30.0-seed-library.zip.sha256` | 107 | `f360f963bcf36341658cd6a6a8b264ba738e1f911c13faca750f6825e03b8e87` |

- Release 元数据：id `450909202`，非 draft、非 prerelease，`created_at=2026-11-19T05:15:42Z`，`published_at=2026-11-19T05:16:30Z`，target `main`（提交 `1c20f550571f15820dba6816f4efbab060197a4d`，标签对象 `0b9aae1deadf7491610272f0a48471ec7d7c0b31`）。
- 包内快照与 `main` 的差异：已冻结源码包内的 POSTCHECK/发布记录仍是打包时点措辞（`remote_verification=pending`），本段实际结果与 `docs/releases/0.30.0.json` 的 `verified` 只存在于 `main`，不改写、不重发已发布附件。

## v0.29.0（2026-11-19，发布前快照）

- 版本与范围：`0.29.0` MINOR 部分交付，公开工具仍 109；交付 [BUG-120](../work-items/BUG-120.md) 的 candidate-3 公开认证（第二方向导线、末端单点、最多 11 位置）与准入前置拒绝；发布记录见 [RELEASE-0.29.0](../validation/RELEASE-0.29.0.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py` → 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `cd3a5d5ec11928670f9e35aa6cdc2deb06314ce94ab9b7d8df5825af34ae8db3`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.29.0`）。
- 源码包由发布提交源码构建，字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.29.0`；四附件为 `MCP_CREO_MechDog-0.29.0-source.zip`、`MCP_CREO_MechDog-0.29.0-source.zip.sha256`、`MCP_CREO_MechDog-0.29.0-seed-library.zip` 与 `MCP_CREO_MechDog-0.29.0-seed-library.zip.sha256`。
- 发布后核对（2026-11-19 12:02 +08:00 / 04:02Z）：`tools\check_release_assets.py --tag v0.29.0` → exit 0，「v0.29.0: four assets downloaded and verified; both sidecars match」。远端 digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.29.0-source.zip` | 11 016 525 | `c108d78bfe8424ed6f1cb23421e5074c58908bee2bb792771da2ccebf1f74772` |
| `MCP_CREO_MechDog-0.29.0-source.zip.sha256` | 101 | `9d00ea946b7478128203c2b454b96e6fc9a9e4f6c5f2dc534d0f3f8074c10fd0` |
| `MCP_CREO_MechDog-0.29.0-seed-library.zip` | 493 442 | `cd3a5d5ec11928670f9e35aa6cdc2deb06314ce94ab9b7d8df5825af34ae8db3` |
| `MCP_CREO_MechDog-0.29.0-seed-library.zip.sha256` | 107 | `77bdfbb90e7fd81b98d5d1802a5920dc7da3a33385a265b5ac2903013c935e3f` |

- Release 元数据：id `450862824`，非 draft、非 prerelease，`created_at=2026-11-19T04:00:53Z`，`published_at=2026-11-19T04:01:24Z`，target `main`（提交 `79f88154598f1576bd5f46aec3cc661ecb1f5fe3`，标签对象 `ae0452b814d7c15477d290bd507399460c36333c`）。
- 包内快照与 `main` 的差异：已冻结源码包内的 POSTCHECK/发布记录仍是打包时点措辞（`remote_verification=pending`），本段实际结果与 `docs/releases/0.29.0.json` 的 `verified` 只存在于 `main`，不改写、不重发已发布附件。

## v0.28.0（2026-11-19，发布前快照）

- 版本与范围：`0.28.0` MINOR 部分交付，公开工具仍 109；交付 [BUG-120](../work-items/BUG-120.md) 的 Creo 10 resident_panel 认证路线、candidate-3 导线/点、两段式球鼻艏演示体与 WorkBuddy 两轮黑盒；发布记录见 [RELEASE-0.28.0](../validation/RELEASE-0.28.0.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py` → 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `dfac1ec5b62a0a926d0debf1efaf77ab13cf627ee0c6318ff6993be5201aacf9`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.28.0`）。
- 源码包由发布提交源码构建，字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.28.0`；四附件为 `MCP_CREO_MechDog-0.28.0-source.zip`、`MCP_CREO_MechDog-0.28.0-source.zip.sha256`、`MCP_CREO_MechDog-0.28.0-seed-library.zip` 与 `MCP_CREO_MechDog-0.28.0-seed-library.zip.sha256`。
- 发布后核对（2026-11-19 11:22 +08:00 / 03:22Z）：`tools\check_release_assets.py --tag v0.28.0` → exit 0，「v0.28.0: four assets downloaded and verified; both sidecars match」。远端 digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.28.0-source.zip` | 11 001 175 | `3d425b80e6d15a5cae9dc7680b6b0df138b570de5f7146053ca9f88f1275910e` |
| `MCP_CREO_MechDog-0.28.0-source.zip.sha256` | 101 | `27149c0f36f3fdb6bd28217514c1b1584e2e37023fdc6aa475b2dfeb2b7019ac` |
| `MCP_CREO_MechDog-0.28.0-seed-library.zip` | 493 442 | `dfac1ec5b62a0a926d0debf1efaf77ab13cf627ee0c6318ff6993be5201aacf9` |
| `MCP_CREO_MechDog-0.28.0-seed-library.zip.sha256` | 107 | `0a695ab71a76dd0450012f458c39ffa9248c1f7b6475ec664acfcead73ccf6a3` |

- Release 元数据：id `450838061`，非 draft、非 prerelease，`created_at=2026-11-19T03:18:57Z`，`published_at=2026-11-19T03:21:43Z`，target `main`（提交 `e1ea2da3a6c62602855ce5d7fde3f5407e1dcfe4`，标签对象 `8808bfed449218609311229412e33599b1a4efc9`）。
- 包内快照与 `main` 的差异：已冻结源码包内的 POSTCHECK/发布记录仍是打包时点措辞（`remote_verification=pending`），本段实际结果与 `docs/releases/0.28.0.json` 的 `verified` 只存在于 `main`，不改写、不重发已发布附件。

## 方法与范围

- 工具：`tools/check_release_assets.py --tag <tag> --version <version>`（gh 取 API 元数据 → 精确 tag 附件 → 下载四文件 → 重算 SHA256 → 比对 sidecar 内容）。
- 时间：2026-11-07T16:58:23Z 起（本机 +08:00），逐版连续执行，exit code 均为 0。
- 环境：Windows x64；Python 3.12 虚拟环境（`.venv`）；`gh` 已登录；源码目录 `C:\i0182`（`origin/main` 的独立工作树，0.18.2 开发分支），核对对象是已发布远端 Release，不受工作区改动影响。
- 命令输出原文见本轮 `build/postcheck/postcheck.log`；下表 digest 由 GitHub Release API 的 `assets[].digest` 读出，与本地重算结果一致。

## v0.27.0（2026-11-17）

- 版本与范围：`0.27.0` MINOR 部分交付，公开工具 108→109；交付 [BUG-130](../work-items/BUG-130.md)、[BUG-131](../work-items/BUG-131.md)、[BUG-132](../work-items/BUG-132.md)、[FEAT-069](../work-items/FEAT-069.md)、[BUG-122](../work-items/BUG-122.md)、[DEV-090](../work-items/DEV-090.md)、[BUG-129](../work-items/BUG-129.md) 与 [BUG-106](../work-items/BUG-106.md) 的已完成子项；BUG-020 已归档，发布记录见 [RELEASE-0.27.0](../validation/RELEASE-0.27.0.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py` → 标签/发布 → `tools\check_release_assets.py` 远端复核。
- 种子包 SHA256 `72cdd8053298981b7fc9ac6665bb66033b9f91daacd4194d3360d2bc0389b36f`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.27.0`）。
- 源码包由发布提交源码构建，字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.27.0`；四附件为 `MCP_CREO_MechDog-0.27.0-source.zip`、`MCP_CREO_MechDog-0.27.0-source.zip.sha256`、`MCP_CREO_MechDog-0.27.0-seed-library.zip` 与 `MCP_CREO_MechDog-0.27.0-seed-library.zip.sha256`。
- 发布后核对（2026-11-17 21:58 +08:00 / 13:58Z）：`tools\check_release_assets.py --tag v0.27.0` → exit 0，「v0.27.0: four assets downloaded and verified; both sidecars match」。远端 digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.27.0-source.zip` | 10 794 751 | `de1119b8e6d0b1515cc0a9123158f2071944af1ff830f2b2fc999b30dd356887` |
| `MCP_CREO_MechDog-0.27.0-source.zip.sha256` | 101 | `240c18b1712f5b3b20c13a2f747c64b586c82ae1465a58df65e62cda8fbb63d9` |
| `MCP_CREO_MechDog-0.27.0-seed-library.zip` | 493 442 | `72cdd8053298981b7fc9ac6665bb66033b9f91daacd4194d3360d2bc0389b36f` |
| `MCP_CREO_MechDog-0.27.0-seed-library.zip.sha256` | 107 | `1dd0180abac63d3aeb84063b3b5d21f792ed5ec0ef39a67113c2398880b8ef1a` |

- Release 元数据：id `448705701`，非 draft、非 prerelease，`created_at=2026-11-17T13:57:39Z`，`published_at=2026-11-17T13:58:26Z`，target `main`（提交 `fc1efaefa68cda1c0b4d46849f18933c35050b64`，标签对象 `7d0ab3432b1c51256ab4f133c5f259e5d7c33330`）。
- 包内快照与 `main` 的差异：已冻结源码包内的 POSTCHECK/发布记录仍是打包时点措辞（`remote_verification=pending`），本段实际结果与 `docs/releases/0.27.0.json` 的 `verified` 只存在于 `main`，不改写、不重发已发布附件。
- 本版修改 `native/generic.cpp`、`native/stl_export.h`、`native/geometry_selectors.cpp`、`native/advanced.cpp`，升级后必须重编译 worker。

## v0.26.0（2026-11-16）

- 版本与范围：`0.26.0` MINOR 部分交付，公开工具仍 108；交付 [DEV-083](../work-items/DEV-083.md)、[DEV-090](../work-items/DEV-090.md)、[DEV-091](../work-items/DEV-091.md)、[BUG-129](../work-items/BUG-129.md)、[FEAT-068](../work-items/FEAT-068.md) 与 [FEAT-069](../work-items/FEAT-069.md) 的已完成子项，发布记录见 [RELEASE-0.26.0](../validation/RELEASE-0.26.0.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py`（内置四附件与发布记录门禁）→ 标签/发布 → `tools\check_release_assets.py --tag v0.26.0`。
- 种子包 SHA256 `b16328fa2f114dcd3f5f520645e63a68752c9a3e1dd049f5a7f778fedd899d5c`（24 个文件、9 个种子，两次构建摘要一致；包内 `seed_manifest.json` 声明 `compatible_server_version=0.26.0`）。
- 源码包 `MCP_CREO_MechDog-0.26.0-source.zip` 由发布提交源码构建，`package.py` 的四附件门禁与发布记录门禁均通过；字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.26.0`；四附件为 `MCP_CREO_MechDog-0.26.0-source.zip`、`MCP_CREO_MechDog-0.26.0-source.zip.sha256`、`MCP_CREO_MechDog-0.26.0-seed-library.zip` 与 `MCP_CREO_MechDog-0.26.0-seed-library.zip.sha256`；`source.zip` 的摘要见同名 sidecar，不写入包内。
- 发布后核对（2026-11-16 14:15 +08:00 / 06:15Z）：`tools\check_release_assets.py --tag v0.26.0` → exit 0，「v0.26.0: four assets downloaded and verified; both sidecars match」。远端 digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.26.0-source.zip` | 10 343 533 | `578bb8ed7e6cc3db53ea9e82d001f55cc96be6741ce4c30c0641fcc1b470d8a6` |
| `MCP_CREO_MechDog-0.26.0-source.zip.sha256` | 101 | `dd177e4732f65a841602c86f3dd1d5eb2e4f2708c66080d2dd0e595fcdd6893a` |
| `MCP_CREO_MechDog-0.26.0-seed-library.zip` | 493 444 | `b16328fa2f114dcd3f5f520645e63a68752c9a3e1dd049f5a7f778fedd899d5c` |
| `MCP_CREO_MechDog-0.26.0-seed-library.zip.sha256` | 107 | `47000b83231263d085ab76924cf47a85f138853cbd7458b4d92daf6d2e19fdcc` |

- Release 元数据：id `446671020`，非 draft、非 prerelease，`created_at=2026-11-16T06:14:59Z`，`published_at=2026-11-16T06:15:23Z`，target `main`（提交 `13609bc5a2889d02ab04e0b62364ca99c29dca02`，标签对象 `6d2e16ec73ed2ad8c362c63cdaf9195df8c87a4e`）。
- 包内快照与 `main` 的差异：已冻结源码包内的 POSTCHECK/发布记录仍是打包时点措辞（`remote_verification=pending`），本段实际结果与 `docs/releases/0.26.0.json` 的 `verified` 只存在于 `main`，不改写、不重发已发布附件。
- 本版修改 `native/base_flange.cpp`、`native/geometry_selectors.cpp`、`native/advanced.cpp`、`native/generic.cpp`，升级后必须重编译 worker。

## v0.24.1（2026-11-13）

- 版本与范围：`0.24.1` PATCH，公开工具仍 107；交付 [BUG-125](../work-items/BUG-125.md)、[BUG-126](../work-items/BUG-126.md)、[BUG-127](../work-items/BUG-127.md)、[BUG-128](../work-items/BUG-128.md) 与 [DEV-089](../work-items/DEV-089.md)，五项无保留范围、按台账规则归档至[完成档案](../BACKLOG_COMPLETED.md)；发布记录见 [RELEASE-0.24.1](../validation/RELEASE-0.24.1.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py`（内置四附件与发布记录门禁）→ 打标签并发布 → `tools\check_release_assets.py --tag v0.24.1`。
- 种子包 SHA256 `ee15813b935e14f7f84c49ea80160c28b45b18947f8b87bcdd5a297a40ce365d`（24 个文件、9 个种子、493 442 字节；回填后本地重算摘要一致，包内 `seed_manifest.json` 声明 `compatible_server_version=0.24.1`）。
- 源码包 `MCP_CREO_MechDog-0.24.1-source.zip` 由发布提交源码构建，`package.py` 的四附件门禁与发布记录门禁均通过；字节数与 SHA256 见同名 sidecar 与 Release 正文，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.24.1`；四附件为 `MCP_CREO_MechDog-0.24.1-source.zip`、`MCP_CREO_MechDog-0.24.1-source.zip.sha256`、`MCP_CREO_MechDog-0.24.1-seed-library.zip` 与 `MCP_CREO_MechDog-0.24.1-seed-library.zip.sha256`；`source.zip` 的摘要见同名 sidecar，不写入包内。
- Release 元数据：id `444282824`，非 draft、非 prerelease，`created_at=2026-11-13T13:46:35Z`，`published_at=2026-11-13T13:47:10Z`，target `main`（提交 `39c54ccf7689ac16e489082cd035082950f16de0`，标签对象 `f1f08ee3cb562279e45c4e57ac33a9d679497a8c`）。
- 核对命令：`tools\check_release_assets.py --tag v0.24.1` → exit 0，「four assets downloaded and verified; both sidecars match」。远端 digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.24.1-source.zip` | 10 125 185 | `b74672b5915f8733fd1e950e76aebbe25fe37bd988a72d23796a5584d3b2712b` |
| `MCP_CREO_MechDog-0.24.1-source.zip.sha256` | 101 | `b2d8b116d7288dcb429018491d197de4d692c39410536ebb05ea2ff6b59b7dfa` |
| `MCP_CREO_MechDog-0.24.1-seed-library.zip` | 493 442 | `ee15813b935e14f7f84c49ea80160c28b45b18947f8b87bcdd5a297a40ce365d` |
| `MCP_CREO_MechDog-0.24.1-seed-library.zip.sha256` | 107 | `98d9a250872b84c6a7dbb04f049177d4fda39b536b5902c131fcc063a0e45ced` |

- 本版含 `native/worker.cpp` 变更，升级后必须重编 worker；手工改 `creo_startup_args` 或 `creo_worker_launch` 后必须重启 MCP 服务。本段只做附件与标签核对，不重新验证包内功能；功能验收与未测范围以 [RELEASE-0.24.1](../validation/RELEASE-0.24.1.md) 与 Release 正文为准。

## v0.17.4

- 标签对象：`v0.17.4` → 提交 `b57dbdac7747c670433b964a5294f8373b6c757b`；发布 2026-11-07T05:24:16Z；非 Pre-release。
- 核对结果：**四附件齐全，两个 sidecar 与对应 ZIP 摘要一致**（exit 0）。

| 附件 | SHA256（远端 digest 与本地重算一致） | 字节 |
| --- | --- | ---: |
| `MCP_CREO_MechDog-0.17.4-source.zip` | `8f8f649c2d7c8420145d23a79f1f0749a525bae4f5f348a97401b71fea4fbc09` | 8 382 351 |
| `MCP_CREO_MechDog-0.17.4-source.zip.sha256` | `34e00b85164135df86fdab798dfa39b413e33a45581618c829f75ca2d9652bd8` | 101 |
| `MCP_CREO_MechDog-0.17.4-seed-library.zip` | `a6c633b49cb243ca1f58e6f3b8756f30a9e0b32eefebcc0e185bec1bd79a3583` | 493 442 |
| `MCP_CREO_MechDog-0.17.4-seed-library.zip.sha256` | `f53acf87a22b9641d9ae2d8b732993451b3ecc05d0ef760150b0c3b23e3e64b2` | 107 |

## v0.18.0

- 标签对象：`v0.18.0` → 提交 `58dd76b2d47e180e7e54d701cfaa4449aae49654`；发布 2026-11-07T07:04:07Z；非 Pre-release。
- 核对结果：**四附件齐全，两个 sidecar 与对应 ZIP 摘要一致**（exit 0）。

| 附件 | SHA256（远端 digest 与本地重算一致） | 字节 |
| --- | --- | ---: |
| `MCP_CREO_MechDog-0.18.0-source.zip` | `dab4ca04ee58ae643e4e492ef3870d04d8724921c57be8e554c96136ee874849` | 8 485 592 |
| `MCP_CREO_MechDog-0.18.0-source.zip.sha256` | `3c4bd463dadc967eba2d3fd52f66b8c2998bb4d0186834ff811fef731fed9dfa` | 101 |
| `MCP_CREO_MechDog-0.18.0-seed-library.zip` | `b6acab41fd727bb555ec6bb825116df2eab1e81e214db1c7c804e4f5e709a05b` | 493 442 |
| `MCP_CREO_MechDog-0.18.0-seed-library.zip.sha256` | `02c3823da9f59a745b3a3685c82d7342abf24d95b4260ffa06d046aa6069b51b` | 107 |

## v0.18.1

- 标签对象：`v0.18.1` → 提交 `9d725691c556c8063316a2cdf4d506c818a7baf7`；发布 2026-11-07T08:53:07Z；非 Pre-release。
- 核对结果：**四附件齐全，两个 sidecar 与对应 ZIP 摘要一致**（exit 0）。

| 附件 | SHA256（远端 digest 与本地重算一致） | 字节 |
| --- | --- | ---: |
| `MCP_CREO_MechDog-0.18.1-source.zip` | `658950c837895f96e4ec254610d18b8fe5012ae585d5a567cc5c2409940d08a7` | 8 444 988 |
| `MCP_CREO_MechDog-0.18.1-source.zip.sha256` | `ea9b403e87d9139fe299b7f5f61770dbac6ecb5eb46093508496bdddb3daf901` | 101 |
| `MCP_CREO_MechDog-0.18.1-seed-library.zip` | `8e5f512571de9ff494db3a0964f7ff00d0c49a4c5f9767f93e08f385436a640e` | 493 442 |
| `MCP_CREO_MechDog-0.18.1-seed-library.zip.sha256` | `c2b3df7825c85203990722b51ab5e80fae589f444845f292b503e8c62bc1f937` | 107 |

## v0.18.2（2026-11-08 DEV-077 补齐四附件数据）

- 发布链接：[v0.18.2](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.18.2)。标签对象 `v0.18.2` → annotated tag `4c659f5e1fe24e0ff76a1142f15ea80c3bc48e08` → 提交 `43862f00237d1aac34bce5cc1e576e2424c3ba39`；发布时间 `2026-11-07T10:18:16Z`；非 Pre-release。
- 核对结果：`tools/check_release_assets.py --tag v0.18.2 --version 0.18.2` exit 0，「v0.18.2: four assets downloaded and verified; both sidecars match」。
- 历史独立核对：[2026-11-07 POSTCHECK 第1节C5与第3节](../validation/feedback-0.17.4-2026-11-07/POSTCHECK-RELEASE.md)：C5 同一命令 exit 0，四附件已下载、两个 sidecar 与 ZIP 一致；C9 另核本地 SHA256 与 API digest 一致。历史窗口 2026-11-07 18:50–19:00 +08:00。
- 数据来源：本批归档的 [0.18.2 离线升级复核原件](../validation/feedback-0.18.2-2026-11-08/originals/2026-11-07CREO10.0.0.0-0.18.2-本版交付卡DEV075仍开发中与台账计数166实为165及POSTCHECK本版段未回填.md) §二.2 与 §七；报告方取值时间 `2026-11-07 18:22 +08:00`，取值方式为 `download_report.json` 的 `api_digest`（GitHub API `assets[].digest`）与本机 `local_sha256` 逐项比对一致。两个 sidecar 均为 ASCII + LF。**DEV-077 只按原件转录补齐本节，本轮未联网重跑、未重新下载重算；精确 tag 的当轮核对仍见 G12。**

| 附件 | SHA256（报告方远端 digest 与本地重算一致） | 字节 |
| --- | --- | ---: |
| `MCP_CREO_MechDog-0.18.2-source.zip` | `4e33ebc713be62485d932267766eb8a1092b2b01f918876848925ef1c55d673b` | 8 458 979 |
| `MCP_CREO_MechDog-0.18.2-source.zip.sha256` | `727cf550231b5fe5bc0e230b409de289adedf2a99478801e68d700c66d65e7af` | 101 |
| `MCP_CREO_MechDog-0.18.2-seed-library.zip` | `676536ca85601d0ce7e954a000fad0af8a73b7579f02ab27f1a8f2bbac606a1a` | 493 442 |
| `MCP_CREO_MechDog-0.18.2-seed-library.zip.sha256` | `6d76cbee146f68ad2200343c382d07177532688b17f3aa83298f21b120d98c7d` | 107 |

四件名称逐个列出，未用通配；两份 sidecar 内容分别是对应 ZIP 的摘要。`docs/validation/RELEASE-0.18.2.md` 是发布前历史原件，按既有策略保持字节不变，其「发布后记录 / 结果补记」两行由本节与统一入口收口，不回写旧文件。

## v0.18.3 / v0.18.4（2026-11-08离线整合，非本轮远端实测）

依据：[原件manifest](../validation/feedback-0.18.4-2026-11-08/manifest.json)、其`release_meta.json`及反馈报告；[勘误与范围](RELEASE-ERRATA-2026-11-08.md)。本轮仅从本地Git对象确认标签提交。平台时间、发布状态、四方摘要结论来自所给资料，未重新访问GitHub，当前main/远端最新版本未确认。

| 版本 | 本地标签指向提交 | 资料所报发布时间UTC | Release链接 |
| --- | --- | --- | --- |
| 0.18.3 | `5cf7c11750711ffc16675e7f82cbaa0fd79465ad` | 2026-11-07T15:45:17Z | [v0.18.3](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.18.3) |
| 0.18.4 | `04927a99a9b8e2ac2a572b11ac9be66ea3f9f391` | 2026-11-07T17:41:40Z | [v0.18.4](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.18.4) |

0.18.4所给元数据：非draft、非prerelease、4附件；声称本地SHA256/sidecar/Release body/API digest四方一致。**以下只是外部记录转录，不是本轮下载重算结果**：

| 附件 | 资料SHA256 | 资料字节数 |
| --- | --- | ---: |
| `MCP_CREO_MechDog-0.18.4-source.zip` | `81ff64939c9b14ae94635bb49928664526d8fd4b64bda25836381320eb0f8f4f` | 8752689 |
| `MCP_CREO_MechDog-0.18.4-source.zip.sha256` | `be337e203d0a0e9e2edfc9d7eeeaa0fa074df8be0eb1ed7f8fe1f3636704e0e5` | 101 |
| `MCP_CREO_MechDog-0.18.4-seed-library.zip` | `1a030983c448d1f76cf5b74d878abce653e5d389ff939468b5cd314b43eb8647` | 493442 |
| `MCP_CREO_MechDog-0.18.4-seed-library.zip.sha256` | `168f7f4a277ad8b92d6b039839ed73626bb2af5ef66d85bcacbceeff27623aca` | 107 |

两个sidecar的101/107字节来自所给报告第2节表格（JSON摘要未列大小）。

2026-11-08T07:41Z 前后补齐精确 tag 重下重算：`tools/check_release_assets.py --tag v0.18.2/v0.18.3/v0.18.4` 三条均 exit 0（「four assets downloaded and verified; both sidecars match」）。0.18.3 与 0.18.4 的 API `assets[].digest` 与本地重算一致：

| 版本 | 附件 | 字节 | SHA256 |
| --- | --- | ---: | --- |
| 0.18.3 | `MCP_CREO_MechDog-0.18.3-source.zip` | 8 650 655 | `042959b54dab8de15044b9991f7defc3abce476c0cee8228997f7f00979b45bb` |
| 0.18.3 | `MCP_CREO_MechDog-0.18.3-source.zip.sha256` | 101 | `de4e08b40a4127d483fb4f93d93d62d726c7a2d7f5d8644ebaee1af0678df657` |
| 0.18.3 | `MCP_CREO_MechDog-0.18.3-seed-library.zip` | 493 442 | `7325485f26201c0242a315e7aa0291714a3de81e852eccbba6e60f6288831102` |
| 0.18.3 | `MCP_CREO_MechDog-0.18.3-seed-library.zip.sha256` | 107 | `06b9ba48b97a240ce4d784e22ee69851f0305b8ac835642a8b77867de165ba6b` |
| 0.18.4 | `MCP_CREO_MechDog-0.18.4-source.zip` | 8 752 689 | `81ff64939c9b14ae94635bb49928664526d8fd4b64bda25836381320eb0f8f4f` |
| 0.18.4 | `MCP_CREO_MechDog-0.18.4-source.zip.sha256` | 101 | `be337e203d0a0e9e2edfc9d7eeeaa0fa074df8be0eb1ed7f8fe1f3636704e0e5` |
| 0.18.4 | `MCP_CREO_MechDog-0.18.4-seed-library.zip` | 493 442 | `1a030983c448d1f76cf5b74d878abce653e5d389ff939468b5cd314b43eb8647` |
| 0.18.4 | `MCP_CREO_MechDog-0.18.4-seed-library.zip.sha256` | 107 | `168f7f4a277ad8b92d6b039839ed73626bb2af5ef66d85bcacbceeff27623aca` |

0.18.3 / 0.18.4 均为非 draft、非 prerelease，`published_at` 分别为 `2026-11-07T15:45:17Z`、`2026-11-07T17:41:40Z`。0.18.2 的四附件数据仍以本节上方报告方转录为准，本轮 `--tag` 命令同样 exit 0，但未逐项重列摘要。

0.18.3/0.18.4 的精确 tag 重下重算已于 2026-11-08T07:41Z 补记；Release body 原文未逐字比对，当前 main 的包含关系见 v0.19.0 段。

## v0.19.0（2026-11-08 本轮联网实测）

- 核对时间：`2026-11-08T07:41:05Z` / `2026-11-08 15:41:05 +08:00`。
- 标签对象：`v0.19.0` → annotated tag `3f17e887de89e8c7f655908371ef04e86ed1258d` → 提交 `86020e71397137600f748b3433de2f9a75383b22`；tagger 时间 `2026-11-08T06:40:44Z`。
- Release：[v0.19.0](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.19.0)，id `438079516`，非 draft、非 prerelease；`created_at=2026-11-08T06:40:44Z`，`published_at=2026-11-08T06:40:55Z`，`target_commitish=main`。
- 核对命令：`tools/check_release_assets.py --tag v0.19.0 --version 0.19.0` → exit 0，「v0.19.0: four assets downloaded and verified; both sidecars match」。
- 四附件逐个列出（未用通配）；API `assets[].digest`、下载后本地实算 SHA256 与 sidecar 内容三者一致：

| 附件 | 字节 | SHA256 | API 创建时间 |
| --- | ---: | --- | --- |
| `MCP_CREO_MechDog-0.19.0-source.zip` | 8 908 094 | `9caa479041c2303e5e923faf48d0e5406de516e39050d71495ea3ec8c00a9878` | 2026-11-08T06:40:50Z |
| `MCP_CREO_MechDog-0.19.0-source.zip.sha256` | 101 | `0eb2615c836a8b96655e12c3fc6f5d443e2e9b5d8e209040d79be9cb3c9a2d9e` | 2026-11-08T06:40:50Z |
| `MCP_CREO_MechDog-0.19.0-seed-library.zip` | 493 442 | `05859ac1ae89d0c0455f6b4aa8a02a34b232588c4d1b4da74d6842f21041a072` | 2026-11-08T06:40:50Z |
| `MCP_CREO_MechDog-0.19.0-seed-library.zip.sha256` | 107 | `9cce3894e4ebd5ae2f3cfe650334becf83e0f398a62bb5234e179c0ffc7d506b` | 2026-11-08T06:40:50Z |

- 本记录只证明远端附件、两个 sidecar 与对应 ZIP 摘要一致；不重新验证包内功能、Creo 实机或安装结果，也不回写 `RELEASE-0.19.0.md` 历史原件。v0.18.2/0.18.3/0.18.4 的精确 tag 已在各自段落按同一命令重下重算并记录（见上），本行旧的「仍待补」表述已删除（DEV-079，2026-11-08）。

## v0.19.1（2026-11-08 本轮联网实测）

- 核对时间：`2026-11-08T08:08:02Z` / `2026-11-08 16:08:02 +08:00`。
- 标签对象：`v0.19.1` → annotated tag `e34075d3a7ec453bec29807329b6c4686bc54c1f` → 提交 `9dcf5ee`。
- Release：[v0.19.1](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.19.1)，id `438114011`，非 draft、非 prerelease；`created_at=2026-11-08T08:07:26Z`，`published_at=2026-11-08T08:07:49Z`，`target_commitish=main`。
- 核对命令：`tools/check_release_assets.py --tag v0.19.1 --version 0.19.1` → exit 0，「v0.19.1: four assets downloaded and verified; both sidecars match」。
- 四附件逐个列出（未用通配）；API `assets[].digest`、下载后本地实算 SHA256 与 sidecar 内容三者一致：

| 附件 | 字节 | SHA256 | API 创建时间 |
| --- | ---: | --- | --- |
| `MCP_CREO_MechDog-0.19.1-source.zip` | 9 160 836 | `eb1644599cff11fb53450c3f02ee5625a71d9b194a6a6170bd515d55cb5b71ef` | 2026-11-08T08:07:46Z |
| `MCP_CREO_MechDog-0.19.1-source.zip.sha256` | 101 | `e6b776917e8492b044659b8c97fbebaa9a4a94c3548376a4e148fc1ba1ca3442` | 2026-11-08T08:07:46Z |
| `MCP_CREO_MechDog-0.19.1-seed-library.zip` | 493 442 | `a7d864271b2e188e1f2a51eeea2046d15cf8615b10fde9b87beb466e8350657f` | 2026-11-08T08:07:46Z |
| `MCP_CREO_MechDog-0.19.1-seed-library.zip.sha256` | 107 | `16206fd52e2aa91f755bfc321beb02fa2403fd8049132d26d34f333befb161e2` | 2026-11-08T08:07:46Z |

## v0.21.0（2026-11-11 本轮联网实测）

- 核对时间：`2026-11-11T05:15:33Z` 发布后立即核对（本机 +08:00）。
- 标签对象：`v0.21.0` → annotated tag `1932c03b7842f04603a979393ffb607db2beaa7a` → 提交 `990c88a`。
- Release：[v0.21.0](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.21.0)，id `441266770`，非 draft、非 prerelease；`created_at=2026-11-11T05:14:44Z`，`published_at=2026-11-11T05:15:33Z`，`target_commitish=main`。
- 核对命令：`tools/check_release_assets.py --tag v0.21.0` → exit 0，「v0.21.0: four assets downloaded and verified; both sidecars match」。
- 四附件逐个列出（未用通配）；API `assets[].digest`、下载后本地实算 SHA256 与 sidecar 内容三者一致：

| 附件 | 字节 | SHA256 | API 创建时间 |
| --- | ---: | --- | --- |
| `MCP_CREO_MechDog-0.21.0-source.zip` | 9 509 982 | `ff3ef09eb27409089375b61a61505c1a1fa359f16cd5507858325dcaac1be4ec` | 2026-11-11T05:15:30Z |
| `MCP_CREO_MechDog-0.21.0-source.zip.sha256` | 101 | `f7b66d0158c79272291a66adda430ab46bca8f74c4222bce791bb8d67b6bcaf0` | 2026-11-11T05:15:30Z |
| `MCP_CREO_MechDog-0.21.0-seed-library.zip` | 493 442 | `da2a2936afdc5c1afbc1c7ffd5c9d70390020ec41f3cdb2f086d2151259a0f46` | 2026-11-11T05:15:30Z |
| `MCP_CREO_MechDog-0.21.0-seed-library.zip.sha256` | 107 | `9309ac3dd750d0f720963ddb9ab31f5fcbdcc8a3945e7103ed613873f6014bfe` | 2026-11-11T05:15:30Z |

- 本记录只证明远端附件、两个 sidecar 与对应 ZIP 摘要一致；不重新验证包内功能、Creo 实机或安装结果。发布前本机四附件闸门（`tools/package.py`）同样通过，源码包解压单测的 MAX_PATH 例外见 [RELEASE-0.21.0](../validation/RELEASE-0.21.0.md)。
- **勘误（2026-11-11，FEAT-065 T4 补记，未改已发布原文）**：[0.21.0 版本说明](../RELEASE_NOTES_0.21.0.md)只列了 FEAT-065 M2（`guides`），漏列同版发布的 M1。对照标签源码可以确认：`src/creo_mechdog/surface_ops.py` 中 `SurfaceLoftOp.sections` 在 `v0.20.0` 为 `max_length=2`，在 `v0.21.0` 为 `max_length=32`；`interpolation` 同版放开为 `straight|smooth`，三截面以上必须用 `smooth`。M1 的实机证据见 [FEAT-065](../work-items/FEAT-065.md)「2026-11-11 M1 实施与实机验收」。这条补记不改变已发布附件及其摘要。

## v0.19.2（2026-11-08 本轮联网实测）

- 核对时间：`2026-11-08T12:20Z` / `2026-11-08 20:20 +08:00`。
- 标签对象：`v0.19.2` → annotated tag `fd8159cd5644d5e57f14cd0b80b35e0d5b7a1be0` → 提交 `df8e178553348fc1f438559a2d506ae6bfd5a9e0`。
- Release：[v0.19.2](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.19.2)，id `438226979`，非 draft、非 prerelease；`created_at=2026-11-08T12:19:21Z`，`published_at=2026-11-08T12:19:48Z`，`target_commitish=main`。
- 核对命令：`tools/check_release_assets.py --tag v0.19.2` → exit 0，「v0.19.2: four assets downloaded and verified; both sidecars match」。
- 四附件逐个列出（未用通配）；API `assets[].digest`、下载后本地实算 SHA256 与 sidecar 内容三者一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.19.2-source.zip` | 9 259 802 | `922fb7fdaf8d514f6cdc13b3b71984d1275213047f80afd5032aa495e447b7b5` |
| `MCP_CREO_MechDog-0.19.2-source.zip.sha256` | 101 | `ec17e070ef9cc696893855db77a5b551f568365496a46916291040ff66903279` |
| `MCP_CREO_MechDog-0.19.2-seed-library.zip` | 493 442 | `22a7a32d7636d6babf7b68b9526b6b935f4d97386ff06ba9c2487002f4e71558` |
| `MCP_CREO_MechDog-0.19.2-seed-library.zip.sha256` | 107 | `aeec87c4c01dbb91466253754cfa05c4210c13e1cd097d425c1fc9adb8bd434d` |

## v0.19.3（2026-11-09）

- 记录时间：2026-11-09。`main` 提交 `096e86a2a6d9a73c4716ca2e6758e03e9fcfab31`（`f1c0a94..096e86a` fast-forward），`origin/main` 同值；附注标签对象 `61d1d2b64fd2490853f2b5ec0bfb6ec74085e1d0`（`v0.19.3`，指向上述提交）。
- Release：[v0.19.3](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.19.3)，id `RE_kwDOU_ueTM4aLAs8`，非 draft（`isDraft=false`）、非 prerelease；`published_at=2026-11-09T12:15:07Z`。
- 核对命令：`tools/check_release_assets.py --tag v0.19.3` → exit 0，「v0.19.3: four assets downloaded and verified; both sidecars match」。
- 四附件逐个列出（未用通配）；下载后本地实算 SHA256 与 sidecar 内容一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.19.3-source.zip` | 9 333 252 | `aed3b422acd815dcf624423d1c9d43640c7fabb28c8a631c2eb2b0d0380df463` |
| `MCP_CREO_MechDog-0.19.3-source.zip.sha256` | 101 | `ddcc3a651173ef293974ffec35eabbb214559a3d7c4c19d56b032dad7f21470e` |
| `MCP_CREO_MechDog-0.19.3-seed-library.zip` | 493 442 | `bc85958afbf8f3da0affde7144c13a145ebdd95eb04df529015595c59ab1e64a` |
| `MCP_CREO_MechDog-0.19.3-seed-library.zip.sha256` | 107 | `8c1299fbb8066d3aefedeb6c3b98b4274a4d594a6a4d0266be4c90847b29f1d5` |

- 本版未改 `native/*.cpp`、未连 Creo、未编译执行器；验收与未测范围以 `docs/validation/RELEASE-0.19.3.md` 与 Release 正文为准。本段只做远端附件核对，不重新验证包内功能。

## v0.20.0（2026-11-10）

- 记录时间：2026-11-10 17:57（+08:00）。`main` = `origin/main` = `2d7b498cd793a3f4693a561df6ae0df8f809d0f7`（`2c78aaa..2d7b498`）；附注标签对象 `3f4ed82589536f572f7265b718d96970ecebe715`（`v0.20.0`，指向上述提交）。
- Release：[v0.20.0](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.20.0)，id `RE_kwDOU_ueTM4aPLew`，非 draft、非 prerelease，`published_at=2026-11-10T09:56:06Z`，target `main`。
- 核对命令：`tools/check_release_assets.py --tag v0.20.0` → exit 0，四附件齐全，两个 sidecar 与对应 ZIP 摘要一致。
- 四附件逐个列出（未用通配）；摘要与 sidecar 内容、远端 `sha256:` 逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.20.0-source.zip` | 9 398 084 | `896e03ffbdfa08c4c270e899c672b3812c98a88106cb575097d6f8da44d9c83d` |
| `MCP_CREO_MechDog-0.20.0-source.zip.sha256` | 101 | `091c580a1dbf0001a807802a72923e1e7c3aa5a4f1985b9b25e665299fa8a1ed` |
| `MCP_CREO_MechDog-0.20.0-seed-library.zip` | 493 442 | `6cde6888e80cf9dd9df1d8d86dec33eb308c193d3c5ca8c1e17af98f41ca0697` |
| `MCP_CREO_MechDog-0.20.0-seed-library.zip.sha256` | 107 | `3692847566796970abe5dbc8ca545b0f74458fcb3a134d03657a010f7368d23c` |

- 本版含 `native/*.cpp` 变更（B2/F11、B4/F08）与 B3/F06 进展字段；源码包解压后独立门禁 `Ran 3263 tests ... OK (skipped=5)`。本段只做远端附件与标签核对，不重新验证包内功能；功能验收以 [RELEASE-0.20.0](../validation/RELEASE-0.20.0.md) 与 Release 正文为准。

## v0.23.0（2026-11-12）

- 记录时间：2026-11-12 12:27（+08:00）/ 2026-11-12T04:27Z。`main` = `origin/main` = `0cfd42909f822dda7863f6d5a4c8dcb677f3dfb9`（`c6eb7f7..0cfd429`）；附注标签对象 `1962224cb99e2f860ca9e67b3cf4223ab03f43a3`（`v0.23.0`，指向上述提交）。
- Release：[v0.23.0](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.23.0)，id `442495969`，非 draft、非 prerelease，`created_at=2026-11-12T04:25:37Z`，`published_at=2026-11-12T04:26:54Z`，target `main`。
- 核对命令：`tools/check_release_assets.py --tag v0.23.0` → exit 0，「v0.23.0: four assets downloaded and verified; both sidecars match」。
- 四附件逐个列出（未用通配）；远端 `sha256:` digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.23.0-source.zip` | 9 694 983 | `a8abb957acd5f6989276ff4d5be426e14cc128050566f8507ec3be0656393e7a` |
| `MCP_CREO_MechDog-0.23.0-source.zip.sha256` | 101 | `6a8ac323bd30184acf288c5547fa7217c21782da796f57ba30c22be9989d30ca` |
| `MCP_CREO_MechDog-0.23.0-seed-library.zip` | 493 442 | `5394664c98f0f10777820dda8dd6ab07abf890b8324ec64ff59d662b1f978c0e` |
| `MCP_CREO_MechDog-0.23.0-seed-library.zip.sha256` | 107 | `ffcd1695bb04001a6adbf23556a0167d2ff63dae961cca6b78865482c317f0b5` |

- 本版含 `native/surface_loft.cpp`、`native/surface_boundary_fill.cpp`、`native/generic.cpp`、`native/sketch_coordinates.cpp`、`native/sketch_edit.cpp`、`native/worker.cpp` 变更（FEAT-066、DEV-082），升级后必须重编译 worker。源码包解压到短路径 `E:\r023\MCP_CREO_MechDog`（无 `.git`）后独立门禁 `Ran 3429 tests ... OK (skipped=6)`；首次在 `build/release-check-0.23.0` 深层路径下运行时有 1 项 `test_dev040_blackbox_fixture` 因 Windows 260 字符路径限制报 `Errno 2`，换短路径后通过，非产品缺陷。本段只做远端附件与标签核对，不重新验证包内功能；功能验收与未测范围以 [RELEASE-0.23.0](../validation/RELEASE-0.23.0.md) 与 Release 正文为准。

## v0.22.0（2026-11-11）

- 记录时间：2026-11-12 00:36（+08:00）/ 2026-11-11T16:36Z。`main` = `origin/main` = `2de2fa8d4e48a8ea0dbadb6c7c4cd7058513f280`（`ea753be..2de2fa8`）；附注标签对象 `e2e33bd1423eb33d097016d9cff68ffae3508809`（`v0.22.0`，指向上述提交）。
- Release：[v0.22.0](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.22.0)，id `441943346`，非 draft、非 prerelease，`created_at=2026-11-11T16:34:20Z`，`published_at=2026-11-11T16:35:24Z`，target `main`。
- 核对命令：`tools/check_release_assets.py --tag v0.22.0` → exit 0，「v0.22.0: four assets downloaded and verified; both sidecars match」。
- 四附件逐个列出（未用通配）；远端 `sha256:` digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.22.0-source.zip` | 9 636 010 | `5db68fe932019eebef3ad5b59e8ddc7f38f1f3c35e93122bb014e174a81af3ab` |
| `MCP_CREO_MechDog-0.22.0-source.zip.sha256` | 101 | `3dd87ec404b06cfb86c0171b01681f2914ea83b8e35a0cd23e5eee15ba7f3a42` |
| `MCP_CREO_MechDog-0.22.0-seed-library.zip` | 493 442 | `9fe456f2855fc165984e1bf715effd092f0d088a1551a50bcfda073d316e7743` |
| `MCP_CREO_MechDog-0.22.0-seed-library.zip.sha256` | 107 | `832968dced37a7e889e13ce043d05e51659a5a2935b8cbbf0243d319533e7000` |

- 本版含 `native/surface_group.cpp` 与 `native/surface_loft.cpp` 变更（FEAT-065 M3/M4）；源码包解压后独立门禁 `Ran 3413 tests ... OK (skipped=6)`。本段只做远端附件与标签核对，不重新验证包内功能；功能验收与未测范围以 [RELEASE-0.22.0](../validation/RELEASE-0.22.0.md) 与 Release 正文为准。

## v0.21.1（2026-11-11）

- 记录时间：2026-11-12（DEV-083 补齐历史缺口）。`main` 提交 `8622f1b3d11808d3c9c2cf76ebb1e3c937183a18`（`990c88a..8622f1b`）；附注标签对象 `f2ffc75ed7e95fd66bf7b1150797cd620e554955`（`v0.21.1`，指向上述提交）。
- Release：[v0.21.1](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.21.1)，id `441312185`，非 draft、非 prerelease，`created_at=2026-11-11T06:30:15Z`，`published_at=2026-11-11T06:31:05Z`，target `main`。
- 核对命令：`tools\check_release_assets.py --tag v0.21.1` → exit 0，「v0.21.1: four assets downloaded and verified; both sidecars match」。
- 四附件逐个列出（未用通配）；数据取自 [RELEASE-0.21.1](../validation/RELEASE-0.21.1.md) 的发布时记录，本轮未联网重下重算：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.21.1-source.zip` | 9 520 388 | `13952311b47b16dd0a6d90d6aca942d14245d660be3ae2e3264816d3a1b07add` |
| `MCP_CREO_MechDog-0.21.1-source.zip.sha256` | 101 | `f11fd5b9eebd620a8aff17131be47a1c65f9dbb52cb30676aaadb193767d4366` |
| `MCP_CREO_MechDog-0.21.1-seed-library.zip` | 493 442 | `49cfe0fdd691fd83796e05dc9a765f10189622d30a2645bbb87b8f42f511a736` |
| `MCP_CREO_MechDog-0.21.1-seed-library.zip.sha256` | 107 | `1ba5e65a6b4155aba788dfb81673e046b1f0d79895998af24633ab0fc2753364` |

- 包内快照与 `main` 的差异：源码包内的 `RELEASE-0.21.1.md`、`RELEASE_NOTES_0.21.1.md` 与 POSTCHECK 均为打包时点内容（当时没有本段）；本段与「源码包解压门禁 3315 项」只存在于 `main`，按冻结规则不回写、不重发已发布附件。本段只做远端附件与标签核对，不重新验证包内功能。

## v0.23.1（2026-11-12）

- 记录时间：2026-11-12（当日发布并回填）。`main` 提交 `3d250ac0340af933f021930db64324d91168d8b0`（`6dfbfba..3d250ac`）；附注标签对象 `fbd6a56e506b65c411919925dea90048c2138000`（`v0.23.1`，指向上述提交）。
- Release：[v0.23.1](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.23.1)，id `442581848`，非 draft、非 prerelease，`created_at=2026-11-12T06:42:32Z`，`published_at=2026-11-12T06:44:28Z`，target `main`。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py`（内置发布记录门禁）→ 标签/发布 → `tools\check_release_assets.py --tag v0.23.1`。
- 种子包 SHA256 `46d8d1f5024a05c4585f051bab1243791a7a9149a9eb90e1764a5ec9afb6a926`（24 个文件、9 个种子，两次构建一致）。
- 核对命令：`tools\check_release_assets.py --tag v0.23.1` → exit 0，「four assets downloaded and verified; both sidecars match」；该命令对 ≥ 0.23.1 同时解压源码包运行记录门禁并通过。
- 四附件逐个列出（未用通配）；远端 `sha256:` digest、本地重算与 sidecar 内容逐一致；`source.zip` 的摘要见同名 sidecar，不写入包内：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.23.1-source.zip` | 9 723 011 | `df02e02fe923d92fd75d117373d7b90384dda565ac0f6dad9113f84276e4c100` |
| `MCP_CREO_MechDog-0.23.1-source.zip.sha256` | 101 | `8262fd01179ac6f71c5a5920ea93faf711fad0dcebab6d572dd0a4f33fd4f908` |
| `MCP_CREO_MechDog-0.23.1-seed-library.zip` | 493 442 | `46d8d1f5024a05c4585f051bab1243791a7a9149a9eb90e1764a5ec9afb6a926` |
| `MCP_CREO_MechDog-0.23.1-seed-library.zip.sha256` | 107 | `161c51d454fb47147daa5c92f3a21b181778b1b1b2925d7bd2ad802ba71bca20` |

- 源码包解压到短路径 `E:\r0231` 后，把该目录临时 editable 安装到本机 venv 并运行 `python -m unittest discover -s tests`：`Ran 3443 tests in 396.706s`、`OK (skipped=6)`；随后已把 venv 恢复到 `E:\Projects\MCP_CREO_MechDog`。包内 `test_standard_install_supports_import_from_unrelated_working_directory` 等 5 项依赖“当前源码目录就是安装目录”，未切换安装前会失败，属测试环境约束而非产品缺陷。
- 本版含 `native/surface_loft.cpp`、`src/creo_mechdog/job_projection.py`、`src/creo_mechdog/operation_results.py`、`src/creo_mechdog/release_integrity.py` 与打包工具变更（BUG-119、DEV-083），升级后必须重编译 worker。Creo 12.4.0.0 实机：已有实体模型放样 8 项、YZ/XZ 正交平面 13 项、guides 回归 38 项全 PASS（报告见 `docs/validation/RELEASE-0.23.1.md`）。
- 包内快照与 `main` 的差异：源码包内的 POSTCHECK、`RELEASE-0.23.1.md`、`RELEASE_NOTES_0.23.1.md` 与 BACKLOG 是打包时点内容（当时没有本段与实际 Release id/时间）；本段、源码包全量单测与远端核对结果只存在于 `main`，按冻结规则不回写、不重发已发布附件。

## v0.25.0（2026-11-15）

- 版本与范围：`0.25.0` MINOR，公开工具 107→108；交付 [DEV-090](../work-items/DEV-090.md) 的 T1/T2/T3（组合）/T4/T5/T6a/T6b/T8 与 T7 诊断措辞，并包含已发布的 0.24.1 启动/无图形修复，发布记录见 [RELEASE-0.25.0](../validation/RELEASE-0.25.0.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py`（内置发布记录门禁）→ 标签/发布 → `tools\check_release_assets.py --tag v0.25.0`。
- 种子包 SHA256 `f8cf62d21d8c9d513fe6335e8e82b8064f48be642ad6a009cd433aa3257705fc`（24 个文件、9 个种子，两次构建摘要一致）。
- 源码包 `MCP_CREO_MechDog-0.25.0-source.zip` 由本提交源码构建，`package.py` 的四附件门禁与发布记录门禁均通过；字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.25.0`；四附件为 `MCP_CREO_MechDog-0.25.0-source.zip`、`MCP_CREO_MechDog-0.25.0-source.zip.sha256`、`MCP_CREO_MechDog-0.25.0-seed-library.zip` 与 `MCP_CREO_MechDog-0.25.0-seed-library.zip.sha256`；`source.zip` 的摘要见同名 sidecar，不写入包内。
- 本版新增 `native/base_flange.cpp`、`native/geometry_selectors.cpp`、`native/linear_pattern.cpp`，并修改 `native/advanced.cpp`、`native/generic.cpp`、`native/sketch_coordinates.cpp`，升级后必须重编译 worker。
- 包内快照与 `main` 的差异：实际 Release id、发布时间、四个附件摘要与本段回填只存在于 `main`，按冻结规则不改写、不重发已发布附件。
- Release：id `446058283`，非 draft、非 prerelease，`published_at=2026-11-15T12:51:01Z`，target `main`（`38bee48692d67d7f962d21ad713abbaa821c2fa7`，标签对象 `f617e5d26d326a0b51d52f298141e965a63d2041`）。
- 发布后核对：`tools/check_release_assets.py --tag v0.25.0` → exit 0，「v0.25.0: four assets downloaded and verified; both sidecars match」。远端 digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.25.0-source.zip` | 10 238 309 | `a1e949a302d1a0003dd9f98c0a44ec9e7096cda740fced526b09dec26f126d40` |
| `MCP_CREO_MechDog-0.25.0-source.zip.sha256` | 101 | `68486baf77050e947b00651003982926b47b193a1e5033fc35c1e449ee584174` |
| `MCP_CREO_MechDog-0.25.0-seed-library.zip` | 493 442 | `f8cf62d21d8c9d513fe6335e8e82b8064f48be642ad6a009cd433aa3257705fc` |
| `MCP_CREO_MechDog-0.25.0-seed-library.zip.sha256` | 107 | `a89288276cf7182dda630998da03130f544dfb2ddc5d7e4145b45f547d83864b` |

- 发布记录勘误（文档，不改已发布附件）：[RELEASE-0250-ERRATA-2026-11-16](../development/RELEASE-0250-ERRATA-2026-11-16.md) 补记直接前版应为 `0.24.1`、0.24.0 单测统计口径，以及 0.26.0 起的发布前后证据规则。

## v0.24.0（2026-11-13）

- 记录时间：2026-11-13 18:28（+08:00）/ 2026-11-13T10:28Z。`main` = `origin/main` = `b4e3d0971a0a8113c365c8d534512b844f3df7ab`（`8a08118..b4e3d09`）；附注标签对象 `71df612132da4904c59e74ac05679c11e4df16ee`（`v0.24.0`，指向上述提交）。
- Release：[v0.24.0](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.24.0)，id `444093452`，非 draft、非 prerelease，`created_at=2026-11-13T10:27:51Z`，`published_at=2026-11-13T10:28:16Z`，target `main`。
- 核对命令：`tools/check_release_assets.py --tag v0.24.0` → exit 0，「v0.24.0: four assets downloaded and verified; both sidecars match」。
- 四附件逐个列出（未用通配）；远端 `sha256:` digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.24.0-source.zip` | 10 090 013 | `cb18e49127f7bb4cfa99756257c7e5a3d3c64b4e35202dfc85668058e431d4f4` |
| `MCP_CREO_MechDog-0.24.0-source.zip.sha256` | 101 | `9d1617287dfaf8dd73a72dd9c364f5ea463463109f52035ab04149674c11974f` |
| `MCP_CREO_MechDog-0.24.0-seed-library.zip` | 493 442 | `c6d9a77b04ac397836464f8e12455a9b796e49b1193a796b2e1d28e782cd68f1` |
| `MCP_CREO_MechDog-0.24.0-seed-library.zip.sha256` | 107 | `7ca78d4e2b6406c8971434cb661150416ded931951f21eb30ada5d7669a62dba` |

- 种子包：24 个文件、9 个种子；回填 `docs/seed_package.json` 后重建一次，摘要仍为 `c6d9a77b04ac397836464f8e12455a9b796e49b1193a796b2e1d28e782cd68f1`。
- 本版含 `native/generic.cpp`、`native/surface_loft.cpp` 变更与新增 `native/import_geometry.cpp`，升级后必须重编译 worker。本段只做远端附件与标签核对，不重新验证包内功能；功能验收与未测范围以 [RELEASE-0.24.0](../validation/RELEASE-0.24.0.md) 与 Release 正文为准。

## v0.23.2（2026-11-13）

- 版本与范围：`0.23.2` PATCH，公开工具仍 107；交付 [BUG-120](../work-items/BUG-120.md) 的 `surface_loft` 提取失败诊断与运行期观测披露，以及 [DEV-083](../work-items/DEV-083.md) 的逐 ID 状态一致性与发布文档本地链接门禁，发布记录见 [RELEASE-0.23.2](../validation/RELEASE-0.23.2.md)。
- 打包顺序：`tools\package_seeds.py` → 回填 `docs/seed_package.json` → 重建确认摘要不变 → `tools\package.py`（内置发布记录门禁）→ 标签/发布 → `tools\check_release_assets.py --tag v0.23.2`。
- 种子包 SHA256 `4a47a58293f773d530c7ab2a771db075f3557222a207fb5dcff853594e66861a`（24 个文件、9 个种子、493 442 字节，两次构建摘要一致）。
- 源码包 `MCP_CREO_MechDog-0.23.2-source.zip` 由本提交源码构建，`package.py` 的四附件门禁与发布记录门禁均通过；字节数与 SHA256 见同名 sidecar，不写入包内文件。
- Release 地址：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.23.2`；四附件为 `MCP_CREO_MechDog-0.23.2-source.zip`、`MCP_CREO_MechDog-0.23.2-source.zip.sha256`、`MCP_CREO_MechDog-0.23.2-seed-library.zip` 与 `MCP_CREO_MechDog-0.23.2-seed-library.zip.sha256`；`source.zip` 的摘要见同名 sidecar，不写入包内。
- 核对命令：`tools\check_release_assets.py --tag v0.23.2` → exit 0，「v0.23.2: four assets downloaded and verified; both sidecars match」；该命令同时解压源码包运行记录门禁并通过。
- `main` 提交 `f20b3bb4136bdffc170b63039357368ffd4ee6bb`；附注标签对象 `58f8d8273aabbdbb947f766371374285f87537b5`（`v0.23.2`，指向上述提交）。
- Release：[v0.23.2](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.23.2)，id `442920884`，非 draft、非 prerelease，`created_at=2026-11-12T12:31:12Z`，`published_at=2026-11-12T12:31:38Z`，target `main`。
- 四附件逐个列出（未用通配）；远端 `sha256:` digest、本地重算与 sidecar 内容逐一致：

| 附件 | 字节 | SHA256 |
| --- | ---: | --- |
| `MCP_CREO_MechDog-0.23.2-source.zip` | 9 778 348 | `1bd12e893b5f37072d3f058af20a0e5d93d1e53195fc2bc2674c555b9400559c` |
| `MCP_CREO_MechDog-0.23.2-source.zip.sha256` | 101 | `d68aefeb652b08b65af555f07b9311fd96c5b22f4e6f346733f91aed07009077` |
| `MCP_CREO_MechDog-0.23.2-seed-library.zip` | 493 442 | `4a47a58293f773d530c7ab2a771db075f3557222a207fb5dcff853594e66861a` |
| `MCP_CREO_MechDog-0.23.2-seed-library.zip.sha256` | 107 | `129f19a1d4221a7d3c98d18998d94665442d05a2f1d93480d7a187b618e0e783` |
- 本批未连接 Creo（未取得本轮当次实机授权），按离线批次发布：Creo 12.4.0.0 实机回归与 `kernel_completion="supported"` 观测未执行，0.23.1 实机结论不外推。升级后必须重新编译 worker（`native/surface_loft.cpp` 变更）。
- 离线验证：`tools\dev_check.py --work-item BUG-120` 为 `success=true`（`Ran 3463 tests`、`OK`）；源码包解压到 `E:\r0232` 后切换 editable 安装运行全量单测为 `Ran 3463 tests in 479.169s`、`OK (skipped=6)`、exit 0，随后已恢复本机 venv 安装。
- 包内快照与 `main` 的差异：源码包内的本段、`RELEASE-0.23.2.md`、`RELEASE_NOTES_0.23.2.md` 与 BACKLOG 是打包时点内容；实际 Release id、发布时间与发布后核对只存在于 `main`，按冻结规则不回写已发布附件。

## 未覆盖

- 本核对只证明**远端附件与 sidecar、摘要三者一致**，不重新验证包内功能、Creo 实机或安装结果；这些结论分别属于各版 `docs/validation/RELEASE-*.md` 的实际范围。
- 只核对 GitHub Release 平台对象；镜像、本地下载缓存和客户端侧校验不在本文件范围。
- 本文件为首次补记，未回改 v0.17.4/v0.18.0/v0.18.1 已发布附件或原发布记录中的日期与结论。
