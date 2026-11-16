# 原始 SolidWorks 球鼻艏与 Creo 实体对比（2026-11-16）

用户打开原始 SolidWorks 文件，并要求查看新的三维画面。本轮已实际查看原件，将独立球鼻艏半体临时孤立、放大，查看前视（对应 TXT 纵向侧视）、俯视和等轴测，最后退出孤立，恢复全部实体并停在船艏局部视图。另用官方 SolidWorks API 只读提取实际几何，不修改或保存源几何。本轮没有连接重启后的 Creo、没有新增 Creo 建模任务。

## 结论

当前 Creo 本体确有中间截面形状差异，不能再只用船体遮挡或视角解释。既定外包络接近，不代表整个曲面一致：后部 X≈66–70 m 的上下肩在原件中更饱满，前部 X≈74–76 m 的下肩在原件中更内收。原图红色也不是完整几何的全部外观：孤立原件后仍能看到灰色上部、红色下部，原件做了曲面分割和局部着色。

证据支持差异集中于截面之间的鼓度/参数对应。相同截面和纵向导线不能据本次结果推定两软件的曲面内部逐点一致；尚未把原因唯一归给截面顺序或某个内核选项，也没有修改源控制点凑体积。

## 原件身份与坐标

- 当前内存原件：`C:\Users\Administrator\Downloads\baquebo .SLDPRT`，SolidWorks Design Premium 2026 SP0.0 / API revision `34.0.0`。
- 原件在本轮读取前即 `GetSaveFlag=true`，读取后仍为 true。因此结论针对当前打开的内存几何，不声称磁盘内容与未保存状态完全相同。直接文件 SHA256 因占用未取得；没有强行保存、关闭或释放文件。
- 8 个实际实体的原生体积总和 `5384.5749747737345 m³`，与 TXT 的参考总值约 `5384.574975 m³` 一致。
- 原件的原生坐标为 X 纵向、Y 高度、Z 横向。与 TXT/Creo 对比使用右手旋转：`[X_txt,Y_txt,Z_txt]=[X_sw,-Z_sw,Y_sw]`，再由 m 乘 1000 转成 mm。不能直接把原件 SW 的 Y、Z 与 TXT 同名轴比较。
- 独立球鼻艏半体名称 `Split Line1[1]`，4 面。两张曲面属于 `Split Line1`，另有两张 `Mirror4` 所属的平面端盖/中心盖。只读特征树确认 `Surface-Loft2`、`Surface-Plane1/2`、`Surface-Knit1`、`Mirror4`、`Fillet1`、`Combine1`、`Split Line1` 均实际存在。
- Creo 对照仍是原先完整独立实体 `5a6ba898d04c44b49bb8b8969e39743f` / revision 6，`.prt.7`，使用已保存的原生导出作业 `37a35d07991647ada1db2170cc61316d`。文件身份及创建时环境见[实体交付记录](FRIGATE-BULB-COMPLETE-2026-11-16.md)，没有用当前 main 的源码版本替代旧模型的创建身份。

## 原生体积与面积

| 指标 | SolidWorks 原件半体 | Creo 对应半边 | Creo 相对原件 |
| --- | --- | --- | --- |
| 体积（m³） | 27.553218732882677 | 27.202575537658512 | −1.272603% |
| 外侧曲面面积（m²，不含中心盖及后盖） | 49.53541788021092 | 49.2442346808476 | 约 −0.588% |

Creo 半体体积使用已验证的对称完整实体体积 `54.405151075317024 m³` 除二，不拿全部 Creo 体积与一个 SW 半体直接比较。SW 通过 `IBody2.GetMassProperties(1.0)` 的 Volume 字段读取；参数 1.0 仅用于计算密度，不设置材料或覆盖体积。外侧面积分别取 SW 两张非平面面和 Creo 单张原半片的原生面积。

## 截面差异与原生参照复核

SW 原件半体共 2616 个显示三角片，其中曲面为 2448 片；Creo STL 共 197118 片。两者先转换到相同坐标、单位和负 Y 半边，再作线性截面相交。各 X 截面的最外半宽差约 0.2–2.4 mm，上下极值差约不超过 2.9 mm；这些小量可能包含显示网格误差。内部肩部差异则明显更大：

