# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from copy import deepcopy
from unittest.mock import MagicMock

from act.core.act_model import VIRTUAL_POWER_DEVICE
from act.core.carbon import SourceType
from act.core.common import AbatementLevel, ModelType
from act.core.processes import DRAMProcess, LogicProcess
from act.core.scaling.power_scaling_model import PowerScalingModel
from act.core.scaling.tech_scaling_manager import TechScalingManager
from act.core.utils.units import kg
from act.tests.base_test_case import BaseTestCase


class TechScalingTests(BaseTestCase):
    """Test technology scaling"""

    def setUp(self):
        super().setUp()
        self.manager = TechScalingManager()

    def _create_mock_scaling_setup(self, src_process, dst_process, model=None):
        """Helper to create mock objects for scaling tests."""
        mock_dev = MagicMock()
        mock_dev.process = src_process
        if model is not None:
            mock_dev.model = model

        mock_bom = MagicMock()
        mock_bom.devices = {"test_dev": mock_dev}

        mock_carbon = MagicMock()
        mock_results = MagicMock()
        mock_results.carbon_by_device = {"test_dev": mock_carbon}

        mock_scaling_data = MagicMock()
        mock_scaling_data.process = dst_process
        mock_scaling_config = MagicMock()
        mock_scaling_config.scaling_paths = {"test_dev": mock_scaling_data}

        mock_act = MagicMock()
        mock_act.results = mock_results
        mock_act.bom = mock_bom
        mock_act.scaling_config = mock_scaling_config

        return mock_dev, mock_bom, mock_carbon, mock_scaling_config, mock_act

    def test_basic_tech_scaling(self):
        """Basic tech scaling coverage test"""
        self.test_args.extend(
            f"-m {self.boms_dir}/server/dellr740/top.yaml --scaling-config {self.configs_dir}/tech_scaling/sample.yaml".split()
        )

        self.run_act()

    def test_silicon_tech_scaling(self):
        """Test tech scaling for each silicon device type"""
        self.test_args.extend(f"-m {self.boms_dir}/tests/tech_scaling.yaml".split())
        base_args = deepcopy(self.test_args)

        # run the base version
        base_act = self.run_act()

        # run with tech scaling
        tech_scaling_config = f"{self.configs_dir}/tech_scaling/tech_scaling_test.yaml"
        self.test_args = base_args
        self.test_args.extend(f"--scaling-config {tech_scaling_config}".split())
        scaled_act = self.run_act()

        # the carbon partial for any devices not in the tech scaling config path should not have changed
        base_results = base_act.results.get_carbon_by_device()
        scaled_results = scaled_act.results.get_carbon_by_device()

        self.assertEqual(set(base_results.keys()), set(scaled_results.keys()))

        # spot check scaling for the target scaled devices
        for dev in base_results.keys():
            base_carbon = base_results[dev]
            scaled_carbon = scaled_results[dev]

            # if any of the paths are scaled, check against manually computed scale factor for manufacturing only
            if dev in ["dram.dut", "hdd.dut", "flash.dut", "logic.dut"]:
                if dev == "logic.dut":
                    logic_model = base_act.logic_model
                    area_factor = (10 / 14) ** 2
                    expected_scale_factor = (
                        logic_model.get_cpa(LogicProcess.N10, gpa=AbatementLevel.GPA95)
                        / logic_model.get_cpa(
                            LogicProcess.N14, gpa=AbatementLevel.GPA95
                        )
                        * area_factor
                    )
                elif dev == "dram.dut":
                    expected_scale_factor = 315 / 600
                elif dev == "hdd.dut":
                    expected_scale_factor = 10.32 / 4.57
                elif dev == "flash.dut":
                    expected_scale_factor = 15 / 31
                else:
                    self.fail()

                expected_scaled_carbon = (
                    base_carbon.partial(SourceType.FABRICATION) * expected_scale_factor
                )
                result_scaled_carbon = scaled_carbon.partial(SourceType.FABRICATION)
                self.assertAlmostEqual(
                    expected_scaled_carbon,
                    result_scaled_carbon,
                    msg=f"Got device: {dev}. Got base carbon {expected_scaled_carbon} and result carbon {result_scaled_carbon} with expected scale factor {expected_scale_factor} which does not match.",
                )
            else:  # not scaled so should partial should be equal
                self.assertAlmostEqual(base_carbon.total(), scaled_carbon.total())

    def test_load_tech_scaling_factors(self):
        """Test that the tech scaling factors load properly and check integrity."""
        model = PowerScalingModel()

        # ensure the scale factor dimensions is square
        factors = model.scale_factors
        self.assertGreater(len(factors), 0)
        for _, v in factors.items():
            self.assertGreater(len(v), 0)

        # ensure the diagonal is all ones
        for k in factors:
            self.assertEqual(factors[k][k], 1)

        # ensure that all values are non-zero
        for k in factors.keys():
            for k_ in factors.keys():
                self.assertGreater(model.get_scale_factor(k, k_), 0)

    def test_power_scaling(self):
        """Test that power scaling properly reduces operational carbon."""
        self.test_args.extend(f"-m {self.boms_dir}/tests/power_scaling.yaml".split())
        base_act = self.run_act()

        self.test_args.extend(
            f"--scaling-config {self.configs_dir}/tech_scaling/power_scaling_test.yaml".split()
        )
        scaled_act = self.run_act()

        self.assertLess(
            scaled_act.results.total_carbon.partial(SourceType.OPERATION),
            base_act.results.total_carbon.partial(SourceType.OPERATION),
        )

        expected_logic_factor = (
            base_act.tech_scaling_manager.power_scaling_model.get_scale_factor(
                src=LogicProcess.N14, dst=LogicProcess.N7
            )
        )

        # the logic operational carbon should have scaled linearly
        base_logic_op = base_act.results.carbon_by_device["cpu"].partial(
            SourceType.OPERATION
        )
        scaled_logic_op = scaled_act.results.carbon_by_device["cpu"].partial(
            SourceType.OPERATION
        )
        self.assertAlmostEqual(base_logic_op * expected_logic_factor, scaled_logic_op)

        # the dram operational carbon should not have scaled
        self.assertEqual(
            base_act.results.carbon_by_device["dram"].partial(SourceType.OPERATION),
            scaled_act.results.carbon_by_device["dram"].partial(SourceType.OPERATION),
        )

    def test_manual_model_scaling(self):
        """Ensure that manually specified models with logic process specifications scale properly."""
        self.test_args.extend(f"-m {self.boms_dir}/tests/manual.yaml".split())
        base_act = self.run_act()

        self.test_args.extend(
            f"--scaling-config {self.configs_dir}/tech_scaling/manual.yaml".split()
        )
        scaled_act = self.run_act()

        # check that manual device models which are expected to scale changed
        base_result = base_act.results
        scaled_result = scaled_act.results

        expected_scaled_devs = [
            "manual.logic0",
            "manual.dram0",
            "manual.ssd0",
            "manual.hdd0",
        ]
        expected_unscaled_devs = [
            "manual.logic1",
            "manual.dram1",
            "manual.ssd1",
            "manual.hdd1",
        ]

        for dev in expected_scaled_devs:
            self.assertNotEqual(
                base_result.carbon_by_device[dev].total(),
                scaled_result.carbon_by_device[dev].total(),
            )
        for dev in expected_unscaled_devs:
            self.assertAlmostEqual(
                base_result.carbon_by_device[dev].total(),
                scaled_result.carbon_by_device[dev].total(),
            )

        # check that the logic power scaled but others did not
        for dname in base_act.results.carbon_by_device:
            if dname == VIRTUAL_POWER_DEVICE:
                continue  # ignore the system wide virtual power device

            base_op_carbon = base_result.carbon_by_device[dname].partial(
                SourceType.OPERATION
            )
            scaled_op_carbon = scaled_result.carbon_by_device[dname].partial(
                SourceType.OPERATION
            )
            self.assertGreater(
                base_op_carbon,
                0 * kg,
                msg=f"Device {dname} has zero operational carbon. Expected non-zero.",
            )

            if dname == "manual.logic0":
                self.assertLess(scaled_op_carbon, base_op_carbon)
            else:
                self.assertAlmostEqual(scaled_op_carbon, base_op_carbon)

    def test_power_scaling_incompatible_process_types(self):
        """Test that power scaling skips when process types are incompatible"""
        mock_dev, mock_bom, _, mock_scaling_config, _ = self._create_mock_scaling_setup(
            LogicProcess.N14, DRAMProcess.DDR4_10NM
        )
        original_power = mock_dev.power
        self.manager.apply_power_scaling(mock_bom, mock_scaling_config)
        self.assertEqual(mock_dev.power, original_power)

    def test_tech_scaling_incompatible_process_types(self):
        """Test that tech scaling skips when process types are incompatible"""
        _, _, mock_carbon, _, mock_act = self._create_mock_scaling_setup(
            LogicProcess.N14, DRAMProcess.DDR4_10NM
        )
        self.manager.apply_tech_scaling(mock_act)
        mock_carbon.set_partials.assert_not_called()
        mock_carbon.set_partial.assert_not_called()

    def test_tech_scaling_na_process_skipped(self):
        """Test that NA processes are skipped during tech scaling"""
        _, _, mock_carbon, _, mock_act = self._create_mock_scaling_setup(
            LogicProcess.NA, LogicProcess.N10
        )
        self.manager.apply_tech_scaling(mock_act)
        mock_carbon.set_partials.assert_not_called()
        mock_carbon.set_partial.assert_not_called()

    def test_tech_scaling_unsupported_model_type_raises(self):
        """Test that unsupported model types raise NotImplementedError"""
        _, _, _, _, mock_act = self._create_mock_scaling_setup(
            LogicProcess.N14, LogicProcess.N10, model=ModelType.AP
        )
        with self.assertRaises(NotImplementedError) as ctx:
            self.manager.apply_tech_scaling(mock_act)
        self.assertIn(
            "does not have a technology scaling calculation", str(ctx.exception)
        )
