# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.card import Card
from act.core.gui.plots.category_cost_plot import CategoryCostPlot
from act.core.gui.plots.cost_table import CostTable
from act.core.gui.plots.cost_type_plot import CostTypePlot
from act.core.gui.plots.subsystem_cost_plot import SubsystemCostPlot


class CostCard(Card):
    """A card that displays cost analysis results.

    This card presents cost breakdowns including:
    1. Cost by device category
    2. Cost by subsystem
    3. Cost by type (capex, opex, offset)
    4. Detailed cost table by device
    """

    def __init__(self, act, *args, **kwargs):
        """Initialize the Cost Card.

        Args:
            act (ACTModel): The ACT analysis object containing cost analysis results.
            *args: Additional positional arguments passed to parent Card class.
            **kwargs: Additional keyword arguments passed to parent Card class.
        """
        self.act = act
        super().__init__(
            id="cost-card-id",
            title="Cost",
            *args,
            **kwargs,
            content=self.generate_content(),
        )

    def generate_content(self):
        """Generate the HTML content for the Cost Card.

        Creates cost visualizations including category, subsystem, and type breakdowns,
        along with a detailed cost table.

        Returns:
            str: HTML content for the card body containing all cost visualizations.
        """
        # self.device_cost_plot = DeviceCostPlot(act=self.act)
        self.category_cost_plot = CategoryCostPlot(act=self.act)
        self.subsystem_cost_plot = SubsystemCostPlot(act=self.act)
        self.cost_type_plot = CostTypePlot(act=self.act)
        self.cost_table = CostTable(act=self.act)

        cost_per_kwhr = self.act.cost_analyzer.cost_per_kwhr
        offset_cost = self.act.cost_analyzer.offset_cost

        content = f"""
            <div class="row">
                <center> <h3>Cost ($) Breakdown View </h3> </center>
                <div class="column", style="width: 33%">
                <center>
                    {self.category_cost_plot.get_html()}
                </center>
                </div>
                <div class="column", style="width: 33%">
                <center>
                    {self.subsystem_cost_plot.get_html()}
                </center>
                </div>
                <div class="column", style="width: 33%">
                <center>
                    {self.cost_type_plot.get_html()}
                </center>
                </div>
            </div>
            <p> Note: Assumes electrical cost at {cost_per_kwhr} and carbon emissions offset cost of {offset_cost}. </p>

            <hr style="height: 20px">

            <center><h3> Detailed Cost by Device View </h3></center>
            <center>{self.cost_table.get_html()}</center>
            <p> Note: Devices without cost specification will not report capex costs. Device which do not consume power will not have opex and opex offset costs. </p>

        """

        return content
