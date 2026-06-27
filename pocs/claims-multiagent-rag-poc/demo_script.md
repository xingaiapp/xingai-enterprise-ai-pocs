# Live demo script — Insurance Claims Multi-Agent RAG POC

Run from `pocs/claims-multiagent-rag-poc` with venv active and vector store built.

## Prerequisites

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# If chromadb fails on Python 3.13, see README "Python 3.13 install notes"
python -m claims_rag.ingestion.build_vector_store
uvicorn claims_rag.api.main:app --reload --port 8090
```

Optional: set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` to show LangSmith traces.

---

## Demo 1 — Clean APPROVE (glass, low risk)

**Claim text**

```text
Policy POL-1001. Alex Rivera. Date of loss 2026-06-20. A rock hit my windshield on I-580 causing an 8-inch crack. Repair quote $450. Claim type auto glass.
```

**Submit**

```bash
curl -s -X POST http://localhost:8090/claims/submit \
  -H 'Content-Type: application/json' \
  -d '{"raw_claim_text":"Policy POL-1001. Alex Rivera. Date of loss 2026-06-20. A rock hit my windshield on I-580 causing an 8-inch crack. Repair quote $450. Claim type auto glass."}' | jq
```

**Talking points**

- Intake extracts structured fields with confidence score.
- Retrieval returns policy excerpts with `document_id`, `chunk_id`, similarity.
- Fraud score stays low (~0.05).
- Decision is **APPROVE** with at least one policy citation.
- *"Every word of this decision traces to a document."*

**Show audit**

```bash
curl -s http://localhost:8090/claims/<trace_id>/audit | jq
```

---

## Demo 2 — Policy exclusion DENY (flood)

**Claim text**

```text
Policy POL-2002. Jordan Lee. Basement flooded after heavy rain and storm surge on 2026-06-18. Carpet damage estimated $3,200. Homeowners claim.
```

**Talking points**

- Retrieval surfaces POL-2002 flood exclusion clause.
- Adjudication returns **DENY** citing the exclusion chunk — not model memory.
- *"The agent can't deny without quoting the exclusion."*

---

## Demo 3 — ESCALATE (fraud frequency OR high dollar)

### 3a — Third glass claim in 30 days

```text
Policy POL-3003. Sam Chen. Windshield shattered 2026-06-22. Quote $920. This is my third glass claim in the last month.
```

### 3b — High dollar amount

```text
Policy POL-2002. Jordan Lee. Kitchen fire smoke damage throughout first floor on 2026-06-10. Estimate $18,500 for restoration.
```

**Talking points**

- Fraud rules fire before the LLM (`risk_score >= 0.70` → escalate).
- Amounts over `$5,000` (from `config/claims_policy.yml`) always escalate.
- *"This is the safety rail — the AI never has unilateral authority above the threshold."*

---

## Eval suite (CI)

```bash
pytest tests/eval/test_golden_claims.py -v -m eval
pytest tests/unit/ -v
```

Target: **≥ 80%** exact-match accuracy on golden-set decision actions.
