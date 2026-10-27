from pathlib import Path

from src.data import load_companies
from src.lexical import rank_lexically, tokenize
from src.query import parse_query


DATASET = Path(__file__).parents[1] / "companies.jsonl"


def test_tokenizer_removes_common_function_words():
    assert tokenize("Companies providing software in Europe") == [
        "software", "europe"
    ]


def test_lexical_ranker_returns_requested_number_and_scores():
    companies = load_companies(DATASET)
    results = rank_lexically(
        companies,
        parse_query("Pharmaceutical companies in Switzerland"),
        limit=5,
    )

    assert len(results) == 5
    assert results[0].lexical_score >= results[-1].lexical_score
    assert all(result.company.record_id for result in results)
