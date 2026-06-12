# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.metrics.carbon_delay_product import CarbonDelayProduct
from act.core.metrics.carbon_energy_product import CarbonEnergyProduct
from act.core.metrics.carbon_energy_squared_product import CarbonEnergySquaredProduct
from act.core.metrics.carbon_squared_energy_product import CarbonSquaredEnergyProduct
from act.core.utils.units import g, J, kg, year
from act.tests.base_test_case import BaseTestCase


class AnalysisTests(BaseTestCase):
    """Tests over analyses over the results"""

    def setUp(self):
        super().setUp()

    def test_metrics_results(self):
        """Spot check the basic metrics data structure is properly populated and numbers check out"""
        self.test_args.extend(
            f"-m {self.boms_dir}/server/dellr740/top.yaml --life-cycle 1 year --duty-cycle 1.0 --op-power 0 W".split()
        )

        act = self.run_act()

        metrics = act.results.metrics
        self.assertGreater(len(metrics), 0)
        expected_carbon = 1523137.6914285717 * g

        self.assertAlmostEqual(metrics[CarbonDelayProduct.NAME], expected_carbon * year)
        self.assertAlmostEqual(metrics[CarbonEnergyProduct.NAME], 0 * kg * J)
        self.assertAlmostEqual(
            metrics[CarbonSquaredEnergyProduct.NAME],
            0 * kg * kg * J,
        )
        self.assertAlmostEqual(metrics[CarbonEnergySquaredProduct.NAME], 0 * kg * J * J)
