# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import copy

from act.core.carbon import SourceType
from act.core.common import AbatementLevel, DEFAULT_OP_YEAR
from act.core.processes import LogicProcess
from act.core.utils.units import kg, mm2, mW, year
from act.tests.base_test_case import BaseTestCase


class BOMTests(BaseTestCase):
    """Tests for bill of materials loading, parsing, and configuration"""

    def setUp(self):
        super().setUp()

    def test_bom_import(self):
        """Test that importing a file works as expected"""
        self.test_args.extend(f"-m {self.boms_dir}/tests/test.yaml".split())
        act = self.run_act()

        # ensure the imported devices appear in the result
        self.assertTrue("subsystem.imported_cap" in act.results.carbon_by_device)
        self.assertTrue("subsystem.imported_si" in act.results.carbon_by_device)
        self.assertTrue("subsystem.imported_mat" in act.results.carbon_by_device)

    def test_bom_power_fields(self):
        """Test that operating power and CI fields are properly detected from BOM."""
        # test that if a operating power and CI is specified, that the run picks up those values by default
        self.test_args.extend(f"-m {self.boms_dir}/tests/op_power.yaml".split())
        act = self.run_act()

        # the run should have autodetected the op power and ci fields
        self.assertEqual(act.op_power, 125 * mW)
        self.assertEqual(act.op_ci, "japan")

    def test_macros(self):
        """Test that macros propagate properly to control BOM."""
        # test that macros propagate properly to control BOM

        # run with base args to ensure default macros work
        self.test_args.extend(f"-m {self.boms_dir}/tests/macros.yaml".split())
        base_act = self.run_act()
        self.assertEqual(base_act.bom.devices["dut"].area, 25 * mm2)
        self.assertEqual(base_act.bom.devices["dut"].process, LogicProcess.N5)

        # pass overrides to check propagation
        self.test_args.extend("-D AREA=12.5mm2 PROCESS=14nm".split())
        test_act = self.run_act()
        self.assertEqual(test_act.bom.devices["dut"].area, 12.5 * mm2)
        self.assertEqual(test_act.bom.devices["dut"].process, LogicProcess.N14)

    def test_recursive_import(self):
        """Test that recursive import with proper path delimiters works."""
        # test that the recursive import with proper path delimiters works
        self.test_args.extend(f"-m {self.boms_dir}/tests/top.yaml".split())
        act = self.run_act()

        bom = act.bom
        expected_materials = ["top_mat", "mid.mid_mat", "mid.bot.bot_mat"]
        expected_si = ["top_si", "mid.mid_si", "mid.bot.bot_si"]
        expected_caps = ["top_cap", "mid.mid_cap", "mid.bot.bot_cap"]

        # ensure properly hierarchical import with delimiters
        for m in expected_materials + expected_si + expected_caps:
            self.assertIn(m, bom.devices)

    def test_year_built(self):
        """Test that the year built properly changes the carbon intensity of relevant devices."""
        # test that the year that the device was built properly changes the carbon intensity of relevant devices
        self.test_args.extend(f"-m {self.boms_dir}/tests/built.yaml".split())
        act = self.run_act()

        # the gas and materials components need to be subtracted out since they are not correlated to CI year
        fab_yield = 0.875
        gas_carbon = (
            act.logic_model.gpa_model[AbatementLevel.GPA97][LogicProcess.N7]
            * 1
            * mm2
            / fab_yield
        )
        materials_carbon = (
            act.logic_model.materials_model[LogicProcess.N7] * 1 * mm2 / fab_yield
        )
        logic_2023 = (
            (
                act.results.carbon_by_device["logic_2023"]
                .partial(SourceType.FABRICATION)
                .to(kg)
            )
            - gas_carbon
            - materials_carbon
        )
        logic_2022 = (
            (
                act.results.carbon_by_device["logic_2022"]
                .partial(SourceType.FABRICATION)
                .to(kg)
            )
            - gas_carbon
            - materials_carbon
        )

        # manually check the logic scaled according to the year
        logic_multiplier = 644.39636 / 639.26575
        self.assertAlmostEqual(logic_2022 * logic_multiplier, logic_2023)

        # manually check that the capacitor result scaled to the year
        cap_2023 = (
            act.results.carbon_by_device["cap_2023"].partial(SourceType.PASSIVES).to(kg)
        )
        cap_2022 = (
            act.results.carbon_by_device["cap_2022"].partial(SourceType.PASSIVES).to(kg)
        )
        cap_multiplier = 493.58505 / 519.6191
        self.assertAlmostEqual(cap_2022 * cap_multiplier, cap_2023)

    def test_op_year(self):
        """Test that the operational year properly affects operational carbon calculations."""
        self.test_args.extend(
            f"-m {self.boms_dir}/tests/empty.yaml --op-ci usa --op-power 100 mW".split()
        )
        base_args = copy.deepcopy(self.test_args)

        # test with a default year
        self.test_args.extend("--op-year 2023".split())
        act_2023 = self.run_act()

        # test with a different year
        self.test_args = base_args
        self.test_args.extend("--op-year 2022".split())
        act_2022 = self.run_act()

        carbon_2023 = act_2023.results.total_carbon.partial(SourceType.OPERATION)
        carbon_2022 = act_2022.results.total_carbon.partial(SourceType.OPERATION)

        # manually calculate the delta factor
        delta_factor = 392.848 / 410.3674

        # check that the power decreased as expected between the two years
        self.assertAlmostEqual(carbon_2022 * delta_factor, carbon_2023)

    def test_incomplete_bom(self):
        """Ensure that a bill of materials with devices missing fields returns an error and aborts"""
        self.test_args.extend(
            f"-m {self.boms_dir}/tests/failing/incomplete_device.yaml".split()
        )

        expected_code = -1
        with self.assertRaises(SystemExit) as cm:
            self.run_act(expected_code)
        self.assertEqual(cm.exception.code, expected_code)

    def test_embodied_and_operational_carbon(self):
        """Test devices which have both the embodied and operational power annotated"""
        self.test_args.extend(f"-m {self.boms_dir}/tests/emb_op_devices.yaml".split())
        act = self.run_act()

        dut0_carbon = act.results.carbon_by_device["dut0"]
        dut1_carbon = act.results.carbon_by_device["dut1"]

        # ensure the devices have both a fabrication and operational component
        self.assertGreater(dut0_carbon.partial(SourceType.OPERATION), 0 * kg)
        self.assertGreater(dut0_carbon.partial(SourceType.FABRICATION), 0 * kg)

        self.assertGreater(dut1_carbon.partial(SourceType.OPERATION), 0 * kg)
        self.assertGreater(dut1_carbon.partial(SourceType.FABRICATION), 0 * kg)

        # check that the individual overrides apply properly

    def test_operational_overrides(self):
        """Test that the default operational parameters proapgate properly and are resolved correctly"""
        self.test_args.extend(f"-m {self.boms_dir}/tests/op_params.yaml".split())
        no_args_act = self.run_act()

        # the defaults should align with the BOM defaults
        default_dev = no_args_act.bom.devices["default_dev"]
        self.assertEqual(default_dev.op_ci, "usa")
        self.assertEqual(default_dev.life_cycle, 1.5 * year)
        self.assertEqual(default_dev.duty_cycle, 0.75)
        self.assertEqual(default_dev.op_year, DEFAULT_OP_YEAR)

        def check_overrided_dev(dev):
            self.assertEqual(dev.op_ci, "south korea")
            self.assertEqual(dev.duty_cycle, 0.66)
            self.assertEqual(dev.life_cycle, 0.5 * year)
            self.assertEqual(dev.op_year, 2018)

        overrided_dev = no_args_act.bom.devices["override_all"]
        check_overrided_dev(overrided_dev)

        # run with command line overrides
        cl_op_ci = "canada"
        cl_duty_cycle = 0.88
        cl_life_cycle = 1.7 * year
        cl_op_year = 2015
        self.test_args.extend(
            f"--op-ci {cl_op_ci} --duty-cycle {cl_duty_cycle} --life-cycle {cl_life_cycle} --op-year {cl_op_year}".split()
        )
        cl_act = self.run_act()

        default_dev = cl_act.bom.devices["default_dev"]
        self.assertEqual(default_dev.op_ci, cl_op_ci)
        self.assertEqual(default_dev.life_cycle, cl_life_cycle)
        self.assertEqual(default_dev.duty_cycle, cl_duty_cycle)
        self.assertEqual(default_dev.op_year, cl_op_year)

        overrided_dev = cl_act.bom.devices["override_all"]
        check_overrided_dev(overrided_dev)

    def test_parameters_field(self):
        """Test that the parameters field is loaded from the BOM YAML file"""
        self.test_args.extend(f"-m {self.boms_dir}/tests/parameters.yaml".split())
        act = self.run_act()

        self.assertIsNotNone(act.bom.parameters)
        self.assertEqual(act.bom.parameters["model_override_1"], "value1")
        self.assertEqual(act.bom.parameters["model_override_2"], 42)
        self.assertIn("nested_config", act.bom.parameters)
        self.assertEqual(act.bom.parameters["nested_config"]["setting_a"], True)
        self.assertEqual(act.bom.parameters["nested_config"]["setting_b"], 3.14)

    def test_parameters_field_empty(self):
        """Test that the parameters field is None when not specified in the BOM"""
        self.test_args.extend(f"-m {self.boms_dir}/tests/empty.yaml".split())
        act = self.run_act()

        self.assertIsNone(act.bom.parameters)
