# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.card import Card
from act.core.gui.plots.supply_chain_table import SupplyChainTable


class SupplyChainCard(Card):
    """
    A card that displays supply chain information for the analyzed system.

    This card presents a table showing supply chain details including manufacturing
    locations, transportation methods, and associated carbon emissions. It provides
    insights into the environmental impact of the system's supply chain and logistics,
    which is an important component of the overall carbon footprint.

    The supply chain information helps identify opportunities for reducing emissions
    through optimized manufacturing locations and transportation choices.
    """

    def __init__(self, act):
        """
        Initialize the Supply Chain Card.

        Args:
            act: The ACT analysis object containing supply chain information
                 used to populate the supply chain table with data about
                 manufacturing locations, transportation, and related
                 carbon emissions.
        """
        self.act = act
        self.supply_chain_table = None
        super().__init__(
            id="supply-chain-card-id",
            title="Supply Chain",
            content=self.generate_content(),
        )

    def generate_content(self):
        """
        Generate the HTML content for the Supply Chain Card.

        Creates a table displaying supply chain information with appropriate
        header and styling.

        Returns:
            str: HTML content for the card body containing the supply chain
                 table with manufacturing, transportation, and carbon footprint
                 information related to the system's supply chain.
        """
        self.supply_chain_table = SupplyChainTable(self.act)

        content = f"""
            <div class="row">
                <center><h3> Supply Chain Information </h3></center>
                {self.supply_chain_table.get_html()}
            </div>
        """
        return content
