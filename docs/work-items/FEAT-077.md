# FEAT-077：零件 JPEG 预览隐藏基准要素与更新检查默认预算/advisory 明确化

- 类型：功能
- 优先级：P2

分类：**已有修复但待验收**（0.39.0 已交付并完成本机 Creo 10.0.0.0 实机验收；Creo 9/12 与 WorkBuddy 黑盒未验）

- 目标版本：0.39.0（MINOR）

来源：[0.36.0 反馈原件 §六（问题 E）、§七（问题 F）](../validation/feedback-0.36.0-2026-11-23/originals/upgrade-session-and-recovery-deadlock.md)。

## 实现变更

- `native/preview.h`：`PreviewDatumDisplayGuard::hide()` 适用范围由 `PRO_ASSEMBLY` 扩展为 `PRO_ASSEMBLY || PRO_PART`（工程图仍保持 `not_applicable`），渲染前通过 `ProConfigoptionGet`/`ProConfigoptSet` 临时关闭会话级 `DATUM_DISPLAY`、`AXIS_DISPLAY`、`DATUM_POINT_DISPLAY`、`DISPLAY_COORDINATE_SYS`，析构时必恢复原值，绝不写 `config.pro`。同步更新 `tests/unit/test_t07_preview.py`。
- `src/creo_mechdog/update_check.py`：默认网络预算从 5 s 调整为 15 s（仍支持 `MECHDOG_UPDATE_TIMEOUT_SECONDS` 1–30 s），并在快照中新增 `advisory=true` 与 `affects_version_check=false`。同步更新 `tests/unit/test_update_check.py` 与 `tests/unit/test_feedback0190_update_guidance.py`。

## 验收证据（2026-11-23）

- 环境：Windows x64 / Python 3.12.10 / Creo 10.0.0.0（`release_numeric=42`），执行器 `build/creo_worker.exe` SHA256 `e1f4a3782146cb969264ded0a32185760dd2e0173dd36d3417e57c785257b321`。
- 实机 `tools/test_feedback0360_recovery_preview_edges.py --live --confirm-session-usable`（`F077_part_preview_hides_datums`，报告 SHA256 `cd0e12d248374ac68dc409784b375ed677d85fb254709b6ee548695ba1a0c083`）：构建预览（`3c7057e2…`）与 JPEG 导出（`db72f87e…`）均回报 `model_type="part"`、`applicable=true`、`attempted=true`、`hide_status="hidden"`、`restore_status="restored"`、`config_file_written=false`，四项基准选项 `get_code=0`/`hide_code=0`/`restore_code=0`、`previous_value="YES"`，JPEG 文件生成并校验通过。
- 单元测试：`test_t07_preview.py`、`test_update_check.py`、`test_feedback0190_update_guidance.py` 与 `tools/test_update_check.py --network-failure` 全部通过。
- 未验范围：Creo 9/12 实机与 WorkBuddy 黑盒。
