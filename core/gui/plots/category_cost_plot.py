# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.common import ModelType
from act.core.gui.plots.base_act_plot import BaseACTPlot
from act.core.gui.style import get_model_type_color, MODEL_TYPE_COLOR_MAP
from act.core.utils.units import dollar


class CategoryCostPlot(BaseACTPlot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plot()

    def get_top_node_label(self):
        total_cost = self.get_total_cost()
        label = "Total<br>" + self.cost_as_str(total_cost)
        return label

    def get_category_cost(self, cost_category):
        total = 0 * dollar
        for dname, cost_result in self.act.cost_analyzer.cost_by_device.items():
            dev_type = self.bom.devices[dname].model
            if dev_type is cost_category:
                total += cost_result.total
        return total

    def get_category_label(self, dtype):
        cat_cost = self.get_category_cost(dtype)
        fcost = self.cost_as_str(cat_cost)
        fpercent = self.cost_as_percent(cat_cost)
        label = f"{dtype.name.title()}<br>{fcost}<br>{fpercent}"
        return label

    def get_child_label(self, name, fcost, fpercent):
        return f"{name}<br>{fcost}<br>{fpercent}"

    def make_sunburst_data(self):
        top_node = self.get_top_node_label()
        total_cost = self.get_total_cost()

        category_label = {
            cost_category: self.get_category_label(cost_category)
            for cost_category in ModelType
        }

        children = [""] + list(category_label.values())
        colors = ["white"] + list(MODEL_TYPE_COLOR_MAP.values())
        parents = [top_node] * len(children)
        values = [0] * len(children)

        # populate the child sectors
        cost_by_device = self.act.cost_analyzer.cost_by_device
        for dname, cost in cost_by_device.items():
            device = self.bom.devices[dname]
            category = device.model

            cost = cost_by_device[dname].total
            fcost = self.cost_as_str(cost)
            fpercent = self.cost_as_percent(cost, total_cost)
            child_label = self.get_child_label(dname, fcost, fpercent)
            parent_label = category_label[category]

            parents.append(parent_label)
            colors.append(get_model_type_color(category))
            values.append(cost.to(self.cost_unit).m)
            children.append(child_label)

        data = {"children": children, "parents": parents, "values": values}
        return data, colors

    def plot(self):
        super().plot(title=f"Cost by Device Category ({self.fcost_unit})")
