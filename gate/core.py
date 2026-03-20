"""Quality gate orchestrator for agentic systems.

Runs a configurable set of checks against agent output before
allowing it to proceed to the next agent or reach a user.
The gate sits at every agent-to-agent handoff, not just the
final output — catching errors early is cheaper than catching
them at delivery.

Usage:
    gate = QualityGate(config=GateConfig.from_yaml("config/sales.yaml"))
    result = gate.run(
        agent_output="Hi Sarah, noticed Acme's AI push...",
        sources=["Acme Corp announced AI partnership..."],
        context={"lead_name": "Sarah Chen", "company": "Acme Corp"},
    )
    if result.approved:
        send(result.output)
    else:
        escalate(result.issues, result.fallback)
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from checks.grounding import GroundingChecker
from checks.compliance import ComplianceChecker
from checks.personalization import PersonalizationChecker
from checks.relevance import RelevanceChecker
from detectors.injection import InjectionDetector
from detectors.toxicity import ToxicityDetector

log = logging.getLogger(__name__)

FALLBACK_RESPONSE = (
    "I'm unable to provide a confident response at this time. "
    "A team member will follow up with you shortly."
)


@dataclass
class GateConfig:
    threshold: float = 0.7
    checks_enabled: list[str] = field(default_factory=lambda: [
        "injection", "grounding", "compliance", "personalization",
        "relevance", "toxicity",
    ])
    compliance_domain: str = "financial"
    escalate_on_compliance_fail: bool = True
    fallback_message: str = FALLBACK_RESPONSE

    @classmethod
    def from_yaml(cls, path: str) -> "GateConfig":
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)


@dataclass
class CheckResult:
    name: str
    passed: bool
    score: float
    details: str = ""
    exec_ms: int = 0


@dataclass
class GateDecision:
    approved: bool
    score: float
    output: str
    fallback: str
    fallback_used: bool = False
    checks: list[CheckResult] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    total_ms: int = 0

    @property
    def failed_checks(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]


class QualityGate:
    """Multi-check validation gate for agent outputs.
    
    Checks are modular and configurable. Enable/disable via config.
    Each check produces a score (0-1) and pass/fail. The gate
    aggregates all checks into a single decision.
    """

    def __init__(self, config: GateConfig = None):
        self.config = config or GateConfig()
        self._checkers = {
            "injection": InjectionDetector(),
            "grounding": GroundingChecker(),
            "compliance": ComplianceChecker(),
            "personalization": PersonalizationChecker(),
            "relevance": RelevanceChecker(),
            "toxicity": ToxicityDetector(),
        }

    def run(self, agent_output: str, sources: list[str] = None,
            query: str = "", context: dict[str, Any] = None) -> GateDecision:
        t0 = time.monotonic()
        checks = []
        sources = sources or []
        context = context or {}

        for name in self.config.checks_enabled:
            checker = self._checkers.get(name)
            if not checker:
                continue

            ct = time.monotonic()
            if name == "injection":
                result = checker.check(agent_output)
                passed = result.safe
                score = 1.0 - result.risk
                details = "; ".join(result.threats[:3]) if result.threats else ""
            elif name == "grounding":
                result = checker.check(agent_output, sources)
                passed = result.grounded
                score = result.score
                details = f"{result.unverified_count} unverified claims" if not passed else ""
            elif name == "compliance":
                result = checker.check(agent_output)
                passed = result.compliant
                score = result.score
                details = f"violations: {result.violations}" if not passed else ""
            elif name == "personalization":
                result = checker.check(agent_output, context)
                passed = result.score >= 0.4
                score = result.score
                details = "; ".join(result.issues) if result.issues else ""
            elif name == "relevance":
                result = checker.check(agent_output, query)
                passed = result.score >= 0.3
                score = result.score
                details = "" if passed else "response may not address the query"
            elif name == "toxicity":
                result = checker.check(agent_output)
                passed = not result.toxic
                score = 1.0 - result.toxicity_score
                details = f"toxic patterns: {result.patterns}" if not passed else ""
            else:
                continue

            elapsed = int((time.monotonic() - ct) * 1000)
            checks.append(CheckResult(
                name=name, passed=passed, score=round(score, 4),
                details=details, exec_ms=elapsed,
            ))

        # Aggregate
        total_ms = int((time.monotonic() - t0) * 1000)
        overall = sum(c.score for c in checks) / len(checks) if checks else 0
        all_pass = all(c.passed for c in checks)
        issues = [c.details for c in checks if not c.passed and c.details]

        # Compliance failure forces escalation
        compliance_failed = any(
            c.name == "compliance" and not c.passed for c in checks
        )
        force_escalate = compliance_failed and self.config.escalate_on_compliance_fail

        use_fallback = not all_pass or overall < self.config.threshold or force_escalate

        if use_fallback:
            log.warning(f"GATE REJECT score={overall:.3f} issues={issues}")

        return GateDecision(
            approved=not use_fallback,
            score=round(overall, 4),
            output=agent_output if not use_fallback else self.config.fallback_message,
            fallback=self.config.fallback_message,
            fallback_used=use_fallback,
            checks=checks,
            issues=issues,
            total_ms=total_ms,
        )
