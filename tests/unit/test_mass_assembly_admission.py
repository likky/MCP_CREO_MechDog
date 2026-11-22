import unittest
from unittest.mock import patch

import generic_bridge


class _Submitted(Exception):
    """Stops the call after admission proves the plan was accepted for a job."""


class MassAssemblyAdmissionTest(unittest.TestCase):
    def test_assembly_query_is_submitted_read_only(self):
        # FEAT-057/T08: an assembly is no longer refused before submission; the
        # read-only plan reaches the native reader, which proves the tree itself.
        with (
            patch.object(generic_bridge, "model_info", return_value={"model_type": "assembly"}),
            patch.object(generic_bridge, "submit", side_effect=_Submitted) as submit,
            self.assertRaises(_Submitted),
        ):
            generic_bridge.get_mass_properties("a" * 32, 7.85)
        submit.assert_called_once()
        operations = submit.call_args.args[0]
        self.assertEqual(operations, [{"op": "mass_properties", "density_g_cm3": 7.85}])
        self.assertTrue(submit.call_args.kwargs["readonly"])

    def test_assembly_query_without_density_keeps_the_what_if_absent(self):
        with (
            patch.object(generic_bridge, "model_info", return_value={"model_type": "assembly"}),
            patch.object(generic_bridge, "submit", side_effect=_Submitted) as submit,
            self.assertRaises(_Submitted),
        ):
            generic_bridge.get_mass_properties("a" * 32)
        operations = submit.call_args.args[0]
        self.assertEqual(operations, [{"op": "mass_properties"}])


if __name__ == "__main__":
    unittest.main()
