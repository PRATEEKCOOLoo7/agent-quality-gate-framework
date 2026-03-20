"""Grounding checker - verifies claims against source documents."""

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)


@dataclass
class GroundingResult:
    grounded: bool
    score: float
    total_claims: int
    verified: int
    unverified_count: int
    unverified_claims: list[str] = field(default_factory=list)


class GroundingChecker:
    def __init__(self, min_len: int = 20, term_len: int = 4,
                 match_thresh: float = 0.2, ground_thresh: float = 0.6):
        self.min_len = min_len
        self.term_len = term_len
        self.match_thresh = match_thresh
        self.ground_thresh = ground_thresh

    def check(self, text: str, sources: list[str]) -> GroundingResult:
        if not sources:
            return GroundingResult(grounded=False, score=0.0, total_claims=0,
                                   verified=0, unverified_count=0,
                                   unverified_claims=["no sources"])

        src_text = " ".join(sources).lower()
        src_terms = set(w for w in src_text.split() if len(w) >= self.term_len and w.isalpha())

        # Extract numbers from sources for financial grounding
        src_nums = set()
        for s in sources:
            for w in s.split():
                c = w.strip("$,%().").replace(",", "")
                try:
                    float(c)
                    src_nums.add(c)
                except ValueError:
                    pass

        claims = [s.strip() for s in text.replace("\n", " ").split(".")
                  if len(s.strip()) >= self.min_len]

        if not claims:
            return GroundingResult(grounded=True, score=0.8, total_claims=0,
                                   verified=0, unverified_count=0)

        verified = 0
        unverified = []

        for claim in claims:
            terms = [w.lower() for w in claim.split() if len(w) >= self.term_len and w.isalpha()]
            claim_nums = set()
            for w in claim.split():
                c = w.strip("$,%().").replace(",", "")
                try:
                    float(c)
                    claim_nums.add(c)
                except ValueError:
                    pass

            if not terms and not claim_nums:
                verified += 1
                continue

            matched = sum(1 for t in terms if t in src_terms) if terms else 0
            ratio = matched / len(terms) if terms else 0
            num_bonus = 0.2 if (claim_nums and claim_nums & src_nums) else 0
            effective = min(ratio + num_bonus, 1.0)

            if effective >= self.match_thresh:
                verified += 1
            else:
                unverified.append(claim[:80])

        score = verified / len(claims)
        return GroundingResult(
            grounded=score >= self.ground_thresh,
            score=round(score, 4),
            total_claims=len(claims),
            verified=verified,
            unverified_count=len(unverified),
            unverified_claims=unverified,
        )
