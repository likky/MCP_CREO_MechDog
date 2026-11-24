# 2026-11-24 CREO MCP_CREO_MechDog 0.40.0 专项反馈

## 结论先行

本次在最新版 `MCP_CREO_MechDog 0.40.0` 下，按唯一指定 TXT 重新完成 TXT-only / MCP-only 建模、装配、分色与配合验证。

- **12/12 零件建成**，最终 job 均 `succeeded` 且 `saved_file_reloaded_and_verified=true`。
- **23 组件固定放置总装成功**，11 族分色成功；23 组件 RGB 写入前后及重载后读回全部在 `1e-6` 内。
- 组件变换矩阵与 TXT 派生计划逐项比对：**23/23 匹配**，最大元素误差 `1.130879917488059e-09`。
- `coaxial:"any"` **大圆柱、小圆柱探针均成功**；0.33.0 起的约束类型文案修复在 0.40.0 仍有效。
- `response_detail="compact"` 与 `creo_list_components(fields,limit,cursor)` 仍有效，大回执未超限。
- **Arm7 两个历史核心问题仍未修复**：
  1. T6c `ExtrudeOp.region` 三区域切除仍在提交期零命中；
  2. T9a G2 R30 圆角可生成，但只有 conic 枚举/半径写入证据，仍无几何级曲率连续性验证字段。
- **全量 60 条配合仍未完成**，失败点与 0.35.4 相同：`arm2_1` 第一条 `mate` 表面选择器零命中，回滚干净。

---

## 1. 版本与环境

| 项目 | 实测值 |
|---|---|
| 本机版本 | `0.40.0` |
| `creo_check_update(force=true)` | `up_to_date`, `latest_version=0.40.0`, `from_cache=false` |
| CREO | `10.0.0.0`, `release_numeric=42` |
| 会话 | `connected=true`, `toolkit_code=0`, `channel_policy=single_channel_busy_rejects_immediately` |
| 唯一几何来源 | `二爪夹持机械臂_跨软件三维建模自然语言说明_v1.5.txt` |
| TXT SHA256 | `9a9b945f72895ed941da84f487988db0516a3c61ad5f77301f93b4bc8d788aee` |
| 外部模型输入 | 无（无 CREO / SW / NX 原文件、STEP、Parasolid、STL、原代码或实体导入） |

初始 `session_health.status="unknown"`，原因 `no_recent_verified_save`，但显式 `creo_session_status` 探针已确认 Toolkit 连接成功且通道空闲；本轮 12 个零件与装配 job 均完成保存重载验证，未构成阻塞。

发布说明核查（`0.36.0` → `0.40.0`）：

- `0.36.0`：保存/恢复修复；B 样条切除新增 `approximation_segments`；放样与同计划引用。
- `0.36.1`：仅验证工具链，不改建模链路。
- `0.37.0`：边选择器类型、嵌套装配源、看门狗、装配基线恢复、B 样条坐标尺寸与面积空值等。
- `0.37.1`：仅冒烟脚本/离线门禁，不改建模核心。
- `0.38.0`：`feature_id` 回填、线性阵列防呆、`extrude cut + through_all + scope`。
- `0.39.0`：旧会话诊断与恢复解死锁、`creo_inspect_model` 近邻查询、边选择器 `feature` 过滤。
- `0.40.0`：恢复超时落盘、冗余巡检优化、倾斜基准面自动正交锚定、盲切低去料告警、`chamfer_type` 内联保留。

**结论：0.36.0–0.40.0 未见针对 Arm7 `ExtrudeOp.region`、G2 几何验证或全量装配配合选择器的直接修复。**

---

## 2. 本轮完成结果

### 2.1 零件 12/12

