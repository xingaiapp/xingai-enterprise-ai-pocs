# MCP Authentication, Deeply Explained — Using This POC's Code as the Worked Example

**中文版：** [mcp-auth-deep-dive.zh.md](./mcp-auth-deep-dive.zh.md)

This document exists because reading "OAuth 2.1 + PKCE" in an architecture diagram and being able to explain *why each piece exists, and what breaks without it* are two different levels of understanding. Every section below points at real code in this POC (`auth_server/`, `mcp_server/`, `client/`) so you can read the explanation and the implementation side by side, in a domain — insurance claims adjudication — where getting this wrong has real financial and regulatory consequences, not just a bad demo.

---

## The three-party problem MCP auth solves

Every MCP deployment has three parties with different levels of trust:

| Party | Example here | What it should be able to prove/do |
|-------|--------------|--------------------------------------|
| **Resource owner** | The insurance carrier — owns the claims data | Grant or deny access; define what "allowed" means |
| **Client / agent** | The claims adjuster-assist agent (`client/`) | Prove it has a valid grant, without ever holding the resource owner's master credentials |
| **Resource server** | The Claims MCP Server (`mcp_server/`) | Verify a presented credential without needing to trust the client's word for it |

The core problem: how does the agent prove it's allowed to read `CLM-8841` and (with narrower permission) adjudicate it, **without the carrier's login credentials ever being typed into, stored by, or passed through the agent**? That's the entire reason OAuth exists instead of "just have the agent log in with a username and password."

### What breaks without this

Imagine instead that `client/main.py` just held a claims-system username and password in a config file (a pattern real community MCP servers have shipped — the source article behind this POC calls this out explicitly for Robinhood). Concretely, that config file compromise now means:

- Whoever reads it can log into the claims system **as the adjuster**, with the adjuster's *full* permissions — not the narrow `claims.read`/`claims.review` slice the agent actually needs.
- There's no way to revoke *just the agent's* access without changing the adjuster's real password, which breaks their own login too.
- There's no token expiry — the credential is valid until someone notices and rotates it.

OAuth's entire value proposition is turning "steal one config file, get someone's real login" into "steal one config file, get a scoped, short-lived, individually-revocable token that can't do anything the scope didn't already allow, and stops working in under 5 minutes." See `client/token_store.py` — even the *token* is stored `chmod 600`, and it still isn't the credential; it's a narrow, time-boxed proof.

---

## PKCE — the part everyone name-drops and few can derive

PKCE (Proof Key for Code Exchange, RFC 7636) is not optional flavor text in OAuth 2.1 — it's mandatory, and understanding why requires walking through the attack it closes.

### The attack PKCE prevents

Without PKCE, the Authorization Code flow is: client redirects the browser to the Authorization Server, human logs in and approves, Authorization Server redirects back to the client's `redirect_uri` with a short-lived `code`, client exchanges that `code` for a token.

The vulnerability: that `code` travels through the browser, appears in browser history, may leak via a referrer header, and — critically for native/desktop apps — a **malicious application on the same machine** can potentially intercept the redirect (e.g. by registering for the same custom URL scheme, or on shared/misconfigured loopback ports) and steal the `code` before the legitimate client sees it. Whoever has the code can redeem it for a token.

### The fix, exactly

```python
# client/oauth.py — generate_pkce_pair()
verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("ascii")
digest = hashlib.sha256(verifier.encode("ascii")).digest()
challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
```

1. The client generates a random secret, `code_verifier` (43+ characters, never sent anywhere yet).
2. It derives `code_challenge = BASE64URL(SHA256(code_verifier))` and sends **only the challenge** in the initial `/authorize` redirect.
3. When exchanging the code for a token, the client sends the **verifier** (not the challenge) to `/token`.
4. The Authorization Server independently computes `SHA256(verifier)` and checks it matches the `challenge` it stored when the code was issued:

```python
# auth_server/security.py — verify_pkce()
digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
return hmac.compare_digest(expected, code_challenge)
```

**Why this closes the attack:** an attacker who steals the `code` from the redirect still doesn't have the `verifier` — it never left the legitimate client's process, never appeared in a URL, never touched the browser. Without the verifier, the stolen code is worthless at the token endpoint. This is a one-way hash relationship: knowing the challenge doesn't let you derive the verifier (that's what SHA-256 buys you).

**Worked numbers, if you want to verify it by hand:**

