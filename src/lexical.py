"""A small, dependency-free TF-IDF retrieval baseline."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from src.data import CompanyRecord
from src.query import ParsedQuery
from src.structured import RankedCompany, score_company

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "and", "for", "in", "of", "the", "with", "than", "more", "less",
    "companies", "company", "that", "could", "provide", "providing",
}


def tokenize(text: str) -> list[str]:
    return [
        token for token in TOKEN_RE.findall(text.lower())
        if len(token) > 2 and token not in STOP_WORDS
    ]


def query_text(query: ParsedQuery) -> str:
    parts = [
        query.raw_query,
        *query.industries,
        *query.role_terms,
        *query.text_terms,
    ]
    return " ".join(parts)


@dataclass(frozen=True)
class LexicalResult:
    company: CompanyRecord
    lexical_score: float
    structured: RankedCompany


class TfidfIndex:
    def __init__(self, companies: list[CompanyRecord]) -> None:
        self.companies = companies
        self.documents = [tokenize(company.search_text) for company in companies]
        self.document_frequency = Counter(
            token for document in self.documents for token in set(document)
        )
        self.document_count = len(companies)
        self.vectors = [self._vector(document) for document in self.documents]
        self.norms = [self._norm(vector) for vector in self.vectors]

    def _vector(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        return {
            token: (1 + math.log(count))
            * math.log((1 + self.document_count) / (1 + self.document_frequency[token]))
            for token, count in counts.items()
        }

    @staticmethod
    def _norm(vector: dict[str, float]) -> float:
        return math.sqrt(sum(value * value for value in vector.values()))

    def score(self, query: str, index: int) -> float:
        query_vector = self._vector(tokenize(query))
        query_norm = self._norm(query_vector)
        if not query_norm or not self.norms[index]:
            return 0.0
        dot_product = sum(
            value * self.vectors[index].get(token, 0.0)
            for token, value in query_vector.items()
        )
        return dot_product / (query_norm * self.norms[index])


def rank_lexically(
    companies: list[CompanyRecord], query: ParsedQuery, limit: int = 20
) -> list[LexicalResult]:
    index = TfidfIndex(companies)
    ranked = [
        LexicalResult(
            company=company,
            lexical_score=index.score(query_text(query), position),
            structured=score_company(company, query),
        )
        for position, company in enumerate(companies)
    ]
    return sorted(
        ranked,
        key=lambda result: (
            result.lexical_score,
            result.structured.score,
            result.company.operational_name or "",
        ),
        reverse=True,
    )[:limit]
