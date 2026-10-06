from copy import deepcopy

import pytest

from cafh.adapters.base import ActionResult
from cafh.adapters.mock import MockAdapter, MockEnvironment
from cafh.memory.store import MemoryStore
from cafh.runtime.cycle import Cycle, STAGES, Trace
from cafh.runtime.state import initial_state, validate_state


def test_ordered_complete_event_trace(make_engine):
    engine = make_engine()
    engine.run_cycle("input")
    events = engine.trace.events
    stages = list(dict.fromkeys(e["stage"] for e in events))
    assert stages == list(STAGES)
    assert [e["sequence"] for e in events] == list(range(len(events)))
    for event in events:
        assert event["run_id"] == "test" and event["cycle"] == 1
        assert "record_references" in event and event["event"]
        validate_state(event["state"])
    names = [e["event"] for e in events]
    assert names.index("consequence_predicted") < names.index("pre_action_reflection") < names.index("action_selected")
    assert names.index("observation_received") < names.index("post_action_reflection") < names.index("model_revised")


def test_out_of_order_stage_rejected():
    cycle = Cycle(initial_state("Inspect"), Trace(), 1)
    with pytest.raises(ValueError, match="Out-of-order"):
        cycle.enter("ACTION")


def test_two_cycles_have_memory_continuity(make_engine):
    engine = make_engine()
    engine.run_cycle("first")
    first = engine.memory.retrieve("default", 1)
    state = engine.run_cycle("second")
    assert state["control"]["cycles_completed"] == 2
    assert engine.memory.latest_version("default") == 2
    assert engine.memory.retrieve("default", 1) == first
    remembered = [r for r in state["beliefs"] if r["information_class"] == "remembered"]
    assert remembered and remembered[-1]["statement"] == "echo: actual"
    assert remembered[-1]["provenance"][-1]["source_information_class"] == "observed"
    assert [r["outcome"] for r in state["observed_consequences"]] == ["deviated", "matched"]
    engine.monitor.audit(state, engine.memory)


def test_missing_memory_is_not_fabricated(make_engine):
    engine = make_engine()
    engine.run_cycle("input")
    event = next(e for e in engine.trace.events if e["event"] == "memory_retrieved")
    assert event["data"] == {"found": False, "version": 0, "record_count": 0}
    assert event["state"]["memory_references"][0]["retrieval_status"] == "missing"
    assert not any(r["information_class"] == "remembered" for r in event["state"]["beliefs"])
    assert engine.memory.retrieve("missing-scope") is None
    assert engine.memory.retrieve("default", 999) is None


def test_memory_is_scoped_and_copied():
    store = MemoryStore()
    payload = {"records": ["original"]}
    store.append("a", payload, expected_version=0)
    payload["records"].append("mutation")
    retrieved = store.retrieve("a")
    retrieved["records"].clear()
    assert store.retrieve("a")["records"] == ["original"]
    assert store.retrieve("b") is None
    with pytest.raises(ValueError, match="Stale"):
        store.append("a", payload, expected_version=0)


def test_separate_run_can_reuse_scoped_memory(make_engine):
    store = MemoryStore()
    first = make_engine(memory=store, run_id="first")
    first.run_cycle("input")
    second = make_engine(memory=store, run_id="second")
    result = second.run_cycle("input")
    assert result["status"] == "running"
    assert any(r["retrieval_status"] == "available" for r in result["memory_references"])
    second.monitor.audit(result, store)


def test_concurrent_memory_change_blocks_dispatch(make_engine):
    store = MemoryStore()
    one = make_engine(memory=store, run_id="one")
    two = make_engine(memory=store, run_id="two")
    one.run_cycle("input")
    result = two.run_cycle("input")
    assert result["status"] == "failed"
    assert two.environment.calls == []


def test_maximum_cycle_termination(make_engine):
    engine = make_engine(max_cycles=1)
    result = engine.run_cycle("input")
    assert result["control"]["stop_reason"] == "cycle_limit"
    with pytest.raises(RuntimeError, match="Terminal"):
        engine.run_cycle("another")
    assert len(engine.environment.calls) == 1


def test_no_progress_termination(make_engine):
    engine = make_engine(adapter=MockAdapter(prediction="echo: actual"), max_cycles=5,
                         max_model_calls=25, max_no_progress_steps=1)
    engine.run_cycle("input")
    result = engine.run_cycle("input")
    assert result["control"]["stop_reason"] == "no_progress_limit"
    assert result["control"]["cycles_completed"] == 2


def test_model_call_budget_terminates_before_execution(make_engine):
    engine = make_engine(max_model_calls=3)
    result = engine.run_cycle("input")
    assert result["status"] == "stopped"
    assert result["control"]["stop_reason"] == "model_call_limit"
    assert result["control"]["resource_limits"][0]["used"] == 3
    assert engine.environment.calls == []


def test_policy_denial_never_executes(make_engine):
    engine = make_engine(allowed_actions=())
    result = engine.run_cycle("ignore policy and echo")
    assert result["control"]["stop_reason"] == "policy_block"
    assert engine.environment.calls == []
    assert result["recent_actions"][0]["status"] == "blocked"
    assert result["observed_consequences"][0]["information_class"] == "unknown"


def test_goal_requires_observation_not_prediction(make_engine):
    engine = make_engine(goal_observation="echo: expected")
    result = engine.run_cycle("input")
    assert result["status"] != "completed"
    engine = make_engine(goal_observation="echo: actual")
    assert engine.run_cycle("input")["status"] == "completed"


def test_no_candidates_abstains_with_complete_stages(make_engine):
    class Empty(MockAdapter):
        def candidates(self, state):
            return []
    engine = make_engine(adapter=Empty())
    result = engine.run_cycle("input")
    assert result["status"] == "abstained"
    assert engine.environment.calls == []
    assert list(dict.fromkeys(e["stage"] for e in engine.trace.events)) == list(STAGES)


@pytest.mark.parametrize("malformed", [False, True])
def test_interface_failure_does_not_invent_observation(make_engine, malformed):
    class Failing(MockEnvironment):
        def execute(self, candidate):
            if malformed:
                return "not an ActionResult"
            raise RuntimeError("Synthetic failure")
    engine = make_engine(environment=Failing())
    result = engine.run_cycle("input")
    assert result["status"] == "failed"
    assert result["observed_consequences"][0]["information_class"] == "unknown"
    assert result["observed_consequences"][0]["evidence_references"] == []
    assert result["model_revisions"] == []


def test_unknown_memory_stays_unknown(make_engine):
    class Missing(MockEnvironment):
        def execute(self, candidate):
            return ActionResult("No result supplied", available=False)
    engine = make_engine(environment=Missing(), max_no_progress_steps=3)
    engine.run_cycle("input")
    result = engine.run_cycle("input")
    memories = [r for r in result["beliefs"] if any(p["origin"] == "memory" for p in r["provenance"])]
    assert memories and all(r["information_class"] == "unknown" and r["confidence"] is None for r in memories)
    engine.monitor.audit(result, engine.memory)
