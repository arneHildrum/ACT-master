# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.carbon import Carbon, SourceType
from act.core.common import ACT_ROOT
from act.core.device_data import AREA, LAYERS
from act.core.models.base_model import BaseModel
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros
from act.core.utils.logger import log
from act.core.utils.units import mm2, units

DEFAULT_PCB_MODEL_FILE = f"{ACT_ROOT}/models/materials/pcb.yaml"

INTERPOLATED_AVERAGE_KEY = "cpla"


class PCBModel(BaseModel):
    """Model for estimating carbon emissions from printed circuit boards.

    This model calculates embodied carbon for PCBs based on area and
    number of layers.

    Attributes:
        model (dict): Carbon per area by number of layers.
        interpolated_cpla (pint.Quantity): Default carbon per layer per area for interpolation.
    """

    MODEL_NAME = "pcb"
    REQUIRED_FIELDS = [AREA, LAYERS]

    def __init__(self, model_file: str = DEFAULT_PCB_MODEL_FILE):
        """Initialize the PCB Model.

        Args:
            model_file (str): Path to the PCB model configuration file.
        """
        self.model_file = model_file
        model_data = load_yaml_with_macros(self.model_file, delete_macros=True)

        self.model = {k: units(v) for k, v in model_data.items()}
        if INTERPOLATED_AVERAGE_KEY in self.model:
            self.interpolated_cpla = self.model[INTERPOLATED_AVERAGE_KEY]
            del self.model[INTERPOLATED_AVERAGE_KEY]
        else:
            log.warn(
                "PCB model does not have a default interpolated average carbon / area / layer. If an unregistered number of layers is provided, the model will throw an error."
            )
            self.interpolated_cpla = None

    def get_carbon(self, device_data):
        """Calculate the carbon emissions for a PCB.

        Args:
            device_data (DeviceData): Device data containing area and layers.

        Returns:
            Carbon: The total carbon emissions for the PCB.

        Raises:
            AssertionError: If the area is not in units of area.
            SystemExit: If no model exists for the number of layers.
        """
        self.validate_data(device_data)

        area = device_data.area
        layers = device_data.layers

        assert area.check(mm2), f"Expected area units for PCB model but got {area}"

        # if the CPA for the number of layers is provided, use it directly
        if layers in self.model:
            cpa = self.model[layers]
        elif self.interpolated_cpla is not None:  # otherwise interpolate
            cpa = self.interpolated_cpla * layers
        else:  # otherwise exit
            log.critical(
                f"No PCB model for number of layers {layers} and not default carbon per area per layer provided. Cannot continue."
            )
            exit(-1)

        c = cpa * area
        return Carbon(c, SourceType.FABRICATION)
