"""Deterministic synthetic proposals and an isolated local echo environment."""

from .base import ActionInterface, ActionResult, Candidate, ModelAdapter
from ..runtime.state import record


class MockAdapter(ModelAdapter):
    def __init__(self, prediction="echo: expected", argument="actual"):
        self.prediction, self.argument = prediction, argument

    def propose(self, stage, state):
        n = state["control"]["cycles_completed"] + 1
        prefix = f"{state['run_id']}:c{n}"
        if stage == "WORLD MODEL":
            return [record(prefix + ":world", "The input is a report, not an independently verified world fact")]
        if stage == "SELF MODEL":
            return [record(prefix + ":self", "I can propose an echo action; its outcome remains to be observed")]
        if stage == "INTERPRETATIONS":
            return [record(prefix + ":unknown", "The next action outcome is not yet observed", "unknown")]
        raise ValueError("Unsupported mock proposal stage")

    def candidates(self, state):
        return [Candidate("echo", self.argument)]

    def predict(self, candidate, state):
        n = state["control"]["cycles_completed"] + 1
        # A prior observation may inform a new hypothesis, never guarantee it.
        remembered = [r for r in state["beliefs"] if r["information_class"] == "remembered"
                      and any(p["source_information_class"] == "observed" for p in r["provenance"])]
        expected = remembered[-1]["statement"] if remembered else self.prediction
        return record(f"c{n}:prediction", expected, "hypothesized")


class MockEnvironment(ActionInterface):
    def __init__(self):
        self.calls = []

    def execute(self, candidate):
        if candidate.name != "echo":
            raise ValueError("Unknown mock action")
        self.calls.append(candidate)
        return ActionResult("echo: " + candidate.argument)
