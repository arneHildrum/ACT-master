# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import pint
from act.core.carbon import Carbon, SourceType
from act.core.common import ACT_ROOT, CARBON_PER_IC_PACKAGE
from act.core.processes import LogicProcess
from act.core.utils.units import units

DEFAULT_AP_CONFIG = f"{ACT_ROOT}/models/logic/ap_model.yaml"
from act.core.device_data import AREA, FAB_YIELD, N_ICS, PROCESS
from act.core.models.base_model import BaseModel
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros


class APModel(BaseModel):
    """
    A model for estimating carbon emissions from application processors (APs).
    Attributes:
        model (dict): A dictionary mapping LogicProcess to carbon per area cost.
    """

    MODEL_NAME = "ap"
    REQUIRED_FIELDS = [AREA, PROCESS, FAB_YIELD, N_ICS]

    def __init__(self, model_file: str = DEFAULT_AP_CONFIG) -> None:
        """
        Initializes a new instance of the APModel class.
        Loads the AP model from a YAML file.
        Args:
            model_file (str, optional): The path to the AP model file. Defaults to DEFAULT_AP_CONFIG.
        """
        self.model_file = model_file
        data = load_yaml_with_macros(model_file, delete_macros=True)
        self.model: dict[LogicProcess, pint.Quantity] = {
            LogicProcess(k): units(v) for k, v in data.items()
        }
        super().__init__()

    def get_carbon(self, device_data) -> Carbon:
        """
        Get the estimated carbon emissions from an AP based on its area, process, fabrication yield, and number of ICs.
        Args:
            area (pint.Quantity): The area of the AP.
            process (LogicProcess): The logic process used to manufacture the AP.
            fab_yield (float): The fabrication yield.
            n_ics (int, optional): The number of ICs. Defaults to 0.
        Returns:
            Carbon: The total carbon emissions from the AP fabrication and packaging.
        Raises:
            AssertionError: If the fabrication yield is not greater than 0 and less than or equal to 1.0.
        """
        self.validate_data(device_data)

        area = device_data.area
        process = device_data.process
        fab_yield = device_data.fab_yield
        n_ics = device_data.n_ics

        assert 0.0 < fab_yield <= 1.0, (
            f"Fab yield must be greater than 0 and <= 1.0. Got {fab_yield}"
        )
        cpa = self.model[process]
        fab_amt = (cpa * area) / fab_yield
        pkg_amt = n_ics * CARBON_PER_IC_PACKAGE / fab_yield
        return Carbon(fab_amt, SourceType.FABRICATION) + Carbon(
            pkg_amt, SourceType.PACKAGING
        )
