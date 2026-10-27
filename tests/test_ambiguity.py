from pathlib import Path

from src.ambiguity import assess_candidate, assess_query
from src.data import load_companies
from src.hybrid import rank_hybrid
from src.query import parse_query


DATASET = Path(__file__).parents[1] / "companies.jsonl"


def test_structured_query_is_low_complexity():
    assessment = assess_query(
        parse_query("Public software companies with more than 1,000 employees.")
    )

    assert assessment.complexity == "low"
    assert assessment.score <= 0.10


def test_relationship_query_is_high_complexity():
    assessment = assess_query(
        parse_query(
            "Companies that could supply packaging materials for a direct-to-consumer cosmetics brand"
        )
    )

    assert assessment.complexity == "high"
    assert assessment.reasons


def test_unknown_platform_evidence_enters_review_queue():
    query = parse_query("E-commerce companies using Shopify or similar platforms")
    query_assessment = assess_query(query)
    result = next(
        item
        for item in rank_hybrid(load_companies(DATASET), query, limit=20)
        if item.company.operational_name == "EasyKassa"
    )

    assessment = assess_candidate(result, query_assessment)

    assert assessment.is_ambiguous
    assert "platform_usage" in " ".join(assessment.reasons)
