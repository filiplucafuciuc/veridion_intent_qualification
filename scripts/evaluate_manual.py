"""Compute metrics over the explicitly reviewed subset."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviews", default="reports/manual_review.json")
    args = parser.parse_args()
    reviews = json.loads(Path(args.reviews).read_text(encoding="utf-8"))["reviews"]
    by_query: dict[str, list[int]] = defaultdict(list)
    for review in reviews:
        by_query[review["query"]].append(review["label"])

    labels = [review["label"] for review in reviews]
    relevant = sum(label > 0 for label in labels)
    strong = sum(label == 2 for label in labels)
    print(f"reviewed={len(labels)}")
    print(f"relevant_or_partial={relevant}")
    print(f"strong_matches={strong}")
    print(f"review_precision={relevant / len(labels):.3f}" if labels else "review_precision=n/a")
    for query, query_labels in by_query.items():
        precision = sum(label > 0 for label in query_labels) / len(query_labels)
        print(f"{query} | reviewed={len(query_labels)} | precision={precision:.3f}")


if __name__ == "__main__":
    main()
