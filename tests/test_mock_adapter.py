import pytest

from cafh.adapters.base import Candidate, ModelAdapter
from cafh.adapters.mock import MockAdapter, MockEnvironment
from cafh.runtime.engine import RuntimeConfig
from cafh.runtime.state import initial_state


def test_model_adapter_is_abstract():
    with pytest.raises(TypeError):
        ModelAdapter()


def test_mock_calls_are_deterministic():
    adapter = MockAdapter()
    state = initial_state("Inspect")
    for stage in ("WORLD MODEL", "SELF MODEL", "INTERPRETATIONS"):
        assert adapter.propose(stage, state) == adapter.propose(stage, state)
    assert adapter.candidates(state) == adapter.candidates(state)
    assert adapter.predict(Candidate("echo", "actual"), state) == adapter.predict(Candidate("echo", "actual"), state)


def test_complete_repeated_execution_identical(make_engine):
    one, two = make_engine(), make_engine()
    for input_text in ("one", "two"):
        assert one.run_cycle(input_text) == two.run_cycle(input_text)
    assert one.trace.events == two.trace.events
    assert one.memory.retrieve("default") == two.memory.retrieve("default")


def test_model_cannot_mutate_controller_state(make_engine):
    class Mutating(MockAdapter):
        def propose(self, stage, state):
            result = super().propose(stage, state)
            state["objective"]["statement"] = "Changed goal"
            state["control"]["max_cycles"] = 10000
            return result
    engine = make_engine(adapter=Mutating())
    state = engine.run_cycle("input")
    assert state["objective"]["statement"] == "Inspect a local response"
    assert state["control"]["max_cycles"] == 2


def test_no_credentials_or_network_required(make_engine, monkeypatch):
    import socket
    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected network call")
    monkeypatch.setattr(socket, "socket", forbidden)
    engine = make_engine()
    assert engine.run_cycle("input")["status"] == "running"


@pytest.mark.parametrize("config", [{"max_cycles": 0}, {"max_reflection_depth": -1},
                                   {"max_model_calls": -1}, {"requested_reflection_depth": 0},
                                   {"max_no_progress_steps": 0}, {"allowed_actions": ["echo"]}])
def test_invalid_runtime_limits_rejected(config):
    with pytest.raises(ValueError):
        RuntimeConfig(**config)


def test_mock_environment_is_separate_action_boundary():
    environment = MockEnvironment()
    assert environment.execute(Candidate("echo", "value")).statement == "echo: value"
    with pytest.raises(ValueError):
        environment.execute(Candidate("other", "value"))
