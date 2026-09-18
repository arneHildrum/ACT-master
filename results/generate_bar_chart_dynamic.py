#!/usr/bin/env python3
"""Plot absolute ACT carbon totals with Plotly, not Matplotlib.

Run in your results directory: python generateBarChart.py
Or: python generateBarChart.py ./results --output ./figures/carbon_breakdown

Dependencies: pip install "plotly>=6.1.1" "PyYAML>=6" "kaleido>=1"
PNG/SVG/PDF export additionally needs Chrome/Chromium (plotly_get_chrome).
HTML export is self-contained, works offline, and does not need Kaleido.

Country/scenario labels are inferred from filenames and op_ci, not verified
against the underlying ACT model. Use --labels for explicit label overrides.
No values are normalized, recomputed with ACT, or read from chart images.
"""
from __future__ import annotations

import argparse
import fnmatch
import html
import json
import math
import re
import sys
import textwrap
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
import plotly.graph_objects as go
import yaml

# Muted palette and thin outlines inspired by the supplied runtime chart.
# Each category retains the same color across every country and scenario.
COLORS = {"operation": "#DCD2EB", "fabrication": "#80B1BA", "packaging": "#C9BF9C"}
OUTLINE = "#666666"
COMPONENTS = ("operation", "fabrication", "packaging")
UNIT_GRAMS = {"g": 1.0, "kg": 1000.0, "t": 1_000_000.0}
MASS_GRAMS = {
    "": 1.0, "g": 1.0, "gram": 1.0, "grams": 1.0,
    "kg": 1000.0, "kilogram": 1000.0, "kilograms": 1000.0,
    "mg": 0.001, "milligram": 0.001, "milligrams": 0.001,
    "t": 1_000_000.0, "tonne": 1_000_000.0, "tonnes": 1_000_000.0,
    "metric ton": 1_000_000.0, "metric tons": 1_000_000.0,
}
NUMBER_AND_UNIT = re.compile(
    r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*(.*?)\s*$"
)
COUNTRY_NAMES = {
    "india": "India", "ind": "India", "norway": "Norway", "nor": "Norway",
    "norwegian": "Norway", "usa": "USA", "us": "USA",
    "unitedstates": "USA", "unitedstatesofamerica": "USA",
    "taiwan": "Taiwan", "twn": "Taiwan",
}


@dataclass
class Report:
    path: Path
    country: str
    scenario: str
    order: int
    grams: dict[str, float]


def extract_grams(value: object) -> float:
    """Parse an ACT mass, including scientific notation and explicit units.

    Bare numeric values are treated as grams, as in the original script.
    Bad/negative/nonfinite values raise an error instead of silently becoming 0.
    """
    if isinstance(value, bool):
        raise ValueError("a boolean is not a carbon mass")
    if isinstance(value, (int, float)):
        grams = float(value)
    elif isinstance(value, str):
        match = NUMBER_AND_UNIT.fullmatch(value)
        if not match:
            raise ValueError(f"invalid carbon value: {value!r}")
        number, unit = match.groups()
        unit = re.sub(r"\s+", " ", unit).lower()
        if unit not in MASS_GRAMS:
            raise ValueError(f"unsupported mass unit {unit!r} in {value!r}")
        grams = float(number) * MASS_GRAMS[unit]
    else:
        raise ValueError(f"expected a number or mass string, got {value!r}")
    if not math.isfinite(grams) or grams < 0:
        raise ValueError(f"carbon must be finite and non-negative: {value!r}")
    return grams


def inferred_labels(path: Path, data: Mapping) -> tuple[str, str, int]:
    """Convenience display labels only; these do not validate a scenario."""
    stem = re.sub(r"[^a-z0-9]", "", path.stem.lower())
    country = "Other"
    for prefix in ("norwegian", "norway", "india", "unitedstates", "usa", "taiwan"):
        if stem.startswith(prefix):
            country = COUNTRY_NAMES[prefix]
            break
    if country == "Other":
        key = re.sub(r"[^a-z]", "", str(data.get("op_ci", "")).lower())
        country = COUNTRY_NAMES.get(key, "Other")
    has_operation = "operation" in stem
    has_fabrication = "fabrication" in stem or "onshore" in stem
    if has_operation and has_fabrication:
        return country, "Operation +\nfabrication", 1
    if has_operation:
        return country, "Operation\nonly", 0
    if has_fabrication:
        return country, "Fabrication\nonly", 2
    # Unknown filenames are not arbitrarily labelled as operation-only.
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", path.stem)
    return country, words.replace("_", " ").replace("-", " "), 3


