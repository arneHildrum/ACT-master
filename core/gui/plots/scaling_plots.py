# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

from math import isclose

import plotly.graph_objects as go
from act.core.carbon import EMBODIED_SOURCES, OPERATIONAL_SOURCES
from act.core.gui.plots.base_plot import BasePlot
from act.core.processes import LOGIC_DATA
from act.core.utils.units import g, kg


class ScalingBasePlot(BasePlot):
    """Base class for scaling projection plots.

    This class provides common functionality for visualizing carbon emissions
    projections over time, including trend lines and stacked bar charts showing
    embodied vs operational carbon.
    """

    def __init__(self, runs, xtitle, base_act, *args, weight_unit=kg, **kwargs):
        """Initialize the scaling base plot.

        Args:
            runs (dict[int, ACTModel]): Dictionary mapping years/deltas to ACT model results.
            xtitle (str): Label for the x-axis.
            base_act (ACTModel): Baseline ACT model for comparison.
            *args: Additional positional arguments passed to BasePlot.
            weight_unit (pint.Quantity): Unit for weight display. Defaults to kg.
            **kwargs: Additional keyword arguments passed to BasePlot.
        """
        self.base_act = base_act
        self.weight_unit = weight_unit
        super().__init__(*args, **kwargs)
        self.plot(runs=runs, xtitle=xtitle)

    def plot(self, runs: dict = None, xtitle="+Year"):
        """Generate the scaling projection plot.

        Creates a visualization with a trend line and stacked bar chart showing
        embodied and operational carbon components over time.

        Args:
            runs (dict[int, ACTModel]): Dictionary mapping years/deltas to ACT model results.
            xtitle (str): Label for the x-axis.

        Raises:
            AssertionError: If runs is None.
        """
        assert runs is not None, (
            "CI plot requires a dict of runs [str, ACTModel] to plot results from."
        )
        years = runs.keys()

        # add the scatter trace trend line
        x_data, y_data = [], []
        for year in sorted(years):
            x_data.append(year)
            y_data.append(
                runs[year].results.total_carbon.total().to(self.weight_unit).m
            )

        trace = go.Scatter(
            x=x_data,
            y=y_data,
            mode="lines+markers",
            line={"width": 2},
            showlegend=False,
        )
        self.fig.add_trace(trace)

        # add stacked bar chart of the embodied and operational components
        embodied = []
        operational = []
        for year in sorted(years):
            total_carbon = runs[year].results.total_carbon
            embodied_total = 0 * g
            for ctype in EMBODIED_SOURCES:
                embodied_total += total_carbon.partial(ctype)
            op_total = 0 * g
            for ctype in OPERATIONAL_SOURCES:
                op_total += total_carbon.partial(ctype)
            assert isclose(
                (embodied_total + op_total).to(g).m, total_carbon.total().to(g).m
            )
            embodied.append(embodied_total.to(self.weight_unit).m)
            operational.append(op_total.to(self.weight_unit).m)

        self.fig.add_trace(go.Bar(x=x_data, y=embodied, name="Embodied"))
        self.fig.add_trace(go.Bar(x=x_data, y=operational, name="Operational"))

        # add horizontal baseline carbon line
        mcarbon = self.base_act.results.total_carbon.total().to(self.weight_unit).m
        funit = format(self.weight_unit.units, "~")
        self.fig.add_hline(
            y=mcarbon,
            line_width=2,
            line_dash="dash",
            line_color="green",
            annotation_text="Baseline<br>" + "%.2f " % mcarbon + funit,
            annotation_position="top left",
            annotation_font_color="green",
        )

        fweight_unit = format(self.weight_unit.units, "~")
        self.fig.update_layout(
            barmode="stack",
            bargap=0.5,
            xaxis_title=xtitle,
            yaxis_title=f"Carbon ({fweight_unit})",
            xaxis={"tickmode": "linear", "dtick": 1},
        )


class CILatestPlot(ScalingBasePlot):
    """Plot for carbon intensity projections with synchronized latest year."""

    def __init__(self, dse_manager, *args, **kwargs):
        """Initialize the CI latest plot.

        Args:
            dse_manager (DSEManager): DSE manager containing projection results.
            *args: Additional positional arguments passed to ScalingBasePlot.
            **kwargs: Additional keyword arguments passed to ScalingBasePlot.
        """
        self.dse_manager = dse_manager
        super().__init__(
            *args,
            runs=dse_manager.ci_latest_runs,
            base_act=self.dse_manager.base_act,
            xtitle="Year",
            **kwargs,
        )

    def plot(self, *args, **kwargs):
        super().plot(*args, **kwargs)


class CIIncPlot(ScalingBasePlot):
    """Plot for carbon intensity projections with incremental year offsets."""

    def __init__(self, dse_manager, *args, **kwargs):
        """Initialize the CI incremental plot.

        Args:
            dse_manager (DSEManager): DSE manager containing projection results.
            *args: Additional positional arguments passed to ScalingBasePlot.
            **kwargs: Additional keyword arguments passed to ScalingBasePlot.
        """
        self.dse_manager = dse_manager
        super().__init__(
            *args,
            runs=dse_manager.ci_inc_runs,
            base_act=dse_manager.base_act,
            xtitle="+Δ Year",
            **kwargs,
        )


class TSLatestPlot(ScalingBasePlot):
    """Plot for technology scaling projections with synchronized latest year."""

    def __init__(self, dse_manager, *args, **kwargs):
        """Initialize the TS latest plot.

        Args:
            dse_manager (DSEManager): DSE manager containing projection results.
            *args: Additional positional arguments passed to ScalingBasePlot.
            **kwargs: Additional keyword arguments passed to ScalingBasePlot.
        """
        self.dse_manager = dse_manager

        super().__init__(
            *args,
            runs=dse_manager.ts_latest_runs,
            base_act=dse_manager.base_act,
            xtitle="Year",
            **kwargs,
        )

        for year in dse_manager.ts_latest_runs:
            processes = []
            for process, data in LOGIC_DATA.items():
                if data is not None and year == data.year:
                    processes.append(process.name)
            if len(processes) > 0:
                self.fig.add_vline(
                    x=year,
                    line_width=2,
                    line_dash="dash",
                    line_color="light grey",
                    annotation_text="<br>".join(processes),
                    annotation_position="top right",
                    annotation_font_color="light grey",
                )


class TSIncPlot(ScalingBasePlot):
    """Plot for technology scaling projections with incremental year offsets."""

    def __init__(self, dse_manager, *args, **kwargs):
        """Initialize the TS incremental plot.

        Args:
            dse_manager (DSEManager): DSE manager containing projection results.
            *args: Additional positional arguments passed to ScalingBasePlot.
            **kwargs: Additional keyword arguments passed to ScalingBasePlot.
        """
        self.dse_manager = dse_manager
        super().__init__(
            *args,
            runs=dse_manager.ts_inc_runs,
            base_act=dse_manager.base_act,
            xtitle="+Δ Year",
            **kwargs,
        )
