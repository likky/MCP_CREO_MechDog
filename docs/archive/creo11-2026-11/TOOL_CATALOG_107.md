# MCP_CREO_MechDog 工具目录（107 个）

> 由 `tools/list` 实时导出，2026-11-09 / 本机 Creo 11.0.0.0 / 服务版本见 `version.py`。
> 「工具数」是接口数量，不等于全部在 Creo 11 上验证过；已验证范围见 `CREO11_TEST_REPORT.md`。

| 类别 | 数量 |
| --- | ---: |
| 启动 / 会话 / 环境 | 10 |
| 新建模型 | 6 |
| 草图与实体特征 | 23 |
| 基准 | 4 |
| 曲面 | 6 |
| 钣金 | 7 |
| 装配 | 7 |
| 工程图 | 10 |
| 放样与翼型 | 1 |
| 参数 / 关系 | 4 |
| 检查 / 测量 | 7 |
| 保存 / 导出 / 导入 | 5 |
| 作业与计划 | 7 |
| 种子库 | 3 |
| 模型维护 | 2 |
| 翼型 / UDF / 底层元素树 | 5 |
| **合计** | **107** |

## 启动 / 会话 / 环境（10）

| 工具 | 说明 |
| --- | --- |
| `creo_callback_status` | Read resident Blend readiness without building, loading a DLL, launching Creo or changing models. |
| `creo_capabilities` | Describe capability boundaries, tool families, reference syntax and test evidence. |
| `creo_check_environment` | Check Creo executable, Toolkit SDK, metric template and compiler. |
| `creo_check_update` | Check public GitHub Releases, including prereleases, against the running version. |
| `creo_lookup_constants` | Look up installed SDK element IDs and feature enum constants for advanced element-tree operations. |
| `creo_migrate_registry` | Split legacy registry details into controlled sidecars (BUG-077), without Toolkit. |
| `creo_reclaim_generations` | Explicitly reclaim selected build generations of this project (DEV-027). |
| `creo_registry_health` | Report registry health without Toolkit (FEAT-047): sizes, 16 MiB budget usage, revision/status, detail forms … |
| `creo_session_status` | Check the configured/unique Creo session through Toolkit (9 second probe budget, no rebuild). |
| `creo_startup_status` | Read a background snapshot with verified_at, verification_age_seconds and stale. |

## 新建模型（6）

| 工具 | 说明 |
| --- | --- |
| `creo_new_airfoil_blade` | Create a new native Blend from varying chord/thickness/twist NACA 00xx sections. |
| `creo_new_assembly` | Create a native metric assembly with default datum planes from the locally installed template. |
| `creo_new_drawing` | Create a native DRW with an isolated snapshot of an owned part/sheetmetal model. |
| `creo_new_loft_part` | Create a NEW part with a native ordinary Blend by rebinding a saved seed. |
| `creo_new_part` | Create a new metric native part with datum planes and coordinate system. |
| `creo_new_sheetmetal` | Prepare a metric sheetmetal model. |

## 草图与实体特征（23）

| 工具 | 说明 |
| --- | --- |
| `creo_axis_pattern` | Create a native angular pattern of a feature or MCP feature group. |
| `creo_boolean_bodies` | Create a parametric multi-body Boolean feature using {kind:'body',id:...}. |
| `creo_chamfer` | Create equal-distance native chamfer sets on explicit edges or face pairs. |
| `creo_create_plate` | Create a NEW native Creo part in mm. |
| `creo_create_sketch` | Create an independent native dimensioned sketch of arbitrary supported entities. |
| `creo_dimension_pattern` | Create a native dimension pattern of a feature. |
| `creo_draft` | Create a native constant-angle, unsplit draft using selected surfaces and a neutral plane. |
| `creo_extrude` | Create native extrusion from a sketch label/ID. |
| `creo_group_features` | Create a native local feature group. |
| `creo_hole` | Create a native straight hole on a planar face using two independent planar references or coplanar straight e… |
| `creo_mirror` | Create native geometry/whole-part mirror about a planar reference. |
| `creo_project_curve` | Project one curve onto one quilt along an explicit direction. |
| `creo_regenerate` | Regenerate, verify, save and reload a native model. |
| `creo_reorder_features` | Reorder owned native features before or after an anchor; dependency conflicts fail and restore the saved chec… |
| `creo_revolve` | Create native revolve/revolved cut from an arbitrary sketch, about its centerline or an external axis. |
| `creo_rib` | Create a native profile rib from an open sketch intersecting the target solid. |
| `creo_round` | Create a native constant-radius fillet on edges or face pairs. |
| `creo_shell` | Create native constant-thickness shell, optionally removing selected faces. |
| `creo_solidify` | Create native solidify from a quilt, or trim a solid with a datum plane using mode='cut'. |
| `creo_sweep` | Create a native constant-section sweep along sketch curves or selected curve/edge references. |
| `creo_thicken` | Create a native thicken feature from a quilt. |
| `creo_transform_geometry` | Create a native rigid transform of whole solid bodies or quilts/datums/curves. |
| `creo_update_sketch_geometry` | Replace native sketch geometry in place, preserving sketch feature ID. |

