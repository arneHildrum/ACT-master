# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.carbon import Carbon, SourceType
from act.core.common import ACT_ROOT
from act.core.device_data import CAPACITY
from act.core.models.base_model import BaseModel
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros
from act.core.utils.logger import log
from act.core.utils.units import kg, kWh, units

DEFAULT_BATTERY_CONFIG = f"{ACT_ROOT}/models/battery/battery.yaml"

# default battery type if none is specified
DEFAULT_BATTERY_TYPE = "NMC"


class BatteryModel(BaseModel):
    """Model for estimating carbon emissions from batteries.

    This model calculates embodied carbon based on battery capacity
    and cathode chemistry type. Battery types and their carbon intensities
    are loaded from a YAML configuration file, making it easy to add
    new battery chemistries.
    """

    MODEL_NAME = "battery"
    REQUIRED_FIELDS = [CAPACITY]

    def __init__(self, model_file: str = DEFAULT_BATTERY_CONFIG) -> None:
        """Initialize the BatteryModel from a YAML config file.

        Args:
            model_file (str): Path to battery config YAML. Defaults to DEFAULT_BATTERY_CONFIG.
        """
        self.model_file = model_file
        model_data = load_yaml_with_macros(self.model_file, delete_macros=True)
        batteries_data = model_data["batteries"]

        # dynamically generate battery types from config keys
        self.battery_types = [b.upper() for b in batteries_data.keys()]

        self.model = {k.upper(): units(v) for k, v in batteries_data.items()}
        for k, v in self.model.items():
            assert v.check(kg / kWh), (
                f"Battery carbon intensity must be in units of mass/energy. Got {v} for battery type {k}."
            )

    def get_carbon(self, device_data) -> Carbon:
        """Get the estimated carbon emissions from a battery.

        Args:
            device_data (DeviceData): Device data containing battery capacity
                and optionally a type field specifying the cathode chemistry.

        Returns:
            Carbon: The total carbon emissions from the battery fabrication.
        """
        self.validate_data(device_data)

        capacity = device_data.capacity
        btype = device_data.type if device_data.type else DEFAULT_BATTERY_TYPE
        btype = btype.upper()

        if btype not in self.model:
            log.error(
                "Battery type '%s' not found in config. Available types: %s. Using default '%s'.",
                btype,
                self.battery_types,
                DEFAULT_BATTERY_TYPE,
            )
            btype = DEFAULT_BATTERY_TYPE

        c = Carbon(capacity * self.model[btype], SourceType.FABRICATION)
        return c
