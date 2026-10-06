# E001 protocol binding

E001 binds to [Deterministic Benchmark Protocol v0.1.0](../../benchmarks/protocol.md), the [fixed task catalog](../../benchmarks/tasks/v0_1.json), [scoring implementation](../../benchmarks/metrics/scoring.py), and [configuration](config/experiment.json).

Freeze these files, runtime/benchmark sources, schema and tests using `config/protocol-lock.json`, then commit before running E001. The raw manifest names the frozen commit. Development tests use PILOT IDs. No post-E001 scoring/hypothesis changes are allowed within this version.

All 24 tasks execute for each of B0, B1, C1-full, C1-no-self-model, C1-no-memory-continuity and C1-no-reflection-revision. Ordering is fixed by `runner.execution.CONDITIONS`, then catalog order. Each trial gets a fresh environment and memory; continuity exists only between that trial's cycles. Seed is fixed to 0. No repeated-trial statistical sample is implied.

Any discovered post-execution defect must be identified in analysis, with affected metrics and scope, and corrected only in a separately versioned experiment. Do not hand-edit raw artifacts.
