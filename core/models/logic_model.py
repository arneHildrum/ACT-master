# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import pint
from act.core.carbon import Carbon, SourceType
from act.core.common import (
    AbatementLevel,
    ACT_ROOT,
    CARBON_PER_IC_PACKAGE,
    DEFAULT_FAB_YIELD,
)
from act.core.device_data import AREA, BUILT, FAB_CI, FAB_YIELD, GPA, N_ICS, PROCESS
from act.core.models.base_logic_model import BaseLogicModel
from act.core.models.ci_model import CIModel, DEFAULT_BUILD_YEAR, DEFAULT_FAB_LOCATION
from act.core.processes import LOGIC_DATA, LogicProcess
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros
from act.core.utils.logger import log
from act.core.utils.units import g, mm2, units

DEFAULT_EPA_CONFIG = f"{ACT_ROOT}/models/logic/epa.yaml"
DEFAULT_MATERIALS_CONFIG = f"{ACT_ROOT}/models/logic/materials.yaml"
DEFAULT_GPA95_CONFIG = f"{ACT_ROOT}/models/logic/gpa_95.yaml"
DEFAULT_GPA99_CONFIG = f"{ACT_ROOT}/models/logic/gpa_99.yaml"


class LogicModel(BaseLogicModel):
    """Model for estimating carbon emissions from logic chips.

    Uses the EPA (energy per area), GPA (gas per area), and materials
    models to compute carbon per area for each process node.
    """

    REQUIRED_FIELDS = [PROCESS, AREA, FAB_YIELD, N_ICS, GPA, FAB_CI, BUILT]

    def __init__(
        self,
        epa_file=DEFAULT_EPA_CONFIG,
        materials_config=DEFAULT_MATERIALS_CONFIG,
        gpa95_file=DEFAULT_GPA95_CONFIG,
        gpa99_file=DEFAULT_GPA99_CONFIG,
        ci_model=None,
        use_legacy=False,
    ) -> None:
        self.use_legacy = use_legacy
        self.materials_config = materials_config
        self.epa_file = epa_file
        self.gpa95_file = gpa95_file
        self.gpa99_file = gpa99_file
        self.ci_model = (
            ci_model if ci_model is not None else CIModel(use_legacy=self.use_legacy)
        )

        self.epa_model = {
            LogicProcess(k): units(v)
            for k, v in load_yaml_with_macros(self.epa_file, delete_macros=True).items()
        }

        self.materials_model = {
            LogicProcess(k): units(v)
            for k, v in load_yaml_with_macros(
                self.materials_config, delete_macros=True
            ).items()
        }

        self.gpa_model = dict()
        self.gpa_model[AbatementLevel.GPA95] = {
            LogicProcess(k): units(v)
            for k, v in load_yaml_with_macros(
                self.gpa95_file, delete_macros=True
            ).items()
        }
        self.gpa_model[AbatementLevel.GPA99] = {
            LogicProcess(k): units(v)
            for k, v in load_yaml_with_macros(
                self.gpa99_file, delete_macros=True
            ).items()
        }
        self.gpa_model[AbatementLevel.GPA97] = {
            key: (
                self.gpa_model[AbatementLevel.GPA95][key]
                + self.gpa_model[AbatementLevel.GPA99][key]
            )
            / 2.0
            for key in self.gpa_model[AbatementLevel.GPA95].keys()
        }

    def get_cpa(
        self,
        process: LogicProcess,
        fab_yield: float = DEFAULT_FAB_YIELD,
        gpa=AbatementLevel.GPA97,
        fab_ci=DEFAULT_FAB_LOCATION,
        year=DEFAULT_BUILD_YEAR,
        **kwargs,
    ) -> pint.Quantity:
        """Get carbon per area from EPA + GPA + materials models."""
        if gpa not in AbatementLevel:
            log.error(f"Abatement level {gpa} not recognized...")
            exit(-1)

        ci = self.ci_model.get_ci(fab_ci, year=year)

        carbon_energy = ci * self.epa_model[process]
        carbon_gas = self.gpa_model[gpa][process]
        carbon_materials = self.materials_model[process]

        carbon_per_area = carbon_energy + carbon_gas + carbon_materials
        carbon_per_area = carbon_per_area / fab_yield

        return carbon_per_area

    def get_carbon(self, device_data) -> Carbon:
        """Get total carbon for a logic device using EPA+GPA+materials."""
        self.validate_data(device_data)

        if self.is_process_supported(device_data.process):
            process = device_data.process
        elif device_data.process is LogicProcess.NA:
            return Carbon(0 * g, SourceType.OTHER)
        else:
            process = self.get_closest_supported_process(device_data.process)

        area = device_data.area
        fab_yield = device_data.fab_yield
        n_ics = device_data.n_ics
        gpa = device_data.gpa
        fab_ci = device_data.fab_ci
        year = device_data.built

        assert area.check(mm2)

        if process not in self.epa_model:
            log.error(f"Logic process {process} not found in EPA model.")
            exit(-1)
        if process not in self.gpa_model[gpa]:
            log.error(f"Logic process {process} not found in GPA model.")
            exit(-1)
        if process not in self.materials_model:
            log.error(f"Logic process {process} not found in materials model.")
            exit(-1)

        cpa = self.get_cpa(
            process=process, fab_yield=fab_yield, gpa=gpa, fab_ci=fab_ci, year=year
        )
        carbon = Carbon(area * cpa, SourceType.FABRICATION) + Carbon(
            n_ics * CARBON_PER_IC_PACKAGE, SourceType.PACKAGING
        )
        return carbon

    def is_process_supported(self, process: LogicProcess) -> bool:
        return (
            process in self.materials_model
            and process in self.epa_model
            and process in self.gpa_model[AbatementLevel.GPA95]
            and process in self.gpa_model[AbatementLevel.GPA99]
        )

    def supported_processes(self) -> set:
        return set(self.epa_model.keys())

    def get_closest_supported_process(self, process: LogicProcess) -> LogicProcess:
        """Find the closest supported process (preserves legacy behavior)."""
        process_year = LOGIC_DATA[process].year
        closest_delta = float("inf")
        closest_process = None

        for p in self.epa_model:
            p_year = LOGIC_DATA[process].year
            if p_year is None or process_year is None:
                continue
            if p_year <= process_year:
                delta = abs(p_year - process_year)
                if closest_process is None or delta < closest_delta:
                    closest_process, closest_delta = p, delta

        if closest_process is None:
            supported = list(self.epa_model.keys())
            if supported:
                closest_process = supported[0]

        assert closest_process is not None
        return closest_process

    def get_carbon_energy(
        self, process: LogicProcess, fab_ci=DEFAULT_FAB_LOCATION
    ) -> pint.Quantity:
        return self.ci_model.get_ci(fab_ci) * self.epa_model[process]

    def get_carbon_gas(
        self, process: LogicProcess, gpa=AbatementLevel.GPA97
    ) -> pint.Quantity:
        return self.gpa_model[gpa][process]

    def get_carbon_materials(self, process: LogicProcess) -> pint.Quantity:
        return self.materials_model[process]
