# Insurance Claims Multi-Agent RAG POC

**Pattern:** Supervisor orchestration + specialized agents + RAG with citations + human-in-the-loop  
**Status:** Runnable demo — Phases 1–6 complete  
**Platform mapping:** [enterprise-mapping.md](./enterprise-mapping.md)

> Decision assistant — not auto-adjudication. High-risk or high-dollar claims escalate to a human.

---

## Plain-English summary (Part A)

When someone files a claim, a human adjuster reads the claim, looks up the policy, checks history, checks rules, and decides. This POC automates that **workflow** with specialized agents — each agent does one job, hands off to the next, and every decision cites source documents.

**RAG** = retrieve real documents first, then generate an answer grounded in them (not from model memory).

**Why multi-agent?** One giant prompt that "reads the claim AND checks policy AND checks fraud AND decides" is unreliable. Specialized agents mirror a real claims department: intake clerk → investigator → adjuster.

## Architecture

```text
Claim → Supervisor (LangGraph) → Intake → Retrieval (RAG) → Fraud-Check → Adjudication → Audit
```

See [architecture.md](./architecture.md), [flow.mmd](./flow.mmd), and [demo_script.md](./demo_script.md).

## Glossary

| Term | Meaning |
|------|---------|
| **RAG** | Look up real documents before answering |
| **Embedding** | Text → numbers so similar meanings sit close together |
| **Vector store** | Database for similarity search over embeddings |
| **Agent** | LLM call with one job, tools, and structured output |
| **Citation** | Decision tied to a specific source chunk |
| **Human-in-the-loop** | Uncertain or high-stakes → person decides |
| **Trace** | Timeline of agent steps for debug and audit |

## Quick start

```bash
cd pocs/claims-multiagent-rag-poc
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional: ANTHROPIC_API_KEY, OPENAI_API_KEY, LangSmith

python -m claims_rag.ingestion.build_vector_store
pytest tests/unit/ -v
pytest tests/eval/test_golden_claims.py -v -m eval

uvicorn claims_rag.api.main:app --reload --port 8090
```

### Python 3.13 install notes

`onnxruntime` (Chroma default embeddings) may not ship wheels for Python 3.13. This POC uses **offline hash embeddings** when `OPENAI_API_KEY` is unset — no onnxruntime required. If `pip install chromadb` fails, install runtime deps manually:

```bash
pip install numpy httpx uvicorn fastapi pypika tqdm bcrypt mmh3 orjson typer posthog \
  tokenizers overrides importlib-resources grpcio build chroma-hnswlib \
  jsonschema kubernetes opentelemetry-api opentelemetry-sdk \
  opentelemetry-exporter-otlp-proto-grpc pybase64
pip install chromadb --no-deps
```

**Recommended:** Python 3.11 or 3.12 for full Chroma + onnxruntime support.

## API

| Endpoint | Purpose |
|----------|---------|
| `POST /claims/submit` | Run full pipeline on raw claim text |
| `GET /claims/{trace_id}/audit` | Immutable audit trail for one run |
| `GET /health` | Liveness |

## Enterprise standards in this POC

- Thresholds in `config/claims_policy.yml` — no magic numbers in code
- PII redaction before audit log (`audit_logger.redact`)
- Every retrieval chunk carries `document_id`, `chunk_id`, similarity
- High fraud score / high dollar → `ESCALATE_TO_HUMAN` (never silent auto-deny on fraud alone)
- Structured JSON logs with `trace_id`
- Golden-set eval ≥ 80% decision accuracy
- Graceful degradation → escalate on agent/retrieval failure

## PII (synthetic data only)

All policyholders and policies are fictional. A production deployment would add encryption at rest, field-level access control, retention limits, and contractual coverage before sending PII to third-party model APIs.

## License

Private — XingAI internal.
