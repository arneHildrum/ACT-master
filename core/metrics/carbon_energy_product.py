# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.metrics.base_metric import BaseMetric
from act.core.utils.units import J, kg


class CarbonEnergyProduct(BaseMetric):
    """Carbon energy product optimization metric.

    This metric calculates the product of carbon emissions and energy consumption,
    useful for optimizing the trade-off between carbon footprint and energy usage.
    """

    NAME = "Carbon Energy Product"

    def calculate(self):
        """Calculate the carbon energy product.

        Returns:
            pint.Quantity: The product of carbon emissions and energy consumption (kg*J).
        """
        energy = (
            self.act_model.op_power
            * self.act_model.life_cycle
            * self.act_model.duty_cycle
        )
        carbon = self.act_model.results.total_carbon.total()
        value = carbon * energy

        # dimensional analysis check
        assert value.check(kg * J)

        return value
