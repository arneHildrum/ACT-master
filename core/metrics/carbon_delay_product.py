# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.metrics.base_metric import BaseMetric
from act.core.utils.units import kg, s


class CarbonDelayProduct(BaseMetric):
    """Carbon delay product optimization metric.

    This metric calculates the product of carbon emissions and device lifetime,
    useful for optimizing the trade-off between carbon footprint and longevity.
    """

    NAME = "Carbon Delay Product"

    def calculate(self):
        """Calculate the carbon delay product.

        Returns:
            pint.Quantity: The product of carbon emissions and device lifetime (kg*s).
        """
        delay = self.act_model.life_cycle
        carbon = self.act_model.results.total_carbon.total()
        value = delay * carbon

        # dimensional analysis check
        assert value.check(kg * s)

        return value
