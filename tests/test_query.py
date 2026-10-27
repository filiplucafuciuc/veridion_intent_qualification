from src.query import parse_query


def test_parses_numeric_public_and_location_constraints():
    parsed = parse_query("Public software companies with more than 1,000 employees.")

    assert parsed.industries == ["software"]
    assert parsed.required_attributes == {"is_public": True}
    assert parsed.numeric_constraints[0].field == "employee_count"
    assert parsed.numeric_constraints[0].value == 1000


def test_expands_scandinavia_without_mutating_company_locations():
    parsed = parse_query(
        "Renewable energy equipment manufacturers in Scandinavia"
    )

    assert parsed.regions["scandinavia"] == ("dk", "no", "se")
    assert parsed.countries == ["dk", "no", "se"]


def test_expands_europe_to_explicit_country_codes():
    parsed = parse_query("B2B SaaS companies providing HR solutions in Europe")

    assert "de" in parsed.countries
    assert "ro" in parsed.countries
    assert parsed.regions["europe"]


def test_accepts_logistic_singular_as_the_logistics_industry():
    parsed = parse_query("Logistic companies in Romania")

    assert parsed.industries == ["logistics"]
    assert parsed.countries == ["ro"]


def test_parses_revenue_and_foundation_constraints():
    parsed = parse_query(
        "Construction companies in the United States with revenue over $50 million"
    )

    assert parsed.countries == ["us"]
    assert ("revenue", ">", 50_000_000) == (
        parsed.numeric_constraints[0].field,
        parsed.numeric_constraints[0].operator,
        parsed.numeric_constraints[0].value,
    )


def test_parses_qualitative_evidence_requirements():
    parsed = parse_query(
        "Fast-growing fintech companies competing with traditional banks in Europe"
    )

    assert parsed.qualitative_terms == ["growth", "bank_competition"]
