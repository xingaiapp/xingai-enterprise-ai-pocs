# Claims MCP OAuth 2.1 + PKCE POC

> **Status: Runnable · Phase 1**

**Pattern:** Real OAuth 2.1 + PKCE + JWT authentication and authorization in front of a claims-industry MCP server — not a placeholder, not a diagram, an actual token-issuing Authorization Server and an actual token-verifying MCP Server that a claims adjuster-assist agent authenticates against end-to-end.

**中文：** [README.zh.md](./README.zh.md) · **Deep dive on MCP auth:** [docs/mcp-auth-deep-dive.md](./docs/mcp-auth-deep-dive.md) ([中文](./docs/mcp-auth-deep-dive.zh.md))

---

## What This Proves

That the exact authentication pattern Robinhood ships for its Agentic Trading MCP — OAuth 2.1 + mandatory PKCE, `.well-known` metadata discovery, short-lived scoped JWTs, a Review→Execute split for anything binding — generalizes cleanly to a completely different regulated, money-adjacent domain: insurance claims adjudication. The [source case study](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-11-mcp-in-production-robinhood-case.md) and its [companion OAuth lab](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md) are written for a brokerage; this POC is that same lab, ported: same crypto, same protocol flow, same two-wall model, different domain nouns (`claims.read`/`claims.adjudicate` instead of `portfolio.read`/`orders.place`, a settlement-authority cap instead of a per-order notional cap, an "AI-assist queue" instead of an isolated Agentic brokerage account).

## Enterprise Pattern

