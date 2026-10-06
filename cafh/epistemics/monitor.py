"""Conservative admission: a model cannot certify its own evidence."""

from copy import deepcopy
from dataclasses import dataclass, asdict

from ..runtime.state import records, validate_record, validate_state


class EpistemicError(ValueError):
    pass


@dataclass(frozen=True)
class Evidence:
    id: str
    statement: str
    origin: str
    verified: bool = False
    action_reference: str | None = None


class EpistemicMonitor:
    def __init__(self):
        self._evidence = {}

    def register(self, evidence):
        prior = self._evidence.get(evidence.id)
        if prior is not None and prior != evidence:
            raise EpistemicError("Evidence cannot be overwritten")
        self._evidence[evidence.id] = evidence

    def export(self):
        return [asdict(e) for e in self._evidence.values()]

    def restore(self, entries):
        for entry in entries:
            self.register(Evidence(**entry))

    def check(self, value, *, model_proposal=False, definition="record"):
        item = deepcopy(value)
        validate_record(item, definition)
        if model_proposal:
            if any(p["origin"] != "model" for p in item["provenance"]):
                raise EpistemicError("Model attempted to assert trusted provenance")
            if item["information_class"] in {"observed", "remembered"}:
                raise EpistemicError("Observed/remembered records require a trusted interface")
        for key in ("evidence_references", "counterevidence_references"):
            for ref in item[key]:
                if ref not in self._evidence:
                    raise EpistemicError("Unresolved evidence reference: " + ref)
        if item["information_class"] == "unknown":
            if item["confidence"] is not None or item["evidence_status"] == "supported":
                raise EpistemicError("Unknown cannot be normalized into knowledge")
        if item["evidence_status"] == "supported" or item["information_class"] == "observed":
            # v0.1 verifies only exact, scoped interface statements; no entailment oracle.
            matching = [self._evidence[r] for r in item["evidence_references"]
                        if self._evidence[r].verified and self._evidence[r].statement == item["statement"]]
            if not matching:
                raise EpistemicError("No independently registered evidence for the statement")
            if item["information_class"] == "observed" and not any(
                p["source_reference"] == evidence.id and p["origin"] == evidence.origin
                for p in item["provenance"] for evidence in matching
            ):
                raise EpistemicError("Observed provenance does not match registered evidence")
        return item

    def audit(self, state, memory=None):
        validate_state(state)
        definitions = {"active_intentions": "intention", "attention": "attention",
                       "recent_actions": "action", "predicted_consequences": "prediction",
                       "observed_consequences": "observation", "model_revisions": "revision"}
        self.check(state["objective"])
        self.check(state["reflection"]["assessment"])
        for name, values in state.items():
            if isinstance(values, list) and name != "memory_references":
                for item in values:
                    self.check(item, definition=definitions.get(name, "record"))
        index = {r["id"]: r for r in records(state)}
        typed = {name: {r["id"] for r in state[name]} for name in definitions}
        for intention in state["active_intentions"]:
            if intention["goal_reference"] != state["objective"]["id"]:
                raise EpistemicError("Unresolved objective")
        for action in state["recent_actions"]:
            if action["intention_reference"] not in typed["active_intentions"]:
                raise EpistemicError("Unresolved intention")
            if not set(action["observation_references"]) <= typed["observed_consequences"]:
                raise EpistemicError("Unresolved observation")
            if action["status"] in {"authorized", "executed"}:
                authority = self._evidence.get(action["authorization_reference"])
                if not authority or not authority.verified or authority.origin != "trusted_configuration" or authority.action_reference != action["id"]:
                    raise EpistemicError("Action lacks trusted authorization")
        for prediction in state["predicted_consequences"]:
            if prediction["action_reference"] not in typed["recent_actions"]:
                raise EpistemicError("Unresolved predicted action")
        for observation in state["observed_consequences"]:
            if observation["action_reference"] not in typed["recent_actions"]:
                raise EpistemicError("Unresolved observed action")
            for ref in observation["prediction_references"]:
                if ref not in typed["predicted_consequences"] or index[ref]["action_reference"] != observation["action_reference"]:
                    raise EpistemicError("Inconsistent observation/prediction link")
                if observation["information_class"] == "observed":
                    expected = "matched" if index[ref]["statement"] == observation["statement"] else "deviated"
                    if observation["outcome"] != expected:
                        raise EpistemicError("Incorrect prediction/observation comparison")
            if observation["information_class"] == "observed":
                if not any(self._evidence[ref].action_reference == observation["action_reference"]
                           for ref in observation["evidence_references"]):
                    raise EpistemicError("Observation evidence belongs to a different action")
                action = index[observation["action_reference"]]
                if action["status"] != "executed" or observation["id"] not in action["observation_references"]:
                    raise EpistemicError("Observation lacks executed action backlink")
        graph = {}
        for revision in state["model_revisions"]:
            old, new = revision["prior_record_reference"], revision["replacement_record_reference"]
            if old not in index or new not in index or old == new:
                raise EpistemicError("Invalid revision references")
            if not revision["trigger_references"] or not set(revision["trigger_references"]) <= set(index):
                raise EpistemicError("Unresolved revision trigger")
            if old in typed["predicted_consequences"]:
                triggers = [index[ref] for ref in revision["trigger_references"]
                            if ref in typed["observed_consequences"]
                            and index[ref]["action_reference"] == index[old]["action_reference"]]
                if not triggers:
                    raise EpistemicError("Prediction revision needs its action observation")
            graph.setdefault(old, []).append(new)
        def visit(key, ancestors):
            if key in ancestors:
                raise EpistemicError("Cyclic revision")
            for child in graph.get(key, []):
                visit(child, ancestors | {key})
        for key in graph:
            visit(key, set())
        for focus in state["attention"]:
            if not set(focus["target_references"]) <= set(index):
                raise EpistemicError("Unresolved attention target")
        reflection = state["reflection"]
        for field, target in (("prediction_references", "predicted_consequences"),
                              ("observation_references", "observed_consequences"),
                              ("revision_references", "model_revisions")):
            if not set(reflection[field]) <= typed[target]:
                raise EpistemicError("Unresolved reflection reference")
        values = state["values_check"]
        for ref in values["policy_references"]:
            if ref not in self._evidence or self._evidence[ref].origin != "trusted_configuration":
                raise EpistemicError("Unresolved trusted policy")
        if not set(values["conflict_references"]) <= set(index):
            raise EpistemicError("Unresolved values conflict")
        if values["disposition"] == "pass":
            auth = self._evidence.get(values["authorization_reference"])
            if not auth or not auth.verified or values["authorization_reference"] not in values["policy_references"]:
                raise EpistemicError("Values pass lacks authorization")
        resolved_memory = {}
        for ref in state["memory_references"]:
            if memory is None:
                raise EpistemicError("Memory references require a store for validation")
            if ref["scope"] != state["continuity_scope"]:
                raise EpistemicError("Memory scope mismatch")
            try:
                payload = memory.retrieve(ref["scope"], int(ref["version"]))
            except ValueError as exc:
                raise EpistemicError("Invalid memory version") from exc
            original = next((r for _, r in payload["records"] if r["id"] == ref["record_reference"]), None) if payload else None
            if ref["retrieval_status"] == "missing":
                if original is not None:
                    raise EpistemicError("Available memory falsely marked missing")
            elif original is None:
                raise EpistemicError("Fabricated memory reference")
            else:
                resolved_memory[(ref["record_reference"], ref["version"])] = original
        for item in index.values():
            retrievals = [p for p in item["provenance"] if p["origin"] == "memory"]
            if item["information_class"] == "remembered" and not retrievals:
                raise EpistemicError("Remembered claim lacks retrieval provenance")
            for p in retrievals:
                matches = [r for (ref, version), r in resolved_memory.items()
                           if ref == p["source_reference"] and p["locator"] == f"memory:{version}:{ref}"]
                if not matches:
                    raise EpistemicError("Unresolved memory provenance")
                original = matches[0]
                for field in ("statement", "confidence", "evidence_status", "evidence_references", "counterevidence_references", "revision_conditions"):
                    if item[field] != original[field]:
                        raise EpistemicError("Remembered evidence metadata was changed")
                if p["source_information_class"] != original["information_class"]:
                    raise EpistemicError("Memory origin classification changed")
                if original["information_class"] == "unknown" and item["information_class"] != "unknown":
                    raise EpistemicError("Remembering cannot reclassify an unknown")
