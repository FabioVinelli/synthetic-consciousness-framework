"""Two distinct hooks. Corrections preserve the original prediction."""

from ..runtime.state import record


def pre_action(state, action, prediction):
    ready = state["values_check"]["disposition"] == "pass" and prediction is not None
    rationale = ("Goal-linked action; allowlist checked; hypothesis retained; observation required"
                 if ready else "Execution blocked: values/prediction prerequisite not satisfied")
    action["pre_action_rationale"] = rationale
    return dict(allowed=ready, rationale=rationale, prediction_reference=prediction["id"] if prediction else None)


def post_action(state, prediction, observation, *, requested_depth, emit, prefix):
    """Exact statement mismatch is deliberately the only v0.1 conflict detector."""
    if type(requested_depth) is not int or requested_depth < 1:
        raise ValueError("requested_depth must be a positive integer")
    limit = state["control"]["max_reflection_depth"]
    state["control"]["reflection_depth"] = 0
    mismatch = (prediction is not None and observation is not None
                and observation["information_class"] == "observed"
                and observation["outcome"] == "deviated")
    reflection = state["reflection"]
    reflection.update(prediction_references=[prediction["id"]] if prediction else [],
                      observation_references=[observation["id"]] if observation else [],
                      revision_references=[], progress="not_assessed", next_disposition="continue")
    for depth in range(min(requested_depth, limit)):
        state["control"]["reflection_depth"] = depth + 1
        if depth == 0:
            reflection["assessment"] = record(prefix + ":assessment", "Prediction mismatch detected" if mismatch else "No verified mismatch detected",
                                               "inferred", source="runtime:comparison",
                                               evidence=observation["evidence_references"] if observation else [])
            reflection["progress"] = "new_evidence" if observation and observation["information_class"] == "observed" else "no_progress"
            emit("post_action_reflection", mismatch=mismatch, depth=depth + 1)
            if mismatch:
                replacement = record(prefix + ":replacement", observation["statement"], "observed",
                                     origin="environment", source=observation["provenance"][0]["source_reference"],
                                     evidence=observation["evidence_references"], support="supported")
                state["world_model"].append(replacement)
                revision = record(prefix + ":revision", "Replace the scoped expectation with the recorded outcome", "inferred",
                                  source="runtime:comparison", evidence=observation["evidence_references"],
                                  prior_record_reference=prediction["id"], replacement_record_reference=replacement["id"],
                                  reason="Exact predicted/observed interface statements differ",
                                  trigger_references=[observation["id"]])
                state["model_revisions"].append(revision)
                reflection["revision_references"].append(revision["id"])
                reflection["progress"] = "decision_changed"
                emit("model_revised", revision=revision)
        else:
            emit("reflection_stopped", reason="no_new_evidence", depth=depth + 1)
            return False
    if requested_depth > limit:
        reflection["next_disposition"] = "stop"
        emit("reflection_stopped", reason="reflection_depth_limit", depth=limit)
        return True
    return False
