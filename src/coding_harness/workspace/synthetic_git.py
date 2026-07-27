"""Task-local, non-authoritative Synthetic Git compatibility execution.

This module consumes the frozen WP-10 BaselineManifest/TaskWorkspace binding.
It does not issue authority, inspect persistence, or interact with the origin
repository.  The immutable compatibility anchor and mutable synthetic index
exist only to provide bounded status/diff/stage/unstage semantics.
"""

from __future__ import annotations

import hashlib
import os
import stat
import threading
from collections.abc import Iterable
from dataclasses import dataclass
from difflib import ndiff
from enum import Enum
from pathlib import Path

from coding_harness.workspace.file_model import (
    InspectionStatus,
    SupportedEntry,
    SupportedEntryKind,
    inspect_supported_entry,
)
from coding_harness.workspace.manifest import BaselineManifest
from coding_harness.workspace.materialize import TaskWorkspace
from coding_harness.workspace.paths import RepoPath

_MAX_EXPLICIT_PATHS = 10_000
_MAX_WORKSPACE_ENTRIES = 10_000
_MAX_CONTENT_BYTES = 8 * 1024 * 1024
_EMPTY_FEEDBACK: SyntheticGitFeedback


class _ClosedEnum(Enum):
    def __bool__(self) -> bool:
        raise TypeError(f"{type(self).__name__} has no truth value")


class GitOperation(_ClosedEnum):
    """The complete Synthetic Git compatibility execution capability set."""

    STATUS = "STATUS"
    DIFF = "DIFF"
    CACHED_DIFF = "CACHED_DIFF"
    STAGE = "STAGE"
    UNSTAGE = "UNSTAGE"


class SyntheticGitDisposition(_ClosedEnum):
    """Observable production outcomes, excluding test binding failures."""

    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    INTERNAL_FAILURE = "INTERNAL_FAILURE"


@dataclass(frozen=True, slots=True)
class SyntheticGitFeedback:
    """Bounded, non-authoritative compatibility facts."""

    paths: frozenset[str] = frozenset()
    added_lines: frozenset[str] = frozenset()
    removed_lines: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if (
            type(self.paths) is not frozenset
            or type(self.added_lines) is not frozenset
            or type(self.removed_lines) is not frozenset
            or any(type(value) is not str for value in self.paths)
            or any(type(value) is not str for value in self.added_lines)
            or any(type(value) is not str for value in self.removed_lines)
        ):
            raise ValueError("synthetic Git feedback is invalid")

    def __bool__(self) -> bool:
        raise TypeError("SyntheticGitFeedback has no truth value")


_EMPTY_FEEDBACK = SyntheticGitFeedback()


@dataclass(frozen=True, slots=True)
class SyntheticGitAcquisition:
    """Outcome of consuming the frozen WP-10 binding contract."""

    disposition: SyntheticGitDisposition
    context: object | None
    feedback: SyntheticGitFeedback = _EMPTY_FEEDBACK

    def __post_init__(self) -> None:
        if (
            type(self.disposition) is not SyntheticGitDisposition
            or type(self.feedback) is not SyntheticGitFeedback
            or (
                self.disposition is SyntheticGitDisposition.ACCEPTED
                and type(self.context) is not _SyntheticGitContext
            )
            or (
                self.disposition is not SyntheticGitDisposition.ACCEPTED
                and self.context is not None
            )
        ):
            raise ValueError("synthetic Git acquisition is invalid")

    def __bool__(self) -> bool:
        raise TypeError("SyntheticGitAcquisition has no truth value")


@dataclass(frozen=True, slots=True)
class SyntheticGitResult:
    """Observable outcome of the WP-12 execution boundary."""

    disposition: SyntheticGitDisposition
    feedback: SyntheticGitFeedback = _EMPTY_FEEDBACK

    def __post_init__(self) -> None:
        if (
            type(self.disposition) is not SyntheticGitDisposition
            or type(self.feedback) is not SyntheticGitFeedback
            or (
                self.disposition is not SyntheticGitDisposition.ACCEPTED
                and self.feedback != _EMPTY_FEEDBACK
            )
        ):
            raise ValueError("synthetic Git result is invalid")

    def __bool__(self) -> bool:
        raise TypeError("SyntheticGitResult has no truth value")


