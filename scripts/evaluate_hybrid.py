"""Run and persist hybrid ranking results for all challenge queries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.data import load_companies
from src.hybrid import rank_hybrid
from src.queries import CHALLENGE_QUERIES
from src.query import parse_query


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="companies.jsonl")
    parser.add_argument("--output", type=Path, default=Path("reports/hybrid_baseline.json"))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--candidate-limit", type=int, default=100)
    args = parser.parse_args()

    companies = load_companies(args.data)
    report = []
    for query in CHALLENGE_QUERIES:
        results = rank_hybrid(
            companies,
            parse_query(query),
            limit=args.limit,
            candidate_limit=args.candidate_limit,
        )
        report.append(
            {
                "query": query,
                "results": [
                    {
                        "record_id": result.company.record_id,
                        "name": result.company.operational_name,
                        "website": result.company.website,
                        "country": result.company.address.country,
                        "final_score": result.final_score,
                        "lexical_score": result.lexical_score,
                        "evidence_score": result.evidence_score,
                        "decision": result.decision,
                        "confidence": result.confidence,
                        "matched_constraints": result.matched_constraints,
                        "uncertain_constraints": result.uncertain_constraints,
                        "violated_constraints": result.violated_constraints,
                    }
                    for result in results
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
