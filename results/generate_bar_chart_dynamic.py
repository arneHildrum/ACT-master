#!/usr/bin/env python3
"""
ACT country-by-country carbon breakdown, with one chart per scenario folder.
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

COLORS = {"operation": "#DCD2EB", "fabrication": "#80B1BA", "packaging": "#C9BF9C"}
OUTLINE = "#666666"
RENEWABLE_LINE_COLOR = "#D62728"
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
    "germany": "Germany", "deu": "Germany", "de": "Germany",
    "india": "India", "ind": "India", "in": "India",
    "japan": "Japan", "jpn": "Japan", "jp": "Japan",
    "nigeria": "Nigeria", "nga": "Nigeria", "ng": "Nigeria",
    "norway": "Norway", "norwegian": "Norway", "nor": "Norway", "no": "Norway",
    "russia": "Russia", "russianfederation": "Russia", "rus": "Russia", "ru": "Russia",
    "taiwan": "Taiwan", "twn": "Taiwan", "tw": "Taiwan",
    "unitedkingdom": "United Kingdom", "uk": "United Kingdom", "gb": "United Kingdom", "UK": "United Kingdom", "gbr": "United Kingdom",
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
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def country_from_filename(path: Path) -> str | None:
    stem = compact_key(path.stem)
    for alias in sorted(COUNTRY_NAMES, key=len, reverse=True):
        if not stem.startswith(alias):
            continue
        remainder = stem[len(alias):]
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


@dataclass(frozen=True)
class RenewablePercentage:
    location: str
    renew: float
    year: int | None


def country_key(value: str) -> str:
    """Normalize country names and abbreviations, preserving EU27."""
    return compact_key(COUNTRY_NAMES.get(compact_key(value), value))

def resolve_renewable_file(path: Path | None, directory: Path) -> Path:
    """Use an explicit file, or look in the working, report, and script folders."""
    if path is not None:
        if not path.is_file():
            raise ValueError(f"renewable-percentage file does not exist: {path}")
        return path
    candidates = (
        Path.cwd() / "renewable_percentage.yaml",
        directory / "renewable_percentage.yaml",
        Path(__file__).resolve().parent / "renewable_percentage.yaml",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise ValueError(
        "--double-y-axis needs renewable_percentage.yaml in the working directory, "
        "report directory, or script directory. Specify its path with --renewable-file."
    )


def load_renewable_percentages(path: Path) -> dict[str, RenewablePercentage]:
    """Read the supplied location/renew/year schema without estimating any values.

    Percentages may be numbers or numeric strings (optionally ending in '%').
    A missing year is allowed; a provided year must be a positive integer.
    Duplicate countries, including aliases such as USA/United States, are errors.
    """
    try:
        with path.open(encoding="utf-8-sig") as stream:
            data = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid renewable-percentage YAML in {path}: {exc}") from exc
    if not isinstance(data, list) or not data:
        raise ValueError(f"{path}: expected a non-empty YAML list of location/renew/year records")
    values: dict[str, RenewablePercentage] = {}
    for index, row in enumerate(data, start=1):
        context = f"{path}, record {index}"
        if not isinstance(row, Mapping):
            raise ValueError(f"{context}: each record must be a mapping")
        location = row.get("location")
        if not isinstance(location, str) or not location.strip() or not country_key(location):
            raise ValueError(f"{context}: location must be a non-empty country name")
        location = location.strip()
        raw = row.get("renew")
        if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
            raise ValueError(f"{context}: renew must be a percentage between 0 and 100")
        try:
            renew = float(raw.strip().removesuffix("%").strip() if isinstance(raw, str) else raw)
        except (ValueError, OverflowError) as exc:
            raise ValueError(f"{context}: invalid renewable percentage {raw!r}") from exc
        if not math.isfinite(renew) or not 0 <= renew <= 100:
            raise ValueError(f"{context}: renew must be finite and between 0 and 100, got {raw!r}")
        year = row.get("year")
        if year is not None and (type(year) is not int or not 1 <= year <= 9999):
            raise ValueError(f"{context}: year must be an integer from 1 to 9999 when supplied")
        key = country_key(location)
        if key in values:
            raise ValueError(
                f"{context}: duplicate country {location!r} (also {values[key].location!r}); "
                "provide exactly one record per country for the line"
            )
        values[key] = RenewablePercentage(location=location, renew=renew, year=year)
    return values


def extract_grams(value: object) -> float:
    """Parse an ACT emissions, including scientific notation and explicit units.

    Bare numeric values are treated as grams.
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
        if "/" not in name or name.split("/", 1)[0] == directory.name:
            print(f"Note: label override has no loaded report in {directory.name}: {name}", file=sys.stderr)
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


