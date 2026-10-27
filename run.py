"""Run the final intent qualification pipeline for one query."""

from __future__ import annotations

import argparse
import json

from src.data import load_companies
from src.hybrid import rank_hybrid
from src.query import parse_query


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rank companies against a natural-language query."
    )
    parser.add_argument("query")
    parser.add_argument("--data", default="companies.jsonl")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--candidate-limit", type=int, default=100)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    companies = load_companies(args.data)
    parsed = parse_query(args.query)
    results = rank_hybrid(
        companies,
        parsed,
        limit=args.limit,
        candidate_limit=args.candidate_limit,
    )
    payload = [
        {
            "record_id": result.company.record_id,
            "name": result.company.operational_name,
            "website": result.company.website,
            "country": result.company.address.country,
            "decision": result.decision,
            "score": round(result.final_score, 6),
            "confidence": round(result.confidence, 6),
            "matched_constraints": result.matched_constraints,
            "uncertain_constraints": result.uncertain_constraints,
            "violated_constraints": result.violated_constraints,
        }
        for result in results
    ]
    if args.as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    print(f"Query: {args.query}")
    for item in payload:
        print(
            f"{item['name'] or '<unnamed>'} | {item['decision']} | "
            f"score={item['score']:.3f} | confidence={item['confidence']:.3f} | "
            f"matched={','.join(item['matched_constraints']) or '-'} | "
            f"uncertain={','.join(item['uncertain_constraints']) or '-'}"
        )


if __name__ == "__main__":
    main()
