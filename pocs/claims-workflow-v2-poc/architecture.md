# Architecture — Claims Workflow v2 POC

## Layers

```text
claims_workflow/            Agent logic + orchestration (this process)
  graph/supervisor_graph.py   LangGraph StateGraph — Phase 3
  pipeline.py                 submit_claim / resume_claim entry points
  agents/                     8 agent functions (heuristic + LLM dual path)
  ledger.py                   DecisionLedger — client view onto mcp_server
  mcp_client.py                thin JSON-RPC client
  llm_client.py                shared Claude wrapper

mcp_server/                 Data-access boundary — Phase 1
  main.py                     JSON-RPC /mcp endpoint, 5 tools
  store.py                    policy fixture, ledger rows, settlements
  rag.py, policy_documents.py Phase 2 retrieval corpus
```

`claims_workflow` never touches `mcp_server`'s stores directly — every
policy lookup, ledger write, and payment goes through an MCP tool call
(`mcp_client.get_client().call_tool(...)`), in-process by default (ASGI
transport, no socket) or over real HTTP when `MCP_SERVER_URL` is set. See
[ADR-009](../../docs/adr/009-claims-workflow-v2-mcp-multiagent.md) for why.

## Orchestration (Phase 3 — LangGraph)

```text
Intake → Document Verification → Fraud Triage → Damage Assessment → Fraud Scoring
       → Policy Coverage → Approval → Payment
```

`claims_workflow/graph/supervisor_graph.py` builds a `StateGraph` from the
same 8 agent functions as nodes; conditional edges check
`claim.escalation`/`claim.status` after each node to decide whether to
continue or stop (mirroring what the agent function itself just decided).
Two entry points, unchanged since ADR-008 (`pipeline.py`):

- `submit_claim(claim)` — runs the graph from `"intake"` through
  settlement, denial, or the first escalation.
- `resume_claim(claim, ledger, human_decision)` — `agents/router.py`'s
  `resolve_case()` picks a specific re-entry stage, and
  `build_graph(entry_point)` compiles a **fresh** graph starting there
  (not a checkpoint resume — see ADR-009 "Phase 3 implementation note"
  for why, and what a production version would need instead).

## Fix 1 — fraud detection split into two agents

`agents/fraud_triage.py` runs before Damage Assessment and only evaluates
signals that don't need a cost estimate: claim velocity
(`prior_claims_count`), policy tenure (days between `policy_start_date`
and `loss_date`), and — Phase 2 — the free-text `loss_description`.
`agents/fraud_scoring.py` runs after Damage Assessment and evaluates cost
anomaly (`reported_amount` vs. the independently assessed `damage_cost`),
a photo-forensics flag, and again `loss_description`. Each has a heuristic
implementation (unchanged from ADR-008, numeric thresholds only) and an
LLM implementation (Phase 2, reasons over the free text too), dispatching
on `llm_client.is_available()` with fallback to heuristic on any
`LLMError`. Each pins its own `model_version` string in the ledger so a
flagged decision can be traced to the specific model that produced it —
see `test_audit_trail.py::test_fraud_triage_and_scoring_pin_different_model_versions`.

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
writes to it (via MCP, `record_ledger_decision`), same shape as
`xingai-engineering-system/patterns/decision-ledger-schema.md`, also
adopted by `xingai-learn` ADR-003. Two things read from it:

- `agents/adverse_action_letter.py::draft_letter()` — turns the specific
  ledger row that denied the claim into letter prose, citing the exact
  policy clause. Heuristic path is a template string; LLM path (Phase 2)
  drafts the paragraph from the same already-verified facts (low
  hallucination risk by construction — it isn't asked to invent anything).
- `GET /claims/{id}/audit` — the full, timestamped decision history for a
  claim, the raw material for regulatory reporting and fairness audits.

## Policy Coverage — heuristic dict lookup vs. RAG (Phase 2)

`agents/policy_coverage.py`'s heuristic path calls the `get_policy_coverage`
MCP tool — a flat `{covered, limit, clause}` answer sourced from
`mcp_server/store.py`'s `MOCK_POLICIES`. Its LLM path instead calls
`search_policy_documents`, which retrieves the top-k most relevant clause
chunks (`mcp_server/policy_documents.py`, including exclusions the flat
dict can't express) via a small pure-Python hashing-trick embedding
(`mcp_server/rag.py` — no vector database) and reasons over the retrieved
text against the claim's `loss_description`. This means the LLM path can
deny a claim the flat dict would call "covered" if an exclusion clause
genuinely applies — a real redetermination, not just prettier wording
around the same answer.

## Idempotent payment writes

`mcp_server/store.py::create_payment()` keys settlements by
`f"{claim_id}-settlement"`; replaying a payment for the same claim returns
the original settlement (wrapped as `{"record": ..., "idempotent": True}`)
instead of paying twice — same non-negotiable requirement this repo's
`claims-partner-api-mcp-poc` enforces on its `/payments` endpoint.
`agents/payment.py` logs `recommendation="idempotent_replay"` to the
ledger when this happens, so a retry is visible in the audit trail, not
silently absorbed.

## In-memory only

`mcp_server/store.py`'s policy fixture, ledger rows, and settlements, plus
the FastAPI `_CLAIMS` dict in `claims_workflow/api/main.py`, are all
in-process — same "runnable, not production" precedent as
`claims-mcp-oauth-poc`'s `MOCK_CLAIMS`. See README "Not Production Yet"
for the full list of what's missing before this could hold a real claim.