## 基准（4）

| 工具 | 说明 |
| --- | --- |
| `creo_datum_axis` | Create an axis through two planes, a cylindrical face, straight edge or axis. |
| `creo_datum_csys` | Create an offset native coordinate system. |
| `creo_datum_plane` | Create an offset/angled/three-point datum plane. |
| `creo_datum_points` | Create dimensioned datum points: [{name: 'p1', position: [x,y,z]}], relative to a coordinate system. |

## 曲面（6）

| 工具 | 说明 |
| --- | --- |
| `creo_quilt_merge` | Join two quilts into one surface merge (a real JOIN feature). |
| `creo_surface_fill` | Create a native planar fill surface from a closed sketch. |
| `creo_surface_loft` | Create a native boundary-blend surface quilt from exactly two sketch sections. |
| `creo_surface_offset` | Offset a quilt along its surface normal; the result reports the measured offset distance. |
| `creo_surface_round` | Round the edge shared by two member faces of one quilt with a constant radius. |
| `creo_surface_trim` | Trim one quilt with another quilt, a datum plane or a curve. |

## 钣金（7）

| 工具 | 说明 |
| --- | --- |
| `creo_resize_sheetmetal_planar_wall` | Resize a native planar wall in place, keeping its feature identity and gauge. |
| `creo_sheetmetal_bend_back` | Refold previously unbent sheetmetal about a fixed surface. |
| `creo_sheetmetal_flange` | Attach a native bent flange to a sheetmetal edge. |
| `creo_sheetmetal_flat_pattern` | Create a native flat-pattern feature about a fixed sheetmetal surface. |
| `creo_sheetmetal_planar_wall` | Create the first sheetmetal wall as a native unattached planar wall. |
| `creo_sheetmetal_unbend` | Unbend a native sheetmetal part about a fixed surface. |
| `creo_sheetmetal_wall` | Create the first flat sheetmetal wall from an open straight-line sketch, depth and thickness. |

## 装配（7）

| 工具 | 说明 |
| --- | --- |
| `creo_assemble_component` | Insert a revision snapshot of a verified MCP part/sheetmetal model as a native assembly component. |
| `creo_component_constraints` | Replace native component placement with mate/align/offset/insert/csys constraints to assembly references. |
| `creo_component_placement` | Replace component constraints with fixed placement. |
| `creo_list_components` | Read the last verified assembly component list, native transforms and placement status. |
| `creo_plan_assembly_rebuild` | Plan an ordered insert-then-constrain rebuild from a frozen assembly snapshot (FEAT-049). |
| `creo_recolor_assembly` | Paint the components of an MCP-managed single-level assembly by part family (FEAT-052); colors are written at… |
| `creo_remove_component` | Remove a component feature from this MCP assembly, preserving its source model and native file. |

## 工程图（10）

| 工具 | 说明 |
| --- | --- |
| `creo_drawing_delete` | Delete a drawing item. |
| `creo_drawing_dimension` | Show an existing driving model dimension in a drawing view. |
| `creo_drawing_note` | Create a native multiline drawing note. |
| `creo_drawing_note_update` | Edit the text, absolute position or text height of an existing native drawing note. |
| `creo_drawing_projection` | Create a native projected view from a drawing view label/ID, on the parent's sheet. |
| `creo_drawing_sheet` | Add or resize a native drawing sheet; dimensions use mm. |
| `creo_drawing_table` | Create an editable native drawing table. |
| `creo_drawing_table_cell` | Edit one native table cell. |
| `creo_drawing_view` | Create a native model-associated general drawing view. |
| `creo_drawing_view_update` | Change view scale/style or move it by a sheet-space [dx,dy] vector in mm. |

