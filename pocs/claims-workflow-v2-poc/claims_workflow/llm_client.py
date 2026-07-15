"""Shared Claude client wrapper for the Phase 2 LLM-backed agents.

Every LLM-backed agent (fraud_triage, fraud_scoring, policy_coverage,
adverse_action_letter) goes through complete_json() and is expected to
catch LLMError and fall back to its heuristic implementation — see
ADR-009 "Testing strategy". The `anthropic` import is lazy so this module
(and everything that imports it) loads fine even when the package isn't
installed, as long as is_available() is checked first.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

DEFAULT_MODEL = os.getenv("CLAIMS_WORKFLOW_LLM_MODEL", "claude-sonnet-5")


class LLMError(RuntimeError):
    """Raised for any failure in the LLM path — missing key, network
    error, or a response that doesn't parse as the expected JSON shape.
    Callers are expected to catch this specific exception and fall back to
    their heuristic implementation, not swallow arbitrary exceptions."""


def is_available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _call_anthropic(system: str, user: str, model: str) -> str:
    """Isolated in its own function so tests can monkeypatch exactly this
    call and inject a canned response without needing the anthropic
    package installed or a real API key."""
    try:
        import anthropic
    except ImportError as exc:
        raise LLMError(f"anthropic package not installed: {exc}") from exc

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text
    except Exception as exc:  # noqa: BLE001 — any SDK/network failure becomes LLMError
        raise LLMError(f"Anthropic API call failed: {exc}") from exc


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def complete_json(system: str, user: str, model: Optional[str] = None) -> dict[str, Any]:
    """Send a system+user prompt, expect a JSON object back (optionally
    wrapped in prose or a markdown code fence — this extracts the first
    {...} block), and return it parsed. Raises LLMError on any failure:
    missing key, network error, or unparseable response."""
    if not is_available():
        raise LLMError("ANTHROPIC_API_KEY not set")

    raw = _safe_call_anthropic(system, user, model or DEFAULT_MODEL)
    match = _JSON_BLOCK_RE.search(raw)
    if not match:
        raise LLMError(f"No JSON object found in model response: {raw[:200]!r}")

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise LLMError(f"Model response was not valid JSON: {exc}") from exc


def complete_text(system: str, user: str, model: Optional[str] = None) -> str:
    """Like complete_json but for free-text generation (e.g. letter
    drafting) where the response isn't a structured object."""
    if not is_available():
        raise LLMError("ANTHROPIC_API_KEY not set")
    text = _safe_call_anthropic(system, user, model or DEFAULT_MODEL).strip()
    if not text:
        raise LLMError("Model returned an empty response")
    return text


def _safe_call_anthropic(system: str, user: str, model: str) -> str:
    """Defense in depth around _call_anthropic: that function wraps SDK
    calls in its own try/except, but callers (or tests monkeypatching it
    directly) shouldn't be able to leak a raw, non-LLMError exception past
    this module's boundary — every agent's fallback logic depends on
    catching exactly LLMError, nothing broader."""
    try:
        return _call_anthropic(system, user, model)
    except LLMError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise LLMError(f"Unexpected error calling model: {exc}") from exc
