"""Narrow LLM proposal interface for the agent package."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from coding_harness.agent.actions import StructuredAction
from coding_harness.agent.context import BuiltContext


@runtime_checkable
class LLMAdapter(Protocol):
    def complete(self, context: BuiltContext, /) -> StructuredAction:
        """Return one structured proposal without performing side effects."""
        raise NotImplementedError("protocol method")


__all__ = ["LLMAdapter"]
