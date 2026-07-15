# Architecture — Claims Workflow v2 POC

## Pipeline (nine agents, two entry points)

```text
Intake → Document Verification → Fraud Triage → Damage Assessment → Fraud Scoring
       → Policy Coverage → Approval → Payment
```

Two Python-level entry points instead of one loop, because escalation is a
real pause/resume boundary, not just a branch (`claims_workflow/pipeline.py`):

- `submit_claim(claim)` — runs until settlement, denial, or the first escalation.
- `resume_claim(claim, ledger, human_decision)` — the Case Resolution Router
  decides exactly which stage to resume at; see `agents/router.py`.

## Fix 1 — fraud detection split into two agents

`agents/fraud_triage.py` runs before Damage Assessment and only evaluates
signals that don't need a cost estimate: claim velocity
(`prior_claims_count`) and policy tenure (days between `policy_start_date`
and `loss_date`). `agents/fraud_scoring.py` runs after Damage Assessment and
evaluates cost anomaly (`reported_amount` vs. the independently assessed
`damage_cost`) and a photo-forensics flag. Each pins its own
`model_version` string in the ledger so a flagged decision can be traced to
the specific model that produced it — see `test_audit_trail.py::test_fraud_triage_and_scoring_pin_different_model_versions`.

## Fix 2 — Case Resolution Router

`agents/router.py::resolve_case()` maps `(escalation.reason,
escalation.stage, human_decision["outcome"])` to a specific pipeline
re-entry point — never a restart from intake. The mapping is stage-aware:
a Fraud Triage clearance still needs Damage Assessment + Fraud Scoring to
run (they hadn't yet); a Fraud Scoring clearance skips straight to Policy
Coverage since both already ran. Any combination the router doesn't
recognize falls through to `SAFE_DEFAULT_TARGET = "deny_upheld"` rather
than guessing its way back to intake — see
`test_router.py::test_unrecognized_outcome_defaults_to_safe_deny_not_silent_restart`.

## Fix 3 — Compliance & Audit Trail

`ledger.py::DecisionLedger` is not a pipeline stage — every agent above
writes to it directly (same shape as
`xingai-engineering-system/patterns/decision-ledger-schema.md`, also
adopted by `xingai-learn` ADR-003). Two things read from it:

- `DecisionLedger.adverse_action_letter(claim_id)` — drafts a letter from
  the specific ledger row that denied the claim, citing the exact policy
  clause (`agents/policy_coverage.py`'s `MOCK_POLICIES[...]["clause"]`),
  not a generic "claim denied" message.
- `GET /claims/{id}/audit` — the full, timestamped decision history for a
  claim, the raw material for regulatory reporting and fairness audits.

## Idempotent payment writes

`agents/payment.py` keys settlements by `f"{claim_id}-settlement"` in a
module-level store; replaying a payment for the same claim returns the
original settlement and logs `recommendation="idempotent_replay"` instead
of paying twice — same non-negotiable requirement this repo's
`claims-partner-api-mcp-poc` enforces on its `/payments` endpoint.

## In-memory only

`MOCK_POLICIES` (policy_coverage.py), the payment settlement store, and the
FastAPI `_CLAIMS` dict are all in-process dicts — same "runnable, not
production" precedent as `claims-mcp-oauth-poc`'s `MOCK_CLAIMS`. See
README "Not Production Yet" for what's missing before this could hold a
real claim.
