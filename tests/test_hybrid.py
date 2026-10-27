from pathlib import Path

from src.data import load_companies
from src.hybrid import rank_hybrid
from src.query import parse_query


DATASET = Path(__file__).parents[1] / "companies.jsonl"


def test_hybrid_does_not_return_wrong_country_as_a_match():
    results = rank_hybrid(
        load_companies(DATASET),
        parse_query("Construction companies in the United States with revenue over $50 million"),
        limit=10,
    )

    assert results
    assert all(
        result.company.address.country_code == "us"
        for result in results
        if result.decision == "match"
    )


def test_hybrid_exposes_evidence_and_uncertainty():
    results = rank_hybrid(
        load_companies(DATASET),
        parse_query("Companies with more than 1,000 employees"),
        limit=477,
        candidate_limit=477,
    )

    assert results
    assert all(result.final_score <= 1.0 for result in results)
    assert any(result.uncertain_constraints for result in results)
