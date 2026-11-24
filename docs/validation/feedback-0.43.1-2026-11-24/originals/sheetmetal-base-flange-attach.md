# 2026-11-24 CREO MCP_CREO_MechDog 0.43.2 反馈

收件：MCP_CREO_MechDog 作者
环境：Windows x64 / Python 3.12.10 / Creo Parametric 10.0.0.0（`release_numeric=42`）
本机版本：0.43.0（`server_version=0.43.0`，`tool_count=111`，`release_status=stable`）
上游最新：0.43.2（2026-11-24 查询）
主题：`sheetmetal_base_flange` 在 Creo 10 实机通过，但只能新建独立两段链；钣金成形类能力仍未解禁，配电箱剩余缺口只能靠通用薄板近似推进

---

## 1. 版本差分（不跳过中间版本）

| 版本 | 类型 | 与本任务相关内容 |
|---|---|---|
| 0.43.0 | MINOR | 111 工具；交付 BUG-183（B 样条除料求解面积）、FEAT-082（JPEG 全正交视图/自定义矩阵）、BUG-184（草图位移诊断）、FEAT-083（`ExtrudeOp.region` 内点选区）、BUG-185（`get_job` 参数说明）。未提钣金成形。 |
| 0.43.1 | PATCH | 仅 BUG-017 加强筋逐阶段原生诊断与未激活再生失败回执；Creo 10 L 形加强筋 17/17 通过；工具数仍 111。未提钣金成形。 |
| 0.43.2 | PATCH | 仅 BUG-175 启动单测补修；4495 项单测通过；Creo 9/10/12 原生安装、连接、建模与几何重载及外部反馈复测**未执行**；工具数仍 111。未提钣金成形。 |

结论：`0.43.1`/`0.43.2` 两个 PATCH 都不改变钣金能力；本机 0.43.0 与上游 0.43.2 在本任务相关能力上没有差异。

## 2. 新能力实机证据（Creo 10）

### 2.1 `sheetmetal_base_flange` 可用

作业 `c685213cbb3b40caaee71dc249028c1c`，模型 `bf_probe_043`（`2c61b9df3fcf40d1be8c1c49ac4d2cf8`）：

```json
{
  "op": "sheetmetal_base_flange",
  "label": "bfprobe",
  "plane": "XY",
  "section": [
    {"type":"line","name":"l1","start":[0,0,0],"end":[20,0,0]},
    {"type":"line","name":"l2","start":[20,0,0],"end":[20,8,0]}
  ],
  "width": 50, "thickness": 1, "radius": 2.54, "k_factor": 0.5
}
```

结果：`status=succeeded`、`toolkit_code=0`、`saved_file_reloaded_and_verified=true`；
`volume_mm3=1334.7610416982188`，包围盒 `X=0..20, Y=0..50, Z=-8..1`，1 body、14 surfaces、28 edges、10 features。
这是该操作首次在 Creo 10 上留下实机证据（此前工作卡只写 Creo 12.4.0.0 测过）。

### 2.2 但对配电箱剩余缺口不可用

TXT §4.3/§4.4 要在**已有箱体**的 ±X 壁顶边补 20 mm 向内水平框边，再在内缘向 **+Z** 折 8 mm 止口。实测/源码契约显示：

1. `sheetmetal_base_flange` 由「矩形 planar wall + 一条 90° flange」组合而成，只能新建独立两段链，没有附着到已有壁/已有边的模式；
2. 第二腿朝板法向反侧：XY 平面下第一腿在 `Z=0..1`，第二腿在 `Z=-8..0`，无法直接得到向 +Z 的止口；
3. `expected_width_direction_world` 只是断言，不是旋转控制（`BUG-129`）；
4. `section` 只接受恰好两条相连且垂直的直线，不能表达带释放槽的闭合框边。

因此只能回退到 `extrude(mode=add, new_body=true)` 薄板近似（作业 `af8ef5a7ec374493a57ad14c88788474`，增料精确 10368.0 mm³）。

