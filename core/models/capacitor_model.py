# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import pint
from act.core.carbon import Carbon, SourceType
from act.core.common import ACT_ROOT, CapacitorType
from act.core.device_data import BUILT, FAB_CI, N_ICS, TYPE, WEIGHT
from act.core.models.base_model import BaseModel
from act.core.models.ci_model import CIModel
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros
from act.core.utils.units import units

DEFAULT_CP_CONFIG = f"{ACT_ROOT}/models/passives/capacitors.yaml"


class CapacitorModel(BaseModel):
    """
    A model for estimating carbon emissions from capacitors.
    Attributes:
        capacitor_model (dict): A dictionary mapping CapacitorType to units of carbon per weight.
        ci_model: The ci model for carbon intensity values.
    """

    MODEL_NAME = "capacitor"
    REQUIRED_FIELDS = [FAB_CI, TYPE, WEIGHT, N_ICS, BUILT]

    def __init__(
        self, model_file=DEFAULT_CP_CONFIG, ci_model=None, use_legacy=False
    ) -> None:
        """
        Initializes a new instance of the CapacitorModel class.
        Loads the capacitor model and carbon intensity model from YAML files.
        Args:
            model_file: Capacitor model file to load

        """
        self.capacitor_model: dict[CapacitorType, pint.Quantity] = {
            CapacitorType(c): units(v)
            for c, v in load_yaml_with_macros(model_file, delete_macros=True).items()
        }
        self.use_legacy = use_legacy
        self.ci_model = (
            ci_model if ci_model is not None else CIModel(use_legacy=use_legacy)
        )

    def get_carbon(self, device_data) -> Carbon:
        """
        Get the carbon emissions cost based on the capacitor type and weight of the capacitor.
        Args:
            ci (str): Carbon intensity per manufacturing energy.
            ctype (CapacitorType): The capacitor type (MLCC or TEC).
            weight (pint.Quantity): Weight of the capacitor.
            n_caps (int, optional): Number of capacitors. Defaults to 1.
        Returns:
            Carbon: A carbon object that encodes the emissions cost of manufacturing.
        """
        self.validate_data(device_data)

        ci = device_data.fab_ci
        ctype = device_data.type
        weight = device_data.weight
        n_caps = device_data.n_ics
        year = device_data.built

        _ci = self.ci_model.get_ci(ci, year=year)
        c = Carbon(
            self.capacitor_model[ctype] * weight * n_caps * _ci,
            SourceType.PASSIVES,
        )
        return c
