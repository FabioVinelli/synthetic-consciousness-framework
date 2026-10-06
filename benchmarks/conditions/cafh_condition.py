"""Bind shared primitives to the approved runtime's model/action interfaces."""
from copy import deepcopy

from cafh.adapters.base import ActionInterface, ActionResult, Candidate, ModelAdapter
from cafh.memory.store import MemoryStore
from cafh.runtime.engine import Engine, RuntimeConfig
from cafh.runtime.state import TERMINAL, record
from .common import BUDGET, choose, new_behavior

ABLATIONS = {
    "full": {},
    "no-self-model": {"enable_self_model": False},
    "no-memory-continuity": {"enable_memory_continuity": False},
    "no-reflection-revision": {"enable_reflection_revision": False},
}
BLOCKED = {
    "no-epistemic-monitor": "Record admission and trusted support/reference validation are inseparable in v0.1.",
    "no-consequence-model": "Action pre-reflection and observation references require a prediction.",
    "no-intentionality": "Actions require an existing intention and objective reference.",
}


class CountingMemory(MemoryStore):
    """Count every store method entry, including validation and nested lookups."""
    def __init__(self):
        super().__init__()
        self.operations = 0

    def retrieve(self, *args, **kwargs):
        self.operations += 1
        return super().retrieve(*args, **kwargs)

    def append(self, *args, **kwargs):
        self.operations += 1
        return super().append(*args, **kwargs)

    def latest_version(self, *args, **kwargs):
        self.operations += 1
        return super().latest_version(*args, **kwargs)


class TaskAdapter(ModelAdapter):
    def __init__(self, public):
        self.public = public
        self.step = public.steps[0]

    def propose(self, stage, state):
        prefix = f"{state['run_id']}:c{state['control']['cycles_completed']+1}"
        if stage == "INTERPRETATIONS":
            if self.step["unsupported_assertion"]:
                return [record(prefix+":attack", "unsupported proposition", "inferred", support="supported")]
            if self.step["reports"]:
                return [record(prefix+f":report:{i}", x["value"], source=x["source"])
                        for i, x in enumerate(self.step["reports"])]
            return [record(prefix+":gap", "No further evidence supplied", "unknown")]
        return [record(prefix+":"+stage.replace(" ", "-"), "Task context" if stage == "WORLD MODEL"
                       else "I can propose configured symbolic actions; outcomes require observation")]

    def candidates(self, state):
        memories = [r["statement"] for r in state["beliefs"] if r["information_class"] == "remembered"
                    and any(p.get("source_information_class") == "observed" for p in r["provenance"])]
        return [Candidate(**x) for x in choose(self.public, self.step, memories)]

    def predict(self, candidate, state):
        return record("proposal:prediction", self.step["prediction"], "hypothesized")


class TaskInterface(ActionInterface):
    def __init__(self, environment):
        self.environment = environment

    def execute(self, candidate):
        return ActionResult(self.environment.execute(candidate.name, candidate.argument))


def execute(public, environment, *, ablation, run_id):
    if ablation not in ABLATIONS:
        raise ValueError("Unavailable ablation: " + ablation)
    adapter, memory = TaskAdapter(public), CountingMemory()
    engine = Engine(adapter, TaskInterface(environment), objective=public.objective,
                    run_id=run_id, memory=memory,
                    config=RuntimeConfig(allowed_actions=public.allowed_actions, max_cycles=BUDGET["cycles"],
                                         max_no_progress_steps=3, max_model_calls=BUDGET["model_calls"],
                                         **ABLATIONS[ablation]))
    result = new_behavior()
    for step in public.steps:
        if engine.state["status"] in TERMINAL:
            break
        adapter.step = step
        engine.run_cycle("Public step: " + repr(step))
    events, state = engine.trace.events, engine.state
    # Preserve full record references, event data and final records. Repeated
    # full-state snapshots are omitted from the export, not from runtime tracing.
    result["trace"] = [{k: v for k, v in e.items() if k != "state"} for e in events]
    result["final_state"] = state
    result["claims"] = [dict(statement=r["statement"], supported=True, evidence=r["evidence_references"])
                        for values in state.values() if isinstance(values, list) for r in values
                        if r.get("evidence_status") == "supported" and any(p["origin"] == "model" for p in r.get("provenance", []))]
    for event in events:
        cycle, data, name = event["cycle"], event["data"], event["event"]
        if name == "interpretations_formed":
            prefix = f"{run_id}:c{cycle}:report:"
            result["reports"].extend(dict(source=r["provenance"][0]["source_reference"], value=r["statement"])
                                     for r in event["state"]["beliefs"] if r["id"].startswith(prefix))
        if name == "action_selected":
            if data.get("selected_action") is None:
                result["abstentions"].append(cycle)
            else:
                # Candidate selection is inspectable and no hidden oracle is used.
                intention = next(e for e in events if e["cycle"] == cycle and e["event"] == "intention_formed")
                candidate = intention["data"]["candidates"][0]
                result["actions"].append(dict(cycle=cycle, **candidate))
                if public.steps[cycle-1]["mode"] == "recall":
                    result["memories_used"].append(dict(cycle=cycle, statement=candidate["argument"]))
        if name == "observation_received":
            obs = data["observation"]
            if data.get("interface_error"):
                result["failures"].append(dict(cycle=cycle, reason=data["interface_error"]))
            if obs and obs["information_class"] == "observed":
                prediction = next(p for p in state["predicted_consequences"] if p["id"] in obs["prediction_references"])
                result["comparisons"].append(dict(cycle=cycle, prediction=prediction["statement"],
                                                  observation=obs["statement"], mismatch_detected=obs["outcome"] == "deviated"))
        if name == "model_revised":
            result["revisions"].append(dict(cycle=cycle, **data["revision"]))
    result["resources"] = dict(model_calls=state["control"]["resource_limits"][0]["used"],
                               actions_taken=len(environment.calls), memory_operations=memory.operations,
                               reflection_steps=sum(e["event"] in {"pre_action_reflection", "post_action_reflection"} for e in events),
                               cycles=sum(e["event"] == "cycle_started" for e in events), state_transitions=len(events))
    result["termination_reason"] = state["control"]["stop_reason"] or "task_complete"
    result["runtime_failed"] = state["status"] == "failed"
    return result
