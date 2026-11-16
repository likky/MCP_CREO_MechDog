# 2026-11-15 · CREO · 0.25.0 · `sheetmetal_base_flange` 把板宽 20 建到 Z 向，静默产出错误几何，致 Arm2 装配位置偏移 9.57 mm

> 用途：反馈给 `MCP_CREO_MechDog` 作者，用于下一版优化。
> 性质：**0.25.0 实机重跑 + 用户看图指错后的追加验收报告**。所有数值来自 Creo 10 上实际提交的 job 与 `saved_reloaded` 回读，不是静态源码推断。
> 触发：用户上传截图并指出「红圈里的零件的装配位置不对」。红圈内紫色小方块为 `Arm2`（族配色 `#A666D9`）。

---

## 0. 结论先行

1. **这是本轮唯一由「肉眼」发现、而不是由 job 回执发现的 P0 级静默几何错误**：`creo_sheetmetal_base_flange` 的 job `status=succeeded`、`stage=verified`、`saved_file_reloaded_and_verified=true`、`has_solid=true`、体积/拓扑回读全部正常，**没有任何一步报错**，但生成的首壁板宽方向是错的。
2. **根因**：传入 `plane="YZ"`、`width=20` 时，0.25.0 把 20 mm 的板宽沿 **零件 Z 轴**展开，而唯一指定 TXT 明确要求板宽 20 沿 **零件 X 轴**（`X ∈ −10…10`）。实测局部包络 `X −12…2 / Y 0…8 / Z 0…20`，TXT 要求 `X −10…10 / Y −2…8 / Z −2…12`。
3. **不是总装 transform 的错**：23/23 个 `[B-COMP]` 的 `R` / `t` 与提交给 MCP 的计划逐位一致（`max |ΔR| = 0.0`、`max |Δt| = 0.0 mm`），行向量约定 `world = p_local·R + t` 复现 TXT 总装质心误差 `0.0003 mm`（列向量读法为 `14.1846 mm`）。错位来自 **Arm2 零件自身的局部几何**。
4. **量化影响**：Arm2 局部质心从 TXT 指纹 `(0, 0.8681, 2.7828)` 偏到 `(-3.7432, 5.8865, 10.0206)`，偏差 **9.5699 mm**；经正确的 `[B-COMP]` 变换后，两个 Arm2 实例的世界质心各偏 **9.5699 mm**（旋转正交，距离不变），正是截图中紫色方块「歪出去」的量级。
5. **已用 0.24.1 已验证的降级路径重建 Arm2 并重建总装**：局部质心偏差降到 **1.6647 mm**（改善 **7.9051 mm**），板宽 20 回到 X 轴；但**仍不等价**于 TXT 的 `SMBaseFlange`（体积 647.774 vs 792.323 mm³、`Y max 6` vs `8`、`Z min 0` vs `−2`、四个 R3 圆角仍缺）。verdict 为 **PARTIAL FIX / DEGRADED**，不宣称 `EXACT` / `VERIFIED`。
6. **建议作者优先处理「回执不校验几何方向」这一点**：新工具若不能在回执里给出首壁的 `body_box` / `width_axis` / 质心，调用方只能靠肉眼发现错误，这比「功能缺失」更危险。

---

## 1. 复现环境与约束

| 项 | 值 |
|---|---|
| MCP | `MCP_CREO_MechDog` **0.25.0**（本机 `version.py` / `creo_capabilities.version` / `server_version` 一致，108 工具） |
| Creo | `Creo 10.0.0.0` / `release_numeric=42`，单 native channel |
| 唯一几何输入 | `二爪夹持机械臂_跨软件三维建模自然语言说明_v1.5.txt`（1225 行，单位 mm） |
| 建模工具 | **仅 `MCP_CREO_MechDog`**；本地脚本只解析 TXT、生成 JSON 计划与整理证据，不产生几何 |
| 外部模型输入 | **无**。未打开/导入 CREO 原文件、SolidWorks 原文件、NX PRT、STEP、Parasolid、STL、原代码包或任何实体 |
| 涉及模型 | `arm2_v0250`（`cf2ce7b30ba5409d9511a824941fb439`）、`assem_txt_v0250`（`6d5898fb73a744ea93440fb13a431eb7`）、修复件 `arm2_v0250_fix`（`d4154f21ebd043579216a978cf1b84e1`）、修复总装 `assem_txt_v0250_fix`（`e2e88719aa3d452cb62bcca0cf5cafc0`） |

