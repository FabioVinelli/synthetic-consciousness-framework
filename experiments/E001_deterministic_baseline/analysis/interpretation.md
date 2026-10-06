# E001 post-execution interpretation

Status: post-execution interpretation for deterministic benchmark v0.1.0. This document is downstream of the immutable raw results and generated descriptive analysis. It does not alter the frozen protocol, tasks, scoring rules, or raw artifacts.

## Reproducibility and validity checks

- Frozen protocol commit: `1a9a159da042df09f63da795725d7ba7ea772d04`.
- Phase-3 approved runtime: `191cf62b5d508dad66b8be30ae813ae3a6e1a7b9`.
- 144 trials executed: 24 fixed tasks across 6 executable conditions.
- Two independent executions produced identical manifests, results, and trace inventories.
- Canonical `results.jsonl` SHA-256: `85ac72962f8803b64baee180cd71de8e66a9e7055d5df4b36117ce73dd3640fc`.
- Manifest SHA-256 for each independent run: `cf882a818ed3f78abf4b6570ee48a3ca6e3624f9eb5f00ab8ee1843a9c2090ea`.
- Protocol-lock SHA-256: `feabf20264960b8b57974cd7a23f5f7d75f21cde0f1594b140273ff3fd55cfcf`.
- Full repository suite passed before and after execution: 138 tests.
- Execution environment: Python 3.12.14, jsonschema 4.26.0, rfc3339-validator 0.1.4, pytest 9.1.1.

## Primary results

| Condition | Success | Rate | Model/decision calls | Actions | Memory ops | Reflection hooks | Runtime failures |
|---|---:|---:|---:|---:|---:|---:|---:|
| B0 | 14 / 24 | 58.3% | 82 | 18 | 0 | 0 | 2 |
| B1 | 20 / 24 | 83.3% | 92 | 24 | 56 | 0 | 0 |
| C1-full | 18 / 24 | 75.0% | 150 | 22 | 358 | 60 | 4 |
| C1-no-memory-continuity | 14 / 24 | 58.3% | 146 | 18 | 0 | 60 | 4 |
| C1-no-reflection-revision | 18 / 24 | 75.0% | 150 | 22 | 358 | 30 | 4 |
| C1-no-self-model | 18 / 24 | 75.0% | 118 | 22 | 322 | 60 | 4 |

The strongest overall condition was the conventional B1 baseline: 20/24 successes versus 18/24 for C1-full and 14/24 for B0.

C1-full improved on B0 by 4 successful trials, eliminated the two unsupported promotions observed in B0, and recovered legitimate continuity on T6/T8. It did so with substantially greater measured resource consumption: +68 model/decision calls, +358 memory operations, +60 reflection hooks, and +424 structured transitions relative to B0.

C1-full underperformed B1 by 2 successful trials while consuming +58 model/decision calls, +302 memory operations, +60 reflection hooks, and +348 transitions. B1 also completed the T11 recovery family, whereas C1-full preserved the Phase-3 terminal interface-failure behavior and did not recover.

These are descriptive fixed-task results. Equal resource ceilings are not actual compute equalization, so the observed differences do not establish resource-controlled causal superiority of any architecture.

## Ablation findings

### Memory continuity

Removing CAFH memory continuity reduced success from 18/24 to 14/24, removed all 4 memory hits, introduced 4 inappropriate abstentions, and specifically removed success on T6 and T8. Fabricated memories remained zero.

This is the clearest mechanism-sensitive result in E001. It supports the claim that continuity matters for these fixed cross-cycle tasks, but does not establish that CAFH's memory design is uniquely necessary: B1's ordinary memory also solved these tasks and achieved higher aggregate performance.

### Self-model

Removing the self-model produced no change in task success, goal adherence, unsupported claims, memory hits, mismatch handling, or runtime failures. It reduced model/decision calls from 150 to 118 and memory operations from 358 to 322.

E001 therefore provides no behavioral support for the self-model on this suite. The neutral result is bounded by the protocol's deliberately small symbolic policy, which does not heavily consume self-description.

### Reflection revision

