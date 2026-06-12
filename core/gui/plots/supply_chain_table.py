# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.plots.base_table import BaseTable
from act.core.utils.units import g, kg, kWh


class SupplyChainTable(BaseTable):
    def __init__(self, act, *args, weight_unit=kg, **kwargs):
        self.act = act
        self.weight_unit = weight_unit
        super().__init__(*args, **kwargs)
        self.plot()

    def plot(self):
        self.header = [
            "Device",
            "Carbon (" + format(self.weight_unit.units, "~") + ")",
            "Year Built",
            "Manufacturing<br>Location",
            "Manufacturing<br>Carbon Intensity",
            "Yield",
            "Operating Year",
            "Operating Location",
            "Operating<br>Carbon Intensity",
        ]

        for dname in sorted(self.act.bom.devices):
            data = self.act.bom.devices[dname]
            fcarbon = "%.2f" % self.act.results.carbon_by_device[dname].total().to(kg).m
            fab_ci = self.act.ci_model.get_ci(
                loc_or_src=data.fab_ci, year=data.built
            ).to(g / kWh)
            ffab_ci = "%.2f " % fab_ci.m + format(fab_ci.units, "~")

            op_ci = self.act.ci_model.get_ci(
                loc_or_src=data.op_ci, year=data.op_year
            ).to(g / kWh)
            fop_ci = "%.2f" % op_ci.m + format(op_ci.units, "~")

            self.data.append(
                [
                    dname,
                    fcarbon,
                    data.built,
                    data.fab_ci,
                    ffab_ci,
                    data.fab_yield,
                    data.op_year,
                    data.op_ci,
                    fop_ci,
                ]
            )
