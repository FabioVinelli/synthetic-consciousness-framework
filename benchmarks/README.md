# Deterministic benchmark v0.1

This is a symbolic experimental apparatus, not evidence of phenomenal consciousness or a real-model benchmark. Read the [frozen protocol](protocol.md), especially its exact-statement and resource-comparability limitations.

From a repository checkout with Python 3.11+:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python -m examples.minimal_agent
```

The E001 [experiment README](../experiments/E001_deterministic_baseline/README.md) identifies the frozen commit through its raw manifest. On a checkout containing the committed experiment:

```bash
FROZEN_COMMIT=$(python -c 'import json; print(json.load(open("experiments/E001_deterministic_baseline/raw/manifest.json"))["protocol_commit"])')
python -m benchmarks.runner run --protocol-commit "$FROZEN_COMMIT" --output /tmp/cafh-e001-reproduction
python -m benchmarks.runner verify experiments/E001_deterministic_baseline/raw /tmp/cafh-e001-reproduction
python -m benchmarks.runner analyze --raw experiments/E001_deterministic_baseline/raw/results.jsonl --output /tmp/cafh-e001-analysis
```

Use new empty output directories: raw overwrite is rejected. Raw manifests include dependency versions, so exact manifest equality requires the recorded environment (Python 3.12.14, jsonschema 4.26.0, rfc3339-validator 0.1.4, pytest 9.1.1 for the initial environment). On a different environment, compare results/traces separately and investigate any differences; do not discard metadata differences. Installation requires package access; execution requires no credentials or network.

Sources: [task catalog](tasks/v0_1.json), independent [B0/B1](conditions/baselines.py), [C1 binding and ablations](conditions/cafh_condition.py), [condition-blind scoring](metrics/scoring.py), [raw-only aggregation](metrics/aggregate.py), [runner](runner/__main__.py). B0/B1 do not import CAFH. The C1 binding uses the approved Engine with default-preserving feature controls.

To define a later experiment, create a new version and protocol before generating its results. Do not reuse E001 as a mutable tuning set. Freeze hashes can be verified using `benchmarks.runner.__main__.verify_lock(Path.cwd())`; they are checked automatically by `run`.
