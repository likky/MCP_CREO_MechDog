# Creo 10 / MCP 0.45.2：独立曲面放样、合并与 G1 回归

日期：2026-11-26。来源：用户转交的 WorkBuddy 黑盒执行摘要；原始作业 JSON、模型二进制、受测源码提交与 dirty 状态未提供。本页不是归档原件，也不是整理时重新执行的实机验收。版本为运行时回读值，不据此推定源码或构建完全一致。

## 受测环境与试件

- Creo Parametric 10.0.0.0，`release_numeric=42`；MechDog MCP 0.45.2，单位 mm。
- 放样显式选择 `creation_route=resident_panel`。回调 `ready/live_identity_verified`，protocol 4、loader ABI 2、契约 `resident-panel-selection-v4-ticketed-mm`。
- Profile `creo10-bbl-candidate-3` 回执为 `certified`，同时有 `unverified_bindings=["payload_sha256"]`；认证记录与部署载荷的哈希不一致。本次记录只证明该会话中的实测行为，不证明部署载荷通过哈希绑定验证。
- 原件 `mmns_panel_loft_2611b`，`model_id=d5e4c0124e67456b95bc95cc4903ed75`。基线为 rev 5、两张开放 quilt、无实体，文件 SHA-256 摘要前后均为 `a079f7e7…ce3af9`（用户摘要未提供完整哈希）。

## 结果与作业引用

| 环节 | 公开工具 / 输入摘要 | 结果 | job_id |
| --- | --- | --- | --- |
| 第一段放样 | `creo_surface_loft`，三条半圆截面，两条导线，`smooth`，不传收敛点 | rev 3；quilt 80，6099.28698 mm²，保存与重载通过 | `77d9fb8c4df24062b1d0821cc225a0f5` |
| 第二段放样 | `creo_surface_loft`，复用 X=80 截面并收敛到基准点，不传导线 | rev 5；quilt 94，989.19768 mm²，保存与重载通过 | `d8f83c59fb674274b04347c6ac9a2324` |
| 独立受管副本 | Creo 手动保存副本后，`creo_adopt_file` inspect → apply；不对受管原件重做 adopt | `adopt_c228766a`，`model_id=c228766afdd24472bfc3992f6582b69a`，rev 1，源文件未变、两张开放 quilt | `e0222457e4364456848b64fea945ea9a` / `22552552ab2942e9b7b3e6063005f440` |
| 仅在副本上合并 | `creo_quilt_merge`，重新回读并定位 quilt 80 / 94 | 已提交，rev 2；feature 100，结果 quilt 80，`retrimmed_target_quilt`，面积 7088.4817 mm²，保存与重载通过 | `3b70220590aa4ca28998ac8bb2627a8f` |
| 接缝拓扑 | `creo_measure_surface_group` 复核结果 quilt 80 | 面 75 / 89；一条拓扑共享边，X=80 半圆不再是开放边；整个试件的开放边由 7 降到 5 | `4c6c9db52a0f4fbaabe051a4746e3033` |
| 接缝 G1 | `creo_measure_surface_curvature`，结果 quilt 80，面 75 / 89 | 共享边 101；17 个有效边采样；最大法向夹角 **22.4332°**，阈值 0.5°，`within_g1=false` | `a777ba0ef46b4c44a14cd38af5fe5803` |

这是一条预期的 G1 负对照：**两段放样、合并与重载通过，接缝能接上但不相切**。合并不是光顺或合并前间隙的验收。未放宽精度、未自动修补；未镜像、封口或实体化。原件保持 rev 5，无待处理作业。

### 未验收与保留观察

- 合并前 0.01 mm 间隙：`gap_max_mm=null`、`within_tolerance=null`、`no_member_seam_candidate`；原件用 1 mm 和 5 mm 搜索，副本复核，均未取得数值（作业 `2ed774f2b704404aa3b3083c5efaed0e`、`3d17070249cb438d995baab224e4b2d9`、`4f3841c7b70146a391ff3ffac404bc01`）。端点及弧长吻合不代替整边间隙测量，null 不视为零。
- 合并回执写 `consumed_quilt_ids=[94]`，巡检仍可寻址 quilt 94（含边 101）；保留两条观察。未判定它仍是独立曲面，也不定性为缺陷。
- 以上不外推到其他 Creo/MCP 版本、其他几何或路线；不关闭 [BUG-193](../work-items/BUG-193.md)。

## 后续建议（整理时未执行）

后续补录：第 1 项在原记录之后取得 [0.46.0 WorkBuddy 黑盒结果](BUG-193-CREO10-WORKBUDDY-0.46.0-2026-11-26.md)。

1. **先验 BUG-193 的 0.46.0 WorkBuddy 黑盒缺口。** 在独立测试会话取得明确的 `not_loaded`，比对 `creo_callback_status` 与 `creo_capabilities`，再分别对 `creo_loft` 和显式 `resident_panel` 的 `creo_surface_loft` 用已校验输入提交。应在建 job 前拒绝，返回结构化 callback 诊断，不生成新 job、不占用通道、模型 revision 不变；可用公开接口观测不到的项标为未证实。加载后再核对披露恢复为 ready，并在新试件上只跑一个最小成功用例。不能拿 0.45.2 的成功案例替代此项。
2. **为 G1 测量补一条正对照。** 另用通用试件保留两个相切面和一条可测共享边，与本次折角负对照配对。先验实际存在共享边，再验有效采样及最大法向夹角 ≤0.5°；如果共享边消失或采样无效，标为未测得，不以零值通过。
3. **如果流程需要合并前数值门禁，再做独立边对的只读测量。** 用已知重合、已知小于/大于阈值的边对验证几何距离与覆盖率，明确区分拓扑共享和几何距离；无候选或采样不足时保持不可判定。无需为该项重做本次试件。
