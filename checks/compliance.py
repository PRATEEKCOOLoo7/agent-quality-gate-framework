"""Domain-specific compliance checker.

Financial domain: SEC violations, guaranteed returns, risk-free claims.
Sales domain: CAN-SPAM compliance, false urgency, misleading claims.
"""

import re
from dataclasses import dataclass, field

FINANCIAL_VIOLATIONS = [
    (r"guaranteed?\s+returns?", "guaranteed_returns"),
    (r"risk[\s-]?free", "risk_free"),
    (r"you\s+will\s+(definitely|certainly|surely)\s+make\s+money", "assured_profit"),
    (r"100\s*%\s+safe", "absolute_safety"),
    (r"can'?t\s+lose", "no_loss"),
    (r"insider\s+(info|information|tip|knowledge)", "insider_ref"),
    (r"guaranteed?\s+profit", "guaranteed_profit"),
    (r"no\s+risk\s+(?:at\s+all|whatsoever)", "no_risk"),
    (r"(?:buy|invest)\s+(?:now|immediately|today)", "urgency_pressure"),
]

SALES_VIOLATIONS = [
    (r"guaranteed?\s+(?:results?|roi|revenue)", "guaranteed_results"),
    (r"act\s+now\s+or\s+(?:lose|miss)", "false_urgency"),
    (r"only\s+\d+\s+(?:spots?|seats?)\s+(?:left|remaining)", "artificial_scarcity"),
    (r"this\s+offer\s+(?:expires?|ends?)\s+(?:today|tonight|soon)", "fake_deadline"),
]


@dataclass
class ComplianceResult:
    compliant: bool
    violations: list[str] = field(default_factory=list)
    score: float = 1.0
    domain: str = "financial"


class ComplianceChecker:
    def __init__(self, domain: str = "financial"):
        self.domain = domain
        self._patterns = FINANCIAL_VIOLATIONS if domain == "financial" else SALES_VIOLATIONS

    def check(self, text: str) -> ComplianceResult:
        lower = text.lower()
        violations = [label for pat, label in self._patterns if re.search(pat, lower)]
        compliant = len(violations) == 0
        score = max(0.0, 1.0 - 0.3 * len(violations))

        return ComplianceResult(
            compliant=compliant, violations=violations,
            score=round(score, 3), domain=self.domain,
        )
