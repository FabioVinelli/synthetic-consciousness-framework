from copy import deepcopy

import pytest

from cafh.adapters.mock import MockAdapter
from cafh.epistemics.monitor import Evidence, EpistemicError, EpistemicMonitor
from cafh.runtime.state import record


@pytest.mark.parametrize("kind", ["observed", "reported", "remembered", "inferred", "hypothesized", "imagined", "intended", "unknown"])
def test_eight_epistemic_classes_and_metadata_preserved(kind):
    monitor = EpistemicMonitor()
    monitor.register(Evidence("source", "Scoped claim", "environment", True))
    monitor.register(Evidence("counter", "Contrary report", "human", False))
    value = record("claim", "Scoped claim", kind, origin="environment", source="source",
                   evidence=["source"] if kind == "observed" else [],
                   confidence=None if kind == "unknown" else 0.4)
    value["counterevidence_references"] = ["counter"]
    before = deepcopy(value)
    checked = monitor.check(value)
    assert checked == before
    checked["statement"] = "different"
    assert value == before


def test_unknown_does_not_become_evidence_of_absence():
    monitor = EpistemicMonitor()
    value = record("unknown", "Whether a signal exists is unknown", "unknown")
    result = monitor.check(value, model_proposal=True)
    assert result == value
    assert result["evidence_status"] == "unassessed" and result["confidence"] is None


@pytest.mark.parametrize("forgery", ["observed", "supported", "origin", "reference"])
def test_model_cannot_self_certify_knowledge(forgery):
    monitor = EpistemicMonitor()
    value = record("claim", "A fabricated fact", "inferred")
    if forgery == "observed":
        value["information_class"] = "observed"
    elif forgery == "supported":
        value["evidence_status"] = "supported"
    elif forgery == "origin":
        value["provenance"][0]["origin"] = "environment"
    else:
        value["evidence_references"] = ["invented"]
    with pytest.raises(EpistemicError):
        monitor.check(value, model_proposal=True)


def test_unrelated_real_evidence_cannot_support_new_claim():
    monitor = EpistemicMonitor()
    monitor.register(Evidence("real", "A different observation", "environment", True))
    value = record("claim", "Unknown fact asserted", "inferred", support="supported", evidence=["real"])
    with pytest.raises(EpistemicError, match="No independently"):
        monitor.check(value, model_proposal=True)


def test_registered_matching_evidence_can_support_scoped_claim():
    monitor = EpistemicMonitor()
    monitor.register(Evidence("real", "Measured output", "environment", True))
    value = record("claim", "Measured output", "inferred", support="supported", evidence=["real"])
    assert monitor.check(value, model_proposal=True) == value


def test_report_is_not_verified_merely_because_registered():
    monitor = EpistemicMonitor()
    monitor.register(Evidence("report", "Claim", "human", False))
    with pytest.raises(EpistemicError):
        monitor.check(record("claim", "Claim", "inferred", support="supported", evidence=["report"]), model_proposal=True)


def test_unknown_cannot_be_promoted_by_later_model_assertion(make_engine):
    class Asserting(MockAdapter):
        def predict(self, candidate, state):
            return record("assertion", "The next action outcome is now certain", "inferred",
                          support="supported", confidence=1.0)
    engine = make_engine(adapter=Asserting())
    state = engine.run_cycle("input")
    assert state["status"] == "failed"
    assert state["uncertainties"][0]["information_class"] == "unknown"
    assert state["uncertainties"][0]["confidence"] is None
    assert state["predicted_consequences"] == []
    assert engine.environment.calls == []


def test_uncertainties_survive_multiple_cycles(make_engine):
    engine = make_engine()
    first = engine.run_cycle("input")["uncertainties"][0]
    state = engine.run_cycle("input")
    assert first in state["uncertainties"]
    assert all(r["information_class"] == "unknown" and r["confidence"] is None for r in state["uncertainties"])


