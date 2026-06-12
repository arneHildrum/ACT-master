# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.common import CARBON_PER_IC_PACKAGE
from act.core.utils.units import kg
from act.tests.base_test_case import BaseTestCase


class UseCaseTests(BaseTestCase):
    """Tests for specific use case scenarios to prevent regressions"""

    def setUp(self):
        super().setUp()

    def test_dellr740(self):
        """Ensure that the dell R740 results preserve the original ACT model results as closely as possible"""
        self.test_args.extend(f"-m {self.boms_dir}/server/dellr740/top.yaml".split())
        act = self.run_act()

        carbon_by_device = act.results.carbon_by_device
        cpu_total = self._filtered_total("cpu", carbon_by_device)
        ssd_secondary_total = self._filtered_total("ssd.secondary", carbon_by_device)
        ssd_main_total = self._filtered_total("ssd.main", carbon_by_device)
        dram_total = self._filtered_total("dram.main", carbon_by_device)

        # check CPU carbon emissions total
        # weak bound due to some possible floating point error between the original and updated
        self.assertAlmostEqual(cpu_total, 23.143405714285716 * kg, places=0)

        # the amount emitted in the original model does not include DRAM IC packaging (n = 19)
        self.assertAlmostEqual(
            ssd_secondary_total, 62.75 * kg + 19 * CARBON_PER_IC_PACKAGE
        )

        # check that the per SSD costs are the same as in the original per SSD
        self.assertAlmostEqual(ssd_main_total, 8 * (136.0457142857143 + 1.95) * kg)

        # check DRAM costs total
        self.assertAlmostEqual(dram_total, 330.4285714285714 * kg)

    def test_fairphone3(self):
        """Ensure that the fairphone3 model aligns with the original results as closely as possible to ensure no regression"""
        self.test_args.extend(f"-m {self.boms_dir}/samples/fairphone3.yaml".split())
        act = self.run_act()

        carbon_by_device = act.results.carbon_by_device

        # ensure expected number of devices appear
        self.assertEqual(len(carbon_by_device), 24)
        dram_flash_carbon = (
            carbon_by_device["dram"].total() + carbon_by_device["ssd"].total()
        )
        self.assertAlmostEqual(dram_flash_carbon, 5.310285714285714 * kg)

        cpu_carbon = carbon_by_device["cpu"].total()
        self.assertAlmostEqual(cpu_carbon, 0.8992937142857143 * kg)

        ic_carbon = self._filtered_total("ics", carbon_by_device)
        self.assertAlmostEqual(ic_carbon, 5.691643885714286 * kg)
