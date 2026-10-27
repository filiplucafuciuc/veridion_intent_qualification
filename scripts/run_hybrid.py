"""Run the hybrid candidate retrieval and reranking pipeline."""

from __future__ import annotations

import argparse

from src.data import load_companies
from src.hybrid import rank_hybrid
from src.query import parse_query


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--data", default="companies.jsonl")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--candidate-limit", type=int, default=100)
    args = parser.parse_args()

    parsed = parse_query(args.query)
    for result in rank_hybrid(
        load_companies(args.data),
        parsed,
        limit=args.limit,
        candidate_limit=args.candidate_limit,
    ):
        print(
            f"{result.company.operational_name or '<unnamed>'} | "
            f"{result.decision} | final={result.final_score:.3f} | "
            f"lexical={result.lexical_score:.3f} | "
            f"matched={','.join(result.matched_constraints) or '-'} | "
            f"unknown={','.join(result.uncertain_constraints) or '-'} | "
            f"violated={','.join(result.violated_constraints) or '-'}"
        )


if __name__ == "__main__":
    main()