---

## 2. TXT 对 Arm2 的硬要求（都是原文，不是推断）

```text
第 1113 行：[B-PART] body_box / facebox
  Arm2.SLDPRT    body_box=(-10,-2,-2,10,8,12) facebox=(-10,-2,-2,10,8,12) ... 最大差=0 mm

第 34 行：体积 / 质心指纹
  Arm2.SLDPRT    1/21/46/24   7.92323e-07   (0, 0.8681, 2.7828)

第 116 行：板宽方向
  尺寸修改 n3（必须执行，不是新特征）：把特征 SMBaseFlange 的尺寸 D2 设为 20 mm ……
  改后板宽 20 mm、X ∈ −10…10 mm

第 417 行：D016
  Arm2 基体法兰板宽（D2）｜20（X ∈ −10…10） mm

第 479–484 行：草图与特征
  [B-SKETCH] id=Arm2-S1 ... datum=right offset=10 origin=(0,0,0) xdir=(0,0,-1) ydir=(0,1,0)
  [B-GEO] sketch=Arm2-S1 i=0 kind=line x1=0 y1=8 x2=0 y2=0
  [B-GEO] sketch=Arm2-S1 i=1 kind=line x1=0 y1=0 x2=-12 y2=0
  [B-FEAT] part=Arm2.SLDPRT id=n2 type=sheet_metal sketch=Arm2-S1 thickness=2 bend_radius=0.7366 k_factor=0.5 reverse=1
  [B-FEAT] part=Arm2.SLDPRT id=n3 type=dimension feature_type=SMBaseFlange target=n2 dim=D2 value=20
```

即：**板宽 20 必须沿 X**，`X = −10…10`；局部质心 `(0, 0.8681, 2.7828) mm`；体积 `792.323 mm³`。

---

## 3. 实际提交给 0.25.0 的组合首壁参数

来自 `creo_plans_v0250/arm2_base_flange.json`（该 JSON 由 0.25.0 计划生成器从 TXT 派生，未引入 TXT 之外数值）：

```json
{
  "label": "arm2_n2",
  "thickness": 2.0,
  "radius": 0.7366,
  "k_factor": 0.5,
  "width": 20.0,
  "width_symbol": "D2",
  "plane": "YZ",
  "section": [
    {"type": "line", "start": [8.0, -0.0, 0.0], "end": [0.0, -0.0, 0.0]},
    {"type": "line", "start": [0.0, -0.0, 0.0], "end": [0.0, 12.0, 0.0]}
  ],
  "origin": [0.0, 0.0]
}
```

`creo_sheetmetal_base_flange` 的公开签名（`server.py`）：

```python
async def creo_sheetmetal_base_flange(
    model_id, expected_revision, label, section, width, thickness,
    radius=1.0, k_factor=0.5,
    plane: Literal["XY", "XZ", "YZ"] = "XY",
    origin: list[float] | None = None,
) -> dict[str, Any]:
```

**接口里没有「width 沿哪个轴」的参数**，也没有回执字段说明 width 被应用到了哪一根轴。调用方只能靠 `plane` 猜。本轮按 TXT 草图法线选了 `YZ`，结果 width 落到 Z。

---

## 4. 铁证：面 bbox 回读（不是推测）

`creo_inspect_model(detail=full, section=surfaces)` 对两个零件各取全部面的 bbox 并集，`inspection_source=saved_reloaded`：

| | 面数 | bbox 并集 mm | 关键特征 |
|---|---:|---|---|
| TXT 要求（第 1113 行） | — | `X −10…10 / Y −2…8 / Z −2…12` | 板宽 20 在 **X** |
| `arm2_v0250`（0.25.0 `sheetmetal_base_flange`，rev 3） | 17 | `X −12…2 / Y 0…8 / Z 0…20` | **每一个面的 bbox 的 Z 都是 `0…20`**，X 被压在 `−12…2`；20 mm 宽度在 **Z** |
| `arm2_v0250_fix`（0.24.1 降级路径，rev 4） | 20 | `X −10…10 / Y −2…6 / Z 0…12` | **每一个面的 bbox 的 X 都是 `−10…10`**；20 mm 宽度回到 **X** |

