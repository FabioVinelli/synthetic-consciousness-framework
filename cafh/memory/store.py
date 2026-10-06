"""Copy-isolated, scope-aware immutable versions; no missing-data synthesis."""

from copy import deepcopy


class MemoryStore:
    def __init__(self):
        self._versions = {}

    def latest_version(self, scope):
        return len(self._versions.get(scope, []))

    def retrieve(self, scope, version=None):
        versions = self._versions.get(scope, [])
        version = len(versions) if version is None else version
        if type(version) is not int or version < 1 or version > len(versions):
            return None
        return deepcopy(versions[version - 1])

    def append(self, scope, payload, *, expected_version):
        if self.latest_version(scope) != expected_version:
            raise ValueError("Stale memory version")
        self._versions.setdefault(scope, []).append(deepcopy(payload))
        return self.latest_version(scope)
