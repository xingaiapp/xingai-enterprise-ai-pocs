from __future__ import annotations

from tools.fake_research_tool import _match_topic, fake_research_lookup


def test_match_topic_invest():
    assert _match_topic("I want to build an invest AI tool") == "invest"


def test_match_topic_meal():
    assert _match_topic("Build a meal planning app") == "meal"


def test_match_topic_learn():
    assert _match_topic("SAT prep and study helper") == "learn"


def test_match_topic_enterprise():
    assert _match_topic("Enterprise workflow automation") == "enterprise"


def test_match_topic_default():
    assert _match_topic("Something completely unrelated") == "default"


def test_fake_research_lookup_returns_dict(db):
    result, tool = fake_research_lookup(db, "I want to build an invest product")
    assert isinstance(result, dict)
    assert "trend" in result
    assert "opportunity" in result
    assert tool in ("fake_research_tool", "cache_tool")


def test_fake_research_lookup_caches_on_second_call(db):
    fake_research_lookup(db, "invest topic for caching test")
    _, tool = fake_research_lookup(db, "invest topic for caching test")
    assert tool == "cache_tool"


def test_different_topics_return_different_fixtures(db):
    invest, _ = fake_research_lookup(db, "build an invest AI")
    meal, _ = fake_research_lookup(db, "build a meal coach app")
    assert invest["trend"] != meal["trend"]
