# Architecture — Claims Multi-Agent RAG POC

## Supervisor pattern (LangGraph)

A linear state machine for the demo — easy to draw on a whiteboard:

```text
Intake → Retrieval → FraudCheck → Adjudication → AuditLog
         ↑ low intake confidence → HumanReview (skip pipeline)
```

## Three vector collections (never mixed)

| Collection | Contents |
|------------|----------|
| `policy_documents` | Coverage, exclusions, deductibles |
| `claim_history` | Past claims per synthetic policyholder |
| `regulations` | State claim-handling rules |

## Enterprise standards (POC level)

- Config-driven thresholds (`config/claims_policy.yml`)
- Every retrieval returns citation (doc id, chunk id, score)
- Fraud: rules first, LLM second
- Adjudication: no approve/deny without policy citation
- Escalation: fraud score ≥ threshold OR amount ≥ threshold → human
- Audit: append-only SQLite (Phase 5)

## Production path (not built)

- Pinecone/Weaviate instead of Chroma
- PDF/email intake parser
- Field-level encryption, retention policies
- Real policy admin system integration
