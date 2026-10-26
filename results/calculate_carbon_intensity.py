#!/usr/bin/env python3
"""
Calculate a generation-weighted carbon intensity for one Area and Year.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import tempfile
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
import yaml

# Naming equivalents only: do not map a mixed category to a single fuel.
SOURCE_ALIASES = {"hydro": "hydropower", "bioenergy": "biomass"}
AGGREGATE_SOURCES = {
    "wind and solar", "hydro, bioenergy and other renewables", "renewables",
    "clean", "fossil", "total generation",
}
NON_GENERATION_SOURCES = {"net imports", "demand"}
REQUIRED_HEADERS = {
    "area": "Area",
    "year": "Year",
    "source": "Electricity source",
    "share": "Share of generation (%)",
}
AGGREGATE_HEADERS = {
    "isaggregateseries", "isaggregate", "aggregate", "aggregated",
    "isaggregated", "electricitysourceaggregated", "electricitysourceisaggregate",
}
# Explicitly selected by --headerless, never silently assumed for other files.
# One-based positions: Area 1, Year 3, source 5, aggregate flag 6, share 10.
HEADERLESS_COLUMNS = {"area": 0, "year": 2, "source": 4, "aggregate": 5, "share": 9}
HUNDRED = Decimal("100")
ZERO = Decimal("0")
FACTOR_RE = re.compile(
    r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*g\s*/\s*kwh\s*$",
    re.IGNORECASE,
)


def name_key(value: str) -> str:
    """Case-insensitive, whitespace-tolerant matching, not fuzzy matching."""
    return " ".join(value.split()).casefold()


def header_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys rather than silently keeping the last value."""


def unique_mapping(loader: UniqueKeyLoader, node: yaml.MappingNode) -> dict:
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str):
            raise ValueError("source.yaml must have string source names as keys")
        if key in result:
            raise ValueError(f"duplicate YAML source key: {key!r}")
        result[key] = loader.construct_object(value_node, deep=True)
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping
)


