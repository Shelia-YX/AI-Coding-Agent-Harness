"""Durable filesystem apply, deterministic rollback, and final verification."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import os
from pathlib import Path
import stat

from coding_harness.domain.enums import TaskState
from coding_harness.transaction.conflicts import (
    ApplyConfirmation,
    detect_conflicts,
)
from coding_harness.transaction.journal import (
    ApplyJournal,
    has_blocking_transaction,
)
from coding_harness.transaction.models import (
    ApplyDecision,
    ApplyPhase,
    ApplyPlan,
    ApplyPlanEntry,
    ApplyResult,
    JournalStage,
    JournalStatus,
    RecoveryState,
    make_apply_plan,
)
from coding_harness.workspace.changeset import (
    ChangeOperation,
    ChangeScope,
    ChangeSet,
    compute_changeset,
)
from coding_harness.workspace.file_model import SupportedEntryKind
from coding_harness.workspace.manifest import BaselineManifest, _run_git
from coding_harness.workspace.materialize import TaskWorkspace
from coding_harness.workspace.paths import RepoPath


class UncertainEffectError(RuntimeError):
    """Raised only when the caller cannot prove whether a target effect occurred."""


class _ApplyFailure(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class _Snapshot:
    content: bytes
    digest: str
    kind: SupportedEntryKind
    executable: bool
    symlink_target: str | None


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _directory_status_identity(status: os.stat_result) -> str:
    return _digest(f"{status.st_dev}:{status.st_ino}".encode("ascii"))


def _valid_transaction_id(value: object) -> bool:
    if type(value) is not str or not value or "\0" in value:
        return False
    try:
        return len(value.encode("utf-8", errors="strict")) <= 1024
    except UnicodeError:
        return False


def _quarantine_name(transaction_id: str, path: RepoPath) -> str:
    identity = _digest(
        (transaction_id + "\0" + path.identity).encode("utf-8", errors="strict")
    )
    return ".coding-harness-old-" + identity


def _temporary_name(
    transaction_id: str,
    path: RepoPath,
    digest: str,
) -> str:
    identity = _digest(
        (
            transaction_id
            + "\0"
            + path.identity
            + "\0"
            + digest
        ).encode("utf-8", errors="strict")
    )
    return ".coding-harness-new-" + identity


def _trusted_root(root: Path) -> Path:
    if not isinstance(root, Path):
        raise ValueError("apply transaction is invalid")
    try:
        status = os.lstat(root)
        resolved = root.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError("apply transaction is invalid") from None
    if (
        stat.S_ISLNK(status.st_mode)
        or not stat.S_ISDIR(status.st_mode)
        or resolved != root.absolute()
    ):
        raise ValueError("apply transaction is invalid")
    return resolved


_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)


def _open_parent_fd(
    root: Path,
    path: RepoPath,
    *,
    create: bool = False,
    allowed_created: tuple[RepoPath, ...] = (),
    created: list[tuple[RepoPath, str]] | None = None,
    opened_parents: list[tuple[RepoPath, str]] | None = None,
    root_identity: list[str] | None = None,
) -> tuple[int, str]:
    allowed = {item.identity for item in allowed_created}
    try:
        descriptor = os.open(root, _DIRECTORY_FLAGS)
    except OSError:
        raise _ApplyFailure("target root is unsafe") from None
    root_status = os.fstat(descriptor)
    if root_identity is not None:
        root_identity.append(_directory_status_identity(root_status))
    traversed: list[str] = []
    try:
        for segment in path.segments[:-1]:
            traversed.append(segment)
            current_path = RepoPath.from_segments(tuple(traversed))
            was_created = False
            try:
                child = os.open(segment, _DIRECTORY_FLAGS, dir_fd=descriptor)
            except FileNotFoundError:
                if not create or current_path.identity not in allowed:
                    raise
                os.mkdir(segment, 0o755, dir_fd=descriptor)
                os.fsync(descriptor)
                child = os.open(segment, _DIRECTORY_FLAGS, dir_fd=descriptor)
                was_created = True
            status = os.fstat(child)
            if not stat.S_ISDIR(status.st_mode):
                os.close(child)
                raise _ApplyFailure("target parent is unsafe")
            identity = _directory_status_identity(status)
            if opened_parents is not None:
                opened_parents.append((current_path, identity))
            if was_created and created is not None:
                created.append((current_path, identity))
            os.close(descriptor)
            descriptor = child
        return descriptor, path.segments[-1]
    except BaseException:
        os.close(descriptor)
        raise


def _read_regular(
    parent_descriptor: int,
    name: str,
    expected: os.stat_result,
) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    try:
        status = os.fstat(descriptor)
        if (
            not stat.S_ISREG(status.st_mode)
            or status.st_dev != expected.st_dev
            or status.st_ino != expected.st_ino
            or status.st_size > 8 * 1024 * 1024
        ):
            raise _ApplyFailure("unsupported target entry")
        chunks: list[bytes] = []
        remaining = status.st_size + 1
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        if len(content) != status.st_size:
            raise _ApplyFailure("target changed during inspection")
        repeated = os.fstat(descriptor)
        if (
            repeated.st_dev != status.st_dev
            or repeated.st_ino != status.st_ino
            or repeated.st_size != status.st_size
            or repeated.st_mtime_ns != status.st_mtime_ns
        ):
            raise _ApplyFailure("target changed during inspection")
        return content, repeated
    finally:
        os.close(descriptor)


def _snapshot_at(parent_descriptor: int, name: str) -> _Snapshot | None:
    try:
        try:
            status = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            return None
        if stat.S_ISREG(status.st_mode):
            content, read_status = _read_regular(
                parent_descriptor,
                name,
                status,
            )
            return _Snapshot(
                content=content,
                digest=_digest(content),
                kind=SupportedEntryKind.REGULAR_FILE,
                executable=bool(read_status.st_mode & 0o111),
                symlink_target=None,
            )
        if stat.S_ISLNK(status.st_mode):
            try:
                target = os.readlink(name, dir_fd=parent_descriptor)
                encoded = target.encode("utf-8", errors="strict")
                repeated = os.stat(
                    name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
            except (OSError, UnicodeError):
                raise _ApplyFailure("target symlink is unreadable") from None
            if (
                repeated.st_dev != status.st_dev
                or repeated.st_ino != status.st_ino
                or repeated.st_mtime_ns != status.st_mtime_ns
            ):
                raise _ApplyFailure("target changed during inspection")
            return _Snapshot(
                content=encoded,
                digest=_digest(encoded),
                kind=SupportedEntryKind.SYMLINK,
                executable=False,
                symlink_target=target,
            )
        raise _ApplyFailure("unsupported target entry")
    except OSError:
        raise _ApplyFailure("target is unreadable") from None


def _snapshot(root: Path, path: RepoPath) -> _Snapshot | None:
    try:
        parent_descriptor, name = _open_parent_fd(root, path)
    except FileNotFoundError:
        return None
    except (OSError, _ApplyFailure):
        raise _ApplyFailure("target is unreadable") from None
    try:
        return _snapshot_at(parent_descriptor, name)
    finally:
        os.close(parent_descriptor)


def _snapshot_matches(snapshot: _Snapshot | None, entry: ApplyPlanEntry, *, new: bool) -> bool:
    expected_digest = entry.new_digest if new else entry.expected_original_digest
    expected_kind = entry.new_kind if new else entry.original_kind
    expected_executable = (
        entry.new_executable if new else entry.original_executable
    )
    expected_target = (
        entry.new_symlink_target if new else entry.original_symlink_target
    )
    if expected_digest is None:
        return snapshot is None
    return (
        snapshot is not None
        and snapshot.digest == expected_digest
        and snapshot.kind is expected_kind
        and snapshot.executable == expected_executable
        and snapshot.symlink_target == expected_target
    )


def _workspace_payload(workspace: TaskWorkspace, change) -> bytes | None:
    if change.current_digest is None:
        return None
    current = _snapshot(_trusted_root(workspace.root), change.path)
    if (
        current is None
        or current.kind is not change.current_kind
        or current.executable != change.current_executable
        or current.symlink_target != change.current_symlink_target
    ):
        raise ValueError("apply transaction is invalid")
    content = current.content
    if _digest(content) != change.current_digest:
        raise ValueError("apply transaction is invalid")
    return content


def _index_digest(root: Path) -> str:
    return _digest(_run_git(root, "ls-files", "--stage", "-z"))


def _write_regular_atomic(
    parent_descriptor: int,
    name: str,
    content: bytes,
    executable: bool,
    temporary: str,
) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    temporary_exists = False
    try:
        descriptor = os.open(
            temporary,
            flags,
            0o600,
            dir_fd=parent_descriptor,
        )
        temporary_exists = True
        remaining = memoryview(content)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("short write")
            remaining = remaining[written:]
        os.fchmod(descriptor, 0o755 if executable else 0o644)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.link(
            temporary,
            name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        os.unlink(temporary, dir_fd=parent_descriptor)
        temporary_exists = False
        os.fsync(parent_descriptor)
    except BaseException:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if temporary_exists:
            try:
                os.unlink(temporary, dir_fd=parent_descriptor)
                os.fsync(parent_descriptor)
            except OSError:
                pass
        raise


def _write_symlink_atomic(
    parent_descriptor: int,
    name: str,
    target: str,
) -> None:
    try:
        os.symlink(target, name, dir_fd=parent_descriptor)
        os.fsync(parent_descriptor)
    except BaseException:
        raise


def _restore_quarantined(
    parent_descriptor: int,
    name: str,
    quarantine: str,
    snapshot: _Snapshot,
) -> bool:
    try:
        if snapshot.kind is SupportedEntryKind.REGULAR_FILE:
            os.link(
                quarantine,
                name,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        else:
            assert snapshot.symlink_target is not None
            os.symlink(
                snapshot.symlink_target,
                name,
                dir_fd=parent_descriptor,
            )
        os.unlink(quarantine, dir_fd=parent_descriptor)
        os.fsync(parent_descriptor)
        return True
    except OSError:
        return False


def _conditional_leaf_effect(
    parent_descriptor: int,
    name: str,
    expected: _Snapshot | None,
    desired: _Snapshot | None,
    quarantine: str,
    temporary: str | None,
) -> None:
    quarantined: _Snapshot | None = None
    if expected is not None:
        try:
            os.link(
                name,
                quarantine,
                src_dir_fd=parent_descriptor,
                dst_dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            os.fsync(parent_descriptor)
            quarantined = _snapshot_at(parent_descriptor, quarantine)
            if quarantined != expected:
                os.unlink(quarantine, dir_fd=parent_descriptor)
                os.fsync(parent_descriptor)
                raise UncertainEffectError(
                    "target leaf changed before publish"
                )
            os.unlink(name, dir_fd=parent_descriptor)
            os.fsync(parent_descriptor)
        except BaseException as error:
            raise UncertainEffectError(
                "target leaf could not be quarantined"
            ) from error
    else:
        if _snapshot_at(parent_descriptor, name) is not None:
            raise UncertainEffectError("target leaf appeared before publish")
        if _snapshot_at(parent_descriptor, quarantine) is not None:
            raise UncertainEffectError("target quarantine already exists")

    try:
        if desired is not None:
            if desired.kind is SupportedEntryKind.REGULAR_FILE:
                _write_regular_atomic(
                    parent_descriptor,
                    name,
                    desired.content,
                    desired.executable,
                    temporary,
                )
            elif (
                desired.kind is SupportedEntryKind.SYMLINK
                and desired.symlink_target is not None
            ):
                _write_symlink_atomic(
                    parent_descriptor,
                    name,
                    desired.symlink_target,
                )
            else:
                raise _ApplyFailure("payload type is invalid")
        if quarantined is not None:
            os.unlink(quarantine, dir_fd=parent_descriptor)
            os.fsync(parent_descriptor)
    except BaseException as error:
        if (
            quarantined is not None
            and _restore_quarantined(
                parent_descriptor,
                name,
                quarantine,
                quarantined,
            )
        ):
            raise _ApplyFailure("conditional target publish failed") from error
        raise UncertainEffectError(
            "conditional target publish cannot be restored"
        ) from error


def _directory_exists(root: Path, path: RepoPath) -> bool:
    try:
        parent_descriptor, name = _open_parent_fd(root, path)
    except FileNotFoundError:
        return False
    try:
        try:
            status = os.stat(
                name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return False
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
            raise _ApplyFailure("target parent is unsafe")
        return True
    finally:
        os.close(parent_descriptor)


def _missing_parent_paths(root: Path, path: RepoPath) -> tuple[RepoPath, ...]:
    missing: list[RepoPath] = []
    ancestor_missing = False
    for length in range(1, len(path.segments)):
        parent = RepoPath.from_segments(path.segments[:length])
        if ancestor_missing or not _directory_exists(root, parent):
            ancestor_missing = True
            missing.append(parent)
    return tuple(missing)


def _existing_parent_identity(root: Path, path: RepoPath) -> str | None:
    try:
        parent_descriptor, _ = _open_parent_fd(root, path)
    except FileNotFoundError:
        return None
    try:
        status = os.fstat(parent_descriptor)
        if not stat.S_ISDIR(status.st_mode):
            raise _ApplyFailure("target parent is unsafe")
        return _directory_status_identity(status)
    finally:
        os.close(parent_descriptor)


def _created_parents_absent(root: Path, entry: ApplyPlanEntry) -> bool:
    return all(
        not _directory_exists(root, path)
        for path in entry.created_parent_paths
    )


def _directory_identity(root: Path, path: RepoPath) -> str:
    parent_descriptor, name = _open_parent_fd(root, path)
    try:
        status = os.stat(
            name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
            raise _ApplyFailure("created parent was replaced")
        return _directory_status_identity(status)
    finally:
        os.close(parent_descriptor)


def _remove_created_parents(
    root: Path,
    entry: ApplyPlanEntry,
    evidence: dict[str, str] | None = None,
    *,
    allow_unverified: bool = False,
) -> None:
    for path in reversed(entry.created_parent_paths):
        expected_identity = None if evidence is None else evidence.get(path.identity)
        if expected_identity is None and not allow_unverified:
            continue
        try:
            parent_descriptor, name = _open_parent_fd(root, path)
        except FileNotFoundError:
            continue
        try:
            try:
                status = os.stat(
                    name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                if (
                    stat.S_ISLNK(status.st_mode)
                    or not stat.S_ISDIR(status.st_mode)
                    or (
                        expected_identity is not None
                        and _directory_status_identity(status)
                        != expected_identity
                    )
                ):
                    continue
                os.rmdir(name, dir_fd=parent_descriptor)
                os.fsync(parent_descriptor)
            except FileNotFoundError:
                pass
            except OSError:
                # Never remove a directory populated or replaced by the user.
                pass
        finally:
            os.close(parent_descriptor)


def _publish_entry(
    target_root: Path,
    entry: ApplyPlanEntry,
    journal: ApplyJournal,
) -> tuple[tuple[RepoPath, str], ...]:
    created: list[tuple[RepoPath, str]] = []
    opened_parents: list[tuple[RepoPath, str]] = []
    root_identity: list[str] = []

    def named_chain_matches() -> bool:
        try:
            current_root = os.stat(target_root, follow_symlinks=False)
            return (
                bool(root_identity)
                and _directory_status_identity(current_root) == root_identity[0]
                and all(
                    _directory_identity(target_root, path) == identity
                    for path, identity in opened_parents
                )
            )
        except (OSError, ValueError, _ApplyFailure):
            return False

    try:
        parent_descriptor, name = _open_parent_fd(
            target_root,
            entry.path,
            create=entry.new_digest is not None,
            allowed_created=entry.created_parent_paths,
            created=created,
            opened_parents=opened_parents,
            root_identity=root_identity,
        )
        try:
            if not named_chain_matches():
                raise UncertainEffectError(
                    "target parent chain changed before publish"
                )
            expected = _snapshot_at(parent_descriptor, name)
            if not _snapshot_matches(expected, entry, new=False):
                raise UncertainEffectError("target leaf changed before publish")
            desired = None
            if entry.new_digest is not None:
                assert entry.payload_relative_path is not None
                try:
                    payload = journal.read_blob(entry.payload_relative_path)
                except (OSError, ValueError) as error:
                    raise UncertainEffectError(
                        "transaction payload is unavailable"
                    ) from error
                if _digest(payload) != entry.new_digest:
                    raise _ApplyFailure("payload verification failed")
                desired = _Snapshot(
                    content=payload,
                    digest=entry.new_digest,
                    kind=entry.new_kind,
                    executable=entry.new_executable,
                    symlink_target=entry.new_symlink_target,
                )
            _conditional_leaf_effect(
                parent_descriptor,
                name,
                expected,
                desired,
                _quarantine_name(journal.transaction_id, entry.path),
                (
                    None
                    if entry.new_digest is None
                    else _temporary_name(
                        journal.transaction_id,
                        entry.path,
                        entry.new_digest,
                    )
                ),
            )
            if not named_chain_matches():
                raise UncertainEffectError(
                    "target parent chain changed during publish"
                )
        finally:
            os.close(parent_descriptor)
        return tuple(created)
    except BaseException:
        temporary_entry = replace(
            entry,
            created_parent_paths=tuple(path for path, _ in created),
        )
        _remove_created_parents(
            target_root,
            temporary_entry,
            {path.identity: identity for path, identity in created},
        )
        raise


def _restore_entry(
    target_root: Path,
    entry: ApplyPlanEntry,
    journal: ApplyJournal,
    *,
    created_parent_evidence: dict[str, str] | None = None,
) -> None:
    opened_parents: list[tuple[RepoPath, str]] = []
    root_identity: list[str] = []
    parent_descriptor, name = _open_parent_fd(
        target_root,
        entry.path,
        create=entry.expected_original_digest is not None,
        opened_parents=opened_parents,
        root_identity=root_identity,
    )

    def named_chain_matches() -> bool:
        try:
            current_root = os.stat(target_root, follow_symlinks=False)
            return (
                bool(root_identity)
                and _directory_status_identity(current_root) == root_identity[0]
                and all(
                    _directory_identity(target_root, path) == identity
                    for path, identity in opened_parents
                )
            )
        except (OSError, ValueError, _ApplyFailure):
            return False

    try:
        if not named_chain_matches():
            raise UncertainEffectError(
                "target parent chain changed before rollback"
            )
        current = _snapshot_at(parent_descriptor, name)
        if _snapshot_matches(current, entry, new=False):
            pass
        else:
            if not _snapshot_matches(current, entry, new=True):
                raise UncertainEffectError(
                    "target leaf changed before rollback"
                )
            desired = None
            if entry.expected_original_digest is not None:
                assert entry.backup_relative_path is not None
                try:
                    content = journal.read_blob(entry.backup_relative_path)
                except (OSError, ValueError) as error:
                    raise UncertainEffectError(
                        "transaction backup is unavailable"
                    ) from error
                if _digest(content) != entry.expected_original_digest:
                    raise _ApplyFailure("backup verification failed")
                desired = _Snapshot(
                    content=content,
                    digest=entry.expected_original_digest,
                    kind=entry.original_kind,
                    executable=entry.original_executable,
                    symlink_target=entry.original_symlink_target,
                )
            _conditional_leaf_effect(
                parent_descriptor,
                name,
                current,
                desired,
                _quarantine_name(journal.transaction_id, entry.path),
                (
                    None
                    if entry.expected_original_digest is None
                    else _temporary_name(
                        journal.transaction_id,
                        entry.path,
                        entry.expected_original_digest,
                    )
                ),
            )
        if not named_chain_matches():
            raise UncertainEffectError(
                "target parent chain changed during rollback"
            )
    finally:
        os.close(parent_descriptor)
    _remove_created_parents(
        target_root,
        entry,
        created_parent_evidence,
    )


def _verify_applied(target_root: Path, plan: ApplyPlan) -> bool:
    try:
        return all(
            _snapshot_matches(_snapshot(target_root, entry.path), entry, new=True)
            for entry in plan.entries
        )
    except (OSError, ValueError, _ApplyFailure):
        return False


def _verify_restored(
    target_root: Path,
    entries: tuple[ApplyPlanEntry, ...],
) -> bool:
    try:
        return all(
            _snapshot_matches(_snapshot(target_root, entry.path), entry, new=False)
            for entry in entries
        )
    except (OSError, ValueError, _ApplyFailure):
        return False


def _transaction_artifacts_absent(
    target_root: Path,
    plan: ApplyPlan,
) -> bool:
    try:
        for entry in plan.entries:
            try:
                parent_descriptor, _ = _open_parent_fd(
                    target_root,
                    entry.path,
                )
            except FileNotFoundError:
                continue
            try:
                names = [_quarantine_name(plan.transaction_id, entry.path)]
                for digest in {
                    entry.expected_original_digest,
                    entry.new_digest,
                }:
                    if digest is not None:
                        names.append(
                            _temporary_name(
                                plan.transaction_id,
                                entry.path,
                                digest,
                            )
                        )
                if any(
                    _snapshot_at(parent_descriptor, name) is not None
                    for name in names
                ):
                    return False
            finally:
                os.close(parent_descriptor)
        return True
    except (OSError, ValueError, _ApplyFailure):
        return False


def _plan_filesystem_identity_matches(
    target_root: Path,
    plan: ApplyPlan,
) -> bool:
    try:
        root_status = os.stat(target_root, follow_symlinks=False)
        if (
            not stat.S_ISDIR(root_status.st_mode)
            or _directory_status_identity(root_status)
            != plan.target_root_identity
        ):
            return False
        for entry in plan.entries:
            if entry.target_parent_identity is None:
                continue
            parent_descriptor, _ = _open_parent_fd(target_root, entry.path)
            try:
                parent_status = os.fstat(parent_descriptor)
                if (
                    not stat.S_ISDIR(parent_status.st_mode)
                    or _directory_status_identity(parent_status)
                    != entry.target_parent_identity
                ):
                    return False
            finally:
                os.close(parent_descriptor)
        return True
    except (OSError, ValueError, _ApplyFailure):
        return False


def _resolve_transaction_artifacts(
    target_root: Path,
    entry: ApplyPlanEntry,
    transaction_id: str,
    phase: ApplyPhase,
) -> None:
    opened_parents: list[tuple[RepoPath, str]] = []
    root_identity: list[str] = []
    try:
        parent_descriptor, name = _open_parent_fd(
            target_root,
            entry.path,
            opened_parents=opened_parents,
            root_identity=root_identity,
        )
    except FileNotFoundError:
        return

    def named_chain_matches() -> bool:
        try:
            root_status = os.stat(target_root, follow_symlinks=False)
            return (
                bool(root_identity)
                and _directory_status_identity(root_status) == root_identity[0]
                and all(
                    _directory_identity(target_root, path) == identity
                    for path, identity in opened_parents
                )
            )
        except (OSError, ValueError, _ApplyFailure):
            return False

    displaced_is_new = phase is ApplyPhase.ROLLING_BACK
    desired_is_new = not displaced_is_new
    try:
        if not named_chain_matches():
            raise UncertainEffectError(
                "target parent chain changed during recovery"
            )
        desired_digest = (
            entry.new_digest
            if desired_is_new
            else entry.expected_original_digest
        )
        if desired_digest is not None:
            temporary = _temporary_name(
                transaction_id,
                entry.path,
                desired_digest,
            )
            temporary_snapshot = _snapshot_at(parent_descriptor, temporary)
            if temporary_snapshot is not None:
                if not _snapshot_matches(
                    temporary_snapshot,
                    entry,
                    new=desired_is_new,
                ):
                    raise UncertainEffectError(
                        "transaction temporary evidence is invalid"
                    )
                os.unlink(temporary, dir_fd=parent_descriptor)
                os.fsync(parent_descriptor)

        quarantine = _quarantine_name(transaction_id, entry.path)
        quarantined = _snapshot_at(parent_descriptor, quarantine)
        if quarantined is not None:
            if not _snapshot_matches(
                quarantined,
                entry,
                new=displaced_is_new,
            ):
                raise UncertainEffectError(
                    "transaction quarantine evidence is invalid"
                )
            current = _snapshot_at(parent_descriptor, name)
            if current is None:
                if not _restore_quarantined(
                    parent_descriptor,
                    name,
                    quarantine,
                    quarantined,
                ):
                    raise UncertainEffectError(
                        "transaction quarantine cannot be restored"
                    )
            elif (
                _snapshot_matches(current, entry, new=displaced_is_new)
                or _snapshot_matches(current, entry, new=desired_is_new)
            ):
                os.unlink(quarantine, dir_fd=parent_descriptor)
                os.fsync(parent_descriptor)
            else:
                raise UncertainEffectError(
                    "target changed while transaction was interrupted"
                )
        if not named_chain_matches():
            raise UncertainEffectError(
                "target parent chain changed during recovery"
            )
    finally:
        os.close(parent_descriptor)


def _created_parents_restored(
    target_root: Path,
    entries: tuple[ApplyPlanEntry, ...],
) -> bool:
    try:
        return all(
            not _directory_exists(target_root, path)
            for entry in entries
            for path in entry.created_parent_paths
        )
    except (OSError, ValueError, _ApplyFailure):
        return False


def _result(
    transaction_id: str,
    decision: ApplyDecision,
    task_state: TaskState,
    *,
    phase: ApplyPhase | None = None,
    recovery_state: RecoveryState | None = None,
    plan: ApplyPlan | None = None,
    journal: ApplyJournal | None = None,
    index_digest_after: str | None = None,
    reason: str = "",
) -> ApplyResult:
    return ApplyResult(
        transaction_id=transaction_id,
        decision=decision,
        phase=phase,
        task_state=task_state,
        recovery_state=recovery_state,
        plan=plan,
        journal=journal,
        index_digest_after=index_digest_after,
        reason=reason,
    )


def _existing_recovery_result(
    transaction_id: str,
    journal: ApplyJournal | None,
    plan: ApplyPlan | None,
    reason: str,
) -> ApplyResult:
    if journal is not None:
        try:
            if journal.latest_phase is not ApplyPhase.RECOVERY_REQUIRED:
                journal.record(
                    JournalStage.RECOVERY,
                    JournalStatus.COMPLETED,
                    phase=ApplyPhase.RECOVERY_REQUIRED,
                    detail="transaction journal or effect is not provable",
                )
        except BaseException:
            pass
    return _result(
        transaction_id,
        ApplyDecision.APPLY,
        TaskState.RECOVERY_REQUIRED,
        phase=ApplyPhase.RECOVERY_REQUIRED,
        recovery_state=RecoveryState.RECOVERY_REQUIRED,
        plan=plan,
        journal=journal,
        reason=reason,
    )


def _replay_existing_transaction(
    journal: ApplyJournal,
    target_root: Path,
    *,
    requested_baseline: BaselineManifest,
    requested_changeset: ChangeSet,
    requested_decision: ApplyDecision,
) -> ApplyResult:
    plan: ApplyPlan | None = None
    try:
        plan = journal.plan
        phase = journal.latest_phase
        target = _trusted_root(target_root)
        index_after = _index_digest(target)
    except BaseException:
        return _existing_recovery_result(
            journal.transaction_id,
            journal,
            plan,
            "transaction id identifies corrupt or nonterminal evidence",
        )
    mismatch = (
        requested_decision is not ApplyDecision.APPLY
        or requested_baseline.digest != plan.baseline_digest
        or requested_changeset.digest != plan.changeset_digest
    )
    if mismatch:
        return _result(
            journal.transaction_id,
            requested_decision,
            TaskState.NOT_APPLIED,
            plan=plan,
            journal=journal,
            index_digest_after=index_after,
            reason="transaction id conflicts with the existing request",
        )
    reason = "transaction id replayed existing terminal result"
    if (
        phase is ApplyPhase.APPLIED
        and _verify_applied(target, plan)
        and _transaction_artifacts_absent(target, plan)
        and _plan_filesystem_identity_matches(target, plan)
        and index_after == plan.index_digest_before
    ):
        return _result(
            journal.transaction_id,
            ApplyDecision.APPLY,
            TaskState.COMPLETED,
            phase=ApplyPhase.APPLIED,
            recovery_state=RecoveryState.SUCCESS,
            plan=plan,
            journal=journal,
            index_digest_after=index_after,
            reason=reason,
        )
    if (
        phase is ApplyPhase.ROLLED_BACK
        and _verify_restored(target, plan.entries)
        and _created_parents_restored(target, plan.entries)
        and _transaction_artifacts_absent(target, plan)
        and _plan_filesystem_identity_matches(target, plan)
        and index_after == plan.index_digest_before
    ):
        return _result(
            journal.transaction_id,
            ApplyDecision.APPLY,
            TaskState.FAILED,
            phase=ApplyPhase.ROLLED_BACK,
            recovery_state=RecoveryState.FAILED,
            plan=plan,
            journal=journal,
            index_digest_after=index_after,
            reason=reason,
        )
    return _existing_recovery_result(
        journal.transaction_id,
        journal,
        plan,
        "transaction id identifies nonterminal or unverifiable evidence",
    )


class ApplyCoordinator:
    def __init__(self, transaction_root: Path) -> None:
        if not isinstance(transaction_root, Path):
            raise ValueError("apply coordinator is invalid")
        self._transaction_root = transaction_root

    def apply(
        self,
        *,
        transaction_id: str,
        baseline: BaselineManifest,
        changeset: ChangeSet,
        workspace: TaskWorkspace,
        target_root: Path,
        decision: ApplyDecision,
        confirmation: ApplyConfirmation | None,
        current_task_id: str,
        current_plan_version_identity: str,
        current_acceptance_contract_version_identity: str,
        current_state: TaskState,
        current_idempotency_key: str,
        acceptance_satisfied: bool,
        nonterminal_apply_transaction: bool,
        recovery_required: bool,
        policy_denied: bool,
    ) -> ApplyResult:
        if (
            not _valid_transaction_id(transaction_id)
            or type(decision) is not ApplyDecision
            or type(current_state) is not TaskState
        ):
            raise ValueError("apply transaction is invalid")
        try:
            existing = ApplyJournal.find_existing(
                self._transaction_root,
                transaction_id,
            )
        except BaseException:
            return _existing_recovery_result(
                transaction_id,
                None,
                None,
                "transaction id lookup found corrupt evidence",
            )
        if existing is not None:
            return _replay_existing_transaction(
                existing,
                target_root,
                requested_baseline=baseline,
                requested_changeset=changeset,
                requested_decision=decision,
            )
        if has_blocking_transaction(self._transaction_root):
            return _result(
                transaction_id,
                decision,
                TaskState.RECOVERY_REQUIRED,
                phase=ApplyPhase.RECOVERY_REQUIRED,
                recovery_state=RecoveryState.RECOVERY_REQUIRED,
                reason="an unfinished disk transaction blocks apply",
            )
        if decision is ApplyDecision.REJECT:
            return _result(
                transaction_id,
                decision,
                TaskState.NOT_APPLIED,
                reason="user rejected apply",
            )
        if type(confirmation) is not ApplyConfirmation:
            raise ValueError("apply transaction is invalid")
        trusted_target = _trusted_root(target_root)
        report = detect_conflicts(
            baseline,
            changeset,
            workspace,
            trusted_target,
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
        if not report.apply_permitted:
            return _result(
                transaction_id,
                decision,
                current_state,
                reason="apply conflict",
            )
        current_changeset = compute_changeset(
            baseline,
            workspace,
            target_paths=changeset.target_paths,
        )
        if current_changeset.digest != changeset.digest:
            return _result(
                transaction_id,
                decision,
                current_state,
                reason="change set digest changed",
            )
        index_before = _index_digest(trusted_target)
        payloads: dict[int, bytes] = {}
        backups: dict[int, bytes] = {}
        entries: list[ApplyPlanEntry] = []
        claimed_created_parents: set[str] = set()
        for order, change in enumerate(changeset.changed_files, 1):
            if change.scope is not ChangeScope.TARGET:
                return _result(
                    transaction_id,
                    decision,
                    current_state,
                    reason="change set contains unrelated paths",
                )
            original = _snapshot(trusted_target, change.path)
            if (
                change.baseline_digest is None
                and original is not None
                or change.baseline_digest is not None
                and (
                    original is None
                    or original.digest != change.baseline_digest
                    or original.kind is not change.baseline_kind
                    or original.executable != change.baseline_executable
                    or original.symlink_target != change.baseline_symlink_target
                )
            ):
                return _result(
                    transaction_id,
                    decision,
                    current_state,
                    reason="target changed while preparing apply plan",
                )
            payload = _workspace_payload(workspace, change)
            if payload is not None:
                payloads[order] = payload
            if original is not None:
                backups[order] = original.content
            missing_parents = _missing_parent_paths(
                trusted_target,
                change.path,
            )
            owned_created_parents = tuple(
                path
                for path in missing_parents
                if path.identity not in claimed_created_parents
            )
            claimed_created_parents.update(
                path.identity for path in owned_created_parents
            )
            entries.append(
                ApplyPlanEntry(
                    order=order,
                    path=change.path,
                    operation=change.operation,
                    expected_original_digest=change.baseline_digest,
                    new_digest=change.current_digest,
                    original_kind=change.baseline_kind,
                    new_kind=change.current_kind,
                    original_executable=change.baseline_executable,
                    new_executable=change.current_executable,
                    original_symlink_target=change.baseline_symlink_target,
                    new_symlink_target=change.current_symlink_target,
                    backup_relative_path=(
                        None if original is None else f"backups/{order:06d}.blob"
                    ),
                    payload_relative_path=(
                        None if payload is None else f"payloads/{order:06d}.blob"
                    ),
                    backup_digest=(
                        None if original is None else original.digest
                    ),
                    payload_digest=(
                        None if payload is None else _digest(payload)
                    ),
                    created_parent_paths=owned_created_parents,
                    target_parent_identity=_existing_parent_identity(
                        trusted_target,
                        change.path,
                    ),
                )
            )
        plan = make_apply_plan(
            transaction_id=transaction_id,
            baseline_digest=baseline.digest,
            changeset_digest=changeset.digest,
            index_digest_before=index_before,
            target_root_identity=_directory_status_identity(
                os.stat(trusted_target, follow_symlinks=False)
            ),
            entries=tuple(entries),
        )
        try:
            journal = ApplyJournal.create(
                self._transaction_root,
                transaction_id,
                plan,
            )
        except BaseException as error:
            try:
                journal = ApplyJournal.find_existing(
                    self._transaction_root,
                    transaction_id,
                )
            except BaseException:
                journal = None
            existing_plan: ApplyPlan | None = None
            if journal is not None:
                try:
                    existing_plan = journal.plan
                except BaseException:
                    pass
            return _existing_recovery_result(
                transaction_id,
                journal,
                plan if existing_plan is None else existing_plan,
                "transaction id prepare header could not be persisted: "
                + str(error),
            )

        def require_recovery(reason: BaseException | str) -> ApplyResult:
            try:
                if journal.latest_phase is not ApplyPhase.RECOVERY_REQUIRED:
                    journal.record(
                        JournalStage.RECOVERY,
                        JournalStatus.COMPLETED,
                        phase=ApplyPhase.RECOVERY_REQUIRED,
                        detail="transaction journal or effect is not provable",
                    )
            except BaseException:
                # The preceding durable nonterminal phase still blocks new apply.
                pass
            return _result(
                transaction_id,
                decision,
                TaskState.RECOVERY_REQUIRED,
                phase=ApplyPhase.RECOVERY_REQUIRED,
                recovery_state=RecoveryState.RECOVERY_REQUIRED,
                plan=plan,
                journal=journal,
                reason=str(reason),
            )

        try:
            for entry in plan.entries:
                if entry.payload_relative_path is not None:
                    journal.write_blob(
                        entry.payload_relative_path,
                        payloads[entry.order],
                    )
                journal.record(
                    JournalStage.BACKUP,
                    JournalStatus.PENDING,
                    path=entry.path,
                    detail="backup pending",
                )
                if entry.backup_relative_path is not None:
                    digest = journal.write_blob(
                        entry.backup_relative_path,
                        backups[entry.order],
                    )
                    if digest != entry.backup_digest:
                        raise _ApplyFailure("backup digest mismatch")
                if not _snapshot_matches(
                    _snapshot(trusted_target, entry.path),
                    entry,
                    new=False,
                ):
                    raise _ApplyFailure("target changed during backup")
                journal.record(
                    JournalStage.BACKUP,
                    JournalStatus.COMPLETED,
                    path=entry.path,
                    detail="backup verified",
                    evidence_digest=entry.backup_digest,
                )
            journal.record(
                JournalStage.BACKUP,
                JournalStatus.COMPLETED,
                phase=ApplyPhase.BACKUP_READY,
                detail="all backups verified",
                evidence_digest=plan.digest,
            )
        except BaseException as error:
            return require_recovery(error)

        if not _plan_filesystem_identity_matches(trusted_target, plan):
            return require_recovery(
                _ApplyFailure("target filesystem identity changed")
            )
        try:
            journal.record(
                JournalStage.APPLY,
                JournalStatus.COMPLETED,
                phase=ApplyPhase.APPLYING,
                detail="apply phase persisted",
            )
        except BaseException as error:
            return require_recovery(error)
        affected: list[ApplyPlanEntry] = []
        created_parent_evidence: dict[str, dict[str, str]] = {}
        failure: BaseException | None = None
        for entry in plan.entries:
            effect_started = False
            try:
                if not _snapshot_matches(
                    _snapshot(trusted_target, entry.path),
                    entry,
                    new=False,
                ) or not _created_parents_absent(trusted_target, entry):
                    raise _ApplyFailure("target changed before write")
                try:
                    journal.record(
                        JournalStage.APPLY,
                        JournalStatus.PENDING,
                        path=entry.path,
                        detail="apply effect pending",
                    )
                except BaseException as error:
                    return require_recovery(error)
                effect_started = True
                created_items = _publish_entry(
                    trusted_target,
                    entry,
                    journal,
                )
                entry_created_evidence = {
                    path.identity: evidence
                    for path, evidence in created_items
                }
                created_parent_evidence[entry.path.identity] = (
                    entry_created_evidence
                )
                for path, evidence in created_items:
                    try:
                        journal.record(
                            JournalStage.APPLY,
                            JournalStatus.COMPLETED,
                            path=path,
                            detail=(
                                "created parent for "
                                + entry.path.canonical
                            ),
                            evidence_digest=evidence,
                        )
                    except BaseException as error:
                        return require_recovery(error)
                if not _snapshot_matches(
                    _snapshot(trusted_target, entry.path),
                    entry,
                    new=True,
                ):
                    raise _ApplyFailure("apply verification failed")
                affected.append(entry)
                try:
                    journal.record(
                        JournalStage.APPLY,
                        JournalStatus.COMPLETED,
                        path=entry.path,
                        detail="apply effect verified",
                        evidence_digest=entry.new_digest,
                    )
                except BaseException as error:
                    return require_recovery(error)
            except UncertainEffectError as error:
                return require_recovery(error)
            except BaseException as error:
                if not effect_started:
                    failure = error
                    break
                try:
                    current = _snapshot(trusted_target, entry.path)
                    if _snapshot_matches(current, entry, new=True):
                        affected.append(entry)
                    elif not _snapshot_matches(current, entry, new=False):
                        raise UncertainEffectError
                except BaseException:
                    return require_recovery(error)
                failure = error
                break
        if failure is None:
            if (
                not _verify_applied(trusted_target, plan)
                or not _transaction_artifacts_absent(trusted_target, plan)
                or not _plan_filesystem_identity_matches(
                    trusted_target,
                    plan,
                )
            ):
                failure = _ApplyFailure("final target verification failed")
            else:
                try:
                    repeated = compute_changeset(
                        baseline,
                        workspace,
                        target_paths=changeset.target_paths,
                    )
                except BaseException as error:
                    failure = error
                else:
                    try:
                        journal.record(
                            JournalStage.VERIFY,
                            JournalStatus.COMPLETED,
                            detail="change set digest rechecked",
                            evidence_digest=repeated.digest,
                        )
                    except BaseException as error:
                        return require_recovery(error)
                    if repeated.digest != plan.changeset_digest:
                        failure = _ApplyFailure("change set digest changed")
        if failure is None:
            try:
                index_after = _index_digest(trusted_target)
            except BaseException as error:
                failure = error
            else:
                try:
                    journal.record(
                        JournalStage.VERIFY,
                        JournalStatus.COMPLETED,
                        detail="index digest rechecked",
                        evidence_digest=index_after,
                    )
                except BaseException as error:
                    return require_recovery(error)
                if index_after != plan.index_digest_before:
                    failure = _ApplyFailure("repository index changed")
        if failure is None:
            try:
                journal.record(
                    JournalStage.VERIFY,
                    JournalStatus.COMPLETED,
                    phase=ApplyPhase.APPLIED,
                    detail="apply transaction verified",
                    evidence_digest=plan.digest,
                )
            except BaseException as error:
                return require_recovery(error)
            return _result(
                transaction_id,
                decision,
                TaskState.COMPLETED,
                phase=ApplyPhase.APPLIED,
                recovery_state=RecoveryState.SUCCESS,
                plan=plan,
                journal=journal,
                index_digest_after=index_after,
            )

        try:
            journal.record(
                JournalStage.ROLLBACK,
                JournalStatus.COMPLETED,
                phase=ApplyPhase.ROLLING_BACK,
                detail="rollback phase persisted",
            )
        except BaseException as error:
            return require_recovery(error)
        try:
            for entry in reversed(affected):
                current = _snapshot(trusted_target, entry.path)
                if _snapshot_matches(current, entry, new=True):
                    restore_required = True
                elif _snapshot_matches(current, entry, new=False):
                    restore_required = not _created_parents_restored(
                        trusted_target,
                        (entry,),
                    )
                else:
                    raise _ApplyFailure(
                        "rollback target changed after apply"
                    )
                journal.record(
                    JournalStage.ROLLBACK,
                    JournalStatus.PENDING,
                    path=entry.path,
                    detail="rollback effect pending",
                )
                if restore_required:
                    _restore_entry(
                        trusted_target,
                        entry,
                        journal,
                        created_parent_evidence=created_parent_evidence.get(
                            entry.path.identity
                        ),
                    )
                if not _snapshot_matches(
                    _snapshot(trusted_target, entry.path),
                    entry,
                    new=False,
                ):
                    raise _ApplyFailure("rollback verification failed")
                journal.record(
                    JournalStage.ROLLBACK,
                    JournalStatus.COMPLETED,
                    path=entry.path,
                    detail="rollback effect verified",
                    evidence_digest=entry.expected_original_digest,
                )
            if (
                not _verify_restored(trusted_target, tuple(affected))
                or not _transaction_artifacts_absent(trusted_target, plan)
                or not _plan_filesystem_identity_matches(
                    trusted_target,
                    plan,
                )
            ):
                raise _ApplyFailure("final rollback verification failed")
            if not _created_parents_restored(
                trusted_target,
                tuple(affected),
            ):
                raise _ApplyFailure(
                    "transaction-created parent restoration failed"
                )
            index_after = _index_digest(trusted_target)
            if index_after != plan.index_digest_before:
                raise _ApplyFailure("index changed during rollback")
            journal.record(
                JournalStage.VERIFY,
                JournalStatus.COMPLETED,
                detail="rollback index digest rechecked",
                evidence_digest=index_after,
            )
            journal.record(
                JournalStage.VERIFY,
                JournalStatus.COMPLETED,
                phase=ApplyPhase.ROLLED_BACK,
                detail="rollback verified",
                evidence_digest=plan.digest,
            )
            return _result(
                transaction_id,
                decision,
                TaskState.FAILED,
                phase=ApplyPhase.ROLLED_BACK,
                recovery_state=RecoveryState.FAILED,
                plan=plan,
                journal=journal,
                index_digest_after=index_after,
                reason=str(failure),
            )
        except BaseException as rollback_error:
            return require_recovery(rollback_error)


__all__ = ["ApplyCoordinator", "UncertainEffectError"]
