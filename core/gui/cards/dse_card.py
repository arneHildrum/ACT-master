# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.card import Card
from act.core.gui.plots.scaling_plots import (
    CIIncPlot,
    CILatestPlot,
    TSIncPlot,
    TSLatestPlot,
)


class DSECard(Card):
    """A card that displays Design Space Exploration (DSE) results.

    This card presents carbon emissions projections over time using both
    carbon intensity scaling and technology node scaling approaches.
    """

    def __init__(self, dse_manager):
        """Initialize the DSE Card.

        Args:
            dse_manager (DSEManager): The DSE manager containing projection results.
        """
        self.dse_manager = dse_manager
        super().__init__(id="dse-card-id", title="DSE", content=self.generate_content())

    def generate_content(self):
        """Generate the HTML content for the DSE Card.

        Creates four projection plots:
        - CI incremental: Carbon intensity projection by year increments
        - CI latest: Carbon intensity projection by absolute year
        - TS incremental: Technology scaling projection by year increments
        - TS latest: Technology scaling projection by absolute year

        Returns:
            str: HTML content for the card body containing all DSE visualizations.
        """
        self.ci_inc_plot = CIIncPlot(dse_manager=self.dse_manager)
        self.ci_latest_plot = CILatestPlot(dse_manager=self.dse_manager)
        self.ts_inc_plot = TSIncPlot(dse_manager=self.dse_manager)
        self.ts_latest_plot = TSLatestPlot(dse_manager=self.dse_manager)

        content = f"""
        <center><h3>Iso-Technology Node Carbon Emissions Projection Over Time </h3></center>

        <div class="row">
            <div class = "column" style="width: 50%">
                <center><h4>Projection by Year Increments</h4></center>
                {self.ci_inc_plot.get_html()}

                <p>Increments the CI year relative to the original manufacture date for each device. If device A is built in 2023 and device B is built in 2021, a delta of +2 projects projects the carbon if A was built in 2023+2=2025 and B was build in 2021+2=2023.</p>
            </div>
            <div class = "column" style="width: 50%">
                <center><h4>Projection by Absolute Year</h4></center>
                {self.ci_latest_plot.get_html()}

                <p>Adjusts the CI year to the same year for all devices. If device A is built in 2023 and device B is built in 2021, the projection for year 2025 will adjust the CI for the manufacturing year as if A and B are both built in 2025.</p>
            </div>

        </div>

        <center><h3>Iso-Carbon Intensity Technology Scaling Projection Over Time </h3></center>
        <div class="row">
            <div class = "column" style="width: 50%">
                <center><h4>Projection by Year Increments</h4></center>
                {self.ts_inc_plot.get_html()}

                <p>Increments the technology node relative to the original manufacturing year for each device. If device A is built in 2021, the projection for +2 years will choose the closest existing technology node for 2021+2=2023. Only applies the technology scaling to logic nodes.</p>
            </div>
            <div class = "column" style="width: 50%">
                <center><h4>Projection by Absolute Year</h4></center>
                {self.ts_latest_plot.get_html()}

                <p>Set the technology node for all devices to the most bleeding edge available node. Only applies the technology scaling to logic nodes.</p>
            </div>
        </div>
        """

        return content