@dataclass(frozen=True, slots=True)
class _Snapshot:
    content: bytes
    executable: bool
    kind: SupportedEntryKind
    symlink_target: str | None

    def __post_init__(self) -> None:
        if (
            type(self.content) is not bytes
            or type(self.executable) is not bool
            or type(self.kind) is not SupportedEntryKind
            or (
                self.kind is SupportedEntryKind.REGULAR_FILE
                and self.symlink_target is not None
            )
            or (
                self.kind is SupportedEntryKind.SYMLINK
                and (
                    type(self.symlink_target) is not str
                    or not self.symlink_target
                    or self.executable
                )
            )
        ):
            raise ValueError("synthetic Git snapshot is invalid")


@dataclass(frozen=True, slots=True)
class _AnchorEntry:
    path: RepoPath
    snapshot: _Snapshot


@dataclass(frozen=True, slots=True)
class _SyntheticAnchor:
    baseline_digest: str
    entries: tuple[_AnchorEntry, ...]

    def __post_init__(self) -> None:
        if (
            type(self.baseline_digest) is not str
            or type(self.entries) is not tuple
            or any(type(entry) is not _AnchorEntry for entry in self.entries)
            or tuple(
                sorted(self.entries, key=lambda entry: entry.path.canonical)
            )
            != self.entries
            or len({entry.path.identity for entry in self.entries})
            != len(self.entries)
        ):
            raise ValueError("synthetic Git anchor is invalid")


class _SyntheticGitContext:
    """Opaque task-local state; neither this object nor its contents authorize."""

    __slots__ = (
        "_anchor",
        "_index",
        "_lock",
        "_root",
        "_root_device",
        "_root_inode",
    )

    def __init__(
        self,
        anchor: _SyntheticAnchor,
        root: Path,
        root_device: int,
        root_inode: int,
    ) -> None:
        self._anchor = anchor
        self._index = {
            entry.path.canonical: entry.snapshot for entry in anchor.entries
        }
        self._lock = threading.RLock()
        self._root = root
        self._root_device = root_device
        self._root_inode = root_inode

    def __bool__(self) -> bool:
        raise TypeError("Synthetic Git compatibility context has no truth value")


class _RejectedOperation(Exception):
    pass


class _UnexpectedOperationFailure(Exception):
    pass


@dataclass(frozen=True, slots=True)
class _ReadSnapshot:
    present: bool
    snapshot: _Snapshot | None

    def __post_init__(self) -> None:
        if (
            type(self.present) is not bool
            or (self.present and type(self.snapshot) is not _Snapshot)
            or (not self.present and self.snapshot is not None)
        ):
            raise ValueError("synthetic Git read result is invalid")


def _accepted_acquisition(context: _SyntheticGitContext) -> SyntheticGitAcquisition:
    return SyntheticGitAcquisition(
        disposition=SyntheticGitDisposition.ACCEPTED,
        context=context,
    )


def _rejected_acquisition() -> SyntheticGitAcquisition:
    return SyntheticGitAcquisition(
        disposition=SyntheticGitDisposition.REJECTED,
        context=None,
    )


def _failed_acquisition() -> SyntheticGitAcquisition:
    return SyntheticGitAcquisition(
        disposition=SyntheticGitDisposition.INTERNAL_FAILURE,
        context=None,
    )


def _accepted_result(
    feedback: SyntheticGitFeedback = _EMPTY_FEEDBACK,
) -> SyntheticGitResult:
    return SyntheticGitResult(
        disposition=SyntheticGitDisposition.ACCEPTED,
        feedback=feedback,
    )


def _rejected_result() -> SyntheticGitResult:
    return SyntheticGitResult(disposition=SyntheticGitDisposition.REJECTED)


def _failed_result() -> SyntheticGitResult:
    return SyntheticGitResult(
        disposition=SyntheticGitDisposition.INTERNAL_FAILURE,
    )


