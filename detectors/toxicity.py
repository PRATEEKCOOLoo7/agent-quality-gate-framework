"""Toxicity and inappropriate content detector.

Catches hostile, discriminatory, or unprofessional language
in agent outputs. Important for outreach agents where tone
directly impacts brand reputation.
"""

import re
from dataclasses import dataclass, field

TOXIC_PATTERNS = [
    (r"\b(?:stupid|idiot|moron|dumb)\b", "insult"),
    (r"\b(?:hate|despise|loathe)\s+(?:you|your|them)", "hostility"),
    (r"\b(?:scam|fraud|ponzi|cheat)\b", "fraud_accusation"),
    (r"\b(?:threatening|threat|warned you)\b", "threat"),
    (r"\b(?:shut\s+up|go\s+away|leave\s+me)\b", "dismissive"),
    (r"\b(?:obviously|clearly)\s+(?:you|your)\s+(?:don't|can't|won't)", "condescending"),
]

UNPROFESSIONAL = [
    (r"(?:lol|lmao|rofl|omg)\b", "informal"),
    (r"(?:!!!|!!!)\s", "excessive_punctuation"),
    (r"(?:wtf|wth|smh)\b", "slang"),
]


@dataclass
class ToxicityResult:
    toxic: bool
    toxicity_score: float
    patterns: list[str] = field(default_factory=list)
    unprofessional: list[str] = field(default_factory=list)


class ToxicityDetector:
    def check(self, text: str) -> ToxicityResult:
        lower = text.lower()
        patterns = []
        unprof = []

        for pat, label in TOXIC_PATTERNS:
            if re.search(pat, lower):
                patterns.append(label)

        for pat, label in UNPROFESSIONAL:
            if re.search(pat, lower):
                unprof.append(label)

        tox_score = min(len(patterns) * 0.3 + len(unprof) * 0.1, 1.0)
        toxic = len(patterns) > 0 or tox_score > 0.3

        return ToxicityResult(
            toxic=toxic, toxicity_score=round(tox_score, 3),
            patterns=patterns, unprofessional=unprof,
        )
