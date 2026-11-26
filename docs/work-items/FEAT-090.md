# FEAT-090：近容差端点焊接支持异心圆弧对接并暴露到草图公开工具

类型：功能增强。优先级：P1。

分类：**已有修复但待验收**。0.46.0 交付近容差 `arc-arc` 端点焊接与草图公开工具参数暴露；Creo 10 实机 40 弧微间隙拉伸通过。关联：FEAT-039、BUG-101、BUG-159。 [发布记录](../validation/RELEASE-0.46.0.md)

## 来源与现象

2026-11-26 外部 0.45.1 / Creo 10.0.0.0 反馈 §2（[原件](../validation/feedback-0.45.1-2026-11-26/originals/draft-flip-loft-arc-weld.md)）。

`gear10.json`（40 段异心圆弧、10 个近闭合轮廓，端点簇扩散 `8.21534265e-07 mm`）直接拉伸失败（`ProFeatureWithoptionsCreate=-1`），外部预先吸附端点后拉伸成功。原因有三层：
1. `creo_create_sketch` 与 `creo_update_sketch_geometry` 未暴露 `snap_endpoints`、`endpoint_policy`、`max_endpoint_move_mm`、`closure_tolerance_mm`；
2. `endpoint_welding.py` 的 `_arc_consistent` 拒绝不同圆心的圆弧对接，`_snap_entities` 返回 `arc_pair_not_snappable`；
3. `native/endpoint_weld.h` 仅处理 `line`/`centerline`，跳过 `arc`。

## 范围与验收

1. 在 `creo_create_sketch` 和 `creo_update_sketch_geometry` 暴露可选参数 `snap_endpoints`、`endpoint_policy`、`max_endpoint_move_mm`、`closure_tolerance_mm`（默认值不变）。
2. 在显式 `snap_endpoints=True` 下支持 `arc-arc` 近容差共点：
   - 两圆存在距原两端点均 `≤ max_move` 的交点时，仅调整起止角（圆心与半径零改动）；
   - 两圆相切/微离无交点且在容差内时，取共点中点并用“非焊接端 + 原弧中点 + 新共点”三点重算圆弧，如实回报 `max_shift_mm` 与 `max_radius_delta_mm`。
3. `native/endpoint_weld.h` 扩展残差测量支持 `PRO_2D_ARC`。
4. 补充单元测试（40 弧多轮廓交点/三点重算/超限拒绝/不跨环）与本机 Creo 10 实机 `snap_endpoints=True` + `extrude` 保存重载验收。

## 实现与验证证据（2026-11-26）

- 分支：`codex/feedback-0451-draft-weld-loft-cap`（基点 `870b5142`，dirty=true，未合入 `main`、未发版）。
- 变更：`src/creo_mechdog/endpoint_welding.py`、`native/endpoint_weld.h`、`src/creo_mechdog/server.py`、`tests/unit/test_weld_eligibility.py`、`tests/unit/test_arc_endpoint_welding.py`。
- 原生构建：`.\.venv\Scripts\python.exe bridge.py build` exit 0。
- 单元测试：`tests.unit.test_arc_endpoint_welding`、`test_weld_eligibility`、`test_endpoint_welding` 全部通过（40 弧 10 轮廓 `8.215e-7 mm` 间隙全部吸附至 `< 1e-12 mm`；相交异心圆弧零半径漂移；微离无交点圆弧三点重算有界漂移）。
- 本机 Creo 10.0.0.0（release 42）实机：40 段异心圆弧（10 闭合轮廓，`8.215e-7 mm` 微间隙）开启 `snap_endpoints=True, max_endpoint_move_mm=1e-4` 创建草图并拉伸 2 mm，作业 `5ced5a2ea83a40049ebe5499299853b9` `succeeded`，`saved_file_reloaded_and_verified=True`，实测体积 `1047.002224 mm³`（解析值 `1047.002218 mm³`，相对误差 `< 1e-8`）。
- 未测范围：外部原件 `scripts/gear10.json` 同输入（报告未附原 JSON）、Creo 9 / Creo 12.4、WorkBuddy 黑盒验收。
