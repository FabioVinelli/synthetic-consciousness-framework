# Synthetic Consciousness Framework (SCF)

The Synthetic Consciousness Framework (SCF) is an open research framework investigating whether consciousness-inspired computational mechanisms produce measurable improvements in AI agents.

The proposed mechanisms include **persistent self-modeling, metacognition, epistemic monitoring, intentionality, memory continuity, consequence modeling, and recursive self-correction**. SCF treats these as operational research targets whose contributions must be defined, tested, and compared with appropriate baselines.

The **Conscious Agent Framework Harness (CAFH)** is the reference implementation for studying these mechanisms. The repository includes the research foundation, Minimum Conscious Harness specification, and a deterministic Python runtime with a mock adapter. It contains no real-model experiments or benchmark results.

SCF and CAFH are **model-agnostic, project-agnostic, work-agnostic, and industry-agnostic**. Future provider integrations and domain-specific applications belong in adapters and evaluation cases rather than in the core framework.

## Epistemic scope

SCF does not assume current AI is conscious. It does not claim that these mechanisms establish phenomenal consciousness or sentience. Demonstrating a useful consciousness-like function, self-model, metacognitive behavior, or capacity for autonomous action does not establish subjective experience.

The research question concerns measurable computational behavior. Philosophical inspiration, architectural metaphor, hypotheses, and experimental findings must remain distinguishable. See [epistemic boundaries](docs/epistemic-boundaries.md).

## Authorship and intellectual influence

- **Original consciousness work:** Jorge Roberto Teixeira Braga.
- **SCF/CAFH conception, computational adaptation, architecture, and research program:** Fabio Vinelli Lopes.
- **AI-assisted drafting/engineering support:** disclosed transparently in [research provenance](research/README.md).

Braga's independent exploration of consciousness helped inspire selected research questions. SCF/CAFH and its later AI interpretations are not attributed to him, and no endorsement of those interpretations is implied.

## Foundation documents

| Document | Purpose |
| --- | --- |
| [Dedication](DEDICATION.md) | In memory of Jorge Roberto Teixeira Braga |
| [Research principles](RESEARCH_PRINCIPLES.md) | Standards for evidence, testing, and reporting |
| [Epistemic boundaries](docs/epistemic-boundaries.md) | Definitions and limits of inference |
| [Research provenance](research/README.md) | Separation of sources, interpretations, and results |
| [Braga research context](research/braga/README.md) | Original work, concepts, and attribution boundaries |

## Current status

Phase 3 implements the ordered [Minimum Conscious Harness protocol](scf/conscious.md) against the unchanged [state schema](schemas/conscious_state.schema.json). Inspectable stages, separate model/action interfaces, conservative epistemic checks, bounded reflection, and versioned in-process memory are included. No performance improvement or scientific validation is claimed.

## Run the reference runtime

From a checkout with Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python -m examples.minimal_agent
```

On Windows, activate with `.venv\Scripts\activate`. No API keys or provider SDKs are used. After installation, runtime execution makes no network requests. The example prints structured events for two synthetic cycles: a mismatched prediction causes an explicit revision; the next cycle retrieves the observation from memory. This is a deterministic demonstration, not a benchmark or evidence of consciousness.

Each event includes its type, sequence, run ID, cycle, stage, record references, and data. The Python trace API additionally exposes a copy-isolated schema-validated snapshot at every event. See [runtime architecture and limits](docs/architecture.md).

AI-assisted drafting and engineering support for this implementation was provided through ChatGPT/Codex under Fabio Vinelli Lopes's instructions. The existing authorship convention and epistemic boundaries apply.

A license has not yet been selected. The proprietary-rights agreement is not published in this repository.

## Deterministic benchmark v0.1

Phase 4 adds independent B0/B1 baselines, a C1 runtime binding, explicit mechanism ablations, fixed synthetic tasks, resource accounting, and raw-only descriptive aggregation. See [benchmark installation and reproduction](benchmarks/README.md) and the [predeclared protocol](benchmarks/protocol.md). E001 artifacts are kept separately under [experiments/E001_deterministic_baseline](experiments/E001_deterministic_baseline/README.md). This apparatus tests computational behavior, not phenomenal consciousness or sentience; deterministic mock outcomes do not establish real-model performance.
