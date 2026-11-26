# 完整独立球鼻艏实体（2026-11-16）

用户结合原图要求「调用 Creo 就创建这个」。本轮将[既有原始半片](FRIGATE-BULB-LIVE-2026-11-16.md)补成左右完整、后端封闭的球鼻艏原生实体，没有创建整船或修改原船模。

## 交付结果

- 模型：`5a6ba898d04c44b49bb8b8969e39743f`，`bulb_verified_03989988`，最终 revision 6。
- [原生 Creo 文件](../../models/5a6ba898d04c44b49bb8b8969e39743f/output/bulb_verified_03989988.prt.7)，SHA256 `a4beea13c9d71e8ad0048073264bb8f271b92353c728217c20dc9fd11a7b5d85`。旧 `.prt.2` 是半片阶段，不能当完整实体交付。
- 一个活动且有材料的实体 body 144、三张实体面；另有一个 `no_geometry` 模板空体，不是第二个实体。
- 实测体积 `54405151075.317024 mm³`（54.4051510753 m³），体积查询 code=0，质心 `[69258.4196944475,0,-5597.197124282068] mm`。
- 原生包围盒约 `[64094.6161742,-1818.1796033,-6603.0236631]` 至 `[78095.1709544,1818.1796033,-4596.9842813] mm`，包络尺寸约长 14.001 m、宽 3.636 m、高 2.006 m，Y 上下界对称。包围盒是 API 包络，不作为精确曲面极值或工程公差。
- 所有五次写任务均 `succeeded` 且 `saved_file_reloaded_and_verified=true`；最终重载仍 `has_solid=true`、一个活动材料体、正体积。

## 原生操作与作业

保留 TXT 的原始样条和尺寸（1000 mm/m），采用先镜像曲面、再封完整后截面的等价构造，省去原半体顺序中的中心面封口：

| 操作 | job_id | 结果 |
| --- | --- | --- |
| 绕 Y=0 镜像 quilt 84，保留原件 | `543e69f2e79a46acb5e92c34657261a0` | rev2，另一半 quilt95，与原件面积/包络对称 |
| JOIN 左右半片 | `1ae0f083b2504900bb198e7e43482af9` | rev3，result_quilt_id=84，原位扩展目标，tool95 被消费 |
| 后截面闭合草图+平面封盖 | `321d75fb74aa4c618308b74e80812258` | rev4，quilt134；两条原后截面/镜像反向 B 样条构成一闭环，原生 open_ends=0、控制点偏差0 |
| JOIN 后端盖 | `b86a4d4b70964cbea14b9e61f1ef194f` | rev5，result_quilt_id=84，tool134 被消费 |
| 只读闭合检查 | `8a5d9297839f4002bf99d0d3e586e231` | state=closed、open_edges=0、7条拓扑共边、3面，rev5 不变 |
| 实体化 | `13bb734ae5dd4cd89f3e5d04859d19f0` | rev6，体积0→54405151075.317024 mm³，保存重载true |
| 独立只读体积/质心查询 | `ae89f196096b4f92ac0bdda14056ff6c` | 同体积、质心Y=0、rev6不变；只读任务的保存重载字段false不是写任务失败 |

每次都只提交一次，接受后轮询 `creo_get_job`，使用最新 revision 和真实 quilt ID，不以 JOIN 特征标签猜结果面组。原生 JOIN 返回的消费关系与 inspection 中保留的历史 quilt 记录不同，最终实体以活动材料 body 和实体面为准。

## 证据与边界

证据目录：`build/frigate_bulb_complete_20261116_1794808418960/`，包含每次请求/响应、[汇总](../../build/frigate_bulb_complete_20261116_1794808418960/report.json)、[八项交付核验](../../build/frigate_bulb_complete_20261116_1794808418960/verification.json) 和 `MANIFEST-SHA256.json`。每个作业的完整原生回执、日志及请求继续保留在 `jobs/<job_id>/`。

本机 Creo 12.4.0.0 / release_numeric44，服务 `MCP_CREO_MechDog_dev` 0.25.0，Windows / Python3.12.14。源码提交 `581977e142cd1341196349f704a1e0ee748b7f4c`、分支 `codex/dev-091-feedback-0250-plan`、dirty=true；受测 native source_digest `fd85fe3530cc02cfe40672c8239c7c3e467554ffc05c93b26c0caa671024f211`，worker SHA256 `30a18e88b8977765f5b2438370b08339bac3f58136d3ebac1974bd3dcca3f41b`。未改原生源码、未编译新执行器、未提交/合并/发布。

开始时另一客户端正占用 `session_status`，本次请求立即 busy 拒绝；只读确认通道释放后才显式检查当前连接，没有清锁、排队或重放。BUG-001 历史根因仍未定，没有故障注入、进程重启或保护清理。

有两个指标仍不可宣称通过：合并后的 `ProQuiltVolumeEval=-62`，其闭合标量保持 `null/available=false`；独立拓扑闭合和随后实体化、实体体积、保存重载成功分别构成实际证据，不改写该错误码。面重叠扫描因样本预算超限未完成，因此不声称严格无自交或与原软件曲面逐点一致。没有赋密度，质量查询不可用，但不影响几何体积结果。

Creo 窗口已显示完整实体；尝试放大时桌面输入返回非目标窗口，刷新/激活恢复又遇 `GetCursorPos failed: 拒绝访问 (0x80070005)`，已停止 UI 输入，没有继续尝试绕过。视图放大未完成，实体文件已保存且几何验证不受影响。未改变模型颜色；未接入船体，Creo10/其他版本和完整船体外观仍未验证。
