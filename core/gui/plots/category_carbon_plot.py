# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.common import ModelType
from act.core.gui.plots.base_act_plot import BaseACTPlot
from act.core.gui.style import MODEL_TYPE_COLOR_MAP
from act.core.utils.units import kg


class CategoryCarbonPlot(BaseACTPlot):
    """
    Plot the carbon emissions breakdown by device category type.

    This visualization creates a sunburst chart that shows the distribution of carbon
    emissions across different device categories (e.g., Logic, DRAM, PCB, etc.) in the
    system. The chart displays hierarchical data with the total emissions at the center,
    device categories in the middle ring, and individual devices in the outer ring.

    Each segment's size represents the relative carbon contribution, making it easy to
    identify which device types and specific components contribute most significantly
    to the overall carbon footprint of the system.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the DevicePlot visualization.

        Args:
            *args: Variable length argument list passed to BaseACTPlot.
                  Should include the ACT analysis object.
            **kwargs: Arbitrary keyword arguments passed to BaseACTPlot.
                      May include configuration options for the plot.

        The constructor initializes the plot by calling the parent class constructor
        and then immediately generates the plot visualization.
        """
        super().__init__(*args, **kwargs)
        self.plot()

    def get_top_node_label(self):
        """
        Generate the label for the center node of the sunburst chart.

        This method calculates the total carbon weight across all devices and formats
        it into a label string for the center (top) node of the sunburst visualization.
        The label includes the word "Total" and the formatted carbon weight value.

        Returns:
            str: HTML-formatted label string with "Total" and the carbon weight value.
        """
        total_weight = self.get_total_carbon_weight()
        label = "Total<br>" + self.weight_as_str(total_weight)
        return label

    def get_category_carbon(self, power_category):
        """
        Calculate the total carbon emissions for a specific device category type.

        This method sums the carbon emissions for all devices that match the specified
        model type (power_category). It filters the carbon results to include only
        devices of the matching type before summing their total carbon values.

        Args:
            power_category (ModelType): The device model type to calculate carbon for.

        Returns:
            Quantity: Total carbon emissions for the specified device category with
                appropriate units (typically kg CO2e).
        """
        total = 0 * kg
        for dname, carbon in self.carbon_results.items():
            dev_type = self.bom.devices[dname].model
            if dev_type is power_category:
                total += carbon.total()
        return total

    def get_category_label(self, dtype):
        """
        Generate a formatted label for a device category in the sunburst chart.

        Creates a label that includes the device category type name, carbon emissions value,
        and percentage of total emissions. This label is used for the middle ring segments
        in the sunburst visualization, representing different device categories.

        Args:
            dtype (ModelType): The device model type to create a label for.

        Returns:
            str: HTML-formatted label string with category name, carbon value, and percentage.
        """
        cat_carbon = self.get_category_carbon(dtype)
        fcarbon = self.weight_as_str(cat_carbon)
        fpercent = self.weight_as_percent(cat_carbon)
        label = f"{dtype.name.title()}<br>{fcarbon}<br>{fpercent}"
        return label

    def get_child_label(self, name, fcarbon, fpercent):
        """
        Return the formatted label for a device in the sunburst chart.

        Args:
            name (str): The name of the device.
            fcarbon (str): Formatted string representing the carbon emissions value.
            fpercent (str): Formatted string representing the percentage of total emissions.

        Returns:
            str: HTML-formatted label string with device name, carbon value, and percentage.
        """
        return f"{name}<br>{fcarbon}<br>{fpercent}"

    def make_sunburst_data(self):
        """
        Generate data for the device category sunburst visualization.

        This method creates a hierarchical data structure for the sunburst chart with:
        - The total emissions at the center
        - Device categories in the middle ring
        - Individual devices in the outer ring

        It pre-computes category labels and then populates child sectors with device-specific
        carbon emission data, formatting labels with appropriate carbon values and percentages.

        Returns:
            tuple: A tuple containing:
                - dict: Data dictionary with 'children', 'parents', and 'values' keys
                - list: List of colors for the sunburst segments
        """
        # top node in the chart
        top_node = self.get_top_node_label()
        total_weight = self.get_total_carbon_weight()

        # pre-compute category labels
        category_label = {
            power_category: self.get_category_label(power_category)
            for power_category in ModelType
        }

        children = [""] + list(category_label.values())
        colors = ["white"] + list(MODEL_TYPE_COLOR_MAP.values())
        parents = [top_node] * len(children)
        values = [0] * len(children)

        # populate the child sectors
        for dname, carbon in self.carbon_results.items():
            device = self.bom.devices[dname]
            category = device.model

            weight = carbon.total()
            fcarbon = self.weight_as_str(weight)
            fpercent = self.weight_as_percent(weight, total_weight)
            child_label = self.get_child_label(dname, fcarbon, fpercent)
            parent_label = category_label[category]

            parents.append(parent_label)
            colors.append(MODEL_TYPE_COLOR_MAP[category])
            values.append(weight.to(self.weight_unit).m)
            children.append(child_label)

        data = {"children": children, "parents": parents, "values": values}
        return data, colors

    def plot(self):
        """
        Generate the device category sunburst plot.

        Creates a sunburst visualization showing the hierarchical breakdown of carbon
        emissions by device category. The plot displays the total emissions at the center,
        device categories in the middle ring, and individual devices in the outer ring.

        The plot title includes the weight unit used for carbon measurements, and the
        visualization is configured with appropriate layout settings.
        """
        super().plot(title=f"Carbon Emissions by Device Category ({self.fweight_unit})")
