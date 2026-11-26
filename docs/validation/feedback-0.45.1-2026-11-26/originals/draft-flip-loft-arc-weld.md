# MCP_CREO_MechDog 0.45.1 验收问题汇总

## 0. 验收环境与结论

- 日期：2026-11-26
- 服务版本：`MCP_CREO_MechDog 0.45.1`
  - `creo_session_status.server_version = 0.45.1`
  - `creo_capabilities.update.latest_version = 0.45.1`
  - release：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.45.1`
- CAD：Creo Parametric 10.0.0.0，`release_numeric=42`，单位 mm
- 会话：`connected=true`，`toolkit_code=0`，`state=ready`
- 验收方式：只通过 MCP 新建临时 MCP 管理零件做最小算例；没有引用工作空间外模型输入，没有导入实体。
- 总体结论：
  - v0.44.0 的 `extrude add` 静默抹实体、bbox 包含刀具包络、`dimensioning:auto` 挪圆心这三个高危问题，在本次最小回归中未复现。
  - 但发现 3 类仍需作者处理的问题：`draft` flip 语义与公开说明相反；`surface_loft` / `creo_loft` 在当前 Creo 10 会话中开箱不可用；近容差端点焊接本体仍未实现，只能靠调用方预吸附绕过。
  - 另有一项能力边界容易误导：`creo_capabilities` 的 `registered_operations` 包含 4 个 `unavailable_operations`。

---

## 1. P1：`draft` 的 flip 语义与工具说明相反，按文档操作会加料而不是去料

### 实测

基准件：XY 平面圆 `R3`，圆心 `(0, -0.092)`，沿 +Z 拉伸 2 mm。中性面取 XY 基准面 `datum_plane id=6`，拔模圆柱侧面 `surface id=57/59`，角度 `+5°`。

| 调用 | 体积 before → after (mm³) | `material_delta_mm3` | `draft_geometry` |
|---|---:|---:|---|
| `flip=false` | 56.5486677646 → 59.9110369070 | **+3.3623691424** | `applied_pull_vector=[0,0,1]`, `effective_flip=false`, `direction_flip_code=1` |
| `flip=true` | 56.5486677646 → 53.3145470845 | **−3.2341206801** | `applied_pull_vector=[-0,-0,-1]`, `effective_flip=true`, `direction_flip_code=-1` |

对应作业：

- `498e0e4c74124f49b1a1563ac6074fca`（`flip=false`）
- `f74103945bc94ecab48dc781bcdf5a29`（`flip=true`）

### 问题

`creo_draft` 工具说明写的是：

> 对外圆柱凸台，中性面在底部、pull 朝自由端时，正角度会收窄自由端。

本次中性面在 z=0，基准面法向 +Z 正好朝自由端 z=2；按说明 `flip=false` 应收窄自由端、体积减少。实测却是 `flip=false` 加料，`flip=true` 去料。也就是说，公开语义与实际体积效应相反。

虽然 job 返回了 `effective_flip` / `applied_pull_vector` / `direction_flip_code`，但这些字段只描述原生翻转码，没有告诉调用方“这次是加料还是去料”。用户按文档写脚本会做错方向。

### 影响

- 逆向建模时若按文档选 `flip=false` 做“收窄”拔模，实际会放大凸台。
- 只有在读 `material_delta_mm3` 后再重试相反 flip 才能成功，自动化脚本不能一次写对。

### 建议

1. 修正工具说明，明确 Creo 10 实测口径：上述几何下 `flip=false` 加料、`flip=true` 去料；或者修正底层 flip 映射，使文档语义成立。
2. 在 job 结果里增加 `material_effect`：`added` / `removed` / `unchanged`，从 `material_delta_mm3` 派生，避免用户只靠经验判断。
3. 若保留现有行为，建议 `direction_flip_code=1` 与 `effective_flip=false` 的关系也解释清楚，否则字段看似矛盾。

---

## 2. P1：近容差端点焊接本体仍未实现，诊断有了但能力没有

### 实测

使用历史回归件 `scripts/gear10.json`（40 段圆弧，10 个近闭合轮廓）。

- 原始文件作业：`07847274462145a8a26d7c1c924134e2`
  - 草图成功：10 closed contours，40 entities，0 open ends，analytic area `184.9802950743`
  - 几何偏差最大 `2.136e-14 mm`
  - 但 native section 报告端点簇扩散 `8.21534265e-07 mm`
  - 后续 `extrude` 失败：
    `ProFeatureWithoptionsCreate=-1`
    `SURFACE / section looks closed but endpoints joined only by diagnostic tolerance are not welded by kernel`
- 对照文件 `scripts/gear10_snapped.json`（调用方预先吸附端点）：
  - 作业：`d58c3697134a468ab249ea6f3de78681`
  - 成功，体积 `184.9802853253 mm³`，保存重载验证通过。

对照计划文件：

- `scripts/v0451_gear10_plan.json`
- `scripts/v0451_gear10_snapped_plan.json`

### 问题

这是从 0.9.0 起反复反馈的老问题，到 0.45.1 仍然是：

- MCP 能诊断近容差端点，能告诉用户“snap endpoints and retry”；
- 但 MCP 自身没有把端点真正焊到一起的能力；
- 用户必须离线修改 JSON 或在调用前自己做吸附。

换句话说：诊断能力已修，建模能力未修。

### 影响

- 从 TXT 或测量数据重建轮廓时，圆弧/直线端点经常有 1e-7 ~ 1e-4 mm 级误差；
- 只要误差落在 Creo 的焊接容忍窗口之外，整条特征链就断在 extrude；
- 用户必须维护一套“外部吸附脚本”，违背只靠 TXT + MCP 建模的目标。

### 建议

1. 在 `create_sketch` / `sketch` 中提供真正的 `weld_pairs` 或 `snap_endpoints=true`，把诊断出的端点对写回为同一坐标或添加 Creo 约束。
2. 至少在 `coordinates` 模式下，对被判定为同一闭合轮廓且间隙小于显式 `weld_tolerance_mm` 的相邻端点自动强制共点，并把吸附量报告出来。
3. 若设计上不打算自动吸附，请把这个能力从“sketch profile diagnostics”表述中分离出来，避免被理解为已经支持端点焊接。

---

## 3. P1：`surface_loft` 在 Creo 10 上两条创建路径都不可用，但 capability 仍显示为 enabled

### 3.1 element_tree 路径实测

作业：`d5d77b968e0d4415bf26f1413d026d53`

模型：两个 XY 开直线草图，`z=0` 与 `z=10`，各一条 `(0,0)→(10,0)`。

调用：

```json
{
  "creation_route": "element_tree",
  "sections": ["sl0", "sl1"],
  "interpolation": "straight"
}
```

结果：

- `create_code = 0`
- `extract_code = -18`
- `feature_incomplete = true`
- 作业失败：`SURFACE_LOFT_EXTRACT_UNSUPPORTED`
- job 已回滚：`rollback_status = succeeded`

### 3.2 resident_panel 路径实测

作业：`8bf651141b4d4538bdaee3b9b70cf6b9`

调用：

```json
{
  "creation_route": "resident_panel",
  "sections": [
    {"label": "sl0", "open_confirmed": true},
    {"label": "sl1", "open_confirmed": true}
  ]
}
```

结果：

- `BLEND_CALLBACK_SETUP_REQUIRED`
- `readiness = not_loaded`
- `reason = recorded_application_not_active`
- `next_action = start_or_register_application_manually`
- 回滚成功，没有产生曲面。

同时 `creo_callback_status` 实测：

```json
{
  "readiness": "not_loaded",
  "registration_status": "unknown",
  "reason": "recorded_application_not_active"
}
```

### 问题

`creo_capabilities` compact 报告：

- `operations` 包含 `surface_loft`
- `families.surface_loft.enabled = true`
- `creo_session_status.worker_build_identity.features.surface_loft_panel.state = ready`

但在这台实际的 Creo 10 机器上：

- element_tree 路径被 Creo 10 的 `ProFeatureElemtreeExtract=-18` 卡死；
- resident_panel 路径需要人工注册并启动 `blend_callback_protk.dat`；
- 不人工干预时，`surface_loft` 实际不可创建任何曲面。

这属于“MCP 有工具，但开箱不可用”。

### 建议

1. 在 `creo_capabilities` 的 `surface_loft` family 中增加清晰的 `runtime_admission`，例如：
   - Creo 10：element_tree unsupported；resident_panel requires callback ready；
   - callback not_loaded 时，compact 页面不要只显示 enabled。
2. `creo_surface_loft` 在提交 job 前，如果 `creation_route=resident_panel` 且 callback 不 ready，直接 before-job 拒绝；本次是 job 建立后才失败，虽然回滚成功，但占用了通道。
3. 如 `accept_unverified_completion=true` 对 Creo 10 仍不能保留特征，应在工具说明里直说，不要让用户误以为它是可用逃生口。
4. 提供真正不依赖手工 GUI 注册的 fallback，或把“注册/启动辅助应用”的步骤做成明确的一键/脚本流程。

---

## 4. P2：`creo_loft` 同样依赖未启动的 resident callback

### 实测

模型 `4f0860b5860c4dcfb355a26519a031a1`：两个 R5 圆草图，z=0 与 z=10。

调用 `creo_loft(sections=["loft_a","loft_b"], mode="add", interpolation="straight")`：

- 作业：`b0f3acddc9bf479dbd8e6c0c844bd388`
- 失败阶段：`callback_preflight`
- 结果：`BLEND_CALLBACK_SETUP_REQUIRED`
- `readiness = not_loaded`
- `model_unchanged = true`

### 问题

工具说明已经写了 callback 要求，但 compact capabilities 仍把 loft 家族列为 enabled。对调用方而言，这是又一个“工具存在但当前会话用不了”的入口。

### 建议

与第 3 项合并处理：在能力页和工具文档中把 `enabled` 拆成 `implemented` 与 `runtime_ready`，并在 `creo_loft` 的 receipt 中直接返回 `callback_status`，不要等到 job 才拒绝。

---

## 5. P2：capability 列表把未实现操作列入 registered_operations，容易误导

`creo_capabilities` compact 中同时出现：

`registered_operations`：

- `sheetmetal_flange_profile`
- `sheetmetal_corner_relief`
- `sheetmetal_quilt_form`
- `surface_boundary_fill`

`unavailable_operations` / `unavailable_tools` 又说明这些是 offline candidate 或不可用。

### 问题

如果客户端只用 `registered_operations` 判断能力，会误以为这些功能可调用。虽然 compact 页面另有 `unavailable_operations`，但两个列表并列且字段相似，容易被自动化逻辑读错。

### 建议

1. `operations` 只列当前会话可提交的操作；
2. 新增 `registered_but_unavailable_operations`；
3. 或者给每个 operation 条目加 `callable: true/false` 与 `reason` 字段。

---

## 6. 本次回归通过项

以下问题在 0.45.1 的最小算例中未复现，建议作者保留修复：

| 项目 | 作业 | 实测 |
|---|---|---|
| v0.44.0 `extrude add` 静默抹掉已有实体 | `d6aa8fa5e0bc42378cd1d8068057a242` | 重复添加同一 10×10×5 实体，V 500→500，`material_delta=0`，没有体积倒跌 |
| bbox 包含刀具/草图包络 | `4ea2bbbf6d4d4ebba864954df389fd9f` | 刀具从 z=-2 到 z=7 切除，最终 bbox 仍为 `[0,10]×[0,10]×[0,5]`，V=320 |
| `dimensioning:auto` 挪圆心 | `d5878277e2254c8c87d35d80ce33f5ab` | 圆中心 `(0,-0.092)` 保持不变，`solver.used=coordinates`，CoG y=-0.092 |
| `datum_plane` 角度符号 | `5f6ea5158486419fbac92f70fbe8ce45` | 绕 +Z 从 RIGHT 面旋转 +54°，读回 normal `(0.587785, 0.809017, 0)`，与文档一致 |
| FEAT-069 region extrude | `222280c7e7734d91b88f8ce6608c5fff` | YZ 双矩形草图，用 `interior_point_yz_mm=[5,5]` 只拉伸左轮廓，V=500，派生草图正确 |
| 会话歧义 / startup -4 | `creo_session_status` / `creo_callback_status` | 当前 `connected=true`, `toolkit_code=0`；两个 Creo 进程被诊断列出，但没有触发 -36；未复现 startup -4 |

补充使用注意：region extrude 使用 `interior_point_yz_mm` 时，源草图要用显式 `line`/`arc` 图元；直接用 `rectangle` primitive 会被拒绝并提示没有 open boundary entities。该行为与工具说明的“circles/rectangles/ellipses cannot be named by a boundary signature”部分一致，但建议把 `interior_point_yz_mm` 模式同样适用的限制写得更明确。

---

## 7. 建议优先级

1. **高**：修正 `draft` flip 文档与/或语义，并在结果中给出加料/去料结论。
2. **高**：实现真正的近容差端点焊接，或把“不支持焊接”作为明确的一等能力边界。
3. **高**：让 `surface_loft` 在 Creo 10 上至少有一条开箱可用路径；否则 capability 不要显示 enabled。
4. **中**：让 `creo_loft` / callback 依赖在提交前即可判定，并统一到 `runtime_ready` 字段。
5. **中**：整理 `registered_operations` 与 `unavailable_operations` 的展示口径，避免客户端误判。
