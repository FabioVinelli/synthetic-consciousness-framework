from copy import deepcopy

from jsonschema import Draft202012Validator, ValidationError
import pytest

from cafh.runtime.state import initial_state, record, schema, validate_state


def test_initial_state_conforms():
    state = initial_state("Inspect a response")
    validate_state(state)
    assert state["status"] == "initialized"
    assert state["self_model"] == state["memory_references"] == []
    assert state["objective"]["information_class"] == "intended"


def test_draft_2020_12_schema_valid():
    assert schema()["$schema"].endswith("draft/2020-12/schema")
    Draft202012Validator.check_schema(schema())


@pytest.mark.parametrize("mutation", [
    lambda s: s.pop("self_model"),
    lambda s: s.update(updated_at="not-a-date"),
    lambda s: s.update(unexpected=True),
    lambda s: s["objective"].update(confidence=1.01),
    lambda s: s["objective"].update(information_class="certain"),
    lambda s: s["objective"].update(provenance=[]),
    lambda s: s["objective"].update(information_class="unknown", confidence=0.5),
    lambda s: s.update(status="completed"),
])
def test_invalid_schema_state_rejected(mutation):
    state = initial_state("Inspect")
    mutation(state)
    with pytest.raises(ValidationError):
        validate_state(state)


def test_duplicate_ids_rejected():
    state = initial_state("Inspect")
    state["beliefs"] = [record("goal", "Duplicate")]
    with pytest.raises(ValueError, match="Duplicate"):
        validate_state(state)


@pytest.mark.parametrize("field,maximum", [("cycles_completed", "max_cycles"),
                                          ("reflection_depth", "max_reflection_depth"),
                                          ("no_progress_steps", "max_no_progress_steps")])
def test_control_limit_rejected(field, maximum):
    state = initial_state("Inspect")
    state["control"][field] = state["control"][maximum] + 1
    with pytest.raises(ValueError):
        validate_state(state)


def test_resource_limit_rejected():
    state = initial_state("Inspect")
    state["control"]["resource_limits"][0]["used"] = 100
    with pytest.raises(ValueError, match="Resource"):
        validate_state(state)


def test_snapshots_and_public_state_are_isolated(make_engine):
    engine = make_engine()
    engine.run_cycle("input")
    prior = deepcopy(engine.trace.events[0])
    public = engine.state
    public["objective"]["statement"] = "mutated"
    events = engine.trace.events
    events[0]["state"]["objective"]["statement"] = "mutated"
    engine.run_cycle("input")
    assert engine.state["objective"]["statement"] != "mutated"
    assert engine.trace.events[0] == prior