| 零件 | model_id | 最终 job | revision | 体积 mm³ |
|---|---|---|---:|---:|
| arm1 | `bedf4ce824d34f309887685067e59d88` | `ab98ee19362d4597b2414245b3bb70fa` | 2 | 4126.083392843276 |
| arm2 | `fb2c1fdc4f20454a9bd9d6b04961e128` | `2a7eb013175e4291b6c5a1160d9a1ac7` | 4 | 647.7742992709299 |
| arm3 | `8dc69569ecef4d1ab0cf2edabb110d2b` | `e48e286491714ae4a39b08ea37dd75bb` | 2 | 4191.876137929114 |
| arm4 | `d847439240bc406086666c7969138825` | `5571824feee9401287c1182a4ae8e849` | 2 | 2134.6763516951005 |
| arm5 | `573094e7f7f34fe1b848f8627536ff1d` | `d6fdfb9bff5345c9a257a1d901f34529` | 2 | 1962.2637132689993 |
| arm6 | `9cc9bd6be6a848d08da9b2a92d08c75e` | `f67d121d6f484084b90e62f5706714be` | 2 | 406.52209570730724 |
| arm7 | `0c45d333166e43498333fb80f6912259` | `8f28f3700d944da4b672114fbc77fccd` | 3 | 1446.2293728128377 |
| arm8 | `0eb33cbd6f4e4c97b90fde4d7f425b88` | `2b906c40ebcc44d7ad6cbb38dc01f70f` | 2 | 113.09733552923255 |
| base | `f826a57c87d14308b928c97d8fc7b567` | `5859c006e9eb4c0caeab9a652f14e8e4` | 2 | 20970.97133874671 |
| hom | `a68064c568d94cb6983bb1c4d19ab97e` | `8e77de7802a942daac04d41f573005f5` | 2 | 98007.61545738482 |
| lateral | `e82e194279c2444d8b0d9719cfd4870b` | `85eb43afba80489a96015bab775ebd4d` | 2 | 19927.02392055217 |
| rotor | `6faac0bbfe2b4eea8ea20942d54a38cc` | `eac82ff9b1d04aec82881428df2bb2e9` | 2 | 17103.94539497728 |

说明：arm6 体积较 TXT E16 指纹仍低约 12.37%，属于 TXT v1.5 自身未闭合项，非本轮 MCP 缺陷。

### 2.2 固定放置总装与分色

```text
assembly model = assem_txt_v0400
model_id       = 3e651ddb024b4caf9171b1f87dd89d30
assembly job   = 86723bf09d67473c81ec275c057e3cb1
status         = succeeded, revision 2
components     = 23
part_file      = ...\assem_txt_v0400.asm.3
sha256         = 28982f55fdfa71bf6e6cbf2585814f9b5bc950529228a677f5e80216f032bf80

recolor job    = 1692d791c1534aa8a3148cd5f57c0098
status         = succeeded, revision 3
families       = 11
painted        = 23
unmatched      = 0
readback_before_save_count  = 23
readback_after_reload_count = 23
readback_all_within_tolerance = true
readback_tolerance = 1e-6
```

几何级位姿复核：

```text
components compared        = 23
all source_model_id match  = true
all constraints fix        = true
all underconstrained=false = true
max matrix element error   = 1.130879917488059e-09
worst label                = rotor_1
```

---

## 3. 已确认修复或保持有效的项目

### 3.1 `coaxial:"any"` 大/小圆柱均成功

```text
large model = coax_large_v0400
large job   = 460f5625626b4cedad1474423eddeec0
status      = succeeded, revision 2

small model = coax_small_v0400
small job   = ab59295ad81342b19efc19df8efa5d0e
status      = succeeded, revision 2
components  = base_1, hom_1, lateral_1
```

0.31.1 的小圆柱误选平面问题在 0.35.4 已修复，0.40.0 复测仍通过。

### 3.2 约束错误文案按真实约束类型

全量配合失败时，顶层与失败诊断都明确指向 `mate`，不再把 `mate_offset` 误写成 `concentric/insert needs a real cylinder`：

```json
{
  "feature_label": "arm2_1",
  "failed_constraint_index": 0,
  "failed_constraint_type": "mate",
  "constraint_stage": "reference",
  "constraint_reason": "constraint_rejected"
}
```

### 3.3 大回执与组件列表仍在预算内

- `creo_execute_plan(response_detail="compact")` 提交 23 组件 / 60 约束计划正常返回。
- `creo_list_components(fields,limit)` 可一次返回 23 组件；无字符超限。

---

## 4. 仍未修复问题 P1：Arm7 T6c `ExtrudeOp.region` 零命中

复测计划：

```text
creo_plans_v0400\arm7_region_cut_probe_ops.json
model_id = 0c45d333166e43498333fb80f6912259
expected_revision = 1
```

提交阶段即被拒绝，未创建 job：