## 放样与翼型（1）

| 工具 | 说明 |
| --- | --- |
| `creo_loft` | Append a native solid Blend using independent MCP-owned XY sketches, ordered by increasing Z. |

## 参数 / 关系（4）

| 工具 | 说明 |
| --- | --- |
| `creo_set_dimensions` | Modify native model dimensions by IDs returned in inspection. |
| `creo_set_parameters` | Create/update native part parameters. |
| `creo_set_relations` | Set native part relations using simple arithmetic assignments, e.g. |
| `creo_set_sketch_dimensions` | Modify named explicit sketch dimensions, or numeric sketch dimension IDs, and regenerate dependent features. |

## 检查 / 测量（7）

| 工具 | 说明 |
| --- | --- |
| `creo_dump_feature_tree` | Export a native feature's Toolkit element tree to XML for inspection; returns a job_id. |
| `creo_get_mass_properties` | Read the model's own mass properties (volume, mass, density, centre of mass). |
| `creo_inspect_model` | Read a saved verified snapshot, compact by default (identity/revision/status/volume/counts). |
| `creo_inspect_session_assembly` | Read-only inspection of a resident session assembly (FEAT-045). |
| `creo_inspect_udf` | Read a local Creo UDF (.gph) reference prompts and variable dimensions. |
| `creo_measure_surface_curvature` | Analyse principal curvature and G1 numerically (read-only). |
| `creo_measure_surface_group` | Measure a surface group's real boundary: open edges, seam gap and overlap. |

## 保存 / 导出 / 导入（5）

| 工具 | 说明 |
| --- | --- |
| `creo_adopt_current_model` | Explicitly adopt the current window model as a managed copy; the original is never saved, erased or renamed. |
| `creo_adopt_file` | Adopt 1?20 ordered disk paths without displaying or switching windows. |
| `creo_export_model` | Export STEP/STL/IGES/JPEG, drawing PDF/JPEG, or an explicit native assembly bundle. |
| `creo_open_file` | Retrieve an existing on-disk .prt/.asm into the connected Creo session and display it, read-only. |
| `creo_save_model` | Save a new native PRT version to the owned model directory, then reload and verify it. |

## 作业与计划（7）

| 工具 | 说明 |
| --- | --- |
| `creo_erase_session_models` | Explicitly erase selected models from the connected Creo session (FEAT-046). |
| `creo_execute_plan` | Execute an ordered general feature plan. |
| `creo_get_job` | Read modeling progress/result. |
| `creo_list_jobs` | List recent jobs, including jobs that continue after their MCP client disconnects. |
| `creo_list_models` | List owned models, compact by default. |
| `creo_list_session_models` | List models already in the connected Creo session without loading, saving, activating or adopting them. |
| `creo_plan_product_variant` | Plan the sole template box_frame offline in mm. |

## 种子库（3）

| 工具 | 说明 |
| --- | --- |
| `creo_install_seed_library` | Register a local verified library, install its original ZIP, or verify the bundled library. |
| `creo_list_seeds` | Discover bundled/registered native Blend seeds and verify their SHA256. |
| `creo_validate_seed` | Verify a seed's file hash/provenance without connecting Creo and without trial-loading it. |

## 模型维护（2）

| 工具 | 说明 |
| --- | --- |
| `creo_reconcile_model` | Inspect uncertain owned models without requiring Creo. |
| `creo_refresh_model` | Query live native model through Toolkit. |

## 翼型 / UDF / 底层元素树（5）

| 工具 | 说明 |
| --- | --- |
| `creo_create_airfoil_section` | Create a native symmetric NACA 00xx spline sketch. |
| `creo_create_feature_tree` | Advanced native feature creation from Toolkit element tree JSON. |
| `creo_create_udf` | Place a native independent UDF group, preserving editable features. |
| `creo_set_airfoil_parameters` | Update an existing airfoil's chord, thickness_ratio, twist_deg, origin or pivot_fraction. |
| `creo_set_geometry_transform` | Change a native transform's translation and rotation in place; preserves its feature ID and regenerates downs… |
