#!/usr/bin/env python3
"""ACT carbon heatmap: fabrication on x, operation on y.

Requires Python 3.10+.
Install: python -m pip install PyYAML "plotly>=6.1.1"
Run:     python generate_heatmap_dynamic.py ./results --show

The default is an 8 x 8 matrix, ordered on BOTH axes as:
Taiwan, USA, China, Norway, France, Germany, UK, India.
Rows run from top to bottom. Each cell is ONE report, not a combination of
emissions taken from different files. Values are absolute kg CO2e by default.

LOCATION LABELS
  The recommended filenames are fab_Taiwan__op_Norway.yaml, etc.
  Both role-first and country-first names work, in either axis order:
    fab_Taiwan__op_Norway.yaml
    operation_Norway_fabrication_Taiwan.yml
    TaiwanFabricationNorwayOperation.yaml
  Case, spaces, underscores, and hyphens are ignored in these tagged names.
  Untagged names such as Taiwan_Norway.yaml are NOT guessed.

  Alternatively, arbitrary filenames can use country-valued YAML fields:
    fabrication_location / fabrication_country / fab_ci
    operation_location   / operation_country   / op_ci
  Use --fabrication-key and --operation-key for other fields (dot paths work).
  Numeric carbon intensities do not identify countries and are not guessed.

  An optional --labels locations.json explicitly overrides either axis:
    {"report.yaml": {"fabrication": "Taiwan", "operation": "Norway"}}
  Keys are paths relative to the results directory, using forward slashes.
  Without an override, recognized YAML and filename labels must agree.
  Labels never change the emissions or validate the simulation settings.

EMISSIONS AND OUTPUTS
  Reads total_carbon.operation, .fabrication, and .packaging just like the
  supplied bar-chart script: bare numbers are grams; supported mass strings
  are converted to grams; absent known components become zero; negative,
  nonfinite, invalid, and nonzero unknown categories are rejected.
  Defaults to all three components. --components selects a subset.
  Duplicate pairs are errors. Missing pairs are errors unless --allow-missing
  is set, which displays them as N/A, not zero. No averaging or interpolation.

  Always writes a .matrix.csv and .data.json audit. HTML is the default chart
  output and embeds Plotly for offline use. For static PNG/SVG/PDF export:
    python -m pip install --upgrade "plotly>=6.1.1" "kaleido>=1"
    plotly_get_chrome
    python generate_heatmap_dynamic.py ./results --formats html png svg
  Chrome/Chromium is needed only for static export, not HTML generation.
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import html
import json
import math
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

try:
    import plotly.graph_objects as go
    import yaml
except ImportError as exc:
    raise SystemExit(
        'Install dependencies: python -m pip install PyYAML "plotly>=6.1.1"'
    ) from exc

COMPONENTS = ("operation", "fabrication", "packaging")
COUNTRIES = ("Taiwan", "USA", "China", "Norway", "France", "Germany", "UK", "India")
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
    "taiwan": "Taiwan", "twn": "Taiwan", "tw": "Taiwan",
    "usa": "USA", "us": "USA", "unitedstates": "USA", "unitedstatesofamerica": "USA",
    "uk": "UK", "gb": "UK", "gbr": "UK", "unitedkingdom": "UK", "greatbritain": "UK", "england": "UK",
    "norway": "Norway", "nor": "Norway", "no": "Norway", "norwegian": "Norway",
    "france": "France", "fra": "France", "fr": "France",
    "germany": "Germany", "deu": "Germany", "de": "Germany",
    "china": "China", "chn": "China", "cn": "China",
    "india": "India", "ind": "India", "in": "India",
}
LOCATION_KEYS = {
    "fabrication": ("fabrication_location", "fabrication_country", "fab_ci"),
    "operation": ("operation_location", "operation_country", "op_ci"),
}
_COUNTRY_RE = "(?:" + "|".join(sorted(COUNTRY_NAMES, key=len, reverse=True)) + ")"
_FAB = rf"(?P<fabrication>{_COUNTRY_RE})"
_OP = rf"(?P<operation>{_COUNTRY_RE})"
_FILENAME_PATTERNS = tuple(re.compile(pattern) for pattern in (
    rf"(?:fabrication|fab){_FAB}(?:operation|op){_OP}",
    rf"(?:operation|op){_OP}(?:fabrication|fab){_FAB}",
    rf"{_FAB}(?:fabrication|fab){_OP}(?:operation|op)",
    rf"{_OP}(?:operation|op){_FAB}(?:fabrication|fab)",
))


@dataclass
class Report:
    path: Path
    fabrication: str
    operation: str
    grams: dict[str, float]
    location_sources: dict[str, list[str]]

    def displayed_grams(self, components: Sequence[str]) -> float:
        value = sum(self.grams[c] for c in components)
        if not math.isfinite(value):
            raise ValueError(f"{self.path.name}: the sum of carbon values is too large to plot")
        return value


def extract_grams(value: object) -> float:
    """Same mass parsing and validation as the supplied bar-chart script."""
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


def country_name(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    key = re.sub(r"[\s_.-]+", "", value.strip().casefold())
    return COUNTRY_NAMES.get(key)


def filename_locations(path: Path) -> dict[str, str]:
    stem = re.sub(r"[\s_.-]+", "", path.stem.casefold())
    for pattern in _FILENAME_PATTERNS:
        match = pattern.fullmatch(stem)
        if match:
            return {axis: COUNTRY_NAMES[value] for axis, value in match.groupdict().items()}
    return {}


def nested_value(data: Mapping, key: str) -> object:
    """Accept a top-level key or a dot-separated path into nested mappings."""
    if key in data:
        return data[key]
    value: object = data
    for part in key.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return value


def read_label_overrides(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    with path.open(encoding="utf-8-sig") as stream:
        labels = json.load(stream)
    if not isinstance(labels, dict):
        raise ValueError("the label file must be a JSON object keyed by relative filename")
    result = {}
    for name, entry in labels.items():
        if not isinstance(entry, dict) or not entry:
            raise ValueError(f"label entry {name!r} must be a non-empty object")
        if set(entry) - {"fabrication", "operation"}:
            raise ValueError(f"{name!r}: label keys must be 'fabrication' and/or 'operation'")
        result[name] = {}
        for axis, raw in entry.items():
            country = country_name(raw)
            if country is None:
                raise ValueError(f"{name!r}: unsupported {axis} country {raw!r}; use {', '.join(COUNTRIES)}")
            result[name][axis] = country
    return result


def resolve_locations(path: Path, data: Mapping, override: Mapping,
                      keys: Mapping[str, Sequence[str]]) -> tuple[dict, dict]:
    from_filename = filename_locations(path)
    locations, sources = {}, {}
    for axis in ("fabrication", "operation"):
        if axis in override:
            locations[axis] = override[axis]
            sources[axis] = ["explicit --labels override"]
            continue
        candidates = []
        for key in keys[axis]:
            country = country_name(nested_value(data, key))
            if country is not None:
                candidates.append((f"YAML:{key}", country))
        if axis in from_filename:
            candidates.append(("tagged filename", from_filename[axis]))
        choices = {country for _, country in candidates}
        if len(choices) > 1:
            details = ", ".join(f"{source}={country}" for source, country in candidates)
            raise ValueError(f"conflicting {axis} locations ({details}); correct the labels "
                             "or explicitly choose one with --labels")
        if not choices:
            raise ValueError(
                f"cannot identify {axis} country. Use country-valued YAML fields "
                f"{', '.join(keys[axis])}, a filename like fab_Taiwan__op_Norway.yaml, "
                f"--{axis}-key, or --labels. Numeric intensities are not countries."
            )
        locations[axis] = next(iter(choices))
        sources[axis] = [source for source, _ in candidates]
    return locations, sources


def load_reports(directory: Path, labels: Mapping, patterns: Sequence[str], *,
                 keys: Mapping[str, Sequence[str]] = LOCATION_KEYS,
                 recursive: bool = False, skip_invalid: bool = False) -> list[Report]:
    if not directory.is_dir():
        raise ValueError(f"results directory does not exist: {directory}")
    candidates = directory.rglob("*") if recursive else directory.iterdir()
    files = sorted(
        (p for p in candidates if p.is_file() and p.suffix.lower() in (".yaml", ".yml")
         and any(fnmatch.fnmatchcase(p.name.lower(), pat.lower()) or
                 fnmatch.fnmatchcase(p.relative_to(directory).as_posix().lower(), pat.lower())
                 for pat in patterns)),
        key=lambda p: p.relative_to(directory).as_posix().casefold(),
    )
    reports, errors = [], []
    for path in files:
        relative_name = path.relative_to(directory).as_posix()
        try:
            with path.open(encoding="utf-8-sig") as stream:
                data = yaml.safe_load(stream)
            if not isinstance(data, Mapping) or "total_carbon" not in data:
                print(f"Skipping non-report YAML: {relative_name}", file=sys.stderr)
                continue
            total = data["total_carbon"]
            if not isinstance(total, Mapping) or not any(c in total for c in COMPONENTS):
                raise ValueError("total_carbon must contain named emission categories")
            grams = {c: extract_grams(total.get(c, 0)) for c in COMPONENTS}
            for key in set(total) - set(COMPONENTS):
                if extract_grams(total[key]) != 0:
                    raise ValueError(f"non-zero extra category {key!r}; add it to COMPONENTS first")
            locations, sources = resolve_locations(path, data, labels.get(relative_name, {}), keys)
            reports.append(Report(path, locations["fabrication"], locations["operation"], grams, sources))
        except (OSError, UnicodeError, ValueError, OverflowError, yaml.YAMLError) as exc:
            errors.append(f"{relative_name}: {exc}")
    if errors:
        message = "\n".join(errors)
        if not skip_invalid:
            raise ValueError("Invalid report(s); no chart generated:\n" + message)
        print("WARNING: explicitly skipping invalid reports:\n" + message, file=sys.stderr)
    if not reports:
        raise ValueError("no valid ACT reports with total_carbon and both locations were found")
    used = {r.path.relative_to(directory).as_posix() for r in reports}
    for name in sorted(set(labels) - used):
        print(f"Note: label override has no loaded report: {name}", file=sys.stderr)
    return reports


def build_matrix(reports: Sequence[Report], *, countries: Sequence[str] = COUNTRIES,
                 components: Sequence[str] = COMPONENTS, unit: str = "kg",
                 allow_missing: bool = False) -> tuple[list, dict, list]:
    # This orientation is deliberate: matrix[operation_index][fabrication_index].
    cells = {}
    for report in reports:
        if report.fabrication not in countries or report.operation not in countries:
            raise ValueError(f"{report.path.name}: location is outside --country-order; "
                             "include that country or filter files with --include")
        pair = (report.operation, report.fabrication)
        if pair in cells:
            raise ValueError(
                f"duplicate pair: fabrication={report.fabrication}, operation={report.operation}\n"
                f"  {cells[pair].path}\n  {report.path}\n"
                "Use one report per pair, or filter one scenario with --include. "
                "Reports are never silently summed, averaged, or overwritten."
            )
        cells[pair] = report
    missing = [(operation, fabrication) for operation in countries for fabrication in countries
               if (operation, fabrication) not in cells]
    if missing and not allow_missing:
        sample = "\n".join(f"  fabrication={fab}, operation={op}" for op, fab in missing[:12])
        remainder = f"\n  ... and {len(missing) - 12} more" if len(missing) > 12 else ""
        raise ValueError(
            f"missing {len(missing)} of {len(countries) ** 2} country pairs:\n{sample}{remainder}\n"
            "Add the missing reports or use --allow-missing to show N/A cells (not zero)."
        )
    if missing:
        print(f"WARNING: {len(missing)} missing pair(s) will be N/A, not zero.", file=sys.stderr)
    divisor = UNIT_GRAMS[unit]
    matrix = [[cells[(op, fab)].displayed_grams(components) / divisor
               if (op, fab) in cells else None for fab in countries] for op in countries]
    return matrix, cells, missing


def build_figure(matrix: list, cells: Mapping, args: argparse.Namespace) -> go.Figure:
    countries = args.country_order
    divisor = UNIT_GRAMS[args.unit]
    customdata, text = [], []
    for i, operation in enumerate(countries):
        custom_row, text_row = [], []
        for j, fabrication in enumerate(countries):
            report = cells.get((operation, fabrication))
            value = matrix[i][j]
            if report is None:
                custom_row.append(["", None, None, None])
                text_row.append("")
            else:
                custom_row.append([html.escape(report.path.relative_to(args.directory).as_posix()),
                                   *(report.grams[c] / divisor for c in COMPONENTS)])
                # Preserve visibility of very small nonzero values despite rounding.
                label = f"{value:,.{args.decimals}f}"
                if value > 0 and round(value, args.decimals) == 0:
                    label = f"{value:.2g}"
                text_row.append(label)
        customdata.append(custom_row)
        text.append(text_row)
    all_components = set(args.components) == set(COMPONENTS)
    metric = "Total carbon" if all_components else " + ".join(c.capitalize() for c in args.components)
    colorbar_title = "Total carbon" if all_components else " +<br>".join(c.capitalize() for c in args.components)
    hover = ("<b>Fabrication: %{x}</b><br>Operation: %{y}<br>"
             + metric + ": %{z:,.6g} " + args.unit + " CO\u2082e<br>"
             + "<br>".join(c.capitalize() + f": %{{customdata[{i + 1}]:,.6g}} "
                            + args.unit + " CO\u2082e" for i, c in enumerate(COMPONENTS))
             + "<br>File: %{customdata[0]}<extra></extra>")
    values = [value for row in matrix for value in row if value is not None]
    lower, upper = min(values), max(values)
    # A constant/all-zero dataset must not acquire an artificial negative scale.
    if lower == upper:
        lower, upper = 0.0, upper if upper > 0 else 1.0
    fig = go.Figure(go.Heatmap(
        x=list(countries), y=list(countries), z=matrix,
        text=text, texttemplate="" if args.no_cell_labels else "%{text}",
        textfont=dict(size=max(10, args.font_size - 4)),
        customdata=customdata, hovertemplate=hover,
        hoverongaps=False, connectgaps=False, zsmooth=False,
        xgap=2, ygap=2, colorscale=args.colorscale,
        zmin=lower, zmax=upper, zauto=False,
        colorbar=dict(title=dict(text=colorbar_title + f"<br>({args.unit} CO\u2082e)"),
                      thickness=22, len=0.88, tickformat=",.4~g"),
    ))
    fig.update_layout(
        template="plotly_white", width=args.width, height=args.height,
        font=dict(family="Arial, Helvetica, sans-serif", size=args.font_size),
        margin=dict(l=145, r=190, t=85 if args.title else 40, b=120),
        title=dict(text=html.escape(args.title), x=0.5, xanchor="center"),
        hoverlabel=dict(font=dict(size=14)),
        xaxis=dict(title=dict(text="Fabrication location", standoff=20),
                   type="category", categoryorder="array", categoryarray=list(countries),
                   tickmode="array", tickvals=list(countries), tickangle=args.tick_angle,
                   side="bottom", showgrid=False, zeroline=False, automargin=True),
        yaxis=dict(title=dict(text="Operation location", standoff=20),
                   type="category", categoryorder="array", categoryarray=list(countries),
                   tickmode="array", tickvals=list(countries), autorange="reversed",
                   showgrid=False, zeroline=False, automargin=True),
    )
    # Heatmap text is not drawn on gaps, so missing-cell labels are annotations.
    for i, operation in enumerate(countries):
        for j, fabrication in enumerate(countries):
            if matrix[i][j] is None:
                fig.add_annotation(x=fabrication, y=operation, text="N/A", showarrow=False,
                                   font=dict(size=max(10, args.font_size - 4)))
    return fig


def save_outputs(fig: go.Figure, reports: Sequence[Report], matrix: list,
                 missing: list, args: argparse.Namespace) -> bool:
    prefix = args.output
    if prefix.suffix.lower() in (".html", ".svg", ".png", ".pdf", ".csv"):
        prefix = prefix.with_suffix("")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    destination = Path(str(prefix) + ".matrix.csv")
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow([f"Operation / Fabrication ({args.unit} CO2e)", *args.country_order])
        for country, row in zip(args.country_order, matrix):
            writer.writerow([country, *("" if value is None else value for value in row)])
    print(f"Saved matrix: {destination}")
    manifest = {
        "normalized": False,
        "display_unit": args.unit,
        "displayed_components": list(args.components),
        "matrix_orientation": "rows=operation (top to bottom); columns=fabrication (left to right)",
        "operation_order": list(args.country_order),
        "fabrication_order": list(args.country_order),
        "matrix": matrix,
        "missing_pairs": [{"fabrication": fab, "operation": op} for op, fab in missing],
        "labels_are_metadata_only_not_validation_of_simulation_settings": True,
        "reports": [{"file": str(r.path.resolve()), "fabrication": r.fabrication,
                     "operation": r.operation, "location_sources": r.location_sources,
                     "total_carbon_grams": r.grams,
                     "displayed_cell_grams": r.displayed_grams(args.components)} for r in reports],
    }
    destination = Path(str(prefix) + ".data.json")
    destination.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False),
                           encoding="utf-8")
    print(f"Saved data/label audit: {destination}")
    formats = list(dict.fromkeys(args.formats))
    if "html" in formats:
        destination = Path(str(prefix) + ".html")
        fig.write_html(str(destination), include_plotlyjs=True, full_html=True,
                       auto_open=args.show, config={"responsive": True, "displaylogo": False,
                       "toImageButtonOptions": {"format": "svg", "filename": prefix.name}})
        print(f"Saved: {destination}")
    elif args.show:
        fig.show()
    success = True
    for fmt in formats:
        if fmt == "html":
            continue
        destination = Path(str(prefix) + "." + fmt)
        try:
            fig.write_image(str(destination), format=fmt, scale=args.scale if fmt == "png" else 1)
            print(f"Saved: {destination}")
        except Exception as exc:
            success = False
            print(f"Static export failed ({fmt}): {exc}\n"
                  'Install: python -m pip install -U "plotly>=6.1.1" "kaleido>=1"\n'
                  "Install Chrome if needed: plotly_get_chrome\n"
                  "Already-saved files remain available. Use --formats html to avoid "
                  "the static-export dependency.", file=sys.stderr)
    return success


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("directory", nargs="?", type=Path, default=Path("."), help="ACT report directory")
    parser.add_argument("--output", type=Path, default=Path("carbon_heatmap"), help="output filename prefix")
    parser.add_argument("--formats", nargs="+", choices=("html", "png", "svg", "pdf"), default=["html"])
    parser.add_argument("--unit", choices=tuple(UNIT_GRAMS), default="kg", help="display unit; no normalization")
    parser.add_argument("--labels", type=Path, help="JSON mapping relative filenames to fabrication/operation")
    parser.add_argument("--fabrication-key", help="country-valued YAML key; dot-separated nested paths work")
    parser.add_argument("--operation-key", help="country-valued YAML key; dot-separated nested paths work")
    parser.add_argument("--include", nargs="+", default=["*"], help="quoted filename or relative-path glob(s)")
    parser.add_argument("--recursive", action="store_true", help="also read YAML reports in subdirectories")
    parser.add_argument("--country-order", nargs="+", default=list(COUNTRIES), help="order on both axes")
    parser.add_argument("--components", nargs="+", choices=COMPONENTS, default=list(COMPONENTS),
                        help="categories to sum in each cell; defaults to all three")
    parser.add_argument("--allow-missing", action="store_true", help="show missing pairs as N/A instead of failing")
    parser.add_argument("--skip-invalid", action="store_true", help="explicitly skip invalid reports")
    parser.add_argument("--width", type=int, default=1100, help="figure width in pixels")
    parser.add_argument("--height", type=int, default=950, help="figure height in pixels")
    parser.add_argument("--font-size", type=float, default=18, help="base font size in pixels")
    parser.add_argument("--decimals", type=int, default=2, help="cell label decimal places; saved data are unrounded")
    parser.add_argument("--no-cell-labels", action="store_true", help="hide numeric cell labels, retaining N/A")
    parser.add_argument("--colorscale", default=None, help="optional Plotly colorscale name; uses Plotly default otherwise")
    parser.add_argument("--tick-angle", type=int, choices=(0, -45, -90), default=0)
    parser.add_argument("--title", default="Carbon emissions by location", help="figure title; use an empty string to omit")
    parser.add_argument("--scale", type=float, default=3, help="PNG resolution multiplier, not data scaling")
    parser.add_argument("--show", action="store_true", help="open the chart in your browser")
    args = parser.parse_args(argv)
    if args.width < 650 or args.height < 500 or not 8 <= args.font_size <= 48:
        parser.error("use width >= 650, height >= 500, and font-size between 8 and 48")
    if not 0 <= args.decimals <= 8 or not 0 < args.scale <= 10:
        parser.error("decimals must be in [0,8] and scale in (0,10]")
    if len(set(args.components)) != len(args.components):
        parser.error("components must not be repeated")
    countries = [country_name(value) for value in args.country_order]
    if None in countries or len(set(countries)) != len(countries):
        parser.error("country-order must contain unique supported countries: " + ", ".join(COUNTRIES))
    args.country_order = countries
    keys = {axis: (getattr(args, axis + "_key"),) if getattr(args, axis + "_key") else defaults
            for axis, defaults in LOCATION_KEYS.items()}
    try:
        reports = load_reports(args.directory, read_label_overrides(args.labels), args.include,
                               keys=keys, recursive=args.recursive, skip_invalid=args.skip_invalid)
        matrix, cells, missing = build_matrix(reports, countries=args.country_order,
                                             components=args.components, unit=args.unit,
                                             allow_missing=args.allow_missing)
        fig = build_figure(matrix, cells, args)
        print(f"Plotting {len(reports)}/{len(countries) ** 2} pairs; absolute {args.unit} CO2e; "
              f"components: {', '.join(args.components)}")
        print("X = fabrication; Y = operation. Country order:", ", ".join(countries))
        for operation in countries:
            for fabrication in countries:
                report = cells.get((operation, fabrication))
                if report is not None:
                    print(f"  {report.path.relative_to(args.directory).as_posix()} -> "
                          f"fabrication={fabrication}; operation={operation}")
        return 0 if save_outputs(fig, reports, matrix, missing, args) else 1
    except (OSError, UnicodeError, ValueError, OverflowError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
