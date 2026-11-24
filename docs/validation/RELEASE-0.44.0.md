# 发布记录 v0.44.0

日期为 2026-11-24，版本类型为 MINOR，公开工具数 111。

上一版本：0.43.2（`v0.43.2`，提交 `a6769c3cc2507e9bb69fc26651d45050e2d2d27a`）。

## 验收范围

本版汇集 [DEV-100](../work-items/DEV-100.md) 与 [DEV-101](../work-items/DEV-101.md) 已完成本机 Creo 10.0.0.0（`release_numeric=42`）实机验收的 9 项交付（[BUG-186](../work-items/BUG-186.md)、[FEAT-084](../work-items/FEAT-084.md)、[FEAT-085](../work-items/FEAT-085.md)、[BUG-187](../work-items/BUG-187.md)、[BUG-188](../work-items/BUG-188.md)、[BUG-189](../work-items/BUG-189.md)、[BUG-190](../work-items/BUG-190.md)、[FEAT-088](../work-items/FEAT-088.md)、[FEAT-089](../work-items/FEAT-089.md)），以及 [BUG-130](../work-items/BUG-130.md) 独立导出预算/阶段进度补项与 DEV-100 草图闭合/旋转两点轴与弧度收敛。

- **钣金与 STL**（BUG-186 / FEAT-084 / BUG-130 / FEAT-089）：Creo 10 四象限法兰实测、Arm2 毛坯 `850.185803 mm³` / 包络 `(-10,-2,-2)–(10,8,12)` / 内外弯 R0.7366/R2.7366、错误宽向断言回滚、0.02 mm STL 导出 90 s 预算与 6 阶段日志、连续两段 `sheetmetal_flange` 附着与方向控制（`35bd8865…`）均保存重载通过。
- **边选择器**（FEAT-085）：薄板直边与圆盘圆弧 6 组正反例实测 `on_face` 过滤、`ambiguity="nearest"` 唯一最近与等距拒绝，保存重载与回滚均通过。
- **草图闭合、显式 v 轴、构造圆与旋转输入**（DEV-100 / BUG-187 / BUG-188）：
  - 4 缝 `4.33418842e-4 mm` 圆弧+直线槽自动焊合拉伸（`7c4b8163…`，`2785.398 mm³`、`residual_max_mm=0.0`）；0.005 mm 开口坐标草图失败报错 `Nearest open ends:` 并回滚（`b1dc66dd…`）；
  - 无中心线草图 + 两点式 `axis={"start_mm":[0,0],"end_mm":[0,16.285538]}` + `angle_rad=6.28319` 旋转（`76b8c23e…`，`1279.063164 mm³`、`angle_clamped_from_deg=360.000269`）及冲突中心线拒绝回滚（`917b7865…`）；
  - 偏移 XZ 基准面 `flip` + 显式 `v_axis=[0,0,1]` 拉伸（`0046cec9…`，`1000.0 mm³`、Z `[0,20]`）及平行法线拒绝回滚（`4e5d44b7…`）；
  - `coordinates` 含 2 构造圆 + 3 构造线草图拉伸（`f7d9e4be…`，`1000.0 mm³`、`construction_entities=5`、`geometry_deviation_max_mm=1.22e-30`）。
- **装配与 MCP 调用/诊断**（FEAT-088 / BUG-189 / BUG-190）：3 实例装配（`3c502dfe…`，`fixed` `constraint_count=1` vs `packaged` `constraint_count=0`，`3000.0 mm³`，重心 `[25.0, 8.3333, 5.0]`，保存重载通过）；未知工具参数按 schema 拒绝并附拼写建议；`creo_get_job` 失败作业顶层透传 `failed_operation_index`/`failed_stage`/`failure_phase`/`native_result_path`/`round_failure_summary`。

## 单测与离线检查

验证环境为 Windows x64 和 Python 3.12.10。

