# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import os

from act.core.gui.plots.base_table import BaseTable


class ModelConfigsTable(BaseTable):
    """
    A table that displays the configuration files used in the carbon analysis.

    This table presents the file paths for all model configuration files used in the
    ACT analysis, including AP model, DRAM model, storage models (HDD/SSD), logic models,
    and PCB model. It provides transparency about which configuration files were used
    to generate the carbon analysis results, which is important for reproducibility
    and verification of the analysis.

    The table is formatted with two columns: "Model" (showing the model type) and
    "Configuration File" (showing the filename of the configuration file used).
    """

    def __init__(self, act, *args, **kwargs):
        """
        Initialize the Model Configs Table with ACT analysis data.

        Args:
            act: The ACT analysis object containing references to all model configuration
                 files used in the carbon analysis.
            *args: Variable length argument list passed to BaseTable.
            **kwargs: Arbitrary keyword arguments passed to BaseTable.

        The constructor initializes the table with the provided ACT analysis object,
        then immediately calls plot() to populate the table with model configuration data.
        """
        self.act = act
        super().__init__(*args, **kwargs)
        self.plot()

    def plot(self):
        """
        Populate the table with model configuration file data.

        This method sets up the table header with "Model" and "Configuration File" columns,
        and populates the data dictionary with entries for each model type used in the
        carbon analysis. For each model, it extracts the basename of the configuration
        file path to display a more concise representation.

        For models with multiple configuration files (like HDD and SSD models), the
        filenames are joined with commas for display in a single table cell.
        """
        self.header = ["Model", "Configuration File"]

        fx = os.path.basename
        self.data_dict = {
            "AP Model": fx(self.act.ap_model.model_file),
            "DRAM Model": fx(self.act.dram_model.model_file),
            "HDD Model": ", ".join([fx(x) for x in self.act.hdd_model.model_files]),
            "SSD Model": ", ".join([fx(x) for x in self.act.ssd_model.model_files]),
            "Logic EPA Model": fx(self.act.logic_model.epa_file),
            "Logic Materials Model": fx(self.act.logic_model.materials_config),
            "Logic GPA95 Model": fx(self.act.logic_model.gpa95_file),
            "Logic GPA99 Model": fx(self.act.logic_model.gpa99_file),
            "PCB Model": fx(self.act.pcb_model.model_file),
        }

    def get_html(self):
        """
        Generate the HTML representation of the model configurations table.

        Overrides the parent class method to apply left alignment to all columns
        in the table for better readability of the configuration file paths.

        Returns:
            str: HTML representation of the table with left-aligned columns.
        """
        return super().get_html(align={k: "l" for k in self.header})
