# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.metrics.cost_analyzer import DEFAULT_COST_PER_KWHR, DEFAULT_OFFSET_COST
from act.core.utils.units import dollar, kWh, ton
from act.tests.base_test_case import BaseTestCase


class CostAnalysisTest(BaseTestCase):
    """Tests for cost analysis functionality"""

    def setUp(self):
        super().setUp()

    def test_cost_analysis_test(self):
        """Test the cost analysis logic with default parameters."""
        self.test_args.extend(f"-m {self.boms_dir}/tests/cost_test.yaml".split())
        act = self.run_act()

        # validate the cost analyzer results
        cost_analysis = act.cost_analyzer.get_results()

        logic_cost = cost_analysis["logic0"]

        # make sure that the cost value across operation, manufacturing, and offsets populated as non-zero
        self.assertGreater(logic_cost.opex, 0 * dollar)
        self.assertGreater(logic_cost.opex_offset, 0 * dollar)
        self.assertGreater(logic_cost.capex, 0 * dollar)
        self.assertGreater(logic_cost.capex_offset, 0 * dollar)

        # spot check the offset costs
        carbon = act.results.carbon_by_device["logic0"]
        self.assertEqual(logic_cost.capex, act.bom.devices["logic0"].cost)

        self.assertAlmostEqual(
            (carbon.embodied() * DEFAULT_OFFSET_COST).to(dollar),
            logic_cost.capex_offset,
        )
        self.assertAlmostEqual(
            (carbon.op() * DEFAULT_OFFSET_COST).to(dollar), logic_cost.opex_offset
        )

    def test_cost_analysis_uses_default_values_when_no_parameters(self):
        """Test that default cost values are used when no parameters are specified"""
        self.test_args.extend(f"-m {self.boms_dir}/tests/cost_test.yaml".split())
        act = self.run_act()

        self.assertEqual(act.cost_analyzer.cost_per_kwhr, DEFAULT_COST_PER_KWHR)
        self.assertEqual(act.cost_analyzer.offset_cost, DEFAULT_OFFSET_COST)

    def test_cost_analysis_with_custom_parameters(self):
        """Test that custom cost parameters from BOM are used"""
        self.test_args.extend(f"-m {self.boms_dir}/tests/cost_params_test.yaml".split())
        act = self.run_act()

        expected_DEFAULT_ELECTRICITY_COST = 0.25 * dollar / kWh
        expected_offset_cost = 10.0 * dollar / ton

        self.assertEqual(
            act.cost_analyzer.cost_per_kwhr.to(dollar / kWh),
            expected_DEFAULT_ELECTRICITY_COST.to(dollar / kWh),
        )
        self.assertEqual(
            act.cost_analyzer.offset_cost.to(dollar / ton),
            expected_offset_cost.to(dollar / ton),
        )

        cost_analysis = act.cost_analyzer.get_results()
        logic_cost = cost_analysis["logic0"]
        carbon = act.results.carbon_by_device["logic0"]

        self.assertAlmostEqual(
            (carbon.embodied() * expected_offset_cost).to(dollar),
            logic_cost.capex_offset,
        )
        self.assertAlmostEqual(
            (carbon.op() * expected_offset_cost).to(dollar), logic_cost.opex_offset
        )
