"""Relevance checker — is the response on-topic for the query?"""

from dataclasses import dataclass


@dataclass
class RelevanceResult:
    score: float
    query_terms: int
    matched_terms: int


class RelevanceChecker:
    def check(self, text: str, query: str) -> RelevanceResult:
        if not query or not query.strip():
            return RelevanceResult(score=0.7, query_terms=0, matched_terms=0)

        q_terms = set(w.lower() for w in query.split() if len(w) > 3 and w.isalpha())
        r_terms = set(w.lower() for w in text.split() if len(w) > 3 and w.isalpha())

        if not q_terms:
            return RelevanceResult(score=0.7, query_terms=0, matched_terms=0)

        matched = len(q_terms & r_terms)
        score = min(matched / len(q_terms) * 1.5, 1.0)

        return RelevanceResult(
            score=round(score, 4),
            query_terms=len(q_terms),
            matched_terms=matched,
        )
