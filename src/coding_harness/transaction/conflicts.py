"""Deterministic pre-apply conflict detection for WP-13."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import os
from pathlib import Path
import stat

from coding_harness.domain.enums import TaskState
from coding_harness.workspace.changeset import (
    ChangeScope,
    ChangeSet,
    FileChange,
    compute_changeset,
)
from coding_harness.workspace.file_model import (
    InspectionStatus,
    SupportedEntry,
    SupportedEntryKind,
    inspect_supported_entry,
)
from coding_harness.workspace.manifest import BaselineEntry, BaselineManifest
from coding_harness.workspace.materialize import TaskWorkspace
from coding_harness.workspace.paths import RepoPath


_INVALID_CONFLICT_INPUT = "conflict detection failed"


def _is_digest(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_text(value: object) -> bool:
    return type(value) is str and bool(value) and "\0" not in value


class _ClosedEnum(Enum):
    def __bool__(self) -> bool:
        raise TypeError(f"{type(self).__name__} has no truth value")


class ConflictType(_ClosedEnum):
    BASELINE_MISMATCH = "BASELINE_MISMATCH"
    TARGET_CHANGED = "TARGET_CHANGED"
    DIGEST_MISMATCH = "DIGEST_MISMATCH"
    CONFIRMATION_INVALID = "CONFIRMATION_INVALID"
    ACCEPTANCE_INVALID = "ACCEPTANCE_INVALID"
    APPLY_TRANSACTION_ACTIVE = "APPLY_TRANSACTION_ACTIVE"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    POLICY_DENIED = "POLICY_DENIED"


class _UnsupportedTarget(_ClosedEnum):
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class ApplyConfirmation:
    """Immutable TXN-017 binding presented to the deterministic apply gate."""

    task_id: str
    changeset_digest: str
    baseline_manifest_digest: str
    plan_version_identity: str
    acceptance_contract_version_identity: str
    expected_state: TaskState
    idempotency_key: str

    def __post_init__(self) -> None:
        if (
            not _is_text(self.task_id)
            or not _is_digest(self.changeset_digest)
            or not _is_digest(self.baseline_manifest_digest)
            or not _is_text(self.plan_version_identity)
            or not _is_text(self.acceptance_contract_version_identity)
            or type(self.expected_state) is not TaskState
            or not _is_text(self.idempotency_key)
        ):
            raise ValueError("apply confirmation is invalid")

    def __bool__(self) -> bool:
        raise TypeError("ApplyConfirmation has no truth value")


@dataclass(frozen=True, slots=True)
class Conflict:
    conflict_type: ConflictType
    affected_paths: tuple[RepoPath, ...]
    reason: str

    def __post_init__(self) -> None:
        if (
            type(self.conflict_type) is not ConflictType
            or type(self.affected_paths) is not tuple
            or any(type(path) is not RepoPath for path in self.affected_paths)
            or tuple(sorted(self.affected_paths, key=lambda path: path.canonical))
            != self.affected_paths
            or len({path.identity for path in self.affected_paths})
            != len(self.affected_paths)
            or not _is_text(self.reason)
        ):
            raise ValueError("conflict is invalid")

    def __bool__(self) -> bool:
        raise TypeError("Conflict has no truth value")


@dataclass(frozen=True, slots=True)
class ConflictReport:
    conflicts: tuple[Conflict, ...]
    unrelated_paths: tuple[RepoPath, ...]
    apply_permitted: bool

    def __post_init__(self) -> None:
        if (
            type(self.conflicts) is not tuple
            or any(type(conflict) is not Conflict for conflict in self.conflicts)
            or type(self.unrelated_paths) is not tuple
            or any(type(path) is not RepoPath for path in self.unrelated_paths)
            or tuple(sorted(self.unrelated_paths, key=lambda path: path.canonical))
            != self.unrelated_paths
            or len({path.identity for path in self.unrelated_paths})
            != len(self.unrelated_paths)
            or type(self.apply_permitted) is not bool
            or self.apply_permitted
            != (not self.conflicts and not self.unrelated_paths)
        ):
            raise ValueError("conflict report is invalid")

    def __bool__(self) -> bool:
        raise TypeError("ConflictReport has no truth value")


@dataclass(frozen=True, slots=True)
class _ComparableSnapshot:
    digest: str
    kind: SupportedEntryKind
    executable: bool
    symlink_target: str | None


def _baseline_snapshot(entry: BaselineEntry | None) -> _ComparableSnapshot | None:
    if entry is None:
        return None
    return _ComparableSnapshot(
        digest=entry.content_digest,
        kind=entry.kind,
        executable=entry.executable,
        symlink_target=entry.symlink_target,
    )


def _final_snapshot(change: FileChange) -> _ComparableSnapshot | None:
    if change.current_digest is None:
        return None
    if (
        change.current_kind is None
        or change.current_executable is None
    ):
        raise ValueError(_INVALID_CONFLICT_INPUT)
    return _ComparableSnapshot(
        digest=change.current_digest,
        kind=change.current_kind,
        executable=change.current_executable,
        symlink_target=change.current_symlink_target,
    )


def _target_snapshot(
    target_root: Path,
    path: RepoPath,
    baseline_digest: str,
) -> _ComparableSnapshot | _UnsupportedTarget | None:
    candidate = target_root.joinpath(*path.segments)
    try:
        status = os.lstat(candidate)
    except FileNotFoundError:
        return None
    except OSError:
        return _UnsupportedTarget.UNSUPPORTED
    if not (stat.S_ISREG(status.st_mode) or stat.S_ISLNK(status.st_mode)):
        return _UnsupportedTarget.UNSUPPORTED
    inspected = inspect_supported_entry(
        target_root,
        path,
        baseline_digest=baseline_digest,
    )
    if (
        inspected.status is not InspectionStatus.SUPPORTED
        or type(inspected.entry) is not SupportedEntry
    ):
        return _UnsupportedTarget.UNSUPPORTED
    entry = inspected.entry
    digest = (
        hashlib.sha256(entry.symlink_target.encode("utf-8")).hexdigest()
        if entry.kind is SupportedEntryKind.SYMLINK
        and entry.symlink_target is not None
        else entry.content_digest
    )
    return _ComparableSnapshot(
        digest=digest,
        kind=entry.kind,
        executable=entry.executable,
        symlink_target=entry.symlink_target,
    )


def _affected_paths(changeset: ChangeSet) -> tuple[RepoPath, ...]:
    return tuple(
        change.path
        for change in changeset.changed_files
        if change.scope is ChangeScope.TARGET
    )


def _target_conflicts(
    baseline: BaselineManifest,
    changeset: ChangeSet,
    target_root: Path,
) -> tuple[Conflict, ...]:
    baseline_by_identity = {
        entry.path.identity: entry for entry in baseline.entries
    }
    conflicts: list[Conflict] = []
    for change in changeset.changed_files:
        if change.scope is not ChangeScope.TARGET:
            continue
        baseline_state = _baseline_snapshot(
            baseline_by_identity.get(change.path.identity)
        )
        final_state = _final_snapshot(change)
        current_target = _target_snapshot(
            target_root,
            change.path,
            baseline.digest,
        )
        if current_target is _UnsupportedTarget.UNSUPPORTED:
            conflicts.append(
                Conflict(
                    conflict_type=ConflictType.TARGET_CHANGED,
                    affected_paths=(change.path,),
                    reason="target path is unsupported or unreadable",
                )
            )
            continue
        if current_target not in (baseline_state, final_state):
            conflicts.append(
                Conflict(
                    conflict_type=ConflictType.TARGET_CHANGED,
                    affected_paths=(change.path,),
                    reason="target path changed since baseline",
                )
            )
    return tuple(conflicts)


def _validate_inputs(
    *,
    baseline: object,
    changeset: object,
    workspace: object,
    target_root: object,
    confirmation: object,
    current_task_id: object,
    current_plan_version_identity: object,
    current_acceptance_contract_version_identity: object,
    current_state: object,
    current_idempotency_key: object,
    acceptance_satisfied: object,
    nonterminal_apply_transaction: object,
    recovery_required: object,
    policy_denied: object,
) -> tuple[BaselineManifest, ChangeSet, TaskWorkspace, Path, ApplyConfirmation]:
    if (
        type(baseline) is not BaselineManifest
        or type(changeset) is not ChangeSet
        or type(workspace) is not TaskWorkspace
        or not isinstance(target_root, Path)
        or type(confirmation) is not ApplyConfirmation
        or not _is_text(current_task_id)
        or not _is_text(current_plan_version_identity)
        or not _is_text(current_acceptance_contract_version_identity)
        or type(current_state) is not TaskState
        or not _is_text(current_idempotency_key)
        or any(
            type(value) is not bool
            for value in (
                acceptance_satisfied,
                nonterminal_apply_transaction,
                recovery_required,
                policy_denied,
            )
        )
    ):
        raise ValueError(_INVALID_CONFLICT_INPUT)
    try:
        root_status = os.lstat(target_root)
        trusted_root = target_root.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError(_INVALID_CONFLICT_INPUT) from None
    if stat.S_ISLNK(root_status.st_mode) or not stat.S_ISDIR(root_status.st_mode):
        raise ValueError(_INVALID_CONFLICT_INPUT)
    return baseline, changeset, workspace, trusted_root, confirmation


def _conflict(
    conflict_type: ConflictType,
    affected_paths: tuple[RepoPath, ...],
    reason: str,
) -> Conflict:
    return Conflict(
        conflict_type=conflict_type,
        affected_paths=affected_paths,
        reason=reason,
    )


def detect_conflicts(
    baseline: BaselineManifest,
    changeset: ChangeSet,
    workspace: TaskWorkspace,
    target_root: Path,
    *,
    confirmation: ApplyConfirmation,
    current_task_id: str,
    current_plan_version_identity: str,
    current_acceptance_contract_version_identity: str,
    current_state: TaskState,
    current_idempotency_key: str,
    acceptance_satisfied: bool,
    nonterminal_apply_transaction: bool,
    recovery_required: bool,
    policy_denied: bool,
) -> ConflictReport:
    """Recompute current state and report blockers without merging or applying."""

    baseline, changeset, workspace, target_root, confirmation = _validate_inputs(
        baseline=baseline,
        changeset=changeset,
        workspace=workspace,
        target_root=target_root,
        confirmation=confirmation,
        current_task_id=current_task_id,
        current_plan_version_identity=current_plan_version_identity,
        current_acceptance_contract_version_identity=(
            current_acceptance_contract_version_identity
        ),
        current_state=current_state,
        current_idempotency_key=current_idempotency_key,
        acceptance_satisfied=acceptance_satisfied,
        nonterminal_apply_transaction=nonterminal_apply_transaction,
        recovery_required=recovery_required,
        policy_denied=policy_denied,
    )
    current_changeset = compute_changeset(
        baseline,
        workspace,
        target_paths=changeset.target_paths,
    )
    affected_paths = _affected_paths(current_changeset)
    conflicts: list[Conflict] = []
    baseline_matches = (
        changeset.baseline_digest == baseline.digest
        and current_changeset.baseline_digest == baseline.digest
        and confirmation.baseline_manifest_digest == baseline.digest
    )
    if not baseline_matches:
        conflicts.append(
            _conflict(
                ConflictType.BASELINE_MISMATCH,
                affected_paths,
                "baseline digest does not match current confirmation binding",
            )
        )
    confirmation_matches = (
        confirmation.task_id == current_task_id
        and confirmation.changeset_digest == changeset.digest
        and confirmation.baseline_manifest_digest == baseline.digest
        and confirmation.plan_version_identity == current_plan_version_identity
        and confirmation.acceptance_contract_version_identity
        == current_acceptance_contract_version_identity
        and confirmation.expected_state is TaskState.READY_TO_APPLY
        and current_state is TaskState.READY_TO_APPLY
        and confirmation.idempotency_key == current_idempotency_key
    )
    if not confirmation_matches:
        conflicts.append(
            _conflict(
                ConflictType.CONFIRMATION_INVALID,
                affected_paths,
                "apply confirmation binding does not match current task facts",
            )
        )
    if (
        confirmation.changeset_digest != changeset.digest
        or current_changeset.digest != changeset.digest
    ):
        conflicts.append(
            _conflict(
                ConflictType.DIGEST_MISMATCH,
                affected_paths,
                "approved change set digest is stale",
            )
        )
    if not acceptance_satisfied:
        conflicts.append(
            _conflict(
                ConflictType.ACCEPTANCE_INVALID,
                affected_paths,
                "required acceptance conditions are not satisfied",
            )
        )
    if nonterminal_apply_transaction:
        conflicts.append(
            _conflict(
                ConflictType.APPLY_TRANSACTION_ACTIVE,
                affected_paths,
                "a nonterminal apply transaction already exists",
            )
        )
    if recovery_required:
        conflicts.append(
            _conflict(
                ConflictType.RECOVERY_REQUIRED,
                affected_paths,
                "recovery is required before apply",
            )
        )
    if policy_denied:
        conflicts.append(
            _conflict(
                ConflictType.POLICY_DENIED,
                affected_paths,
                "policy denied apply",
            )
        )
    conflicts.extend(
        _target_conflicts(baseline, current_changeset, target_root)
    )
    unrelated_paths = tuple(
        change.path
        for change in current_changeset.changed_files
        if change.scope is ChangeScope.UNRELATED
    )
    ordered_conflicts = tuple(
        sorted(
            conflicts,
            key=lambda conflict: (
                conflict.conflict_type.value,
                tuple(path.canonical for path in conflict.affected_paths),
            ),
        )
    )
    return ConflictReport(
        conflicts=ordered_conflicts,
        unrelated_paths=unrelated_paths,
        apply_permitted=not ordered_conflicts and not unrelated_paths,
    )


__all__ = [
    "ApplyConfirmation",
    "ConflictReport",
    "ConflictType",
    "detect_conflicts",
]
