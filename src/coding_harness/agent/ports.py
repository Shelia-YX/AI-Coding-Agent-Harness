"""Narrow orchestration ports used by the agent loop."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from coding_harness.agent.actions import StructuredAction, ToolAction
from coding_harness.agent.context import BuiltContext
from coding_harness.agent.results import ToolResult


@runtime_checkable
class PolicyPort(Protocol):
    def allows(self, *, action: StructuredAction) -> bool:
        """Return an exact boolean policy decision for one action."""
        raise NotImplementedError("protocol method")


@runtime_checkable
class ToolPort(Protocol):
    def execute(self, *, action: ToolAction) -> ToolResult:
        """Execute one already-authorized tool action."""
        raise NotImplementedError("protocol method")


@runtime_checkable
class StorePort(Protocol):
    def record_attempt(
        self,
        *,
        attempt_number: int,
        context: BuiltContext,
        started_at: float,
    ) -> None:
        """Persist an attempt marker before its provider call."""
        raise NotImplementedError("protocol method")


@runtime_checkable
class ClockPort(Protocol):
    def now(self) -> float:
        """Return the injected attempt timestamp."""
        raise NotImplementedError("protocol method")


__all__ = ["PolicyPort", "ToolPort", "StorePort", "ClockPort"]