def read_label_overrides(path: Path | None) -> dict:
    if path is None:
        return {}
    with path.open(encoding="utf-8-sig") as stream:
        labels = json.load(stream)
    if not isinstance(labels, dict):
        raise ValueError("the label file must be a JSON object keyed by filename")
    for name, entry in labels.items():
        if not isinstance(entry, dict):
            raise ValueError(f"label entry {name!r} must be an object")
        unknown = set(entry) - {"country", "scenario", "order"}
        if unknown:
            raise ValueError(f"unknown label settings for {name!r}: {sorted(unknown)}")
        for key in ("country", "scenario"):
            if key in entry and (not isinstance(entry[key], str) or not entry[key].strip()):
                raise ValueError(f"{name!r}: {key} must be a non-empty string")
        if "order" in entry and type(entry["order"]) is not int:
            raise ValueError(f"{name!r}: order must be an integer")
    return labels


def load_reports(directory: Path, labels: Mapping, patterns: Sequence[str],
                 skip_invalid: bool = False) -> list[Report]:
    if not directory.is_dir():
        raise ValueError(f"results directory does not exist: {directory}")
    files = sorted(
        (p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in (".yaml", ".yml")
         and any(fnmatch.fnmatchcase(p.name.lower(), pattern.lower()) for pattern in patterns)),
        key=lambda p: p.name.casefold(),
    )
    reports, errors = [], []
    for path in files:
        try:
            with path.open(encoding="utf-8-sig") as stream:
                data = yaml.safe_load(stream)
            if not isinstance(data, Mapping) or "total_carbon" not in data:
                print(f"Skipping non-report YAML: {path.name}", file=sys.stderr)
                continue
            total = data["total_carbon"]
            if not isinstance(total, Mapping) or not any(c in total for c in COMPONENTS):
                raise ValueError("total_carbon must contain named emission categories")
            grams = {c: extract_grams(total.get(c, 0)) for c in COMPONENTS}
            # Do not silently omit a non-zero source category in a 'total' chart.
            for key in set(total) - set(COMPONENTS):
                if extract_grams(total[key]) != 0:
                    raise ValueError(f"non-zero extra category {key!r}; add it to COMPONENTS and COLORS first")
            country, scenario, order = inferred_labels(path, data)
            override = labels.get(path.name, {})
            reports.append(Report(path, override.get("country", country),
                                  override.get("scenario", scenario),
                                  override.get("order", order), grams))
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{path.name}: {exc}")
    if errors:
        message = "\n".join(errors)
        if not skip_invalid:
            raise ValueError("Invalid report(s); no chart generated:\n" + message)
        print("WARNING: explicitly skipping invalid reports:\n" + message, file=sys.stderr)
    if not reports:
        raise ValueError("no ACT reports with total_carbon were found")
    used = {r.path.name for r in reports}
    for name in set(labels) - used:
        print(f"Note: label override has no loaded report: {name}", file=sys.stderr)
    counts = Counter((r.country, r.scenario) for r in reports)
    for r in reports:
        if counts[r.country, r.scenario] > 1:
            print(f"WARNING: repeated display label for {r.path.name}; showing the filename. "
                  "Use --labels or --include to distinguish/filter reports.", file=sys.stderr)
            r.scenario = r.path.stem
    # Never collapse two reports into one bar just because their labels match.
    return reports


def wrap_label(value: str, width: int = 15) -> str:
    lines = []
    for line in value.splitlines() or [value]:
        lines.extend(textwrap.wrap(line, width=width, break_long_words=True) or [""])
    return "<br>".join(html.escape(line) for line in lines)


