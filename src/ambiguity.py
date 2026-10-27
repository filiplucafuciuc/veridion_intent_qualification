"""Explainable ambiguity detection for selective human or LLM review."""

from __future__ import annotations

from dataclasses import dataclass

from src.hybrid import HybridResult
from src.query import ParsedQuery


RELATIONAL_TERMS = (
    "could supply",
    "competing with",
    "fast-growing",
    "fast growing",
    "critical components",
    "similar platforms",
    "providing",
    "serving",
)


@dataclass(frozen=True)
class QueryAmbiguity:
    complexity: str
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CandidateAmbiguity:
    record_id: str
    is_ambiguous: bool
    score: float
    reasons: tuple[str, ...]
    recommended_action: str


def assess_query(query: ParsedQuery) -> QueryAmbiguity:
    lowered = query.raw_query.lower()
    reasons: list[str] = []
    score = 0.0
    relational = [term for term in RELATIONAL_TERMS if term in lowered]
    if relational:
        score += 0.35
        reasons.append(f"relational language: {', '.join(relational)}")
    if query.qualitative_terms:
        score += 0.25
        reasons.append(
            f"unobservable qualitative requirements: {', '.join(query.qualitative_terms)}"
        )
    if len(query.numeric_constraints) + len(query.required_attributes) >= 2:
        score += 0.10
        reasons.append("multiple structured constraints")
    if query.target_markets:
        score += 0.15
        reasons.append("target-market relationship")
    score = min(1.0, score)
    complexity = "high" if score >= 0.45 else "medium" if score >= 0.20 else "low"
    return QueryAmbiguity(complexity, score, tuple(reasons))


def assess_candidate(
    result: HybridResult,
    query_ambiguity: QueryAmbiguity,
    score_margin: float | None = None,
) -> CandidateAmbiguity:
    reasons: list[str] = []
    unknown = result.uncertain_constraints
    if unknown:
        reasons.append(f"unknown constraints: {', '.join(unknown)}")
    if "industry" in result.uncertain_constraints:
        reasons.append("requested industry appears only in contextual evidence")
    if result.lexical_score >= 0.10 and result.evidence_score <= 0.0:
        reasons.append("lexical and structured evidence disagree")
    if score_margin is not None and score_margin < 0.05:
        reasons.append(f"small ranking margin: {score_margin:.3f}")
    if result.company.operational_name is None:
        reasons.append("company name is missing")
    if not result.company.description:
        reasons.append("description is missing")
    if query_ambiguity.complexity == "high" and (
        result.evidence_score < 0.3 or result.decision == "possible"
    ):
        reasons.append("query is judgment-heavy")

    is_ambiguous = bool(reasons) and result.decision != "reject"
    action = "optional_llm_or_manual_review" if is_ambiguous else "offline_result"
    return CandidateAmbiguity(
        record_id=result.company.record_id,
        is_ambiguous=is_ambiguous,
        score=result.final_score,
        reasons=tuple(dict.fromkeys(reasons)),
        recommended_action=action,
    )
