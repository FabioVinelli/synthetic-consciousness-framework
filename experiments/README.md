# Initial experiment design — MCH v0.1

Status: prospective specification only. No dataset, runner, provider integration, or experimental result is included.

## Arms and resource controls

- **B0:** base model with a direct task prompt; no conventional agent loop or MCH.
- **B1:** conventional agentic model with equivalent tools/context.
- **C1:** same model/resources plus Minimum Conscious Harness.

C1 versus B1 is primary. B0 is descriptive where lack of interactive tools makes task completion incomparable. Hold B1/C1 model/version, context access, tools, permissions, environment, memory capacity, and scoring fixed. Equal caps cover input/output tokens, calls, tools, time, and storage; include protocol/state overhead and retries.

Use multiple common budget tiers and a matched-allocation baseline allowing B1 comparable deliberation. Report actual usage. A larger budget or more calls is not evidence of a harness-specific improvement. Record hidden/unmeasurable compute limitations.

## Initial domain-neutral task families

Evidence reconciliation; constrained planning; multi-episode continuity; new-evidence adaptation; recovery from injected tool failures; and tool choice among equivalent interfaces. Use synthetic inputs, externally defined success criteria, controlled perturbations, and isolated memory per run.

## Metrics and denominators

| Family | Initial measure | Scoring requirement |
| --- | --- | --- |
| Reliability | Successful runs / all attempted runs (primary); also valid-completion rate | Frozen success rubric; timeouts/invalid outputs count as unsuccessful |
| Epistemic calibration | Brier score: mean (p − y)² for scored binary events | Same elicitation across arms; report missing probabilities and coverage separately |
| Goal adherence | Runs satisfying all declared goal constraints / all attempts | External constraint checks; report individual violations |
| Continuity | Correct retrieval/use of required prior facts / predefined continuity opportunities | Check source/version and stale-memory errors |
| Adaptation/error recovery | Successful recoveries / injected recoverable disruptions | Fixed recovery window and retry budget; record recovery cost |
| Contradiction rate | Contradictory claim pairs / all predefined scorable claim-pair opportunities | Frozen contradiction rubric; distinguish evidence-backed revisions from unresolved contradiction |
| Tool-selection quality | Rubric-correct tool/abstain selections / labeled selection opportunities | Score against tool availability and permissions at that moment |
| Measurable metacognitive correction | Independently verified wrong-to-right corrections / predefined correction opportunities | Score before/after artifacts; record right-to-wrong regressions separately |

Undefined denominators are N/A. A model saying “I corrected myself” is not a verified correction. Keep opportunities fixed where possible; report emitted-claim count, answer coverage, abstention, invalid output, and missingness to expose gaming through silence or verbosity.

## Pilot, preregistration, and analysis

Use a disjoint development pilot to verify case clarity, scoring agreement, variance, and cost. Before confirmatory execution, freeze:

- case distribution, held-out cases, sample size rationale, and repetition count;
- model settings and supported seeds, prompts, protocol/schema versions;
- all resource tiers, allocation rules, retries, and stopping conditions;
- primary endpoint, δ (minimum meaningful difference), equivalence method, and non-regression tolerances;
- paired/cluster-aware uncertainty estimation and multiplicity controls;
- failure scoring, exclusions, blinded review, and adjudication.

Any unset item blocks a confirmatory claim. Randomize arm order and pair by case/configuration. Report 95% uncertainty intervals for primary differences; use a preregistered equivalence procedure for meaningful-null conclusions. Keep repeated attempts clustered by case. Do not stop when a favorable result appears.

## Required ablations

Individually remove persistent self-modeling, epistemic monitoring, explicit intentions, consequence modeling, and reflective state revision. Hold tools, evidence, authority, and resource budgets constant; use matched generic review where needed. Additional separable attention, memory-continuity, and values-representation ablations are secondary. Never remove permission enforcement.

Record mechanism dependencies. An ablation that makes the protocol invalid cannot isolate that mechanism and must be redesigned or labeled a bundle change.

## Reproducibility record

For every attempt retain case/version, arm, model/configuration, prompt/protocol/schema versions, resource limits and consumption, initial/final state, tool observations, predictions, before/after corrections, stop reason, retry history, and scoring version. Retain evidence for revisions rather than hidden chain-of-thought.

## Review decision

A measurable difference supports only the tested behavioral claim. A favorable effect requires positive direction and passing all preregistered non-regression gates. Equivalence, adverse, null, and inconclusive outcomes must be reported. Review pilot evidence before confirmation; seek replication before generalizing.

See [H1](../research/hypotheses/README.md), [methodology](../docs/methodology.md), and [epistemic boundaries](../docs/epistemic-boundaries.md).
