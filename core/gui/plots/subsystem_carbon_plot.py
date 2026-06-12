# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.plots.base_act_plot import BaseACTPlot
from act.core.utils.units import kg


class SubsystemCarbonPlot(BaseACTPlot):
    """
    Plot the carbon emissions breakdown by subsystem hierarchy in a sunburst chart.

    This visualization creates a sunburst chart that shows the distribution of carbon
    emissions across different subsystems in the system hierarchy. The chart displays
    hierarchical data with the total emissions at the center, subsystem categories in
    the middle rings, and individual devices in the outer ring.

    Each segment's size represents the relative carbon contribution, making it easy to
    identify which subsystems and specific components contribute most significantly
    to the overall carbon footprint of the system.

    The hierarchical visualization allows users to understand how carbon emissions are
    distributed across different levels of the system architecture.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the SubsystemPlot visualization.

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
        """Return the label name for the top node in the chart"""
        total_weight = self.get_total_carbon_weight()
        label = "Total<br>" + self.weight_as_str(total_weight)
        return label

    def get_subsystem_carbon(self, subsys_path):
        """
        Calculate the total carbon emissions for a specific subsystem path.

        Args:
            subsys_path (str): The subsystem path to calculate carbon emissions for.

        Returns:
            Quantity: Total carbon emissions for the specified subsystem with appropriate units.
        """
        total_partials = 0 * kg
        for dname, carbon in self.carbon_results.items():
            if subsys_path in dname:
                total_partials += carbon.total()
        return total_partials

    def get_subsystem_label(self, subsys_path):
        """
        Generate a formatted label for a subsystem in the sunburst chart.

        Creates a label that includes the subsystem path name, carbon emissions value,
        and percentage of total emissions.

        Args:
            subsys_path (str): The subsystem path to create a label for.

        Returns:
            str: HTML-formatted label string with subsystem path, carbon value, and percentage.
        """
        subsys_carbon = self.get_subsystem_carbon(subsys_path)
        fcarbon = self.weight_as_str(subsys_carbon)
        fpercent = self.weight_as_percent(subsys_carbon)
        label = f"{subsys_path}<br>{fcarbon}<br>{fpercent}"
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
        Generate data for the subsystem hierarchy sunburst visualization.

        This method creates a hierarchical data structure for the sunburst chart that represents
        the nested structure of subsystems in the system. It identifies all subsystem paths from
        device names, creates appropriate labels, and calculates values for each segment.
        """
        top_node = self.get_top_node_label()
        total_weight = self.get_total_carbon_weight()

        children = [""]
        parents = [top_node]
        values = [0]

        # generate all of the subsystem paths
        subsys_paths = set()
        for dname in self.carbon_results:
            path_tokens = dname.split(".")

            # glob all the subsys paths in the device path to handle edge case
            for x in range(1, len(path_tokens)):
                subsys_path = ".".join(path_tokens[:-x])
                subsys_paths.add(subsys_path)
        ordered_paths = sorted(list(subsys_paths))
        subsys_labels = {path: self.get_subsystem_label(path) for path in ordered_paths}

        # for each path, set the parent to the proper subsystem path label
        for path in ordered_paths:
            child_label = subsys_labels[path]
            path_tokens = path.split(".")
            parent_path = ".".join(path_tokens[:-1])
            if (
                parent_path == ""
            ):  # if this is the top level, the parent is the top node
                parent_label = top_node
            else:
                parent_label = subsys_labels[parent_path]

            children.append(child_label)
            parents.append(parent_label)
            values.append(0)

        # for each device add the child and sector weight
        for dname, carbon in self.carbon_results.items():
            path_tokens = dname.split(".")
            parent_path = ".".join(path_tokens[:-1])

            if (
                parent_path == ""
            ):  # if this is the top level, the parent is the top node
                parent_label = top_node
            else:
                parent_label = subsys_labels[parent_path]

            weight = carbon.total()
            fweight = self.weight_as_str(weight)
            fpercent = self.weight_as_percent(weight, total_weight)
            child_label = self.get_child_label(dname, fweight, fpercent)
            sector_weight = weight.to(self.weight_unit).m
            children.append(child_label)
            parents.append(parent_label)
            values.append(sector_weight)

        data = {"children": children, "parents": parents, "values": values}
        return data, None

    def plot(self):
        """
        Generate the subsystem hierarchy sunburst plot.

        Creates a sunburst visualization showing the hierarchical breakdown of carbon
        emissions by subsystem. The plot displays the total emissions at the center,
        subsystem categories in the middle rings, and individual devices in the outer ring.

        The plot title includes the weight unit used for carbon measurements (e.g., kg CO2e),
        and the visualization is configured with appropriate layout settings.
        """
        super().plot(title=f"Carbon Emissions by Subsystem ({self.fweight_unit})")
