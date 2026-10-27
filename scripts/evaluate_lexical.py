"""Run and persist lexical retrieval results for all challenge queries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.data import load_companies
from src.lexical import rank_lexically
from src.queries import CHALLENGE_QUERIES
from src.query import parse_query


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="companies.jsonl")
    parser.add_argument("--output", type=Path, default=Path("reports/lexical_baseline.json"))
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    companies = load_companies(args.data)
    report = []
    for query in CHALLENGE_QUERIES:
        parsed = parse_query(query)
        report.append(
            {
                "query": query,
                "results": [
                    {
                        "record_id": result.company.record_id,
                        "name": result.company.operational_name,
                        "website": result.company.website,
                        "country": result.company.address.country,
                        "lexical_score": result.lexical_score,
                        "structured_decision": result.structured.decision,
                        "structured_score": result.structured.score,
                    }
                    for result in rank_lexically(companies, parsed, args.limit)
                ],
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
