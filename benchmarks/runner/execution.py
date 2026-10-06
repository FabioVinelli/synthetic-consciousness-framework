"""Experiment orchestration; task policy cannot access the scoring oracle."""
from copy import deepcopy
from hashlib import sha256
import json

from ..conditions import baselines
from ..conditions.common import BUDGET, Environment, new_behavior
from ..metrics.scoring import score
from ..tasks.catalog import public_task

CONDITIONS = ("B0", "B1", "C1-full", "C1-no-self-model", "C1-no-memory-continuity", "C1-no-reflection-revision")
BENCHMARK_VERSION = "0.1.0"
APPROVED_RUNTIME = "191cf62b5d508dad66b8be30ae813ae3a6e1a7b9"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n"


def digest(value):
    return sha256(canonical(value).encode()).hexdigest()


def run_trial(task, condition, *, experiment_id="PILOT", seed=0):
    if condition not in CONDITIONS or seed != 0:
        raise ValueError("Unknown condition or unsupported seed")
    identifier = experiment_id + ":" + condition + ":" + task["task_id"] + ":0"
    environment = Environment(deepcopy(task["environment"]))
    public = public_task(task)
    try:
        if condition in {"B0", "B1"}:
            behavior = baselines.execute(public, environment, agentic=condition == "B1")
        else:
            from ..conditions.cafh_condition import execute
            behavior = execute(public, environment, ablation=condition.removeprefix("C1-"), run_id=identifier)
    except Exception as exc:
        # Infrastructure exceptions are retained, never turned into abstention success.
        behavior = new_behavior()
        behavior["runtime_failed"] = True
        behavior["resource_accounting_complete"] = False
        behavior["termination_reason"] = "benchmark_error:" + type(exc).__name__ + ":" + str(exc)
        behavior["failures"].append(dict(cycle=0, reason=behavior["termination_reason"]))
        behavior["resources"]["actions_taken"] = len(environment.calls)
        behavior["actions"] = [dict(cycle=i+1, **a) for i,a in enumerate(environment.calls)]
    if any(behavior["resources"][k] > cap for k, cap in BUDGET.items()):
        behavior["runtime_failed"] = True
        behavior["termination_reason"] = "resource_limit_exceeded"
    for event in behavior["trace"]:
        event.setdefault("run_id", identifier)
    row = dict(experiment_id=experiment_id, condition=condition, ablation=condition.removeprefix("C1-") if condition.startswith("C1-") else "none",
               task_family=task["task_family"], task_id=task["task_id"], trial_id=identifier, seed=seed,
               task_version=task["task_version"], benchmark_version=BENCHMARK_VERSION,
               approved_runtime_commit=APPROVED_RUNTIME, task_digest=digest(task), public_context_digest=digest(task["public"]),
               environment_digest=digest(task["environment"]), configuration=dict(budget=BUDGET, condition=condition),
               trace_file="traces/" + condition + "-" + task["task_id"] + ".json",
               trace_sha256=digest(behavior), **score(task, behavior))
    return row, behavior
