# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.card import Card
from act.core.gui.plots.delta_carbon_barchart import DeltaCarbonBarchart
from act.core.gui.plots.delta_carbon_table import DeltaCarbonTable
from act.core.gui.plots.source_plot import SourcePlot
from act.core.gui.style import DeltaCardLayout, get_column_class


class DeltaOverviewCard(Card):
    """
    A card that displays carbon emissions delta comparison overview.
    """

    def __init__(self, base_sim, delta_sims):
        """
        Initialize the Delta Overview Card.

        Args:
            base_sim: The baseline ACT simulation object
            delta_sims: List of experiment ACT simulation objects to compare against baseline
        """
        self.base_sim = base_sim
        self.delta_sims = delta_sims
        self.sunburst_plot = None
        self.barchart_plot = None
        self.table_plot = None
        super().__init__(
            id="delta-overview-card-id",
            title="Emissions",
            content=self.generate_content(),
        )

    def generate_content(self):
        """
        Generate the HTML content for the Delta Overview Card.

        Creates visualizations showing carbon emissions by source type for all simulations:
        1. Row of sunburst charts - One SourcePlot for each simulation (baseline + experiments)
        2. Bar chart - Full-width carbon emissions delta comparison
        3. Table - Detailed numerical breakdown of carbon emissions differences

        Returns:
            str: HTML content for the card body containing all visualizations.
        """
        # Create SourcePlot sunburst charts for all simulations
        all_sims = [self.base_sim] + self.delta_sims
        sunburst_plots = []

        for _i, sim in enumerate(all_sims):
            if sim is not None:
                source_plot = SourcePlot(act=sim)
                sunburst_plots.append(source_plot)

        # Create other plots
        self.barchart_plot = DeltaCarbonBarchart(self.base_sim, self.delta_sims)
        self.table_plot = DeltaCarbonTable(self.base_sim, self.delta_sims)

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
                <center><h4>Carbon Emissions by Device Category</h4></center>
                {sunburst_html}
            </div>

            {DeltaCardLayout.HORIZONTAL_DIVIDER}

            <div class="row">
                <div class="col-md-12">
                    <center><h4>Carbon Emissions Difference</h4></center>
                    <div class="plot-container">
                        {self.barchart_plot.get_html()}
                    </div>
                </div>
            </div>

            {DeltaCardLayout.HORIZONTAL_DIVIDER}

            <div class="row">
                <center><h4>Carbon Emissions Delta Details</h4></center>
                {self.table_plot.get_html()}
            </div>
        """
        return content
