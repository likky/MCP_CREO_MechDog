# 原始球鼻艏半片曲面实机验证（2026-11-16）

关联：[FEAT-065](../work-items/FEAT-065.md)、[离线准备](FRIGATE-BULB-OFFLINE-2026-11-16.md)。

后续更新：用户进一步要求创建完整球鼻艏后，已补镜像、后端封口、缝合和实体化，见[完整独立实体记录](FRIGATE-BULB-COMPLETE-2026-11-16.md)。本文 `.prt.2` 和 revision1 仍是先前开放半片的历史证据；最终完整件为 `.prt.7` / revision6。

本次已经在 Creo 12.4 中创建、保存并重载了原始球鼻艏的单张开放曲面。五条曲线沿用 TXT 控制点、节点与空间位置；上、下导线采用离线验证的精确单曲线表示。**本算例把收敛点放在最后一个截面才成功**，原先尖点在首位的三导线组合失败。只改变求解顺序，不修改源几何，也没有用无导线对照件充当最终结果。

## 授权与环境

用户本轮明确要求「可以，你试试使用 Creo 验证下」。仅操作两个独立新建测试件，没有修改原船模，没有故障注入、结束/重启 Creo 或 nmsd、清锁、清 unknown。BUG-001 历史卡死根因未定这一事实不变，本轮不作根因结论。

开发服务：`MCP_CREO_MechDog_dev`，服务版本 0.25.0，公开 runtime 的 code/data root 均为 `E:\Projects\MCP_CREO_MechDog`。Creo 12.4.0.0，`release_numeric=44`；Windows 11 / Python 3.12.14。首次启动状态是旧 timeout 快照；本次显式 `creo_session_status` 返回 connected=true / toolkit_code=0，随后准备状态为 ready，未采取进程恢复动作。

源码提交：`581977e142cd1341196349f704a1e0ee748b7f4c`，分支 `codex/dev-091-feedback-0250-plan`，dirty=true，保留其他任务现场。

- 实际 worker 自报 `identity_status=verified`。
- 受测原生 `source_digest=fd85fe3530cc02cfe40672c8239c7c3e467554ffc05c93b26c0caa671024f211`。
- worker SHA256：`30a18e88b8977765f5b2438370b08339bac3f58136d3ebac1974bd3dcca3f41b`。
- 原 TXT SHA256：`9723a7bd81e707ebca6e94c8daf5c1f3f7408c365a8da184e1421b588798c9e7`；全尺寸 `1000 mm/m`。本次没有在 Creo 里测试 1:100。

## 单变量对照与最终件

所有原生提交均通过公开 MCP 工具 `creo_execute_plan`，受理后只轮询 `creo_get_job`，不重提已受理作业。没有队列、公平调度或并发结论。

| 步骤 / job_id | 实际输入 / 结果 |
| --- | --- |
| 曲线 `31f1b1241b5b48eab4a276ca25a8afb6` | 五张单 B 样条草图+一个 datum point；成功，revision 1，保存重载 true |
| 原顺序 `c4481decd3fc4fa090308b8a0d0c312b` | `[tip,mid,rear]`+3 导线；create=0 / extract=0 / incomplete=false，但 feature_status=6 / quilt_count=0；明确失败，rollback_succeeded=true，原曲线文件 SHA 和 revision 1 均保持 |
| 无导线对照 `8dbf813e2f7f4809b043e4c29b260a2d` | 保持 `[tip,mid,rear]`，仅移除 guides；单张开放面成功，保存重载 true；仅用于定位，不是交付形状 |
| 反序对照 `e6b8c93973f74bcebacd5d9b86c0a135` | 改为 `[rear,mid,tip]`，恢复完全相同的三条导线；成功，保存重载 true |
| 干净重建 `847b2c2cdd8445dca5e2b54dab492b6c` | 新模型一次创建原五曲线/尖点+反序三导线放样；成功，revision 1，单张开放面，保存重载 true |
| 重载后边界测量 `3665068a1ae84345a57886f1474a3488` | `creo_measure_surface_group`；成功 / no_effect，revision 仍为 1；取得三条开放边的原生端点和长度 |

对照模型 ID：`354a39c114954c24b60d46ec37ce3246`（保留无导线与三导线两张对照面）。