`python tools/dev_check.py --work-item DEV-101` 通过。工作树全量单测通过，0 失败、0 错误，Ruff 与 clang-format 按项目基线检查无新增问题；更新检查、模型恢复及 MCP stdio 三项离线门禁通过，MCP 服务报告 0.44.0 和 111 个工具。精确的 `tests_run`、`run_id` 与受测源码指纹由当次打包时配套的 `build/unit_test_report.json` 与 `build/unit_test_run.json` 共同校验。

## 种子包

先运行 `tools/package_seeds.py --allow-record-mismatch` 取得摘要并回填 `docs/seed_package.json`，再用默认校验重建确认一致。种子包含 24 个文件和 9 个种子，SHA256 为 `cfc72a788053ce067feb90021d6558a1c1db1f5f5002edcca341d779edc7a791`。

## 未测范围

Creo 9/12 实机编译与建模、WorkBuddy 黑盒验收、两圆弧直接焊合、报告原件完整 Arm2/Arm7 零件、原 STL 挂死超时现场，以及 [FEAT-086](../work-items/FEAT-086.md)（放样曲线链）、[FEAT-087](../work-items/FEAT-087.md)（按重建镜像特征）均不在本版实机验收范围内。

## 附件

- `MCP_CREO_MechDog-0.44.0-source.zip`
- `MCP_CREO_MechDog-0.44.0-source.zip.sha256`
- `MCP_CREO_MechDog-0.44.0-seed-library.zip`
- `MCP_CREO_MechDog-0.44.0-seed-library.zip.sha256`

种子包 SHA256 为 `cfc72a788053ce067feb90021d6558a1c1db1f5f5002edcca341d779edc7a791`。源码包摘要记录在同名 sidecar 中。两份同名 sidecar 分别记录对应 ZIP 的实际 SHA256。[GitHub Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.44.0)

## 逐 ID 状态核对

| ID | 交付版本 | 实际 Release | 技术状态 | 卡首页 | 主台账 | 差异说明 |
| --- | --- | --- | --- | --- | --- | --- |
| [BUG-186](../work-items/BUG-186.md) | 0.44.0 | v0.44.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 本机 Creo 10 四组合通过；待 Creo 9/12 与外部复测 |
| [FEAT-084](../work-items/FEAT-084.md) | 0.44.0 | v0.44.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 本机 Creo 10 Arm2 毛坯与回滚通过；待完整零件与外部复测 |
| [FEAT-085](../work-items/FEAT-085.md) | 0.44.0 | v0.44.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 本机 Creo 10 直边/圆弧 6 组通过；待原 Arm7 与 Creo 9/12 |
| [BUG-187](../work-items/BUG-187.md) | 0.44.0 | v0.44.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 本机 Creo 10 正反例通过；待 Creo 9/12 与 WorkBuddy 黑盒 |
| [BUG-188](../work-items/BUG-188.md) | 0.44.0 | v0.44.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 本机 Creo 10 构造圆+构造线通过；待 Creo 9/12 与 WorkBuddy 黑盒 |
| [BUG-189](../work-items/BUG-189.md) | 0.44.0 | v0.44.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 离线协议单测与 stdio 检查通过；待 WorkBuddy 黑盒 |
| [BUG-190](../work-items/BUG-190.md) | 0.44.0 | v0.44.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 离线 compact/full 投影单测与原生构建通过；待 WorkBuddy 黑盒 |
| [FEAT-088](../work-items/FEAT-088.md) | 0.44.0 | v0.44.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 本机 Creo 10 3 实例 packaged 装配通过；待 Creo 9/12 与 WorkBuddy 黑盒 |
| [FEAT-089](../work-items/FEAT-089.md) | 0.44.0 | v0.44.0 | 已有修复但待验收 | 已有修复但待验收 | 已有修复但待验收 | 本机 Creo 10 实测确认现有 SheetmetalFlangeOp 覆盖；待外部复测 |

## 远端核对

发布后执行，当前未验证。发布后远端证据将记录在[发布后附件核对记录](../development/RELEASE-POSTCHECK-2026-11-07.md)。
