# 原始球鼻艏离线准备（2026-11-16）

关联：[FEAT-065](../work-items/FEAT-065.md)、[FEAT-066](../work-items/FEAT-066.md)。

后续更新：用户另行授权后，已在 Creo 12.4 生成并保存重载原始球鼻艏的开放半片，见[实机验证](FRIGATE-BULB-LIVE-2026-11-16.md)。当前 builder/最小 JSON 已使用实机成功的 `[rear,mid,tip]` 截面顺序；原始数据快照未改。下文离线通过与未测陈述仍指离线阶段，不能替代该实机记录。

这次解决的是原始数据整理及两条复合导线的输入适配。离线数学和公共 schema 检查通过；没有创建 Creo 曲面，也没有证明 Creo 10 的 Toolkit 路线已修复。用户本轮只授权离线，实机另行确认。

## 输入与交付

原始输入是用户给出的《简易护卫舰_跨软件三维建模自然语言说明.txt》A18—A23，不需要先打开原始 CAD 文件。原 TXT SHA256：`9723a7bd81e707ebca6e94c8daf5c1f3f7408c365a8da184e1421b588798c9e7`。

| 文件 | 用途 |
| --- | --- |
| [frigate_bulb_source.json](../../examples/frigate_bulb_source.json) | 原米制数据、六段 TXT 摘录与来源摘要；保留原控制点、节点、权重和被排除的辅助线 |
| [frigate_bulb_minimal.json](../../examples/frigate_bulb_minimal.json) | 公共 `creo_execute_plan` 的完整待用 payload；五张单曲线草图、一个尖点和一次开放曲面放样 |
| [prepare_frigate_bulb.py](../../tools/prepare_frigate_bulb.py) | 可重跑的纯离线入口，没有 live 模式，不提交任务 |
| `build/frigate_bulb_offline/report.json` | 本次数学诊断、来源核对、执行源码摘要、Git 提交/dirty 和未测范围 |
| `build/frigate_bulb_offline/curves_plan.json` | 后续先创建五条曲线和一个尖点的独立请求 |
| `build/frigate_bulb_offline/loft_operations.json` | 后续追加放样的操作片段；须使用前一步实际 model_id、最新 expected_revision，不能当作新件请求单独提交 |
| `build/frigate_bulb_offline/MANIFEST-SHA256.json` | 本批生成文件的字节数和 SHA256；生成物不进入源码包 |

## 几何适配及核验依据

原文正文将半体写在负 Y，附录 A20/A22/A23 控制点实际在正 Y。本批以附录正 Y 半体为准，后续再镜像。默认 `1000 mm/m`，即原尺寸米→毫米，不自动缩比。`10 mm/m` 才是 1:100；长度全部同比变换，角度及节点不缩放。

Sketch64/65 的直线和 Bézier 相接点按原记录完全相同。将后端 R→接点 M 的直线升为三次，控制点为 `R, R+(M-R)/3, R+2(M-R)/3, M`；再接上倒序的原 Bézier，共七个控制点。节点为 `[0,0,0,0,1,1,1,2,2,2,2]`，权重全一。中间三重节点保留原连接形状，不进行平滑拟合或吸附修正。计划再精确反向，使三导线都从尖点指向后截面；后续实机确认只将截面顺序反转为后→中→尖点才成功，导线方向保持不变。

Sketch67 只取其纵向样条；X=72.094736179 的横向辅助直线仍在来源快照中，但不进入导线草图。两个截面直接保留原 B 样条数据。坐标映射核对现有实现：YZ 局部 `[Y,Z]`、XZ 局部 `[X,Z]`、XY 局部 `[X,Y]`；offset 分别是全局 X、Y、Z 坐标。

本次全尺寸结果：

| 检查 | 独立依据 / 预设标准 | 实际结果 |
| --- | --- | --- |
| 拼接等价 | 直线插值和原三次 Bernstein 多项式，与合并后的 de Boor 求值对照；每段 1001 点及内部节点两侧；≤1e-7 mm | 最大误差 `2.8477166477147973e-11 mm` |
| 草图坐标还原 | 全部控制点按平面映射还原全局坐标，≤1e-7 mm | `0.0 mm` |
| 三导线×三截面/尖点 | 对实际曲线求交；预设原尺寸诊断阈值 0.01 mm（不是 Creo 内核精度设置） | 九组最大残差 `6.386935583079491e-8 mm` |
| 中截面/侧导线交点 | 独立实现另算：侧导线参数约 0.595088180787544，中截面参数约 0.498476283483533 | 与以上残差量级一致，属于 TXT 数字舍入；未修正源点 |
| 后截面中心高度横向值 | 原样条在参数 0.5 求值，Y≈1.8 m、Z≈−5.6 m | Y≈1800 mm；控制点峰值 1813.25 mm，不能替代实际曲线值 |
| 下导线艏部极值 | 原三次 Bézier 的 X 导数求根，比较端点及区间内实根 | 最大 X≈78095.05974013 mm，比尖点向前 `0.32356113 mm` |
| 公共操作输入 | 当前 `validate_operations` | 五张单曲线草图、单点、3 截面+3 导线 smooth 被接受；不等于 CAD 创建成功 |

