"""BUG-120/D3: the panel protocol generation must not drift from its consumers.

The panel route speaks protocol 4 over loader ABI 2. The already released
boundary-blend callback speaks protocol 3 over ABI 1, and that generation must keep
working untouched: 0.27.0 deployments declare 3/1 and are still served by the same
loader. These assertions pin the two generations apart in the source, catch a
silent bump of either one, and check that the ABI2 table is append-only over the
ABI1 table. The behavioural rules of the state machine are proven by
``tools/test_panel_selection_state.py``; this file only guards the contract wiring.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PANEL_PROTOCOL = ROOT / "native/panel_protocol.h"
CALLBACK_IDENTITY = ROOT / "native/callback_identity.h"
CALLBACK_API = ROOT / "native/callback_api.h"
LOADER = ROOT / "native/blend_loader.cpp"

ABI1_FIELDS = (
    "array_size",
    "array_alloc",
    "arguments_free",
    "wstring_set",
    "current_model",
    "model_name",
    "model_item",
    "selection_alloc",
    "selection_record",
    "selection_free",
    "command_add",
)
ABI2_ADDITIONS = (
    "macro_load",
    "command_id_find",
    "bracket_func_add",
    "feature_geomitem_visit",
    "curve_init",
    "curve_type_get",
    "curve_length_eval",
)


class ProtocolGenerations(unittest.TestCase):
    def test_the_panel_generation_is_protocol_4_over_abi_2(self):
        text = PANEL_PROTOCOL.read_text(encoding="utf-8")
        self.assertRegex(text, r"constexpr int protocol = 4;")
        self.assertRegex(text, r"constexpr int loader_abi = 2;")
        self.assertIn("resident-panel-selection-v4-ticketed-mm", text)

    def test_the_released_blend_generation_is_untouched(self):
        # 0.27.0 payloads declare 3/1; changing either number would orphan them.
        text = CALLBACK_IDENTITY.read_text(encoding="utf-8")
        self.assertRegex(text, r"constexpr int protocol = 3;")
        self.assertRegex(text, r"constexpr int loader_abi = 1;")
        self.assertIn("blend-selection-v3-ordered-curves-mm", text)

    def test_a_mixed_deployment_is_refused_not_downgraded(self):
        text = PANEL_PROTOCOL.read_text(encoding="utf-8")
        for name in ("ProtocolMismatch", "AbiMismatch", "DeploymentMismatch"):
            self.assertIn(name, text)
        self.assertIn("contract_state(int deployment_protocol", text)

    def test_the_loader_keeps_both_paths_and_refuses_the_mix(self):
        text = LOADER.read_text(encoding="utf-8")
        self.assertIn("&host_api2", text)
        self.assertIn("&host_api)", text)
        self.assertIn("mechdog_panel::contract_state", text)
        self.assertIn("Panel deployment protocol mismatch", text)
        # The single-shot rule stays: a loader is not retried inside one session.
        self.assertIn("if (attempted)", text)
        self.assertIn("No FreeLibrary", text)

    def test_the_ticket_capacity_is_the_documented_bound(self):
        text = PANEL_PROTOCOL.read_text(encoding="utf-8")
        self.assertRegex(text, r"constexpr int ticket_capacity = 512;")


class Abi2Table(unittest.TestCase):
    def _struct_fields(self, name: str) -> list[str]:
        text = CALLBACK_API.read_text(encoding="utf-8")
        start = text.index(f"struct {name} {{")
        end = text.index("};", start)
        body = text[start:end]
        return [field for _, field in re.findall(r"decltype\(&(\w+)\)\s+(\w+);", body)]

    def test_abi2_starts_with_the_abi1_prefix_in_order(self):
        abi1 = self._struct_fields("MechDogCallbackApi")
        abi2 = self._struct_fields("MechDogCallbackApi2")
        self.assertEqual(tuple(abi1), ABI1_FIELDS)
        self.assertEqual(tuple(abi2[: len(abi1)]), tuple(abi1))

    def test_abi2_appends_exactly_the_panel_members(self):
        abi1 = self._struct_fields("MechDogCallbackApi")
        abi2 = self._struct_fields("MechDogCallbackApi2")
        self.assertEqual(tuple(abi2[len(abi1) :]), ABI2_ADDITIONS)

    def test_the_loader_fills_the_abi2_table_with_sdk_symbols(self):
        text = LOADER.read_text(encoding="utf-8")
        for symbol in (
            "&ProMacroLoad",
            "&ProCmdCmdIdFind",
            "&ProCmdBracketFuncAdd",
            "&ProFeatureGeomitemVisit",
            "&ProCurveInit",
            "&ProCurveTypeGet",
            "&ProCurveLengthEval",
        ):
            self.assertIn(symbol, text)


class PanelPayloadWiring(unittest.TestCase):
    """The panel generation must be wired, not merely declared.

    These assertions read the payload source because the collector only runs inside
    Creo: without them a refactor could delete the dispatch and every offline rule
    would still pass while the dialog never consumed a ticket.
    """

    PAYLOAD = ROOT / "native/blend_sync.cpp"

    def test_the_loader_requires_the_panel_entry_points(self):
        protocol = PANEL_PROTOCOL.read_text(encoding="utf-8")
        for name in (
            "MechDogPanelInitialize",
            "MechDogPanelPrepare",
            "MechDogPanelFinalize",
            "MechDogPanelEvent",
            "MechDogPanelState",
            "MechDogPanelRelease",
        ):
            self.assertIn(name, protocol)
        loader = LOADER.read_text(encoding="utf-8")
        self.assertIn('GetProcAddress(payload, "MechDogPanelInitialize")', loader)
        self.assertIn("mechdog_panel::panel_exports", loader)
        # The worker reaches the payload through the loader's own exports, so the
        # panel generation needs forwarding exports, not just internal lookups.
        for name in (
            "MechDogPanelPrepare",
            "MechDogPanelFinalize",
            "MechDogPanelEvent",
            "MechDogPanelState",
            "MechDogPanelRelease",
        ):
            self.assertIn(f"PRO_TK_DLL_EXPORT ProError {name}(", loader)

    def test_the_payload_exports_the_panel_generation(self):
        text = self.PAYLOAD.read_text(encoding="utf-8")
        self.assertIn("__declspec(dllexport) int MechDogPanelInitialize(", text)
        for symbol in (
            "MechDogPanelPrepare",
            "MechDogPanelFinalize",
            "MechDogPanelEvent",
            "MechDogPanelState",
            "MechDogPanelRelease",
        ):
            self.assertIn(f"PRO_TK_DLL_EXPORT ProError {symbol}(", text)

    def test_the_selection_callback_dispatches_to_the_panel_collector(self):
        text = self.PAYLOAD.read_text(encoding="utf-8")
        self.assertIn("if (panel_run)", text)
        self.assertIn("return select_panel_section();", text)
        self.assertIn("PRO_SELECT_OVERRIDE : PRO_SELECT_TOGGLE", text)
        # A spent ticket must not be reused: the collector checks exhaustion first.
        self.assertIn("PANEL_SELECTION_EXHAUSTED", text)
        self.assertIn("panel_state.abandon(", text)

    def test_the_done_call_site_verifies_the_command_before_loading_a_macro(self):
        text = self.PAYLOAD.read_text(encoding="utf-8")
        self.assertIn("command_id_find", text)
        self.assertIn("macro_load", text)
        self.assertIn("PANEL_DONE_MACRO_MISSING", text)
        # The macro comes from the request; no command name is hard-coded here.
        self.assertNotIn("ProCmdBracketBlend", text)

    def test_the_payload_publishes_the_wait_marker_the_watchdog_reads(self):
        text = self.PAYLOAD.read_text(encoding="utf-8")
        self.assertIn("panel_wait.json", text)
        self.assertIn("write_marker_atomic", text)
        for field in ('"job_id"', '"nonce"', '"profile_id"', '"seq"', '"phase"', '"at_epoch_ms"'):
            self.assertIn(field, text)
        for phase in ("panel_select_wait", "panel_done_wait", "panel_close_wait"):
            self.assertIn(phase, text)


class PanelJobWiring(unittest.TestCase):
    """The job must carry what the native panel route binds its tickets to."""

    SUBMIT = ROOT / "generic_bridge.py"
    RUN = ROOT / "native/panel_run.h"

    def test_admission_identity_reaches_the_operation(self):
        text = self.SUBMIT.read_text(encoding="utf-8")
        self.assertIn('operation["panel"] = {', text)
        for key in ("job_id", "request_id", "nonce", "profile_id", "open_macro"):
            self.assertIn(f'"{key}":', text)

    def test_the_native_route_refuses_instead_of_inventing_a_macro(self):
        text = self.RUN.read_text(encoding="utf-8")
        self.assertIn("PANEL_OPEN_MACRO_MISSING", text)
        self.assertIn("PANEL_ADMISSION_INCOMPLETE", text)
        self.assertIn("PANEL_DEPLOYMENT_REQUIRED", text)
        # The macro is data from the profile: no dialog element names are hard-coded.
        self.assertNotIn("blend_sectionspage", text)
        self.assertNotIn("dashInst0.Done", text)

    def test_the_native_route_refuses_to_claim_an_unobserved_success(self):
        text = self.RUN.read_text(encoding="utf-8")
        self.assertIn("PANEL_SELECTION_INCOMPLETE", text)
        self.assertIn("MechDogPanelFinalize", text)
        self.assertIn("MechDogPanelRelease", text)


class MarkerContract(unittest.TestCase):
    def test_marker_rules_reject_foreign_and_untyped_progress(self):
        text = PANEL_PROTOCOL.read_text(encoding="utf-8")
        self.assertIn("marker_valid", text)
        self.assertIn("write_marker_atomic", text)
        # A failed rename must be reported, never repaired by deleting the target.
        self.assertIn("cannot replace", text)
        self.assertNotIn("remove(target", text)


if __name__ == "__main__":
    unittest.main()