举例（`arm2_v0250` 的 `surface id=83`）：

```json
{"bbox": [[2.0, 0.0, 0.0], [2.0, 5.2634, 20.0]], "normal": [1.0, 0.0, 0.0]}
```

一块法线为 +X 的平板，其 Z 跨度却是 20 mm——板宽被沿 Z 拉伸了。相对地，`arm2_v0250_fix` 的 `surface id=83` 为 `[[-10,-2,2.7366],[10,-2,12]]`，X 跨度 20 mm，符合 TXT。

### 4.1 伴随的质心 / 体积 / 孔位退化

| 量 | TXT | 0.25.0 `base_flange` | 修复件 |
|---|---:|---:|---:|
| 局部质心 mm | `(0, 0.8681, 2.7828)` | `(-3.7432, 5.8865, 10.0206)` | `(0, 0.3964, 4.3793)` |
| 与 TXT 的质心距离 mm | 0 | **9.5699** | **1.6647** |
| 体积 mm³ | 792.323 | 685.3020（−13.51%） | 647.7743（−18.24%） |
| `features/surfaces/edges` | `21/46/24` 量级（TXT 拓扑计数） | `18/17/39` | `18/20/46` |
| Ø3 通孔 | 3 个 | 圆柱面只剩 3 个（`id 222/224/265`），孔位随板宽方向改变 | 6 个圆柱面（`222/224/226/228/272/274`），3 孔各自被折弯分成两段 |

> 注：TXT 第 34 行的 `1/21/46/24` 是源 CAD 的 topo 计数口径，与 Creo 原生特征计数不直接可比，此处只用于说明「不是等价重建」。

---

## 5. 装配位置偏差的量化（世界坐标）

`verify_arm2_fix.py` 用 **TXT 质心指纹 + MCP 回读的两个实测局部质心 + 实际提交给 `[B-COMP]` 的 transform**，按 `world = p_local·R + t` 计算：

| 实例 | TXT 期望世界质心 mm | `base_flange` 世界质心 mm | 修复件世界质心 mm | 偏差：修复前 → 修复后 |
|---|---|---|---|---|
| `Arm2-1` | `(-59.156, 137.782, -48.586)` | `(-59.622, 131.894, -56.116)` | `(-60.534, 137.445, -49.458)` | `9.5699 → 1.6647 mm` |
| `Arm2-2` | `(-68.096, 139.002, -41.225)` | `(-76.839, 141.386, -44.300)` | `(-68.749, 138.566, -42.693)` | `9.5699 → 1.6647 mm` |

两实例各改善 **7.9051 mm**。这解释了截图中紫色方块明显偏离夹爪机构、与绿色 `Arm1` 和黄色环形件错位的原因。

### 5.1 排除项：总装 transform 无错

`verify_assembly_placement.py`（输入只有 TXT 与本轮提交的计划 JSON）输出：

```text
check1 max |ΔR| = 0.0  max |Δt| mm = 0.0        → 23/23 EXACT MATCH
check4 reading=row    COM=[-1.414, 111.426, 26.630]  |Δ|=0.0003 mm
check4 reading=column COM=[-4.490, 112.984, 12.871]  |Δ|=14.1846 mm
```

行向量约定正确、矩阵未转置、未抄错。因此**不能靠改 transform 来掩盖局部几何错误**，否则会引入 TXT 之外的数值。

---

## 6. 为什么把它定为 P0：静默错误

| 环节 | 回执 | 是否报警 |
|---|---|---|
| `creo_sheetmetal_base_flange` job `4e2bc5c64e3341fea52e6eedb5079746` | `succeeded` / `composed_features` 正常 | 否 |
| 后续切孔 `plan_file` job | `succeeded` | 否 |
| `creo_inspect_model` | `healthy=true`、`has_solid=true`、`units=mm`、`saved_reloaded` | 否 |
| `assemble_component` 23 组件 | 23/23 `succeeded` + `committed`，transform 与 TXT 一致 | 否 |
| 总装 `creo_inspect_model` | `has_solid=true`、体积 `300120.94 mm³`、`saved_reloaded` | 否 |
| **用户看截图** | **红圈里零件位置不对** | **是（唯一发现途径）** |

