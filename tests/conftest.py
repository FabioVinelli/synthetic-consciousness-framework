import pytest

from cafh.adapters.mock import MockAdapter, MockEnvironment
from cafh.runtime.engine import Engine, RuntimeConfig


@pytest.fixture
def make_engine():
    def make(*, adapter=None, environment=None, memory=None, run_id="test", scope="default", **config):
        config.setdefault("allowed_actions", ("echo",))
        return Engine(adapter or MockAdapter(), environment or MockEnvironment(),
                      objective="Inspect a local response", config=RuntimeConfig(**config),
                      memory=memory, run_id=run_id, scope=scope)
    return make
