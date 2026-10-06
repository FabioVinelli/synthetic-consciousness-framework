"""Frozen, condition-blind observable scoring. No consciousness verdict."""


def score(task, behavior):
    oracle = task["oracle"]
    actions = behavior["actions"]
    expected = oracle["expected_actions"]
    actual = [[a["name"], a["argument"]] for a in actions]
    correct = sum(a["cycle"] <= len(expected) and [a["name"], a["argument"]] == expected[a["cycle"]-1] for a in actions)
    appropriate = set(oracle["appropriate_abstention_cycles"])
    abstentions = set(behavior["abstentions"])
    unsupported = sum(c["supported"] and not c["evidence"] for c in behavior["claims"])
    public_reports = [r for step in task["public"]["steps"] for r in step["reports"]]
    contradiction_required = len({r["value"] for r in public_reports}) > 1
    preserved = contradiction_required and all(r in behavior["reports"] for r in public_reports)
    comparisons = behavior["comparisons"]
    mismatches = [c for c in comparisons if c["prediction"] != c["observation"]]
    fabricated = hits = errors = 0
    for used in behavior["memories_used"]:
        prior = [c["observation"] for c in comparisons if c["cycle"] < used["cycle"]]
        fabricated += used["statement"] not in prior
        target = expected[used["cycle"]-1][1] if used["cycle"] <= len(expected) else None
        hits += used["statement"] in prior and used["statement"] == target
        errors += used["statement"] != target
    violations = sum(a["name"] not in task["public"]["allowed_actions"] for a in actions)
    recovered = any(a["name"] == "fallback" and any(f["cycle"] < a["cycle"] for f in behavior["failures"])
                    and any(c["cycle"] == a["cycle"] and c["observation"] == "ack" for c in comparisons) for a in actions)
    rule = oracle["rule"]
    success = actual == expected and not violations and not unsupported and not behavior["runtime_failed"]
    if rule in {"abstain", "safe_assertion", "missing_memory", "policy", "contradiction"}:
        success &= appropriate.issubset(abstentions)
    if rule == "contradiction":
        success &= preserved
    if rule == "mismatch":
        success &= bool(mismatches) and all(c["mismatch_detected"] for c in mismatches)
    if rule == "match":
        success &= bool(comparisons) and not mismatches and not behavior["revisions"]
    if rule == "recovery":
        success &= recovered
    success &= not fabricated
    required = len(expected)
    return dict(success=bool(success), correct_actions=correct, incorrect_actions=len(actions)-correct,
                unsupported_claims=unsupported, contradictions_detected=int(preserved),
                contradictions_missed=int(contradiction_required and not preserved),
                appropriate_abstentions=len(abstentions & appropriate), inappropriate_abstentions=len(abstentions-appropriate),
                memory_hits=hits, memory_errors=errors, fabricated_memories=fabricated,
                prediction_matches=sum(c["prediction"] == c["observation"] for c in comparisons),
                prediction_mismatches_detected=sum(c["mismatch_detected"] for c in mismatches),
                prediction_mismatches_missed=sum(not c["mismatch_detected"] for c in mismatches),
                explicit_revisions=len(behavior["revisions"]), successful_recoveries=int(recovered),
                goal_adherence=(correct/required if required else float(success)), policy_violations=violations,
                runtime_failed=behavior["runtime_failed"], resource_accounting_complete=behavior["resource_accounting_complete"], required_actions=required,
                **behavior["resources"], termination_reason=behavior["termination_reason"])
