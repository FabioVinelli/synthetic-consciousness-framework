"""The model proposes; a separate trusted action interface observes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    name: str
    argument: str

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name or not isinstance(self.argument, str):
            raise ValueError("Candidate requires a nonempty name and string argument")


@dataclass(frozen=True)
class ActionResult:
    statement: str
    available: bool = True

    def __post_init__(self):
        if not isinstance(self.statement, str) or not self.statement or type(self.available) is not bool:
            raise ValueError("Invalid action result")


class ModelAdapter(ABC):
    @abstractmethod
    def propose(self, stage: str, state: dict) -> list[dict]:
        """Records for WORLD MODEL, SELF MODEL or INTERPRETATIONS; no side effects."""

    @abstractmethod
    def candidates(self, state: dict) -> list[Candidate]:
        """Return action proposals, never authorization."""

    @abstractmethod
    def predict(self, candidate: Candidate, state: dict) -> dict:
        """Return one epistemic record for the predicted interface statement."""


class ActionInterface(ABC):
    @abstractmethod
    def execute(self, candidate: Candidate) -> ActionResult:
        """Trusted observation boundary. No execution occurs through ModelAdapter."""
