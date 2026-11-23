# 保存、恢复、样条和放样反馈验收

2026-11-23 汇总。受测环境为 Windows x64、Creo Parametric 10.0.0.0、Toolkit release 42 及匹配 SDK。开发分支从 `b54bff681d955edc2efe2ddf39685082f355d4b8` 开出，受测工作树有此批改动。使用新建夹具和受管输出。反馈原件的 SHA256 为 `b25371f3e94bc19a968f15313f900ef9c2d211b0ae0fe0e090376f9ff591324e`。见[原件](feedback-0.35.5-2026-11-22/originals/save-and-loft.md)。

两截面种子和完整恢复矩阵的原生源码指纹为 `0bce25096765374bd1ec5a15a8c51512ba8eae85972e9f255f38545883a5c380`，worker SHA256 为 `cc9dd153a7e7a6affedfe6ee24b3cfea11d945f5b91aff9a0b271e477e883382`。追加 JPEG 回执修正后的原生源码指纹为 `87e727d77a5de0c72413fd99cd24554a378c247ef064b99eae2f2c853b4bab77`，worker SHA256 为 `a2e02b5b2fd88550b700f972601505f3bfa7f05b5aeb65b228b3bbba893bb6e7`，由 `bridge.py build` 生成。

## 保存与恢复

- 修复前 `build/bug152-baseline.jsonl` 中的一组新建、拉伸、圆孔及独立保存都成功，依次生成 `.prt.2` 到 `.prt.5`。在该夹具上未观察到第三次保存失败。原现场 `ProMdlnameBackup=-1` 的触发条件仍缺原始会话证据。
- 修复后 `build/bug152-fixed.jsonl` 同类零件经历四次成功保存，revision 1 到 4。既有零件的三个作业原生日志均为 `ProMdlSave=0`，例如圆孔作业 `d0cd1ba07efd4e4184da3646c545e4c7`。范围外圆孔作业 `737cd2b82f594a5f8ff0fe4e38deaaf5` 回滚成功。
- `tools/test_model_reconciliation.py` 在全新受管夹具中以 12 秒子进程超时制造会话差异，并以隐藏结果文件模拟交付不确认。恢复基线作业 `81fef069f092432c860808a7c23968e0` 从已分岔的会话恢复至 24,000 mm³，原文件 SHA256 与 revision 1 保持，后续参数更新到 revision 2。接纳已保存版本 `48001f08d9bb43f4966386ef9d4c4b4a` 和接纳会话版本 `39303084324c4958a3a1e5c68db21ba6` 均保存重载并可继续编辑。放弃未保存新件 `ad01ab2c2a614fc59bee3785a3ae0e8e` 成功。
- `python build/bug152-accept-live-existing.py` 用最终执行器接纳已有检查点的会话零件。作业 `a86dc0cf89ec40648b4394d4fbe2406a` 原生日志为 `ProMdlSave=0`，保存重载通过，revision 3 到 4，模型为 `ready`，旧文件 SHA256 保持。
- PTC 的 `ProMdlErase` 说明指出，活动对象的数据可能保留到 Creo 取得执行控制。对受管检查点，本批在读取前确认同名对象已消失，读取后用 `ProMdlOriginGet` 及文件同一性核对所选版本。以 `ProMdlDirectoryPathGet` 获取写入目标，确认目标目录与模型无依赖时对已登记零件执行 `ProMdlSave`。见 [PTC 文件管理说明](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r13/usascii/creo_toolkit/user_guide/File_Management_Operations.html)。

## 样条切除

测试为新建长方体与从 XZ 面对称切入的封闭轮廓。精确样条作业 `517c41a6ef15493d80c72391bf5bfe20` 的原生草图有 1 个闭合轮廓、0 个开放端点，最大控制点偏差约 7.42e-12 mm。原生去料为零，回滚成功。按 SDK 约定改为 `ProArray` 后，作业 `c9f38fb0a6584e9baed9cdd903ff5140` 仍复现该零去料。

作业 `810863334602456683f63f0a73e6568a` 通过 `approximation_segments=21` 去料 215,464,586,469.734 mm³，revision 1 到 2，保存重载通过。手工折线作业 `be6f604752bf40bb8bb2ccabb9a01df8` 的实测体积相同。独立预期用三次 Bézier 公式取 22 个点，按多边形面积乘长方体宽度 13,800 mm。

