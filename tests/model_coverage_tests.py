# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.carbon import SourceType
from act.core.common import AbatementLevel, CapacitorType, ModelType
from act.core.device_data import DeviceData
from act.core.models.ap_model import APModel
from act.core.models.capacitor_model import CapacitorModel
from act.core.models.ci_model import CIModel
from act.core.models.dram_model import DRAMModel
from act.core.models.hdd_model import HDDModel
from act.core.models.logic_model import LogicModel
from act.core.models.materials_model import MaterialsModel, NA
from act.core.models.ssd_model import SSDModel
from act.core.processes import DRAMProcess, HDDProcess, LogicProcess, SSDProcess
from act.core.utils.units import g, GB, mm2
from act.tests.base_test_case import BaseTestCase


class ModelCoverageTests(BaseTestCase):
    """Tests for model coverage across all parameter ranges"""

    def setUp(self):
        super().setUp()

    def test_logic_coverage(self):
        """Check that all model values properly load across each parameter range"""

        ci_model = CIModel()
        model = LogicModel()
        valid_processes = [
            LogicProcess.N28,
            LogicProcess.N20,
            LogicProcess.N14,
            LogicProcess.N10,
            LogicProcess.N8,
            LogicProcess.N7,
            LogicProcess.N5,
            LogicProcess.N3,
        ]

        for lp in valid_processes:
            for gpa in AbatementLevel:
                common_args = {
                    "process": lp,
                    "area": str(2 * mm2),
                    "fab_yield": 0.87,
                    "gpa": gpa,
                }
                for ci in ci_model.entities:
                    device_data = DeviceData(**common_args, fab_ci=ci, built=2023)
                    model.get_carbon(device_data)
                for ci in ci_model.sources:
                    device_data = DeviceData(**common_args, fab_ci=ci, built=2023)
                    model.get_carbon(device_data)

    def test_dram_coverage(self):
        """Check that all model values properly load across parameter range"""
        model = DRAMModel()
        for dp in DRAMProcess:
            if dp is DRAMProcess.NA:
                continue
            model.get_carbon(DeviceData(model=ModelType.DRAM, size=1 * GB, process=dp))

    def test_ssd_coverage(self):
        """Check that all SSD model values properly run"""
        model = SSDModel()
        for sp in SSDProcess:
            if sp is SSDProcess.NA:
                continue
            model.get_carbon(DeviceData(model=ModelType.FLASH, size=3 * GB, process=sp))

    def test_hdd_coverage(self):
        """Check that all HDD model values properly run."""
        model = HDDModel()
        for hp in HDDProcess:
            if hp is HDDProcess.NA:
                continue
            model.get_carbon(DeviceData(model=ModelType.HDD, size=1 * GB, process=hp))

    def test_capacitor_coverage(self):
        """Check that all capacitor model values properly run."""
        model = CapacitorModel()
        for cp in CapacitorType:
            device_data = DeviceData(type=cp, weight=0.03 * g, n_ics=2)
            model.get_carbon(device_data)

    def test_ap_coverage(self):
        """Check that all application processor model values properly run."""
        model = APModel()
        valid_nodes = [
            LogicProcess.N28,
            LogicProcess.N20,
            LogicProcess.N14,
            LogicProcess.N10,
            LogicProcess.N7_EUV,
            LogicProcess.N7,
            LogicProcess.N5,
            LogicProcess.N3,
        ]
        for p in valid_nodes:
            device_data = DeviceData(
                area=str(100 * mm2), process=p, fab_yield=0.97, model=ModelType.AP
            )
            model.get_carbon(device_data)

    def test_materials_coverage(self):
        """Basic coverage over materials model"""
        model = MaterialsModel()
        for m in model.material_types:
            if m != NA:
                device_data = DeviceData(type=m, weight=100 * g)
                c = model.get_carbon(device_data)
                self.assertTrue(SourceType.MATERIALS in c.carbon_by_type.keys())
