"""Immutable models for the durable apply transaction runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from coding_harness.domain.enums import TaskState
from coding_harness.workspace.changeset import ChangeOperation
from coding_harness.workspace.file_model import SupportedEntryKind
from coding_harness.workspace.paths import RepoPath

if TYPE_CHECKING:
    from coding_harness.transaction.journal import ApplyJournal


def _is_digest(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_text(value: object) -> bool:
    if type(value) is not str or not value or "\0" in value:
        return False
    try:
        return len(value.encode("utf-8", errors="strict")) <= 1024
    except UnicodeError:
        return False


def _is_private_relative(value: object) -> bool:
    if type(value) is not str or not value or "\\" in value or "\0" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and tuple(path.parts)
        and all(part not in {"", ".", ".."} for part in path.parts)
        and str(path) == value
    )


class _ClosedEnum(Enum):
    def __bool__(self) -> bool:
        raise TypeError(f"{type(self).__name__} has no truth value")


class ApplyDecision(_ClosedEnum):
    APPLY = "APPLY"
    REJECT = "REJECT"


class ApplyPhase(_ClosedEnum):
    PREPARING = "PREPARING"
    BACKUP_READY = "BACKUP_READY"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class JournalStage(_ClosedEnum):
    PREPARE = "PREPARE"
    BACKUP = "BACKUP"
    APPLY = "APPLY"
    ROLLBACK = "ROLLBACK"
    VERIFY = "VERIFY"
    RECOVERY = "RECOVERY"


class JournalStatus(_ClosedEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


class RecoveryState(_ClosedEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


@dataclass(frozen=True, slots=True)
class ApplyPlanEntry:
    order: int
    path: RepoPath
    operation: ChangeOperation
    expected_original_digest: str | None
    new_digest: str | None
    original_kind: SupportedEntryKind | None
    new_kind: SupportedEntryKind | None
    original_executable: bool | None
    new_executable: bool | None
    original_symlink_target: str | None
    new_symlink_target: str | None
    backup_relative_path: str | None
    payload_relative_path: str | None
    backup_digest: str | None
    payload_digest: str | None
    created_parent_paths: tuple[RepoPath, ...]
    target_parent_identity: str | None

    def __post_init__(self) -> None:
        if (
            type(self.order) is not int
            or self.order <= 0
            or type(self.path) is not RepoPath
            or type(self.operation) is not ChangeOperation
            or (
                self.expected_original_digest is not None
                and not _is_digest(self.expected_original_digest)
            )
            or self.new_digest is not None
            and not _is_digest(self.new_digest)
            or (
                self.original_kind is not None
                and type(self.original_kind) is not SupportedEntryKind
            )
            or (
                self.new_kind is not None
                and type(self.new_kind) is not SupportedEntryKind
            )
            or (
                self.original_executable is not None
                and type(self.original_executable) is not bool
            )
            or (
                self.new_executable is not None
                and type(self.new_executable) is not bool
            )
            or (
                self.original_symlink_target is not None
                and type(self.original_symlink_target) is not str
            )
            or (
                self.new_symlink_target is not None
                and type(self.new_symlink_target) is not str
            )
            or (
                self.backup_relative_path is not None
                and not _is_private_relative(self.backup_relative_path)
            )
            or (
                self.payload_relative_path is not None
                and not _is_private_relative(self.payload_relative_path)
            )
            or (
                self.backup_digest is not None
                and not _is_digest(self.backup_digest)
            )
            or (
                self.payload_digest is not None
                and not _is_digest(self.payload_digest)
            )
            or type(self.created_parent_paths) is not tuple
            or any(
                type(path) is not RepoPath for path in self.created_parent_paths
            )
            or tuple(
                sorted(
                    self.created_parent_paths,
                    key=lambda path: len(path.segments),
                )
            )
            != self.created_parent_paths
            or len({path.identity for path in self.created_parent_paths})
            != len(self.created_parent_paths)
            or any(
                path.segments != self.path.segments[: len(path.segments)]
                or len(path.segments) >= len(self.path.segments)
                for path in self.created_parent_paths
            )
            or (
                self.target_parent_identity is not None
                and not _is_digest(self.target_parent_identity)
            )
        ):
            raise ValueError("apply plan entry is invalid")
        original_exists = self.expected_original_digest is not None
        new_exists = self.new_digest is not None
        if (
            original_exists
            != (
                self.original_kind is not None
                and self.original_executable is not None
                and self.backup_relative_path is not None
                and self.backup_digest == self.expected_original_digest
            )
            or new_exists
            != (
                self.new_kind is not None
                and self.new_executable is not None
                and self.payload_relative_path is not None
                and self.payload_digest == self.new_digest
            )
            or self.operation is ChangeOperation.ADD
            and (original_exists or not new_exists)
            or self.operation is ChangeOperation.DELETE
            and (not original_exists or new_exists)
            or self.operation is ChangeOperation.MODIFY
            and (not original_exists or not new_exists)
        ):
            raise ValueError("apply plan entry is invalid")

    def __bool__(self) -> bool:
        raise TypeError("ApplyPlanEntry has no truth value")


def _entry_payload(entry: ApplyPlanEntry) -> dict[str, object]:
    return {
        "order": entry.order,
        "path": entry.path.canonical,
        "operation": entry.operation.value,
        "expected_original_digest": entry.expected_original_digest,
        "new_digest": entry.new_digest,
        "original_kind": (
            None if entry.original_kind is None else entry.original_kind.value
        ),
        "new_kind": None if entry.new_kind is None else entry.new_kind.value,
        "original_executable": entry.original_executable,
        "new_executable": entry.new_executable,
        "original_symlink_target": entry.original_symlink_target,
        "new_symlink_target": entry.new_symlink_target,
        "backup_relative_path": entry.backup_relative_path,
        "payload_relative_path": entry.payload_relative_path,
        "backup_digest": entry.backup_digest,
        "payload_digest": entry.payload_digest,
        "created_parent_paths": [
            path.canonical for path in entry.created_parent_paths
        ],
        "target_parent_identity": entry.target_parent_identity,
    }


def _plan_body(
    transaction_id: str,
    baseline_digest: str,
    changeset_digest: str,
    index_digest_before: str,
    target_root_identity: str,
    entries: tuple[ApplyPlanEntry, ...],
) -> dict[str, object]:
    return {
        "schema": "coding-harness:apply-plan:v1",
        "transaction_id": transaction_id,
        "baseline_digest": baseline_digest,
        "changeset_digest": changeset_digest,
        "index_digest_before": index_digest_before,
        "target_root_identity": target_root_identity,
        "entries": [_entry_payload(entry) for entry in entries],
    }


def _digest_plan_body(body: dict[str, object]) -> str:
    serialized = json.dumps(
        body, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


@dataclass(frozen=True, slots=True)
class ApplyPlan:
    transaction_id: str
    baseline_digest: str
    changeset_digest: str
    index_digest_before: str
    target_root_identity: str
    entries: tuple[ApplyPlanEntry, ...]
    digest: str

    def __post_init__(self) -> None:
        body = _plan_body(
            self.transaction_id,
            self.baseline_digest,
            self.changeset_digest,
            self.index_digest_before,
            self.target_root_identity,
            self.entries,
        )
        if (
            not _is_text(self.transaction_id)
            or not _is_digest(self.baseline_digest)
            or not _is_digest(self.changeset_digest)
            or not _is_digest(self.index_digest_before)
            or not _is_digest(self.target_root_identity)
            or type(self.entries) is not tuple
            or any(type(entry) is not ApplyPlanEntry for entry in self.entries)
            or tuple(entry.order for entry in self.entries)
            != tuple(range(1, len(self.entries) + 1))
            or tuple(sorted(self.entries, key=lambda item: item.path.canonical))
            != self.entries
            or len({entry.path.identity for entry in self.entries})
            != len(self.entries)
            or not _is_digest(self.digest)
            or self.digest != _digest_plan_body(body)
        ):
            raise ValueError("apply plan is invalid")

    def serialize(self) -> bytes:
        payload = _plan_body(
            self.transaction_id,
            self.baseline_digest,
            self.changeset_digest,
            self.index_digest_before,
            self.target_root_identity,
            self.entries,
        )
        payload["digest"] = self.digest
        return (
            json.dumps(
                payload,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")

    def __bool__(self) -> bool:
        raise TypeError("ApplyPlan has no truth value")


def make_apply_plan(
    *,
    transaction_id: str,
    baseline_digest: str,
    changeset_digest: str,
    index_digest_before: str,
    target_root_identity: str,
    entries: tuple[ApplyPlanEntry, ...],
) -> ApplyPlan:
    body = _plan_body(
        transaction_id,
        baseline_digest,
        changeset_digest,
        index_digest_before,
        target_root_identity,
        entries,
    )
    return ApplyPlan(
        transaction_id=transaction_id,
        baseline_digest=baseline_digest,
        changeset_digest=changeset_digest,
        index_digest_before=index_digest_before,
        target_root_identity=target_root_identity,
        entries=entries,
        digest=_digest_plan_body(body),
    )


def parse_apply_plan(serialized: bytes) -> ApplyPlan:
    try:
        payload = json.loads(serialized)
        if type(payload) is not dict:
            raise ValueError
        raw_entries = payload["entries"]
        if type(raw_entries) is not list or len(raw_entries) > 10_000:
            raise ValueError
        entries = tuple(
            ApplyPlanEntry(
                order=item["order"],
                path=RepoPath.parse(item["path"]),
                operation=ChangeOperation(item["operation"]),
                expected_original_digest=item["expected_original_digest"],
                new_digest=item["new_digest"],
                original_kind=(
                    None
                    if item["original_kind"] is None
                    else SupportedEntryKind(item["original_kind"])
                ),
                new_kind=(
                    None
                    if item["new_kind"] is None
                    else SupportedEntryKind(item["new_kind"])
                ),
                original_executable=item["original_executable"],
                new_executable=item["new_executable"],
                original_symlink_target=item["original_symlink_target"],
                new_symlink_target=item["new_symlink_target"],
                backup_relative_path=item["backup_relative_path"],
                payload_relative_path=item["payload_relative_path"],
                backup_digest=item["backup_digest"],
                payload_digest=item["payload_digest"],
                created_parent_paths=tuple(
                    RepoPath.parse(path)
                    for path in item["created_parent_paths"]
                ),
                target_parent_identity=item["target_parent_identity"],
            )
            for item in raw_entries
        )
        if payload.get("schema") != "coding-harness:apply-plan:v1":
            raise ValueError
        return ApplyPlan(
            transaction_id=payload["transaction_id"],
            baseline_digest=payload["baseline_digest"],
            changeset_digest=payload["changeset_digest"],
            index_digest_before=payload["index_digest_before"],
            target_root_identity=payload["target_root_identity"],
            entries=entries,
            digest=payload["digest"],
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise ValueError("apply plan is invalid") from None


@dataclass(frozen=True, slots=True)
class JournalRecord:
    order: int
    stage: JournalStage
    status: JournalStatus
    phase: ApplyPhase | None
    path: RepoPath | None
    detail: str
    evidence_digest: str | None

    def __post_init__(self) -> None:
        if (
            type(self.order) is not int
            or self.order <= 0
            or type(self.stage) is not JournalStage
            or type(self.status) is not JournalStatus
            or self.phase is not None
            and type(self.phase) is not ApplyPhase
            or self.path is not None
            and type(self.path) is not RepoPath
            or type(self.detail) is not str
            or "\0" in self.detail
            or len(self.detail.encode("utf-8")) > 1024
            or self.evidence_digest is not None
            and not _is_digest(self.evidence_digest)
        ):
            raise ValueError("journal record is invalid")

    def __bool__(self) -> bool:
        raise TypeError("JournalRecord has no truth value")


@dataclass(frozen=True, slots=True)
class ApplyResult:
    transaction_id: str
    decision: ApplyDecision
    phase: ApplyPhase | None
    task_state: TaskState
    recovery_state: RecoveryState | None
    plan: ApplyPlan | None
    journal: ApplyJournal | None
    index_digest_after: str | None
    reason: str

    def __post_init__(self) -> None:
        if (
            not _is_text(self.transaction_id)
            or type(self.decision) is not ApplyDecision
            or self.phase is not None
            and type(self.phase) is not ApplyPhase
            or type(self.task_state) is not TaskState
            or self.recovery_state is not None
            and type(self.recovery_state) is not RecoveryState
            or self.plan is not None
            and type(self.plan) is not ApplyPlan
            or self.index_digest_after is not None
            and not _is_digest(self.index_digest_after)
            or type(self.reason) is not str
            or "\0" in self.reason
        ):
            raise ValueError("apply result is invalid")

    def __bool__(self) -> bool:
        raise TypeError("ApplyResult has no truth value")


__all__ = [
    "ApplyDecision",
    "ApplyPhase",
    "ApplyPlan",
    "ApplyPlanEntry",
    "ApplyResult",
    "JournalStage",
    "JournalStatus",
    "RecoveryState",
]
