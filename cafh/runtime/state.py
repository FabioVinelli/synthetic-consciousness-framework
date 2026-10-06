"""State construction and local Draft 2020-12 validation."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker


COLLECTIONS = (
    "constraints", "self_model", "world_model", "active_intentions", "attention",
    "beliefs", "uncertainties", "assumptions", "capabilities", "limitations",
    "unresolved_questions", "recent_actions", "predicted_consequences",
    "observed_consequences", "model_revisions", "memory_references",
)
TERMINAL = {"completed", "abstained", "escalated", "stopped", "failed"}


def logical_time(revision):
    """Reproducible logical timestamp, NOT a claim of wall-clock observation time."""
    return (datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=revision)).isoformat()


@lru_cache(maxsize=1)
def schema():
    source = Path(__file__).resolve().parents[2] / "schemas/conscious_state.schema.json"
    if not source.is_file():
        source = Path(sys.prefix) / "share/cafh/conscious_state.schema.json"
    value = json.loads(source.read_text())
    Draft202012Validator.check_schema(value)
    return value


def validate_record(record, definition="record"):
    contract = {"$schema": schema()["$schema"], "$defs": schema()["$defs"],
                "$ref": "#/$defs/" + definition}
    Draft202012Validator(contract, format_checker=FormatChecker()).validate(record)


def records(state):
    yield state["objective"]
    yield state["reflection"]["assessment"]
    for name in COLLECTIONS:
        if name != "memory_references":
            yield from state[name]


def validate_state(state):
    Draft202012Validator(schema(), format_checker=FormatChecker()).validate(state)
    ids = [r["id"] for r in records(state)] + [r["id"] for r in state["memory_references"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate state record ID")
    c = state["control"]
    if c["cycles_completed"] > c["max_cycles"] or c["reflection_depth"] > c["max_reflection_depth"]:
        raise ValueError("Control limit exceeded")
    if c["no_progress_steps"] > c["max_no_progress_steps"]:
        raise ValueError("No-progress limit exceeded")
    if any(r["used"] > r["limit"] for r in c["resource_limits"]):
        raise ValueError("Resource limit exceeded")


def record(key, statement, kind="reported", *, origin="model", source="model:proposal",
           evidence=(), support="unassessed", confidence=None, **extra):
    value = dict(id=key, statement=statement, information_class=kind,
                 provenance=[dict(source_reference=source, locator=source, origin=origin,
                                  source_information_class=None, captured_at=None, transformation=None)],
                 confidence=confidence, evidence_status=support,
                 evidence_references=list(evidence), counterevidence_references=[],
                 revision_conditions=["New independently recorded evidence or changed constraints"], **extra)
    return value


def initial_state(objective, *, run_id="run", scope="default", max_cycles=2,
                  max_reflection_depth=1, max_no_progress_steps=2, max_model_calls=10):
    state = {name: [] for name in COLLECTIONS}
    state.update(schema_version="0.1", run_id=run_id, state_revision=0,
                 previous_state_reference=None, continuity_scope=scope, updated_at=logical_time(0),
                 phase="INPUT", status="initialized",
                 objective=record("goal", objective, "intended", origin="trusted_configuration", source="config:goal"),
                 values_check=dict(policy_references=[], disposition="pending", rationale="Not checked",
                                   conflict_references=[], authorization_reference=None),
                 reflection=dict(assessment=record("reflection:initial", "No reflection performed", "unknown",
                                                   origin="trusted_configuration", source="config:initial"),
                                 prediction_references=[], observation_references=[], revision_references=[],
                                 progress="not_assessed", next_disposition="continue"),
                 control=dict(max_cycles=max_cycles, cycles_completed=0,
                              max_reflection_depth=max_reflection_depth, reflection_depth=0,
                              max_no_progress_steps=max_no_progress_steps, no_progress_steps=0,
                              resource_limits=[dict(name="model_calls", unit="call", limit=max_model_calls, used=0)],
                              stop_reason=None))
    validate_state(state)
    return deepcopy(state)
