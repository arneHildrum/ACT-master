#!/usr/bin/env python3
"""ACT country-by-country carbon breakdown, with one chart per scenario folder.

One scenario:
  python generate_bar_chart_dynamic.py ./results/informed
All four scenario folders:
  python generate_bar_chart_dynamic.py ./results --output ./figures/carbon

Expected folders: operation, conservative, informed, exaggerated.
Report filenames may be country names alone, such as norway.yaml or EU27.yaml.
Legacy names such as norwayOperationFabrication.yaml are also recognized.

Dependencies: pip install "plotly>=6.1.1" "PyYAML>=6" "kaleido>=1"
PNG/SVG/PDF export additionally needs Chrome/Chromium (plotly_get_chrome).
Use --formats html to avoid the static-export dependency.

Country labels are display metadata inferred from filenames or op_ci. Folder
names identify the scenario; neither verifies the actual ACT configuration.
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
    "australia": "Australia", "aus": "Australia", "au": "Australia",
    "brazil": "Brazil", "brasil": "Brazil", "bra": "Brazil", "br": "Brazil",
    "canada": "Canada", "can": "Canada", "ca": "Canada",
    "china": "China", "chn": "China", "cn": "China",
    "ethiopia": "Ethiopia", "eth": "Ethiopia", "et": "Ethiopia",
    "eu27": "EU27", "eu": "EU27", "europeanunion": "EU27",
    "europeanunion27": "EU27", "europeanunion27countries": "EU27",
    "france": "France", "fra": "France", "fr": "France",
    "india": "India", "ind": "India", "in": "India",
    "japan": "Japan", "jpn": "Japan", "jp": "Japan",
    "nigeria": "Nigeria", "nga": "Nigeria", "ng": "Nigeria",
    "norway": "Norway", "norwegian": "Norway", "nor": "Norway", "no": "Norway",
    "russia": "Russia", "russianfederation": "Russia", "rus": "Russia", "ru": "Russia",
    "taiwan": "Taiwan", "twn": "Taiwan", "tw": "Taiwan",
    "usa": "USA", "us": "USA", "unitedstates": "USA",
    "unitedstatesofamerica": "USA",
}
SCENARIO_FOLDERS = ("operation", "conservative", "informed", "exaggerated")
SCENARIO_NAMES = {name: name.capitalize() for name in SCENARIO_FOLDERS}
LEGACY_SUFFIXES = (
    "operation", "fabrication", "onshore", "conservative", "informed",
    "exaggerated", "central", "electricityheavy",
)


def compact_key(value: object) -> str:
    """Keep digits: EU27 must not become EU during country matching."""
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def country_from_filename(path: Path) -> str | None:
    stem = compact_key(path.stem)
    for alias in sorted(COUNTRY_NAMES, key=len, reverse=True):
        if not stem.startswith(alias):
            continue
        remainder = stem[len(alias):]
        # Restrict prefix matching, so e.g. 'au' does not label Austria Australia.
        if not remainder or remainder.isdigit() or remainder.startswith(LEGACY_SUFFIXES):
            return COUNTRY_NAMES[alias]
    return None


def scenario_from_directory(directory: Path) -> str:
    name = directory.resolve().name
    return SCENARIO_NAMES.get(name.casefold(), name)



@dataclass
class Report:
    path: Path
    country: str
    scenario: str
    order: int
    grams: dict[str, float]


def extract_grams(value: object) -> float:
    """Parse an ACT emissions, including scientific notation and explicit units.

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
    """The filename/op_ci identifies country; the parent folder identifies scenario."""
    country = country_from_filename(path)
    if country is None:
        country = COUNTRY_NAMES.get(compact_key(data.get("op_ci", "")))
    if country is None:
        # Preserve a meaningful label for unlisted countries rather than 'Other'.
        words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", path.stem)
        words = re.sub(r"operation|fabrication|onshore", " ", words, flags=re.I)
        country = re.sub(r"[\s_-]+", " ", words).strip().title() or path.stem
    return country, scenario_from_directory(path.parent), 0


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
    return {name.replace("\\", "/"): entry for name, entry in labels.items()}


