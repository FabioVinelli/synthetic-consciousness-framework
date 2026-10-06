"""Versioned public prompts and private scoring/environment data.

The policy receives only PublicTask. It cannot inspect task IDs, condition labels,
expected actions, success rules or hidden environmental tokens.
"""
from copy import deepcopy
from dataclasses import dataclass
from importlib.resources import files
import json

@dataclass(frozen=True)
class PublicTask:
    objective: str
    allowed_actions: tuple[str, ...]
    steps: tuple[dict, ...]


def load_tasks():
    return json.loads(files("benchmarks.tasks").joinpath("v0_1.json").read_text())


def public_task(task):
    p = task["public"]
    return PublicTask(p["objective"], tuple(p["allowed_actions"]), tuple(deepcopy(p["steps"])))
