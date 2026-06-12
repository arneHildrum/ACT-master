# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass

import pint
from act.core.common import DEFAULT_CARBON_OFFSET_COST, DEFAULT_ELECTRICITY_COST
from act.core.utils.units import dollar, kg, kWh, mW, ton, year

# base on 2025 data from https://www.eia.gov/electricity/monthly/epm_table_grapher.php?t=table_5_03
DEFAULT_COST_PER_KWHR = 0.0856 * dollar / kWh

# based on the 2024 number from https://carboncredits.com/carbon-credits-in-2024-what-to-expect-in-2025-and-beyond-250b-by-2050/
DEFAULT_OFFSET_COST = 4.8 * dollar / ton


@dataclass
class CostResult:
    """Data class for storing cost analysis results for a device.

    Attributes:
        dname (str): Device name.
        opex (pint.Quantity): Operational cost (electricity).
        opex_offset (pint.Quantity): Carbon offset cost for operational emissions.
        capex (pint.Quantity): Capital/manufacturing cost.
        capex_offset (pint.Quantity): Carbon offset cost for embodied emissions.
    """

    dname: str
    opex: pint.Quantity
    opex_offset: pint.Quantity
    capex: pint.Quantity  # i.e., manufacturing cost
    capex_offset: pint.Quantity

    def __post_init__(self):
        self.total = self.opex + self.opex_offset + self.capex + self.capex_offset


class CostAnalyzer:
    """Analyzer for calculating device and system costs.

    This class calculates operational costs (opex), capital costs (capex),
    and carbon offset costs for each device in the system.

    Attributes:
        act (ACTModel): The ACT model containing analysis results.
        cost_unit (pint.Quantity): Unit for cost display.
        cost_by_device (dict): Dictionary mapping device names to CostResult objects.
        cost_per_kwhr (pint.Quantity): Electricity cost per kilowatt-hour.
        offset_cost (pint.Quantity): Carbon offset cost per ton.
    """

    def __init__(self, act, cost_unit=dollar):
        """Initialize the Cost Analyzer.

        Args:
            act (ACTModel): The ACT model containing analysis results.
            cost_unit (pint.Quantity): Unit for cost display. Defaults to dollar.
        """
        self.act = act
        self.cost_unit = cost_unit
        self.cost_by_device = dict()

        self.cost_per_kwhr = self._resolve_cost_per_kwhr()
        self.offset_cost = self._resolve_offset_cost()

        self.analyze()

    def _resolve_cost_per_kwhr(self):
        """Resolve the electricity cost per kilowatt-hour.

        Returns:
            pint.Quantity: Electricity cost from BOM parameters or default.
        """
        parameters = self.act.bom.parameters
        if parameters and DEFAULT_ELECTRICITY_COST in parameters:
            from act.core.utils.units import units

            return units(parameters[DEFAULT_ELECTRICITY_COST])
        return DEFAULT_COST_PER_KWHR

    def _resolve_offset_cost(self):
        """Resolve the carbon offset cost per ton.

        Returns:
            pint.Quantity: Offset cost from BOM parameters or default.
        """
        parameters = self.act.bom.parameters
        if parameters and DEFAULT_CARBON_OFFSET_COST in parameters:
            from act.core.utils.units import units

            return units(parameters[DEFAULT_CARBON_OFFSET_COST])
        return DEFAULT_OFFSET_COST

    def get_results(self):
        """Get the cost analysis results by device.

        Returns:
            dict[str, CostResult]: Dictionary mapping device names to cost results.
        """
        return self.cost_by_device

    def analyze(self):
        """Perform cost analysis for all devices in the BOM."""
        for dname, dev in self.act.bom.devices.items():
            carbon = self.act.results.carbon_by_device[dname]
            opex = self.get_opex(dev.power, dev.life_cycle, dev.duty_cycle)
            opex_offset = self.get_offset_cost(carbon.op())
            capex_offset = self.get_offset_cost(carbon.embodied())

            self.cost_by_device[dname] = CostResult(
                dname=dname,
                opex=opex.to(self.cost_unit),
                opex_offset=opex_offset.to(self.cost_unit),
                capex=dev.cost.to(self.cost_unit),
                capex_offset=capex_offset.to(self.cost_unit),
            )

    def get_opex(
        self, power: pint.Quantity, life_cycle: pint.Quantity, duty_cycle: float
    ):
        """Calculate operational cost for a device.

        Args:
            power (pint.Quantity): Device power consumption.
            life_cycle (pint.Quantity): Device lifetime.
            duty_cycle (float): Device utilization rate.

        Returns:
            pint.Quantity: Operational cost.
        """
        assert power.check(mW)
        assert life_cycle.check(year)
        return power * life_cycle * duty_cycle * self.cost_per_kwhr

    def get_total_build_cost(self):
        """Get the total build/manufacturing cost for all devices.

        Returns:
            pint.Quantity: Total build cost.
        """
        bom = self.act_model.bom
        return sum([dev.cost for dev in bom.devices.values()])

    def get_total_cost(self):
        """Get the total cost across all devices.

        Returns:
            pint.Quantity: Total cost including opex, capex, and offsets.
        """
        return sum([x.total for x in self.cost_by_device.values()])

    def get_offset_cost(self, amt: pint.Quantity):
        """Calculate carbon offset cost for a given carbon amount.

        Args:
            amt (pint.Quantity): Carbon amount in weight units.

        Returns:
            pint.Quantity: Carbon offset cost.
        """
        assert amt.check(kg)
        return amt * self.offset_cost