def _binding_matches(
    baseline: BaselineManifest,
    workspace: TaskWorkspace,
) -> bool:
    return (
        workspace.baseline_digest == baseline.digest
        and workspace.source_head == baseline.source_head
        and workspace.source_branch == baseline.source_branch
        and workspace.source_index_digest == baseline.source_index_digest
        and workspace.source_status_digest == baseline.source_status_digest
    )


def _anchor_from_baseline(baseline: BaselineManifest) -> _SyntheticAnchor:
    return _SyntheticAnchor(
        baseline_digest=baseline.digest,
        entries=tuple(
            _AnchorEntry(
                path=entry.path,
                snapshot=_Snapshot(
                    content=bytes(entry.content),
                    executable=entry.executable,
                    kind=entry.kind,
                    symlink_target=entry.symlink_target,
                ),
            )
            for entry in baseline.entries
        ),
    )


def acquire_synthetic_git(
    baseline: object,
    workspace: object,
) -> SyntheticGitAcquisition:
    """Consume a matching WP-10 binding without reissuing its authority."""

    if type(baseline) is not BaselineManifest or type(workspace) is not TaskWorkspace:
        return _rejected_acquisition()
    if not _binding_matches(baseline, workspace):
        return _rejected_acquisition()
    try:
        root_status = os.lstat(workspace.root)
    except FileNotFoundError:
        return _rejected_acquisition()
    except OSError:
        return _failed_acquisition()
    if stat.S_ISLNK(root_status.st_mode) or not stat.S_ISDIR(root_status.st_mode):
        return _rejected_acquisition()
    try:
        trusted_root = workspace.root.resolve(strict=True)
        anchor = _anchor_from_baseline(baseline)
        context = _SyntheticGitContext(
            anchor=anchor,
            root=trusted_root,
            root_device=root_status.st_dev,
            root_inode=root_status.st_ino,
        )
    except (OSError, RuntimeError):
        return _failed_acquisition()
    # This public boundary must isolate unexpected production failures from
    # ordinary security rejection without exposing internal exception details.
    except Exception:  # noqa: BLE001
        return _failed_acquisition()
    return _accepted_acquisition(context)


def _root_is_current(context: _SyntheticGitContext) -> bool:
    try:
        status = os.lstat(context._root)
    except OSError:
        return False
    return (
        stat.S_ISDIR(status.st_mode)
        and not stat.S_ISLNK(status.st_mode)
        and status.st_dev == context._root_device
        and status.st_ino == context._root_inode
    )


def _parse_explicit_paths(paths: object) -> tuple[RepoPath, ...]:
    if type(paths) is not tuple or not paths or len(paths) > _MAX_EXPLICIT_PATHS:
        raise _RejectedOperation
    parsed: list[RepoPath] = []
    identities: set[str] = set()
    for value in paths:
        try:
            path = RepoPath.parse(value)
        except (TypeError, ValueError):
            raise _RejectedOperation from None
        if ".git" in path.segments or path.identity in identities:
            raise _RejectedOperation
        identities.add(path.identity)
        parsed.append(path)
    return tuple(parsed)


def _validate_no_options(options: object) -> None:
    if type(options) is not tuple or options:
        raise _RejectedOperation


def _snapshot_from_supported(
    root: Path,
    path: RepoPath,
    entry: SupportedEntry,
) -> _Snapshot:
    candidate = root.joinpath(*path.segments)
    try:
        content = candidate.read_bytes()
    except OSError:
        raise _UnexpectedOperationFailure from None
    if hashlib.sha256(content).hexdigest() != entry.content_digest:
        raise _UnexpectedOperationFailure
    repeated = inspect_supported_entry(
        root,
        path,
        baseline_digest=entry.baseline_digest,
        max_bytes=_MAX_CONTENT_BYTES,
    )
    if (
        repeated.status is not InspectionStatus.SUPPORTED
        or repeated.entry != entry
    ):
        raise _UnexpectedOperationFailure
    return _Snapshot(
        content=content,
        executable=entry.executable,
        kind=entry.kind,
        symlink_target=entry.symlink_target,
    )


