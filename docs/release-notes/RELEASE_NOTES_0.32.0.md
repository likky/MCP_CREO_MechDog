# MCP_CREO_MechDog 0.32.0

一句话：把 0.27.0 反馈批的六项离线修复与两条诊断接通——提交回执和组件列表有了有界分页，坏引用在派发前就拒绝，切除与焊接给出分型判据，同一圆边被拆成多段时不再建议“缩小公差”，回转轴与草图平面的关系也能在失败回执里读到实测数字。

- 类型：MINOR（新增可选入参 `response_detail`、`fields`/`limit`/`cursor`，新增回执与诊断字段）
- 日期：2026-11-20
- 公开工具：**109 个**（不变；能力通过既有工具的参数与回执扩展）
- 上一版本：0.31.1
- 主台账：[BACKLOG](../BACKLOG.md) · 发布记录：[RELEASE-0.32.0](../validation/RELEASE-0.32.0.md) · 工作卡：[DEV-094](../work-items/DEV-094.md) · [FEAT-068](../work-items/FEAT-068.md) · [FEAT-023](../work-items/FEAT-023.md) · [BUG-076](../work-items/BUG-076.md) · [BUG-019](../work-items/BUG-019.md) · [FEAT-008](../work-items/FEAT-008.md) · [FEAT-051](../work-items/FEAT-051.md) · [FEAT-039](../work-items/FEAT-039.md)

## 对外可见变化

### 1. 提交回执与组件列表有界（FEAT-023 / BUG-076）

- `creo_execute_plan` 新增可选 `response_detail: "full" | "compact"`，缺省仍是 `full`。`compact` 只在 MCP 回执里省略 `operations` 数组，保留 `job_id`/`status`/`revision`/`message` 等标量与文件摘要；`jobs/<id>/job.json` 仍写完整内容，轮询 `creo_get_job` 不受影响。非法取值的拒绝发生在取 Toolkit 通道之前。
- `creo_list_components` 新增 `fields`、`limit`、`cursor`：32 KiB 以内保持旧形状，超出后按 `model_id`+`revision`+`fields`+记录快照指纹绑定游标分页；单条自身超预算时返回超限标记而不是截断记录。分页原语与 `creo_get_job` 共用同一预算实现，不再各写一套。

### 2. 请求形态在派发前拒绝（BUG-019 / FEAT-008）

- 顶层裸引用、`edge` 与 `surfaces` 混用、两者皆缺、`surfaces` 不是两项、槽位与操作不匹配、空 `edge` 槽，现在都在提交阶段给出具名错误，不再进 worker 才失败。

### 3. 模型名拒绝按原因分类（DEV-094 任务 1）

- 长度、字符、首字符与大小写提示分开：只有请求里真的出现大写时才提示“已转小写”，字符错误会指出具体字符，长度错误带实际字符数，命名词前缀不再无条件附加。

### 4. 切除体积变化分型（FEAT-051）

- 体积变化回执新增 `material_increased` / `material_removed` / `no_material_removed` / `unmeasurable` 四态，原始 `before`/`after`/`removed` 与原生 `status` 原样保留；本层只分类，不重写原生状态、不自行判成功。

### 5. 焊接资格判据共用（FEAT-039）

- 端点焊接的资格从“间隙 ≤ 阈值”改为几何与拓扑分类（圆弧不一致、位移超限、合并会闭合轮廓、歧义配对、两开链接缝未解决），准入与提交调用同一个函数；诊断文案统一带 “For this profile:”。

### 6. 同圆多弧段拒绝改为可行路径（FEAT-068）

- 一条物理圆边被 Creo 报告为多段同圆心、同半径圆弧时，圆心+半径过滤会全部命中，任何更小的 `tolerance_mm` 都无法收敛。拒绝文案现在列出命中的弧段 id，并给出 `point_mm`（指定目标跨度上的点）或 `{kind:'edge',id:N}` 两条可行路径。
- 判据按**实测**圆心与半径比较（分量差与半径差均 `≤ 1e-6 mm`）。两个不同圆恰好都落进较宽公差时仍保留“缩小公差”的原建议，不会被误报成同圆。

### 7. 回转轴与草图平面的实测关系（DEV-094 任务 4）

- 显式轴回转在创建特征前暂存 `revolve_axis_plane_relation`：实测轴原点/方向、草图平面原点/法向、有符号距离、出平面角、到法向角与 `axis_lies_in_plane`，并附 `thresholds`（`1e-6 mm` / `1e-3 deg`）。
- 再生失败时同一组数字会重复在失败消息里，不必打开操作记录。**该关系只分类、不设闸门**：Creo 允许绕空间任意直线回转，非共面轴本身不是错误，文案明确写“这些实测数字本身不说明 Creo 为何拒绝”。

## 行为变化与升级注意

1. `response_detail`、`fields`/`limit`/`cursor` 都是可选参数，旧调用行为不变；`compact` 只影响 MCP 回执，不影响落盘作业记录。
2. 本版**有原生改动**（`native/geometry_selectors.cpp`、`native/generic.cpp`）：升级后需重新编译 worker（`bridge.py build`），不能沿用上一版本的构建。
3. 种子库 `compatible_server_version=0.32.0`，与 0.31.x 的种子包不通用。
4. 同圆多弧段场景下，`radius_mm`+`center_mm` 单独使用仍会被判为多命中（这是事实，不是缺陷）；请改用 `point_mm` 或按 id 选择。

## 验证

- 离线：`tools/dev_check.py` 全量单测通过、lint 0、未格式化 0；`python bridge.py build` exit 0。
- 实机（Creo 12.4.0.0，经用户确认后执行）：
  - 同圆多弧段四算例（圆管夹具）：只给圆心+半径时回执列出 `ids 72, 90` 并给 `point_mm`/id 指引，`point_mm` 与 `{kind:'edge',id:90}` 各自圆角成功、保存重载通过、体积 2304.668647961009 mm³。
  - 容差对照（实心圆柱，两圆同心距 10 mm）：`tolerance_mm=20` 命中 4 条边仍给“缩小公差”，收紧到 `0.01` 切到同圆专用文案。
  - 双 R20 凸台（异圆心同半径）：`centre+radius+point_mm` 两次圆角均 `committed`，体积 121132.74122871833 → 120921.81921275367 mm³。
  - 回转轴四档：共面（距离 ≈0、`lies_in_plane=true`、成功）、50 mm 离面、0.00039 mm 偏移、倾斜 60°，后三档失败回执均带实测数字。
- 未验：六项离线子项（FEAT-023/BUG-076/BUG-069 文案、BUG-019/FEAT-008、FEAT-051、FEAT-039）没有实机回归；Creo 9/10 运行期；WorkBuddy 黑盒；`revolve_axis_plane_relation` 的阈值是否等于 Creo 的准入边界（可能不存在）。