def resolve_breakdown_stacks(reports: Sequence[Report],
                             components: Sequence[str],
                             breakdown_order: Sequence[str] = ("smallest-to-largest",)
                             ) -> list[tuple[str, ...]]:
    selected = list(components)
    requested = list(breakdown_order)
    if not requested:
        raise ValueError("--breakdown-order requires a mode or a component list")
    if len(requested) == 1 and requested[0] in ("smallest-to-largest", "largest-to-smallest"):
        increasing = requested[0] == "smallest-to-largest"
        priority = {name: index for index, name in enumerate(COMPONENTS)}
        return [tuple(sorted(selected, key=lambda name: (
            report.grams[name] if increasing else -report.grams[name],
            priority[name],
        ))) for report in reports]
    if len(requested) != len(selected) or set(requested) != set(selected):
        raise ValueError(
            "--breakdown-order must be 'smallest-to-largest', 'largest-to-smallest', "
            "or each selected --components category exactly once, bottom to top "
            f"(selected: {', '.join(selected)}; got: {', '.join(requested)})"
        )
    return [tuple(requested) for _ in reports]


def build_figure(reports: list[Report], *, unit: str = "kg", components=COMPONENTS,
                 country_order: Sequence[str] = (), width: int | None = None,
                 height: int = 500, font_size: float = 22, bar_width: float = 0.90,
                 group_gap: float = 0.0, title: str = "", totals: bool = True,
                 tick_angle: int | None = None,
                 renewable_data: Mapping[str, RenewablePercentage] | None = None,
                 renewable_source: Path | None = None,
                 breakdown_order: Sequence[str] = ("smallest-to-largest",)
                 ) -> tuple[go.Figure, list[Report]]:
    """Single regular interval per report, country-only ticks, optional y2 line."""
    if not reports:
        raise ValueError("cannot plot an empty report list")
    rank = {COUNTRY_NAMES.get(compact_key(name), name).casefold(): i
            for i, name in enumerate(country_order)}
    ordered = sorted(reports, key=lambda r: (
        rank.get(r.country.casefold(), len(rank)), r.country.casefold(),
        r.order, r.path.name.casefold(),
    ))
    xs = list(range(len(ordered)))
    bar_stacks = resolve_breakdown_stacks(ordered, components, breakdown_order)
    divisor = UNIT_GRAMS[unit]
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
    left_margin = 112 if unit != "t" else 96
    right_margin = 120 if renewable_data is not None else 24
    longest_total = max(len(s) for s in total_strings)
    slot_width = max(66, longest_total * total_font * 0.56 + 12) if totals else 66
    if width is None:
        width = max(1000, int(math.ceil(left_margin + right_margin + len(ordered) * slot_width)))
    available_per_bar = (width - left_margin - right_margin) / (len(ordered) + 0.36)
    max_lines = max(label.count("<br>") + 1 for label in labels)
    longest_label = max(max(len(html.unescape(line)) for line in label.split("<br>")) for label in labels)
    label_width = longest_label * label_font * 0.56
    if tick_angle is None:
        tick_angle = 0 if label_width + 10 <= available_per_bar else -45
        if available_per_bar < label_font * 2:
            tick_angle = -90
    radians = math.radians(abs(tick_angle))
    label_depth = max_lines * label_font * 1.2 * math.cos(radians) + label_width * math.sin(radians)
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
    legend_priority = (list(breakdown_order)
                       if len(breakdown_order) > 1 else list(components))
    legend_rank = {name: index for index, name in enumerate(legend_priority)}
    shown_legend: set[str] = set()
    for level in range(len(components)):
        for component in components:
            # Keep only segments for which this component occupies this level.
            # None is an absent segment, *not* a zero-valued observation.
            ys = [r.grams[component] / divisor if bar_stacks[i][level] == component
                  else None for i, r in enumerate(ordered)]
            if all(value is None for value in ys):
                continue
            first_legend = component not in shown_legend
            shown_legend.add(component)
            fig.add_trace(go.Bar(
                x=xs, y=ys, width=bar_width, name=component.capitalize(),
                legendgroup=component, showlegend=first_legend,
                legendrank=legend_rank[component],
                marker=dict(color=COLORS[component],
                            line=dict(color=OUTLINE, width=0.75)),
                customdata=hover, cliponaxis=False,
                hovertemplate=("<b>%{customdata[1]}</b><br>Folder/scenario: %{customdata[2]}"
                               "<br>File: %{customdata[0]}<br>"
                               + component.capitalize() + ": %{y:,.3f} " + unit + " CO\u2082e"
                               + "<br>Displayed stack: %{customdata[3]:,.3f} " + unit
                               + " CO\u2082e<extra></extra>"),
            ))
    if renewable_data is not None:
        # One point per COUNTRY, located at the mean center of all its bars.
        # Fill absent countries with None; never reinterpret missing as zero.
        country_positions: dict[str, list[int]] = {}
        country_labels: dict[str, str] = {}
        for x, report in zip(xs, ordered):
            key = country_key(report.country)
            country_positions.setdefault(key, []).append(x)
            country_labels.setdefault(key, report.country)
        points = []
        for key, positions in sorted(country_positions.items(), key=lambda pair: pair[1][0]):
            record = renewable_data.get(key)
            points.append({
                "country": country_labels[key], "x": sum(positions) / len(positions),
                "source_location": record.location if record else None,
                "renew": record.renew if record else None,
                "year": record.year if record else None,
            })
        missing = [p["country"] for p in points if p["renew"] is None]
        if len(missing) == len(points):
            raise ValueError("no plotted country matches the renewable-percentage data; "
                             "check country labels, --labels, or the location records")
        if missing:
            print("WARNING: no renewable percentage for: " + ", ".join(missing)
                  + ". Leaving gaps in the line; emissions bars are unchanged.", file=sys.stderr)
        fig.add_trace(go.Scatter(
            x=[p["x"] for p in points], y=[p["renew"] for p in points],
            yaxis="y2", name="Renewable energy (%)", mode="lines+markers",
            line=dict(color=RENEWABLE_LINE_COLOR, width=3),
            marker=dict(color=RENEWABLE_LINE_COLOR, size=9),
            connectgaps=False, cliponaxis=False,
            customdata=[[html.escape(p["country"]),
                         html.escape(p["source_location"] or "Not available"),
                         str(p["year"]) if p["year"] is not None else "Not supplied"] for p in points],
            hovertemplate=("<b>%{customdata[0]}</b><br>Renewable energy: %{y:.1f}%"
                           "<br>Source location: %{customdata[1]}"
                           "<br>Year: %{customdata[2]}<extra></extra>"),
        ))
        fig.update_layout(meta={"renewable_overlay": {
            "metric": "renewable_percentage", "source_field": "renew", "unit": "%",
            "source_file": str(renewable_source.resolve()) if renewable_source else None,
            "is_carbon_intensity": False, "axis": "y2", "axis_range": [0, 100],
            "point_placement": "center of each displayed country group",
            "missing_countries": missing, "points": points,
        }})
    if totals:
        for x, y, label in zip(xs, totals_y, total_strings):
            fig.add_annotation(x=x, y=y, text=label, showarrow=False,
                               yshift=7, yanchor="bottom",
                               font=dict(size=total_font, color="#333333"))
    all_components = set(components) == set(COMPONENTS)
    ytitle = "Carbon emissions" if all_components else " + ".join(c.capitalize() for c in components)
    fig.update_layout(
        template="none", width=width, height=height, barmode="stack", bargap=0, bargroupgap=0,
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
                   showgrid=True, gridcolor="#E5E5E5", gridwidth=1, zeroline=False,
                   showline=True, linecolor="#777777", linewidth=1,
                   ticks="outside", ticklen=4, tickcolor="#777777",
                   tickfont=dict(size=font_size - 2)),
    )
    if renewable_data is not None:
        fig.update_layout(yaxis2=dict(
            title=dict(text="Renewable energy (%)", standoff=12),
            overlaying="y", side="right", anchor="x", type="linear", range=[0, 100],
            tickmode="linear", tick0=0, dtick=20, tickformat=".0f", ticksuffix="%",
            showgrid=False, zeroline=False, showline=True,
            linecolor=RENEWABLE_LINE_COLOR, linewidth=1, ticks="outside", ticklen=4,
            tickcolor=RENEWABLE_LINE_COLOR,
            tickfont=dict(size=font_size - 2, color=RENEWABLE_LINE_COLOR),
        ))
    if title:
        fig.update_layout(title=dict(text=html.escape(title), x=0.5, xanchor="center",
                                     y=0.98, yanchor="top", font=dict(size=font_size)))
    fig.update_layout(meta={**(fig.layout.meta or {}), "breakdown_stacking": {
        "mode_or_order": list(breakdown_order),
        "direction": "bottom-to-top",
        "per_report": [
            {"file": str(report.path.resolve()), "country": report.country,
             "bottom_to_top": list(stack)}
            for report, stack in zip(ordered, bar_stacks)
        ],
    }})
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
    if fig.layout.meta and "renewable_overlay" in fig.layout.meta:
        manifest["renewable_overlay"] = fig.layout.meta["renewable_overlay"]
    if fig.layout.meta and "breakdown_stacking" in fig.layout.meta:
        manifest["breakdown_stacking"] = fig.layout.meta["breakdown_stacking"]
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
    """One scenario folder, or four separate recognized scenario subfolders."""
    if not directory.is_dir():
        raise ValueError(f"results directory does not exist: {directory}")
    children = {p.name.casefold(): p for p in directory.iterdir() if p.is_dir()}
    scenarios = [children[name] for name in SCENARIO_FOLDERS if name in children]
    if scenarios:
        root_yaml = [p for p in directory.iterdir()
                     if p.is_file() and p.suffix.lower() in (".yaml", ".yml")]
        if root_yaml:
            print(f"Note: {len(root_yaml)} root-level YAML file(s) in {directory} "
                  "are not mixed into scenario charts.", file=sys.stderr)
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
                        help="country order; otherwise alphabetical")
    parser.add_argument("--components", nargs="+", choices=COMPONENTS, default=list(COMPONENTS))
    parser.add_argument("--breakdown-order", nargs="+", default=["smallest-to-largest"],
                        metavar="COMPONENT",
                        help="bar segment order from bottom to top: default "
                             "'smallest-to-largest' per bar, 'largest-to-smallest', "
                             "or custom e.g. 'fabrication operation packaging'")
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=500)
    parser.add_argument("--font-size", type=float, default=22)
    parser.add_argument("--bar-width", type=float, default=0.90)
    parser.add_argument("--group-gap", type=float, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--tick-angle", type=int, choices=(0, -45, -90), default=None)
    parser.add_argument("--title", default="", help="{scenario} expands to scenario folder label")
    parser.add_argument("--scale", type=float, default=3)
    parser.add_argument("--no-total-labels", action="store_true")
    parser.add_argument("--skip-invalid", action="store_true")
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--double-y-axis", "--dual-y-axis", dest="double_y_axis", action="store_true",
                        help="overlay renewable energy (%%) as a line on a second 0-100%% y-axis")
    parser.add_argument("--renewable-file", type=Path,
                        help="location/renew/year YAML; default: find renewable_percentage.yaml")
    args = parser.parse_args(argv)
    if ((args.width is not None and args.width < 500) or args.height < 250
            or not 8 <= args.font_size <= 48):
        parser.error("use width >= 500, height >= 250, and font-size between 8 and 48")
    if not 0 < args.bar_width <= 1 or not 0 < args.scale <= 10:
        parser.error("bar-width must be in (0,1] and scale in (0,10]")
    if len(set(args.components)) != len(args.components):
        parser.error("components must not be repeated")
    try:
        resolve_breakdown_stacks([], args.components, args.breakdown_order)
    except ValueError as exc:
        parser.error(str(exc))
    if args.renewable_file is not None and not args.double_y_axis:
        parser.error("--renewable-file requires --double-y-axis")
    if args.group_gap is not None:
        print("Note: --group-gap is deprecated and ignored; country bars are evenly spaced.",
              file=sys.stderr)
    try:
        labels = read_label_overrides(args.labels)
        directories = discover_report_directories(args.directory)
        renewable_data = None
        if args.double_y_axis:
            args.renewable_file = resolve_renewable_file(args.renewable_file, args.directory)
            renewable_data = load_renewable_percentages(args.renewable_file)
    except (OSError, ValueError, yaml.YAMLError) as exc:
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
                renewable_data=renewable_data, renewable_source=args.renewable_file,
                breakdown_order=args.breakdown_order,
            )
            per_chart = argparse.Namespace(**vars(args))
            per_chart.directory = directory
            if args.output is None:
                per_chart.output = Path("figures") / f"carbon_breakdown_{directory.name}"
            else:
                per_chart.output = output_prefix(args.output, directory, batch)
            print(f"\nScenario folder: {directory} ({len(reports)} reports)")
            print("Plotting absolute emissions. Country labels:")
            print("Breakdown stack order (bottom to top): " + " ".join(args.breakdown_order))
            for report, tick in zip(reports, fig.layout.xaxis.ticktext):
                print(f"  {report.path.name} -> {html.unescape(tick.replace('<br>', ' '))}")
            if args.double_y_axis:
                print(f"Renewable percentages: {args.renewable_file}")
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
