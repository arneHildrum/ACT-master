# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.carbon import SourceType
from act.core.common import CapacitorType, DEFAULT_OP_YEAR, ModelType
from act.core.device_data import DeviceData
from act.core.models.ap_model import APModel
from act.core.models.battery_model import BatteryModel
from act.core.models.capacitor_model import CapacitorModel
from act.core.models.ci_model import CIModel, DEFAULT_CAP_LOCATION
from act.core.models.dram_model import DRAMModel
from act.core.models.hdd_model import HDDModel
from act.core.models.manual_model import ManualModel
from act.core.models.materials_model import MaterialsModel
from act.core.models.pcb_model import PCBModel
from act.core.models.ssd_model import SSDModel
from act.core.processes import DRAMProcess, HDDProcess, LogicProcess, SSDProcess
from act.core.utils.units import cm2, g, GB, kg, kWh, m2, MJ, mm2, mW, mWh, year
from act.tests.base_test_case import BaseTestCase


class ModelUnitTests(BaseTestCase):
    """Unit tests over carbon models"""

    def setUp(self):
        super().setUp()

    def test_logic_model(self):
        """Basic unit to spot check the logic carbon calculation result"""
        fab_yield = 0.943543
        area = 145 * mm2
        device_data = DeviceData(
            fab_yield=fab_yield,
            area=str(area),
            process=LogicProcess.N10,
            n_ics=1,
            gpa=self.gpa,
            fab_ci=self.fab_ci,
        )
        result = self.act_model.logic_model.get_carbon(
            device_data,
        )

        # ensure manually calculated value is correct
        expected = (
            1.475 * kWh / cm2 * area * 583 * g / kWh
            + 240 * g / cm2 * area
            + 500 * g / cm2 * area
        ) / fab_yield + 150 * g
        self.assertEqual(
            set(result.types()), {SourceType.FABRICATION, SourceType.PACKAGING}
        )
        self.assertAlmostEqual(result.partial(SourceType.PACKAGING), 150 * g)
        self.assertAlmostEqual(result.total(), expected)

    def test_storage_models(self):
        """Basic unit tests over storage models"""

        dram_model = DRAMModel()
        ssd_model = SSDModel()
        hdd_model = HDDModel()
        fab_yield = 0.9
        n_ics = 2

        size = 10 * GB
        common_args = {"size": str(size), "n_ics": n_ics, "fab_yield": fab_yield}
        expected_ctypes = {SourceType.FABRICATION, SourceType.PACKAGING}
        pkg_partial = 150 * g * n_ics

        def _check_results(result, expected):
            self.assertAlmostEqual(result.total(), expected)
            self.assertEqual(set(result.types()), expected_ctypes)
            self.assertAlmostEqual(result.partial(SourceType.PACKAGING), pkg_partial)

        # test DRAM model
        dram_data = DeviceData(
            process=DRAMProcess.DDR3_30NM, model=ModelType.DRAM, **common_args
        )
        result = dram_model.get_carbon(dram_data)
        expected = (230 * g / GB * size / fab_yield) + 150 * g * n_ics
        _check_results(result, expected)

        # test SSD model
        ssd_data = DeviceData(
            process=SSDProcess.NAND_30NM, model=ModelType.FLASH, **common_args
        )
        result = ssd_model.get_carbon(ssd_data)
        expected = (31 * g / GB * size / fab_yield) + 150 * g * n_ics
        _check_results(result, expected)

        # test HDD model
        hdd_data = DeviceData(
            process=HDDProcess.BARRACUDA, model=ModelType.HDD, **common_args
        )
        result = hdd_model.get_carbon(hdd_data)
        expected = (4.57 * g / GB * size / fab_yield) + 150 * g * n_ics
        _check_results(result, expected)

    def test_op_model(self):
        """Basic unit test over operational carbon model"""
        life_cycle = 3.5 * year
        duty_cycle = 0.723
        op_power = 273 * mW
        op_ci = "australia"

        device_data = DeviceData(
            life_cycle=life_cycle,
            duty_cycle=duty_cycle,
            power=op_power,
            op_ci=op_ci,
            op_year=DEFAULT_OP_YEAR,
        )
        op_carbon = self.act_model.op_model.get_carbon(
            device_data,
        )

        # manually calculate expected
        expected = 597 * g / kWh * op_power * duty_cycle * life_cycle
        self.assertEqual(op_carbon.types(), [SourceType.OPERATION])
        self.assertAlmostEqual(expected, op_carbon.total())

    def test_ap_model(self):
        """Basic test over application processor model"""

        ap_model = APModel()

        # test inputs
        area = 10.0 * cm2
        process = LogicProcess("14nm")
        fab_yield = 0.8
        n_ics = 2

        expected_carbon = 47.88 * kg
        expected_packaging = 300 * g / fab_yield
        device_data = DeviceData(
            area=str(area),
            process=process,
            fab_yield=fab_yield,
            n_ics=n_ics,
            model=ModelType.AP,
        )
        result_carbon = ap_model.get_carbon(device_data)

        self.assertAlmostEqual(result_carbon.total().to(kg), expected_carbon, places=2)

        # check partials
        self.assertAlmostEqual(
            result_carbon.partial(SourceType.PACKAGING), expected_packaging
        )
        self.assertAlmostEqual(
            result_carbon.partial(SourceType.FABRICATION).to(kg),
            expected_carbon - expected_packaging,
            places=2,
        )

        # check carbon types
        self.assertEqual(
            set(result_carbon.carbon_by_type.keys()),
            set([SourceType.FABRICATION, SourceType.PACKAGING]),
        )

    def test_capacitor_model(self):
        model = CapacitorModel(use_legacy=True)
        ci = DEFAULT_CAP_LOCATION
        weight = 1.0 * kg
        n_caps = 2

        # test the MLCC model
        device_data = DeviceData(
            fab_ci=ci, type=CapacitorType.MLCC, weight=str(weight), n_ics=n_caps
        )
        carbon = model.get_carbon(
            device_data,
        )
        expected_carbon = 6862 * MJ / kg * weight * 485 * g / kWh * n_caps
        self.assertAlmostEqual(carbon.total(), expected_carbon)
        self.assertEqual(carbon.types(), [SourceType.PASSIVES])

        # test the TEC model
        device_data = DeviceData(
            fab_ci=ci, type=CapacitorType.TEC, weight=str(weight), n_ics=n_caps
        )
        carbon = model.get_carbon(
            device_data,
        )
        expected_carbon = 5567 * MJ / kg * weight * 485 * g / kWh * n_caps
        self.assertAlmostEqual(carbon.total(), expected_carbon)
        self.assertEqual(carbon.types(), [SourceType.PASSIVES])

    def test_materials_model(self):
        """Basic materials model test"""
        model = MaterialsModel()

        mat = "steel"
        weight = 0.25 * kg
        device_data = DeviceData(type=mat, weight=str(weight))
        carbon = model.get_carbon(device_data)
        expected_carbon = weight * 1.89  # manually calculate
        self.assertAlmostEqual(expected_carbon, carbon.total())
        self.assertEqual(carbon.types(), [SourceType.MATERIALS])

    def test_battery_model(self):
        """Basic battery model test with default NMC cathode"""
        model = BatteryModel()
        capacity = 1000 * mWh
        device_data = DeviceData(capacity=str(capacity))
        carbon = model.get_carbon(device_data)
        expected_carbon = 87 * kg / kWh * capacity
        self.assertAlmostEqual(expected_carbon, carbon.total())
        self.assertEqual(carbon.types(), [SourceType.FABRICATION])

    def test_battery_model_lfp(self):
        """Battery model test with LFP cathode type"""
        model = BatteryModel()
        capacity = 1000 * mWh
        device_data = DeviceData(capacity=str(capacity), type="LFP")
        carbon = model.get_carbon(device_data)
        expected_carbon = 61.5 * kg / kWh * capacity
        self.assertAlmostEqual(expected_carbon, carbon.total())
        self.assertEqual(carbon.types(), [SourceType.FABRICATION])

    def test_battery_model_nmc_explicit(self):
        """Battery model test with explicit NMC cathode type"""
        model = BatteryModel()
        capacity = 1000 * mWh
        device_data = DeviceData(capacity=str(capacity), type="NMC")
        carbon = model.get_carbon(device_data)
        expected_carbon = 87 * kg / kWh * capacity
        self.assertAlmostEqual(expected_carbon, carbon.total())
        self.assertEqual(carbon.types(), [SourceType.FABRICATION])

    def test_battery_model_dynamic_types(self):
        """Battery model types are dynamically loaded from config"""
        model = BatteryModel()
        self.assertIn("NMC", model.battery_types)
        self.assertIn("LFP", model.battery_types)

    def test_pcb_model(self):
        """Basic PCB model test"""
        model = PCBModel()

        # test a case where the value exists in the file
        area = 1.5 * cm2
        layers = 4
        device_data = DeviceData(area=str(area), layers=layers)
        result = model.get_carbon(device_data)
        expected = 0.43 * kg / m2 * area
        self.assertAlmostEqual(result.total(), expected)
        self.assertEqual(result.types(), [SourceType.FABRICATION])

        # test an interpolated test case
        area = 2.5 * cm2
        layers = 7
        device_data = DeviceData(area=str(area), layers=layers)
        result = model.get_carbon(device_data)
        expected = 0.13 * kg / m2 * layers * area
        self.assertAlmostEqual(result.total(), expected)
        self.assertEqual(result.types(), [SourceType.FABRICATION])

    def test_ci_model(self):
        """Test that CI model loads and runs as expected"""
        ci_model = CIModel()

        # check non-empties
        self.assertGreater(len(ci_model.carbon_data), 0)
        self.assertGreater(len(ci_model.years), 0)
        self.assertGreater(len(ci_model.entities), 0)

        # spot check entity membership
        expected_entities = [
            "India",
            "Australia",
            "Taiwan",
            "Singapore",
            "USA",
            "Europe",
            "Brazil",
            "Iceland",
            "South Korea",
            "Japan",
            "Indonesia",
        ]
        for entity in expected_entities:
            self.assertIn(entity.lower(), ci_model.entities)

        # check a few configurations
        ci_model.get_ci("usa", year=2016)
        ci_model.get_ci("Taiwan", year=2023)
        ci_model.get_ci("JAPAN", year=2020)
        ci_model.get_ci("China")  # make sure default year works

        # spot check source membership and that they properly fetch
        expected_sources = [
            "coal",
            "gas",
            "biomass",
            "solar",
            "geothermal",
            "hydropower",
            "nuclear",
            "wind",
        ]
        for source in expected_sources:
            self.assertIn(source.lower(), ci_model.sources)
            ci_model.get_ci(source)

    def test_manual_model(self):
        """Test that manual model passes through carbon without implicit calculations"""
        model = ManualModel()

        carbon = 501 * g
        device_data = DeviceData(
            carbon=carbon,
            ctype=SourceType.FABRICATION,
        )
        result = model.get_carbon(device_data)

        self.assertEqual(carbon, result.total())

    def test_manual_model_passthrough(self):
        """Test that manual model does not scale by yield or add packaging"""
        model = ManualModel()

        carbon = 500 * g
        device_data = DeviceData(
            carbon=carbon,
            ctype=SourceType.FABRICATION,
            fab_yield=0.5,
            n_ics=4,
        )
        result = model.get_carbon(device_data)

        self.assertEqual(carbon, result.total())