def _read_workspace_snapshot(
    context: _SyntheticGitContext,
    path: RepoPath,
) -> _ReadSnapshot:
    candidate = context._root.joinpath(*path.segments)
    try:
        os.lstat(candidate)
    except FileNotFoundError:
        return _ReadSnapshot(present=False, snapshot=None)
    except OSError:
        raise _UnexpectedOperationFailure from None
    inspected = inspect_supported_entry(
        context._root,
        path,
        baseline_digest=context._anchor.baseline_digest,
        max_bytes=_MAX_CONTENT_BYTES,
    )
    if (
        inspected.status is not InspectionStatus.SUPPORTED
        or type(inspected.entry) is not SupportedEntry
    ):
        raise _RejectedOperation
    return _ReadSnapshot(
        present=True,
        snapshot=_snapshot_from_supported(
            context._root,
            path,
            inspected.entry,
        ),
    )


def _scan_workspace_paths(root: Path) -> tuple[RepoPath, ...]:
    pending = [root]
    paths: list[RepoPath] = []
    inspected = 0
    while pending:
        current = pending.pop()
        try:
            iterator = os.scandir(current)
        except OSError:
            raise _UnexpectedOperationFailure from None
        with iterator:
            for entry in iterator:
                inspected += 1
                if inspected > _MAX_WORKSPACE_ENTRIES:
                    raise _RejectedOperation
                if entry.name == ".git":
                    raise _RejectedOperation
                try:
                    entry_status = entry.stat(follow_symlinks=False)
                except OSError:
                    raise _UnexpectedOperationFailure from None
                entry_path = Path(entry.path)
                if stat.S_ISDIR(entry_status.st_mode):
                    pending.append(entry_path)
                    continue
                try:
                    relative = entry_path.relative_to(root).as_posix()
                    paths.append(RepoPath.parse(relative))
                except (TypeError, ValueError):
                    raise _RejectedOperation from None
    return tuple(sorted(paths, key=lambda path: path.canonical))


def _anchor_snapshots(context: _SyntheticGitContext) -> dict[str, _Snapshot]:
    return {
        entry.path.canonical: entry.snapshot for entry in context._anchor.entries
    }


def _line_changes(
    before: _Snapshot | None,
    after: _Snapshot | None,
) -> tuple[set[str], set[str]]:
    before_lines = (
        []
        if before is None
        else before.content.decode("utf-8", errors="replace").splitlines()
    )
    after_lines = (
        []
        if after is None
        else after.content.decode("utf-8", errors="replace").splitlines()
    )
    added: set[str] = set()
    removed: set[str] = set()
    for line in ndiff(before_lines, after_lines):
        if line.startswith("+ "):
            added.add(line[2:])
        elif line.startswith("- "):
            removed.add(line[2:])
    return added, removed


def _feedback_between(
    before: dict[str, _Snapshot],
    after: dict[str, _Snapshot],
) -> SyntheticGitFeedback:
    changed_paths: set[str] = set()
    added_lines: set[str] = set()
    removed_lines: set[str] = set()
    for path in sorted(set(before) | set(after)):
        before_snapshot = before.get(path)
        after_snapshot = after.get(path)
        if before_snapshot == after_snapshot:
            continue
        changed_paths.add(path)
        added, removed = _line_changes(before_snapshot, after_snapshot)
        added_lines.update(added)
        removed_lines.update(removed)
    return SyntheticGitFeedback(
        paths=frozenset(changed_paths),
        added_lines=frozenset(added_lines),
        removed_lines=frozenset(removed_lines),
    )


def _worktree_snapshots(
    context: _SyntheticGitContext,
    paths: Iterable[str],
) -> dict[str, _Snapshot]:
    snapshots: dict[str, _Snapshot] = {}
    for canonical in paths:
        try:
            path = RepoPath.parse(canonical)
        except (TypeError, ValueError):
            raise _UnexpectedOperationFailure from None
        read = _read_workspace_snapshot(context, path)
        if read.present:
            assert type(read.snapshot) is _Snapshot
            snapshots[canonical] = read.snapshot
    return snapshots


