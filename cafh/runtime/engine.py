"""Deterministic staged controller. No provider APIs, I/O or background workers."""

from copy import deepcopy
from dataclasses import dataclass

from ..adapters.base import ActionResult
from ..epistemics.monitor import Evidence, EpistemicError, EpistemicMonitor
from ..intentionality.manager import form_intention
from ..memory.store import MemoryStore
from ..reflection.engine import post_action, pre_action
from .cycle import Cycle, Trace
from .state import TERMINAL, initial_state, record, validate_state


@dataclass(frozen=True)
class RuntimeConfig:
    allowed_actions: tuple[str, ...] = ()
    max_cycles: int = 2
    max_reflection_depth: int = 1
    requested_reflection_depth: int = 1
    max_no_progress_steps: int = 2
    max_model_calls: int = 10
    goal_observation: str | None = None

    def __post_init__(self):
        for name in ("max_cycles", "requested_reflection_depth", "max_no_progress_steps"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(name + " must be positive")
        for name in ("max_reflection_depth", "max_model_calls"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise ValueError(name + " must be nonnegative")
        if not isinstance(self.allowed_actions, tuple) or not all(isinstance(x, str) and x for x in self.allowed_actions):
            raise ValueError("allowed_actions must be an immutable tuple of names")
        if self.goal_observation is not None and (not isinstance(self.goal_observation, str) or not self.goal_observation):
            raise ValueError("goal_observation must be a nonempty string or None")


class BudgetExceeded(RuntimeError):
    pass


class Engine:
    def __init__(self, adapter, environment, *, objective, config=None, memory=None,
                 run_id="run", scope="default"):
        self.adapter, self.environment = adapter, environment
        self.config = config or RuntimeConfig()
        self.memory = memory if memory is not None else MemoryStore()
        self.monitor, self.trace = EpistemicMonitor(), Trace()
        self._expected_memory_version = self.memory.latest_version(scope)
        previous = self.memory.retrieve(scope)
        if previous is not None and previous["run_id"] == run_id:
            raise ValueError("A new run sharing memory must use a distinct run_id")
        self._state = initial_state(objective, run_id=run_id, scope=scope,
                                    max_cycles=self.config.max_cycles,
                                    max_reflection_depth=self.config.max_reflection_depth,
                                    max_no_progress_steps=self.config.max_no_progress_steps,
                                    max_model_calls=self.config.max_model_calls)

    @property
    def state(self):
        return deepcopy(self._state)

    def _call(self, method, *args):
        budget = self._state["control"]["resource_limits"][0]
        if budget["used"] >= budget["limit"]:
            raise BudgetExceeded("model_call_limit")
        budget["used"] += 1
        return method(*deepcopy(args))

    def _proposals(self, stage):
        proposals = self._call(self.adapter.propose, stage, self.state)
        if not isinstance(proposals, list):
            raise EpistemicError("Adapter must return a list of records")
        known = {r["id"] for k, v in self._state.items() if isinstance(v, list) for r in v}
        known |= {self._state["objective"]["id"], self._state["reflection"]["assessment"]["id"]}
        accepted = []
        for proposal in proposals:
            item = self.monitor.check(proposal, model_proposal=True)
            if item["id"] in known:
                raise EpistemicError("Adapter attempted to overwrite a record")
            known.add(item["id"])
            accepted.append(item)
        return accepted

    def _memory(self, cycle, prefix):
        s = self._state
        version = self.memory.latest_version(s["continuity_scope"])
        if version != self._expected_memory_version:
            raise ValueError("Concurrent memory update; reconcile before action")
        payload = self.memory.retrieve(s["continuity_scope"], version)
        if payload is None:
            s["memory_references"].append(dict(id=prefix + ":missing-memory", record_reference="memory:prior",
                                              version="0", scope=s["continuity_scope"], retrieval_status="missing",
                                              provenance=record("unused", "No prior memory", "unknown", origin="memory",
                                                                source="memory:prior")["provenance"]))
            cycle.emit("memory_retrieved", found=False, version=0, record_count=0)
            return
        self.monitor.restore(payload["evidence"])
        for i, (collection, original) in enumerate(payload["records"]):
            alias = deepcopy(original)
            alias["id"] = f"{prefix}:remembered:{i}"
            alias["information_class"] = "unknown" if original["information_class"] == "unknown" else "remembered"
            alias["provenance"].append(dict(source_reference=original["id"], locator=f"memory:{version}:{original['id']}",
                                             origin="memory", source_information_class=original["information_class"],
                                             captured_at=None, transformation="Retrieved unchanged statement and support metadata"))
            # Remembering an unknown is a record of a gap, not supported knowledge.
            if original["information_class"] == "unknown":
                alias["confidence"] = None
            self.monitor.check(alias)
            s[collection].append(alias)
            s["memory_references"].append(dict(id=f"{prefix}:memory:{i}", record_reference=original["id"], version=str(version),
                                              scope=s["continuity_scope"], retrieval_status="available", provenance=deepcopy(alias["provenance"])))
        cycle.emit("memory_retrieved", found=True, version=version, record_count=len(payload["records"]))

    def run_cycle(self, input_text):
        s = self._state
        if s["status"] in TERMINAL:
            raise RuntimeError("Terminal run cannot dispatch another cycle")
        if not isinstance(input_text, str) or not input_text:
            raise ValueError("A nonempty input report is required")
        n = s["control"]["cycles_completed"] + 1
        prefix = f"{s['run_id']}:c{n}"
        c = Cycle(s, self.trace, n)
        try:
            c.enter("INPUT")
            s["status"] = "running"
            c.emit("cycle_started")
            source = prefix + ":input-source"
            self.monitor.register(Evidence(source, input_text, "human", False))
            s["beliefs"].append(record(prefix + ":input", input_text, origin="human", source=source))
            c.emit("input_received", source=source)

            c.enter("CONTEXT")
            c.emit("context_established", objective=s["objective"]["statement"], allowed_actions=self.config.allowed_actions)

            c.enter("MEMORY")
            self._memory(c, prefix)

            c.enter("WORLD MODEL")
            s["world_model"].extend(self._proposals("WORLD MODEL"))
            c.emit("world_model_updated")

            c.enter("SELF MODEL")
            s["self_model"].extend(self._proposals("SELF MODEL"))
            s["capabilities"].append(record(prefix + ":capability", "Configured action names: " + repr(self.config.allowed_actions),
                                              origin="trusted_configuration", source="config:actions"))
            s["limitations"].append(record(prefix + ":limitation", "Only exact interface-statement mismatches can be detected",
                                             origin="trusted_configuration", source="config:limitations"))
            c.emit("self_model_updated")

            c.enter("ATTENTION")
            s["attention"].append(record(prefix + ":attention", "Prioritize current objective and unresolved outcome", "intended",
                                         origin="trusted_configuration", source="config:attention", target_references=[s["objective"]["id"]],
                                         priority=100, salience_reason="Deterministic objective-first policy"))
            c.emit("attention_updated")

            c.enter("INTERPRETATIONS")
            for item in self._proposals("INTERPRETATIONS"):
                s["uncertainties" if item["information_class"] == "unknown" else "beliefs"].append(item)
            c.emit("interpretations_formed")

            c.enter("EPISTEMIC CHECK")
            self.monitor.audit(s, self.memory)
            c.emit("epistemic_check", accepted=True, absence_of_evidence_is_not_negation=True)

            c.enter("INTENTION")
            candidates = self._call(self.adapter.candidates, self.state)
            candidate, action = form_intention(s, candidates, prefix)
            c.emit("intention_formed", current_state_revision=s["state_revision"], desired_state=s["objective"]["statement"],
                   candidates=[dict(name=x.name, argument=x.argument) for x in candidates],
                   candidate_action=action["id"] if action else None, selection_rule="lexicographic name then argument")

            c.enter("VALUES CHECK")
            allowed = candidate is not None and candidate.name in self.config.allowed_actions
            policy_ref = prefix + ":policy"
            self.monitor.register(Evidence(policy_ref, "Trusted action allowlist", "trusted_configuration", allowed,
                                           action["id"] if action else None))
            s["values_check"] = dict(policy_references=[policy_ref], disposition="pass" if allowed else "block",
                                      rationale="Exact trusted allowlist check", conflict_references=[],
                                      authorization_reference=policy_ref if allowed else None)
            c.emit("values_checked", allowed=allowed)

            c.enter("CONSEQUENCE MODEL")
            prediction = None
            if candidate:
                proposal = self._call(self.adapter.predict, candidate, self.state)
                prediction = self.monitor.check(proposal, model_proposal=True)
                if prediction["information_class"] not in {"inferred", "hypothesized", "imagined"}:
                    raise EpistemicError("Prediction must be inferred, hypothesized or imagined")
                prediction["id"] = prefix + ":prediction"
                prediction.update(action_reference=action["id"], observation_horizon="Immediate interface response")
                s["predicted_consequences"].append(prediction)
            c.emit("consequence_predicted", prediction=prediction)

            c.enter("ACTION")
            review = pre_action(s, action, prediction) if action else dict(allowed=False, rationale="No candidates")
            c.emit("pre_action_reflection", **review)
            self.monitor.audit(s, self.memory)
            result = None
            error = None
            if action:
                if review["allowed"] and candidate.name in self.config.allowed_actions:
                    action.update(status="authorized", authorization_reference=policy_ref)
                    c.emit("action_selected", selected_action=action["id"], predicted_consequence=prediction["id"])
                    try:
                        result = self.environment.execute(candidate)
                        if not isinstance(result, ActionResult):
                            raise ValueError("Action interface must return ActionResult")
                        action["status"] = "executed" if result.available else "unknown"
                    except Exception as exc:
                        # No retry: external outcome may be unknown after an exception.
                        action["status"] = "unknown"
                        error = type(exc).__name__
                        result = None
                    c.emit("action_result", disposition=action["status"], interface_error=error)
                else:
                    action["status"] = "blocked"
                    c.emit("action_selected", selected_action=None, disposition="blocked")
            else:
                c.emit("action_selected", selected_action=None, disposition="abstain")

            c.enter("OBSERVATION")
            observation = None
            if action:
                available = result is not None and result.available
                statement = result.statement if available else "Action outcome unavailable"
                event_source = prefix + ":environment-source"
                if available:
                    self.monitor.register(Evidence(event_source, statement, "environment", True, action["id"]))
                observation = record(prefix + ":observation", statement, "observed" if available else "unknown",
                                     origin="environment", source=event_source,
                                     evidence=[event_source] if available else [], support="supported" if available else "unassessed",
                                     action_reference=action["id"], prediction_references=[prediction["id"]] if prediction else [],
                                     outcome=("matched" if statement == prediction["statement"] else "deviated") if available and prediction else "unresolved")
                self.monitor.check(observation, definition="observation")
                s["observed_consequences"].append(observation)
                action["observation_references"].append(observation["id"])
                if available:
                    s["active_intentions"][-1]["status"] = "achieved"
            c.emit("observation_received", observation=observation, interface_error=error,
                   action_disposition=action["status"] if action else "no_action")

            c.enter("REFLECTION")
            depth_stopped = post_action(s, prediction, observation, requested_depth=self.config.requested_reflection_depth,
                                        emit=c.emit, prefix=prefix)

            c.enter("STATE/MEMORY UPDATE")
            s["control"]["cycles_completed"] += 1
            earlier_outcomes = {r["statement"] for r in s["observed_consequences"]
                                if r is not observation and r["information_class"] == "observed"}
            progressed = (s["reflection"]["progress"] == "decision_changed" or
                          (observation is not None and observation["information_class"] == "observed"
                           and observation["statement"] not in earlier_outcomes))
            s["control"]["no_progress_steps"] = 0 if progressed else s["control"]["no_progress_steps"] + 1
            reason, status = None, "running"
            if observation and observation["information_class"] == "observed" and observation["statement"] == self.config.goal_observation:
                reason, status = "goal_observed", "completed"
            elif candidate is None:
                reason, status = "no_candidate_actions", "abstained"
            elif not allowed:
                reason, status = "policy_block", "stopped"
            elif error:
                reason, status = "interface_outcome_unknown", "failed"
            elif depth_stopped:
                reason, status = "reflection_depth_limit", "stopped"
            elif s["control"]["no_progress_steps"] >= self.config.max_no_progress_steps:
                reason, status = "no_progress_limit", "stopped"
            elif n >= self.config.max_cycles:
                reason, status = "cycle_limit", "stopped"
            elif s["control"]["resource_limits"][0]["used"] >= self.config.max_model_calls:
                reason, status = "model_call_limit", "stopped"
            s["status"], s["control"]["stop_reason"] = status, reason
            if reason:
                s["reflection"]["next_disposition"] = "stop"
            self.monitor.audit(s, self.memory)
            validate_state(s)
            # Persist original self records plus the latest observed record only.
            # Repeated retrieval never invents a new observation or erases history.
            retained = [("self_model", r) for r in s["self_model"] if r["information_class"] != "remembered"]
            if observation:
                retained.append(("beliefs", {k: v for k, v in observation.items()
                                             if k not in {"action_reference", "prediction_references", "outcome"}}))
            payload = dict(run_id=s["run_id"], records=retained, evidence=self.monitor.export(), state=deepcopy(s))
            self._expected_memory_version = self.memory.append(s["continuity_scope"], payload,
                                                              expected_version=self._expected_memory_version)
            c.emit("memory_updated", version=self._expected_memory_version, retained=len(retained))
            c.emit("cycle_completed", status=s["status"], stop_reason=reason)
        except Exception as exc:
            failed_stage = s["phase"]
            consumed = deepcopy(s["control"]["resource_limits"])
            # Reject partial invalid mutations, retain the latest validated trace state.
            # There are no automatic retries after dispatch or a failed validation.
            if self.trace.events:
                accepted = self.trace.events[-1]["state"]
                s.clear()
                s.update(accepted)
            s["control"]["resource_limits"] = consumed
            s["phase"] = failed_stage
            s["status"] = "stopped" if isinstance(exc, BudgetExceeded) else "failed"
            s["control"]["stop_reason"] = str(exc) or type(exc).__name__
            c.emit("cycle_failed", error_type=type(exc).__name__, failed_stage=failed_stage,
                   reason=s["control"]["stop_reason"])
        return self.state
