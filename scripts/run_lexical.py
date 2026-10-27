"""Run the lexical retrieval baseline for one query."""

from __future__ import annotations

import argparse

from src.data import load_companies
from src.lexical import rank_lexically
from src.query import parse_query


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--data", default="companies.jsonl")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    query = parse_query(args.query)
    for result in rank_lexically(load_companies(args.data), query, args.limit):
        print(
            f"{result.company.operational_name or '<unnamed>'} | "
            f"lexical={result.lexical_score:.3f} | "
            f"structured={result.structured.decision} "
            f"(score={result.structured.score:.3f}) | "
            f"{result.company.address.country or '<unknown>'}"
        )


if __name__ == "__main__":
    main()
