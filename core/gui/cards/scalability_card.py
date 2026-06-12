# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.card import Card
from act.core.gui.plots.scaling_table import ScalingTable


class ScalabilityCard(Card):
    """A card that displays scalability analysis results.

    This card presents a table showing how carbon emissions scale with
    different device configurations and parameters.
    """

    def __init__(self, act):
        """Initialize the Scalability Card.

        Args:
            act (ACTModel): The ACT analysis object containing scalability data.
        """
        self.act = act
        super().__init__(
            id="Scalability", title="Scalability", content=self.generate_content()
        )

    def generate_content(self):
        """Generate the HTML content for the Scalability Card.

        Creates a scaling table showing carbon emissions scalability analysis.

        Returns:
            str: HTML content for the card body containing the scaling table.
        """
        self.scaling_table = ScalingTable(
            act=self.act,
        )

        content = f"""
        <center> <h3> Scalability Analysis View </h3> </center>
        <center> {self.scaling_table.get_html()} </center>

        """
        return content
