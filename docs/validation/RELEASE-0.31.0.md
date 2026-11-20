# 0.31.0 发布记录

- 版本：`0.31.0`（MINOR，部分交付）
- 日期：2026-11-20
- 版本说明：[RELEASE_NOTES_0.31.0](../RELEASE_NOTES_0.31.0.md)
- 主台账：[BACKLOG](../BACKLOG.md) · 工作卡：[DEV-093](../work-items/DEV-093.md) · [FEAT-068](../work-items/FEAT-068.md) · [FEAT-023](../work-items/FEAT-023.md) · [BUG-076](../work-items/BUG-076.md) · [BUG-019](../work-items/BUG-019.md) · [FEAT-008](../work-items/FEAT-008.md) · [FEAT-051](../work-items/FEAT-051.md) · [FEAT-039](../work-items/FEAT-039.md) · 交付快照：[0.31.0](../releases/0.31.0.json)
- 受测提交：本记录所在开发分支的提交（标签 `v0.31.0` 的对象与提交号只在合入 `main` 后登记到 `main` 的[POSTCHECK](../development/RELEASE-POSTCHECK-2026-11-07.md) `## v0.31.0` 段）
- 与上一版本的关系：上一版本：0.30.0（`v0.30.0`，提交 `1c20f550571f15820dba6816f4efbab060197a4d`），本版在其之上接入 0.27.0 反馈批的六项离线修复与两条诊断（同圆多弧段拒绝文案、回转轴与草图平面实测关系）

## 包内容对照（相对 0.30.0）

| 项 | 0.30.0 | 0.31.0 | 说明 |
| --- | --- | --- | --- |
| 公开工具 | 109 | 109 | 不变 |
| `creo_execute_plan` | 无回执体量选项 | 可选 `response_detail="full"\|"compact"` | `compact` 只省 MCP 回执里的 `operations` |
| `creo_list_components` | 只有基础列表 | 新增 `fields`/`limit`/`cursor` 有界分页 | 32 KiB 内保持旧形状 |
| 引用结构 | 部分形态进 worker 才失败 | 派发前拒绝裸引用、`edge`+`surfaces` 混用、空槽 | 具名错误 |
| 切除体积 | 只有原始数值 | 四态分型 `material_increased`/`material_removed`/`no_material_removed`/`unmeasurable` | 不重写原生状态 |
| 焊接资格 | 只看间隙阈值 | 几何/拓扑分类，准入与提交共用 | 诊断统一前缀 |
| 圆边选择 | 同圆多弧段建议“缩小公差” | 列出弧段 id，改指 `point_mm`/`{kind:'edge',id:N}` | 判据按实测圆心与半径 |
| 回转轴回执 | 只有 `revolve_axis` | 另加 `revolve_axis_plane_relation` | 只分类，不设闸门 |
| 种子库 | 9 个种子 | 9 个种子 | `compatible_server_version=0.31.0` |
| 原生/worker/loader | 0.30.0 构建 | 本版有原生改动 | 需重新编译 |

## 验证

- 环境：Windows x64、Python 3.12.14、MSVC x64 构建工具、本机 Creo 12.4.0.0 / 匹配 Toolkit SDK。
- 离线：`python bridge.py build` exit 0；`tools/dev_check.py` 全量单测通过、`lint_findings=0`、`unformatted_files=0`（C++ 67、Python 557 个文件）。
- 实机（经用户 2026-11-20 确认后执行，未启动/重启 Creo、未清锁或保护状态、未改用户模型）：
  - `tools/test_feedback0270_same_circle.py`：圆管夹具四个圆边各为 2 段弧；只给圆心+半径时回执 `matched 2 arcs of one circle (ids 72, 90)` 并给 `point_mm`/id 指引；`point_mm` 与 `{kind:'edge',id:90}` 各自圆角成功，体积 2356.194490192345 → 2304.668647961009 mm³，保存重载通过；实心圆柱容差对照（`tolerance_mm=20` 命中 4 边仍给“缩小公差”，`0.01` 切同圆文案）。
  - `tools/test_feedback0270_task4.py`：双 R20 凸台 `centre+radius+point_mm` 两次圆角 `committed`，121132.74122871833 → 120921.81921275367 mm³；回转轴四档（共面成功、50 mm、0.00039 mm、倾斜 60°）失败回执均带实测数字。
  - `tools/test_revolve_axis_live.py`：既有三例通过，共面轴 `origin_distance_mm≈6e-21`、`axis_lies_in_plane=true`。
- 发布资料：`tools/check_release_records.py --version 0.31.0` 与 `tools/package.py` 的四附件/发布记录门禁在打包时执行。
- 证据：`docs/work-items/DEV-093.md`、`docs/work-items/FEAT-068.md` 内逐项记录，运行报告保留在忽略的 `build/feedback0270_*` 与 `build/revolve_axis/`。

## 逐 ID 状态核对

成员：本版交付 8 个 ID，均为部分交付（软件层完成；六项离线子项未做实机回归）。

