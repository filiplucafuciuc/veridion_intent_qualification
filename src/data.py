"""Loading and normalization for the company dataset."""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


COUNTRY_NAMES = {
    "at": "Austria",
    "au": "Australia",
    "be": "Belgium",
    "br": "Brazil",
    "ca": "Canada",
    "ch": "Switzerland",
    "cl": "Chile",
    "cn": "China",
    "de": "Germany",
    "dk": "Denmark",
    "eg": "Egypt",
    "es": "Spain",
    "fi": "Finland",
    "fr": "France",
    "gb": "United Kingdom",
    "gr": "Greece",
    "hk": "Hong Kong",
    "hr": "Croatia",
    "id": "Indonesia",
    "ie": "Ireland",
    "in": "India",
    "is": "Iceland",
    "it": "Italy",
    "jp": "Japan",
    "kr": "South Korea",
    "kw": "Kuwait",
    "lt": "Lithuania",
    "lu": "Luxembourg",
    "nl": "Netherlands",
    "no": "Norway",
    "nz": "New Zealand",
    "pl": "Poland",
    "pt": "Portugal",
    "ro": "Romania",
    "ru": "Russia",
    "se": "Sweden",
    "sg": "Singapore",
    "tr": "Turkey",
    "tw": "Taiwan",
    "ua": "Ukraine",
    "us": "United States",
    "vn": "Vietnam",
}


@dataclass(frozen=True)
class Naics:
    code: str | None
    label: str | None


@dataclass(frozen=True)
class Location:
    country_code: str | None
    country: str | None
    region: str | None
    town: str | None
    latitude: float | None
    longitude: float | None


@dataclass(frozen=True)
class CompanyRecord:
    """A normalized company while preserving the source record identity."""

    record_id: str
    source_line: int
    website: str | None
    operational_name: str | None
    year_founded: int | None
    address: Location
    employee_count: float | None
    revenue: float | None
    primary_naics: Naics
    secondary_naics: tuple[Naics, ...]
    description: str
    business_model: tuple[str, ...]
    target_markets: tuple[str, ...]
    core_offerings: tuple[str, ...]
    is_public: bool | None
    search_text: str


def parse_embedded_value(value: Any) -> Any:
    """Accept both native JSON values and serialized Python literals."""
    if not isinstance(value, str):
        return value
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value


def _optional_float(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _optional_year(value: Any) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def _clean_text(value: Any) -> str:
    return " ".join(str(value).strip().split()) if value is not None else ""


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in (_clean_text(item) for item in value) if item)


def normalize_location(value: Any) -> Location:
    raw = parse_embedded_value(value)
    if not isinstance(raw, dict):
        return Location(None, None, None, None, None, None)
    code = _clean_text(raw.get("country_code")).lower() or None
    return Location(
        country_code=code,
        country=COUNTRY_NAMES.get(code) if code else None,
        region=_clean_text(raw.get("region_name")) or None,
        town=_clean_text(raw.get("town")) or None,
        latitude=_optional_float(raw.get("latitude")),
        longitude=_optional_float(raw.get("longitude")),
    )


def normalize_naics(value: Any) -> Naics:
    raw = parse_embedded_value(value)
    if not isinstance(raw, dict):
        return Naics(None, None)
    code = _clean_text(raw.get("code")) or None
    label = _clean_text(raw.get("label")) or None
    return Naics(code, label)


def normalize_secondary_naics(value: Any) -> tuple[Naics, ...]:
    raw = parse_embedded_value(value)
    if raw is None:
        return ()
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return ()
    return tuple(
        naics for item in raw if (naics := normalize_naics(item)).code or naics.label
    )


def build_search_text(
    *,
    name: str | None,
    primary_naics: Naics,
    secondary_naics: tuple[Naics, ...],
    description: str,
    business_model: tuple[str, ...],
    target_markets: tuple[str, ...],
    core_offerings: tuple[str, ...],
) -> str:
    parts: list[str] = []
    if name:
        parts.append(name)
    if primary_naics.label:
        parts.append(primary_naics.label)
    parts.extend(naics.label for naics in secondary_naics if naics.label)
    parts.extend((description, *business_model, *target_markets, *core_offerings))
    return re.sub(r"\s+", " ", " ".join(parts)).strip().lower()


def normalize_company(raw: dict[str, Any], source_line: int) -> CompanyRecord:
    name = _clean_text(raw.get("operational_name")) or None
    website = _clean_text(raw.get("website")).lower() or None
    primary_naics = normalize_naics(raw.get("primary_naics"))
    secondary_naics = normalize_secondary_naics(raw.get("secondary_naics"))
    description = _clean_text(raw.get("description"))
    business_model = _string_tuple(raw.get("business_model"))
    target_markets = _string_tuple(raw.get("target_markets"))
    core_offerings = _string_tuple(raw.get("core_offerings"))
    return CompanyRecord(
        record_id=f"company-{source_line:04d}",
        source_line=source_line,
        website=website,
        operational_name=name,
        year_founded=_optional_year(raw.get("year_founded")),
        address=normalize_location(raw.get("address")),
        employee_count=_optional_float(raw.get("employee_count")),
        revenue=_optional_float(raw.get("revenue")),
        primary_naics=primary_naics,
        secondary_naics=secondary_naics,
        description=description,
        business_model=business_model,
        target_markets=target_markets,
        core_offerings=core_offerings,
        is_public=raw.get("is_public") if isinstance(raw.get("is_public"), bool) else None,
        search_text=build_search_text(
            name=name,
            primary_naics=primary_naics,
            secondary_naics=secondary_naics,
            description=description,
            business_model=business_model,
            target_markets=target_markets,
            core_offerings=core_offerings,
        ),
    )


def load_companies(path: str | Path) -> list[CompanyRecord]:
    """Load JSONL records and normalize them without silently skipping rows."""
    records: list[CompanyRecord] = []
    for source_line, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise ValueError(f"Expected an object on line {source_line}")
        records.append(normalize_company(raw, source_line))
    return records
