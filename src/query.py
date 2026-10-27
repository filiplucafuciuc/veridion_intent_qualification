"""Transparent parsing of structured intent from the challenge queries."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


COUNTRY_ALIASES = {
    "romania": "ro",
    "germany": "de",
    "france": "fr",
    "switzerland": "ch",
    "united states": "us",
    "usa": "us",
    "denmark": "dk",
    "norway": "no",
    "sweden": "se",
    "finland": "fi",
    "iceland": "is",
}

REGION_COUNTRIES = {
    "scandinavia": ("dk", "no", "se"),
    "nordics": ("dk", "fi", "is", "no", "se"),
    "europe": (
        "at", "be", "ch", "de", "dk", "es", "fi", "fr", "gb", "gr",
        "hr", "ie", "is", "it", "lt", "lu", "nl", "no", "pl", "pt",
        "ro", "se", "ua",
    ),
}

INDUSTRY_ALIASES = {
    "logistic": "logistics",
    "logistics": "logistics",
    "software": "software",
    "food and beverage": "food and beverage",
    "pharmaceutical": "pharmaceutical",
    "construction": "construction",
    "fintech": "fintech",
    "clean energy": "clean energy",
    "renewable energy": "renewable energy",
    "e-commerce": "e-commerce",
    "electric vehicle": "electric vehicle",
    "battery": "battery",
    "packaging": "packaging",
}


@dataclass(frozen=True)
class NumericConstraint:
    field: str
    operator: str
    value: float


@dataclass
class ParsedQuery:
    raw_query: str
    industries: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    regions: dict[str, tuple[str, ...]] = field(default_factory=dict)
    numeric_constraints: list[NumericConstraint] = field(default_factory=list)
    required_attributes: dict[str, bool] = field(default_factory=dict)
    role_terms: list[str] = field(default_factory=list)
    qualitative_terms: list[str] = field(default_factory=list)
    target_markets: list[str] = field(default_factory=list)
    text_terms: list[str] = field(default_factory=list)

    @property
    def has_structured_constraints(self) -> bool:
        return bool(
            self.countries
            or self.regions
            or self.numeric_constraints
            or self.required_attributes
        )


def _extract_location(query: str, parsed: ParsedQuery) -> None:
    lowered = query.lower()
    for region, countries in REGION_COUNTRIES.items():
        if re.search(rf"\b{re.escape(region)}\b", lowered):
            parsed.regions[region] = countries
            parsed.countries.extend(countries)

    for country, code in COUNTRY_ALIASES.items():
        if re.search(rf"\b{re.escape(country)}\b", lowered):
            parsed.countries.append(code)

    parsed.countries = list(dict.fromkeys(parsed.countries))


def _extract_numeric_constraints(query: str, parsed: ParsedQuery) -> None:
    lowered = query.lower().replace(",", "")
    patterns = (
        (r"(?:more than|over|above)\s+\$?([\d.]+)\s*m(?:illion)?\s+revenue", "revenue", ">", 1_000_000),
        (r"revenue\s+(?:of\s+)?(?:more than|over|above)\s+\$?([\d.]+)\s*m(?:illion)?", "revenue", ">", 1_000_000),
        (r"(?:more than|over|above)\s+\$?([\d.]+)\s*(?:employees|employee)", "employee_count", ">", 1),
        (r"(?:fewer than|less than|under)\s+([\d.]+)\s*(?:employees|employee)", "employee_count", "<", 1),
        (r"(?:founded|established)\s+after\s+(\d{4})", "year_founded", ">", 1),
        (r"(?:founded|established)\s+before\s+(\d{4})", "year_founded", "<", 1),
    )
    for pattern, field, operator, multiplier in patterns:
        match = re.search(pattern, lowered)
        if match:
            parsed.numeric_constraints.append(
                NumericConstraint(field, operator, float(match.group(1)) * multiplier)
            )


def parse_query(query: str) -> ParsedQuery:
    parsed = ParsedQuery(raw_query=query)
    lowered = query.lower()
    _extract_location(query, parsed)
    _extract_numeric_constraints(query, parsed)

    if re.search(r"\bpublic\b", lowered):
        parsed.required_attributes["is_public"] = True
    if re.search(r"\b(?:startup|start-up)\b", lowered):
        parsed.required_attributes["startup"] = True
    if re.search(r"\bsaas\b", lowered):
        parsed.required_attributes["saas"] = True
    if re.search(r"\bb2b\b", lowered):
        parsed.required_attributes["b2b"] = True
    if "shopify" in lowered or "similar platform" in lowered:
        parsed.qualitative_terms.append("platform_usage")
    if "fast-growing" in lowered or "fast growing" in lowered:
        parsed.qualitative_terms.append("growth")
    if "competing with traditional banks" in lowered:
        parsed.qualitative_terms.append("bank_competition")
    if "hr solutions" in lowered or "human resources" in lowered:
        parsed.target_markets.append("human resources")
    if "cosmetics" in lowered:
        parsed.target_markets.append("cosmetics")

    parsed.industries = list(
        dict.fromkeys(
            canonical
            for term, canonical in INDUSTRY_ALIASES.items()
            if re.search(rf"\b{re.escape(term)}\b", lowered)
        )
    )
    if "manufacturer" in lowered or "manufacturers" in lowered or "manufacture" in lowered:
        parsed.role_terms.append("manufacturing")
    if "supplier" in lowered or "supply" in lowered:
        parsed.role_terms.append("supplier")
    if "companies" in lowered and "software" in lowered:
        parsed.role_terms.append("software")

    parsed.text_terms = [
        token
        for token in re.findall(r"[a-z][a-z-]+", lowered)
        if len(token) >= 4
    ]
    return parsed