```python
>>> import base64, hashlib
>>> verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
>>> digest = hashlib.sha256(verifier.encode("ascii")).digest()
>>> base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM'
```

Run this yourself — it's exactly the two lines `verify_pkce()` runs, and it's why `tests/test_auth_server.py::TestPKCE::test_pkce_tampered_challenge` (a one-character change to the challenge fails verification) is a real, meaningful test and not a formality.

**One more detail that matters:** `verify_pkce` uses `hmac.compare_digest`, not `==`. A naive string comparison short-circuits on the first mismatched byte, and the tiny timing difference between "failed on byte 3" and "failed on byte 40" is — over enough attempts — a real side channel an attacker can use to guess the challenge byte by byte. It's a slow attack, but there's no reason to leave the door open when constant-time comparison costs nothing.

---

## The `state` parameter — CSRF, not PKCE's job

PKCE and `state` solve *different* problems and both are needed:

- **PKCE** proves the client that requested authorization is the same client redeeming the code (protects the code exchange).
- **`state`** proves the authorization response the client is processing corresponds to a request *that client itself* initiated (protects against a forged callback).

Without `state`, an attacker could trick a victim's browser into completing *the attacker's* OAuth flow, landing the attacker's authorization code in the victim's callback — a session-fixation-style CSRF attack. `client/main.py` generates a random `state`, sends it in the `/authorize` redirect, and rejects the callback if the returned `state` doesn't match exactly:

```python
if callback.get("state") != state:
    raise ValueError("state mismatch — possible CSRF attack!")
```

This check has to happen **before** the code is ever exchanged for a token — a state mismatch is a hard stop, not a warning.

---

## Why discovery matters for MCP specifically

`.well-known/oauth-authorization-server` (RFC 8414) and `.well-known/oauth-protected-resource/mcp` (RFC 9728) let `client/discovery.py` learn every endpoint URL — `authorization_endpoint`, `token_endpoint`, `jwks_uri` — from two HTTP calls, instead of a hardcoded per-deployment config.

This is not a nice-to-have for MCP specifically: **the entire pitch of MCP is one client talking to many independently-operated servers.** If an adjuster-assist agent had to hardcode Carrier A's auth endpoints, then rewriting that config for Carrier B, C, D means N configurations to maintain and get right. Discovery means the client's *code* never changes — point it at a different claims MCP server, and it bootstraps its own auth flow from that server's own advertised metadata.

`client/discovery.py` also enforces one more thing worth noticing: it refuses to proceed if the discovered Authorization Server doesn't advertise `S256` in `code_challenge_methods_supported`:

```python
if "S256" not in pkce_methods:
    raise ValueError("AS does not support S256 PKCE — refusing to connect")
```

A claims agent should never downgrade its own security posture just because a server it discovered happens to support a weaker method (or none). Refuse and fail loud, don't silently proceed.

---

## Short-lived, audience-scoped JWTs — blast radius, not just "signed"

`auth_server/security.py`'s `create_access_token` signs a JWT with RS256 (asymmetric — the MCP server only ever needs the *public* key to verify, and can never forge a token even if fully compromised) and sets:

```python
"iss": ISSUER,       # who issued this
"aud": audience,      # who this token is *for* — see below
"exp": now + ttl,     # 5 minutes by default
"scope": scope,       # what it authorizes
```

Two properties do most of the security work:

1. **Short TTL (5 minutes).** A stolen token is only useful for a few minutes, not indefinitely. `client/token_store.py`'s `get_valid_access_token()` proactively refreshes before expiry, so this cost is invisible to normal operation but real for an attacker.
2. **Audience binding.** `aud` names *this specific claims MCP server*. If the same OAuth pattern is deployed for a second, unrelated resource (say, a policy-quoting MCP server), a token minted for the claims server fails verification there — `jwt.InvalidAudienceError` — even if it's a perfectly valid, unexpired, correctly-signed token. This stops a token leaked from one system being replayed against a different one just because they share an Authorization Server.

---

## The Four-Layer Protection Model

This is the mental model to hold the whole system in your head at once — four independent checks, each answering a different question, none of which substitutes for the others:

```text
Layer 1 — Identity           "Who are you?"
  OAuth 2.1 + PKCE            mcp_server/auth.py: verify_token()
  Prevents: forged/stolen credentials, authorization-code interception

Layer 2 — API Authorization  "What tools can you call?"
  Scope + Audience            mcp_server/auth.py: require_scopes()
  Prevents: a claims.read-only grant being used to call claims.adjudicate

Layer 3 — Agent Authorization "How much can you do?"
  Agent Policy (wall #2)      mcp_server/policies.py: check_adjudication_policy()
  Prevents: a valid claims.adjudicate token adjudicating a claim outside
  this agent's settlement authority, claim-type allowlist, or AI-assist queue

Layer 4 — Business Confirmation "Did this go through the right process?"
  Review → Adjudicate + Idempotency   mcp_server/tools.py
  Prevents: a decision becoming binding without being frozen and (for a real
  deployment) human-confirmed first; a network retry double-adjudicating
```

**The key insight, stated as plainly as possible: authorizing an agent to access a claims system is not the same claim as authorizing it to finalize every settlement it's technically capable of calling the API for.** A production incident report that says "the OAuth was configured correctly" is not the same as an incident report that says "nothing went wrong" — Layers 3 and 4 are where most of the actual business risk in an adjuster-assist agent lives, and they're the layers a generic "connect to OAuth" enterprise MCP writeup usually skips.

---

## Scope is not policy (the two-wall model, in depth)

It's tempting to read `claims.adjudicate` as "this agent can adjudicate claims" and stop there. `mcp_server/policies.py` exists specifically to break that assumption:

```python
def check_adjudication_policy(claim: dict, settlement_amount: float) -> None:
    if claim["status"] != AI_ASSIST_QUEUE_STATUS:
        raise HTTPException(403, "... not in the AI-assist queue ...")
    if claim["claim_type"] not in ALLOWED_CLAIM_TYPES:
        raise HTTPException(403, "... outside agent settlement authority ...")
    if settlement_amount > MAX_SETTLEMENT_USD:
        raise HTTPException(403, "... exceeds agent settlement authority ...")
```

