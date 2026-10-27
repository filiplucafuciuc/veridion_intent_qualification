"""Profile the company JSONL dataset and write reproducible reports."""

from __future__ import annotations

import argparse
import ast
import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any


def parse_embedded_mapping(value: Any) -> Any:
    """Parse fields that may be dictionaries or serialized Python mappings."""
    if not isinstance(value, str):
        return value
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"Expected an object on line {line_number}")
        rows.append(row)
    return rows


def quantiles(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {}
    return {
        name: ordered[round((len(ordered) - 1) * fraction)]
        for name, fraction in (
            ("min", 0.0),
            ("p25", 0.25),
            ("median", 0.5),
            ("p75", 0.75),
            ("p90", 0.9),
            ("p95", 0.95),
            ("max", 1.0),
        )
    }


def profile(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    field_coverage: dict[str, dict[str, int]] = {}
    for field in sorted({key for row in rows for key in row}):
        null_count = sum(row.get(field) is None for row in rows)
        empty_count = sum(row.get(field) in ("", []) for row in rows)
        field_coverage[field] = {
            "present": total - null_count,
            "null": null_count,
            "empty": empty_count,
        }

    countries: Counter[str] = Counter()
    primary_naics: Counter[str] = Counter()
    raw_types: dict[str, Counter[str]] = {}
    for field in ("address", "primary_naics", "secondary_naics"):
        raw_types[field] = Counter(type(row.get(field)).__name__ for row in rows)

    for row in rows:
        address = parse_embedded_mapping(row.get("address"))
        if isinstance(address, dict):
            countries[address.get("country_code", "unknown")] += 1
        naics = parse_embedded_mapping(row.get("primary_naics"))
        if isinstance(naics, dict):
            primary_naics[naics.get("label", "unknown")] += 1

    list_fields: dict[str, dict[str, Any]] = {}
    for field in ("business_model", "target_markets", "core_offerings"):
        lengths = [
            len(row[field])
            for row in rows
            if isinstance(row.get(field), list)
        ]
        list_fields[field] = {
            "min_length": min(lengths) if lengths else None,
            "median_length": median(lengths) if lengths else None,
            "max_length": max(lengths) if lengths else None,
            "top_values": Counter(
                item
                for row in rows
                if isinstance(row.get(field), list)
                for item in row[field]
            ).most_common(15),
        }

    numeric_fields: dict[str, Any] = {}
    for field in ("year_founded", "employee_count", "revenue"):
        values = [
            float(row[field])
            for row in rows
            if isinstance(row.get(field), (int, float))
        ]
        numeric_fields[field] = {
            "count": len(values),
            "missing": total - len(values),
            "quantiles": quantiles(values),
        }

    def normalized_duplicates(field: str) -> list[tuple[str, int]]:
        values = Counter(
            str(row[field]).strip().lower()
            for row in rows
            if row.get(field) is not None
        )
        return [(value, count) for value, count in values.most_common() if count > 1]

    return {
        "record_count": total,
        "field_coverage": field_coverage,
        "raw_types": {
            field: dict(counter)
            for field, counter in raw_types.items()
        },
        "country_counts": countries.most_common(),
        "primary_naics_counts": primary_naics.most_common(25),
        "list_fields": list_fields,
        "numeric_fields": numeric_fields,
        "is_public_counts": dict(Counter(row.get("is_public") for row in rows)),
        "duplicate_websites": normalized_duplicates("website"),
        "duplicate_operational_names": normalized_duplicates("operational_name"),
        "description_length": quantiles(
            [float(len(row["description"])) for row in rows if row.get("description")]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Path to companies.jsonl")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/data_profile.json"),
        help="Profile output path",
    )
    args = parser.parse_args()

    report = profile(load_rows(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output} for {report['record_count']} records")


if __name__ == "__main__":
    main()
