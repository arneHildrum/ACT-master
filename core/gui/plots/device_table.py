# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.plots.base_table import BaseTable
from act.core.utils.units import kg, kWh, MB, mm2, mW


class DeviceTable(BaseTable):
    """
    A table that displays detailed device information for carbon analysis.

    This table presents comprehensive information about each device in the system,
    including physical characteristics (area, weight), technical specifications
    (process, layers), manufacturing details (fab yield, location), and carbon
    footprint data.

    The table includes details such as:
    - Device model type and number of ICs
    - Manufacturing information (process, year built, fab yield, location)
    - Physical attributes (area, size, weight)
    - Technical specifications (type, layers)
    - Carbon footprint and battery capacity data

    The table organizes devices alphabetically by name and formats
    measurements with appropriate units.
    """

    def __init__(
        self,
        act,
        *args,
        weight_unit=kg,
        area_unit=mm2,
        size_unit=MB,
        capacity_unit=kWh,
        power_unit=mW,
        **kwargs,
    ):
        """
        Initialize the Device Table with ACT analysis data and unit preferences for measurements.

        Args:
            act: The ACT analysis object containing the bill of materials with
                 device information to be displayed in the table.
            *args: Variable length argument list passed to BaseTable.
            weight_unit (Unit, optional): The unit to use for displaying weight and
                carbon values. Defaults to kilograms (kg).
            area_unit (Unit, optional): The unit to use for displaying device area.
                Defaults to square millimeters (mm²).
            size_unit (Unit, optional): The unit to use for displaying memory size.
                Defaults to megabytes (MB).
            capacity_unit (Unit, optional): The unit to use for displaying battery
                capacity. Defaults to kilowatt-hours (kWh).
            **kwargs: Arbitrary keyword arguments passed to BaseTable.

        The constructor stores the ACT analysis object and unit preferences as instance
        variables, initializes the base table structure by calling the parent class
        constructor, and then populates the table with device data by calling plot().

        The constructor initializes the table with the provided ACT analysis object
        and unit preferences, then immediately calls plot() to populate the table data.
        """
        self.act = act
        self.weight_unit = weight_unit
        self.area_unit = area_unit
        self.size_unit = size_unit
        self.capacity_unit = capacity_unit
        self.power_unit = power_unit
        super().__init__(*args, **kwargs)
        self.plot()

    def plot(self):
        """
        Populate the table with device information data.

        This method:
        1. Sets up the table header with columns for device attributes
        2. Formats the unit labels for display in column headers
        3. Iterates through all devices in the bill of materials
        4. For each device, extracts and formats its attributes
        5. Adds each device's data as a row in the table

        The table includes columns for:
        - Device name and model type
        - Manufacturing details (process, year, yield, location)
        - Physical characteristics (area, size, weight)
        - Technical specifications (type, layers)
        - Carbon footprint and battery capacity
        - Number of integrated circuits
        """
        fweight_unit = format(self.weight_unit.units, "~")
        farea_unit = format(self.area_unit.units, "~")
        fsize_unit = format(self.size_unit.units, "~")
        fcap_unit = format(self.capacity_unit.units, "~")
        fpower_unit = format(self.power_unit.units, "~")

        self.header = [
            "Device",
            "Model Type",
            "# ICs",
            "Process",
            "Year Built",
            "Fab Yield",
            "Fab Location",
            f"Area<br>({farea_unit})",
            f"Size<br>({fsize_unit})",
            "Type",
            f"Weight<br>({fweight_unit})",
            f"Capacity<br>({fcap_unit})",
            f"Manual Carbon<br>({fweight_unit})",
            "Layers",
            f"Power ({fpower_unit})",
            "Op CI",
            "Op Year",
            "Lifetime",
            "Duty Cycle",
        ]

        for dname in sorted(self.act.bom.devices):
            data = self.act.bom.devices[dname]

            table_entry = [
                dname,
                data.model.name,
                data.n_ics,
                data.process.name,
                data.built,
                data.fab_yield,
                data.fab_ci,
                "%.2f" % data.area.to(self.area_unit).m
                if data.area is not None
                else "-",  # area
                "%.2f" % data.size.to(self.size_unit).m
                if data.size is not None
                else "-",  # size
                data.type if data.type is not None else "-",
                "%.2f" % data.weight.to(self.weight_unit).m
                if data.weight is not None
                else "-",  # weight
                "%.2f" % data.capacity.to(self.capacity_unit).m
                if data.capacity is not None
                else "-",  # battery capacity
                "%.2f" % data.carbon.to(self.weight_unit).m
                if data.carbon is not None
                else "-",  # manual weight
                data.layers if data.layers is not None else "-",
                "%.2f" % data.power.to(self.power_unit).m
                if data.power is not None
                else "-",
                data.op_ci,
                data.op_year if data.op_year is not None else "-",
                str(data.life_cycle) if data.life_cycle is not None else "-",
                data.duty_cycle if data.duty_cycle is not None else "-",
            ]
            assert len(table_entry) == len(self.header)
            self.data.append(table_entry)