def _status(context: _SyntheticGitContext) -> SyntheticGitFeedback:
    anchor = _anchor_snapshots(context)
    cached = _feedback_between(anchor, context._index)
    workspace_paths = _scan_workspace_paths(context._root)
    relevant = set(context._index)
    relevant.update(path.canonical for path in workspace_paths)
    worktree = _worktree_snapshots(context, relevant)
    unstaged = _feedback_between(context._index, worktree)
    return SyntheticGitFeedback(paths=cached.paths | unstaged.paths)


def _diff(context: _SyntheticGitContext) -> SyntheticGitFeedback:
    worktree = _worktree_snapshots(context, context._index)
    return _feedback_between(context._index, worktree)


def _cached_diff(context: _SyntheticGitContext) -> SyntheticGitFeedback:
    return _feedback_between(_anchor_snapshots(context), context._index)


def _stage(
    context: _SyntheticGitContext,
    paths: tuple[RepoPath, ...],
) -> SyntheticGitFeedback:
    anchor = _anchor_snapshots(context)
    staged: dict[str, _Snapshot | None] = {}
    for path in paths:
        read = _read_workspace_snapshot(context, path)
        if not read.present and (
            path.canonical not in anchor and path.canonical not in context._index
        ):
            raise _RejectedOperation
        staged[path.canonical] = read.snapshot
    for canonical, snapshot in staged.items():
        if snapshot is None:
            context._index.pop(canonical, None)
        else:
            context._index[canonical] = snapshot
    return SyntheticGitFeedback(paths=frozenset(staged))


def _unstage(
    context: _SyntheticGitContext,
    paths: tuple[RepoPath, ...],
) -> SyntheticGitFeedback:
    anchor = _anchor_snapshots(context)
    if any(
        path.canonical not in anchor and path.canonical not in context._index
        for path in paths
    ):
        raise _RejectedOperation
    for path in paths:
        if path.canonical in anchor:
            context._index[path.canonical] = anchor[path.canonical]
        else:
            context._index.pop(path.canonical, None)
    return SyntheticGitFeedback(
        paths=frozenset(path.canonical for path in paths),
    )


class SyntheticGit:
    """Real WP-12 semantic execution boundary."""

    @staticmethod
    def operation_capabilities() -> tuple[GitOperation, ...]:
        return (
            GitOperation.STATUS,
            GitOperation.DIFF,
            GitOperation.CACHED_DIFF,
            GitOperation.STAGE,
            GitOperation.UNSTAGE,
        )

    @staticmethod
    def run(
        context: object,
        operation: object,
        *,
        paths: object = (),
        options: object = (),
    ) -> SyntheticGitResult:
        if type(context) is not _SyntheticGitContext:
            return _rejected_result()
        if type(operation) is not GitOperation:
            return _rejected_result()
        try:
            with context._lock:
                if not _root_is_current(context):
                    raise _RejectedOperation
                _validate_no_options(options)
                if operation in {
                    GitOperation.STATUS,
                    GitOperation.DIFF,
                    GitOperation.CACHED_DIFF,
                }:
                    if type(paths) is not tuple or paths:
                        raise _RejectedOperation
                    if operation is GitOperation.STATUS:
                        feedback = _status(context)
                    elif operation is GitOperation.DIFF:
                        feedback = _diff(context)
                    else:
                        feedback = _cached_diff(context)
                else:
                    parsed = _parse_explicit_paths(paths)
                    if operation is GitOperation.STAGE:
                        feedback = _stage(context, parsed)
                    else:
                        feedback = _unstage(context, parsed)
        except _RejectedOperation:
            return _rejected_result()
        except _UnexpectedOperationFailure:
            return _failed_result()
        # Unexpected implementation failures are observable only through the
        # distinct INTERNAL_FAILURE disposition, never as REJECTED.
        except Exception:  # noqa: BLE001
            return _failed_result()
        return _accepted_result(feedback)


__all__ = [
    "GitOperation",
    "SyntheticGit",
    "SyntheticGitAcquisition",
    "SyntheticGitDisposition",
    "SyntheticGitFeedback",
    "SyntheticGitResult",
    "acquire_synthetic_git",
]
