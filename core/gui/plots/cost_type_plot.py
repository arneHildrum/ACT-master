# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import random

from act.core.gui.plots.base_act_plot import BaseACTPlot
from act.core.gui.style import MODEL_TYPE_COLOR_MAP
from act.core.utils.units import dollar


class CostTypePlot(BaseACTPlot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plot()

    def get_top_node_label(self):
        """Return the label name for the top node in the chart"""
        total_cost = self.get_total_cost()
        label = "Total<br>" + self.cost_as_str(total_cost)
        return label

    def get_category_cost(self, fx):
        """Return the total cost for this source type in units of cost"""
        total_partials = 0 * dollar

        for v in self.act.cost_analyzer.cost_by_device.values():
            total_partials += fx(v)
        return total_partials

    def get_category_label(self, cname, fx):
        """Return the label for the category source type sector"""
        cat_cost = self.get_category_cost(fx=fx)
        fcost = self.cost_as_str(cat_cost)
        fpercent = self.cost_as_percent(cat_cost)
        label = f"{cname}<br>{fcost}<br>{fpercent}"
        return label

    def get_child_label(self, name, ctype, fcost, fpercent):
        """
        Return the formatted label for a device in the sunburst chart.

        Args:
            name (str): The name of the device.
            stype (SourceType): The source type of the device.
            fcost (str): Formatted string representing the cost emissions value.
            fpercent (str): Formatted string representing the percentage of total emissions.

        Returns:
            str: HTML-formatted label string with device name, cost value, percentage, and source type.
        """
        return f"{name}<br>{fcost}<br>{fpercent}<br>({ctype.title()})"

    def make_sunburst_data(self):
        """
        Generate data for the source type sunburst visualization.

        This method creates a hierarchical data structure for the sunburst chart with:
        - The total emissions at the center
        - Source type categories in the middle ring
        - Individual devices in the outer ring

        It pre-computes category labels and then populates child sectors with device-specific
        cost emission data, formatting labels with appropriate cost values and percentages.
        Each segment is color-coded according to its source type using the COLOR_MAP.

        Returns:
            tuple: A tuple containing:
                - dict: Data dictionary with 'children', 'parents', and 'values' keys
                   for the sunburst chart hierarchy
                - list: List of colors for the sunburst segments based on source types
        """
        # Get the top node label for the center of the sunburst
        top_node = self.get_top_node_label()
        total_cost = self.get_total_cost()

        fx_opex = lambda x: x.opex
        fx_opex_offset = lambda x: x.opex_offset
        fx_capex = lambda x: x.capex
        fx_capex_offset = lambda x: x.capex_offset
        categories = {
            "Opex": fx_opex,
            "Opex Offsets": fx_opex_offset,
            "Capex": fx_capex,
            "Capex Offsets": fx_capex_offset,
        }
        color_map = {
            k: random.choice(list(MODEL_TYPE_COLOR_MAP.values())) for k in categories
        }

        # construct the first level categorical hierarchy with zero cost
        children = [""] + [self.get_category_label(k, v) for k, v in categories.items()]
        colors = ["white"] + [color_map[k] for k in categories]
        parents = [top_node] * len(children)
        values = [0] * len(children)

        # generate the second level child nodes where power by category for each device is instantiated across the categories
        cost_by_device = self.act.cost_analyzer.cost_by_device

        # process operational cost
        for ctype, fx in categories.items():
            category_label = self.get_category_label(cname=ctype, fx=fx)
            color = color_map[ctype]
            for dname, cost in cost_by_device.items():
                partial = fx(cost)
                sector_cost = partial.to(self.cost_unit).m
                fcost = self.cost_as_str(partial)
                fpercent = self.cost_as_percent(partial, total_cost)
                child_label = self.get_child_label(dname, ctype, fcost, fpercent)
                parent_label = category_label

                colors.append(color)
                parents.append(parent_label)
                values.append(sector_cost)
                children.append(child_label)

        data = {"children": children, "parents": parents, "values": values}
        return data, colors

    def plot(self):
        super().plot(title=f"Cost by Expenditure Type ({self.fcost_unit})")
