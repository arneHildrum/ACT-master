# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import random
import tempfile

import plotly.graph_objs as go
from act.core.utils.logger import log
from plotly.io import write_image
from plotly.offline import plot


class BasePlot:
    """
    Base class for all plot objects in the ACT visualization system.

    This class provides common functionality for creating, displaying, and exporting
    plots using Plotly. It handles the initialization of plot figures, saving plots
    in various formats, generating HTML representations, and managing plot data.
    All specialized plot classes in the ACT system should inherit from this base class
    to ensure consistent behavior and appearance.
    """

    def __init__(self, out_dir: str = None, export_plot: bool = False) -> None:
        """Initialize a base plot object with output directory and export settings.


        Args:
            out_dir (str, optional): The output directory for saving plot files.
                If None, a temporary directory will be created.
            export_plot (bool, default=False): Whether to automatically export/save the plot.
                Setting this to True on remote machines without proper graphics
                forwarding may cause the application to hang. When True, plots will be
                saved to disk in the specified output directory.
                forwarding may cause the application to hang.
        """
        self.export_plot = export_plot
        if out_dir is not None:
            self.out_dir = out_dir
        else:
            temp_out = tempfile.TemporaryDirectory(prefix="act_ui_")
            self.out_dir = temp_out

        self.fig = go.Figure()
        random.seed(0)

    def save_plot(self, export_file=None):
        """
        Save the current plot to disk in multiple formats (PNG, HTML, PDF).

        This method saves the current figure to the output directory in three formats:
        PNG (for raster images), HTML (for interactive viewing), and PDF (for printing).

        Args:
            export_file (str, optional): Custom filename for the exported plot.
                If None, the plot will be saved using the class name as the filename.

        Raises:
            Exception: If there is an error writing any of the output files.
        """
        # Check if the plot is empty before saving
        self.check_empty_plot()

        try:
            img_file = (
                f"{self.out_dir}/{type(self).__name__}.png"
                if export_file is None
                else export_file
            )
            self.fig.write_image(f"{img_file}", scale=4)
        except Exception as e:  # noqa
            log.error(e)
            log.error(f"Couldn't write PNG of chart for {img_file}")

        self.fig.write_html(img_file.replace(".png", ".html"))
        write_image(self.fig, img_file.replace(".png", ".pdf"), format="pdf")

    def get_html(self):
        """
        Generate an HTML representation of the current plot.

        This method creates an HTML div containing the interactive Plotly plot,
        which can be embedded in web pages or dashboards. The plot is configured
        to be responsive to container size changes.

        Returns:
            str: HTML string containing the plot as a div element that can be
                embedded in a web page.
        """
        # Check if the plot is empty before generating HTML
        self.check_empty_plot()

        return plot(
            self.fig,
            output_type="div",
            include_plotlyjs=False,
            config={"responsive": True},
        )

    # This is the closest plotly equivalent to plt.close()
    def clear_data(self):
        """
        Clear all data and layout settings from the current figure.

        This method removes all traces and layout settings from the figure,
        effectively resetting it to an empty state. This is similar to
        matplotlib's plt.close() functionality.
        """
        self.fig.data = []
        self.fig.layout = {}

    def check_empty_plot(self):
        """
        Check if the plot is empty after the plot() method has been called.
        Raises an error if the plot is empty.

        This method can be overridden by subclasses if they need custom logic
        for detecting empty plots.
        """
        if not self.fig.data:
            log.error(
                f"Empty plot detected in {self.__class__.__name__}. No data was plotted."
            )

    def get_sunburst_trace(self, data, colors):
        """
        Create a Plotly sunburst trace from the provided data and colors.

        This method generates a sunburst visualization trace that can be added to
        a Plotly figure. It configures the trace with the specified data structure
        and color settings.

        Args:
            data (dict): Dictionary containing the sunburst data structure with keys:
                'children' (list): Labels for each segment
                'parents' (list): Parent labels for each segment
                'values' (list): Values determining the size of each segment
            colors (list): List of colors to use for the sunburst segments

        Returns:
            go.Sunburst: A configured Plotly Sunburst trace object ready to be
                added to a figure
        """
        return go.Sunburst(
            labels=data["children"],
            parents=data["parents"],
            values=data["values"],
            leaf={"opacity": 0.5},
            marker={"colors": colors},
        )
