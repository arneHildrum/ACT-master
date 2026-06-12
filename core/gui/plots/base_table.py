# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import html
import tempfile

from act.core.utils.logger import log
from prettytable import PrettyTable


class BaseTable:
    """
    Base class for table visualizations in the ACT dashboard.

    This class provides common functionality for creating and formatting tables
    that display data in the ACT visualization system. It handles initialization
    of table structures, data management, and HTML rendering with consistent styling.

    Subclasses should extend this class to implement specific table types by
    populating the header and data attributes with appropriate content for their
    visualization needs.
    """

    def __init__(self, out_dir: str = None):
        """
        Initialize a base table object with output directory and data structures.

        Args:
            out_dir (str, optional): The output directory for saving table files.
                If None, a temporary directory will be created with the prefix "act_table_".

        The constructor initializes the table structure with empty header and data,
        setting up the foundation for subclasses to populate with specific content.
        The table object itself is initialized as None and will be created when
        get_html() is called.
        """
        if out_dir is not None:
            self.out_dir = out_dir
        else:
            temp_out = tempfile.TemporaryDirectory(prefix="act_table_")
            self.out_dir = temp_out

        self.table = None
        self.header = []
        self.data = []
        self.data_dict = {}

    def get_html(self, align: dict = None):
        """
        Generate and return the HTML representation of the table.

        This method creates a PrettyTable object from the table's header and data,
        applies any specified alignment settings, and converts it to an HTML string.
        If the data dictionary is populated but the data list is empty, it will
        convert the dictionary to a list format before rendering.

        If both data structures are empty, a warning is logged and an empty table
        will be returned.

        Args:
            align(dict[str -> str]): The header name to align value in PrettyTable if the column should override the default text alignment.

        Returns:
            str: HTML snippet containing the formatted table with appropriate styling.
        """

        # if the data dict is populated, load the table data from there
        if len(self.data_dict) > 0 and len(self.data) == 0:
            self.data = [[k, v] for k, v in self.data_dict.items()]

        # otherwise make sure that the table data is not empty
        if len(self.data) == 0:
            log.warning(
                f"Table {self.__class__.__name__} has not entries in the data_dict. The resulting table will be empty."
            )

        self.table = PrettyTable(header=True, field_names=self.header)
        self.table.format = True
        self.table.add_rows(self.data)

        if align is not None:
            for (
                k,
                v,
            ) in align.items():
                self.table.align[k] = v

        html_output = html.unescape(
            self.table.get_html_string(
                attributes={"border": "1px solid", "text-align": "left"}
            )
        )

        return html_output
