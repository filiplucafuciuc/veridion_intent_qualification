"""Build a compact comparison report for the three ranking stages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _by_query(path: Path) -> dict[str, dict]:
    return {item["query"]: item for item in json.loads(path.read_text(encoding="utf-8"))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structured", default="reports/structured_baseline.json")
    parser.add_argument("--lexical", default="reports/lexical_baseline.json")
    parser.add_argument("--hybrid", default="reports/hybrid_baseline.json")
    parser.add_argument("--output", type=Path, default=Path("reports/method_comparison.json"))
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    structured = _by_query(Path(args.structured))
    lexical = _by_query(Path(args.lexical))
    hybrid = _by_query(Path(args.hybrid))
    queries = list(structured)
    report = []
    for query in queries:
        report.append(
            {
                "query": query,
                "structured": structured[query]["results"][: args.limit],
                "lexical": lexical[query]["results"][: args.limit],
                "hybrid": hybrid[query]["results"][: args.limit],
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output} for {len(report)} queries")


if __name__ == "__main__":
    main()