Every one of these checks runs **after** the OAuth scope check has already passed. A caller presenting a perfectly valid, unexpired, correctly-scoped token for a real, authenticated adjuster session still gets a 403 here if the specific claim is out of bounds. This is deliberate defense in depth, and it maps onto a real, pre-existing insurance concept: **settlement authority tiers**. A junior adjuster at a real carrier doesn't get to settle a six-figure claim just because they're logged in — their *authority level* caps what they can approve without escalation, entirely independent of whether their login itself is valid. This POC's agent is modeled as the most junior possible adjuster on the team: narrow claim types, low dollar cap, and further restricted to a firewalled subset of claims (`AI_ASSIST_QUEUE_STATUS`) an ops lead explicitly routed for AI-assisted handling — the claims-domain equivalent of Robinhood's isolated, separately-funded Agentic account, which the real-world system this POC is derived from uses for exactly the same reason (see `xingai-robinhood-mcp` ADR-001's G6 gate).

---

## Review → Adjudicate as a *separate* defense layer from OAuth

`review_claim_decision` and `submit_claim_decision` are two different tools requiring two different scopes for a reason that has nothing to do with OAuth mechanics: **a decision that's merely proposed and a decision that's binding are different levels of risk, and conflating them into one tool call removes the ability to gate them differently.**

```python
# mcp_server/tools.py — tool_submit_claim_decision()
def tool_submit_claim_decision(review_id: str, idempotency_key: str, user_id: str) -> dict:
    ...
```

Notice what this function's signature does **not** accept: `claim_id`, `decision`, `settlement_amount`. Everything that matters was frozen inside the review record the instant `review_claim_decision` ran. There is no code path — not a parameter, not a header, nothing — by which calling `submit_claim_decision` can finalize a decision that wasn't already reviewed exactly as written. If an agent (or a compromised/confused LLM behind the agent) tries to "helpfully" adjust the settlement amount at submit time, there's no field to put that adjustment in. It has to go back through `review_claim_decision`, which re-runs wall #2 from scratch.

In a real deployment, the gap between review and submit is exactly where a human adjuster's confirmation belongs (`client/main.py`'s `input("Type YES to finalize...")` is the demo's stand-in for that). OAuth answered "is this agent allowed to touch the claims system" minutes or hours earlier when the token was issued — it cannot answer "does a human agree with this specific $640 decision, right now." That's a different question, asked at a different time, and needs a different mechanism.

---

## Idempotency is a security property, not just a UX nicety

```python
with _idempotency_lock:
    cached = _idempotency_results.get(idempotency_key)
    if cached:
        return {**cached, "idempotent": True}
```

Network calls fail, time out, and get retried — by the agent's own retry logic, or by a human re-clicking. Without an idempotency key, a retried `submit_claim_decision` call would attempt to redeem the same `review_id` twice; `review["used"]` already prevents that specific case with a 409. But the idempotency key protects a related, sneakier case: a retry after a response was lost in transit but the first call actually succeeded server-side — the client can't tell "it failed" from "it succeeded but I never got the response," and blindly retrying with a *new* `idempotency_key` (or none) risks a second finalization. Keying the cached result on a client-supplied `idempotency_key` makes retries provably safe: same key, same result, every time, regardless of how many times it's sent.

---

## From this POC to a real claims deployment

| This POC | Production equivalent |
|----------|-------------------------|
| `auth_server/` (in-memory, one hardcoded user) | Okta / Auth0 / Azure AD B2C, or a hardened homegrown IdP with real login, MFA, session management |
| `mcp_server/policies.py`'s `MOCK_CLAIMS`/`MOCK_POLICIES` | A real MCP wrapper in front of Guidewire ClaimCenter, Duck Creek Claims, or a homegrown claims system |
| `MAX_SETTLEMENT_USD` / `ALLOWED_CLAIM_TYPES` (two constants) | A real authority-matrix service, one profile per agent deployment / branch office, versioned and auditable |
| In-memory `_reviews` / `_idempotency_results` / `storage` dicts | PostgreSQL (codes, clients, consent) + Redis (short-TTL codes, idempotency keys), shared across replicas |
| `keys/private.pem` on disk | Key Vault / HSM; JWKS key rotation with overlapping validity windows |
| No audit trail | Append-only log (who, what claim, what tool, what decision, what outcome), retained per state insurance-regulator requirements |
| Fixed demo consent, not persisted | Real, queryable, revocable consent records per (user, client, scope) |
| No rate limiting | Per-agent, per-tool rate limits — matters more once a real LLM (not a scripted demo) is choosing when to call tools |
| Plain HTTP on localhost | HTTPS everywhere; token endpoint responses marked no-store |

## Pre-Launch Checklists

Adapted from the [source lab](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)'s production-upgrade checklists — treat every unchecked item below as a real blocker before touching a real claims system, not a nice-to-have:

**Authorization Server**
- [ ] Authorization code is single-use, TTL ≤ 120s, `code_challenge_method=S256` enforced (never `plain`)
- [ ] PKCE verification uses constant-time compare
- [ ] `redirect_uri` is exact-string matched, never prefix/wildcard
- [ ] Access token TTL ≤ 300s; refresh token rotation revokes the old token the instant a new one issues
- [ ] Revocation endpoint returns 200 even for unknown tokens (prevents enumeration)
- [ ] An empty `access_token` is never returned to a client (see "common mistake" below)
- [ ] Private key lives in a Key Vault/HSM, never in the repository or a general-purpose filesystem
- [ ] Consent is persisted, queryable, and revocable from an admin console

**Claims MCP Server**
- [ ] Every request is verified — no caching of a "this token was valid" result across requests
- [ ] `iss`, `aud`, `exp` all checked, not just signature
- [ ] Each tool has its own scope requirement; insufficient scope returns 403, not 401
- [ ] Agent policy (wall #2) is implemented independently of scope, never folded into it
- [ ] Review records persist in a real DB with row-level locking, not an in-process dict
- [ ] Submit/adjudicate never accepts mutable business parameters — only a review reference
- [ ] Idempotency keys have a bounded retention TTL (e.g. 7 days), not forever
- [ ] Error responses never leak internal stack traces
- [ ] Rate limiting exists per agent, per tool

## A common mistake worth naming explicitly

The source article behind this POC notes a real, previously-reported failure mode in a community Robinhood MCP client: a token endpoint returning HTTP 200 with an **empty** `access_token` got silently treated as a successful login. `client/oauth.py`'s `exchange_code_for_token` guards against exactly this:

```python
access_token = token_data.get("access_token", "")
if not access_token:
    raise ValueError("Token response contains no access_token — refusing to treat this as a successful login")
```

The general lesson generalizes past this one bug: **choosing the right protocol (OAuth 2.1 + PKCE) is necessary but not sufficient.** Every token exchange, every claim verification, every response from an external system needs its own explicit validation — "the HTTP call returned 200" is a transport-layer fact, not a business-layer guarantee that anything useful actually happened.
