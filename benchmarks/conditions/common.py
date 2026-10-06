"""Shared deterministic decision primitives and isolated mock environment.

No CAFH imports: B0 and B1 execute without the CAFH state/schema machinery.
"""
from copy import deepcopy

BUDGET = {"cycles": 3, "model_calls": 15, "actions_taken": 3,
          "state_transitions": 90, "memory_operations": 2000, "reflection_steps": 6}


def choose(public, step, memory):
    mode = step["mode"]
    if mode == "missing":
        return []
    if mode == "recall":
        tokens = [x for x in memory if x.startswith("token:")]
        return [{"name": "answer", "argument": tokens[-1]}] if tokens else []
    if mode == "goal":
        return [{"name": "emit", "argument": public.objective}]
    return sorted(deepcopy(step["candidates"]), key=lambda x: (x["name"], x["argument"]))


class Environment:
    def __init__(self, definition):
        self._tokens = list(definition["tokens"])
        self._read = 0
        self.calls = []

    def execute(self, name, argument):
        self.calls.append({"name": name, "argument": argument})
        if len(self.calls) > BUDGET["actions_taken"]:
            raise RuntimeError("action_limit")
        if name == "attempt":
            raise RuntimeError("deterministic_interface_failure")
        if name == "read":
            if self._read >= len(self._tokens):
                raise RuntimeError("missing_environment_record")
            result = self._tokens[self._read]
            self._read += 1
            return result
        if name in {"emit", "answer", "fallback"}:
            return argument if name == "emit" else "ack"
        raise RuntimeError("unknown_action")


def new_behavior():
    return dict(actions=[], abstentions=[], reports=[], claims=[], comparisons=[],
                revisions=[], memories_used=[], failures=[], trace=[], resources={k: 0 for k in BUDGET},
                termination_reason="task_complete", runtime_failed=False, resource_accounting_complete=True)


def emit(behavior, cycle, event, **data):
    trace = behavior["trace"]
    trace.append(dict(sequence=len(trace), cycle=cycle, stage=event, event=event,
                      record_references=[], data=deepcopy(data)))
    behavior["resources"]["state_transitions"] += 1
