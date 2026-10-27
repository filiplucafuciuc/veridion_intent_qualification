from pathlib import Path

from src.data import load_companies, normalize_location, normalize_naics


DATASET = Path(__file__).parents[1] / "companies.jsonl"


def test_loads_all_records_and_preserves_source_identity():
    companies = load_companies(DATASET)

    assert len(companies) == 477
    assert companies[0].record_id == "company-0001"
    assert companies[0].source_line == 1
    assert companies[-1].record_id == "company-0477"


def test_normalizes_both_native_and_serialized_nested_values():
    serialized_location = "{'country_code': 'de', 'region_name': 'Bavaria'}"
    native_location = {"country_code": "ch", "town": "Basel"}
    serialized_naics = "{'code': '513210', 'label': 'Software Publishers'}"

    assert normalize_location(serialized_location).country == "Germany"
    assert normalize_location(native_location).town == "Basel"
    assert normalize_naics(serialized_naics).code == "513210"


def test_missing_values_are_explicitly_unknown():
    companies = load_companies(DATASET)

    assert any(company.employee_count is None for company in companies)
    assert any(company.year_founded is None for company in companies)
    assert all(company.address.country_code is not None for company in companies)
