# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.card import Card
from act.core.gui.plots.carbon_by_device_table import CarbonByDeviceTable
from act.core.gui.plots.category_carbon_plot import CategoryCarbonPlot
from act.core.gui.plots.op_carbon_table import OpCarbonTable
from act.core.gui.plots.source_plot import SourcePlot
from act.core.gui.plots.subsystem_carbon_plot import SubsystemCarbonPlot


class CarbonCard(Card):
    """
    A card that provides an overview of the carbon emissions analysis results.

    This card presents four visualizations:
    1. Total Emissions by Source - Shows emissions broken down by source categories
    2. Operational Emissions by Device Category - Displays operational emissions by device type
    3. Emissions by Subsystem - Presents emissions organized by subsystem components
    4. Detailed Carbon by Device - A table showing detailed carbon data for each device

    These visualizations give users a comprehensive overview of the carbon footprint
    from different perspectives.
    """

    HAS_PLOT = True
    HAS_TABLE = True

    def __init__(self, act):
        """
        Initialize the Carbon Card.

        Args:
            act: The ACT analysis object containing results data used to generate
                 the overview plots and tables showing carbon emissions from
                 different perspectives.
        """
        self.act = act
        self.carbon_results = act.results.carbon_by_device
        super().__init__(
            id="carbon-card-id", title="Carbon", content=self.generate_content()
        )

    def generate_content(self):
        """
        Generate the HTML content for the Carbon Card.

        Creates four visualizations:
        - Source Plot: Shows emissions by source category
        - Device Plot: Shows operational emissions by device category
        - Subsystem Plot: Shows emissions by subsystem
        - Carbon by Device Table: Detailed breakdown of carbon by device

        Returns:
            str: HTML content for the card body containing all visualizations
                arranged in a responsive layout.
        """
        self.source_plot = SourcePlot(self.act)
        self.category_carbon_plot = CategoryCarbonPlot(self.act)
        self.subsystem_carbon_plot = SubsystemCarbonPlot(act=self.act)
        self.carbon_by_device_table = CarbonByDeviceTable(act=self.act)
        self.op_carbon_table = OpCarbonTable(act=self.act)

        content = f"""
            <center><h3> Carbon Emissions Breakdown View </h3></center>
            <div class="row">
                <div class="column" style="width: 33%">
                    <center>
                        {self.source_plot.get_html()}
                    </center>
                </div>
                <div class="column" style="width: 33%">
                    <center>
                        {self.category_carbon_plot.get_html()}
                    </center>
                </div>
                <div class="column" style="width: 33%">
                    <center>
                        {self.subsystem_carbon_plot.get_html()}
                    </center>
                </div>
            </div>

            <hr style="height: 20px">

            <div class="row">
                <center><h3>Detailed Carbon by Source View</h3></center>
                {self.carbon_by_device_table.get_html()}
            </div>

            <hr style="height: 20px">

            <div class="row">
                <center><h3>Detailed Operational Carbon View</h3></center>
                {self.op_carbon_table.get_html()}
            </div>

        """

        return content