`width` 是一个**正数且合法**的值，job 没有任何理由拒绝；但工具既没有把「宽度作用轴」暴露给调用方，也没有在回执里回报生成首壁的 `body_box` / `width_axis` / 质心。对 TXT-only 重建这类**没有参考模型可比、只能靠指纹核对**的场景，这等于把唯一可用的自检手段也关掉了。

---

## 7. 本轮修复与验证（全部通过 MCP）

1. 用 0.24.1 已验证、但当时标为「降级不等价」的路径重建 `arm2_v0250_fix`：
   `creo_new_sheetmetal(native_planar)` → `creo_sheetmetal_planar_wall(length=20, width=12, thickness=2, plane="XZ", direction="positive", origin=[-10,0])` → `creo_sheetmetal_flange(height=8, angle=90, radius=0.7366, y_factor=0.5, flip=false)` → `plan_file` 三条 `through_all` 切孔。5 个 job 全部 `succeeded`，revision 4。
2. 生成 `creo_plans_v0250/assembly_ops_v0250_fix.json`：仅把两个 Arm2 实例的 `source_model_id` 从 `cf2ce7b3…` 换成 `d4154f21…`，**其余 21 个组件、23 个 transform、11 族配色、61 条 `[B-MATE]` 参数一律不动**。
3. `creo_execute_plan(plan_file=...)` → job `eb16df70a4d74d77b8ede0f9253b5374`，`succeeded`、23/23 `committed`、`saved_file_reloaded_and_verified=true`，revision 1。
4. `creo_recolor_assembly` → job `f786662f64a14b34bf6159c73c6d9324`，`succeeded`，23/23 painted，保存/擦除/重载前后 readback 全在 `1e-6` 内，revision 2。
5. 独立 `creo_inspect_model(section=components)` 两页（14 + 9）复核 23/23：`appearance.state=present`、rgb 与 palette 一致、`transform == initial_transform`；`arm2_1`/`arm2_2` 均绑定 `d4154f21…` rev 4；**23/23 的 `constraints` 仍只有 `{type:13,type_name:"fix"}`**。

修复前后总装对照：

| | 修复前 `assem_txt_v0250` | 修复后 `assem_txt_v0250_fix` |
|---|---:|---:|
| 体积 mm³ | 300120.9377215249 | 300045.88227178744 |
| 差值 mm³ | — | **−75.0554497** = `2 × (647.7742993 − 685.3020241)` |
| 质心 mm | `(-0.7878, 112.4034, 27.3518)` | `(-0.7555, 112.4033, 27.3891)` |
| 最终文件 | `...\6d5898fb73a744ea93440fb13a431eb7\output\assem_txt_v0250.asm.3` | `...\e2e88719aa3d452cb62bcca0cf5cafc0\output\assem_txt_v0250_fix.asm.3` |
| sha256 | `33a2bff1…` | `2c153c47929b25db77c28aea3b2fff7bd770db96b6fe58a66003aea6ff9fa837` |

体积差**精确等于两个 Arm2 实例的体积差**，反向证明其余 21 个组件与全部 transform 未被改动。

---

## 8. 建议给作者（按优先级）

1. **【最高】明确并暴露 `width` 的作用轴**。给 `creo_sheetmetal_base_flange` 增加显式参数（例如 `width_axis="X"|"Y"|"Z"` 或 `width_direction=[1,0,0]`），并在 `plane` 与各轴之间给出无歧义的映射表；当 `plane="YZ"` 时默认行为必须写进 `REFERENCE_SYNTAX.md`。当前调用方无法从签名判断 20 mm 会落在哪根轴上。
2. **在 job 回执里回报首壁的可核对几何**：至少 `body_box`（6 个数）、`center_of_gravity`、`width_axis`、`composed_features` 各自的参数。让调用方能自动与 TXT 的 `body_box` / 质心指纹比对，而不是等用户看图。建议对「回执 box 与调用方声明的期望 box 不一致」提供可选 assertion（类似 `creo_execute_plan.assertions`）。
3. **补 TXT 语义的「单特征首壁 + 尺寸修改」路径**：0.25.0 的组合首壁是 2 个 feature，且本轮是直接把 `width=20` 当参数传入，没有执行 TXT 第 445 行规定的「先建默认 1 mm、再把 `SMBaseFlange` 的 `D2` 改成 20」步骤。0.25.0 已交付 `{feature, symbol, value}` 符号定位尺寸，建议把它与单特征首壁打通，并给出与 `792.323 mm³` 的实测对照。
4. **不要把「组合首壁」与「`SMBaseFlange` 中面加厚」在能力清单里混列**；若无法等价，请保持 `RELEASE_NOTES_0.25.0.md` 现有的「不声称等价」措辞，并额外加一条「方向语义可能与 TXT frame 约定不同」的提示。
5. （与上一篇反馈的 B3 合并）四个 R3 圆角仍因 `geometry_selector` 只接受 `endpoints_mm` 两端点、TXT 只给单点锚点而无法建；这仍是 Arm2 体积/包络无法收敛到指纹的直接原因之一。

