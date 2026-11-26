# BUG-193：Creo 10 / MCP 0.46.0 WorkBuddy 未加载态与恢复态

日期：2026-11-26。来源：用户转交的 WorkBuddy 两阶段黑盒摘要；未取得原始作业 JSON、完整模型哈希、匹配源码提交或 dirty 状态。整理时未重新启动 Creo 或执行建模。环境为 Creo 10.0.0.0（release 42）、MCP 0.46.0、同一会话指纹 `3902767349941073898`。对独立试件 `mmns_bug193_2611c`（`0d96d06a02dc42a4b9e3a109cfc93db3`）测试，不修改 [0.45.2 基线](CREO10-PANEL-LOFT-JOIN-0.45.2-2026-11-26.md) 的原件或副本。

| 检查 | Stop 后（06:34 UTC） | Start 后（06:51 UTC） |
| --- | --- | --- |
| 回调实测 | `not_loaded / recorded_application_not_active` | `ready / live_identity_verified`，同一 Creo 会话 |
| `loft` 家族 | `runtime_ready=false`，`requires_ready_callback` | `runtime_ready=true`，admission `ready` |
| `surface_loft` 家族 | `runtime_ready=false`，admission `not_ready` | `runtime_ready=true`；此响应未带顶层 `runtime_admission` |
| `resident_panel` 路线 | 编译态 `state=ready`，运行态 `runtime_ready=false` | `runtime_ready=true` |
| `element_tree` 路线 | `runtime_ready=false`（`known_release_extract_unsupported`） | 状态不变，未调用 |

## 拦截与恢复

- 独立试件创建作业 `5f765d82adfe47f8935aee1a5290b825`；四张草图作业 `27fc971fe8044173aee47972be0003a0` 后为 rev 2。闭合圆 `c0/c30` 用于 `creo_loft`，开放半圆 `a0/a30` 用于显式 `resident_panel` 的 `creo_surface_loft`。
- 未加载时，两条请求均返回 `BLEND_CALLBACK_SETUP_REQUIRED (before-job preflight)`，包含 `readiness`、`reason`、`next_action` 和注册文件提示；`creo_loft` 另带 `callback_free_route=creo_new_loft_part`。未返回 job ID，公开作业列表未新增；rev 2、哈希、`last_job` 不变，`pending_job=null`。事后通道空闲不能证明调用过程中从未取得锁；不从公开列表推定内部从未分配编号。
- 加载后在同一试件、同一 rev 2 原样重提 `creo_surface_loft`（`bug193_surf`，`resident_panel`，`straight`，`a0/a30` 均 `open_confirmed=true`）。作业 `cf26702a2a674f91b9defdfb4480c1a3` 成功，rev 2→3，新增 feature 70 / quilt 76，保存重载为 true。
- 重载后面积 1986.917653 mm²（与解析半锥台面积一致），1 面、4 条开放边，未生成实体。

## 同一作业的两层几何判定（只读补证）

完整作业回执 `complete=true`、`next_cursor=null`。两层几何测量一致，指向同一 quilt 76，均为重载后测量：

| 字段路径 | 实测判定 |
| --- | --- |
| `result.operations[0].geometry_check` | `verified=false`；未返回 `status`、`reasons`、`error` |
| `result.panel_receipt.geometry_check` | `verified=true`，`status=verified`，`reasons=[]` |
| 作业终态 | `succeeded`，`stage=verified`，`saved_file_reloaded_and_verified=true` |

对照 v0.46.0 tag（`333105a2`）：原生 [`panel_finalize_reloaded_geometry`](https://github.com/wudahua/MCP_CREO_MechDog/blob/v0.46.0/native/panel_run.h#L149-L199) 把操作层 `verified` 初始化为 false，采集几何后不改写该值；[Python 面板回执](https://github.com/wudahua/MCP_CREO_MechDog/blob/v0.46.0/src/creo_mechdog/panel_receipt.py#L91-L146) 根据面组、面积、feature/quilt 关联及重载证据重新生成判定。与实际回执吻合：操作层的 false 不是本次几何测量失败，也不是零导线配对导致；`curve_fit_check` 单独报告 `blocking=false`、`guides=0`、`pairs=[]`。对 resident_panel 的几何判定应读取 `result.panel_receipt.geometry_check`，原生操作层用于追溯测量数据。若通用消费者直接使用操作层标志，建议另行明确该字段语义并加离线回执用例，不必重跑此模型。

结论：两条入口未加载时的公开拦截观察通过；同一请求的 `resident_panel` 恢复与保存重载通过。未测已加载态的 `creo_loft` 建模、Creo 9 / 12.4；瞬时通道锁未测。结论不外推到其他会话或版本。
