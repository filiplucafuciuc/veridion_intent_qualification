"""Structured, explainable baseline ranking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.data import CompanyRecord
from src.query import NumericConstraint, ParsedQuery

ConstraintState = Literal["satisfied", "violated", "unknown", "not_applicable"]


@dataclass(frozen=True)
class ConstraintResult:
    name: str
    state: ConstraintState
    evidence: str


@dataclass(frozen=True)
class RankedCompany:
    company: CompanyRecord
    score: float
    decision: str
    confidence: float
    constraints: tuple[ConstraintResult, ...]


def _compare(actual: float | None, constraint: NumericConstraint) -> ConstraintResult:
    if actual is None:
        return ConstraintResult(
            constraint.field, "unknown", f"{constraint.field} is missing"
        )
    satisfied = (
        actual > constraint.value
        if constraint.operator == ">"
        else actual < constraint.value
    )
    state: ConstraintState = "satisfied" if satisfied else "violated"
    return ConstraintResult(
        constraint.field,
        state,
        f"{actual:g} {constraint.operator} {constraint.value:g}",
    )


def _industry_match(company: CompanyRecord, industries: list[str]) -> ConstraintResult:
    if not industries:
        return ConstraintResult("industry", "not_applicable", "No industry filter parsed")
    strong_haystack = " ".join(
        [
            company.primary_naics.label or "",
            *company.core_offerings,
        ]
    ).lower()
    market_haystack = " ".join(company.target_markets).lower()
    aliases = {
        "logistics": ("logistics", "transportation", "freight", "warehouse"),
        "software": ("software", "computer systems", "programming", "saas"),
        "pharmaceutical": ("pharmaceutical", "medicinal", "drug", "biological"),
        "food and beverage": ("food", "beverage", "drink", "canning", "winery"),
        "renewable energy": ("renewable", "wind", "solar", "clean energy"),
        "clean energy": ("clean energy", "renewable", "wind", "solar"),
        "e-commerce": ("e-commerce", "ecommerce", "online retail"),
        "fintech": ("fintech", "financial transaction", "payment", "digital wallet"),
        "electric vehicle": ("electric vehicle", "ev", "automotive"),
        "battery": ("battery", "lithium", "cell"),
    }
    matched = [
        term for term in industries
        if any(alias in strong_haystack for alias in aliases.get(term, (term,)))
    ]
    if matched:
        return ConstraintResult("industry", "satisfied", f"Matched: {', '.join(matched)}")
    market_only = [
        term for term in industries
        if any(alias in market_haystack for alias in aliases.get(term, (term,)))
    ]
    if market_only:
        return ConstraintResult(
            "industry",
            "unknown",
            f"Only target-market evidence: {', '.join(market_only)}",
        )
    return ConstraintResult("industry", "violated", "No requested industry evidence")


def _location_match(company: CompanyRecord, query: ParsedQuery) -> ConstraintResult:
    if not query.countries:
        return ConstraintResult("location", "not_applicable", "No location filter parsed")
    code = company.address.country_code
    if code is None:
        return ConstraintResult("location", "unknown", "Company country is missing")
    if code in query.countries:
        return ConstraintResult("location", "satisfied", f"Country code: {code}")
    return ConstraintResult("location", "violated", f"Country code: {code}")


def _attribute_results(company: CompanyRecord, query: ParsedQuery) -> list[ConstraintResult]:
    results: list[ConstraintResult] = []
    for attribute, required in query.required_attributes.items():
        if attribute == "is_public":
            actual = company.is_public
            state: ConstraintState = (
                "unknown" if actual is None else
                "satisfied" if actual is required else "violated"
            )
            results.append(ConstraintResult(attribute, state, f"value={actual!r}"))
        elif attribute == "b2b":
            values = {item.lower() for item in company.business_model}
            state = "satisfied" if "business-to-business" in values else "violated"
            results.append(ConstraintResult(attribute, state, "business_model"))
        elif attribute == "saas":
            values = {item.lower() for item in company.business_model}
            state = "satisfied" if "software-as-a-service" in values else "violated"
            results.append(ConstraintResult(attribute, state, "business_model"))
        elif attribute == "startup":
            if company.year_founded is None:
                state = "unknown"
            else:
                state = "satisfied" if company.year_founded >= 2000 else "violated"
            results.append(ConstraintResult(attribute, state, "year_founded heuristic"))
    return results


def _role_results(company: CompanyRecord, query: ParsedQuery) -> list[ConstraintResult]:
    results: list[ConstraintResult] = []
    has_manufacturing = "manufacturing" in query.role_terms
    has_supplier = "supplier" in query.role_terms
    if has_manufacturing and not has_supplier:
        values = {item.lower() for item in company.business_model}
        state: ConstraintState = (
            "satisfied" if "manufacturing" in values else "violated"
        )
        results.append(ConstraintResult("role:manufacturer", state, "business_model"))
    if has_supplier and not has_manufacturing:
        evidence_text = " ".join(
            [
                *company.business_model,
                *company.core_offerings,
                company.description,
            ]
        ).lower()
        supplier_terms = (
            "supply", "supplier", "wholesale", "distribution", "manufacturing",
            "packaging", "provision", "provider",
        )
        state = (
            "satisfied"
            if any(term in evidence_text for term in supplier_terms)
            else "unknown"
        )
        results.append(ConstraintResult("role:supplier", state, "supplier evidence"))
    if has_manufacturing and has_supplier:
        values = {item.lower() for item in company.business_model}
        evidence_text = " ".join(
            [
                *company.business_model,
                *company.core_offerings,
                company.description,
            ]
        ).lower()
        has_manufacturer_evidence = "manufacturing" in values
        has_supplier_evidence = any(
            term in evidence_text
            for term in (
                "supply", "supplier", "wholesale", "distribution",
                "manufacturing", "packaging", "provision", "provider",
            )
        )
        combined_state: ConstraintState = (
            "satisfied"
            if has_manufacturer_evidence or has_supplier_evidence
            else "unknown"
        )
        results.append(
            ConstraintResult(
                "role:manufacturer_or_supplier",
                combined_state,
                "either manufacturing or supplier evidence",
            )
        )
    return results


def _qualitative_results(
    company: CompanyRecord, query: ParsedQuery
) -> list[ConstraintResult]:
    results: list[ConstraintResult] = []
    searchable = " ".join(
        [
            company.description,
            *company.core_offerings,
            *company.target_markets,
        ]
    ).lower()
    if "platform_usage" in query.qualitative_terms:
        state: ConstraintState = (
            "satisfied"
            if "shopify" in searchable
            else "unknown"
        )
        results.append(
            ConstraintResult("platform_usage", state, "technology evidence")
        )
    if "growth" in query.qualitative_terms:
        results.append(
            ConstraintResult(
                "growth",
                "unknown",
                "no historical growth series in the dataset",
            )
        )
    if "bank_competition" in query.qualitative_terms:
        bank_terms = ("compete", "competitor", "traditional bank")
        state: ConstraintState = (
            "satisfied"
            if any(term in searchable for term in bank_terms)
            else "unknown"
        )
        results.append(
            ConstraintResult(
                "bank_competition",
                state,
                "relationship evidence",
            )
        )
    for market in query.target_markets:
        state: ConstraintState = (
            "satisfied"
            if market in {item.lower() for item in company.target_markets}
            or market in searchable
            else "unknown"
        )
        results.append(
            ConstraintResult(
                f"target_market:{market}",
                state,
                "target-market evidence",
            )
        )
    return results


def score_company(company: CompanyRecord, query: ParsedQuery) -> RankedCompany:
    constraints = [
        _location_match(company, query),
        _industry_match(company, query.industries),
        *(_compare(company_value, constraint)
          for constraint in query.numeric_constraints
          for company_value in [getattr(company, constraint.field)]),
        *_attribute_results(company, query),
        *_role_results(company, query),
        *_qualitative_results(company, query),
    ]
    applicable = [item for item in constraints if item.state != "not_applicable"]
    satisfied = sum(item.state == "satisfied" for item in applicable)
    violated = sum(item.state == "violated" for item in applicable)
    unknown = sum(item.state == "unknown" for item in applicable)
    score = (satisfied - 2 * violated - 0.5 * unknown) / max(len(applicable), 1)
    if violated:
        decision = "reject"
    elif unknown:
        decision = "possible"
    else:
        decision = "match"
    confidence = max(0.0, min(1.0, (score + 1) / 2))
    return RankedCompany(
        company=company,
        score=score,
        decision=decision,
        confidence=confidence,
        constraints=tuple(constraints),
    )


def rank_companies(
    companies: list[CompanyRecord], query: ParsedQuery, limit: int = 20
) -> list[RankedCompany]:
    ranked = [score_company(company, query) for company in companies]
    decision_rank = {"match": 2, "possible": 1, "reject": 0}
    return sorted(
        ranked,
        key=lambda result: (
            decision_rank[result.decision],
            result.score,
            result.confidence,
            result.company.operational_name or "",
        ),
        reverse=True,
    )[:limit]
