# FEAT-087 按重建镜像特征的一等操作

分类：**待实现**。功能，P1，目标版本未排期。

来源为 [0.43.1 反馈](../validation/feedback-0.43.1-2026-11-24/originals/datum-plane-normal-sketch-axis-flip.md) §4 与 [0.43.0 反馈](../validation/feedback-0.43.1-2026-11-24/originals/chamfer-propagate-and-surface-loft-creo10.md) §3。`MirrorOp` 仍拒绝 `feature` 引用（BUG-143 的 `PRO_FEATURE` 挂死结论保留），调用方只能自己对坐标取反重建；重建结果没有镜像节点、没有关联关系，斜置草图还要自行推导反射帧。

## 范围

- 新增一等操作 `mirror_feature_by_rebuild`：输入 `feature_id` 与 `mirror_plane`，读出原特征的草图平面与几何，在反射坐标系重建，标签注明 `Reflected copy of Feature N`。
- 反射帧规则：`O → R(O)`、`u → R(u)`、`v → −R(v)`；把 XY/XZ/YZ 的 `n/u/v` 与反射规则写进 `SketchOp.plane` 描述。
- 不改变 `MirrorOp` 对 `feature` 的拒绝，也不改其既有 workaround 文案。

## 验收

用直置与斜置两组拉伸/切除特征验证：反射副本的体积、包围盒、面组与原件一致；保存重载通过；原件修改后副本按本操作语义重建（不是参数关联，回执必须写明）。失败路径回滚且 revision 不变。
