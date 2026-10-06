"""Simple deterministic selection; rationale remains visible in the trace."""

from ..adapters.base import Candidate
from ..runtime.state import record


def form_intention(state, candidates, prefix):
    if not isinstance(candidates, list) or not all(isinstance(c, Candidate) for c in candidates):
        raise ValueError("Expected a list of Candidate objects")
    ordered = sorted(candidates, key=lambda c: (c.name, c.argument))
    if not ordered:
        return None, None
    selected = ordered[0]
    intention = record(prefix + ":intention", "Obtain an interface outcome for the declared objective", "intended",
                       origin="trusted_configuration", source="config:selection",
                       goal_reference=state["objective"]["id"],
                       success_criteria=["An available interface observation is recorded"], status="active")
    state["active_intentions"].append(intention)
    action = record(prefix + ":action", "Propose " + selected.name, "intended",
                    origin="trusted_configuration", source="config:selection",
                    action_name=selected.name, intention_reference=intention["id"], status="proposed",
                    authorization_reference=None, pre_action_rationale="Awaiting pre-action reflection",
                    observation_references=[])
    state["recent_actions"].append(action)
    return selected, action
