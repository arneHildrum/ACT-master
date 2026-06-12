# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import logging
import unittest

from act.core.processes import (
    get_next_largest_logic_process,
    LogicProcess,
    resolve_logic_process_with_rounding,
)
from act.core.utils.units import nm
from act.tests.base_test_case import BaseTestCase


class ProcessRoundingTests(BaseTestCase):
    """Tests for technology node rounding functionality"""

    def test_get_next_largest_logic_process_exact_match(self):
        """Test that exact process sizes return the correct process"""
        result = get_next_largest_logic_process(14 * nm)
        self.assertEqual(result, LogicProcess.N14)

        result = get_next_largest_logic_process(7 * nm)
        self.assertEqual(result, LogicProcess.N7)

        result = get_next_largest_logic_process(5 * nm)
        self.assertEqual(result, LogicProcess.N5)

    def test_get_next_largest_logic_process_rounds_up(self):
        """Test that non-exact sizes round up to the next largest node"""
        result = get_next_largest_logic_process(15 * nm)
        self.assertEqual(result, LogicProcess.N20)

        result = get_next_largest_logic_process(12 * nm)
        self.assertEqual(result, LogicProcess.N14)

        result = get_next_largest_logic_process(6 * nm)
        self.assertEqual(result, LogicProcess.N7)

        result = get_next_largest_logic_process(4 * nm)
        self.assertEqual(result, LogicProcess.N5)

        result = get_next_largest_logic_process(1.5 * nm)
        self.assertEqual(result, LogicProcess.N2)

    def test_get_next_largest_logic_process_no_match(self):
        """Test that sizes larger than all processes return NA"""
        result = get_next_largest_logic_process(100 * nm)
        self.assertEqual(result, LogicProcess.NA)

    def test_resolve_logic_process_with_rounding_exact(self):
        """Test that exact process strings resolve without rounding"""
        result, was_rounded = resolve_logic_process_with_rounding("14nm")
        self.assertEqual(result, LogicProcess.N14)
        self.assertFalse(was_rounded)

        result, was_rounded = resolve_logic_process_with_rounding("7nm")
        self.assertEqual(result, LogicProcess.N7)
        self.assertFalse(was_rounded)

    def test_resolve_logic_process_with_rounding_rounds_up(self):
        """Test that non-exact process strings round up to the next largest node"""
        result, was_rounded = resolve_logic_process_with_rounding("15nm")
        self.assertEqual(result, LogicProcess.N20)
        self.assertTrue(was_rounded)

        result, was_rounded = resolve_logic_process_with_rounding("12nm")
        self.assertEqual(result, LogicProcess.N14)
        self.assertTrue(was_rounded)

        result, was_rounded = resolve_logic_process_with_rounding("6nm")
        self.assertEqual(result, LogicProcess.N7)
        self.assertTrue(was_rounded)

    def test_bom_process_rounding(self):
        """Test that BOM with non-exact processes rounds correctly and logs warning"""
        self.test_args.extend(f"-m {self.boms_dir}/tests/process_rounding.yaml".split())

        with self.assertLogs("ACT", level=logging.WARNING) as log_context:
            act = self.run_act(loglevel=logging.WARNING)

        self.assertEqual(act.bom.devices["logic_exact"].process, LogicProcess.N14)

        self.assertEqual(act.bom.devices["logic_15nm"].process, LogicProcess.N20)

        self.assertEqual(act.bom.devices["logic_12nm"].process, LogicProcess.N14)

        self.assertEqual(act.bom.devices["logic_6nm"].process, LogicProcess.N7)

        self.assertEqual(act.bom.devices["logic_4nm"].process, LogicProcess.N5)

        self.assertEqual(act.bom.devices["logic_1_5nm"].process, LogicProcess.N2)

        warning_messages = [record for record in log_context.output]
        self.assertGreater(len(warning_messages), 0)

        found_rounding_warning = any(
            "is not available" in msg and "Rounding to next largest" in msg
            for msg in warning_messages
        )
        self.assertTrue(found_rounding_warning)
