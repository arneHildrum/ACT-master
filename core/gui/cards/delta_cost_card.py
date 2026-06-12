# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.card import Card
from act.core.gui.plots.category_cost_plot import CategoryCostPlot
from act.core.gui.plots.delta_cost_barchart import DeltaCostBarchart
from act.core.gui.plots.delta_cost_table import DeltaCostTable
from act.core.gui.style import DeltaCardLayout, get_column_class


class DeltaCostCard(Card):
    """
    A card that displays cost delta comparison overview.
    """

    def __init__(self, base_sim, delta_sims):
        """
        Initialize the Delta Cost Card.

        Args:
            base_sim: The baseline ACT simulation object
            delta_sims: List of experiment ACT simulation objects to compare against baseline
        """
        self.base_sim = base_sim
        self.delta_sims = delta_sims
        self.sunburst_plots = None
        self.barchart_plot = None
        self.table_plot = None
        super().__init__(
            id="delta-cost-card-id",
            title="Cost",
            content=self.generate_content(),
        )

    def generate_content(self):
        """
        Generate the HTML content for the Delta Cost Card.

        Creates visualizations showing cost by source type for all simulations:
        1. Row of sunburst charts - One CategoryCostPlot for each simulation (baseline + experiments)
        2. Bar chart - Full-width cost delta comparison
        3. Table - Detailed numerical breakdown of cost differences

        Returns:
            str: HTML content for the card body containing all visualizations.
        """
        # Create CategoryCostPlot sunburst charts for all simulations
        all_sims = [self.base_sim] + self.delta_sims
        sunburst_plots = []

        for _i, sim in enumerate(all_sims):
            if sim is not None:
                cost_plot = CategoryCostPlot(act=sim)
                sunburst_plots.append(cost_plot)

        # Create other plots
        self.barchart_plot = DeltaCostBarchart(self.base_sim, self.delta_sims)
        self.table_plot = DeltaCostTable(self.base_sim, self.delta_sims)

        # Calculate column width based on number of simulations using centralized styling
        num_sims = len(sunburst_plots)
        col_class = get_column_class(num_sims)

        # Generate sunburst charts row
        sunburst_html = ""
        for i, plot in enumerate(sunburst_plots):
            sim_name = "Baseline" if i == 0 else f"Experiment {i}"
            sunburst_html += f"""
                <div class="{col_class}">
                    <center><h5>{sim_name}</h5></center>
                    <div class="plot-container">
                        {plot.get_html()}
                    </div>
                </div>
            """

        content = f"""
            <div class="row">
                <center><h4>Cost by Device Category</h4></center>
                {sunburst_html}
            </div>

            {DeltaCardLayout.HORIZONTAL_DIVIDER}

            <div class="row">
                <div class="col-md-12">
                    <center><h4>Cost Difference</h4></center>
                    <div class="plot-container">
                        {self.barchart_plot.get_html()}
                    </div>
                </div>
            </div>

            {DeltaCardLayout.HORIZONTAL_DIVIDER}

            <div class="row">
                <center><h4>Cost Delta Details</h4></center>
                {self.table_plot.get_html()}
            </div>
        """
        return content
