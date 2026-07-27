"""Deterministic Agent Change Set calculation from baseline and workspace."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import stat

from coding_harness.workspace.file_model import (
    InspectionStatus,
    SupportedEntry,
    SupportedEntryKind,
    inspect_supported_entry,
)
from coding_harness.workspace.manifest import BaselineEntry, BaselineManifest
from coding_harness.workspace.materialize import TaskWorkspace
from coding_harness.workspace.paths import RepoPath


_INVALID_CHANGESET = "change set calculation failed"
_DIGEST_LENGTH = 64
_MAX_SNAPSHOT_FILES = 10_000
_MAX_SNAPSHOT_BYTES = 64 * 1024 * 1024
_MAX_SNAPSHOT_DEPTH = 40


def _is_digest(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == _DIGEST_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


class _ClosedEnum(Enum):
    def __bool__(self) -> bool:
        raise TypeError(f"{type(self).__name__} has no truth value")


class ChangeOperation(_ClosedEnum):
    ADD = "ADD"
    MODIFY = "MODIFY"
    DELETE = "DELETE"


class ChangeScope(_ClosedEnum):
    TARGET = "TARGET"
    UNRELATED = "UNRELATED"


@dataclass(frozen=True, slots=True)
class FileChange:
    """One auditable path-level difference."""

    path: RepoPath
    operation: ChangeOperation
    scope: ChangeScope
    baseline_digest: str | None
    current_digest: str | None
    baseline_kind: SupportedEntryKind | None
    current_kind: SupportedEntryKind | None
    baseline_executable: bool | None
    current_executable: bool | None
    baseline_symlink_target: str | None
    current_symlink_target: str | None

    def __post_init__(self) -> None:
        if (
            type(self.path) is not RepoPath
            or type(self.operation) is not ChangeOperation
            or type(self.scope) is not ChangeScope
            or (
                self.baseline_digest is not None
                and not _is_digest(self.baseline_digest)
            )
            or self.current_digest is not None
            and not _is_digest(self.current_digest)
            or (
                self.baseline_kind is not None
                and type(self.baseline_kind) is not SupportedEntryKind
            )
            or (
                self.current_kind is not None
                and type(self.current_kind) is not SupportedEntryKind
            )
            or (
                self.baseline_executable is not None
                and type(self.baseline_executable) is not bool
            )
            or (
                self.current_executable is not None
                and type(self.current_executable) is not bool
            )
            or (
                self.baseline_symlink_target is not None
                and type(self.baseline_symlink_target) is not str
            )
            or (
                self.current_symlink_target is not None
                and type(self.current_symlink_target) is not str
            )
        ):
            raise ValueError("file change is invalid")
        if self.operation is ChangeOperation.ADD:
            valid = (
                self.baseline_digest is None
                and self.baseline_kind is None
                and self.baseline_executable is None
                and self.baseline_symlink_target is None
                and self.current_digest is not None
                and self.current_kind is not None
                and self.current_executable is not None
            )
        elif self.operation is ChangeOperation.DELETE:
            valid = (
                self.current_digest is None
                and self.current_kind is None
                and self.current_executable is None
                and self.current_symlink_target is None
                and self.baseline_digest is not None
                and self.baseline_kind is not None
                and self.baseline_executable is not None
            )
        else:
            valid = (
                self.baseline_digest is not None
                and self.current_digest is not None
                and self.baseline_kind is not None
                and self.current_kind is not None
                and self.baseline_executable is not None
                and self.current_executable is not None
            )
        if not valid:
            raise ValueError("file change is invalid")

    def __bool__(self) -> bool:
        raise TypeError("FileChange has no truth value")


def _change_payload(change: FileChange) -> dict[str, object]:
    return {
        "path": change.path.canonical,
        "operation": change.operation.value,
        "scope": change.scope.value,
        "baseline_digest": change.baseline_digest,
        "current_digest": change.current_digest,
        "baseline_kind": (
            None if change.baseline_kind is None else change.baseline_kind.value
        ),
        "current_kind": (
            None if change.current_kind is None else change.current_kind.value
        ),
        "baseline_executable": change.baseline_executable,
        "current_executable": change.current_executable,
        "baseline_symlink_target": change.baseline_symlink_target,
        "current_symlink_target": change.current_symlink_target,
    }


def _serialize(
    baseline_digest: str,
    target_paths: tuple[RepoPath, ...] | None,
    changes: tuple[FileChange, ...],
) -> bytes:
    payload = {
        "schema": "coding-harness:change-set:v1",
        "baseline_digest": baseline_digest,
        "target_paths": (
            None
            if target_paths is None
            else [path.canonical for path in target_paths]
        ),
        "changed_files": [_change_payload(change) for change in changes],
    }
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class ChangeSet:
    """Immutable, content-addressed Agent Change Set."""

    baseline_digest: str
    target_paths: tuple[RepoPath, ...] | None
    changed_files: tuple[FileChange, ...]
    digest: str

    def __post_init__(self) -> None:
        if (
            not _is_digest(self.baseline_digest)
            or (
                self.target_paths is not None
                and (
                    type(self.target_paths) is not tuple
                    or any(type(path) is not RepoPath for path in self.target_paths)
                    or tuple(
                        sorted(
                            self.target_paths,
                            key=lambda path: path.canonical,
                        )
                    )
                    != self.target_paths
                    or len({path.identity for path in self.target_paths})
                    != len(self.target_paths)
                )
            )
            or type(self.changed_files) is not tuple
            or any(type(change) is not FileChange for change in self.changed_files)
            or tuple(
                sorted(self.changed_files, key=lambda change: change.path.canonical)
            )
            != self.changed_files
            or len({change.path.identity for change in self.changed_files})
            != len(self.changed_files)
            or not _is_digest(self.digest)
            or self.digest
            != hashlib.sha256(
                _serialize(
                    self.baseline_digest,
                    self.target_paths,
                    self.changed_files,
                )
            ).hexdigest()
        ):
            raise ValueError("change set is invalid")

    def serialize(self) -> bytes:
        return _serialize(
            self.baseline_digest,
            self.target_paths,
            self.changed_files,
        )

    def __bool__(self) -> bool:
        raise TypeError("ChangeSet has no truth value")


@dataclass(frozen=True, slots=True)
class _EntrySnapshot:
    digest: str
    kind: SupportedEntryKind
    executable: bool
    symlink_target: str | None


def _baseline_snapshot(entry: BaselineEntry) -> _EntrySnapshot:
    return _EntrySnapshot(
        digest=entry.content_digest,
        kind=entry.kind,
        executable=entry.executable,
        symlink_target=entry.symlink_target,
    )


def _supported_snapshot(entry: SupportedEntry) -> _EntrySnapshot:
    digest = (
        hashlib.sha256(entry.symlink_target.encode("utf-8")).hexdigest()
        if entry.kind is SupportedEntryKind.SYMLINK
        and entry.symlink_target is not None
        else entry.content_digest
    )
    return _EntrySnapshot(
        digest=digest,
        kind=entry.kind,
        executable=entry.executable,
        symlink_target=entry.symlink_target,
    )


def _workspace_paths(root: Path) -> tuple[RepoPath, ...]:
    paths: list[RepoPath] = []
    scanned_entries = 0
    directory_flags = os.O_RDONLY
    directory_flags |= getattr(os, "O_CLOEXEC", 0)
    directory_flags |= getattr(os, "O_DIRECTORY", 0)
    directory_flags |= getattr(os, "O_NOFOLLOW", 0)

    def close_directory(descriptor: int) -> None:
        try:
            os.close(descriptor)
        except OSError:
            raise ValueError(_INVALID_CHANGESET) from None

    def walk(directory_descriptor: int, parent_segments: tuple[str, ...]) -> None:
        nonlocal scanned_entries
        try:
            os.stat(
                ".git",
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        except OSError:
            raise ValueError(_INVALID_CHANGESET) from None
        else:
            raise ValueError(_INVALID_CHANGESET)

        try:
            with os.scandir(directory_descriptor) as entries:
                for entry in entries:
                    scanned_entries += 1
                    if scanned_entries > _MAX_SNAPSHOT_FILES:
                        raise ValueError(
                            "workspace snapshot limit exceeded: MAX_FILES"
                        )
                    try:
                        path = RepoPath.from_segments(
                            (*parent_segments, entry.name)
                        )
                        status = entry.stat(follow_symlinks=False)
                    except (OSError, UnicodeError, ValueError):
                        raise ValueError(_INVALID_CHANGESET) from None

                    if stat.S_ISDIR(status.st_mode):
                        if len(path.segments) > _MAX_SNAPSHOT_DEPTH:
                            raise ValueError(
                                "workspace snapshot limit exceeded: MAX_DEPTH"
                            )
                        try:
                            child_descriptor = os.open(
                                entry.name,
                                directory_flags,
                                dir_fd=directory_descriptor,
                            )
                        except OSError:
                            raise ValueError(_INVALID_CHANGESET) from None
                        try:
                            current = os.fstat(child_descriptor)
                            if (
                                not stat.S_ISDIR(current.st_mode)
                                or current.st_dev != status.st_dev
                                or current.st_ino != status.st_ino
                            ):
                                raise ValueError(_INVALID_CHANGESET)
                            walk(child_descriptor, path.segments)
                        finally:
                            close_directory(child_descriptor)
                    elif stat.S_ISREG(status.st_mode) or stat.S_ISLNK(
                        status.st_mode
                    ):
                        if len(parent_segments) > _MAX_SNAPSHOT_DEPTH:
                            raise ValueError(
                                "workspace snapshot limit exceeded: MAX_DEPTH"
                            )
                        paths.append(path)
                    else:
                        raise ValueError(_INVALID_CHANGESET)
        except ValueError:
            raise
        except OSError:
            raise ValueError(_INVALID_CHANGESET) from None

    try:
        root_descriptor = os.open(root, directory_flags)
    except OSError:
        raise ValueError(_INVALID_CHANGESET) from None
    try:
        walk(root_descriptor, ())
    finally:
        close_directory(root_descriptor)
    return tuple(sorted(paths, key=lambda path: path.canonical))


def _workspace_snapshot(
    root: Path,
    baseline_digest: str,
) -> dict[str, tuple[RepoPath, _EntrySnapshot]]:
    snapshots: dict[str, tuple[RepoPath, _EntrySnapshot]] = {}
    total_bytes = 0
    for path in _workspace_paths(root):
        remaining_bytes = _MAX_SNAPSHOT_BYTES - total_bytes
        inspected = inspect_supported_entry(
            root,
            path,
            baseline_digest=baseline_digest,
            max_bytes=remaining_bytes,
        )
        if (
            inspected.status is not InspectionStatus.SUPPORTED
            or type(inspected.entry) is not SupportedEntry
        ):
            if inspected.detail == "CONTENT_LIMIT_OR_READ_FAILURE":
                raise ValueError(
                    "workspace snapshot limit exceeded: MAX_BYTES"
                )
            raise ValueError(_INVALID_CHANGESET)
        total_bytes += inspected.entry.size
        if total_bytes > _MAX_SNAPSHOT_BYTES:
            raise ValueError(
                "workspace snapshot limit exceeded: MAX_BYTES"
            )
        snapshots[path.identity] = (path, _supported_snapshot(inspected.entry))
    return snapshots


def _validate_inputs(
    baseline: object,
    workspace: object,
    target_paths: object,
) -> tuple[
    BaselineManifest,
    TaskWorkspace,
    tuple[RepoPath, ...] | None,
]:
    if type(baseline) is not BaselineManifest or type(workspace) is not TaskWorkspace:
        raise ValueError(_INVALID_CHANGESET)
    if (
        workspace.baseline_digest != baseline.digest
        or workspace.source_head != baseline.source_head
        or workspace.source_branch != baseline.source_branch
        or workspace.source_index_digest != baseline.source_index_digest
        or workspace.source_status_digest != baseline.source_status_digest
    ):
        raise ValueError(_INVALID_CHANGESET)
    if target_paths is None:
        targets = None
    elif type(target_paths) is tuple and all(
        type(path) is RepoPath for path in target_paths
    ):
        ordered_targets = tuple(
            sorted(target_paths, key=lambda path: path.canonical)
        )
        identities = tuple(path.identity for path in ordered_targets)
        if len(set(identities)) != len(identities):
            raise ValueError(_INVALID_CHANGESET)
        targets = ordered_targets
    else:
        raise ValueError(_INVALID_CHANGESET)
    try:
        root_status = os.lstat(workspace.root)
        trusted_root = workspace.root.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError(_INVALID_CHANGESET) from None
    if stat.S_ISLNK(root_status.st_mode) or not stat.S_ISDIR(root_status.st_mode):
        raise ValueError(_INVALID_CHANGESET)
    if trusted_root != workspace.root.absolute():
        raise ValueError(_INVALID_CHANGESET)
    return (
        baseline,
        workspace,
        targets,
    )


def compute_changeset(
    baseline: BaselineManifest,
    workspace: TaskWorkspace,
    *,
    target_paths: tuple[RepoPath, ...] | None = None,
) -> ChangeSet:
    """Compare the final Task Workspace with its immutable Baseline Manifest."""

    (
        baseline,
        workspace,
        targets,
    ) = _validate_inputs(
        baseline,
        workspace,
        target_paths,
    )
    baseline_by_identity = {
        entry.path.identity: (entry.path, _baseline_snapshot(entry))
        for entry in baseline.entries
    }
    current_by_identity = _workspace_snapshot(
        workspace.root,
        baseline.digest,
    )
    target_identities = (
        None
        if targets is None
        else frozenset(path.identity for path in targets)
    )
    changes: list[FileChange] = []
    for identity in sorted(
        set(baseline_by_identity) | set(current_by_identity),
        key=lambda item: (
            baseline_by_identity.get(item) or current_by_identity[item]
        )[0].canonical,
    ):
        baseline_item = baseline_by_identity.get(identity)
        current_item = current_by_identity.get(identity)
        baseline_snapshot = None if baseline_item is None else baseline_item[1]
        current_snapshot = None if current_item is None else current_item[1]
        if baseline_snapshot == current_snapshot:
            continue
        path = (baseline_item or current_item)[0]
        operation = (
            ChangeOperation.ADD
            if baseline_snapshot is None
            else (
                ChangeOperation.DELETE
                if current_snapshot is None
                else ChangeOperation.MODIFY
            )
        )
        changes.append(
            FileChange(
                path=path,
                operation=operation,
                scope=(
                    ChangeScope.TARGET
                    if target_identities is None or identity in target_identities
                    else ChangeScope.UNRELATED
                ),
                baseline_digest=(
                    None if baseline_snapshot is None else baseline_snapshot.digest
                ),
                current_digest=(
                    None if current_snapshot is None else current_snapshot.digest
                ),
                baseline_kind=(
                    None if baseline_snapshot is None else baseline_snapshot.kind
                ),
                current_kind=(
                    None if current_snapshot is None else current_snapshot.kind
                ),
                baseline_executable=(
                    None
                    if baseline_snapshot is None
                    else baseline_snapshot.executable
                ),
                current_executable=(
                    None if current_snapshot is None else current_snapshot.executable
                ),
                baseline_symlink_target=(
                    None
                    if baseline_snapshot is None
                    else baseline_snapshot.symlink_target
                ),
                current_symlink_target=(
                    None
                    if current_snapshot is None
                    else current_snapshot.symlink_target
                ),
            )
        )
    changed_files = tuple(changes)
    serialized = _serialize(
        baseline.digest,
        targets,
        changed_files,
    )
    return ChangeSet(
        baseline_digest=baseline.digest,
        target_paths=targets,
        changed_files=changed_files,
        digest=hashlib.sha256(serialized).hexdigest(),
    )


__all__ = [
    "ChangeOperation",
    "ChangeScope",
    "ChangeSet",
    "compute_changeset",
]
