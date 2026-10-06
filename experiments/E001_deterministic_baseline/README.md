# E001 — Deterministic baseline and ablations

Benchmark/task/protocol version: **0.1.0**. Approved Phase-3 baseline: `191cf62b5d508dad66b8be30ae813ae3a6e1a7b9`. Specification and executable definitions are frozen in a separate commit before execution. The generated `raw/manifest.json` records that exact commit and the protocol-lock hash.

- [Hypotheses](hypothesis.md)
- [Protocol](protocol.md)
- [Configuration](config/experiment.json)
- `config/protocol-lock.json`: pre-execution content hashes
- `raw/results.jsonl`: generated individual trials
- `raw/traces/`: generated behavior and C1 reference traces
- `raw/manifest.json`: versions, inventory and content hashes
- `analysis/summary.json` and `analysis/report.md`: generated only from raw rows
- `analysis/interpretation.md`: post-execution interpretation, explicitly separate from raw measurements

[Installation, tests, execution and reproduction instructions](../../benchmarks/README.md). Six executable conditions × 24 fixed tasks = 144 trials. A second independent run tests byte-for-byte reproducibility, not statistical significance. Three structurally blocked ablations are documented and not executed.

No experimental outcome is specified in this pre-execution README. Failures, neutral outcomes and losses are retained. Resource consumption is measured but not exactly equalized; differences cannot by themselves establish a resource-controlled mechanism effect. No conclusion about phenomenal consciousness follows from this experiment.