最终干净模型 ID：`5a6ba898d04c44b49bb8b8969e39743f`，名称 `bulb_verified_03989988`，revision 1。原生文件：[bulb_verified_03989988.prt.2](../../models/5a6ba898d04c44b49bb8b8969e39743f/output/bulb_verified_03989988.prt.2)，SHA256：`2f059831fbfbc9f5fb825d956da1d70da8d953690407d1f36eade9a90204799b`。

## 实际核验

- 每条草图 `native_section.curves=1`。`section_regenerate` 和 `complete_feature` 两阶段均实际测得 control_points，样本可用且未截断，最大控制点偏差 `2.1827872842550278e-11 mm`。当前原生偏差实现会先核次数、控制点数、节点数及节点值，再测控制点；此处没有把输入回显当回读。
- 放样 feature 78：create=0、extract=0、incomplete=false、feature_status=0。实际截面几何为 `[47,55,77]`（后、中、点），三导线为 `[61,69,75]`。重载快照内该特征仍完整/活动，六个父特征匹配原输入。
- 重载后 quilt 84，仅一面 surface 79，开放；面积 `49244234.6808476 mm²`（约 49.2442 m²），与创建回执面积一致。它还不是闭合实体，没有用体积判成功。
- 三条开放边连接“后截面上端—后截面下端—艏尖”三个顶点，最大端点误差 `8.003553375601768e-11 mm`，低于预设 0.01 mm。这个检查证明端点/拓扑对应，不单独证明曲面内部处处符合原模型。
- 原生包围盒：`[64094.6161742,-0.1200048,-6603.0236631]` 至 `[78095.1709544,1818.1796033,-4596.9842813] mm`。这是 API 返回的包络，不是精确极值；不凭它声称面内严格 Y≥0，也没有把原尖点或控制点最大值当严格包围盒目标。局部越界是否为实际面点仍未独立采样确认。
- 电脑操作只将最终新试件窗口置前、选择曲面并局部放大。已经实际看到细长、横向鼓出的半片曲面，后截面开放、前端收敛；视图不是尺寸/曲率证明。原生特征的数值依据仍来自上述结果。

## 证据与重现入口

原始工具响应、请求、分页结果和报告保存在：`build/frigate_bulb_live_20261116_1794803756109/`。

- [实机汇总 report.json](../../build/frigate_bulb_live_20261116_1794803756109/report.json)。
- [二十一项记录核验 geometry_verification.json](../../build/frigate_bulb_live_20261116_1794803756109/geometry_verification.json) 及同目录 `verify_recorded_result.py`；脚本只读取本次结果，不连接 Creo。
- `curves_submit.json` / `loft_submit.json` / `control_*_submit.json` / `clean_submit.json` 保留精确请求；原生完整回执、日志与请求还在上述 job_id 的 `jobs/<id>/`。
- 同目录 `MANIFEST-SHA256.json` 为证据文件字节数和 SHA256。
- 可重现最小请求已回写 [frigate_bulb_minimal.json](../../examples/frigate_bulb_minimal.json)，builder 固定 `[rear,mid,tip]`。专项顺序回归先 RED 后 GREEN，最终 11 项通过，Ruff 检查/格式通过。原尺寸与 1:100 的离线输入已重新生成；后者只有数学检查，不是实机结论。

不改变通用 `surface_loft` 的参数契约、不自动重排其他模型截面，不把本次顺序敏感现象提升为所有 point-first 都不能工作的规则。本文未改原生实现，未提交、合并或发布。

## 未证明范围

- 当前检查没有独立比较权重，也没有在重载后逐项重读 NURBS 内部参数；模型保存重载 true 不等于这些项目分别通过。
- 未与原软件原模型逐点比对内部曲面，未作严格自交/曲率质量或工程性能验收。
- 两处封口、缝合/实体化、镜像、船体并集及整船尚未实施。下一步可在此原生半片基础上逐步验证。
- Creo 10 的 Extract=-18、跨版本模板解析问题没有因此修复；本次只证明该输入在本机 Creo 12.4 的有效创建路线。WorkBuddy 黑盒、其他版本、并发与故障注入未验证。
