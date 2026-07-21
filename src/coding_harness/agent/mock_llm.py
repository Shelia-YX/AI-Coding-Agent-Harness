"""Offline deterministic LLM test adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum

from coding_harness.agent.actions import (
    ControlAction,
    StructuredAction,
    ToolAction,
    parse_action,
)
from coding_harness.agent.context import BuiltContext
from coding_harness.agent.results import ToolResultStatus


class MockFailureCode(StrEnum):
    SCRIPT_EXHAUSTED = "SCRIPT_EXHAUSTED"
    STATUS_MISMATCH = "STATUS_MISMATCH"


class MockLLMFailure(RuntimeError):
    __slots__ = ("_code",)

    def __init__(self, code: MockFailureCode) -> None:
        if type(code) is not MockFailureCode:
            raise ValueError("code must be a MockFailureCode")
        object.__setattr__(self, "_code", code)
        super().__init__("mock LLM could not produce a scripted action")

    @property
    def code(self) -> MockFailureCode:
        return self._code

    def __setattr__(self, _name: str, _value: object) -> None:
        raise AttributeError("MockLLMFailure is immutable")

    def __delattr__(self, _name: str) -> None:
        raise AttributeError("MockLLMFailure is immutable")


@dataclass(frozen=True, slots=True)
class MockScriptStep:
    expected_latest_status: ToolResultStatus | None
    action: StructuredAction

    def __post_init__(self) -> None:
        if (
            self.expected_latest_status is not None
            and type(self.expected_latest_status) is not ToolResultStatus
        ):
            raise ValueError(
                "expected_latest_status must be a ToolResultStatus or None"
            )
        if type(self.action) not in (ToolAction, ControlAction):
            raise ValueError("action must be an exact ToolAction or ControlAction")

    @classmethod
    def from_raw(
        cls,
        *,
        expected_latest_status: ToolResultStatus | None,
        raw_action: str | Mapping[str, object],
    ) -> MockScriptStep:
        try:
            action = parse_action(raw_action)
        except Exception:
            raise ValueError("mock script contains an invalid action") from None
        return cls(
            expected_latest_status=expected_latest_status,
            action=action,
        )


class MockLLM:
    __slots__ = ("_steps", "_cursor")

    def __init__(self, script: Sequence[MockScriptStep]) -> None:
        script_failed = False
        try:
            steps = tuple(script)
        except Exception:
            script_failed = True
            steps = ()
        if script_failed:
            raise ValueError("mock script could not be read")
        if not steps:
            raise ValueError("mock script must not be empty")
        if any(type(step) is not MockScriptStep for step in steps):
            raise ValueError("mock script items must be MockScriptStep instances")
        self._steps = steps
        self._cursor = 0

    def complete(self, context: BuiltContext, /) -> StructuredAction:
        if type(context) is not BuiltContext:
            raise ValueError("context must be a BuiltContext")
        if self._cursor >= len(self._steps):
            raise MockLLMFailure(MockFailureCode.SCRIPT_EXHAUSTED) from None
        step = self._steps[self._cursor]
        if context.latest_result_status is not step.expected_latest_status:
            raise MockLLMFailure(MockFailureCode.STATUS_MISMATCH) from None
        self._cursor += 1
        return step.action


__all__ = ["MockFailureCode", "MockLLMFailure", "MockScriptStep", "MockLLM"]
