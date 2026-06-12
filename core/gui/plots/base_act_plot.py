# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import math
from abc import abstractmethod

import plotly.graph_objects as go
from act.core.common import ModelType
from act.core.gui.plots.base_plot import BasePlot
from act.core.gui.style import DefaultPlotSettings
from act.core.utils.units import dollar, kg, mm2


class BaseACTPlot(BasePlot):
    """
    Base class for ACT (Architecture Carbon Tool) plots.

    This class extends BasePlot to provide common functionality for all ACT-specific
    visualizations, including handling of carbon results, weights, areas, and
    formatting utilities. It serves as a foundation for specialized plot types
    like device plots, source plots, and subsystem plots.

    Subclasses must implement the make_sunburst_data method to generate
    data for sunburst visualizations.
    """

    def __init__(
        self,
        act,
        decimal_places=2,
        weight_unit=kg,
        cost_unit=dollar,
        *args,
        **kwargs,
    ):
        self.act = act
        self.carbon_results = act.results.carbon_by_device
        self.bom = act.bom
        self.decimal_places = decimal_places
        self.weight_unit = weight_unit
        self.fweight_unit = format(self.weight_unit.units, "~")
        self.cost_unit = cost_unit
        self.fcost_unit = format(self.cost_unit.units, "~")
        self.area_unit = mm2
        self.farea_unit = "mm2"  # hardcode since pint doesn't properly compact mm ** 2

        super().__init__(*args, **kwargs)

    def weight_as_str(self, weight):
        """
        Format a weight value as a string with units.

        Args:
            weight: Weight value with units to format

        Returns:
            str: Formatted string with weight value and units"""
        assert weight.check(self.weight_unit)
        weight_val = weight.to(self.weight_unit).m
        fweight_val = f"{weight_val:.{self.decimal_places}f}" + f" {self.fweight_unit}"
        return fweight_val

    def weight_as_percent(self, weight, total_weight=None):
        """
        Calculate and format a weight value as a percentage of the total.

        Args:
            weight: Weight value with units
            total_weight: Optional total weight to use as denominator.
                          If None, uses the total carbon weight from results.

        Returns:
            str: Formatted string with percentage value
        """
        weight_val = weight.to(self.weight_unit).m
        _total_weight = (
            total_weight if total_weight is not None else self.get_total_carbon_weight()
        )
        total = _total_weight.to(self.weight_unit).m

        # guard against floating point error up to 10 places
        if math.isclose(weight_val, total, abs_tol=10**-10):
            weight_val = total

        assert weight_val <= total
        percent = weight_val / total * 100 if total != 0 else 100
        fpercent = f"{percent:.{self.decimal_places}f}%"
        return fpercent

    def get_total_carbon_weight(self):
        """
        Return the total carbon emissions in units of weight.

        Calculates the sum of carbon emissions across all devices in the system.

        Returns:
            Quantity: Total carbon weight with appropriate units (typically kg CO2e)
        """
        return sum([r.total() for _, r in self.carbon_results.items()])

    def get_total_area(self):
        """
        Return total system silicon area with area units.

        Calculates the sum of silicon areas for all logic devices in the bill of materials.
        Only devices with model type LOGIC are included in this calculation.

        Returns:
            Quantity: Total silicon area with appropriate units (typically mm²)
        """
        total = 0 * mm2
        for _, dev_data in self.bom.devices.items():
            if dev_data.model is ModelType.LOGIC:
                total += dev_data.area
        return total

    def cost_as_str(self, cost):
        """Format a cost value as a string with units.

        Args:
            cost: Cost value with units to format.

        Returns:
            str: Formatted string with cost value and units.

        Raises:
            AssertionError: If the cost value doesn't have compatible units.
        """
        assert cost.check(dollar)
        cost_val = cost.to(self.cost_unit).m
        as_str = f"{cost_val:.{self.decimal_places}f}" + self.fcost_unit
        return as_str

    def cost_as_percent(self, cost, total_cost=None):
        """Calculate and format a cost value as a percentage of the total.

        Args:
            cost: Cost value with units.
            total_cost: Optional total cost to use as denominator.
                        If None, uses the total cost from get_total_cost().

        Returns:
            str: Formatted string with percentage value.
        """
        cost_val = cost.to(self.cost_unit).m
        _total_cost = total_cost if total_cost is not None else self.get_total_cost()
        total = _total_cost.to(self.cost_unit).m

        # guard against floating point error up to 10 places
        if math.isclose(cost_val, total, abs_tol=10**-10):
            cost_val = total

        assert cost_val <= total
        percent = cost_val / total * 100 if total != 0 else 100
        fpercent = f"{percent:.{self.decimal_places}f}%"
        return fpercent

    def get_total_cost(self):
        """Return the total cost from the cost analyzer.

        Returns:
            Quantity: Total cost with appropriate units.
        """
        return self.act.cost_analyzer.get_total_cost()

    def area_as_str(self, area):
        """
        Format an area value as a string with units.

        Args:
            area: Area value with units to format

        Returns:
            str: Formatted string with area value and units

        Raises:
            AssertionError: If the area value doesn't have compatible units
        """
        assert area.check(self.area_unit)
        area_val = area.to(self.area_unit).m
        farea_val = f"{area_val:.{self.decimal_places}f}" + f" {self.farea_unit}"
        return farea_val

    def area_as_percent(self, area, total_area=None):
        """
        Calculate and format an area value as a percentage of the total.

        Args:
            area: Area value with units
            total_area: Optional total area to use as denominator.
                        If None, uses the total area from get_total_area().

        Returns:
            str: Formatted string with percentage value
        """
        area_val = area.to(self.area_unit).m
        _total_area = total_area if total_area is not None else self.get_total_area()
        total = _total_area.to(self.area_unit).m
        assert area_val <= total
        percent = area_val / total * 100 if total != 0 else 100
        fpercent = f"{percent:.{self.decimal_places}f}%"
        return fpercent

    @abstractmethod
    def make_sunburst_data(self):
        """
        Generate data for a sunburst visualization.

        This abstract method must be implemented by subclasses to provide
        the specific data structure needed for their sunburst visualizations.

        Returns:
            tuple: A tuple containing:
                - dict: Data dictionary with 'children', 'parents', and 'values' keys
                - list: Optional list of colors for the sunburst segments

        Raises:
            NotImplementedError: If the subclass does not implement this method
        """
        raise NotImplementedError(
            f"Sunburst data generation not implemented for {self.__class__}."
        )

    def plot(self, title, plot_settings=DefaultPlotSettings):
        """
        Create a sunburst plot with the provided title and settings.

        This method generates a sunburst visualization using the data from make_sunburst_data().
        It applies the specified plot settings and saves the plot if export_plot is True.

        Args:
            title (str): Title to display on the plot
            plot_settings (DefaultPlotSettings, optional): Plot configuration settings
                including title position, height, font, and margins
        """
        data, colors = self.make_sunburst_data()

        sunburst_kwargs = {
            "labels": data["children"],
            "parents": data["parents"],
            "values": data["values"],
            "leaf": {"opacity": 0.5},
        }

        if colors is not None:
            sunburst_kwargs.update(marker={"colors": colors})

        self.fig.add_trace(go.Sunburst(**sunburst_kwargs))

        self.fig.update_layout(
            showlegend=True,
            autosize=True,
            title_text=title,
            title_x=plot_settings.TITLE_X.value,
            title_y=plot_settings.TITLE_Y.value,
            height=plot_settings.PLOT_HEIGHT.value,
            font=plot_settings.FONT.value,
            margin=plot_settings.MARGIN_WITH_SUBTITLE.value,
        )

        if self.export_plot:
            self.save_plot()
