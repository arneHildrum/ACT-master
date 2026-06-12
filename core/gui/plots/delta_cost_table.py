# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.common import ModelType
from act.core.gui.plots.base_table import BaseTable
from act.core.utils.units import dollar


class DeltaCostTable(BaseTable):
    """
    A table showing detailed cost delta comparison data.

    This table displays numerical cost differences between baseline
    and experiment simulations, providing detailed breakdowns by subsystem,
    device, and experiment for precise analysis.
    """

    def __init__(self, base_sim, delta_sims, decimal_places=2):
        """
        Initialize the Delta Cost Table.

        Args:
            base_sim: The baseline ACT simulation object
            delta_sims: List of experiment ACT simulation objects to compare against baseline
            decimal_places (int): Number of decimal places for cost values
        """
        self.base_sim = base_sim
        self.delta_sims = delta_sims
        self.decimal_places = decimal_places
        self.cost_unit = dollar
        self.fcost_unit = "USD"

        super().__init__()

        if self.base_sim and self.delta_sims:
            self.plot()

    def get_cost_by_device(self, sim):
        """
        Get cost breakdown by device for a simulation.

        Args:
            sim: ACT simulation object

        Returns:
            dict: Dictionary mapping device name to cost values
        """
        if (
            not sim
            or not hasattr(sim, "cost_analyzer")
            or not hasattr(sim.cost_analyzer, "cost_by_device")
        ):
            return {}

        cost_by_device = {}
        for dname, cost_result in sim.cost_analyzer.cost_by_device.items():
            cost_by_device[dname] = cost_result.total.to(self.cost_unit)
        return cost_by_device

    def get_cost_by_subsystem(self, sim):
        """
        Get cost breakdown by subsystem (model type) for a simulation.

        Args:
            sim: ACT simulation object

        Returns:
            dict: Dictionary mapping ModelType to cost values
        """
        if (
            not sim
            or not hasattr(sim, "cost_analyzer")
            or not hasattr(sim.cost_analyzer, "cost_by_device")
        ):
            return {}

        cost_by_subsystem = {}
        for model_type in ModelType:
            total_cost = 0 * self.cost_unit
            for dname, cost_result in sim.cost_analyzer.cost_by_device.items():
                if hasattr(sim, "bom") and sim.bom and dname in sim.bom.devices:
                    device = sim.bom.devices[dname]
                    if device.model == model_type:
                        total_cost += cost_result.total.to(self.cost_unit)
            cost_by_subsystem[model_type] = total_cost
        return cost_by_subsystem

    def plot(self):
        """
        Populate the table with cost delta data.
        """
        # Set up table header
        self.header = ["Device", f"Baseline ({self.fcost_unit})"]

        # Add experiment columns
        for i, _ in enumerate(self.delta_sims):
            self.header.extend(
                [
                    f"Experiment {i + 1} ({self.fcost_unit})",
                    f"Delta {i + 1} ({self.fcost_unit})",
                    f"Delta {i + 1} (%)",
                ]
            )

        # Get baseline cost data
        baseline_device_costs = self.get_cost_by_device(self.base_sim)
        baseline_subsystem_costs = self.get_cost_by_subsystem(self.base_sim)

        # Add subsystem summary rows first
        for model_type in ModelType:
            baseline_cost = baseline_subsystem_costs[model_type]

            # Skip subsystems with zero cost
            if baseline_cost.m == 0:
                continue

            row = [
                f"[{model_type.name.title()}] Total",
                f"{baseline_cost.m:.{self.decimal_places}f}",
            ]

            # Add experiment data for this subsystem
            for _i, delta_sim in enumerate(self.delta_sims):
                if delta_sim is not None:
                    delta_subsystem_costs = self.get_cost_by_subsystem(delta_sim)
                    delta_cost = delta_subsystem_costs[model_type]
                    difference = delta_cost - baseline_cost
                    percent_change = (
                        (difference.m / baseline_cost.m * 100)
                        if baseline_cost.m != 0
                        else 0
                    )

                    row.extend(
                        [
                            f"{delta_cost.m:.{self.decimal_places}f}",
                            f"{difference.m:+.{self.decimal_places}f}",
                            f"{percent_change:.1f}%",
                        ]
                    )

            self.data.append(row)

        # Add individual device rows grouped by subsystem
        for model_type in ModelType:
            devices_in_subsystem = []
            for dname, device in self.base_sim.bom.devices.items():
                if device.model == model_type and dname in baseline_device_costs:
                    devices_in_subsystem.append(dname)

            # Sort devices within subsystem
            for dname in sorted(devices_in_subsystem):
                baseline_cost = baseline_device_costs[dname]

                # Skip devices with near-zero cost
                if abs(baseline_cost.m) < 1e-5:
                    continue

                row = [
                    f"  {dname}",  # Indent device names
                    f"{baseline_cost.m:.{self.decimal_places}f}",
                ]

                # Add experiment data for this device
                for _i, delta_sim in enumerate(self.delta_sims):
                    if delta_sim is not None:
                        delta_device_costs = self.get_cost_by_device(delta_sim)
                        delta_cost = delta_device_costs.get(dname, 0 * self.cost_unit)
                        difference = delta_cost - baseline_cost
                        percent_change = (
                            (difference.m / baseline_cost.m * 100)
                            if baseline_cost.m != 0
                            else 0
                        )

                        row.extend(
                            [
                                f"{delta_cost.m:.{self.decimal_places}f}",
                                f"{difference.m:+.{self.decimal_places}f}",
                                f"{percent_change:.1f}%",
                            ]
                        )

                self.data.append(row)