@pytest.mark.parametrize("mutate", [
    lambda s: s["predicted_consequences"][0].update(action_reference="missing"),
    lambda s: s["observed_consequences"][0].update(action_reference="missing"),
    lambda s: s["observed_consequences"][0].update(prediction_references=["missing"]),
    lambda s: s["observed_consequences"][0].update(outcome="matched"),
    lambda s: s["model_revisions"][0].update(prior_record_reference="missing"),
    lambda s: s["model_revisions"][0].update(replacement_record_reference="missing"),
    lambda s: s["model_revisions"][0].update(trigger_references=["missing"]),
    lambda s: s["model_revisions"][0].update(trigger_references=[]),
    lambda s: s["active_intentions"][0].update(goal_reference="missing"),
    lambda s: s["recent_actions"][0].update(intention_reference="missing"),
    lambda s: s["recent_actions"][0].update(authorization_reference="missing"),
    lambda s: s["recent_actions"][0].update(observation_references=[]),
    lambda s: s["attention"][0].update(target_references=["missing"]),
    lambda s: s["reflection"].update(revision_references=["missing"]),
    lambda s: s["values_check"].update(policy_references=["missing"]),
])
def test_invalid_semantic_reference_states_rejected(make_engine, mutate):
    engine = make_engine()
    state = engine.run_cycle("input")
    engine.monitor.audit(state, engine.memory)
    mutate(state)
    with pytest.raises(EpistemicError):
        engine.monitor.audit(state, engine.memory)


def test_fabricated_available_memory_rejected(make_engine):
    engine = make_engine()
    state = engine.run_cycle("input")
    state["memory_references"][0]["retrieval_status"] = "available"
    with pytest.raises(EpistemicError, match="Fabricated"):
        engine.monitor.audit(state, engine.memory)


def test_mutated_remembered_evidence_rejected(make_engine):
    engine = make_engine()
    engine.run_cycle("input")
    state = engine.run_cycle("input")
    remembered = next(r for r in state["beliefs"] if r["information_class"] == "remembered")
    remembered["confidence"] = 1.0
    with pytest.raises(EpistemicError, match="metadata"):
        engine.monitor.audit(state, engine.memory)


def test_cyclic_revision_rejected(make_engine):
    engine = make_engine()
    state = engine.run_cycle("input")
    reverse = deepcopy(state["model_revisions"][0])
    reverse["id"] = "reverse"
    reverse["prior_record_reference"], reverse["replacement_record_reference"] = reverse["replacement_record_reference"], reverse["prior_record_reference"]
    state["model_revisions"].append(reverse)
    with pytest.raises(EpistemicError, match="Cyclic"):
        engine.monitor.audit(state, engine.memory)


def test_evidence_registry_cannot_be_overwritten():
    monitor = EpistemicMonitor()
    monitor.register(Evidence("id", "One", "environment", True))
    with pytest.raises(EpistemicError, match="overwritten"):
        monitor.register(Evidence("id", "Two", "environment", True))


def test_observed_provenance_must_match_evidence():
    monitor = EpistemicMonitor()
    monitor.register(Evidence("real", "Scoped measurement", "environment", True))
    with pytest.raises(EpistemicError, match="provenance"):
        monitor.check(record("claim", "Scoped measurement", "observed", source="fake",
                             evidence=["real"], support="supported"))


def test_failed_adapter_proposal_still_consumes_call_budget(make_engine):
    class Bad(MockAdapter):
        def propose(self, stage, state):
            return [record("invalid", "Claim", "observed")]
    engine = make_engine(adapter=Bad())
    state = engine.run_cycle("input")
    assert state["status"] == "failed"
    assert state["control"]["resource_limits"][0]["used"] == 1
    assert state["world_model"] == []


def test_schema_valid_future_id_collision_is_rejected_cleanly(make_engine):
    class Collision(MockAdapter):
        def propose(self, stage, state):
            if stage == "WORLD MODEL":
                return [record("test:c1:attention", "Colliding ID")]
            return super().propose(stage, state)
    engine = make_engine(adapter=Collision())
    state = engine.run_cycle("input")
    assert state["status"] == "failed"
    assert engine.trace.events[-1]["event"] == "cycle_failed"
    assert engine.environment.calls == []
