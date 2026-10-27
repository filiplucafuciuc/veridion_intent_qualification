from src.queries import CHALLENGE_QUERIES


def test_contains_all_queries_from_the_brief():
    assert len(CHALLENGE_QUERIES) == 12
    assert "Logistic companies in Romania" in CHALLENGE_QUERIES
    assert "Renewable energy equipment manufacturers in Scandinavia" in CHALLENGE_QUERIES