最终执行器复测中，精确切除 `65994a314be54bc0861ba1aa2a4b718c` 回执包含原生 `b_spline_entities=1`、`closed_contours=1` 与 `open_ends=0`，去料为零并回滚。21 段近似 `9bbde8e16ddf443c80681b46cdc985df` 与手工折线 `c8ae68e09c47499c8abe3539f67a6253` 再次得到上述体积并通过保存重载。命令分别为 `python build/bug153_probe.py` 和 `python build/bug153_approx.py`。

## 放样

`tools/test_loft_seed.py --seed-file seed_library/seeds/two_straight/mechdog_loft_reference.prt.5 --feature-id 60` 通过。两截面矩形、圆和三角形作业分别为 `a5e40949a2a14bc3bdf4893b8aa9ca90`、`ee34ca5796e84ad2a81315742a1ffcf7`、`770d05df2fb342d887b3dbf6b53ac10c`。解析体积为 7000、1750π 和 3500 mm³，重载实测分别为 7000、5497.787143782138 和 3500 mm³，各作业均 `saved_file_reloaded_and_verified=true`。读取的父特征 ID 覆盖请求的两个截面。矩形件追加改尺寸、故意不满足的体积断言与切孔，重载后为 7840 和 7745.752220392307 mm³，错误断言导致的改型回滚通过。原种子 SHA256 校验一致。

Creo 10 上原 `tools/test_b_spline.py --live --confirm-session-usable` 的精确草图控制点回读通过，曲面放样阶段因元素树提取返回 -18 未通过。最终执行器用两个独立线截面复测，作业 `5e42cae7bd9440c4988f73868274447d` 创建返回 0、提取返回 -18，模型回滚成功。随后 `creo_capabilities` 披露 `refused_before_job`、原始码及这次作业 ID，下一次同路线提交在创建作业前拒绝，revision 仍为 1。证据见本机 `build/bug154-loft-admission-verified.jsonl`。

## 同计划引用

拔模测试用 40×20×15 mm 长方体，在同一计划内以 `feature:"base"` 和几何锚点选中侧面与中性面。对照作业 `358b898fe5514dc793cf02fcf95c70ac` 和 `4f954dc44ec6477a9c892bca30e096be` 的中性面由 53 变为 59，重载体积均为 12196.849492933328 mm³，等于长方体 12,000 mm³ 加上 5° 拔模产生的楔形体积。两例均保存重载通过。

删除拔模作业 `95fb187d86504a9cab5b611de26775c4` 重载体积恢复至 12,000 mm³。追加拔模作业 `6698d39d71584c63a08cf0da5720f923` 再次达到楔形预期，revision 1 到 3，两个版本均保存重载通过，原检查点 SHA256 保持。

## JPEG 导出

`python build/feat074_jpeg_probe.py` 读取实际 JPEG 文件头并核对原生视图。正视 `d38cba98bfd64dd48534b2d71c038608` 为 1400×800，俯视 `a848104272cc4326997eaece15dd7a50` 为 1600×900，等轴测 `980cd0e7598f4e958072dfc59fb58ee3` 为 1200×1000。三个作业的 `view_matrix_matches=true`，compact 回执指向指定的文件。模型 revision 3 和检查点 SHA256 保持。

## 尚未复验的范围

原始工程模型、历史失败现场和七截面种子未随报告提供。Creo 9、12、WorkBuddy 黑盒、装配预览及特征面角色批量选择不在本轮实测范围。Creo 10 曲面元素树的提取限制见 [BUG-135](../work-items/BUG-135.md)，直接 Blend 的环境就绪由 `creo_callback_status` 查询。

## 全量开发检查

`python tools/dev_check.py --work-item BUG-152` 通过。Windows Python 3.12.10 单测运行 4397 项，其中 7 项跳过，0 失败、0 错误。Ruff 与 clang-format 均通过。单测源码指纹为 `44c98bf259505869d5a4aa870dfa4a419ffdcd6fb1e28facd76309fd3a32f07f`。本机报告位于 `build/development_check.json` 和 `build/unit_test_report.json`。
