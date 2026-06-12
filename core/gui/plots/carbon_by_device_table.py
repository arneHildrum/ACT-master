# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from math import isclose

from act.core.carbon import SourceType
from act.core.gui.plots.base_table import BaseTable
from act.core.utils.units import kg


class CarbonByDeviceTable(BaseTable):
    """
    A table that displays carbon emissions breakdown by device and source type.

    This table presents detailed carbon emissions data for each device in the system,
    showing both the total carbon footprint and the breakdown by different source types
    (e.g., Packaging, Materials, Operation, etc.). Each row represents a device, and
    columns show carbon values for different emission sources.

    The table provides a comprehensive view of which devices contribute most significantly
    to the system's carbon footprint and from which sources their emissions primarily come,
    allowing for targeted optimization of high-impact components.
    """

    def __init__(self, act, *args, weight_unit=kg, **kwargs):
        """
        Initialize the Carbon By Device Table with ACT analysis data.

        Args:
            act: The ACT analysis object containing carbon emissions results data
                 broken down by device and source type.
            *args: Variable length argument list passed to BaseTable.
            weight_unit (Unit, optional): The unit to use for displaying carbon weight values.
                Defaults to kilograms (kg).
            **kwargs: Arbitrary keyword arguments passed to BaseTable.

        The constructor initializes the table with the provided ACT analysis object and
        weight unit preference, then immediately calls plot() to populate the table data
        with carbon emissions information for each device.
        """
        self.act = act
        self.weight_unit = weight_unit
        super().__init__(*args, **kwargs)
        self.plot()

    def plot(self):
        """
        Populate the table with carbon emissions data by device and source type.

        This method:
        1. Sets up the table header with columns for device name, total carbon,
           and carbon by each source type
        2. Formats the weight unit for display in column headers
        3. Iterates through all devices in the carbon results
        4. For each device, extracts and formats its total carbon emissions and
           the breakdown by source type
        5. Adds each device's data as a row in the table
        """

        fweight_unit = "(" + format(self.weight_unit.units, "~") + ")"
        self.header = ["Device", f"Total<br>{fweight_unit}"] + [
            t.name.title() + f"<br>{fweight_unit}" for t in SourceType
        ]

        carbon_by_device = self.act.results.carbon_by_device
        for dname in sorted(carbon_by_device):
            carbon = carbon_by_device[dname]
            data_entry = [dname, "%.2f" % carbon.total().to(self.weight_unit).m]

            for t in SourceType:
                partial_val = carbon.partial(t).to(self.weight_unit).m
                if isclose(partial_val, 0):
                    data_entry.append("-")
                else:
                    data_entry.append("%.2f" % carbon.partial(t).to(self.weight_unit).m)
            self.data.append(data_entry)
