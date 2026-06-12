# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.common import AbatementLevel, ModelType
from act.core.device_data import DeviceData
from act.core.models.dram_model import DRAMModel
from act.core.models.hdd_model import HDDModel
from act.core.models.imec_logic_model import IMECLogicModel
from act.core.models.logic_model import LogicModel
from act.core.models.ssd_model import SSDModel
from act.core.processes import DRAMProcess, HDDProcess, LogicProcess, SSDProcess
from act.core.utils.units import cm2, g, GB, kg, mm2
from act.tests.base_test_case import BaseTestCase


class BasicModelTests(BaseTestCase):
    """Ensures that the original ACT functionality is preserved based on the input/output pairs"""

    def test_default_logic_model(self):
        """Ensure that the default legacy ACT model logic results are preserved"""
        logic_model = LogicModel(use_legacy=True)

        tp = LogicProcess.N14
        self.assertAlmostEqual(
            logic_model.get_cpa(process=tp),
            1556.685714285714 * g / cm2,
        )
        self.assertEqual(
            logic_model.get_carbon_energy(process=tp),
            699.6 * g / cm2,
        )
        self.assertEqual(logic_model.get_carbon_gas(process=tp), 162.5 * g / cm2)
        self.assertEqual(logic_model.get_carbon_materials(tp), 500 * g / cm2)

    def test_logic_model_integration(self):
        """Ensure that the default configuration that is fed by default to ACT does not change"""
        tp = LogicProcess.N10
        gpa = AbatementLevel.GPA95
        fab_ci = "coal"
        logic_model = LogicModel()

        self.assertEqual(
            logic_model.get_cpa(gpa=gpa, fab_ci=fab_ci, process=tp),
            2228.0 * g / cm2,
        )
        self.assertEqual(
            logic_model.get_carbon_energy(fab_ci=fab_ci, process=tp),
            1209.5 * g / cm2,
        )
        self.assertEqual(logic_model.get_carbon_gas(gpa=gpa, process=tp), 240 * g / cm2)
        self.assertEqual(logic_model.get_carbon_materials(tp), 500 * g / cm2)

    def test_basic_dram_model(self):
        """Ensure original DRAM model results remain consistent"""
        dram_model = DRAMModel()
        tp = DRAMProcess.DDR4_10NM
        carbon_cost = dram_model.get_carbon(
            DeviceData(model=ModelType.DRAM, process=tp, size=str(3 * GB))
        )

        self.assertEqual(carbon_cost.total(), 222.8571428571429 * g)

    def test_basic_hdd_model(self):
        """Ensure original HDD model results remain consistent"""
        hdd_model = HDDModel()
        hp = HDDProcess.BARRACUDA
        size = 3 * GB
        fab_yield = 1.0  # the original model doesn't properly account for yield

        carbon_cost = hdd_model.get_carbon(
            DeviceData(
                process=hp, size=str(size), fab_yield=fab_yield, model=ModelType.HDD
            )
        )
        cpg = hdd_model.get_cpg(
            hp, fab_yield
        )  # the original HDD model doesn't have a yield

        self.assertAlmostEqual(cpg, 4.57 * g / GB)
        self.assertAlmostEqual(carbon_cost.total(), 13.71 * g)

    def test_basic_ssd_model(self):
        """Ensure SSD model loads and runs correctly"""
        fab_yield = 0.9
        ssd_model = SSDModel()
        ssd_process = SSDProcess.NAND_10NM

        ssd_carbon = ssd_model.get_carbon(
            DeviceData(
                process=ssd_process,
                size=str(3 * GB),
                fab_yield=fab_yield,
                model=ModelType.FLASH,
            )
        )
        ssd_cpg = ssd_model.get_cpg(process=ssd_process, fab_yield=fab_yield)
        self.assertAlmostEqual(ssd_cpg, 10 * g / GB / fab_yield)
        self.assertAlmostEqual(ssd_carbon.total(), 30 * g / fab_yield)

    def test_imec_logic_model(self):
        """Ensure IMEC logic model loads and computes carbon from CPA data."""
        model = IMECLogicModel()

        # Verify CPA values match the YAML (kg/cm2) at unity yield
        self.assertAlmostEqual(
            model.get_cpa(LogicProcess.N14, fab_yield=1.0), 0.97 * kg / cm2
        )
        self.assertAlmostEqual(
            model.get_cpa(LogicProcess.N7, fab_yield=1.0), 1.44 * kg / cm2
        )
        self.assertAlmostEqual(
            model.get_cpa(LogicProcess.N3, fab_yield=1.0), 1.75 * kg / cm2
        )

        # Verify yield adjustment
        self.assertAlmostEqual(
            model.get_cpa(LogicProcess.N7, fab_yield=0.5),
            1.44 * kg / cm2 / 0.5,
        )

        # Verify get_carbon produces a valid result
        device_data = DeviceData(
            area=str(100 * mm2),
            process=LogicProcess.N7,
            fab_yield=0.9,
            model=ModelType.LOGIC,
        )
        carbon = model.get_carbon(device_data)
        self.assertGreater(carbon.total(), 0 * g)

        # Verify process support
        self.assertTrue(model.is_process_supported(LogicProcess.N7))
        self.assertFalse(model.is_process_supported(LogicProcess.N2))

    def test_imec_vs_logic_model(self):
        """Compare IMEC CPA model against legacy EPA+GPA+materials model
        on the same device and verify they produce different but valid results."""
        imec_model = IMECLogicModel()
        logic_model = LogicModel(use_legacy=True)

        process = LogicProcess.N7
        area = 100 * mm2
        fab_yield = 0.9

        # Compare CPA values at the same process and yield
        imec_cpa = imec_model.get_cpa(process, fab_yield=fab_yield)
        logic_cpa = logic_model.get_cpa(process, fab_yield=fab_yield)

        # They should differ since the models use different data sources
        self.assertNotEqual(imec_cpa, logic_cpa)

        # Verify IMEC CPA matches expected value (1.44 kg/cm2 / 0.9 yield)
        self.assertAlmostEqual(imec_cpa, 1.44 * kg / cm2 / fab_yield)

        # Compare full get_carbon results on the same device
        device_data = DeviceData(
            area=str(area),
            process=process,
            fab_yield=fab_yield,
            model=ModelType.LOGIC,
        )
        imec_carbon = imec_model.get_carbon(device_data)
        logic_carbon = logic_model.get_carbon(device_data)

        # Results should differ between the two models
        self.assertNotEqual(imec_carbon.total(), logic_carbon.total())

    def test_imec_logic_model_via_bom(self):
        """Ensure IMEC logic model works end-to-end through ACTModel with a BOM."""
        self.test_args.extend(f"-m {self.boms_dir}/tests/imec_logic.yaml".split())
        act = self.run_act()

        total_carbon = act.results.total_carbon.total()
        self.assertGreater(total_carbon, 0 * g)

        # Verify the device was processed with the IMEC model
        self.assertIn("chip", act.results.carbon_by_device)
        chip_carbon = act.results.carbon_by_device["chip"]
        self.assertGreater(chip_carbon.total(), 0 * g)
