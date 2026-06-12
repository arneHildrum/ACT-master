# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.common import ModelType
from act.core.gui.plots.base_table import BaseTable
from act.core.utils.units import kg


class DeltaCarbonTable(BaseTable):
    """
    A table showing detailed carbon emissions delta comparison data.

    This table displays numerical carbon emissions differences between baseline
    and experiment simulations, providing detailed breakdowns by subsystem,
    device, and experiment for precise analysis.
    """

    def __init__(self, base_sim, delta_sims, decimal_places=2):
        """
        Initialize the Delta Carbon Table.

        Args:
            base_sim: The baseline ACT simulation object
            delta_sims: List of experiment ACT simulation objects to compare against baseline
            decimal_places (int): Number of decimal places for carbon values
        """
        self.base_sim = base_sim
        self.delta_sims = delta_sims
        self.decimal_places = decimal_places
        self.carbon_unit = kg
        self.fcarbon_unit = format(self.carbon_unit.units, "~")

        super().__init__()

        if self.base_sim and self.delta_sims:
            self.plot()

    def get_carbon_by_device(self, sim):
        """
        Get carbon breakdown by device for a simulation.

        Args:
            sim: ACT simulation object

        Returns:
            dict: Dictionary mapping device name to carbon values
        """
        if (
            not sim
            or not hasattr(sim, "results")
            or not hasattr(sim.results, "carbon_by_device")
        ):
            return {}

        carbon_by_device = {}
        for dname, carbon_result in sim.results.carbon_by_device.items():
            carbon_by_device[dname] = carbon_result.total().to(self.carbon_unit)
        return carbon_by_device

    def get_carbon_by_subsystem(self, sim):
        """
        Get carbon breakdown by subsystem (model type) for a simulation.

        Args:
            sim: ACT simulation object

        Returns:
            dict: Dictionary mapping ModelType to carbon values
        """
        if (
            not sim
            or not hasattr(sim, "results")
            or not hasattr(sim.results, "carbon_by_device")
        ):
            return {}

        carbon_by_subsystem = {}
        for model_type in ModelType:
            total_carbon = 0 * self.carbon_unit
            for dname, carbon_result in sim.results.carbon_by_device.items():
                if hasattr(sim, "bom") and sim.bom and dname in sim.bom.devices:
                    device = sim.bom.devices[dname]
                    if device.model == model_type:
                        total_carbon += carbon_result.total().to(self.carbon_unit)
            carbon_by_subsystem[model_type] = total_carbon
        return carbon_by_subsystem

    def plot(self):
        """
        Populate the table with carbon emissions delta data.
        """
        # Set up table header
        self.header = ["Device", f"Baseline ({self.fcarbon_unit})"]

        # Add experiment columns
        for i, _ in enumerate(self.delta_sims):
            self.header.extend(
                [
                    f"Experiment {i + 1} ({self.fcarbon_unit})",
                    f"Delta {i + 1} ({self.fcarbon_unit})",
                    f"Delta {i + 1} (%)",
                ]
            )

        # Get baseline carbon data
        baseline_device_carbon = self.get_carbon_by_device(self.base_sim)
        baseline_subsystem_carbon = self.get_carbon_by_subsystem(self.base_sim)

        # Add subsystem summary rows first
        for model_type in ModelType:
            baseline_carbon = baseline_subsystem_carbon[model_type]

            # Skip subsystems with zero carbon
            if baseline_carbon.m == 0:
                continue

            row = [
                f"[{model_type.name.title()}] Total",
                f"{baseline_carbon.m:.{self.decimal_places}f}",
            ]

            # Add experiment data for this subsystem
            for _i, delta_sim in enumerate(self.delta_sims):
                if delta_sim is not None:
                    delta_subsystem_carbon = self.get_carbon_by_subsystem(delta_sim)
                    delta_carbon = delta_subsystem_carbon[model_type]
                    difference = delta_carbon - baseline_carbon
                    percent_change = (
                        (difference.m / baseline_carbon.m * 100)
                        if baseline_carbon.m != 0
                        else 0
                    )

                    row.extend(
                        [
                            f"{delta_carbon.m:.{self.decimal_places}f}",
                            f"{difference.m:+.{self.decimal_places}f}",
                            f"{percent_change:.1f}%",
                        ]
                    )

            self.data.append(row)

        # Add individual device rows grouped by subsystem
        for model_type in ModelType:
            devices_in_subsystem = []
            for dname, device in self.base_sim.bom.devices.items():
                if device.model == model_type and dname in baseline_device_carbon:
                    devices_in_subsystem.append(dname)

            # Sort devices within subsystem
            for dname in sorted(devices_in_subsystem):
                baseline_carbon = baseline_device_carbon[dname]

                # Skip devices with near-zero carbon
                if abs(baseline_carbon.m) < 1e-5:
                    continue

                row = [
                    f"  {dname}",  # Indent device names
                    f"{baseline_carbon.m:.{self.decimal_places}f}",
                ]

                # Add experiment data for this device
                for _i, delta_sim in enumerate(self.delta_sims):
                    if delta_sim is not None:
                        delta_device_carbon = self.get_carbon_by_device(delta_sim)
                        delta_carbon = delta_device_carbon.get(
                            dname, 0 * self.carbon_unit
                        )
                        difference = delta_carbon - baseline_carbon
                        percent_change = (
                            (difference.m / baseline_carbon.m * 100)
                            if baseline_carbon.m != 0
                            else 0
                        )

                        row.extend(
                            [
                                f"{delta_carbon.m:.{self.decimal_places}f}",
                                f"{difference.m:+.{self.decimal_places}f}",
                                f"{percent_change:.1f}%",
                            ]
                        )

                self.data.append(row)