def load_reports(directory: Path, labels: Mapping, patterns: Sequence[str],
                 skip_invalid: bool = False) -> list[Report]:
    if not directory.is_dir():
        raise ValueError(f"results directory does not exist: {directory}")
    files = sorted(
        (p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in (".yaml", ".yml")
         and any(fnmatch.fnmatchcase(p.name.lower(), pattern.lower()) for pattern in patterns)),
        key=lambda p: p.name.casefold(),
    )
    reports, errors, used_overrides = [], [], set()
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
            relative_key = f"{path.parent.name}/{path.name}"
            override_key = relative_key if relative_key in labels else path.name
            override = labels.get(override_key, {})
            if override:
                used_overrides.add(override_key)
            file_country = country_from_filename(path)
            metadata_country = COUNTRY_NAMES.get(compact_key(data.get("op_ci", "")))
            if (file_country and metadata_country and file_country != metadata_country
                    and "country" not in override):
                print(f"WARNING: {path.name} names {file_country}, but op_ci names "
                      f"{metadata_country}; using the filename. Verify the report "
                      "or supply --labels.", file=sys.stderr)
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
    for name in set(labels) - used_overrides:
        # A folder-qualified override for another scenario is intentionally unused.
        if "/" not in name or name.split("/", 1)[0] == directory.name:
            print(f"Note: label override has no loaded report in {directory.name}: {name}",
                  file=sys.stderr)
    counts = Counter(r.country.casefold() for r in reports)
    for country, count in counts.items():
        if count > 1:
            print(f"WARNING: {count} reports for {country} in {directory}. "
                  "Keeping separate numbered bars; nothing is averaged or merged. "
                  "Use --include to select one run if these are duplicates.", file=sys.stderr)
    return reports


def wrap_label(value: str, width: int = 15) -> str:
    lines = []
    for line in value.splitlines() or [value]:
        lines.extend(textwrap.wrap(line, width=width, break_long_words=True) or [""])
    return "<br>".join(html.escape(line) for line in lines)


