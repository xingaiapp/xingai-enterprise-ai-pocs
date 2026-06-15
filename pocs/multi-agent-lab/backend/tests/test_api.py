from __future__ import annotations


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "openai_configured" in data
    assert "model" in data


def test_demo_agents_returns_registry(client):
    res = client.get("/demo/agents")
    assert res.status_code == 200
    data = res.json()
    assert "agents" in data
    assert "mcp" in data
    # Phase 1 agents must all be present
    names = [a["name"] for a in data["agents"]]
    assert "Orchestrator Agent" in names
    assert "Research Agent" in names
    assert "Product Agent" in names
    assert "Tech Agent" in names
    assert "Critic Agent" in names


def test_demo_metrics_returns_expected_keys(client):
    res = client.get("/demo/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "total_requests" in data
    assert "success_rate" in data
    assert "avg_latency_ms" in data
    assert "phase" in data


def test_demo_run_empty_input_uses_default(client):
    res = client.post("/demo/run", json={"user_input": "", "goal": "product_ideation"})
    assert res.status_code == 200
    data = res.json()
    assert "request_id" in data
    assert "final_answer" in data
    assert len(data["final_answer"]) > 0


def test_demo_run_custom_input(client):
    res = client.post("/demo/run", json={"user_input": "Build an invest AI product", "goal": "product_ideation"})
    assert res.status_code == 200
    data = res.json()
    assert "request_id" in data
    assert "sections" in data
    sections = data["sections"]
    assert "research" in sections
    assert "product" in sections
    assert "tech" in sections
    assert "critic" in sections


def test_demo_run_input_too_long_returns_422(client):
    res = client.post("/demo/run", json={"user_input": "x" * 2001})
    assert res.status_code == 422


def test_demo_run_pipeline_errors_field_present(client):
    res = client.post("/demo/run", json={"user_input": "test input"})
    assert res.status_code == 200
    assert "pipeline_errors" in res.json()


def test_demo_trace_after_run(client):
    run_res = client.post("/demo/run", json={"user_input": "trace test"})
    assert run_res.status_code == 200
    request_id = run_res.json()["request_id"]

    trace_res = client.get(f"/demo/trace/{request_id}")
    assert trace_res.status_code == 200
    data = trace_res.json()
    assert data["request_id"] == request_id
    assert "trace" in data
    assert len(data["trace"]) >= 6  # at least 6 steps (planning + 4 agents + synthesis)


def test_demo_trace_not_found(client):
    res = client.get("/demo/trace/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


def test_demo_trace_invalid_id(client):
    res = client.get("/demo/trace/" + "x" * 37)
    assert res.status_code == 400


def test_trace_steps_have_required_fields(client):
    run_res = client.post("/demo/run", json={"user_input": "trace fields test"})
    request_id = run_res.json()["request_id"]
    trace_res = client.get(f"/demo/trace/{request_id}")
    for step in trace_res.json()["trace"]:
        assert "step" in step
        assert "agent_name" in step
        assert "tool_used" in step
        assert "duration_ms" in step
        assert step["duration_ms"] >= 0
