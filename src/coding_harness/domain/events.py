"""Immutable persisted domain-event models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import PurePosixPath
import unicodedata


_MAX_TEXT_BYTES = 1024
_MAX_PAYLOAD_BYTES = 64 * 1024
_MAX_EVIDENCE_PATH_BYTES = 4096


def _valid_text(value: object) -> bool:
    if type(value) is not str or not value or "\0" in value:
        return False
    try:
        return len(value.encode("utf-8", errors="strict")) <= _MAX_TEXT_BYTES
    except UnicodeError:
        return False


class _ClosedEnum(Enum):
    def __bool__(self) -> bool:
        raise TypeError(f"{type(self).__name__} has no truth value")


class DomainEventKind(_ClosedEnum):
    TASK_CREATED = "TASK_CREATED"
    TASK_STATE_CHANGED = "TASK_STATE_CHANGED"


class EvidenceKind(_ClosedEnum):
    ARTIFACT = "ARTIFACT"
    TEMPORARY_LOG = "TEMPORARY_LOG"


class EvidenceLifecycle(_ClosedEnum):
    AVAILABLE = "AVAILABLE"
    DELETED = "DELETED"


def _is_digest(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _valid_private_reference(value: object) -> bool:
    if type(value) is not str or not value or "\\" in value:
        return False
    try:
        if (
            len(value.encode("utf-8", errors="strict"))
            > _MAX_EVIDENCE_PATH_BYTES
            or any(unicodedata.category(character) == "Cc" for character in value)
        ):
            return False
    except UnicodeError:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and tuple(path.parts)
        and all(part not in {"", ".", ".."} for part in path.parts)
        and str(path) == value
    )


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    kind: EvidenceKind
    relative_path: str
    content_digest: str
    size_bytes: int
    lifecycle: EvidenceLifecycle

    def __post_init__(self) -> None:
        if (
            type(self.kind) is not EvidenceKind
            or not _valid_private_reference(self.relative_path)
            or not _is_digest(self.content_digest)
            or type(self.size_bytes) is not int
            or self.size_bytes < 0
            or type(self.lifecycle) is not EvidenceLifecycle
        ):
            raise ValueError("evidence reference is invalid")

    def __bool__(self) -> bool:
        raise TypeError("EvidenceRef has no truth value")


def canonical_event_payload(
    payload: tuple[tuple[str, str], ...],
) -> str:
    if (
        type(payload) is not tuple
        or any(
            type(item) is not tuple
            or len(item) != 2
            or not _valid_text(item[0])
            or type(item[1]) is not str
            or "\0" in item[1]
            for item in payload
        )
        or tuple(sorted(payload, key=lambda item: item[0])) != payload
        or len({item[0] for item in payload}) != len(payload)
    ):
        raise ValueError("domain event payload is invalid")
    try:
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError):
        raise ValueError("domain event payload is invalid") from None
    if len(encoded.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
        raise ValueError("domain event payload exceeds the size limit")
    return encoded


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_id: int
    event_kind: DomainEventKind
    occurred_at: int
    task_id: str
    entity_identity: str
    entity_revision: int | None
    payload: tuple[tuple[str, str], ...]
    evidence_refs: tuple[EvidenceRef, ...]

    def __post_init__(self) -> None:
        if (
            type(self.event_id) is not int
            or self.event_id < 1
            or type(self.event_kind) is not DomainEventKind
            or type(self.occurred_at) is not int
            or self.occurred_at < 0
            or not _valid_text(self.task_id)
            or not _valid_text(self.entity_identity)
            or self.entity_revision is not None
            and (
                type(self.entity_revision) is not int
                or self.entity_revision < 1
            )
            or type(self.evidence_refs) is not tuple
            or any(
                type(reference) is not EvidenceRef
                for reference in self.evidence_refs
            )
        ):
            raise ValueError("domain event is invalid")
        canonical_event_payload(self.payload)

    def __bool__(self) -> bool:
        raise TypeError("DomainEvent has no truth value")


__all__ = [
    "DomainEvent",
    "DomainEventKind",
    "EvidenceKind",
    "EvidenceLifecycle",
    "EvidenceRef",
]
