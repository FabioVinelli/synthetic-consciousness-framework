import pytest

from cafh.adapters.mock import MockAdapter


def test_matched_prediction_does_not_create_revision(make_engine):
    engine = make_engine(adapter=MockAdapter(prediction="echo: actual"))
    state = engine.run_cycle("input")
    assert state["observed_consequences"][0]["outcome"] == "matched"
    assert state["model_revisions"] == []


def test_deviation_creates_explicit_revision_preserving_prediction(make_engine):
    engine = make_engine()
    state = engine.run_cycle("input")
    prediction = state["predicted_consequences"][0]
    observation = state["observed_consequences"][0]
    revision = state["model_revisions"][0]
    assert observation["outcome"] == "deviated"
    assert revision["prior_record_reference"] == prediction["id"]
    assert revision["trigger_references"] == [observation["id"]]
    replacement = next(r for r in state["world_model"] if r["id"] == revision["replacement_record_reference"])
    assert replacement["statement"] == observation["statement"]
    assert prediction["statement"] == "echo: expected"
    assert prediction["information_class"] == "hypothesized"
    prior_event = next(e for e in engine.trace.events if e["event"] == "consequence_predicted")
    assert prior_event["state"]["predicted_consequences"][0] == prediction


def test_pre_and_post_action_hooks_are_separate(make_engine):
    engine = make_engine()
    engine.run_cycle("input")
    pre = next(e for e in engine.trace.events if e["event"] == "pre_action_reflection")
    post = next(e for e in engine.trace.events if e["event"] == "post_action_reflection")
    assert pre["data"]["allowed"] is True
    assert pre["state"]["observed_consequences"] == []
    assert post["data"]["mismatch"] is True
    assert post["state"]["observed_consequences"]


@pytest.mark.parametrize("limit,expected_revisions", [(0, 0), (1, 1)])
def test_reflection_depth_termination(make_engine, limit, expected_revisions):
    engine = make_engine(max_reflection_depth=limit, requested_reflection_depth=5)
    state = engine.run_cycle("input")
    assert state["control"]["stop_reason"] == "reflection_depth_limit"
    assert state["control"]["reflection_depth"] == limit
    assert len(state["model_revisions"]) == expected_revisions
    assert any(e["event"] == "reflection_stopped" for e in engine.trace.events)


def test_recursive_reflection_stops_without_new_evidence(make_engine):
    engine = make_engine(max_reflection_depth=10, requested_reflection_depth=10)
    state = engine.run_cycle("input")
    stopped = [e for e in engine.trace.events if e["event"] == "reflection_stopped"]
    assert stopped[-1]["data"]["reason"] == "no_new_evidence"
    assert state["control"]["reflection_depth"] == 2
    assert len(state["model_revisions"]) == 1