def build_figure(reports: list[Report], *, unit: str = "kg", components=COMPONENTS,
                 country_order=("India", "Norway", "USA"), width: int = 1100,
                 height: int = 500, font_size: float = 22, bar_width: float = 0.90,
                 group_gap: float = 0.55, title: str = "", totals: bool = True,
                 tick_angle: int = 0) -> tuple[go.Figure, list[Report]]:
    rank = {name.casefold(): i for i, name in enumerate(country_order)}
    ordered = sorted(reports, key=lambda r: (
        rank.get(r.country.casefold(), len(rank)), r.country.casefold(),
        r.order, r.path.name.casefold(),
    ))
    xs, groups = [], []
    cursor = 0.0
    for r in ordered:
        if groups and groups[-1][0] != r.country:
            cursor += group_gap
        xs.append(cursor)
        if not groups or groups[-1][0] != r.country:
            groups.append([r.country, cursor, cursor])
        else:
            groups[-1][2] = cursor
        cursor += 1.0

    divisor = UNIT_GRAMS[unit]  # Unit conversion ONLY, not normalization.
    totals_y = [sum(r.grams[c] for c in components) / divisor for r in ordered]
    largest = max(totals_y)
    if not math.isfinite(largest):
        raise ValueError("the sum of carbon values is too large to plot")
    decimals = 2 if unit == "t" or largest < 20 else (1 if largest < 200 else 0)
    labels = [wrap_label(r.scenario) for r in ordered]
    max_lines = max(label.count("<br>") + 1 for label in labels)
    label_font = max(12, font_size - 3)
    label_depth = max_lines * label_font * 1.15
    if tick_angle:
        label_depth += 60
    bottom_margin = int(label_depth + font_size * 1.7 + 16)
    top_margin = int(font_size * (4.5 if title else 2.8))
    if height - bottom_margin - top_margin < 120:
        height = bottom_margin + top_margin + 150
    plot_height = height - bottom_margin - top_margin
    fig = go.Figure()
    hover = [[html.escape(r.path.name), html.escape(r.country),
              html.escape(r.scenario.replace("\n", " ")), sum(r.grams[c] for c in components) / divisor]
             for r in ordered]
    for component in components:
        fig.add_trace(go.Bar(
            x=xs, y=[r.grams[component] / divisor for r in ordered],
            width=bar_width, name=component.capitalize(),
            marker=dict(color=COLORS[component], line=dict(color=OUTLINE, width=0.75)),
            customdata=hover, cliponaxis=False,
            hovertemplate=("<b>%{customdata[0]}</b><br>%{customdata[1]}: %{customdata[2]}<br>"
                           + component.capitalize() + ": %{y:,.3f} " + unit + " CO\u2082e"
                           + "<br>Displayed stack: %{customdata[3]:,.3f} " + unit
                           + " CO\u2082e<extra></extra>"),
        ))
    if totals:
        for x, y in zip(xs, totals_y):
            fig.add_annotation(x=x, y=y, text=f"{y:,.{decimals}f}",
                               showarrow=False, yshift=9, yanchor="bottom",
                               font=dict(size=font_size - 3, color="#333333"))
    # Group headings below the short scenario labels, like Compute/Flush/Stall.
    for country, first, last in groups:
        fig.add_annotation(
            x=(first + last) / 2, xref="x", y=0, yref="paper",
            yshift=-(label_depth + 20), yanchor="top", showarrow=False,
            text=html.escape(country), font=dict(size=font_size + 2, color="#111111"),
        )
    for previous, following in zip(groups, groups[1:]):
        separator = (previous[2] + following[1]) / 2
        fig.add_shape(type="line", x0=separator, x1=separator, xref="x",
                      y0=0, y1=1, yref="paper", layer="below",
                      line=dict(color="#D4D4D4", width=1, dash="dot"))

    all_components = set(components) == set(COMPONENTS)
    ytitle = "Carbon emissions" if all_components else " + ".join(c.capitalize() for c in components)
    fig.update_layout(
        template="none", width=width, height=height,
        # A linear, zero-based axis and ordinary stacking: no barnorm setting.
        barmode="stack", bargap=0, bargroupgap=0,
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Arial, Helvetica, sans-serif", size=font_size, color="#111111"),
        margin=dict(l=112 if unit != "t" else 96, r=22, t=top_margin, b=bottom_margin),
        legend=dict(orientation="h", x=0, xanchor="left", y=1 + 20 / plot_height,
                    yanchor="bottom", font=dict(size=font_size), traceorder="normal",
                    itemsizing="constant", itemclick=False, itemdoubleclick=False),
        hoverlabel=dict(font=dict(size=15)),
        xaxis=dict(type="linear", tickmode="array", tickvals=xs, ticktext=labels,
                   tickangle=tick_angle, tickfont=dict(size=label_font),
                   range=[xs[0] - 0.68, xs[-1] + 0.68], fixedrange=False,
                   showgrid=False, zeroline=False, showline=True,
                   linecolor="#777777", linewidth=1, ticks=""),
        yaxis=dict(title=dict(text=ytitle + f" ({unit} CO\u2082e)", standoff=12),
                   type="linear", range=[0, largest * (1.16 if totals else 1.08) if largest else 1],
                   nticks=6, tickformat=f",.{decimals}f", exponentformat="none", showexponent="none",
                   showgrid=True, gridcolor="#E5E5E5", gridwidth=1,
                   zeroline=False, showline=True, linecolor="#777777", linewidth=1,
                   ticks="outside", ticklen=4, tickcolor="#777777",
                   tickfont=dict(size=font_size - 2)),
    )
    if title:
        fig.update_layout(title=dict(text=html.escape(title), x=0.5, xanchor="center",
                                     y=0.98, yanchor="top", font=dict(size=font_size)))
    return fig, ordered