## 3. 问题清单

### 3.1 仍门禁（沿用 DEV-078，跨版本未解）

| 操作 | 本机状态 | 原始说明 |
|---|---|---|
| `creo_sheetmetal_flange_profile` | unavailable | `DEV-078 multi-entity flange profiles are offline candidates only; hem/joggle geometry, sheetmetal identity, flat pattern and saved reload are not verified` |
| `creo_sheetmetal_corner_relief` | unavailable | `DEV-078 independent three-surface corner relief is an offline candidate only; a real ripped edge and intersecting bends are prerequisites, not verified inputs` |
| `creo_sheetmetal_quilt_form` | unavailable | `DEV-078 quilt form is an offline candidate only; native forming, gauge retention and flatten/unflatten behavior require hardware evidence` |
| `creo_surface_boundary_fill` | unavailable | `DEV-078 four-boundary two-direction blend is offline only and not published` |

影响：百叶圆滑端部、角部 0.2 mm 接缝/释放槽、冲压罩壳原生成形均无法做。

### 3.2 新增：base flange 缺少附着与方向控制（建议编号 DEV-078 / B-FLANGE-01）

- **现象**：`sheetmetal_base_flange` 只能新建独立 L 形链，第二腿固定朝板法向反侧；无法指定附着到已有钣金壁的某条边，也无法把第二腿翻到 +Z。
- **期望**：提供 `attach_to`（已有壁的边/面引用）与 `second_leg_side` / `flip` 控制；或至少在回执中明确告知「只能新建、不能附着」，避免调用方误判。
- **证据**：作业 `c685213cbb3b40caaee71dc249028c1c`（成功但方向相反），以及 `0.43.0` 源码 `SheetmetalBaseFlangeOp` 契约。

### 3.3 仍存在：多实体无法融合（跨版本未解）

- `BooleanOp.valid_bodies` 明确拒绝负 body id：

  ```text
  BOOLEAN_BODY_REFERENCE_UNSUPPORTED: negative body IDs can be returned by
  inspection but are not supported by this Boolean feature path; ...
  Sheetmetal-to-solid fusion is unverified even with positive IDs
  ```

- 即使切到 `conversion` 模板拿到正 id，Creo 10 上 `boolean_bodies(union)` 仍 `ProFeatureWithoptionsCreate=-1` 并回滚（历史作业见 out5/out6 反馈）。
- `redefine_solidify_body` 只处理失效的 `PRO_E_BODY_SELECT`，**不是**融合工具；0.43.x 没有新增把 `new_body=true` 增料并回钣金主体的能力。
- 影响：箱体 15 bodies、门板 3 bodies，无法达到 TXT 所述单实体。

### 3.4 仍存在：历史回执口径差异（沿用 P-A）

多轮廓含圆弧切除的 `material_removed_mm3` 比 `material_area_mm2` 系统性少约 16.00（格栅）或 21.37（百叶开口）mm³；拓扑面数与解析栅格均证明孔已切穿，是回执口径而非几何错误。

## 4. 对配电箱任务的判断

- 可以推进，但推进来自 `extrude(new_body=true)` + TXT 精确尺寸，不是来自 0.43.1/0.43.2 或新钣金操作。
- 本轮补齐 ±X 两条 20 mm 框边与两条 8 mm 止口，箱体 rev14→rev15，V=`117455.2014563 → 127823.2014563 mm³`，增料与解析值 10368.0 mm³ 完全一致；已重出装配/STEP/快照/预览，见 `out7/交付说明.md`。
- 剩余缺口（角部 0.2 mm 接缝、R2.54 内圆角、R3 圆头、百叶圆滑端部、单实体融合）仍被上述门禁与融合限制挡住，除非作者解禁 DEV-078 相关能力或提供可靠的钣金体增料/融合路径。
- 本轮所有结论均来自 Creo 10 实机作业与落盘回执，未把近似描述成严格原模型。
