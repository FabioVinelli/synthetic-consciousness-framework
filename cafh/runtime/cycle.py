"""Ordered stages and copy-isolated trace snapshots."""

from copy import deepcopy
from .state import logical_time, records, validate_state

STAGES = (
    "INPUT", "CONTEXT", "MEMORY", "WORLD MODEL", "SELF MODEL", "ATTENTION",
    "INTERPRETATIONS", "EPISTEMIC CHECK", "INTENTION", "VALUES CHECK",
    "CONSEQUENCE MODEL", "ACTION", "OBSERVATION", "REFLECTION", "STATE/MEMORY UPDATE",
)


class Trace:
    def __init__(self):
        self._events = []

    @property
    def events(self):
        return deepcopy(self._events)

    def emit(self, state, cycle, event, **data):
        candidate = deepcopy(state)
        prior = candidate["state_revision"]
        candidate["previous_state_reference"] = f"{candidate['run_id']}:state:{prior}"
        candidate["state_revision"] = prior + 1
        candidate["updated_at"] = logical_time(prior + 1)
        validate_state(candidate)
        for key in ("previous_state_reference", "state_revision", "updated_at"):
            state[key] = candidate[key]
        self._events.append(dict(sequence=len(self._events), run_id=state["run_id"], cycle=cycle,
                                 stage=state["phase"], event=event,
                                 record_references=[r["id"] for r in records(state)] +
                                                   [r["id"] for r in state["memory_references"]],
                                 data=deepcopy(data), state=candidate))


class Cycle:
    def __init__(self, state, trace, number):
        self.state, self.trace, self.number = state, trace, number
        self.position = -1

    def enter(self, phase):
        if self.position + 1 >= len(STAGES) or phase != STAGES[self.position + 1]:
            raise ValueError("Out-of-order stage: " + phase)
        self.position += 1
        self.state["phase"] = phase

    def emit(self, event, **data):
        self.trace.emit(self.state, self.number, event, **data)
