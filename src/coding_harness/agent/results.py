"""Bounded immutable tool results for the WP-02 wire protocol."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import re


_MAX_INTEGER = 2**63 - 1
_ACTION_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", re.ASCII)
_RESOURCE_KEY_RE = re.compile(r"[a-z][a-z0-9_]{0,63}", re.ASCII)
_MISSING_ITEM = object()


class ToolResultStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    DENIED = "DENIED"
    TRUNCATED = "TRUNCATED"


def _bounded_string(
    value: object,
    field: str,
    *,
    minimum: int,
    maximum: int,
) -> str:
    if type(value) is not str:
        raise ValueError(f"{field} must be a string")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        size = None
    if size is None:
        raise ValueError(f"{field} must be valid UTF-8 text") from None
    if "\0" in value:
        raise ValueError(f"{field} must not contain NUL")
    if not minimum <= size <= maximum:
        raise ValueError(f"{field} length must be {minimum}..{maximum} UTF-8 bytes")
    return value


def _mapping_items(value: Mapping[object, object]):
    failed = False
    try:
        iterator = iter(value.items())
    except Exception:
        failed = True
        iterator = iter(())
    if failed:
        raise ValueError("resource_counts could not be read") from None

    while True:
        failed = False
        try:
            pair = next(iterator)
        except StopIteration:
            pair = _MISSING_ITEM
        except Exception:
            failed = True
            pair = _MISSING_ITEM
        if failed:
            raise ValueError("resource_counts could not be read") from None
        if pair is _MISSING_ITEM:
            return

        failed = False
        try:
            key, count = pair
        except Exception:
            failed = True
            key = count = None
        if failed:
            raise ValueError("resource_counts contains an invalid item") from None
        yield key, count


def _normalize_resource_counts(value: object) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, Mapping):
        raise ValueError("resource_counts must be a mapping")
    normalized: list[tuple[str, int]] = []
    seen_keys: set[str] = set()
    for index, (key, count) in enumerate(_mapping_items(value)):
        if index >= 16:
            raise ValueError("resource_counts must contain at most 16 items")
        if type(key) is not str or _RESOURCE_KEY_RE.fullmatch(key) is None:
            raise ValueError("resource_counts contains an invalid key")
        if key in seen_keys:
            raise ValueError("resource_counts contains a duplicate key")
        seen_keys.add(key)
        if type(count) is not int:
            raise ValueError(f"resource_counts.{key} must be an integer")
        if not 0 <= count <= _MAX_INTEGER:
            raise ValueError(f"resource_counts.{key} is outside the allowed range")
        normalized.append((key, count))
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True)
class ToolResult:
    action_id: str
    status: ToolResultStatus
    summary: str
    output: str
    resource_counts: tuple[tuple[str, int], ...]
    truncated: bool
    error: str | None

    def __post_init__(self) -> None:
        if type(self.action_id) is not str or _ACTION_ID_RE.fullmatch(self.action_id) is None:
            raise ValueError("action_id has invalid format")
        if not isinstance(self.status, ToolResultStatus):
            raise ValueError("status must be a ToolResultStatus")

        _bounded_string(self.summary, "summary", minimum=1, maximum=4_096)
        _bounded_string(self.output, "output", minimum=0, maximum=65_536)
        normalized_counts = _normalize_resource_counts(self.resource_counts)
        object.__setattr__(self, "resource_counts", normalized_counts)

        if type(self.truncated) is not bool:
            raise ValueError("truncated must be a bool")
        if self.error is not None:
            _bounded_string(self.error, "error", minimum=1, maximum=4_096)

        if self.status is ToolResultStatus.SUCCEEDED:
            if self.error is not None:
                raise ValueError("SUCCEEDED result must not contain an error")
            if self.truncated:
                raise ValueError("SUCCEEDED result must not be truncated")
        elif self.status is ToolResultStatus.TRUNCATED:
            if self.error is not None:
                raise ValueError("TRUNCATED result must not contain an error")
            if not self.truncated:
                raise ValueError("TRUNCATED result must set truncated to true")
        elif self.status in {ToolResultStatus.FAILED, ToolResultStatus.DENIED}:
            if self.truncated:
                raise ValueError(f"{self.status.value} result must not be truncated")
            if self.error is None:
                raise ValueError(f"{self.status.value} result requires an error")

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "status": self.status.value,
            "summary": self.summary,
            "output": self.output,
            "resource_counts": dict(self.resource_counts),
            "truncated": self.truncated,
            "error": self.error,
        }


__all__ = ["ToolResultStatus", "ToolResult"]
