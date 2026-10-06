"""Run with: python -m examples.minimal_agent (after pip install -e .)."""

import json

from cafh.adapters.mock import MockAdapter, MockEnvironment
from cafh.runtime.engine import Engine, RuntimeConfig
from cafh.runtime.state import validate_state


def main():
    engine = Engine(MockAdapter(), MockEnvironment(), objective="Inspect a local echo response",
                    config=RuntimeConfig(allowed_actions=("echo",)), run_id="example")
    for _ in range(2):
        engine.run_cycle("Request a local echo observation")
    for event in engine.trace.events:
        print(json.dumps({k: event[k] for k in ("sequence", "run_id", "cycle", "stage", "event", "record_references", "data")}, sort_keys=True))
    state = engine.state
    validate_state(state)
    print(json.dumps(dict(status=state["status"], stop_reason=state["control"]["stop_reason"],
                          cycles=state["control"]["cycles_completed"], revisions=len(state["model_revisions"]),
                          consequences=[r["outcome"] for r in state["observed_consequences"]],
                          memory_versions=engine.memory.latest_version("default")), sort_keys=True))
    if state["status"] == "failed":
        raise RuntimeError(state["control"]["stop_reason"])


if __name__ == "__main__":
    main()