```text
region signature matched none of 1 closed loops in sketch 'arm7_s7';
compare the YZ endpoints with the sketch frame, not region_index_hint
```

TXT 中完整续建数据仍存在：

```text
[B-SPLINE] index=0 degree=3 order=4 count=4
[B-SPLINE] index=1 degree=3 order=4 count=6
[B-CUT] sketch=Arm7-S7 depth=3 region_count=3 region_index_hint=4,2,5
[B-REGION] region=0/1/2 signature_yz_mm=(...)
```

Arm7 基础 job（`921ce8d25edf4e519b8fe1df6fd20181`）回执显示 `arm7_s7`：

```text
native_section.b_spline_entities = 2
native_section.closed_contours   = 0
native_section.open_ends         = 1
profile.area_status              = unavailable_unsupported_entities
geometry_deviation.max_deviation_mm = 0.04549858399999884
```

这里还存在语义不一致：region 匹配器称“1 closed loops”，native 草图诊断却报 `closed_contours=0 / open_ends=1`。建议作者以同一套 native 环拓扑为准并公开诊断。

影响：Arm7 只能完成主体轮廓、两条 B 样条所在草图与 G2 圆角，T6c 三个指定区域仍无法切除。

建议：

1. 基于草图平面真实拓扑提取闭合环，而不是只取实体首尾端点。
2. 支持 B 样条与直线混合边界按交点重参数化后匹配。
3. 失败回执返回实际 loop 端点、段数、最接近输入签名的 loop 及差异。
4. 统一 region 匹配器与 native section 对“闭合/开端点”的口径。
5. 若 native 确实不支持 sketch-region 选择，应明确标注“不可实现”，而不是保留真实数据上持续零命中的契约。

---

## 5. 仍未修复问题 P2：Arm7 G2 圆角无几何级验证

实测：

```text
base job     = 921ce8d25edf4e519b8fe1df6fd20181
G2 job       = 8f28f3700d944da4b672114fbc77fccd
status       = succeeded, revision 2 (after G2)
save job     = 4a0b7039f13a426380899b4adf8fc257, final revision 3
volume before= 1440.0574689346402 mm³
volume after = 1446.2293728128377 mm³
material_delta_mm3 = 6.171903878197554
saved_file_reloaded_and_verified = true
```

特征树 dump：

```text
job  = 73009f91ac6d4712ab298e03e53adbe8
file = ...\jobs\73009f91ac6d4712ab298e03e53adbe8\output\feature_254.xml
```

关键 XML：

```xml
<PRO_E_STD_FEATURE_NAME type="wstring">ARM7_G2_R30</PRO_E_STD_FEATURE_NAME>
<PRO_E_RNDCH_CONIC_TYPE type="int">3</PRO_E_RNDCH_CONIC_TYPE>
<PRO_E_RNDCH_CONIC_VALUE type="double">0.500000</PRO_E_RNDCH_CONIC_VALUE>
<PRO_E_RNDCH_LEG_VALUE type="double">30.000000</PRO_E_RNDCH_LEG_VALUE>
```

0.40.0 的 round 回执给出 `volume_before_mm3` / `volume_after_mm3` / `material_delta_mm3` / `reference_application`，证明特征确实改变几何；但仍没有 `g2_verification` 或任何曲率连续性几何量。当前证据只能证明“native 特征树写入 conic 枚举与半径”，不能证明几何上达到 G2。

建议：在 `curvature_continuous=true` 时返回：

```json
{
  "requested_curvature_continuous": true,
  "native_conic_type": 3,
  "native_conic_value": 0.5,
  "max_curvature_gap": "...",
  "tolerance": "...",
  "verdict": "pass | fail | unsupported"
}
```

若 Toolkit 无法读取曲率，应返回 `unsupported`，不要把“写入枚举”表达成“验证通过”。

---

## 6. 仍未修复问题 P3：全量 60 条配合仍在 `arm2_1` 零命中

计划：

```text
creo_plans_v0400\assembly_ops_v0400_mated_final.json
ops           = 23
constraints   = 60
model         = mated_txt_v0400
model_id      = 8e402de0965047378d1259ac601c9850
job_id        = e44cb879d1da4b51a340b2888ba976f2
status        = failed
stage         = execute_assemble_component
failed_op_index = 7
failed_label    = arm2_1
rollback_succeeded = true
```