| X（m） | 高度 Z（m） | SW 半宽约（mm） | Creo 半宽约（mm） | SW 比 Creo 更外鼓（mm） |
| --- | --- | --- | --- | --- |
| 66 | −6.4 | 1184.536 | 1082.411 | +102.125 |
| 68 | −6.4 | 1077.716 | 957.580 | +120.137 |
| 68 | −4.8 | 1121.048 | 1027.547 | +93.501 |
| 74 | −6.2 | 626.916 | 724.462 | −97.546 |
| 76 | −6.0 | 422.062 | 510.575 | −88.513 |

这些是固定 X、Z 的横向差，基于显示网格，不能直接当作法向公差或精确改形量。

为排查源显示网格是否造成误判，又把表中五个 Creo 网格截面采样点传给 SW 原生 `IFace2.GetClosestPointOn`，在原件两张曲面中求最近点；实测距离依次为 **36.458、39.642、33.194、60.085、61.305 mm**。这一复核直接使用原件 CAD 面，支持厘米级形状差异存在；Creo 侧输入仍来自显示网格，故不宣称是精确双 CAD 的最大距离、Hausdorff 距离或全曲面公差验收。

原件曲面 0 面积约 7.8271 m²，无显式面级着色，三维中显示为灰色；曲面 3 面积约 41.7083 m²，`HasMaterialPropertyValues=true`，RGB `[1,0,0]`。这与孤立视图中的灰/红分区一致，不能只按原图红区重建全部曲面。

## 建议推进

保留原始尺寸、既有截面和三条导线，从原件补取 X≈66、68、70、74、76 m 等位置的横截面，先控制中间上下肩的饱满程度，再重新构造一个独立 Creo 对照件。先检查半体外形及原生测量，再镜像/封口/实体化；随后按原坐标与船体共同显示，对照船底接合、分割和着色。不能用整体缩放、质量属性覆盖或随意加鼻尖圆角代替曲面鼓度修正。

本轮仅完成查看和诊断，未生成新的 Creo 修正版。精确补充截面、重建和再次保存重载仍未实施；Creo 崩溃原因也未定位，不据画面采集故障推断其原因。

## 可追溯证据

全部本地诊断产物位于 `build/frigate_bulb_sw_compare_20261116/`：

- `probe_sw_identity.ps1`、`probe_sw_bodies.ps1` / `solidworks-bodies.json`：强类型只读身份和八体体积。
- `probe_sw_bulb_mesh.ps1` / `solidworks-bulb-mesh.json` / `solidworks-bulb-unified-mm.csv`：原件半体实际显示网格，坐标已旋转并转为 mm。
- `read_sw_features.ps1` / `solidworks-features.json`：原始特征树，读取错误数组为空。
- `compare_sections.py` / `section_comparison.json`：两份实际网格的同坐标截面比较。
- `creo-sample-points.csv`、`probe_sw_surface_checks.ps1` / `native-source-surface-checks.json`：五个采样点对原生 SW 曲面的最近点复核和着色/平面分类。

PowerShell 探针由 Windows PowerShell 5.1 执行，只通过 `Marshal.GetActiveObject` 取得已运行的 SolidWorks；所有 COM 几何调用留在单个强类型 C# 方法内。早期 PS 晚绑定失败返回的 null 不作为无文档或无几何的结论；不稳定的混合脚本已移除。UI 先遇 GPU/画面采集错误，用户恢复新画面后重新选窗，随后已实际查看并恢复全部实体显示。未更改系统权限，未启动、结束或重启 CAD 进程，未清 Creo 的锁或 unknown 保护。

官方 API 依据：[GetBodies2](https://help.solidworks.com/2026/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IPartDoc~GetBodies2.html)、[GetMassProperties](https://help.solidworks.com/2026/English/api/sldworksapi/SOLIDWORKS.Interop.sldworks~SOLIDWORKS.Interop.sldworks.IBody2~GetMassProperties.html)、[GetTessTriangles 及显示精度限制](https://help.solidworks.com/2026/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IFace2~GetTessTriangles.html)、[GetClosestPointOn](https://help.solidworks.com/2025/english/api/sldworksapi/SOLIDWORKS.Interop.sldworks~SOLIDWORKS.Interop.sldworks.IFace2~GetClosestPointOn.html)。
