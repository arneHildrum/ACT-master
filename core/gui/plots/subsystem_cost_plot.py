# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.plots.base_act_plot import BaseACTPlot
from act.core.utils.units import dollar


class SubsystemCostPlot(BaseACTPlot):
    """
    Plot the cost emissions breakdown by subsystem hierarchy in a sunburst chart.

    This visualization creates a sunburst chart that shows the distribution of cost
    emissions across different subsystems in the system hierarchy. The chart displays
    hierarchical data with the total emissions at the center, subsystem categories in
    the middle rings, and individual devices in the outer ring.

    Each segment's size represents the relative cost contribution, making it easy to
    identify which subsystems and specific components contribute most significantly
    to the overall cost footprint of the system.

    The hierarchical visualization allows users to understand how cost emissions are
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
        total_cost = self.get_total_cost()
        label = "Total<br>" + self.cost_as_str(total_cost)
        return label

    def get_subsystem_cost(self, subsys_path):
        """
        Calculate the total cost emissions for a specific subsystem path.

        Args:
            subsys_path (str): The subsystem path to calculate cost emissions for.

        Returns:
            Quantity: Total cost emissions for the specified subsystem with appropriate units.
        """
        total_partials = 0 * dollar
        cost_by_device = self.act.cost_analyzer.cost_by_device
        for dname, cost in cost_by_device.items():
            if subsys_path in dname:
                total_partials += cost.total
        return total_partials

    def get_subsystem_label(self, subsys_path):
        """
        Generate a formatted label for a subsystem in the sunburst chart.

        Creates a label that includes the subsystem path name, cost emissions value,
        and percentage of total emissions.

        Args:
            subsys_path (str): The subsystem path to create a label for.

        Returns:
            str: HTML-formatted label string with subsystem path, cost value, and percentage.
        """
        subsys_cost = self.get_subsystem_cost(subsys_path)
        fcost = self.cost_as_str(subsys_cost)
        fpercent = self.cost_as_percent(subsys_cost)
        label = f"{subsys_path}<br>{fcost}<br>{fpercent}"
        return label

    def get_child_label(self, name, fcost, fpercent):
        """
        Return the formatted label for a device in the sunburst chart.

        Args:
            name (str): The name of the device.
            fcost (str): Formatted string representing the cost emissions value.
            fpercent (str): Formatted string representing the percentage of total emissions.

        Returns:
            str: HTML-formatted label string with device name, cost value, and percentage.
        """
        return f"{name}<br>{fcost}<br>{fpercent}"

    def make_sunburst_data(self):
        """
        Generate data for the subsystem hierarchy sunburst visualization.

        This method creates a hierarchical data structure for the sunburst chart that represents
        the nested structure of subsystems in the system. It identifies all subsystem paths from
        device names, creates appropriate labels, and calculates values for each segment.
        """
        top_node = self.get_top_node_label()
        total_cost = self.get_total_cost()

        children = [""]
        parents = [top_node]
        values = [0]

        # generate all of the subsystem paths
        subsys_paths = set()
        cost_by_device = self.act.cost_analyzer.cost_by_device
        for dname in cost_by_device:
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

        # for each device add the child and sector cost
        for dname, cost in cost_by_device.items():
            path_tokens = dname.split(".")
            parent_path = ".".join(path_tokens[:-1])

            if (
                parent_path == ""
            ):  # if this is the top level, the parent is the top node
                parent_label = top_node
            else:
                parent_label = subsys_labels[parent_path]

            cost = cost.total
            fcost = self.cost_as_str(cost)
            fpercent = self.cost_as_percent(cost, total_cost)
            child_label = self.get_child_label(dname, fcost, fpercent)
            sector_cost = cost.to(self.cost_unit).m
            children.append(child_label)
            parents.append(parent_label)
            values.append(sector_cost)

        data = {"children": children, "parents": parents, "values": values}
        return data, None

    def plot(self):
        super().plot(title=f"Cost ($) by Subsystem ({self.fcost_unit})")
