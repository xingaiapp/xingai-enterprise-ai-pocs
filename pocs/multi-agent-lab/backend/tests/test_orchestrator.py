from __future__ import annotations

from agents.orchestrator import _run_safe, run_pipeline


def _ok_agent():
    return {"result": "ok"}, "openai"


def _empty_agent():
    return {}, "openai"


def _raising_agent():
    raise ValueError("boom")


def test_run_safe_success():
    result, backend, err = _run_safe("Test Agent", _ok_agent)
    assert result == {"result": "ok"}
    assert backend == "openai"
    assert err is None


def test_run_safe_empty_result_uses_fallback():
    result, backend, err = _run_safe("Test Agent", _empty_agent, fallback_fn=lambda: {"fallback": True})
    assert result == {"fallback": True}
    assert backend == "fallback"
    assert err is not None
    assert "empty result" in err


def test_run_safe_exception_uses_fallback():
    result, backend, err = _run_safe("Test Agent", _raising_agent, fallback_fn=lambda: {"fallback": True})
    assert result == {"fallback": True}
    assert backend == "error"
    assert "boom" in err


def test_run_safe_no_fallback_returns_empty_on_failure():
    result, backend, err = _run_safe("Test Agent", _empty_agent)
    assert result == {}
    assert err is not None


def test_pipeline_runs_without_openai(db):
    """Full pipeline must complete in fallback mode (no API key set)."""
    result = run_pipeline(db, "Build an invest AI product")
    assert "request_id" in result
    assert "final_answer" in result
    assert len(result["final_answer"]) > 0
    assert "sections" in result
    assert "pipeline_errors" in result


def test_pipeline_sections_are_non_empty(db):
    result = run_pipeline(db, "Build a meal coach app")
    sections = result["sections"]
    # Each section should have at least one key even in fallback mode
    assert len(sections["research"]) > 0
    assert len(sections["product"]) > 0
    assert len(sections["tech"]) > 0
    assert len(sections["critic"]) > 0


def test_pipeline_trace_is_persisted(db):
    from trace import get_trace
    result = run_pipeline(db, "Enterprise workflow automation")
    rid = result["request_id"]
    trace = get_trace(db, rid)
    assert trace is not None
    assert len(trace["trace"]) == 6  # planning + 4 agents + synthesis


def test_pipeline_empty_input_uses_default_prompt(db):
    result = run_pipeline(db, "")
    assert "XingAI" in result["final_answer"] or len(result["final_answer"]) > 100
