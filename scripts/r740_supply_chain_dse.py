#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""
Dell R740 Supply Chain Location Design Space Exploration

This script explores the carbon emissions impact of relocating the manufacturing
supply chain for a Dell R740 server across different countries. It uses ACT3
to evaluate how moving all component manufacturing from a baseline location
(Taiwan) to South Korea, Japan, or the United States affects total carbon emissions.

Results are plotted as a bar chart and saved as a PNG.
"""

import argparse
import csv
import logging
import os
from dataclasses import dataclass

import plotly.graph_objects as go
from act.core.act_model import ACTModel
from act.core.bom import BOM
from act.core.scaling.scaling_config import ScalingConfig
from act.core.utils.load_yaml_with_macros import load_yaml_with_macros
from act.core.utils.logger import log, setup_logger

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
BOMS_DIR = os.path.join(SCRIPT_DIR, "..", "boms")
BASE_BOM_PATH = os.path.join(BOMS_DIR, "server", "dellr740", "top.yaml")

# All top-level device path prefixes in the Dell R740 BOM
ALL_DEVICE_PREFIXES = ["cpu", "ssd", "dram"]

# Manufacturing locations to sweep
LOCATIONS = [
    {"label": "Taiwan\n(Baseline)", "location": "taiwan"},
    {"label": "South Korea", "location": "south korea"},
    {"label": "Japan", "location": "japan"},
    {"label": "United States", "location": "usa"},
]


@dataclass
class DSEResult:
    location_label: str
    total_carbon_grams: float


def run_act_with_scaling(
    base_bom_path: str, scaling_config: ScalingConfig | None = None
) -> float:
    """Run ACT with optional scaling config and return total carbon in grams."""
    bom_data = load_yaml_with_macros(base_bom_path)
    bom = BOM(**bom_data, file=base_bom_path)
    model = ACTModel(test=True, scaling_config=scaling_config)
    result = model.get_carbon(bom=bom)
    return result.total().to("gram").magnitude


def make_scaling_config(location: str) -> ScalingConfig:
    """Create a ScalingConfig that moves all device paths to the given location."""
    scaling_paths = {}
    for prefix in ALL_DEVICE_PREFIXES:
        scaling_paths[prefix] = {"location": location}

    return ScalingConfig(
        name=f"All components to {location}",
        compatible_with=["server/dellr740/top.yaml"],
        scaling_paths=scaling_paths,
    )


def run_dse(base_bom_path: str) -> list[DSEResult]:
    """Run the supply chain location design space exploration."""
    results = []

    for loc in LOCATIONS:
        log.info("Evaluating manufacturing in: %s", loc["label"])

        try:
            if loc["location"] == "taiwan":
                # Baseline: use Taiwan as-is (apply scaling to set location explicitly)
                scaling_config = make_scaling_config("taiwan")
            else:
                scaling_config = make_scaling_config(loc["location"])

            total_carbon = run_act_with_scaling(base_bom_path, scaling_config)
            log.info("  Total Carbon: %.2f kg CO2e", total_carbon / 1000.0)
            results.append(
                DSEResult(
                    location_label=loc["label"],
                    total_carbon_grams=total_carbon,
                )
            )
        except Exception as e:
            log.error("  Failed: %s", e)

    return results


def create_plot(results: list[DSEResult], output_path: str) -> None:
    """Create a bar chart of carbon emissions by manufacturing location."""
    labels = [r.location_label for r in results]
    carbon_kg = [r.total_carbon_grams / 1000.0 for r in results]

    # Use distinct colors: baseline in blue, others in lighter shades
    colors = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA"]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=labels,
            y=carbon_kg,
            marker_color=colors[: len(labels)],
        )
    )

    # Add total + delta annotations
    baseline_kg = carbon_kg[0]
    for i, (label, kg) in enumerate(zip(labels, carbon_kg)):
        if i == 0:
            text = f"{kg:.1f} kg"
        else:
            delta_kg = kg - baseline_kg
            delta_pct = (delta_kg / baseline_kg) * 100
            sign = "+" if delta_kg >= 0 else ""
            text = f"{kg:.1f} kg<br><sub>({sign}{delta_kg:.1f} kg / {sign}{delta_pct:.1f}%)</sub>"
        fig.add_annotation(
            x=label,
            y=kg,
            text=text,
            showarrow=False,
            yshift=22,
            font={"size": 14},
        )

    y_max = max(carbon_kg) * 1.25

    fig.update_layout(
        title={
            "text": "Dell R740 Server Carbon Emissions by Manufacturing Location",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 18},
        },
        xaxis_title="Manufacturing Location (All Components)",
        yaxis_title="Total Carbon Emissions (kg CO2e)",
        template="plotly_white",
        font={"size": 14},
        yaxis={"range": [0, y_max], "showgrid": False},
    )

    fig.write_image(output_path, width=900, height=600, scale=2)
    log.info("Plot saved to: %s", output_path)

    pdf_path = output_path.replace(".png", ".pdf")
    fig.write_image(pdf_path, width=900, height=600)
    log.info("PDF saved to: %s", pdf_path)


def print_results_table(results: list[DSEResult]) -> None:
    """Print results as a formatted table and export to CSV."""
    baseline_kg = results[0].total_carbon_grams / 1000.0

    # Print table header
    header = (
        f"{'Location':<25} {'Carbon (kg)':<15} {'Delta (kg)':<15} {'Delta (%)':<10}"
    )
    log.info("\n" + "=" * len(header))
    log.info(header)
    log.info("-" * len(header))

    for r in results:
        kg = r.total_carbon_grams / 1000.0
        delta_kg = kg - baseline_kg
        delta_pct = (delta_kg / baseline_kg) * 100 if baseline_kg != 0 else 0
        label = r.location_label.replace("\n", " ")
        if delta_kg == 0:
            log.info(f"{label:<25} {kg:<15.1f} {'---':<15} {'---':<10}")
        else:
            log.info(f"{label:<25} {kg:<15.1f} {delta_kg:<+15.1f} {delta_pct:<+10.1f}%")

    log.info("=" * len(header))

    # Export CSV alongside the plot
    csv_path = os.path.join(
        os.path.dirname(results[0].location_label) or ".", "r740_supply_chain_dse.csv"
    )
    csv_path = "r740_supply_chain_dse.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Location", "Carbon (kg)", "Delta (kg)", "Delta (%)"])
        for r in results:
            kg = r.total_carbon_grams / 1000.0
            delta_kg = kg - baseline_kg
            delta_pct = (delta_kg / baseline_kg) * 100 if baseline_kg != 0 else 0
            label = r.location_label.replace("\n", " ")
            writer.writerow(
                [label, f"{kg:.1f}", f"{delta_kg:+.1f}", f"{delta_pct:+.1f}"]
            )
    log.info(f"CSV results saved to: {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dell R740 supply chain location carbon emissions exploration"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="r740_supply_chain_dse.png",
        help="Output PNG file for the bar chart",
    )
    parser.add_argument(
        "--base-bom",
        type=str,
        default=None,
        help="Base BOM file (defaults to Dell R740 server)",
    )
    parser.add_argument(
        "-l",
        "--loglevel",
        type=str,
        default="info",
        help="Log level (debug, info, warning, error)",
    )
    args = parser.parse_args()

    loglevel = getattr(logging, args.loglevel.upper())
    setup_logger(loglevel=loglevel)

    base_bom_path = args.base_bom if args.base_bom else BASE_BOM_PATH
    log.info("Using base BOM: %s", base_bom_path)

    results = run_dse(base_bom_path)

    if results:
        create_plot(results, args.output)
        print_results_table(results)
    else:
        log.error("No results were produced")


if __name__ == "__main__":
    main()
