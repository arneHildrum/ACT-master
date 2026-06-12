# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.card import Card
from act.core.gui.plots.model_configs_table import ModelConfigsTable
from act.core.gui.plots.sim_info_table import SimInfoTable


class SimInfoCard(Card):
    """
    A card that displays analysis information and model configuration details.

    This card presents two tables:
    1. Sim Information - Shows general information about the ACT analysis
    2. Model Configuration Paths - Displays the paths to model configuration files used in the analysis
    """

    def __init__(self, act):
        """
        Initialize the Sim Info Card.

        Args:
            act: The ACT analysis object containing results data and configuration information
                 used to populate the analysis information and model configuration tables.
        """
        self.act = act
        self.info_table = None
        self.model_configs_table = None
        super().__init__(
            id="sim-info-card-id",
            title="Simulation Info",
            content=self.generate_content(),
        )

    def generate_content(self):
        """
        Generate the HTML content for the Sim Info Card.

        Creates two tables: one for analysis information and one for model configuration paths.
        Formats them with appropriate headers and styling.

        Returns:
            str: HTML content for the card body containing both tables."""
        self.sim_info_table = SimInfoTable(self.act)
        self.model_configs_table = ModelConfigsTable(self.act)

        content = f"""
            <div class="row">
                <center><h3> Simulation Information </h3></center>
                {self.sim_info_table.get_html()}

                <hr style="height: 20px">

                <center><h3> Model Configuration Paths </h3></center>
                {self.model_configs_table.get_html()}
            </div>
        """
        return content