def nonnegative_decimal(value: str, context: str) -> Decimal:
    try:
        number = Decimal(value.strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{context}: expected a number, got {value!r}") from exc
    if not number.is_finite() or number < 0:
        raise ValueError(f"{context}: must be finite and non-negative, got {value!r}")
    return number


def numeric(value: Decimal) -> float:
    """Write portable YAML numbers without rounding intermediate calculations."""
    result = float(value)
    if not (-float("inf") < result < float("inf")):
        raise ValueError("a calculated value is too large to serialize")
    return result


def load_factors(path: Path) -> dict[str, tuple[str, Decimal]]:
    with path.open(encoding="utf-8-sig") as stream:
        data = yaml.load(stream, Loader=UniqueKeyLoader)
    if not isinstance(data, Mapping) or not data:
        raise ValueError("source.yaml must be a non-empty mapping of sources to g / kWh values")
    factors = {}
    for source, value in data.items():
        key = name_key(source)
        if not key:
            raise ValueError("source.yaml contains an empty source name")
        if key in factors:
            raise ValueError(f"duplicate source after case/whitespace matching: {source!r}")
        match = FACTOR_RE.fullmatch(value) if isinstance(value, str) else None
        if match is None:
            raise ValueError(f"{source!r}: expected a value such as '24 g / kWh', got {value!r}")
        factors[key] = (source, nonnegative_decimal(match.group(1), f"factor for {source}"))
    return factors


def parse_areas(values: Sequence[str] | str) -> list[str]:
    """Accept comma-separated lists or separate names; preserve first occurrence."""
    if isinstance(values, str):
        values = [values]
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise ValueError("--area values must be country/area names")
        for part in value.split(","):
            area = " ".join(part.split())
            if not area:
                raise ValueError("--area cannot contain an empty name; check commas and quotation marks")
            key = name_key(area)
            if key not in seen:
                result.append(area)
                seen.add(key)
    if not result:
        raise ValueError("--area must contain at least one area")
    return result


def selected_rows_many(csv_path: Path, areas: Sequence[str], year: int,
                       headerless: bool) -> tuple[dict[str, list[dict]], dict]:
    """Scan once; return rows keyed by normalized area names in requested order.

    Every requested area must be present for this year. A failure never
    silently changes the set of countries used as the normalization reference.
    """
    requested = {name_key(area): area for area in parse_areas(areas)}
    selected: dict[str, list[dict]] = {key: [] for key in requested}
    available_years: dict[str, set[int]] = {key: set() for key in requested}
    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        if headerless:
            columns = dict(HEADERLESS_COLUMNS)
            column_info = {key: value + 1 for key, value in columns.items()}
        else:
            headers = next((row for row in reader if any(cell.strip() for cell in row)), None)
            if headers is None:
                raise ValueError(f"CSV is empty: {csv_path}")
            positions: dict[str, int] = {}
            duplicates: list[str] = []
            for i, header in enumerate(headers):
                key = header_key(header)
                if key and key in positions:
                    duplicates.append(header)
                if key:
                    positions[key] = i
            missing = [label for label in REQUIRED_HEADERS.values() if header_key(label) not in positions]
            if missing:
                raise ValueError(
                    f"CSV header is missing: {', '.join(missing)}. "
                    "For an extract without a header, use --headerless only when it has "
                    "the supplied norway.csv layout (Area=1, Year=3, source=5, "
                    "aggregate=6, share=10; one-based positions)."
                )
            if duplicates:
                raise ValueError(f"duplicate CSV header: {duplicates[0]!r}")
            columns = {key: positions[header_key(label)] for key, label in REQUIRED_HEADERS.items()}
            aggregates = [i for key, i in positions.items() if key in AGGREGATE_HEADERS]
            if len(aggregates) > 1:
                raise ValueError("more than one possible aggregate-flag column was found")
            if aggregates:
                columns["aggregate"] = aggregates[0]
            column_info = {key: headers[i] for key, i in columns.items()}

        for row in reader:
            if not any(cell.strip() for cell in row):
                continue
            if len(row) <= columns["area"]:
                raise ValueError(f"CSV line {reader.line_num}: missing Area field")
            area_key = name_key(row[columns["area"]])
            if area_key not in requested:
                continue
            if len(row) <= columns["year"]:
                raise ValueError(f"CSV line {reader.line_num}: missing Year field")
            raw_year = row[columns["year"]].strip()
            if not re.fullmatch(r"[0-9]{1,4}", raw_year):
                raise ValueError(f"CSV line {reader.line_num}: invalid Year {raw_year!r}")
            row_year = int(raw_year)
            available_years[area_key].add(row_year)
            if row_year != year:
                continue
            if len(row) <= max(columns.values()):
                raise ValueError(f"CSV line {reader.line_num}: too few columns for the selected fields")
            entry = {key: row[i].strip() for key, i in columns.items()}
            entry["csv_line"] = reader.line_num
            selected[area_key].append(entry)
    errors = []
    for key, area in requested.items():
        if selected[key]:
            continue
        years = available_years[key]
        suffix = (f" Available years: {', '.join(map(str, sorted(years)))}."
                  if years else " Use the full CSV Area name; matching ignores case/extra whitespace.")
        errors.append(f"no rows found for Area={area!r}, Year={year}.{suffix}")
    if errors:
        raise ValueError("Requested area/year data missing; no output written:\n" + "\n".join(errors))
    return selected, column_info


def selected_rows(csv_path: Path, area: str, year: int, headerless: bool) -> tuple[list[dict], dict]:
    """Compatibility wrapper for callers selecting exactly one area."""
    areas = parse_areas([area])
    if len(areas) != 1:
        raise ValueError("selected_rows expects one area; use selected_rows_many for multiple areas")
    grouped, columns = selected_rows_many(csv_path, areas, year, headerless)
    return grouped[name_key(areas[0])], columns


def is_aggregate(value: str, line: int) -> bool:
    key = value.strip().casefold()
    if key in {"true", "1", "yes"}:
        return True
    if key in {"false", "0", "no", ""}:
        return False
    raise ValueError(f"CSV line {line}: invalid aggregate flag {value!r}")


def _calculate_area(rows: Sequence[dict], factors: Mapping[str, tuple[str, Decimal]],
                    *, year: int, allow_unmatched: bool = False) -> tuple[dict[str, Any], Decimal]:
    """Return an auditable per-area report and its unrounded intensity."""
    if not rows:
        raise ValueError("no rows supplied for this Area/Year")
    if len({name_key(row["area"]) for row in rows}) != 1:
        raise ValueError("calculate expects rows for one area only")
    matched: list[dict] = []
    unmatched: list[dict] = []
    excluded: list[dict] = []
    seen: set[str] = set()
    notes: list[str] = []
    for row in rows:
        source, line = row["source"], row["csv_line"]
        key = name_key(source)
        if not key:
            raise ValueError(f"CSV line {line}: Electricity source is empty")
        reason = None
        if key in NON_GENERATION_SOURCES:
            reason = "demand or net trade, not an individual generation source"
        elif key in AGGREGATE_SOURCES or is_aggregate(row.get("aggregate", ""), line):
            reason = "aggregate category; individual sources are counted instead"
        if reason:
            excluded.append({"electricity_source": source, "csv_line": line, "reason": reason})
            continue
        if key in seen:
            raise ValueError(f"CSV line {line}: duplicate generation source {source!r} for this Area/Year")
        seen.add(key)
        share = nonnegative_decimal(row["share"], f"CSV line {line}, Share of generation (%)")
        if share > HUNDRED:
            raise ValueError(f"CSV line {line}: generation share exceeds 100%")
        # An exact normalized name takes precedence; aliases bridge known spellings.
        target = key if key in factors else SOURCE_ALIASES.get(key, key)
        common = {"electricity_source": source, "csv_line": line, "share": share}
        if target not in factors:
            unmatched.append(common)
            continue
        yaml_source, factor = factors[target]
        matched.append({**common, "yaml_source": yaml_source, "factor": factor})

    nonzero_unmatched = [row for row in unmatched if row["share"] > 0]
    if nonzero_unmatched:
        details = ", ".join(f"{row['electricity_source']} ({row['share']}%)" for row in nonzero_unmatched)
        message = f"No source.yaml factor for: {details}."
        if not allow_unmatched:
            raise ValueError(message + " Add explicit factors to source.yaml, or use --allow-unmatched "
                             "to calculate only from matched sources (and record the missing coverage).")
        notes.append(message + " These sources are excluded, not assigned zero emissions. "
                     "The unnormalized intensity and its cross-area normalized value omit their contributions. "
                     "The separate share_normalized intensity describes only the matched generation mix.")

    matched_share = sum((row["share"] for row in matched), ZERO)
    unmatched_share = sum((row["share"] for row in unmatched), ZERO)
    generation_share = matched_share + unmatched_share
    if matched_share <= 0:
        raise ValueError("matched sources have zero total generation share; a share-normalized mean is undefined")
    if generation_share != HUNDRED:
        notes.append(f"Individual generation shares sum to {generation_share}%, not 100%. "
                     "This may reflect rounding or missing rows; no shares are filled in.")
    weighted_sum = sum((row["share"] * row["factor"] for row in matched), ZERO)
    unnormalized = weighted_sum / HUNDRED
    share_normalized = weighted_sum / matched_share

    report = {
        "area": rows[0]["area"],
        "year": year,
        "unit": "g / kWh",
        "coverage": {
            "selected_csv_rows": len(rows),
            "individual_generation_sources": len(matched) + len(unmatched),
            "generation_share_percent": numeric(generation_share),
            "matched_share_percent": numeric(matched_share),
            "unmatched_share_percent": numeric(unmatched_share),
            "all_nonzero_generation_sources_matched": not nonzero_unmatched,
            "generation_share_difference_from_100_percent": numeric(generation_share - HUNDRED),
        },
        "unnormalized": {
            "carbon_intensity_g_per_kwh": numeric(unnormalized),
            "denominator_percent": 100.0,
            "weight_sum": numeric(matched_share / HUNDRED),
            "formula": "sum(share_percent * factor_g_per_kwh) / 100",
            "interpretation": "Original-share contribution of matched sources; incomplete when sources are unmatched.",
        },
        "share_normalized": {
            "carbon_intensity_g_per_kwh": numeric(share_normalized),
            "denominator_percent": numeric(matched_share),
            "weight_sum": 1.0,
            "formula": "sum(share_percent * factor_g_per_kwh) / sum(matched_share_percent)",
            "interpretation": "Weighted mean of matched sources only, with their shares rescaled to 100%.",
        },
        "sources": [
            {
                "electricity_source": row["electricity_source"],
                "yaml_source": row["yaml_source"],
                "csv_line": row["csv_line"],
                "share_of_generation_percent": numeric(row["share"]),
                "normalized_share_percent": numeric(row["share"] / matched_share * HUNDRED),
                "factor_g_per_kwh": numeric(row["factor"]),
                "unnormalized_contribution_g_per_kwh": numeric(row["share"] * row["factor"] / HUNDRED),
                "share_normalized_contribution_g_per_kwh": numeric(row["share"] * row["factor"] / matched_share),
            }
            for row in matched
        ],
        "unmatched_sources": [
            {"electricity_source": row["electricity_source"], "csv_line": row["csv_line"],
             "share_of_generation_percent": numeric(row["share"]),
             "reason": "no matching factor in source.yaml"}
            for row in unmatched
        ],
        "excluded_rows": excluded,
        "warnings": notes,
    }

    return report, unnormalized


def calculate(rows: Sequence[dict], factors: Mapping[str, tuple[str, Decimal]],
              *, year: int, allow_unmatched: bool = False) -> dict[str, Any]:
    """Compute one area before cross-area scaling; see calculate_areas for scaling."""
    report, _ = _calculate_area(rows, factors, year=year, allow_unmatched=allow_unmatched)
    return report


def calculate_areas(grouped_rows: Mapping[str, Sequence[dict]],
                    factors: Mapping[str, tuple[str, Decimal]], *, year: int,
                    allow_unmatched: bool = False) -> dict[str, Any]:
    """Normalize original-share intensities against the selected maximum, not a minimum.

    Decimal values are retained through division by the maximum. Only the YAML
    representation is converted to portable floating-point numbers.
    """
    if not grouped_rows:
        raise ValueError("no areas supplied for calculation")
    calculations: list[tuple[dict[str, Any], Decimal]] = []
    errors: list[str] = []
    for key, rows in grouped_rows.items():
        area = rows[0]["area"] if rows else key
        try:
            calculations.append(_calculate_area(rows, factors, year=year,
                                                allow_unmatched=allow_unmatched))
        except (ValueError, InvalidOperation, OverflowError) as exc:
            errors.append(f"Area={area!r}: {exc}")
    if errors:
        raise ValueError("Area calculation failed; no output written:\n" + "\n".join(errors))

    maximum = max(intensity for _, intensity in calculations)
    all_zero = maximum == ZERO
    maximum_areas = [report["area"] for report, intensity in calculations if intensity == maximum]
    areas: list[dict[str, Any]] = []
    for report, intensity in calculations:
        relative = ZERO if all_zero else intensity / maximum
        # Keep the two requested values adjacent; retain the former share-based
        # normalization separately, with its original physical unit.
        item = dict(report)
        share_normalized = item.pop("share_normalized")
        tail = {key: item.pop(key) for key in ("sources", "unmatched_sources", "excluded_rows", "warnings")}
        item["normalized"] = {"value": numeric(relative), "unit": "dimensionless"}
        item["share_normalized"] = share_normalized
        item.update(tail)
        areas.append(item)

    notes: list[str] = []
    if all_zero:
        notes.append("All selected carbon intensities are zero; normalized values are set to 0, "
                     "avoiding division by zero. There is no positive maximum to map to 1.")
    if any(not report["coverage"]["all_nonzero_generation_sources_matched"] for report in areas):
        notes.append("Some nonzero generation sources have no factor and were explicitly omitted. "
                     "Relative normalization uses these incomplete original-share intensities; "
                     "it does not correct missing coverage. See each area's unmatched_sources.")

    return {
        "schema_version": 2,
        "year": year,
        "unit": "g / kWh",
        "normalization": {
            "method": "divide_by_selected_maximum",
            "basis": "unnormalized.carbon_intensity_g_per_kwh",
            "scope": "only the selected areas for the requested year",
            "formula": "area_intensity / max(selected_area_intensities)",
            "unit": "dimensionless",
            "maximum_carbon_intensity_g_per_kwh": numeric(maximum),
            "maximum_areas": maximum_areas,
            "zero_reference_g_per_kwh": 0.0,
            "subtract_minimum": False,
            "all_intensities_zero": all_zero,
            "zero_maximum_policy": "set all normalized values to 0",
        },
        "areas": areas,
        "warnings": notes,
    }


def write_yaml(path: Path, result: Mapping) -> None:
    """Create all parent directories, then atomically replace the exact filename."""
    serialized = yaml.safe_dump(dict(result), sort_keys=False, allow_unicode=True, width=100)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, prefix=f".{path.name}.",
                                         suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(serialized)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--area", "--areas", required=True, nargs="+", action="extend", metavar="AREA",
                        help="full CSV Area names, case-insensitive; accepts a comma-separated list, "
                        "separate quoted names, or repeated --area flags")
    parser.add_argument("--year", type=int, required=True, help="CSV Year, e.g. 2025")
    parser.add_argument("--csv", type=Path, default=Path("results/release_generation_yearly_global.csv"),
                        help="generation CSV (default: results/release_generation_yearly_global.csv)")
    parser.add_argument("--sources", type=Path, default=Path("models/carbon_intensity/source.yaml"),
                        help="emissions factor YAML (default: models/carbon_intensity/source.yaml)")
    parser.add_argument("--output", type=Path, required=True,
                        help="exact output YAML filename; missing parent folders are created")
    parser.add_argument("--headerless", action="store_true",
                        help="read the supplied snippet layout rather than named CSV headers")
    parser.add_argument("--allow-unmatched", action="store_true",
                        help="explicitly permit missing factors; record/exclude those sources, never guess factors")
    args = parser.parse_args(argv)
    try:
        areas = parse_areas(args.area)
    except ValueError as exc:
        parser.error(str(exc))
    if not 1 <= args.year <= 9999:
        parser.error("--year must be between 1 and 9999")
    try:
        if args.output.resolve() in {args.csv.resolve(), args.sources.resolve()}:
            raise ValueError("--output must not overwrite either input file")
        factors = load_factors(args.sources)
        rows, columns = selected_rows_many(args.csv, areas, args.year, args.headerless)
        result = calculate_areas(rows, factors, year=args.year, allow_unmatched=args.allow_unmatched)
        result["inputs"] = {
            "requested_areas": areas,
            "csv": str(args.csv.resolve()),
            "source_yaml": str(args.sources.resolve()),
            "headerless": args.headerless,
            "column_names" if not args.headerless else "column_positions_1_based": columns,
            "source_aliases": SOURCE_ALIASES,
            "allow_unmatched": args.allow_unmatched,
        }
        for note in result["warnings"]:
            print(f"WARNING: {note}", file=sys.stderr)
        for item in result["areas"]:
            for note in item["warnings"]:
                print(f"WARNING [{item['area']}]: {note}", file=sys.stderr)
        write_yaml(args.output, result)
        maximum = result["normalization"]["maximum_carbon_intensity_g_per_kwh"]
        print(f"Year: {args.year} | Selected areas: {len(result['areas'])}")
        print(f"Normalization reference (selected maximum): {maximum:.8f} g / kWh")
        for item in result["areas"]:
            print(f"Area: {item['area']}")
            print(f"  Matched generation share: {item['coverage']['matched_share_percent']:.6f}%")
            print(f"  Unnormalized: {item['unnormalized']['carbon_intensity_g_per_kwh']:.8f} g / kWh")
            print(f"  Normalized:   {item['normalized']['value']:.8f} (dimensionless)")
        print(f"Saved: {args.output}")
        return 0
    except (OSError, ValueError, csv.Error, yaml.YAMLError, InvalidOperation, OverflowError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
