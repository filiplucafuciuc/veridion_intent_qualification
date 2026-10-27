"""Run the structured baseline for one query."""

from __future__ import annotations

import argparse

from src.data import load_companies
from src.query import parse_query
from src.structured import rank_companies


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--data", default="companies.jsonl")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    parsed = parse_query(args.query)
    print("Parsed query:")
    print(f"  industries={parsed.industries}")
    print(f"  countries={parsed.countries}")
    print(f"  regions={parsed.regions}")
    print(f"  numeric_constraints={parsed.numeric_constraints}")
    print(f"  required_attributes={parsed.required_attributes}")
    print()
    for result in rank_companies(load_companies(args.data), parsed, args.limit):
        evidence = "; ".join(
            f"{item.name}: {item.state} ({item.evidence})"
            for item in result.constraints
            if item.state != "not_applicable"
        )
        print(
            f"{result.company.operational_name or '<unnamed>'} | "
            f"{result.decision} | score={result.score:.3f} | "
            f"confidence={result.confidence:.3f} | {evidence}"
        )


if __name__ == "__main__":
    main()
