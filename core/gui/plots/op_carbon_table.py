# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.plots.base_table import BaseTable
from act.core.utils.units import dollar, kg, kWh, mW


class OpCarbonTable(BaseTable):
    def __init__(
        self, act, *args, weight_unit=kg, power_unit=mW, cost_unit=dollar, **kwargs
    ):
        self.act = act
        self.weight_unit = weight_unit
        self.cost_unit = cost_unit
        self.power_unit = power_unit
        super().__init__(*args, **kwargs)
        self.plot()

    def plot(self):
        def uformat(quant, unit):
            m = "%.2f" % quant.to(unit).m
            u = format(unit.units, "~")
            return f"{m} {u}"

        fcost_unit = format(self.cost_unit.units, "~")
        fpower_unit = format(self.power_unit.units, "~")
        self.header = [
            "Device",
            f"Power<br>{fpower_unit}",
            "Duty Cycle",
            "Life Cycle",
            "Op Location",
            "Op CI",
            "Op Year",
            f"Total Opex Cost<br>({fcost_unit})",
            f"Opex Cost<br>({fcost_unit})",
            f"Opex Offset<br>({fcost_unit})",
            "Cost / kWh",
        ]

        cost_per_kwhr = self.act.cost_analyzer.cost_per_kwhr

        for dname in sorted(self.act.bom.devices):
            dev = self.act.bom.devices[dname]
            dev_cost = self.act.cost_analyzer.cost_by_device[dname]
            data_line = [
                dname,
                uformat(dev.power, self.power_unit),
                dev.duty_cycle,
                dev.life_cycle,
                dev.op_ci,
                uformat(self.act.ci_model.get_ci(dev.op_ci, dev.op_year), kg / kWh),
                dev.op_year,
                uformat(dev_cost.opex + dev_cost.opex_offset, self.cost_unit),
                uformat(dev_cost.opex, self.cost_unit),
                uformat(dev_cost.opex_offset, self.cost_unit),
                uformat(cost_per_kwhr, dollar / kWh),
            ]
            assert len(data_line) == len(self.header)
            self.data.append(data_line)