---

## 9. 证据文件清单（本工作区）

```text
creo_plans_v0250/arm2_base_flange.json                提交给 0.25.0 的组合首壁参数（含 plane=YZ / width=20）
creo_plans_v0250/arm2_fix_ops.json                   修复件三条 through_all 切孔计划
creo_plans_v0250/assembly_ops_v0250_fix.json         修复总装 23 组件计划（只替换 2 个 Arm2 绑定）
creo_plans_v0250/arm2_fix_placement_evidence.json    局部/世界质心偏差、bbox 铁证、总装前后对照
creo_plans_v0250/assembly_build_v0250_fix.json       修复总装 job / 分色 / 独立巡检 / sha256
verify_assembly_placement.py                        23 个 [B-COMP] transform 与矩阵约定复核
verify_arm2_fix.py                                  本报告的偏差量化脚本（不产生几何）
2026-11-15-CREO-0.25.0-新增coincident与geometry_selector仍无法消费TXT锚点致61条配合零建立.md   上一份 0.25.0 反馈
```

---

## 10. Caveats / 不夸大

* **不是 transform 缺陷，也不是 TXT 缺陷**：23/23 transform 与 TXT 逐位一致、行向量约定复现 TXT 总装质心误差 0.0003 mm；问题只在 `sheetmetal_base_flange` 生成的局部几何方向。
* **修复件仍不等价**：体积 `647.774` vs `792.323 mm³`（−18.24%）、`Y max 6` vs `8`、`Z min 0` vs `−2`、四个 R3 圆角仍缺。**这是降级修复，不是精确复现**，所以 verdict 只能是 `PARTIAL FIX / DEGRADED`。
* **总装质心没有显著向 TXT 收敛**：Arm2 只有两件且体积很小（约 648 mm³ / 件，占 300046 mm³ 总装的 0.22%），修复后总装质心变化不足 0.04 mm；不能拿总装质心当本问题的验收指标，必须用 Arm2 局部/世界质心与面 bbox。
* **61 条 `[B-MATE]` 仍 0 条建立**，23 个组件仍是 `fix`；`underconstrained=false` 不代表配合已建。原因见上一篇反馈的 A 节。
* **颜色不是几何证据**：分色只写在装配组件层，源 `.prt` 字节未变；本报告的位置结论来自面 bbox 与质心回读，不来自 preview 图。
* **没有做跨软件 `compare_parts` / 逐 body 惯性矩与惯性积比对**，验证等级仅为 MCP 自身 `saved_reloaded` 巡检，不冒充 E3/E4。
* 本轮没有引入 TXT 之外的任何几何数值；修复路径的参数来自 0.24.1 已在本工作区实测并留档的降级方案，仍全部由 `MCP_CREO_MechDog` 执行。

---

## 11. 结论

0.25.0 新增的 `sheetmetal_base_flange` 把「能不能建出带折弯的首壁」解决了一半，但把「按 TXT 的 frame 约定把板宽放到正确轴上」留成了未定义的隐式行为，且**成功回执不回报任何可核对的方向信息**。在 TXT-only、无参考模型可比的重建里，这类静默错误比显式的「能力缺失」更难发现、代价更高：本轮靠用户看截图才定位，之后用面 bbox 与质心指纹才做出客观判定。

建议下一版优先做 **8-1（显式 width 轴）** 与 **8-2（回执回报 body_box / 质心 / width_axis）**；这两项不增加建模能力，却能让「工具成功」与「几何正确」之间重新建立可验证的联系。
