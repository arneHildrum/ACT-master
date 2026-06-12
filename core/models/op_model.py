# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.carbon import Carbon, SourceType
from act.core.device_data import DUTY_CYCLE, LIFE_CYCLE, OP_CI, OP_YEAR, POWER
from act.core.models.base_model import BaseModel
from act.core.models.ci_model import CIModel
from act.core.utils.logger import log
from act.core.utils.units import s


class OpModel(BaseModel):
    """Model for estimating operational carbon emissions.

    This model calculates carbon emissions from device operation based on
    power consumption, duty cycle, lifetime, and grid carbon intensity.

    Attributes:
        ci_model (CIModel): Carbon intensity model for energy calculations.
        use_legacy (bool): Whether to use legacy carbon intensity data.
    """

    MODEL_NAME = "op"
    REQUIRED_FIELDS = [LIFE_CYCLE, DUTY_CYCLE, POWER, OP_CI, OP_YEAR]

    def __init__(self, ci_model=None, use_legacy=False) -> None:
        """Initialize the Operation Model.

        Args:
            ci_model (CIModel): Optional pre-initialized carbon intensity model.
            use_legacy (bool): If True, use legacy carbon intensity data.
        """
        self.ci_model = ci_model if ci_model is not None else CIModel()
        self.use_legacy = use_legacy

    def get_carbon(
        self,
        device_data,
    ) -> Carbon:
        """Get the estimated carbon operation costs.

        Args:
            life_cycle (units): The estimated device life_cycle.
            duty_cycle (float): The estimated device active duty cycle.
            op_power (units): The average operating power of the device.
            op_ci (str): The carbon intensity of the energy grid for operation.
        Returns:
            Carbon: The total carbon emissions from operation.
        Raises:
            SystemExit: If the life_cycle does not have units of time.
        """
        self.validate_data(device_data)

        life_cycle = device_data.life_cycle
        duty_cycle = device_data.duty_cycle
        op_power = device_data.power
        op_ci = device_data.op_ci
        year = device_data.op_year

        if not life_cycle.check(s):
            log.error(
                f"Operating life_cycle of device must have units of time. Got {life_cycle}"
            )
            exit(-1)

        _op_ci = self.ci_model.get_ci(op_ci, year=year)

        op_time = life_cycle * duty_cycle
        carbon = _op_ci * op_power * op_time

        return Carbon(carbon, SourceType.OPERATION)
