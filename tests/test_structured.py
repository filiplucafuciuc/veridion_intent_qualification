from pathlib import Path

from src.data import load_companies
from src.query import parse_query
from src.structured import score_company


DATASET = Path(__file__).parents[1] / "companies.jsonl"


def test_missing_numeric_value_is_unknown_not_violated():
    companies = load_companies(DATASET)
    company = next(item for item in companies if item.employee_count is None)
    query = parse_query("Companies with more than 1,000 employees")

    result = score_company(company, query)

    employee_result = next(
        item for item in result.constraints if item.name == "employee_count"
    )
    assert employee_result.state == "unknown"
    assert result.decision == "possible"


def test_explicit_wrong_country_is_rejected():
    companies = load_companies(DATASET)
    company = next(item for item in companies if item.address.country_code == "fr")
    query = parse_query("Pharmaceutical companies in Switzerland")

    result = score_company(company, query)

    location_result = next(
        item for item in result.constraints if item.name == "location"
    )
    assert location_result.state == "violated"
    assert result.decision == "reject"


def test_manufacturer_role_is_evaluated_separately_from_industry():
    companies = load_companies(DATASET)
    company = next(
        item for item in companies
        if "Manufacturing" in item.business_model
    )
    query = parse_query("Food and beverage manufacturers in France")

    result = score_company(company, query)

    role_result = next(
        item for item in result.constraints if item.name == "role:manufacturer"
    )
    assert role_result.state == "satisfied"


def test_target_market_alone_is_not_strong_industry_evidence():
    companies = load_companies(DATASET)
    company = next(item for item in companies if item.operational_name == "CBRE Romania")
    query = parse_query("Logistics companies in Romania")

    result = score_company(company, query)

    industry_result = next(
        item for item in result.constraints if item.name == "industry"
    )
    assert industry_result.state == "unknown"
    assert result.decision == "possible"


def test_missing_platform_evidence_is_unknown():
    companies = load_companies(DATASET)
    company = next(item for item in companies if item.operational_name == "EasyKassa")
    query = parse_query("E-commerce companies using Shopify or similar platforms")

    result = score_company(company, query)

    platform_result = next(
        item for item in result.constraints if item.name == "platform_usage"
    )
    assert platform_result.state == "unknown"
    assert result.decision == "possible"


def test_fintech_alias_matches_payment_industry_evidence():
    companies = load_companies(DATASET)
    company = next(item for item in companies if item.operational_name == "European Pay")
    query = parse_query("Fintech companies in Europe")

    result = score_company(company, query)

    industry_result = next(
        item for item in result.constraints if item.name == "industry"
    )
    assert industry_result.state == "satisfied"