| ID / 工作卡 | 技术状态 | 交付版本 | 剩余范围 | 卡首页 | 主台账 | 差异说明 | 版本说明 | 开发入口 | 实际 Release |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [DEV-093](../work-items/DEV-093.md) | 部分交付 0.31.0（六项离线子项与 `revolve_axis_plane_relation` 已实施；实机回归待执行） | 0.31.0 | 六项离线子项的实机回归；圆弧保形、Arm7 区域切除、G2 几何证据、实体边链与嵌套子装配未做 | 部分交付 0.31.0（六项离线子项与 `revolve_axis_plane_relation` 已实施；实机回归待执行） | 部分交付 0.31.0（六项离线子项与 `revolve_axis_plane_relation` 已实施；实机回归待执行） | — | 已列入 | 已列入 | v0.31.0 |
| [FEAT-068](../work-items/FEAT-068.md) | 部分交付 0.31.0（同圆多弧段文案与判据已实机验收；倒角邻面与多约束组合仍待验收） | 0.31.0 | 倒角邻面、61 条完整集与多约束组合；报告方 266 实体回转件原例未复现 | 部分交付 0.31.0（同圆多弧段文案与判据已实机验收；倒角邻面与多约束组合仍待验收） | 部分交付 0.31.0（同圆多弧段文案与判据已实机验收；倒角邻面与多约束组合仍待验收） | — | 已列入 | 已列入 | v0.31.0 |
| [FEAT-023](../work-items/FEAT-023.md) | 部分交付 0.31.0（精简回执与组件列表分页已实施；实机与真实 stdio 字节未验） | 0.31.0 | 真实 stdio 字节核对、jobs 日志与复杂请求/union 错误体量 | 部分交付 0.31.0（精简回执与组件列表分页已实施；实机与真实 stdio 字节未验） | 部分交付 0.31.0（精简回执与组件列表分页已实施；实机与真实 stdio 字节未验） | — | 已列入 | 已列入 | v0.31.0 |
| [BUG-076](../work-items/BUG-076.md) | 部分交付 0.31.0（组件列表分页已实施；真实零件全链路复核仍待） | 0.31.0 | 真实零件全链路与公开复核；阻断修复仍归 BUG-077 | 部分交付 0.31.0（组件列表分页已实施；真实零件全链路复核仍待） | 部分交付 0.31.0（组件列表分页已实施；真实零件全链路复核仍待） | — | 已列入 | 已列入 | v0.31.0 |
| [BUG-019](../work-items/BUG-019.md) | 部分交付 0.31.0（边与面引用结构预检已实施；公开终验仍缺） | 0.31.0 | 计划入口/三入口公开终验与真实请求核对 | 部分交付 0.31.0（边与面引用结构预检已实施；公开终验仍缺） | 部分交付 0.31.0（边与面引用结构预检已实施；公开终验仍缺） | — | 已列入 | 已列入 | v0.31.0 |
| [FEAT-008](../work-items/FEAT-008.md) | 部分交付 0.31.0（边与面引用槽位预检已实施；首批其余范围仍缺） | 0.31.0 | 首批其余范围与真多中心线原件 | 部分交付 0.31.0（边与面引用槽位预检已实施；首批其余范围仍缺） | 部分交付 0.31.0（边与面引用槽位预检已实施；首批其余范围仍缺） | — | 已列入 | 已列入 | v0.31.0 |
| [FEAT-051](../work-items/FEAT-051.md) | 部分交付 0.31.0（切除体积变化分型已实施；外部 -1 定因与实机矩阵仍缺） | 0.31.0 | 外部 -1 原案定因、单位实机矩阵与回执补证 | 部分交付 0.31.0（切除体积变化分型已实施；外部 -1 定因与实机矩阵仍缺） | 部分交付 0.31.0（切除体积变化分型已实施；外部 -1 定因与实机矩阵仍缺） | — | 已列入 | 已列入 | v0.31.0 |
| [FEAT-039](../work-items/FEAT-039.md) | 部分交付 0.31.0（焊接资格判据已由准入与提交共用；多截面/offset/fill/交线未排期） | 0.31.0 | 多截面/边界混合、offset 语义与真实交线诊断 | 部分交付 0.31.0（焊接资格判据已由准入与提交共用；多截面/offset/fill/交线未排期） | 部分交付 0.31.0（焊接资格判据已由准入与提交共用；多截面/offset/fill/交线未排期） | — | 已列入 | 已列入 | v0.31.0 |

## 未纳入本版

- 六项离线子项（精简回执、组件列表分页、引用结构预检、切除体积分型、焊接资格共用、模型名文案）的 Creo 实机回归。
- 圆弧保形、Arm7 区域切除、G2 几何证据、实体边链圆角、嵌套子装配（DEV-093 余项）。
- `revolve_axis_plane_relation` 的阈值是否为 Creo 的准入边界：本版只证明 `1e-6 mm`/`1e-3 deg` 能把 0.00039 mm 与 60° 分类为不在平面内，未证明存在该边界。
- WorkBuddy 黑盒；Creo 9/10 运行期；非 mm 单位。

## 发布核对

本版发布四个附件（逐个列出，不使用通配）：

- `MCP_CREO_MechDog-0.31.0-source.zip`
- `MCP_CREO_MechDog-0.31.0-source.zip.sha256`（源码包摘要记录在同名 sidecar 中，一行 `<64 位 SHA256>  文件名`）
- `MCP_CREO_MechDog-0.31.0-seed-library.zip`
- `MCP_CREO_MechDog-0.31.0-seed-library.zip.sha256`（种子包摘要同样在 sidecar 中）

- 种子包 SHA256：`fef385db303722c3279b9fc6525dc8fd06717b6d67f99d6128c587d04a2e8356`（24 个文件、9 个种子，与 `docs/seed_package.json` 一致）。
- 源码包：由本版合入 `main` 的提交源码构建；字节数与 SHA256 见同名 sidecar，不写入包内。
- Release：`https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.31.0`（发布后执行，当前未验证；发布状态与实际附件核对结果记入 `main` 的 POSTCHECK `## v0.31.0` 段）。
