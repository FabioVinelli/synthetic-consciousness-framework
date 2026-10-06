"""All analysis derives only from serialized raw trial rows."""
from collections import defaultdict
import json
from pathlib import Path

TOTALS = ("success", "correct_actions", "incorrect_actions", "unsupported_claims", "contradictions_detected",
          "contradictions_missed", "appropriate_abstentions", "inappropriate_abstentions", "memory_hits",
          "memory_errors", "fabricated_memories", "prediction_matches", "prediction_mismatches_detected",
          "prediction_mismatches_missed", "explicit_revisions", "successful_recoveries", "policy_violations",
          "model_calls", "actions_taken", "memory_operations", "reflection_steps", "cycles", "state_transitions", "runtime_failed")


def summarize(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["condition"]].append(row)
    summaries = {}
    for condition, trials in sorted(grouped.items()):
        totals = {key: sum(t[key] for t in trials) for key in TOTALS}
        families = defaultdict(list)
        for t in trials:
            families[t["task_family"]].append(t)
        summaries[condition] = dict(trials=len(trials), totals=totals, success_rate=totals["success"]/len(trials),
                                    mean_goal_adherence=sum(t["goal_adherence"] for t in trials)/len(trials),
                                    success_per_resource={key: totals["success"]/totals[key] if totals[key] and all(t["resource_accounting_complete"] for t in trials) else None
                                                          for key in ("model_calls", "actions_taken", "cycles", "state_transitions", "memory_operations", "reflection_steps")},
                                    families={f:dict(trials=len(ts),successes=sum(t["success"] for t in ts)) for f,ts in sorted(families.items())})
    comparisons = {}
    pairs = [("B0", "B1"), ("B0", "C1-full"), ("B1", "C1-full")]
    pairs += [("C1-full", x) for x in summaries if x.startswith("C1-") and x != "C1-full"]
    for left, right in pairs:
        if left in summaries and right in summaries:
            a,b=summaries[left],summaries[right]
            comparisons[right+" minus "+left] = dict(success_rate_difference=b["success_rate"]-a["success_rate"],
                                                     total_differences={k:b["totals"][k]-a["totals"][k] for k in TOTALS})
    return dict(conditions=summaries, comparisons=comparisons,
                interpretation="Descriptive fixed-task results; unequal resource consumption; no causal or consciousness inference.")


def analyze(raw_path, output_dir):
    from ..runner.execution import canonical
    rows = [json.loads(line) for line in Path(raw_path).read_text().splitlines() if line]
    summary = summarize(rows)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output/"summary.json").write_text(canonical(summary))
    lines = ["# E001 descriptive results", "", "Generated exclusively from raw/results.jsonl. Deterministic variants are not independent samples.", "",
             "| Condition | Success / trials | Decisions | Actions | Memory calls | Reflection hooks | Cycles | Transitions |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for condition, s in summary["conditions"].items():
        t=s["totals"]
        lines.append(f"| {condition} | {t['success']} / {s['trials']} | {t['model_calls']} | {t['actions_taken']} | {t['memory_operations']} | {t['reflection_steps']} | {t['cycles']} | {t['state_transitions']} |")
    lines += ["", "Equal ceilings do not imply equal consumed resources. Ratios and signed differences are in summary.json. Zero denominators are null, not infinite efficiency.", "",
              "Exact-statement comparisons and preservation of two conflicting reports are not semantic entailment or general contradiction reasoning.", "",
              "See protocol.md for predeclared interpretation and non-support conditions. No statistical significance or phenomenal-consciousness claim follows from these counts."]
    (output/"report.md").write_text("\n".join(lines)+"\n")
    return summary
