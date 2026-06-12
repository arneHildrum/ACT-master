# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import plotly.graph_objects as go
from act.core.gui.plots.base_act_plot import BaseACTPlot
from act.core.gui.style import DeltaCardLayout, get_model_type_color
from plotly.offline import plot


class DeltaCarbonBarchart(BaseACTPlot):
    """
    A horizontal stacked bar chart showing carbon emissions differences by model type.

    This plot displays carbon emissions differences between baseline
    and experiment simulations in a horizontal stacked bar chart format,
    showing device-level details on hover and using consistent colors per category.
    """

    def __init__(self, base_sim, delta_sims):
        """
        Initialize the Delta Carbon Bar Chart plot.

        Args:
            base_sim: The baseline ACT simulation object
            delta_sims: List of experiment ACT simulation objects to compare against baseline
        """
        self.base_sim = base_sim
        self.delta_sims = delta_sims
        # Use base_sim as the act parameter for BaseACTPlot
        super().__init__(act=base_sim)

    def make_sunburst_data(self):
        """
        Generate data for a sunburst visualization.

        Returns:
            tuple: A tuple containing:
                - dict: Data dictionary with 'children', 'parents', and 'values' keys
                - list: Optional list of colors for the sunburst segments
        """
        # Placeholder implementation - not used for bar chart
        data = {"children": ["Placeholder"], "parents": [""], "values": [1.0]}
        colors = None
        return data, colors

    def make_stacked_barchart_data(self, sim):
        """
        Creates dataset for a stacked barchart from carbon results.

        Args:
            sim: ACT simulation object

        Returns:
            dict: Dictionary with ModelType.value as keys and lists of device data as values
        """
        if (
            not sim
            or not hasattr(sim, "results")
            or not hasattr(sim.results, "carbon_by_device")
        ):
            return {}

        barchart_data = {}
        total_carbon = sim.results.total_carbon.total().to(self.weight_unit)

        for device_name, carbon_result in sim.results.carbon_by_device.items():
            # Get device data to determine model type
            if hasattr(sim, "bom") and sim.bom and device_name in sim.bom.devices:
                device_data = sim.bom.devices[device_name]
                model_type = device_data.model

                # Convert carbon to weight unit
                carbon_value = carbon_result.total().to(self.weight_unit)
                carbon_magnitude = carbon_value.m

                # Skip devices with near-zero carbon
                if abs(carbon_magnitude) < 1e-5:
                    continue

                # Format carbon value and percentage
                fcarbon_val = f"{carbon_magnitude:.2f} {self.fweight_unit}"
                if total_carbon.m > 0:
                    fpercent = f"{(carbon_magnitude / total_carbon.m * 100):.2f}"
                else:
                    fpercent = "0.00"

                # Add the category to the barchart data if it doesn't exist yet
                category_name = model_type.value.title()
                if category_name not in barchart_data:
                    barchart_data[category_name] = []

                barchart_data[category_name].append(
                    {
                        "device_name": device_name,
                        "carbon_value": carbon_value,
                        "fcarbon_val": fcarbon_val,
                        "fpercent": fpercent,
                        "color": get_model_type_color(model_type),
                    }
                )

        return barchart_data

    def generate_stacked_bar_traces(self, barchart_data, category_suffix):
        """
        Converts the barchart data into plotly stacked bar traces list.

        Args:
            barchart_data (dict): The barchart data to convert.
            category_suffix (str): The suffix to add to the category labels.

        Returns:
            tuple: A tuple containing the barchart traces and annotations.
        """
        barchart_traces = {}
        barchart_traces_current_val = {}
        barchart_annotations = []

        for category, barchart_items in barchart_data.items():
            category_label = f"{category} ({category_suffix})"
            # Initialize the trace list for category if it doesn't exist
            if category not in barchart_traces:
                barchart_traces[category] = []
                barchart_traces_current_val[category] = 0.0

            # if there are no items in category, generate a single empty bar as a placeholder
            if not barchart_items:
                barchart_traces[category].append(
                    go.Bar(
                        y=[category_label],
                        x=[0],
                        orientation="h",
                        base=0,
                    )
                )
            else:
                # convert barchart data into plotly stacked barchart items
                for barchart_item in barchart_items:
                    trace_label = f"{barchart_item['device_name']}<br>{barchart_item['fcarbon_val']}<br>{barchart_item['fpercent']}%"

                    barchart_traces[category].append(
                        go.Bar(
                            y=[category_label],
                            x=[barchart_item["carbon_value"].m],
                            customdata=[trace_label],
                            name="",
                            orientation="h",
                            marker_color=barchart_item["color"],
                            base=barchart_traces_current_val[category],
                            hovertemplate="%{customdata}",
                        )
                    )

                    # keep track where to stack the next item on x axis
                    barchart_traces_current_val[category] += barchart_item[
                        "carbon_value"
                    ].m

            # Add the total carbon annotation for each stacked bar
            category_carbon_total = (
                f"{barchart_traces_current_val[category]:.2f} {self.fweight_unit}"
            )
            barchart_annotations.append(
                go.layout.Annotation(
                    x=barchart_traces_current_val[category],
                    y=category_label,
                    text=category_carbon_total,
                    showarrow=False,
                    xanchor="left",
                    yanchor="middle",
                )
            )

        return barchart_traces, barchart_annotations

    def relocate_identical_values(self, barchart_data_1, barchart_data_2):
        """
        Puts all identical components within each barchart dataset at top of lists and makes empty rows for missing categories.

        Args:
            barchart_data_1 (dict): The first barchart data.
            barchart_data_2 (dict): The second barchart data.

        Returns:
            tuple: A tuple containing the sorted barchart data.
        """
        sorted_barchart_data_1 = {}
        sorted_barchart_data_2 = {}

        # Iterate through each category in both datasets
        all_categories = set(barchart_data_1.keys()).union(barchart_data_2.keys())
        for category in all_categories:
            identical_1 = []
            identical_2 = []
            non_identical_1 = []
            non_identical_2 = []

            barchart_items_1 = barchart_data_1.get(category, [])
            barchart_items_2 = barchart_data_2.get(category, [])

            # Iterate through barchart_items_1 and compare with barchart_items_2
            for i, item_1 in enumerate(barchart_items_1):
                if i < len(barchart_items_2):
                    item_2 = barchart_items_2[i]
                    if abs(item_1["carbon_value"].m - item_2["carbon_value"].m) < 1e-5:
                        identical_1.append(item_1)
                        identical_2.append(item_2)
                    else:
                        non_identical_1.append(item_1)
                        non_identical_2.append(item_2)
                else:
                    non_identical_1.append(item_1)

            # Add remaining items from barchart_items_2 to non_identical_2
            for j in range(len(barchart_items_1), len(barchart_items_2)):
                non_identical_2.append(barchart_items_2[j])

            sorted_barchart_data_1[category] = identical_1 + non_identical_1
            sorted_barchart_data_2[category] = identical_2 + non_identical_2

        return sorted_barchart_data_1, sorted_barchart_data_2

    def get_html(self):
        """
        Generate HTML content for the horizontal stacked bar chart showing carbon emissions differences.

        Returns:
            str: HTML content containing the Plotly horizontal stacked bar chart.
        """
        # Get stacked barchart data for all simulations
        base_barchart_data = self.make_stacked_barchart_data(self.base_sim)
        exp_barchart_data = []

        for experiment_sim in self.delta_sims:
            base_barchart_data, exp_barchart = self.relocate_identical_values(
                base_barchart_data,
                self.make_stacked_barchart_data(experiment_sim),
            )
            exp_barchart_data.append(exp_barchart)

        # Convert baseline barchart dataset into plotly stacked bar dataset
        base_barchart_traces, barchart_annotations = self.generate_stacked_bar_traces(
            base_barchart_data, "Baseline"
        )

        # Convert experiment barchart datasets into plotly stacked bar datasets
        exp_traces = []
        for idx, exp_barchart_rows in enumerate(exp_barchart_data):
            exp_trace, exp_annotation = self.generate_stacked_bar_traces(
                exp_barchart_rows, f"Experiment {idx + 1}"
            )
            exp_traces.append((exp_trace, exp_annotation))

        # Collect all traces with their labels for sorting
        all_traces = []

        # Add baseline traces
        for cat in base_barchart_traces.keys():
            for trace in base_barchart_traces[cat]:
                all_traces.append(trace)

        # Add experiment traces and annotations
        for exp_trace, exp_ann in exp_traces:
            barchart_annotations += exp_ann
            for cat in exp_trace.keys():
                for trace in exp_trace[cat]:
                    all_traces.append(trace)

        # Sort traces by parsing simulation type from y-axis labels
        def get_sort_key(trace):
            if hasattr(trace, "y") and trace.y:
                label = trace.y[0]  # Get the y-axis label
                if "(" in label and ")" in label:
                    # Extract the part in parentheses
                    sim_type = label.split("(")[1].split(")")[0]
                    category = label.split("(")[0].strip()

                    # Create sort key: (category, simulation_order)
                    if sim_type == "Baseline":
                        return (category, 0)
                    elif sim_type.startswith("Experiment "):
                        try:
                            exp_num = int(sim_type.split("Experiment ")[1])
                            return (category, exp_num)
                        except (ValueError, IndexError):
                            return (category, 999)  # fallback for malformed labels
                    else:
                        return (category, 999)  # fallback for unknown types
                else:
                    return (label, 999)  # fallback for labels without parentheses
            return ("", 999)  # fallback for traces without y labels

        # Sort all traces by category and simulation type (reverse to put baseline first)
        all_traces.sort(key=get_sort_key, reverse=True)
        joint_barchart_trace_data = all_traces

        # Define layout using centralized styling
        bar_plot_layout = go.Layout(
            barmode="stack",
            xaxis={"title": f"Carbon Emissions ({self.fweight_unit})"},
            yaxis={"title": "Carbon Category (Model Type)"},
            showlegend=False,
            bargap=0.1,
            title="Carbon Emissions Difference",
            height=max(
                DeltaCardLayout.BAR_CHART_MIN_HEIGHT,
                len(base_barchart_traces)
                * DeltaCardLayout.BAR_CHART_HEIGHT_PER_CATEGORY,
            ),
            margin=DeltaCardLayout.BAR_CHART_MARGIN,
        )

        # Create the figure
        fig = go.Figure(
            data=joint_barchart_trace_data,
            layout=bar_plot_layout,
        )

        # Add annotations to bars
        fig.update_layout(annotations=barchart_annotations)

        # Convert to HTML
        plot_html = plot(fig, output_type="div", include_plotlyjs=True)

        return plot_html