Removing post-action reflection/revision produced no change in success or the other scored behavioral outcomes. Explicit revisions fell from 10 to 0, reflection-hook count fell from 60 to 30 because pre-action reflection remains, and transitions fell from 588 to 578.

E001 therefore does not support a behavioral benefit from post-action reflection/revision on these tasks. More revision records in C1-full did not translate into improved recovery.

### Structurally unavailable ablations

The following were not executed and must not be assigned zero performance:

- `C1-no-epistemic-monitor`
- `C1-no-consequence-model`
- `C1-no-intentionality`

Their dependencies remain inseparable from the v0.1 runtime contracts, so isolated causal claims about those mechanisms remain unavailable.

## Predeclared hypothesis assessment

### H1 — SUPPORTED ON E001

Measurable behavioral differences occurred among B0, B1, C1-full, and the memory ablation. This satisfies the predeclared descriptive E001 observation that the mechanisms may produce differences, not necessarily improvements.

This does **not** establish that CAFH is superior. B1 outperformed C1-full overall, and consumed resources were unequal.

### H1-E — SUPPORTED ON E001, attribution limited

C1-full recorded zero unsupported promotions versus two each for B0 and B1. However, T3 remained unsuccessful for C1-full because the runtime rejected the unsupported assertion via failure rather than completing the task successfully.

Because the epistemic-monitor ablation is structurally unavailable, E001 cannot isolate the monitor as the causal component.

### H1-M — SUPPORTED ON E001

C1-full solved the T6/T8 continuity tasks and recorded 4 legitimate memory hits with zero fabricated memories. Removing memory continuity reduced those hits to zero and removed four successes, while fabricated memories remained zero.

B1 also solved the continuity tasks with ordinary memory, so the result supports continuity as useful here rather than CAFH memory as uniquely superior.

### H1-R — NOT SUPPORTED ON E001

C1-full and the no-reflection-revision condition had identical success rates. C1-full emitted 10 explicit revisions but did not improve T11 recovery; B1 recovered successfully instead.

The fixed suite therefore provides no behavioral support for the predeclared reflection/recovery hypothesis.

### H1-I — NOT SUPPORTED ON E001

C1-full did not outperform B0 or B1 on T9 goal persistence; all three achieved the same task-family success. The intentionality ablation is unavailable, so isolated causal attribution is also impossible.

### H1-C — NOT SUPPORTED ON E001

Mismatch detection was not better in C1-full than the baselines under the benchmark's exact comparison rule. The consequence-model ablation is unavailable, preventing isolated causal attribution.

## Scientific interpretation

E001 does not show a general CAFH advantage. It shows a mixed architecture result:

1. persistent continuity materially helps the tasks that require legitimate cross-cycle information;
2. conventional B1 memory/recovery is sufficient to outperform C1-full overall on this deterministic suite;
3. the self-model and post-action revision mechanisms create measurable overhead without task-success gains here;
4. the CAFH epistemic boundary prevents unsupported promotion in T3, but by failing closed rather than completing the task;
5. C1's approved Phase-3 interface-failure semantics hurt T11 recovery relative to B1;
6. T12 remains unsolved across all conditions, showing the suite contains a common failure that does not privilege CAFH.

The correct next scientific move is not to optimize CAFH against E001. E001 must remain frozen as the first benchmark. Any richer policies, cost-equalized designs, cleanly separable mechanisms, stochastic/model-provider trials, or revised recovery semantics belong in a separately versioned future experiment.

## Limitations

- deterministic symbolic benchmark only;
- no external or real LLM providers;
- no inferential statistics from repeated deterministic runs;
- exact-statement/scoped-evidence checks are not general semantic entailment;
- explicit opposing-report preservation is not general contradiction understanding;
- resource ceilings do not equalize actual computation;
- three mechanism ablations are structurally unavailable;
- the policy primitives deliberately underuse some CAFH state;
- the benchmark does not measure phenomenal consciousness, sentience, qualia, or subjective experience.

No benchmark defect or nondeterminism was observed during E001 execution. This does not constitute external validation of the benchmark.
