# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.carbon import SourceType
from act.core.gui.plots.base_act_plot import BaseACTPlot
from act.core.gui.style import get_source_type_color, SOURCE_TYPE_COLOR_MAP
from act.core.utils.units import kg


class SourcePlot(BaseACTPlot):
    """
    Plot the carbon emissions breakdown by source type in a sunburst chart.

    This visualization creates a sunburst chart that shows the distribution of carbon
    emissions across different source types (e.g., Packaging, Materials, Operation, etc.)
    in the system. The chart displays hierarchical data with the total emissions at the center,
    source categories in the middle ring, and individual devices in the outer ring.

    Each segment's size represents the relative carbon contribution, making it easy to
    identify which source types and specific components contribute most significantly
    to the overall carbon footprint of the system.

    The color coding of different source types (e.g., blue for Packaging, orange for Materials)
    makes it easy to visually distinguish between different categories and quickly identify
    which source types are the major contributors to the system's carbon footprint.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the SourcePlot visualization.

        Args:
            *args: Variable length argument list passed to BaseACTPlot.
                  Should include the ACT analysis object.
            **kwargs: Arbitrary keyword arguments passed to BaseACTPlot.
                      May include configuration options for the plot.

        The constructor initializes the SourcePlot visualization with the provided ACT analysis
        object and configuration options. It sets up the necessary data structures for the plot
        by calling the parent class constructor with the provided arguments and keyword arguments,
        and then immediately generates the plot visualization.
        """
        super().__init__(*args, **kwargs)
        self.plot()

    def get_top_node_label(self):
        """Return the label name for the top node in the chart"""
        total_weight = self.get_total_carbon_weight()
        label = "Total<br>" + self.weight_as_str(total_weight)
        return label

    def get_category_carbon(self, stype: SourceType):
        """Return the total carbon for this source type in units of weight"""
        total_partials = 0 * kg
        for _k, v in self.carbon_results.items():
            total_partials += v.partial(stype)
        return total_partials

    def get_category_label(self, stype):
        """Return the label for the category source type sector"""
        cat_carbon = self.get_category_carbon(stype)
        fcarbon = self.weight_as_str(cat_carbon)
        fpercent = self.weight_as_percent(cat_carbon)
        label = f"{stype.name}<br>{fcarbon}<br>{fpercent}"
        return label

    def get_child_label(self, name, stype, fcarbon, fpercent):
        """
        Return the formatted label for a device in the sunburst chart.

        Args:
            name (str): The name of the device.
            stype (SourceType): The source type of the device.
            fcarbon (str): Formatted string representing the carbon emissions value.
            fpercent (str): Formatted string representing the percentage of total emissions.

        Returns:
            str: HTML-formatted label string with device name, carbon value, percentage, and source type.
        """
        return f"{name}<br>{fcarbon}<br>{fpercent}<br>({stype.name.title()})"

    def make_sunburst_data(self):
        """
        Generate data for the source type sunburst visualization.

        This method creates a hierarchical data structure for the sunburst chart with:
        - The total emissions at the center
        - Source type categories in the middle ring
        - Individual devices in the outer ring

        It pre-computes category labels and then populates child sectors with device-specific
        carbon emission data, formatting labels with appropriate carbon values and percentages.
        Each segment is color-coded according to its source type using the COLOR_MAP.

        Returns:
            tuple: A tuple containing:
                - dict: Data dictionary with 'children', 'parents', and 'values' keys
                   for the sunburst chart hierarchy
                - list: List of colors for the sunburst segments based on source types
        """
        # Get the top node label for the center of the sunburst
        top_node = self.get_top_node_label()
        total_carbon = self.get_total_carbon_weight()

        category_labels = {
            stype: self.get_category_label(stype) for stype in SourceType
        }

        # construct the first level categorical hierarchy with zero weight
        children = [""] + list(category_labels.values())
        colors = ["white"] + list(SOURCE_TYPE_COLOR_MAP.values())
        parents = [top_node] * len(children)
        values = [0] * len(children)

        # generate the second level child nodes where power by category for each device is instantiated across the categories
        for dname, carbon in self.carbon_results.items():
            for stype in SourceType:
                partial = carbon.partial(stype)
                sector_weight = partial.to(self.weight_unit).m
                fcarbon = self.weight_as_str(partial)
                fpercent = self.weight_as_percent(partial, total_carbon)
                child_label = self.get_child_label(dname, stype, fcarbon, fpercent)
                parent_label = category_labels[stype]

                parents.append(parent_label)
                colors.append(get_source_type_color(stype))
                values.append(sector_weight)
                children.append(child_label)

        data = {"children": children, "parents": parents, "values": values}
        return data, colors

    def plot(self):
        """
        Generate the source type sunburst plot.

        Creates a sunburst visualization showing the hierarchical breakdown of carbon
        emissions by source type. The plot displays the total emissions at the center,
        source type categories in the middle ring, and individual devices in the outer ring.

        The plot title includes the weight unit used for carbon measurements (e.g., kg CO2e),
        and the visualization is configured with appropriate layout settings from the
        parent class's plot method.
        """
        super().plot(title=f"Carbon Emissions by Source Type ({self.fweight_unit})")
