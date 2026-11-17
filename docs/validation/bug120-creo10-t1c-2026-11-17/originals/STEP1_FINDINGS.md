# T1-C 第 1 步：原件补齐与逐项比对（离线，未连接 Creo）

- 输入包：`D:\my\MCP_CREO_MechDog\test_runs\2026-11-17_t1b_id_driven_blend`（只读）
- 回执根：`D:\my\MCP_CREO_MechDog`（含 `models/`、`jobs/`）
- 输出：`test_runs/2026-11-17_t1c_closure/offline/`
- 工具：`review_t1b_package.py`（随包）+ 本目录新增 `verify_identity.py`

## 一、补齐结果

| 项 | 结果 |
| --- | --- |
| 随包审计 `prt_matches` | **6/6**（字节数与 SHA256 均与报告一致，模型 ID 与矩阵一致） |
| 随包审计 `host_matches` | **6/6**（宿主逐步选取日志与矩阵 `selection_log` 逐元组一致） |
| `integrity_ok` | **true** |
| 指定原件缺失数 | **0**（12 份全部收集到 `receipts/`） |

说明：`handoff/audit.json`（18:20 生成）里 12 项全缺，是因为那份是在异地、**没有** `--receipt-root` 的情况下跑的；在本机带上回执根重跑后缺失为 0。旧文件未被覆盖，本目录是新的补证输出。

额外补齐（任务书要求，随包审计不含）：按六个 `adopted_model_id` 找收养作业原始请求与结果，共 **18 个 `job.json` + 6 个 `batch.json`**，落在 `receipts/adoption/<model_id>/<job_id>/`。

| 模型 | inspect | apply | item |
| --- | --- | --- | --- |
| T1B_RUN_01 | `ed313b9e…` | `ef5099a9…` | `c7c630df…` |
| T1B_A_03 | `43c6f636…` | `2758a859…` | `8d98ea74…` |
| T1B_B_02 | `27942bcd…` | `e3f1ae5e…` | `654079c5…` |
| T1B_C_03 | `0d2b45a5…` | `4770db4b…` | `c8db5e04…` |
| T1B_C_05 | `867238a0…` | `aa88777f…` | `c9c83033…` |
| T1B_D_02 | `292ab22f…` | `33a9b417…` | `e10a8f53…` |

## 二、逐项比对（`identity_checks.json`）

六例 `identity_ok` 全为 true，逐项为：

| 检查 | 说明 | 结果 |
| --- | --- | --- |
| 面组关联本次新特征 | `quilt.feature_ids` 含矩阵里的 `created_feature_id`（54/63/63/71/87/65） | 6/6 通过 |
| 不是“取第一个 quilt” | 六个快照各只有 **1** 个 quilt，且该 quilt 正是新特征所属；同时按 `quilt_id` 命中而非按序号 | 6/6 通过（本批不存在多 quilt 干扰） |
| 测量作业指向同一 quilt | `operations[0].references` 与 `group.quilt_ids` 均为矩阵 quilt id（61/70/70/77/93/72） | 6/6 通过 |
| 作业模型一致 | `job.model_id` == `adopted_model_id` | 6/6 通过 |
| 重载校验 | `saved_file_reloaded_and_verified=true`、`source_unchanged=true`、`window_unchanged=true` | 6/6 通过 |
| 输入文件摘要 | apply 条目的 `file.sha256` 与该 PRT 在报告中的 SHA256 一致 | 6/6 通过 |

## 三、差异与需要更正的口径

1. **父引用顺序不能当作采集器顺序。** 矩阵里 `parents_are_the_requested_sketches` 用的是数组相等，只能证明“依赖集合恰好是这几个草图”。T1-B 报告 §5.1 把它写成“顺序与请求 index 一一对应”，这个表述**超出证据**，本步起降级为“集合证据”。真正的顺序观察放在第 4 步（抬高中间截面）。
2. **`ProFeatureNumSectionsGet` 返回 0** 的问题依旧存在，链数没有 API 回执。
3. **三/五截面 bbox 偏差 0.120005 mm**：本步用**原始测量作业里的 `open_edge_records.endpoints_mm`** 复算，六例的裁剪边界极值与预期完全一致（≤1e-6），三/五截面的四条边全部落在 Z=0：
   - C 三截面：`(0,0,0) (20,0,0) (0,40,0) (20,40,0)`
   - C 五截面：同上
   - 而 `bbox` 六向各多出 0.120005。
   - `bbox` 的来源已核实：`native/quilt_query.h:57-67` 对每个面取 `ProSurfaceDataGet(...)->data.p_surface_data->xyz_min/xyz_max` 求并集，是**曲面数据范围**，不是裁剪边界极值。
   - 若这 0.12 真是几何外扩，平面面积应为 20.24001×40.24001 ≈ **814.66 mm²**，而实测面积为 **800.0**。因此判定为数据范围余量，几何未偏移。第 2 步在实机副本上复核这一点。
4. **收养告警**：六份 apply 条目均带 `inspection_warnings: [{reason_code: native_sidecar_write_failed, fallback_status: verified}]`，已原样保留。

## 四、结论

- 原件补齐**完成**，矩阵不再只靠包外数据：指定快照与测量作业、收养请求与结果都已在包内，且逐项关联通过。
- 这仍不等于“几何被独立重测”——原件是当时测量的记录，不是重新测量。第 2 步会在实机副本上重新取样。
- 原测试的 `bbox_ok=false` **不修改**。
