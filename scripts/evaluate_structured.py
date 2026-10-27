"""Run and persist the structured baseline for all challenge queries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.data import load_companies
from src.queries import CHALLENGE_QUERIES
from src.query import parse_query
from src.structured import rank_companies


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="companies.jsonl")
    parser.add_argument("--output", type=Path, default=Path("reports/structured_baseline.json"))
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    companies = load_companies(args.data)
    results = []
    for query in CHALLENGE_QUERIES:
        parsed = parse_query(query)
        ranked = rank_companies(companies, parsed, args.limit)
        results.append(
            {
                "query": query,
                "parsed": {
                    "industries": parsed.industries,
                    "countries": parsed.countries,
                    "regions": parsed.regions,
                    "numeric_constraints": [
                        {
                            "field": item.field,
                            "operator": item.operator,
                            "value": item.value,
                        }
                        for item in parsed.numeric_constraints
                    ],
                    "required_attributes": parsed.required_attributes,
                },
                "results": [
                    {
                        "record_id": item.company.record_id,
                        "name": item.company.operational_name,
                        "website": item.company.website,
                        "country": item.company.address.country,
                        "score": item.score,
                        "decision": item.decision,
                        "confidence": item.confidence,
                        "constraints": [
                            {
                                "name": constraint.name,
                                "state": constraint.state,
                                "evidence": constraint.evidence,
                            }
                            for constraint in item.constraints
                            if constraint.state != "not_applicable"
                        ],
                    }
                    for item in ranked
                ],
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output} for {len(results)} queries")


if __name__ == "__main__":
    main()
