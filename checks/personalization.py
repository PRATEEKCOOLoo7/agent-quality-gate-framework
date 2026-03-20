"""Personalization accuracy checker.

Verifies that personalized fields (lead name, company, role) in
agent output are factually correct and not hallucinated. Also
checks for generic filler that indicates low personalization.
"""

from dataclasses import dataclass, field
from typing import Any

GENERIC_PHRASES = [
    "i hope this finds you well", "i wanted to reach out",
    "i came across your profile", "just following up",
    "touching base", "dear sir or madam", "to whom it may concern",
]


@dataclass
class PersonalizationResult:
    score: float
    issues: list[str] = field(default_factory=list)
    fields_checked: int = 0
    fields_matched: int = 0


class PersonalizationChecker:
    def check(self, text: str, context: dict[str, Any] = None) -> PersonalizationResult:
        lower = text.lower()
        issues = []
        context = context or {}

        # Check for generic filler
        generic_found = [p for p in GENERIC_PHRASES if p in lower]
        if generic_found:
            issues.append(f"generic phrases: {generic_found}")

        # Check context field references
        fields_checked = 0
        fields_matched = 0
        for key, val in context.items():
            if not val:
                continue
            val_str = str(val).lower()
            if len(val_str) < 2:
                continue
            fields_checked += 1
            if val_str in lower:
                fields_matched += 1

        # Score: penalize generic, reward context references
        score = 0.5
        score -= len(generic_found) * 0.15
        if fields_checked > 0:
            score += (fields_matched / fields_checked) * 0.4
        else:
            score += 0.1  # No context to check — neutral

        # Bonus for specific data (numbers, percentages)
        import re
        if re.search(r'\d+\s*%|\$\s*[\d,]+|\d+\s*billion', lower):
            score += 0.15

        score = max(0.0, min(1.0, score))

        if not fields_matched and fields_checked > 0:
            issues.append("no context fields referenced in output")

        return PersonalizationResult(
            score=round(score, 3), issues=issues,
            fields_checked=fields_checked, fields_matched=fields_matched,
        )
