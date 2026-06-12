# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.metrics.base_metric import BaseMetric
from act.core.utils.units import J, kg


class CarbonEnergySquaredProduct(BaseMetric):
    """Carbon energy squared product optimization metric.

    This metric calculates the product of carbon emissions and energy squared,
    useful for optimizing scenarios where energy efficiency is heavily weighted.
    """

    NAME = "Carbon Energy Squared Product"

    def calculate(self):
        """Calculate the carbon energy squared product.

        Returns:
            pint.Quantity: The product of carbon emissions and energy squared (kg*J^2).
        """
        energy = (
            self.act_model.op_power
            * self.act_model.life_cycle
            * self.act_model.duty_cycle
        )
        carbon = self.act_model.results.total_carbon.total()
        value = carbon * energy * energy

        # dimensional analysis check
        assert value.check(kg * J * J)

        return value