失败诊断：

```json
{
  "failed_constraint_index": 0,
  "failed_constraint_type": "mate",
  "constraint_stage": "reference",
  "constraint_reason": "constraint_rejected"
}
```

顶层消息仍为：

```text
geometry_selector surface filters matched none of the 23 planar/cylindrical model faces
(tolerance_mm=0.001000, axis_tolerance_deg=0.500000);
re-read creo_inspect_model surfaces[] and pass current normal/origin/radius,
or use {kind:'surface',id:N}.
radius_mm filters a cylinder's radius; it is not a surface-type filter.
The closest nameable faces are listed in geometry_selector_diagnostic.nearest_surfaces
```

`geometry_selector_diagnostic` 实测：

```text
candidate_count = 23
matched_ids     = []
nearest_surfaces[0] = {id:233, type:plane, normal:[0,1,0], origin_mm:[0,-0.254,0], error_mm:0.25400001539911266}
nearest_surfaces[1] = {id:66,  type:plane, normal:[0,1,0], origin_mm:[0,0,0],    error_mm:0.5080000153991127}
```

结论：0.35.4 → 0.40.0 失败点完全一样，`arm2_1` 第一条 `mate` 仍零命中；失败后 23 个组件干净回滚，未残留半状态。小圆柱探针能成功，说明问题不是所有 `geometry_selector` 都失效，而是全量计划中该 `mate` 的面选择条件没有可执行修复路径。

建议：

1. `nearest_surfaces` 后给出可直接复制的 `{kind:"surface",id:N}` 修复建议。
2. 明确 `requested_coordinate_space="assembly"` 时搜索的是装配坐标下的组件面还是装配面；当前消息写 “model faces”，诊断又写 assembly。
3. 对 `points_mm + axis` 的 `mate/coincident`，允许在公差内投影到候选平面并报告投影误差，而不是零命中。
4. 增加一个“dry-run 只验证所有选择器”的入口，避免长计划在最后阶段才整体回滚。

---

## 7. job 证据索引

| 用途 | job_id | 结果 |
|---|---|---|
| Arm7 基础模型 | `921ce8d25edf4e519b8fe1df6fd20181` | succeeded，B-spline entities=2 |
| Arm7 region 复测 | 无 job，提交期拒绝 | 仍零命中 |
| Arm7 G2 R30 | `8f28f3700d944da4b672114fbc77fccd` | succeeded，体积增加 6.171903878197554 mm³ |
| Arm7 保存 | `4a0b7039f13a426380899b4adf8fc257` | succeeded，revision 3 |
| Arm7 G2 特征树 dump | `73009f91ac6d4712ab298e03e53adbe8` | succeeded，`feature_254.xml` |
| 23 组件固定总装 | `86723bf09d67473c81ec275c057e3cb1` | succeeded，revision 2 |
| 11 族分色 | `1692d791c1534aa8a3148cd5f57c0098` | succeeded，revision 3 |
| coaxial 大圆柱 | `460f5625626b4cedad1474423eddeec0` | succeeded |
| coaxial 小圆柱 | `ab59295ad81342b19efc19df8efa5d0e` | succeeded |
| 全量 60 条配合 | `e44cb879d1da4b51a340b2888ba976f2` | failed，`arm2_1` 零命中 |

---

## 8. 优先级建议

| 优先级 | 问题 | 建议 |
|---|---|---|
| P1 | Arm7 T6c region 仍零命中 | 基于 native 环拓扑匹配，统一闭合口径，补充 loop 差异诊断 |
| P1 | 全量 60 条配合在 `arm2_1` 零命中 | `nearest_surfaces` 后给可执行修复路径，明确 assembly/model 坐标语义 |
| P2 | G2 仍无几何级验证 | 增加 `g2_verification` 或明确的 `unsupported` 状态 |
| P3 | region 契约长期零命中 | 若 native 不可实现，应显式标注不可实现，避免用户反复投入 |

---

## 9. 交付说明

本文件用于反馈给 `MCP_CREO_MechDog` 作者。所有结论来自本机 `0.40.0` 实跑；几何来源仅为指定 TXT，建模过程未使用任何外部模型输入，也未导入实体。计划与证据目录：`creo_plans_v0400/`；汇总证据：`rebuild_summary_v0400.json`。
