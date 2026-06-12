# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.models.ci_model import CIModel
from act.tests.base_test_case import BaseTestCase


class SupplyChainTests(BaseTestCase):
    """Tests for supply chain scaling functionality"""

    def test_basic_supply_chain_change(self):
        """Test that supply chain location changes properly scale carbon emissions."""
        ci_model = CIModel()

        self.test_args.extend(f"-m {self.boms_dir}/server/dellr740/top.yaml".split())
        base_act = self.run_act()

        self.test_args.extend(
            f"--scaling-config {self.configs_dir}/supply_chain/sample.yaml".split()
        )
        scaled_act = self.run_act()

        # check that the resulting carbon for each component reflects that changes to the manufacturing location
        for dname, dev in base_act.bom.devices.items():
            base_carbon = base_act.results.carbon_by_device[dname]
            scaled_carbon = scaled_act.results.carbon_by_device[dname]

            if dname.startswith("cpu0.main"):
                expected_factor = ci_model.get_ci_scale_factor(
                    src_or_loc=dev.fab_ci, new_src_or_loc="usa", built=dev.built
                )
                expected_carbon = base_carbon * expected_factor
            elif dname.startswith("ssd"):
                expected_factor = ci_model.get_ci_scale_factor(
                    src_or_loc=dev.fab_ci, new_src_or_loc="china", built=dev.built
                )
                expected_carbon = base_carbon * expected_factor
            elif dname.startswith("dram.main2"):
                expected_factor = ci_model.get_ci_scale_factor(
                    src_or_loc=dev.fab_ci,
                    new_src_or_loc="south korea",
                    built=dev.built,
                )
                expected_carbon = base_carbon * expected_factor
            else:  # all other devices should not have scaled
                expected_carbon = base_carbon
            self.assertAlmostEqual(
                expected_carbon.total(),
                scaled_carbon.total(),
                msg=f"Device {dname} expected carbon = {expected_carbon.total()} but got {scaled_carbon.total()}. Original carbon {base_carbon.total()}.",
            )
