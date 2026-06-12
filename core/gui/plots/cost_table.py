# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from math import isclose

from act.core.gui.plots.base_table import BaseTable
from act.core.utils.units import dollar


class CostTable(BaseTable):
    """A table that displays cost breakdown by device.

    This table shows operational costs (opex), manufacturing costs (capex),
    and carbon offset costs for each device in the system.
    """

    def __init__(self, act, *args, cost_unit=dollar, **kwargs):
        """Initialize the Cost Table.

        Args:
            act (ACTModel): The ACT analysis object containing cost data.
            *args: Additional positional arguments passed to BaseTable.
            cost_unit (pint.Quantity): Unit for cost display. Defaults to dollar.
            **kwargs: Additional keyword arguments passed to BaseTable.
        """
        self.act = act
        self.cost_unit = cost_unit
        self.fcost_unit = format(cost_unit.units, "~")
        super().__init__(*args, **kwargs)
        self.plot()

    def plot(self):
        """Populate the table with cost data by device.

        Sets up the table header and populates rows with cost breakdown
        for each device including opex, capex, and offset costs.
        """
        self.header = [
            "Device",
            "Cost",
            "Operational Cost<br>(Opex)",
            "Operation Offset Cost",
            "Manufacturing Cost<br>(Capex)",
            "Embodied Offset Cost",
        ]

        def fcost(cost):
            if isclose(cost.m, 0):
                return "-"
            else:
                return f"{cost.to(self.cost_unit).m:.2f} " + self.fcost_unit

        cost_by_device = self.act.cost_analyzer.cost_by_device
        for dname in sorted(cost_by_device):
            result = cost_by_device[dname]
            dataline = [
                dname,
                fcost(result.total),
                fcost(result.opex),
                fcost(result.opex_offset),
                fcost(result.capex),
                fcost(result.capex_offset),
            ]
            self.data.append(dataline)