def build_figure(reports: list[Report], *, unit: str = "kg", components=COMPONENTS,
                 country_order: Sequence[str] = (), width: int | None = None,
                 height: int = 500, font_size: float = 22, bar_width: float = 0.90,
                 group_gap: float = 0.0, title: str = "", totals: bool = True,
                 tick_angle: int | None = None) -> tuple[go.Figure, list[Report]]:
    """Country ticks only, uniform spacing, no lower group headings or separators.

    group_gap is accepted for compatibility with old callers but has no effect.
    None width/angle selects a layout based on country count and label length.
    """
    if not reports:
        raise ValueError("cannot plot an empty report list")
    rank = {COUNTRY_NAMES.get(compact_key(name), name).casefold(): i
            for i, name in enumerate(country_order)}
    ordered = sorted(reports, key=lambda r: (
        rank.get(r.country.casefold(), len(rank)), r.country.casefold(),
        r.order, r.path.name.casefold(),
    ))
    # One regular interval per report. No artificial inter-country group gaps.
    xs = list(range(len(ordered)))
    divisor = UNIT_GRAMS[unit]  # Unit conversion ONLY, not normalization.
    totals_y = [sum(r.grams[c] for c in components) / divisor for r in ordered]
    largest = max(totals_y)
    if not math.isfinite(largest):
        raise ValueError("the sum of carbon values is too large to plot")
    decimals = 2 if unit == "t" or largest < 20 else (1 if largest < 200 else 0)
    total_strings = [f"{y:,.{decimals}f}" for y in totals_y]

    counts = Counter(r.country.casefold() for r in ordered)
    seen = Counter()
    labels = []
    for report in ordered:
        key = report.country.casefold()
        seen[key] += 1
        label = wrap_label(report.country, width=18)
        if counts[key] > 1:
            label += f"<br>({seen[key]})"
        labels.append(label)

    label_font = max(12, font_size - 3)
    total_font = max(11, font_size - 4)
    left_margin, right_margin = (112 if unit != "t" else 96), 24
    # Allow room for total labels without expanding short charts unnecessarily.
    longest_total = max(len(s) for s in total_strings)
    slot_width = max(66, longest_total * total_font * 0.56 + 12) if totals else 66
    if width is None:
        width = max(1000, int(math.ceil(left_margin + right_margin + len(ordered) * slot_width)))
    available_per_bar = (width - left_margin - right_margin) / (len(ordered) + 0.36)
    max_lines = max(label.count("<br>") + 1 for label in labels)
    longest_label = max(max(len(html.unescape(line)) for line in label.split("<br>"))
                        for label in labels)
    label_width = longest_label * label_font * 0.56
    if tick_angle is None:
        tick_angle = 0 if label_width + 10 <= available_per_bar else -45
        if available_per_bar < label_font * 2:
            tick_angle = -90
    radians = math.radians(abs(tick_angle))
    label_depth = (max_lines * label_font * 1.2 * math.cos(radians)
                   + label_width * math.sin(radians))
    bottom_margin = int(math.ceil(label_depth + 24))
    top_margin = int(font_size * (4.5 if title else 2.8))
    if height - bottom_margin - top_margin < 150:
        height = bottom_margin + top_margin + 150
    plot_height = height - bottom_margin - top_margin
    if totals:
        total_font = max(9, min(total_font, (available_per_bar - 8) / (longest_total * 0.56)))

    fig = go.Figure()
    hover = [[html.escape(r.path.name), html.escape(r.country),
              html.escape(r.scenario.replace("\n", " ")),
              sum(r.grams[c] for c in components) / divisor] for r in ordered]
    for component in components:
        fig.add_trace(go.Bar(
            x=xs, y=[r.grams[component] / divisor for r in ordered],
            width=bar_width, name=component.capitalize(),
            marker=dict(color=COLORS[component], line=dict(color=OUTLINE, width=0.75)),
            customdata=hover, cliponaxis=False,
            hovertemplate=("<b>%{customdata[1]}</b><br>Folder/scenario: %{customdata[2]}"
                           "<br>File: %{customdata[0]}<br>"
                           + component.capitalize() + ": %{y:,.3f} " + unit + " CO\u2082e"
                           + "<br>Displayed stack: %{customdata[3]:,.3f} " + unit
                           + " CO\u2082e<extra></extra>"),
        ))
    if totals:
        for x, y, text in zip(xs, totals_y, total_strings):
            fig.add_annotation(x=x, y=y, text=text, showarrow=False, yshift=7,
                               yanchor="bottom", font=dict(size=total_font, color="#333333"))
    # No country/scenario group annotations below the x-axis.
    # Countries appear exactly once as ordinary tick labels.
    all_components = set(components) == set(COMPONENTS)
    ytitle = "Carbon emissions" if all_components else " + ".join(c.capitalize() for c in components)
    fig.update_layout(
        template="none", width=width, height=height,
        barmode="stack", bargap=0, bargroupgap=0,
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Arial, Helvetica, sans-serif", size=font_size, color="#111111"),
        margin=dict(l=left_margin, r=right_margin, t=top_margin, b=bottom_margin),
        legend=dict(orientation="h", x=0, xanchor="left", y=1 + 20 / plot_height,
                    yanchor="bottom", font=dict(size=font_size), traceorder="normal",
                    itemsizing="constant", itemclick=False, itemdoubleclick=False),
        hoverlabel=dict(font=dict(size=15)),
        xaxis=dict(type="linear", tickmode="array", tickvals=xs, ticktext=labels,
                   tickangle=tick_angle, tickfont=dict(size=label_font), automargin=True,
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
        "source_directory": str(args.directory.resolve()),
        "scenario_folder": args.directory.name,
        "xaxis_labels": list(fig.layout.xaxis.ticktext),
        "layout": {"width": fig.layout.width, "height": fig.layout.height,
                   "tick_angle": fig.layout.xaxis.tickangle},
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


def discover_report_directories(directory: Path) -> list[Path]:
    """Read a scenario directory, or split a results root into its known children.

    Deliberately nonrecursive: baseline and sensitivity reports are not pooled.
    Unrecognized subdirectories are not loaded automatically.
    """
    if not directory.is_dir():
        raise ValueError(f"results directory does not exist: {directory}")
    children = {p.name.casefold(): p for p in directory.iterdir() if p.is_dir()}
    scenarios = [children[name] for name in SCENARIO_FOLDERS if name in children]
    if scenarios:
        root_yaml = [p for p in directory.iterdir()
                     if p.is_file() and p.suffix.lower() in (".yaml", ".yml")]
        if root_yaml:
            print(f"Note: {len(root_yaml)} root-level YAML file(s) in {directory} "
                  "are not mixed into the scenario charts. Select a single folder "
                  "containing only the reports to compare.", file=sys.stderr)
        return scenarios
    return [directory]


def output_prefix(base: Path, directory: Path, batch: bool) -> Path:
    if base.suffix.lower() in (".html", ".svg", ".png", ".pdf"):
        base = base.with_suffix("")
    return base.with_name(f"{base.name}_{directory.name}") if batch else base


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("directory", nargs="?", type=Path,
                        default=Path("results") if Path("results").is_dir() else Path("."),
                        help="scenario folder, or results root containing the four scenario folders")
    parser.add_argument("--output", type=Path, default=None,
                        help="output prefix; in batch mode each scenario folder name is appended")
    parser.add_argument("--formats", nargs="+", choices=("html", "png", "svg", "pdf"),
                        default=["html", "png", "svg"])
    parser.add_argument("--unit", choices=tuple(UNIT_GRAMS), default="kg",
                        help="display unit; data are never normalized")
    parser.add_argument("--labels", type=Path,
                        help="JSON country/scenario/order overrides keyed by filename or folder/filename")
    parser.add_argument("--include", nargs="+", default=["*"],
                        help="quoted filename glob(s), e.g. '*norway*.yaml'")
    parser.add_argument("--country-order", nargs="+", default=[],
                        help="optional country ordering; otherwise countries are alphabetical")
    parser.add_argument("--components", nargs="+", choices=COMPONENTS, default=list(COMPONENTS),
                        help="stack categories; defaults to all three")
    parser.add_argument("--width", type=int, default=None,
                        help="figure width in pixels; omitted = automatic based on bar count")
    parser.add_argument("--height", type=int, default=500, help="figure height in pixels")
    parser.add_argument("--font-size", type=float, default=22, help="base font size in pixels")
    parser.add_argument("--bar-width", type=float, default=0.90,
                        help="bar width; all adjacent centers are 1 unit apart")
    parser.add_argument("--group-gap", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--tick-angle", type=int, choices=(0, -45, -90), default=None,
                        help="country-label angle; omitted = automatic")
    parser.add_argument("--title", default="",
                        help="optional title; {scenario} expands to the scenario folder label")
    parser.add_argument("--scale", type=float, default=3,
                        help="PNG resolution multiplier (not data scaling)")
    parser.add_argument("--no-total-labels", action="store_true")
    parser.add_argument("--skip-invalid", action="store_true",
                        help="explicitly skip invalid reports instead of stopping that chart")
    parser.add_argument("--show", action="store_true", help="open HTML in your browser")
    args = parser.parse_args(argv)
    if ((args.width is not None and args.width < 500) or args.height < 250
            or not 8 <= args.font_size <= 48):
        parser.error("use width >= 500, height >= 250, and font-size between 8 and 48")
    if not 0 < args.bar_width <= 1 or not 0 < args.scale <= 10:
        parser.error("bar-width must be in (0,1] and scale in (0,10]")
    if len(set(args.components)) != len(args.components):
        parser.error("components must not be repeated")
    if args.group_gap is not None:
        print("Note: --group-gap is deprecated and ignored; country bars are evenly spaced.",
              file=sys.stderr)
    try:
        labels = read_label_overrides(args.labels)
        directories = discover_report_directories(args.directory)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    batch = any(path != args.directory for path in directories)
    successful = True
    for directory in directories:
        try:
            reports = load_reports(directory, labels, args.include, args.skip_invalid)
            fig, reports = build_figure(
                reports, unit=args.unit, components=args.components, country_order=args.country_order,
                width=args.width, height=args.height, font_size=args.font_size, bar_width=args.bar_width,
                title=args.title.replace("{scenario}", scenario_from_directory(directory)),
                totals=not args.no_total_labels, tick_angle=args.tick_angle,
            )
            per_chart = argparse.Namespace(**vars(args))
            per_chart.directory = directory
            if args.output is None:
                # Stable per-folder names prevent accidental overwriting across invocations.
                per_chart.output = Path("figures") / f"carbon_breakdown_{directory.name}"
            else:
                per_chart.output = output_prefix(args.output, directory, batch)
            print(f"\nScenario folder: {directory} ({len(reports)} reports)")
            print("Plotting absolute emissions. Country labels:")
            for report, tick in zip(reports, fig.layout.xaxis.ticktext):
                print(f"  {report.path.name} -> {html.unescape(tick.replace('<br>', ' '))}")
            print(f"Layout: {fig.layout.width} x {fig.layout.height} px, "
                  f"country label angle {fig.layout.xaxis.tickangle} degrees")
            if not save_outputs(fig, reports, per_chart):
                successful = False
        except (OSError, ValueError) as exc:
            print(f"Error in {directory}: {exc}", file=sys.stderr)
            successful = False
    return 0 if successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
