"""Compute objective checks that do not require a relevance answer key."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="reports/hybrid_baseline.json")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    total = sum(len(item["results"][: args.limit]) for item in report)
    hard_violations = sum(
        1
        for item in report
        for result in item["results"][: args.limit]
        if result["decision"] == "match"
        and any(
            name in {"location", "employee_count", "revenue", "year_founded", "is_public"}
            for name in result["violated_constraints"]
        )
    )
    duplicate_rows = 0
    for item in report:
        names = [
            result["name"]
            for result in item["results"][: args.limit]
            if result["name"] is not None
        ]
        duplicate_rows += len(names) - len(set(names))
    print(f"evaluated_results={total}")
    print(f"match_with_hard_violations={hard_violations}")
    print(f"duplicate_name_rows={duplicate_rows}")


if __name__ == "__main__":
    main()
