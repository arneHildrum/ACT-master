# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.plots.base_table import BaseTable
from act.core.utils.units import mW


class BOMTable(BaseTable):
    """
    A table that displays Bill of Materials (BOM) information for the analyzed system.

    This table presents key metadata about the system's bill of materials, including
    the BOM name, description, macros, file path, operating power, and operating
    location.

    The BOM information is fundamental to the carbon analysis as it defines the
    components and configuration of the system being analyzed. This table
    provides a concise overview of the system configuration that forms
    the basis of the carbon analysis.

    The table is formatted with two columns: "Field" and "Value", making it easy to
    read and understand the system's basic configuration parameters.
    """

    def __init__(
        self,
        act,
        *args,
        power_unit=mW,
        **kwargs,
    ):
        """
        Initialize the BOM Table with ACT analysis data.

        Args:
            act: The ACT analysis object containing the bill of materials and
                 operating power information.
            *args: Variable length argument list passed to BaseTable.
            power_unit (Unit, optional): The unit to use for displaying power values.
                Defaults to milliwatts (mW).
            **kwargs: Arbitrary keyword arguments passed to BaseTable.

        The constructor initializes the table with the provided ACT analysis object and
        configuration options, then immediately calls plot() to populate the table data.
        """
        self.act = act
        self.power_unit = power_unit
        super().__init__(*args, **kwargs)
        self.plot()

    def plot(self):
        """
        Populate the table with BOM information data.

        This method sets up the table header with "Field" and "Value" columns,
        and populates the data dictionary with key information about the bill of materials,
        including:
        - BOM name and description
        - Macro definitions used in the BOM
        - File path to the BOM source
        - System operating power and location
        """
        self.header = ["Field", "Value"]

        self.data_dict = {
            "Name": self.act.bom.name,
            "Description": self.act.bom.description,
            "Macros": "<br>".join([f"{k}: {v}" for k, v in self.act.bom.macros.items()])
            if self.act.bom.macros is not None
            else "-",
            "File Path": self.act.bom.file,
        }

    def get_html(self):
        """
        Generate the HTML representation of the BOM table.

        Overrides the parent class method to apply left alignment to all columns
        in the table for better readability of the BOM information.

        Returns:
            str: HTML representation of the table with left-aligned columns.
        """
        return super().get_html(align={k: "l" for k in self.header})