后续不要把尖点当作严格最大 X，也不要把控制点包络当作曲面包围盒。相同边界曲线在不同软件放样得到的内部曲面可能有差别；TXT 尚未提供足以唯一确定原软件内部曲面的全部条件。

## 重跑

在仓库根目录使用现有 editable 安装环境：

```powershell
.\.venv\Scripts\python.exe tools\prepare_frigate_bulb.py --source 'C:\Users\Administrator\Downloads\简易护卫舰_跨软件三维建模自然语言说明.txt'
.\.venv\Scripts\python.exe tools\prepare_frigate_bulb.py --mm-per-m 10 --output-dir build\frigate_bulb_offline\scale_1_100
.\.venv\Scripts\python.exe -m unittest tests.unit.test_frigate_bulb -v
.\.venv\Scripts\python.exe tools\dev_check.py --work-item FEAT-065
```

不带 `--source` 时使用已冻结数据，并明确记录本次未读取原 TXT；仍从冻结的 TXT 摘录重新提取，再与 JSON 几何逐项比对，避免自比误报。提供原 TXT 时重新提取，要求全文 SHA256 与冻结来源一致、几何与冻结数据一致，同时分别报告整文件摘要及摘录摘要；任一不一致或校核失败返回非零。工具不会更新版本化样例来掩盖差异。

## 后续实机范围

取得当次授权后，先在新的独立测试零件中创建曲线，检查每条导线只有一个原生曲线实体，并回读次数、节点、权重、控制点和尖点位置。特别检查三重内节点是否被 Creo 保留、草图求解是否改变曲线。随后按最新 model_id/revision 追加放样；任务已受理后只轮询，不因 busy 或失败重复提交。

放样应产生有效开放面组；须实测边界、形状、面积、特征完整性和保存重载。未知面积/包围盒不预填假值。两处平面封口、缝合/实体化、镜像和与整船接入属于后续阶段，尚未生成或验收其原生结果。Creo 10 `extract=-18` 和跨版本模板加载问题均未在本批修复。

## 本次验证身份与边界

起点提交 `581977e142cd1341196349f704a1e0ee748b7f4c`，分支 `codex/dev-091-feedback-0250-plan`，`dirty=true`；保留 DEV-091 等已有未提交现场，未提交/合并/发布。本次 Windows 11 / Python 3.12.14。工具、用例、冻结数据和计划的字节 SHA256 记录在运行报告中，未生成或声明受测 worker。

- 原 TXT 重提取与冻结数据一致，默认全尺寸及显式 1:100 的离线报告均 `passed=true`、`creo_tested=false`。
- 专项 unittest 最终十一项通过，Ruff 检查/格式通过。独立审阅发现冻结数据来源校验原先有自比缺口，新增两条回归先失败后通过：细微修改 JSON 坐标仍在几何连接容差内也必须拒绝；仅给摘录冒充原文，几何相同但全文 SHA 不同也必须拒绝。审阅者已复核修复闭环，最终报告与摘要清单已重建。
- 全量 `dev_check --work-item FEAT-065` 实际运行 3711 项，1 项失败：`test_circular_edge_needs_centre_and_radius_together` 在圆边选择器同时提供 `center_mm/radius_mm/point_mm` 时预期拒绝，但当前验证器接受。已单独复现；对应实现与测试在本轮开始前就是 dirty，均未由本批修改，不把该失败归为球鼻艏通过。证据：`build/frigate_bulb_development_full.json`、`build/frigate_bulb_dev_check.log`、`build/frigate_bulb_unrelated_selector.log`。
- 全量运行期间完成的来源校验审阅增量，由最终专项 11 项另行验证；随后最终 `dev_check --skip-unit --work-item FEAT-065` 通过（`build/frigate_bulb_development_style.json`），保留完整失败报告，没有用语言检查覆盖或宣称全量单测通过。
- 最终报告包含 `source_reextracted_from_excerpt=true` 对应检查，原 TXT 全文摘要、冻结数据重提取、几何比对全部通过；原尺寸与 1:100 的五份生成文件各自 SHA256/字节数核对通过，版本化待用计划与 builder 输出完全一致。独立数学审查与代码修复复核无剩余阻断。
- 没有连接/启动 Creo、没有执行器编译、没有真实建模/回读/保存重载、没有 WorkBuddy 黑盒。