def save_outputs(fig: go.Figure, reports: list[Report], args: argparse.Namespace) -> bool:
    prefix = args.output
    # --output is a prefix, not an extension; accept a familiar image filename too.
    if prefix.suffix.lower() in (".html", ".svg", ".png", ".pdf"):
        prefix = prefix.with_suffix("")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    formats = list(dict.fromkeys(args.formats))
    manifest = {
        "normalized": False, "display_unit": args.unit,
        "displayed_components": list(args.components),
        "labels_are_display_metadata_only": True,
        "reports": [{"file": str(r.path.resolve()), "country": r.country,
                     "scenario": r.scenario, "total_carbon_grams": r.grams,
                     "displayed_stack_grams": sum(r.grams[c] for c in args.components)} for r in reports],
    }
    audit_path = Path(str(prefix) + ".data.json")
    audit_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved data/label audit: {audit_path}")
    if "html" in formats:
        destination = Path(str(prefix) + ".html")
        fig.write_html(str(destination), include_plotlyjs=True, full_html=True,
                       auto_open=args.show, config={"responsive": True, "displaylogo": False,
                       "toImageButtonOptions": {"format": "svg", "filename": prefix.name}})
        print(f"Saved: {destination}")
    elif args.show:
        fig.show()
    static_formats = [fmt for fmt in formats if fmt != "html"]
    for fmt in static_formats:
        destination = Path(str(prefix) + "." + fmt)
        try:
            fig.write_image(str(destination), format=fmt,
                            scale=args.scale if fmt == "png" else 1)
            print(f"Saved: {destination}")
        except Exception as exc:
            print(f"Static export failed ({fmt}): {exc}\n"
                  'Install: python -m pip install -U "plotly>=6.1.1" "kaleido>=1"\n'
                  "Then install Chrome if needed: plotly_get_chrome\n"
                  "Already-saved HTML and data files remain available. "
                  "Use --formats html to run without the static-export dependency.", file=sys.stderr)
            return False
    return True


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("directory", nargs="?", type=Path, default=Path("."), help="ACT report directory")
    parser.add_argument("--output", type=Path, default=Path("carbon_breakdown_chart"), help="output filename prefix")
    parser.add_argument("--formats", nargs="+", choices=("html", "png", "svg", "pdf"), default=["html", "png", "svg"])
    parser.add_argument("--unit", choices=tuple(UNIT_GRAMS), default="kg", help="display unit; data are never normalized")
    parser.add_argument("--labels", type=Path, help="optional JSON mapping filenames to country/scenario/order")
    parser.add_argument("--include", nargs="+", default=["*"], help="quoted filename glob(s), e.g. '*Operation*.yaml'")
    parser.add_argument("--country-order", nargs="+", default=["India", "Norway", "USA"])
    parser.add_argument("--components", nargs="+", choices=COMPONENTS, default=list(COMPONENTS),
                        help="stack categories; defaults to all three")
    parser.add_argument("--width", type=int, default=1100, help="figure width in pixels")
    parser.add_argument("--height", type=int, default=500, help="figure height in pixels")
    parser.add_argument("--font-size", type=float, default=22, help="base font size in pixels")
    parser.add_argument("--bar-width", type=float, default=0.90, help="bar width; centers within a country are 1 unit apart")
    parser.add_argument("--group-gap", type=float, default=0.55, help="additional gap between countries")
    parser.add_argument("--tick-angle", type=int, choices=(0, -45, -90), default=0)
    parser.add_argument("--title", default="", help="optional figure title; omitted by default for paper captions")
    parser.add_argument("--scale", type=float, default=3, help="PNG resolution multiplier (not data scaling)")
    parser.add_argument("--no-total-labels", action="store_true")
    parser.add_argument("--skip-invalid", action="store_true", help="explicitly skip invalid reports instead of stopping")
    parser.add_argument("--show", action="store_true", help="open the HTML in your browser")
    args = parser.parse_args(argv)
    if args.width < 500 or args.height < 250 or not 8 <= args.font_size <= 48:
        parser.error("use width >= 500, height >= 250, and font-size between 8 and 48")
    if not 0 < args.bar_width <= 1 or not 0 <= args.group_gap <= 5 or not 0 < args.scale <= 10:
        parser.error("bar-width must be in (0,1], group-gap in [0,5], scale in (0,10]")
    if len(set(args.components)) != len(args.components):
        parser.error("components must not be repeated")
    try:
        reports = load_reports(args.directory, read_label_overrides(args.labels), args.include, args.skip_invalid)
        fig, reports = build_figure(
            reports, unit=args.unit, components=args.components, country_order=args.country_order,
            width=args.width, height=args.height, font_size=args.font_size, bar_width=args.bar_width,
            group_gap=args.group_gap, title=args.title, totals=not args.no_total_labels,
            tick_angle=args.tick_angle,
        )
        print("Plotting absolute emissions (no normalization). Label mapping:")
        for r in reports:
            print(f"  {r.path.name} -> {r.country} / {r.scenario.replace(chr(10), ' ')}")
        return 0 if save_outputs(fig, reports, args) else 1
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
