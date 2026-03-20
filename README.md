# Agent Quality Gate Framework

A production-grade evaluation and guardrails framework for agentic AI systems. Every agent output passes through a multi-layer quality gate before reaching a user or triggering a downstream action.

Built on the principle: **"Do Not Embarrass Me"** — no AI output ships without verification.

## Why This Exists

Agentic systems that act autonomously (sending emails, making recommendations, qualifying leads) need a fundamentally different quality bar than chatbots. A chatbot hallucination is annoying. An agent hallucination that sends a wrong email to a prospect is a business-ending event.

This framework provides the evaluation layer that sits between agent intent and agent action.

## Architecture

```
Agent Output (any agent in the pipeline)
    │
    ▼
┌───────────────────────────────────────────────────────┐
│                    QUALITY GATE                        │
│                                                        │
│  Layer 1: Input Sanitization                          │
│  ├── Prompt injection detection (15+ patterns)        │
│  ├── Jailbreak prevention guardrails                  │
│  ├── Encoding evasion detection (base64, rot13)       │
│  └── Input length & character validation              │
│                                                        │
│  Layer 2: Output Validation                           │
│  ├── Hallucination detection (claim vs source)        │
│  ├── Factual grounding score (0-1 continuous)         │
│  ├── Tone & compliance check (SEC/regulatory)         │
│  └── Personalization accuracy verification            │
│                                                        │
│  Layer 3: Safety & Routing                            │
│  ├── Confidence threshold (configurable per agent)    │
│  ├── Rate limiting per endpoint                       │
│  ├── Fallback response generation                     │
│  ├── Human escalation routing                         │
│  └── Audit logging                                    │
│                                                        │
│  PASS → Execute action    FAIL → Fallback / Human     │
└───────────────────────────────────────────────────────┘
```

## Features

### Input Protection
- **Prompt Injection Detection**: 15+ regex patterns covering known injection templates (ignore instructions, role hijacking, system prompt extraction)
- **Jailbreak Prevention**: Detects DAN mode, developer mode, unrestricted AI attempts
- **Encoding Evasion**: Catches base64, rot13, hex-encoded bypass attempts
- **Rate Limiting**: Per-user, per-endpoint limits to prevent abuse

### Output Validation  
- **Hallucination Detection**: Extracts claims from agent output, cross-references against retrieved source documents, scores grounding ratio
- **Factual Grounding Score**: Continuous 0-1 score (not binary) — downstream systems can make nuanced decisions (show with disclaimer vs block)
- **Tone Compliance**: Domain-specific tone checking (financial advisory, sales outreach, support) with configurable rule sets
- **Personalization Accuracy**: Verifies that personalized fields (name, company, role) are factually correct, not hallucinated

### Safety & Routing
- **Confidence-Based Fallback**: Low-confidence outputs route to a safe, pre-approved fallback response
- **Human-in-the-Loop Escalation**: Configurable escalation rules — e.g., always escalate compliance failures
- **Adversarial Test Suite**: 50+ test cases that attempt to break the gate (included in `tests/`)
- **Audit Trail**: Every gate decision is logged with full context for compliance review

## Project Structure

```
agent-quality-gate-framework/
├── README.md
├── requirements.txt
├── gate/
│   ├── __init__.py
│   ├── quality_gate.py          # Main gate orchestrator
│   ├── input_guard.py           # Input sanitization & injection detection
│   ├── output_validator.py      # Hallucination, grounding, tone checks
│   ├── safety_router.py         # Fallback, escalation, rate limiting
│   └── audit_logger.py          # Compliance audit trail
├── checks/
│   ├── __init__.py
│   ├── hallucination.py         # Claim extraction & source verification
│   ├── grounding.py             # Continuous grounding scorer
│   ├── tone_compliance.py       # Domain-specific tone rules
│   ├── personalization.py       # Field accuracy verification
│   └── injection_patterns.py    # Pattern database for injection detection
├── config/
│   ├── financial_advisory.yaml  # Rules for financial domain
│   ├── sales_outreach.yaml      # Rules for sales/revenue domain
│   └── default.yaml
├── tests/
│   ├── adversarial/
│   │   ├── test_injection_attacks.py    # 20+ injection attempts
│   │   ├── test_jailbreak_attempts.py   # 15+ jailbreak patterns
│   │   └── test_evasion_techniques.py   # Encoding bypass attempts
│   ├── test_hallucination.py
│   ├── test_grounding.py
│   ├── test_tone_compliance.py
│   └── test_integration.py
└── examples/
    ├── financial_gate.py        # Usage with financial advisory agents
    └── sales_gate.py            # Usage with sales outreach agents
```

## Quick Start

```python
from gate import QualityGate

# Initialize with domain-specific config
gate = QualityGate.from_config("config/sales_outreach.yaml")

# Check agent output before sending
result = gate.evaluate(
    agent_output="Hi Sarah, noticed Acme's AI initiative...",
    source_documents=["Acme Corp announced AI partnership..."],
    agent_context={"lead_name": "Sarah Chen", "company": "Acme Corp"},
)

if result.passed:
    send_email(result.validated_output)
else:
    escalate_to_human(result.issues, result.fallback_response)
```

## Design Philosophy

1. **Gate at every handoff, not just the exit**: In multi-agent systems, each agent-to-agent handoff runs through the gate. Catching errors early is cheaper than catching them at delivery.

2. **Continuous scores, not binary pass/fail**: A grounding score of 0.65 means "probably ok but add a disclaimer." A score of 0.3 means "block entirely." Binary gates lose this nuance.

3. **Domain-configurable rules**: Financial advisory needs SEC compliance checks. Sales outreach needs personalization accuracy and anti-spam checks. The same gate framework supports both via YAML config.

4. **Adversarial-first testing**: The test suite is designed by asking "how would someone break this?" before asking "does the happy path work?"

## Inspired By

The "Do Not Embarrass Me" quality gate concept — the idea that in revenue-critical agentic systems, every output must be verified before it reaches a prospect. The embarrassment cost of one wrong email far exceeds the latency cost of one more validation check.

