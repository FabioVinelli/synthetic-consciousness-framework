# E001 descriptive results

Generated exclusively from raw/results.jsonl. Deterministic variants are not independent samples.

| Condition | Success / trials | Decisions | Actions | Memory calls | Reflection hooks | Cycles | Transitions |
|---|---:|---:|---:|---:|---:|---:|---:|
| B0 | 14 / 24 | 82 | 18 | 0 | 0 | 32 | 164 |
| B1 | 20 / 24 | 92 | 24 | 56 | 0 | 34 | 240 |
| C1-full | 18 / 24 | 150 | 22 | 358 | 60 | 32 | 588 |
| C1-no-memory-continuity | 14 / 24 | 146 | 18 | 0 | 60 | 32 | 584 |
| C1-no-reflection-revision | 18 / 24 | 150 | 22 | 358 | 30 | 32 | 578 |
| C1-no-self-model | 18 / 24 | 118 | 22 | 322 | 60 | 32 | 588 |

Equal ceilings do not imply equal consumed resources. Ratios and signed differences are in summary.json. Zero denominators are null, not infinite efficiency.

Exact-statement comparisons and preservation of two conflicting reports are not semantic entailment or general contradiction reasoning.

See protocol.md for predeclared interpretation and non-support conditions. No statistical significance or phenomenal-consciousness claim follows from these counts.
