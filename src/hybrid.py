"""Constraint-aware reranking that combines lexical recall and structured evidence."""

from __future__ import annotations

from dataclasses import dataclass

from src.data import CompanyRecord
from src.lexical import TfidfIndex, query_text
from src.query import ParsedQuery
from src.structured import ConstraintResult, score_company


HARD_CONSTRAINTS = {"location", "employee_count", "revenue", "year_founded", "is_public"}


@dataclass(frozen=True)
class HybridResult:
    company: CompanyRecord
    final_score: float
    lexical_score: float
    evidence_score: float
    decision: str
    confidence: float
    matched_constraints: tuple[str, ...]
    uncertain_constraints: tuple[str, ...]
    violated_constraints: tuple[str, ...]


def _constraint_groups(
    constraints: tuple[ConstraintResult, ...],
) -> tuple[list[ConstraintResult], list[ConstraintResult], list[ConstraintResult]]:
    matched = [item for item in constraints if item.state == "satisfied"]
    uncertain = [item for item in constraints if item.state == "unknown"]
    violated = [item for item in constraints if item.state == "violated"]
    return matched, uncertain, violated


def _evidence_score(
    constraints: tuple[ConstraintResult, ...],
    lexical_score: float,
) -> tuple[float, str]:
    applicable = [item for item in constraints if item.state != "not_applicable"]
    if not applicable:
        return lexical_score, "lexical-only evidence"
    matched, uncertain, violated = _constraint_groups(constraints)
    structured = (
        len(matched) - 0.5 * len(uncertain) - 2 * len(violated)
    ) / len(applicable)
    return max(-1.0, min(1.0, structured)), (
        f"{len(matched)} satisfied, {len(uncertain)} unknown, "
        f"{len(violated)} violated"
    )


def rank_hybrid(
    companies: list[CompanyRecord],
    query: ParsedQuery,
    limit: int = 20,
    candidate_limit: int = 100,
) -> list[HybridResult]:
    """Retrieve lexically, then rerank using constraint-aware evidence.

    Candidate retrieval is deliberately broader than the returned list. This
    lets a structured match recover from a weak lexical score while keeping
    the reranking cost bounded.
    """
    index = TfidfIndex(companies)
    lexical_scores = [
        index.score(query_text(query), position)
        for position in range(len(companies))
    ]
    candidate_positions = {
        position
        for position, _ in sorted(
            enumerate(lexical_scores),
            key=lambda item: item[1],
            reverse=True,
        )[:candidate_limit]
    }
    results: list[HybridResult] = []
    for position in candidate_positions:
        company = companies[position]
        lexical_score = lexical_scores[position]
        structured = score_company(company, query)
        matched, uncertain, violated = _constraint_groups(structured.constraints)
        hard_violations = [
            item for item in violated if item.name in HARD_CONSTRAINTS
        ]
        evidence_score, _ = _evidence_score(structured.constraints, lexical_score)
        final_score = 0.35 * lexical_score + 0.65 * evidence_score
        if hard_violations:
            decision = "reject"
            final_score -= 1.0
        elif violated:
            decision = "possible"
            final_score -= 0.15
        elif uncertain:
            decision = "possible"
        else:
            decision = "match"
        confidence = max(0.0, min(1.0, (final_score + 1) / 2))
        results.append(
            HybridResult(
                company=company,
                final_score=final_score,
                lexical_score=lexical_score,
                evidence_score=evidence_score,
                decision=decision,
                confidence=confidence,
                matched_constraints=tuple(item.name for item in matched),
                uncertain_constraints=tuple(item.name for item in uncertain),
                violated_constraints=tuple(item.name for item in violated),
            )
        )

    decision_rank = {"match": 2, "possible": 1, "reject": 0}
    return sorted(
        results,
        key=lambda item: (
            decision_rank[item.decision],
            item.final_score,
            item.company.operational_name or "",
        ),
        reverse=True,
    )[:limit]