- **OAuth 2.1 Authorization Code flow with mandatory PKCE** — no implicit grant, no plaintext client secret, S256-only challenge method
- **`.well-known` metadata discovery** (RFC 8414 Authorization Server Metadata + RFC 9728 Protected Resource Metadata) — the agent discovers every endpoint from a 401, never hardcodes a carrier's auth config
- **Short-lived, audience-scoped JWTs** (RS256, 5-minute TTL) verified via JWKS, never a shared secret
- **Scope ≠ policy** — `claims.review` and `claims.adjudicate` are separate scopes; holding both still doesn't authorize adjudicating *any* claim at *any* amount (see Wall #2 below)
- **Review → Adjudicate, never a one-step write** — a decision is drafted, frozen, and only becomes binding via a second call that accepts no mutable business parameters
- **Idempotent finalization** — a network retry can't double-adjudicate the same claim
- **Two independent authorization walls**, matching the [Four-Layer Protection Model](docs/mcp-auth-deep-dive.md#the-four-layer-protection-model): OAuth scope (wall #1, "can this agent call this tool at all") and agent settlement authority (wall #2, "should this specific claim, this specific amount, go through") — see `mcp_server/policies.py`

## Not Production Yet

This POC is deliberately **not** production-ready. Before any real carrier deployment:

- **Real Identity Provider** — replace the demo Authorization Server with Okta / Auth0 / Azure AD B2C / a hardened homegrown IdP. This repo's `auth_server/` skips MFA, real session management, breach detection, and an admin console — all things a real IdP gives you, not things worth rebuilding here.
- **Persistent storage** — `auth_server/storage.py` and the review/idempotency stores in `mcp_server/tools.py` are in-memory `dict`s. A restart silently invalidates every session and open review. Production needs PostgreSQL (codes, clients, consent records) + Redis (short-TTL codes, idempotency keys).
- **Real login + consent records** — the demo `/authorize` page has a fixed user and doesn't persist what was granted. Production needs real authentication, a queryable/revocable consent record per (user, client, scope), and skip-consent-on-reauthorization only when policy allows it.
- **Real claims system integration** — `mcp_server/policies.py`'s `MOCK_CLAIMS`/`MOCK_POLICIES` are synthetic fixtures. Production wraps a real Policy Administration / Claims Management system (Guidewire ClaimCenter, Duck Creek Claims, a homegrown system) behind this same MCP shape.
- **Audit retention meeting regulatory requirements** — this POC does not persist an audit trail at all yet. A real claims MCP needs an append-only log (who, what claim, what tool, what decision, what outcome) retained per state insurance-regulator requirements, not just an in-memory dict.
- **Key management** — `keys/private.pem` here is a file on disk. Production needs a Key Vault / HSM, JWKS key rotation with overlapping validity windows, and the private key never touching a general-purpose filesystem.
- **Rate limiting and prompt-injection defenses** — neither exists here yet; both matter more, not less, once a real LLM is driving tool selection instead of this POC's scripted demo flow.
- **HTTPS everywhere** — all three services run over plain HTTP on localhost for the demo.

See the [Pre-Launch Checklists](docs/mcp-auth-deep-dive.md#pre-launch-checklists) in the deep dive for the full itemized list.

## Architecture

```text
Claims Adjuster-Assist Agent (Python client)
     │
     │ 1. POST /mcp (no token) → 401 + resource_metadata
     ▼
Authorization Server (:8000)
     │  Metadata discovery / PKCE / JWT issuance / Refresh Rotation / Revocation
     ▼  Bearer JWT (RS256, 5 min TTL)
Claims MCP Server (:8001)
     │  Signature verify + Scope (wall #1) + Settlement Authority Policy (wall #2)
     │  + Review → Adjudicate + Idempotency
     ▼
Simulated Claim Files / Policy Coverage / Decisions (no real carrier system)
```

Full Mermaid diagram: [flow.mmd](./flow.mmd). Component responsibilities: [architecture.md](./architecture.md).

## Quick Start

```bash
cd pocs/claims-mcp-oauth-poc
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# Generate the RSA keypair (never committed — see keys/README.md)
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem

pytest tests/ -v   # 33 tests, no servers required
```

Run the full three-service flow (three terminals):

```bash
# Terminal 1
uvicorn auth_server.main:app --port 8000 --reload

# Terminal 2
uvicorn mcp_server.main:app --port 8001 --reload

# Terminal 3
python -m client.main
```

The client opens a browser for the OAuth consent screen, then walks: `get_claim` → `get_policy_coverage` → `review_claim_decision` → **you type `YES`** → `submit_claim_decision` → an idempotent retry demo.

Or with Docker (`auth-server` + `mcp-server` only — see `docker-compose.yml` for why the client runs on the host):

```bash
docker compose up --build
```

## API

| Endpoint | Server | Purpose |
|----------|--------|---------|
| `GET /.well-known/oauth-authorization-server` | Auth (:8000) | RFC 8414 metadata — every OAuth endpoint URL |
| `GET /jwks.json` | Auth (:8000) | Public signing key(s) |
| `POST /register` | Auth (:8000) | Dynamic client registration (loopback redirects only) |
| `GET`/`POST /authorize` | Auth (:8000) | Consent screen + authorization code issuance |
| `POST /token` | Auth (:8000) | Code→token exchange; refresh-token rotation |
| `POST /revoke` | Auth (:8000) | Refresh token revocation |
| `GET /.well-known/oauth-protected-resource/mcp` | MCP (:8001) | RFC 9728 metadata — points at the Authorization Server |
| `POST /mcp` | MCP (:8001) | JSON-RPC 2.0 — `initialize`, `tools/list`, `tools/call` |

Tools exposed via `tools/call`:

| Tool | Scope required | Effect |
|------|-----------------|--------|
| `get_claim` | `claims.read` | Return a claim file |
| `get_policy_coverage` | `policy.read` | Return policy coverage limits/deductibles |
| `review_claim_decision` | `claims.review` | Draft a decision, never binding |
| `submit_claim_decision` | `claims.adjudicate` | Finalize a previously-reviewed decision, idempotent |

## Team Demo Script

1. Show `curl http://localhost:8001/mcp` with no token → 401 + `WWW-Authenticate` naming where to discover the Authorization Server. *"The server never guesses who you are — it tells you exactly where to go prove it."*
2. Run `python -m client.main`, let the browser consent screen render — walk through the scope list out loud. *"This is the moment a human sees exactly what the agent is asking for, in plain language, before anything is granted."*
3. After `review_claim_decision` prints its summary, **stop before typing YES** and ask the room: *"What happens if I skip this step?"* — then show `mcp_server/tools.py`'s `tool_submit_claim_decision`: it accepts only `review_id`, nothing else. There is no code path that adjudicates a claim the review step didn't already freeze.
4. Type `YES`, show the finalized decision, then immediately re-run the idempotency step and point at `idempotent: true` — *"A flaky network retry from the agent can't double-pay this claim."*
5. Open `mcp_server/policies.py` and change `MAX_SETTLEMENT_USD` to `100`, restart the MCP server, and re-run the demo against `CLM-8842` (an $1,850 claim) — watch it get refused with `policy_violation`. *"This isn't the OAuth layer saying no — the token is still perfectly valid. This is the second wall: scope says the agent* can *call this tool, policy says whether* this claim, this amount *goes through."*

## Lessons Learned

- Porting the reference lab's crypto code verbatim looked safe but wasn't: `public_key_to_jwk()` called `_PUBLIC_KEY.public_key()` on an object that was already a public key (loaded straight from `public.pem` via `load_pem_public_key`), not a certificate wrapper needing an extra unwrap. It only surfaced when `pytest` actually exercised `/jwks.json` — a reminder that "adapted from a working reference" and "tested" are not the same claim, especially for crypto glue code nobody reads line-by-line in a design doc.
- The first draft of the scope-enforcement tests mocked `authenticate_request` wholesale (`return_value=limited_claims`), which silently skipped the real `require_scopes()` check it was supposed to be testing — every "insufficient scope" test passed for the wrong reason (nothing was actually asserting scope logic ran at all). Fixed by mocking one layer deeper (`verify_token`) so the real scope check executes against the mocked claims. Lesson: when a security check is the thing under test, mock the *input* to it, never the check itself.
- Writing `MAX_SETTLEMENT_USD` and `ALLOWED_CLAIM_TYPES` next to a comment explaining the real insurance concept (settlement authority tiers) made the demo script noticeably easier to walk a non-engineering audience through than the original notional-cap version — tying a security control to a business concept the audience already has a mental model for is worth the extra paragraph.

## Related Design Docs

- EN: [How MCP Works in Production: A Deep Dive from Robinhood Trading MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-11-mcp-in-production-robinhood-case.md)
- 中文: [生产环境里 MCP 如何真正运转](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-11-mcp-in-production-robinhood-case.zh.md)
- EN: [Build an OAuth 2.1 + PKCE MCP Project from Scratch — Complete Runnable Lab](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md) (this POC's direct source — same code, claims domain instead of brokerage)
- 中文: [从零搭建 OAuth 2.1 + PKCE MCP 项目](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.zh.md)
- EN: [MCP Auth — The Robinhood Deep Dive](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 中文: [从 Robinhood MCP 看懂 MCP 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.zh.md)
- Real-world implementation this pattern is drawn from: [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp) ([ADR-001](https://github.com/xingaiapp/xingai-robinhood-mcp/blob/main/docs/adr/001-mcp-gateway-proxy.md): gateway proxy; G1–G7 execution gates)
- Sibling POC in this repo: [Claims Multi-Agent RAG](../claims-multiagent-rag-poc/) — this POC's `MOCK_POLICIES` reuse that POC's `POL-1001`/`POL-2002`/`POL-3003` policy numbers for narrative continuity; a real Phase 2 could route that POC's Adjudication Agent through this POC's MCP layer instead of calling into the claims system directly
- [ADR-003: MCP Gateway Placeholder Policy for POCs](../../docs/adr/003-mcp-gateway-placeholder-policy.md) — this POC is the first one in the repo to implement *real* OAuth rather than the P1–P5 placeholder rules that ADR defines for everything else; see [enterprise-mapping.md](./enterprise-mapping.md) for how the two relate

See also [references.md](./references.md) for the full external reference list (RFCs, MCP spec).

## Disclaimer

This POC is for **informational and educational** purposes. It is **not** production-ready insurance or claims software.

- Code, docs, and examples are provided **“as is”** with no warranty.
- You are responsible for security, compliance, deployment, and outcomes if you reuse any of this.
- Following this POC does **not** create a professional, legal, or compliance relationship with XingAI.
- Consult qualified professionals for regulated decisions.
