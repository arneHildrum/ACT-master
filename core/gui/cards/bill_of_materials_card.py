# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from act.core.gui.card import Card
from act.core.gui.plots.bom_table import BOMTable
from act.core.gui.plots.device_table import DeviceTable


class BillOfMaterialsCard(Card):
    """
    A card that displays Bill of Materials information and detailed device data.

    This card presents two tables:
    1. Bill of Materials - Shows summary information about the system's bill of materials
    2. Detailed Device List - Displays comprehensive information about each device in the system

    The card provides a complete view of the system components being analyzed,
    including their specifications, manufacturing details, and physical characteristics,
    which form the basis for the carbon emissions calculations.
    """

    def __init__(self, act):
        """
        Initialize the Bill of Materials Card.

        Args:
            act: The ACT analysis object containing the bill of materials and device information
                 used to populate the BOM summary and detailed device tables.
        """
        self.act = act
        super().__init__(
            id="bill-of-materials-card",
            title="Bill of Materials",
            content=self.generate_content(),
        )

    def generate_content(self):
        """
        Generate the HTML content for the Bill of Materials Card.

        Creates two tables: one for the bill of materials summary and one for the
        detailed device list. Formats them with appropriate headers and styling.

        Returns:
            str: HTML content for the card body containing both the BOM summary table
                 and the detailed device table, with appropriate section headers and
                 formatting.
        """
        self.device_table = DeviceTable(act=self.act)
        self.bom_table = BOMTable(act=self.act)

        content = f"""
        <div class="row">
            <center><h2> Bill of Materials View </h2></center>
            <hr style="height: 20px">

            <center><h3> Top Level Summary View </h3></center>
            {self.bom_table.get_html()}

            <hr style="height: 20px">
            <center><h3> Detailed Device List View </h3><center>
            {self.device_table.get_html()}
        </div>
        """

        return content
