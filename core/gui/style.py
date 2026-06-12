# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""
Centralized styling configuration for ACT GUI components.

This module provides consistent styling definitions including color mappings,
layout settings, and other visual styling constants used across the ACT
delta tool and other GUI components.
"""

from enum import Enum

from act.core.carbon import SourceType
from act.core.common import ModelType


# Color mappings for ACT visualization components
# These provide consistent color schemes across different plot types

# Color mapping for ModelType categories (used in barcharts)
MODEL_TYPE_COLOR_MAP = {
    ModelType.LOGIC: "blue",
    ModelType.AP: "orange",
    ModelType.DRAM: "green",
    ModelType.FLASH: "red",
    ModelType.HDD: "purple",
    ModelType.MANUAL: "brown",
    ModelType.MATERIALS: "pink",
    ModelType.CAPACITOR: "gray",
    ModelType.RESISTOR: "olive",
    ModelType.DIODE: "cyan",
    ModelType.PCB: "lime",
    ModelType.BATTERY: "indigo",
    ModelType.SIGNAL_BEAD: "teal",
    ModelType.POWER: "navy",
    ModelType.OTHER: "maroon",
}

# Color mapping for SourceType categories (used in sunburst charts)
SOURCE_TYPE_COLOR_MAP = {
    SourceType.PACKAGING: "blue",
    SourceType.MATERIALS: "orange",
    SourceType.OPERATION: "yellow",
    SourceType.FABRICATION: "purple",
    SourceType.PASSIVES: "green",
    SourceType.PCB: "aqua",
    SourceType.MOSFET: "red",
    SourceType.CONNECTOR: "pink",
    SourceType.OTHER: "white",
}


class DefaultPlotSettings(Enum):
    """Default config settings for plotly figures.

    This enum provides standardized configuration values for plotly visualizations
    used throughout the ACT dashboard. It ensures consistent styling, sizing, and
    positioning of plot elements across different visualization types.
    """

    MARGIN = {"l": 5, "r": 5, "t": 15, "b": 15}
    MARGIN_WITH_SUBTITLE = {"l": 5, "r": 5, "t": 80, "b": 15}
    FONT = {"size": 13}
    TABLE_HEIGHT = 800
    PLOT_HEIGHT = 800
    TITLE_X = 0.5
    TITLE_Y = 0.975

    @staticmethod
    def get_default():
        """
        Return a dictionary of default plot configuration settings.

        Returns:
            dict: A dictionary containing default configuration settings for plotly
                 figures, including autosize, legend visibility, title positioning,
                 height, font, and margin settings.
        """
        return {
            "autosize": True,
            "showlegend": True,
            "title_x": DefaultPlotSettings.TITLE_X.value,
            "title_y": DefaultPlotSettings.TITLE_Y.value,
            "height": DefaultPlotSettings.PLOT_HEIGHT.value,
            "font": DefaultPlotSettings.FONT.value,
            "margin": DefaultPlotSettings.MARGIN.value,
        }


# Layout constants for delta dashboard cards
class DeltaCardLayout:
    """Layout constants for delta dashboard cards."""

    # Column classes for responsive layout based on number of simulations
    COLUMN_CLASSES = {
        2: "col-md-6",
        3: "col-md-4",
        4: "col-md-3",
        "default": "col-md-6",
    }

    # Bar chart layout settings
    BAR_CHART_MARGIN = {"l": 200, "r": 50, "t": 80, "b": 50}
    BAR_CHART_MIN_HEIGHT = 400
    BAR_CHART_HEIGHT_PER_CATEGORY = 80

    # Horizontal divider styling
    HORIZONTAL_DIVIDER = '<hr style="height: 20px">'


# Helper functions for color mapping
def get_model_type_color(model_type: ModelType) -> str:
    """
    Get color for a ModelType.

    Args:
        model_type: The ModelType enum value
        use_alt_colors: Whether to use alternative color scheme

    Returns:
        str: Color name for the model type
    """
    return MODEL_TYPE_COLOR_MAP.get(model_type, "gray")


def get_source_type_color(source_type: SourceType) -> str:
    """
    Get color for a SourceType.

    Args:
        source_type: The SourceType enum value

    Returns:
        str: Color name for the source type
    """
    return SOURCE_TYPE_COLOR_MAP.get(source_type, "gray")


def get_column_class(num_simulations: int) -> str:
    """
    Get responsive column class based on number of simulations.

    Args:
        num_simulations: Number of simulations to display

    Returns:
        str: Bootstrap column class
    """
    return DeltaCardLayout.COLUMN_CLASSES.get(
        num_simulations, DeltaCardLayout.COLUMN_CLASSES["default"]
    )
