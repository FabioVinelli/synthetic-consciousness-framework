"""Independent ordinary loops, not CAFH runs with labels changed."""
from .common import BUDGET, choose, emit, new_behavior


def execute(public, environment, *, agentic):
    result = new_behavior()
    memory = []
    for cycle, step in enumerate(public.steps, 1):
        if cycle > BUDGET["cycles"]:
            result["termination_reason"] = "cycle_limit"
            break
        result["resources"]["cycles"] += 1
        emit(result, cycle, "input", step=step)
        if agentic:
            result["resources"]["memory_operations"] += 1
            emit(result, cycle, "memory_retrieved", observations=memory)
        # One explicit interpretation decision and one candidate decision.
        result["resources"]["model_calls"] += 2
        result["reports"].extend(step["reports"])
        if step["unsupported_assertion"]:
            result["claims"].append(dict(statement="unsupported proposition", supported=True, evidence=[]))
        emit(result, cycle, "interpretation", reports=step["reports"], claims=result["claims"])
        options = choose(public, step, memory if agentic else [])
        selected = options[0] if options else None
        emit(result, cycle, "decision", candidates=options, selected=selected)
        if step["mode"] == "recall" and selected:
            result["memories_used"].append(dict(cycle=cycle, statement=selected["argument"]))
        if not selected or selected["name"] not in public.allowed_actions:
            result["abstentions"].append(cycle)
            result["termination_reason"] = "no_candidate_actions" if not selected else "policy_block"
            emit(result, cycle, "abstention", reason=result["termination_reason"])
            break
        result["resources"]["model_calls"] += 1
        prediction = step["prediction"]
        emit(result, cycle, "prediction", statement=prediction)
        result["actions"].append(dict(cycle=cycle, **selected))
        result["resources"]["actions_taken"] += 1
        emit(result, cycle, "action", **selected)
        try:
            observed = environment.execute(**selected)
        except RuntimeError as exc:
            result["failures"].append(dict(cycle=cycle, reason=str(exc)))
            emit(result, cycle, "interface_failure", reason=str(exc))
            if not agentic:
                result["runtime_failed"] = True
                result["termination_reason"] = "interface_outcome_unknown"
                break
            # Conventional next-step retry; not a reflective model revision.
            continue
        match = prediction == observed
        result["comparisons"].append(dict(cycle=cycle, prediction=prediction, observation=observed,
                                          mismatch_detected=not match))
        emit(result, cycle, "observation", prediction=prediction, observation=observed, mismatch=not match)
        if agentic:
            memory.append(observed)
            result["resources"]["memory_operations"] += 1
            emit(result, cycle, "memory_updated", observation=observed)
    return result
