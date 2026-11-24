# FEAT-080：`ShellOp` 按实体 `body_id` 限定抽壳、`MirrorOp` 可执行替代指引与 `creo_inspect_model` 分页 `total_count`

- 类型：功能
- 优先级：P2

分类：**已有修复但待验收**（0.42.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验）

- 目标版本：0.42.0（MINOR）

来源：[0.40.0 原始反馈（护卫舰 chamfer 切向链延伸与 round 失败无诊断）](../validation/feedback-0.40.0-2026-11-24/originals/frigate-chamfer-tangent-chain-and-round-diagnostics.md) §3、§4、§6 P6、§8 问题 3。

## 修复内容

1. **`ShellOp` 按实体限定抽壳**：`src/creo_mechdog/schema.py` 与 `server.py`（`creo_shell`）新增可选 `body_id: int | None`（允许负数初始实体 ID 如 `-5778` 及正数新建实体 ID）；`native/generic.cpp` 的 `generic_shell` 经 `require_scopable_body` 校验后按精确实体 ID 写入 `PRO_E_BODY_SELECT` 并在回执中返回 `body_id`。
2. **`MirrorOp` 报错替代指引**：保留 `BUG-143` 对 `kind="feature"` 的提交前拒绝，报错补充整件 `kind:'part'`、曲面组 `kind:'quilt'` 与跨镜像面重建草图/独立实体合并三条可执行替代路径。
3. **`creo_inspect_model` 分页总数**：`src/creo_mechdog/model_queries.py` 在分页响应顶层新增 `total_count` 与 `page_count`（保留 `returned_count` 向后兼容），同步更新 `src/creo_mechdog/query_client.py`。

## 验收证据（2026-11-24）

- 实机 `tools/test_feedback0400_live.py`（报告 `build/feedback0400_live_report.json`，Creo 10.0.0.0 / release 42）：
  - `S3` 两实体零件仅对 `body_b_id=90` 抽壳 2 mm（作业 `f3b5f71a2a814bba9f0269554cbfb358`），实测体积 `78751.99999999999 mm³` vs 解析值 `78752.0 mm³`（另一实体 `64000.0 mm³` 零改动），保存重载通过；分页查询返回 `total_count=24`、`page_count=5`。
- 单元测试：`tests/unit/test_feedback0400_fixes.py::Feat080ShellMirrorInspectTests` 全部通过。
- 未验范围：Creo 9/12 与 WorkBuddy 黑盒。
