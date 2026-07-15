"""claims_workflow — Claims Settlement Workflow v2 (XingAI corrected design).

Runnable implementation of the three structural fixes described in
xingai-enterprise-ai-design/articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.md:

1. Fraud detection split into Triage (pre-damage-assessment) and Scoring
   (post-damage-assessment) — see claims_workflow.agents.fraud_triage /
   .fraud_scoring.
2. Case Resolution Router — see claims_workflow.agents.router.
3. Compliance & Audit Trail via a Decision-Ledger-shaped table every stage
   writes to — see claims_workflow.ledger.
"""

__version__ = "0.1.0"
