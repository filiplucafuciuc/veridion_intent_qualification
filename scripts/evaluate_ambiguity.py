"""Report query and candidate ambiguity for the supplied challenge queries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.ambiguity import assess_candidate, assess_query
from src.data import load_companies
from src.hybrid import rank_hybrid
from src.queries import CHALLENGE_QUERIES
from src.query import parse_query


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="companies.jsonl")
    parser.add_argument("--output", type=Path, default=Path("reports/ambiguity_report.json"))
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--candidate-limit", type=int, default=100)
    parser.add_argument(
        "--review-limit",
        type=int,
        default=5,
        help="Maximum ambiguous candidates proposed per query",
    )
    args = parser.parse_args()

    companies = load_companies(args.data)
    report = []
    for raw_query in CHALLENGE_QUERIES:
        parsed = parse_query(raw_query)
        query_assessment = assess_query(parsed)
        candidates = rank_hybrid(
            companies,
            parsed,
            limit=args.candidate_limit,
            candidate_limit=args.candidate_limit,
        )
        margin = (
            candidates[0].final_score - candidates[1].final_score
            if len(candidates) > 1
            else None
        )
        assessments = [
            assess_candidate(result, query_assessment, margin if position < 2 else None)
            for position, result in enumerate(candidates)
        ]
        ambiguous = [
            assessment
            for assessment in assessments
            if assessment.is_ambiguous
        ][: args.review_limit]
        report.append(
            {
                "query": raw_query,
                "query_assessment": {
                    "complexity": query_assessment.complexity,
                    "score": query_assessment.score,
                    "reasons": query_assessment.reasons,
                },
                "candidate_pool_size": len(candidates),
                "ambiguous_candidate_count": sum(
                    assessment.is_ambiguous for assessment in assessments
                ),
                "review_queue": [
                    {
                        "record_id": assessment.record_id,
                        "score": assessment.score,
                        "reasons": assessment.reasons,
                        "recommended_action": assessment.recommended_action,
                    }
                    for assessment in ambiguous
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
