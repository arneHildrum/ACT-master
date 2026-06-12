# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.metrics.base_metric import BaseMetric
from act.core.utils.units import J, kg


class CarbonSquaredEnergyProduct(BaseMetric):
    """Carbon squared energy product optimization metric.

    This metric calculates the product of carbon squared and energy consumption,
    useful for optimizing scenarios where carbon reduction is heavily weighted.
    """

    NAME = "Carbon Squared Energy Product"

    def calculate(self):
        """Calculate the carbon squared energy product.

        Returns:
            pint.Quantity: The product of carbon squared and energy (kg^2*J).
        """
        energy = (
            self.act_model.op_power
            * self.act_model.life_cycle
            * self.act_model.duty_cycle
        )
        carbon = self.act_model.results.total_carbon.total()
        value = carbon * carbon * energy

        # dimensional analysis check
        assert value.check(kg * kg * J)

        return value
