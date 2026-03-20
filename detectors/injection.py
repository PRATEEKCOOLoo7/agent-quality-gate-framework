"""Prompt injection and jailbreak detector.

Multi-pattern detection across 6 attack categories:
1. Direct injection (ignore instructions, role override)
2. System prompt extraction
3. Encoding evasion (base64, rot13, hex)
4. Chain-of-thought manipulation
5. Delimiter attacks (fake XML/JSON roles)
6. Indirect injection (embedded in retrieved docs)
"""

import re
import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

PATTERNS = {
    "injection": [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"ignore\s+(all\s+)?above",
        r"disregard\s+(all\s+)?previous",
        r"forget\s+(all\s+)?prior",
        r"you\s+are\s+now\s+(?:a|an)\s+\w+",
        r"pretend\s+(?:you\s+are|to\s+be)",
        r"act\s+as\s+(?:if|though)",
        r"system\s*:\s*",
        r"<\s*system\s*>",
        r"bypass\s+(?:safety|content|filter|guard)",
        r"jailbreak",
        r"DAN\s+mode",
        r"developer\s+mode",
        r"do\s+anything\s+now",
        r"you\s+have\s+no\s+(?:rules|restrictions|limits)",
        r"enable\s+(?:unrestricted|unfiltered)\s+mode",
    ],
    "extraction": [
        r"what\s+(?:are|is)\s+your\s+(?:system|initial)\s+(?:prompt|instructions)",
        r"repeat\s+(?:your|the)\s+(?:system|initial)\s+(?:prompt|instructions)",
        r"show\s+me\s+your\s+(?:system|hidden)",
        r"output\s+(?:your|the)\s+(?:system|initial)\s+prompt",
        r"print\s+your\s+(?:system|initial|hidden)",
        r"reveal\s+your\s+(?:instructions|prompt|rules)",
        r"what\s+were\s+you\s+told",
    ],
    "evasion": [
        r"base64\s*[:\(]",
        r"rot13\s*[:\(]",
        r"decode\s+(?:this|the\s+following)",
        r"\\x[0-9a-fA-F]{2}",
        r"\\u[0-9a-fA-F]{4}",
        r"eval\s*\(", r"exec\s*\(",
    ],
    "cot_manipulation": [
        r"let'?s\s+think\s+step\s+by\s+step.*(?:ignore|forget|disregard)",
        r"step\s+\d+.*(?:ignore|bypass|override)",
        r"first.*(?:forget|ignore).*then",
    ],
    "delimiter": [
        r"```\s*system",
        r"<\|im_start\|>system",
        r"\[INST\].*\[/INST\]",
        r"###\s*(?:system|human|assistant)\s*:",
    ],
    "indirect": [
        r"important\s*:\s*(?:ignore|disregard|override|skip)",
        r"note\s+to\s+ai",
        r"instruction\s+override",
        r"ai\s+directive",
        r"hidden\s+instruction",
        r"ignore\s+(?:all\s+)?(?:quality|safety|compliance)\s+checks",
    ],
}

WEIGHTS = {
    "injection": 0.4, "extraction": 0.5, "evasion": 0.3,
    "cot_manipulation": 0.4, "delimiter": 0.35, "indirect": 0.45,
}


@dataclass
class InjectionResult:
    safe: bool
    risk: float
    threats: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)


class InjectionDetector:
    MAX_LEN = 4000

    def check(self, text: str) -> InjectionResult:
        threats = []
        risk = 0.0
        cats = set()
        lower = text.lower()

        if len(text) > self.MAX_LEN:
            threats.append(f"length:{len(text)}")
            risk += 0.15

        for category, pats in PATTERNS.items():
            hits = [p[:45] for p in pats if re.search(p, lower)]
            if hits:
                cats.add(category)
                for h in hits:
                    threats.append(f"{category}:{h}")
                risk += WEIGHTS.get(category, 0.3) * len(hits)

        # Role markers in multi-line input
        if re.search(r"\n\s*(?:system|assistant|human)\s*:", lower):
            threats.append("role_marker")
            risk += 0.35
            cats.add("role_injection")

        # Special char ratio
        if text:
            special = sum(1 for c in text if not c.isalnum() and not c.isspace())
            if special / len(text) > 0.25:
                threats.append(f"suspicious_chars:{special/len(text):.2f}")
                risk += 0.1

        risk = min(risk, 1.0)
        safe = risk < 0.3

        if not safe:
            log.warning(f"INJECTION BLOCKED risk={risk:.2f} cats={list(cats)}")

        return InjectionResult(
            safe=safe, risk=round(risk, 4),
            threats=threats, categories=list(cats),
        )
