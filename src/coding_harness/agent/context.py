"""Deterministic, byte-bounded context construction."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import json

from coding_harness.agent.actions import ToolAction, parse_action
from coding_harness.agent.results import ToolResult, ToolResultStatus


def _encode_payload(payload: dict[str, object]) -> bytes:
    encoding_failed = False
    try:
        encoded = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (RecursionError, TypeError, UnicodeEncodeError, ValueError):
        encoding_failed = True
        encoded = b""
    if encoding_failed:
        raise ValueError("payload could not be encoded")
    return encoded


@dataclass(frozen=True, slots=True)
class ContextAttempt:
    action: ToolAction
    result: ToolResult

    def __post_init__(self) -> None:
        if type(self.action) is not ToolAction:
            raise ValueError("action must be a ToolAction")
        if type(self.result) is not ToolResult:
            raise ValueError("result must be a ToolResult")
        if self.action.action_id != self.result.action_id:
            raise ValueError("action_id must match result.action_id")

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action.to_dict(),
            "result": self.result.to_dict(),
        }


def _snapshot_attempt(value: ContextAttempt) -> ContextAttempt:
    action = parse_action(value.action.to_dict())
    if type(action) is not ToolAction:
        raise ValueError("history action must be a ToolAction")
    result = ToolResult(
        action_id=value.result.action_id,
        status=value.result.status,
        summary=value.result.summary,
        output=value.result.output,
        resource_counts=dict(value.result.resource_counts),
        truncated=value.result.truncated,
        error=value.result.error,
    )
    return ContextAttempt(action=action, result=result)


@dataclass(frozen=True, slots=True, init=False)
class BuiltContext:
    task: str
    attempts: tuple[ContextAttempt, ...]
    truncated: bool
    used_bytes: int
    max_bytes: int

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("BuiltContext instances must be created by ContextBuilder")

    @property
    def latest_result_status(self) -> ToolResultStatus | None:
        if not self.attempts:
            return None
        return self.attempts[-1].result.status

    def to_dict(self) -> dict[str, object]:
        return {
            "task": self.task,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "truncated": self.truncated,
        }

    def to_json(self) -> str:
        return _encode_payload(self.to_dict()).decode("utf-8")


def _build_context(
    *,
    task: str,
    attempts: tuple[ContextAttempt, ...],
    truncated: bool,
    used_bytes: int,
    max_bytes: int,
) -> BuiltContext:
    context = object.__new__(BuiltContext)
    object.__setattr__(context, "task", task)
    object.__setattr__(context, "attempts", attempts)
    object.__setattr__(context, "truncated", truncated)
    object.__setattr__(context, "max_bytes", max_bytes)
    object.__setattr__(context, "used_bytes", used_bytes)
    return context


class ContextBuilder:
    @staticmethod
    def build(
        *,
        task: str,
        history: Sequence[ContextAttempt],
        max_bytes: int,
    ) -> BuiltContext:
        if type(task) is not str or not task or "\0" in task:
            raise ValueError("task must be non-empty UTF-8 text without NUL")
        task_encoding_failed = False
        try:
            task.encode("utf-8")
        except UnicodeEncodeError:
            task_encoding_failed = True
        if task_encoding_failed:
            raise ValueError("task must be non-empty UTF-8 text without NUL")
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("max_bytes must be a positive integer")

        history_failed = False
        try:
            snapshot = tuple(history)
        except Exception:
            history_failed = True
            snapshot = ()
        if history_failed:
            raise ValueError("history could not be read")
        if any(type(item) is not ContextAttempt for item in snapshot):
            raise ValueError("history items must be ContextAttempt instances")

        conversion_failed = False
        canonical_attempts: list[ContextAttempt] = []
        attempt_payloads: list[dict[str, object]] = []
        encoded_attempts: list[bytes] = []
        try:
            for attempt in snapshot:
                canonical_attempt = _snapshot_attempt(attempt)
                payload = canonical_attempt.to_dict()
                canonical_attempts.append(canonical_attempt)
                attempt_payloads.append(payload)
                encoded_attempts.append(_encode_payload(payload))
        except Exception:
            conversion_failed = True
        if conversion_failed:
            raise ValueError("history items could not be encoded")

        empty_envelope_sizes = {
            truncated: len(
                _encode_payload(
                    {"task": task, "attempts": [], "truncated": truncated}
                )
            )
            for truncated in (False, True)
        }
        truncated = bool(snapshot)
        if empty_envelope_sizes[truncated] > max_bytes:
            raise ValueError("context envelope exceeds byte budget")

        selected_start = len(snapshot)
        selected_encoded_bytes = 0
        selected_count = 0
        for index in range(len(snapshot) - 1, -1, -1):
            candidate_count = selected_count + 1
            candidate_attempt_bytes = (
                selected_encoded_bytes
                + len(encoded_attempts[index])
                + (1 if selected_count else 0)
            )
            candidate_truncated = index != 0
            candidate_size = (
                empty_envelope_sizes[candidate_truncated]
                + candidate_attempt_bytes
            )
            if candidate_size > max_bytes:
                break
            selected_start = index
            selected_count = candidate_count
            selected_encoded_bytes = candidate_attempt_bytes
            truncated = candidate_truncated

        selected = tuple(canonical_attempts[selected_start:])
        selected_payloads = attempt_payloads[selected_start:]
        payload = {
            "task": task,
            "attempts": selected_payloads,
            "truncated": truncated,
        }
        encoded_payload = _encode_payload(payload)
        calculated_size = (
            empty_envelope_sizes[truncated] + selected_encoded_bytes
        )
        if len(encoded_payload) != calculated_size or calculated_size > max_bytes:
            raise ValueError("context size calculation failed")
        return _build_context(
            task=task,
            attempts=selected,
            truncated=truncated,
            used_bytes=calculated_size,
            max_bytes=max_bytes,
        )


__all__ = ["ContextAttempt", "BuiltContext", "ContextBuilder"]
