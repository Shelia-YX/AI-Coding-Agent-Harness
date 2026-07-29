"""Append-only, fsync-backed disk journal for apply transactions."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat

from coding_harness.transaction.models import (
    ApplyPhase,
    ApplyPlan,
    ApplyPlanEntry,
    JournalRecord,
    JournalStage,
    JournalStatus,
    parse_apply_plan,
)
from coding_harness.workspace.paths import RepoPath


_MAX_JOURNAL_BYTES = 16 * 1024 * 1024
_MAX_PLAN_BYTES = 16 * 1024 * 1024
_MAX_BLOB_BYTES = 8 * 1024 * 1024
_MAX_RECORDS = 100_000
_MAX_TRANSACTION_DIRECTORIES = 10_000


class JournalEnumerationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class JournalSnapshot:
    transaction_id: str
    journal_reference: str
    phase: ApplyPhase | None
    plan_digest: str
    blocking: bool


def _transaction_name(transaction_id: str) -> str:
    if (
        type(transaction_id) is not str
        or not transaction_id
        or "\0" in transaction_id
    ):
        raise ValueError("transaction journal is invalid")
    try:
        encoded = transaction_id.encode("utf-8", errors="strict")
    except UnicodeError:
        raise ValueError("transaction journal is invalid") from None
    if len(encoded) > 1024:
        raise ValueError("transaction journal is invalid")
    return "txn-" + hashlib.sha256(encoded).hexdigest()


def _relative_parts(value: str) -> tuple[str, ...]:
    if type(value) is not str or not value or "\\" in value or "\0" in value:
        raise ValueError("transaction journal is invalid")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {"", ".", ".."} for part in path.parts)
        or str(path) != value
    ):
        raise ValueError("transaction journal is invalid")
    return tuple(path.parts)


def _fsync_directory(path: Path) -> None:
    descriptor = _open_validated_directory(path)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)


def _open_validated_directory(path: Path) -> int:
    try:
        before = os.lstat(path)
        resolved = path.resolve(strict=True)
        descriptor = os.open(path, _DIRECTORY_FLAGS)
    except (OSError, RuntimeError):
        raise ValueError("transaction journal is invalid") from None
    try:
        current = os.fstat(descriptor)
        if (
            stat.S_ISLNK(before.st_mode)
            or not stat.S_ISDIR(before.st_mode)
            or resolved != path.absolute()
            or before.st_uid != os.geteuid()
            or before.st_mode & 0o077
            or current.st_dev != before.st_dev
            or current.st_ino != before.st_ino
            or not stat.S_ISDIR(current.st_mode)
            or current.st_uid != os.geteuid()
            or current.st_mode & 0o077
        ):
            raise ValueError("transaction journal is invalid")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _validate_directory(path: Path) -> Path:
    descriptor = _open_validated_directory(path)
    try:
        return path.resolve(strict=True)
    finally:
        os.close(descriptor)


def _ensure_transaction_root(path: Path) -> Path:
    if not isinstance(path, Path):
        raise ValueError("transaction journal is invalid")
    absolute = path.absolute()
    if not os.path.lexists(absolute):
        parent = _validate_directory(absolute.parent)
        try:
            os.mkdir(absolute, 0o700)
            _fsync_directory(parent)
        except OSError:
            raise ValueError("transaction journal is invalid") from None
    return _validate_directory(absolute)


def _write_all(descriptor: int, content: bytes) -> None:
    remaining = memoryview(content)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("short write")
        remaining = remaining[written:]


def _write_new_file(path: Path, content: bytes) -> None:
    parent_descriptor = _open_validated_directory(path.parent)
    try:
        _write_new_file_at(parent_descriptor, path.name, content)
    finally:
        os.close(parent_descriptor)


def _write_new_file_at(
    parent_descriptor: int,
    name: str,
    content: bytes,
) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(name, flags, 0o600, dir_fd=parent_descriptor)
    try:
        _write_all(descriptor, content)
        os.fsync(descriptor)
    except BaseException:
        try:
            os.unlink(name, dir_fd=parent_descriptor)
        except OSError:
            pass
        raise
    finally:
        os.close(descriptor)
    os.fsync(parent_descriptor)


def _read_bounded_at(
    parent_descriptor: int,
    name: str,
    limit: int,
) -> tuple[bytes, tuple[int, int, int, int]]:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("transaction journal is invalid")
        remaining = before.st_size + 1
        chunks: list[bytes] = []
        while remaining:
            chunk = os.read(descriptor, min(64 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        after = os.fstat(descriptor)
        if (
            len(content) != before.st_size
            or after.st_dev != before.st_dev
            or after.st_ino != before.st_ino
            or after.st_size != before.st_size
            or after.st_mtime_ns != before.st_mtime_ns
        ):
            raise ValueError("transaction journal is invalid")
        return content, (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
    finally:
        os.close(descriptor)


def _bounded_signature_at(
    parent_descriptor: int,
    name: str,
    limit: int,
) -> tuple[int, int, int, int]:
    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    try:
        current = os.fstat(descriptor)
        if not stat.S_ISREG(current.st_mode) or current.st_size > limit:
            raise ValueError("transaction journal is invalid")
        return (
            current.st_dev,
            current.st_ino,
            current.st_size,
            current.st_mtime_ns,
        )
    finally:
        os.close(descriptor)


def _open_relative_parent(
    root: Path,
    parts: tuple[str, ...],
    *,
    create: bool,
) -> int:
    descriptor = _open_validated_directory(root)
    try:
        for part in parts:
            try:
                child = os.open(
                    part,
                    _DIRECTORY_FLAGS,
                    dir_fd=descriptor,
                )
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, 0o700, dir_fd=descriptor)
                os.fsync(descriptor)
                child = os.open(
                    part,
                    _DIRECTORY_FLAGS,
                    dir_fd=descriptor,
                )
            status = os.fstat(child)
            if (
                not stat.S_ISDIR(status.st_mode)
                or status.st_uid != os.geteuid()
                or status.st_mode & 0o077
            ):
                os.close(child)
                raise ValueError("transaction journal is invalid")
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _record_payload(record: JournalRecord) -> bytes:
    payload = {
        "schema": "coding-harness:apply-journal-record:v1",
        "order": record.order,
        "stage": record.stage.value,
        "status": record.status.value,
        "phase": None if record.phase is None else record.phase.value,
        "path": None if record.path is None else record.path.canonical,
        "detail": record.detail,
        "evidence_digest": record.evidence_digest,
    }
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _parse_record(line: bytes) -> JournalRecord:
    try:
        payload = json.loads(line)
        if (
            type(payload) is not dict
            or payload.get("schema")
            != "coding-harness:apply-journal-record:v1"
        ):
            raise ValueError
        return JournalRecord(
            order=payload["order"],
            stage=JournalStage(payload["stage"]),
            status=JournalStatus(payload["status"]),
            phase=(
                None
                if payload["phase"] is None
                else ApplyPhase(payload["phase"])
            ),
            path=(
                None
                if payload["path"] is None
                else RepoPath.parse(payload["path"])
            ),
            detail=payload["detail"],
            evidence_digest=payload["evidence_digest"],
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise ValueError("transaction journal is invalid") from None


_PHASE_PREDECESSORS = {
    ApplyPhase.PREPARING: frozenset(),
    ApplyPhase.BACKUP_READY: frozenset({ApplyPhase.PREPARING}),
    ApplyPhase.APPLYING: frozenset({ApplyPhase.BACKUP_READY}),
    ApplyPhase.APPLIED: frozenset({ApplyPhase.APPLYING}),
    ApplyPhase.ROLLING_BACK: frozenset(
        {
            ApplyPhase.APPLYING,
            ApplyPhase.RECOVERY_REQUIRED,
        }
    ),
    ApplyPhase.ROLLED_BACK: frozenset({ApplyPhase.ROLLING_BACK}),
    ApplyPhase.RECOVERY_REQUIRED: frozenset(
        {
            ApplyPhase.PREPARING,
            ApplyPhase.BACKUP_READY,
            ApplyPhase.APPLYING,
            ApplyPhase.ROLLING_BACK,
            ApplyPhase.APPLIED,
            ApplyPhase.ROLLED_BACK,
        }
    ),
}


_PHASE_STAGE = {
    ApplyPhase.PREPARING: JournalStage.PREPARE,
    ApplyPhase.BACKUP_READY: JournalStage.BACKUP,
    ApplyPhase.APPLYING: JournalStage.APPLY,
    ApplyPhase.APPLIED: JournalStage.VERIFY,
    ApplyPhase.ROLLING_BACK: JournalStage.ROLLBACK,
    ApplyPhase.ROLLED_BACK: JournalStage.VERIFY,
    ApplyPhase.RECOVERY_REQUIRED: JournalStage.RECOVERY,
}


def _validate_applied_evidence(
    records: tuple[JournalRecord, ...],
    plan: ApplyPlan,
    applied_order: int,
) -> None:
    pending_by_path: dict[str, list[JournalRecord]] = {}
    completed_by_path: dict[str, list[JournalRecord]] = {}
    created_by_path: dict[str, list[JournalRecord]] = {}
    found_verification: set[tuple[str, str | None]] = set()
    for record in records:
        identity = None if record.path is None else record.path.identity
        if (
            record.stage is JournalStage.APPLY
            and record.phase is None
            and identity is not None
        ):
            if (
                record.status is JournalStatus.PENDING
                and record.detail == "apply effect pending"
                and record.evidence_digest is None
            ):
                pending_by_path.setdefault(identity, []).append(record)
            elif (
                record.status is JournalStatus.COMPLETED
                and record.detail == "apply effect verified"
            ):
                completed_by_path.setdefault(identity, []).append(record)
            elif (
                record.status is JournalStatus.COMPLETED
                and record.detail.startswith("created parent for ")
                and record.evidence_digest is not None
            ):
                created_by_path.setdefault(identity, []).append(record)
        elif (
            record.stage is JournalStage.VERIFY
            and record.status is JournalStatus.COMPLETED
            and record.phase is None
            and record.path is None
            and record.order < applied_order
        ):
            found_verification.add((record.detail, record.evidence_digest))
    for entry in plan.entries:
        pending = tuple(
            pending_by_path.get(entry.path.identity, ())
        )
        completed = tuple(
            record
            for record in completed_by_path.get(entry.path.identity, ())
            if record.evidence_digest == entry.new_digest
        )
        if (
            len(pending) != 1
            or len(completed) != 1
            or not pending[0].order < completed[0].order < applied_order
        ):
            raise ValueError("transaction journal is invalid")
        for parent in entry.created_parent_paths:
            detail = "created parent for " + entry.path.canonical
            evidence = tuple(
                record
                for record in created_by_path.get(parent.identity, ())
                if record.detail == detail
            )
            if (
                len(evidence) != 1
                or not pending[0].order
                < evidence[0].order
                < completed[0].order
            ):
                raise ValueError("transaction journal is invalid")
    required_verification = {
        ("change set digest rechecked", plan.changeset_digest),
        ("index digest rechecked", plan.index_digest_before),
    }
    if not required_verification.issubset(found_verification):
        raise ValueError("transaction journal is invalid")


def _validate_backup_evidence(
    records: tuple[JournalRecord, ...],
    plan: ApplyPlan,
    backup_ready_order: int,
) -> None:
    pending_by_path: dict[str, list[JournalRecord]] = {}
    completed_by_path: dict[str, list[JournalRecord]] = {}
    for record in records:
        if (
            record.stage is not JournalStage.BACKUP
            or record.phase is not None
            or record.path is None
        ):
            continue
        if (
            record.status is JournalStatus.PENDING
            and record.detail == "backup pending"
            and record.evidence_digest is None
        ):
            pending_by_path.setdefault(record.path.identity, []).append(record)
        elif (
            record.status is JournalStatus.COMPLETED
            and record.detail == "backup verified"
        ):
            completed_by_path.setdefault(
                record.path.identity,
                [],
            ).append(record)
    for entry in plan.entries:
        pending = tuple(pending_by_path.get(entry.path.identity, ()))
        completed = tuple(
            record
            for record in completed_by_path.get(entry.path.identity, ())
            if record.evidence_digest == entry.backup_digest
        )
        if (
            len(pending) != 1
            or len(completed) != 1
            or not pending[0].order
            < completed[0].order
            < backup_ready_order
        ):
            raise ValueError("transaction journal is invalid")


def _validate_rolled_back_evidence(
    records: tuple[JournalRecord, ...],
    plan: ApplyPlan,
    rolled_back_order: int,
) -> None:
    applied_by_path: dict[str, list[JournalRecord]] = {}
    pending_by_path: dict[str, list[JournalRecord]] = {}
    completed_by_path: dict[str, list[JournalRecord]] = {}
    index_evidence: list[JournalRecord] = []
    for record in records:
        if record.phase is not None:
            continue
        if record.path is not None:
            identity = record.path.identity
            if (
                record.stage is JournalStage.APPLY
                and record.status is JournalStatus.COMPLETED
                and record.detail == "apply effect verified"
            ):
                applied_by_path.setdefault(identity, []).append(record)
            elif (
                record.stage is JournalStage.ROLLBACK
                and record.status is JournalStatus.PENDING
                and record.detail == "rollback effect pending"
                and record.evidence_digest is None
            ):
                pending_by_path.setdefault(identity, []).append(record)
            elif (
                record.stage is JournalStage.ROLLBACK
                and record.status is JournalStatus.COMPLETED
                and record.detail == "rollback effect verified"
            ):
                completed_by_path.setdefault(identity, []).append(record)
        elif (
            record.stage is JournalStage.VERIFY
            and record.status is JournalStatus.COMPLETED
            and record.detail == "rollback index digest rechecked"
            and record.evidence_digest == plan.index_digest_before
            and record.order < rolled_back_order
        ):
            index_evidence.append(record)
    for entry in plan.entries:
        applied = tuple(
            record
            for record in applied_by_path.get(entry.path.identity, ())
            if record.evidence_digest == entry.new_digest
        )
        if not applied:
            continue
        if len(applied) != 1:
            raise ValueError("transaction journal is invalid")
        pending = tuple(
            pending_by_path.get(entry.path.identity, ())
        )
        completed = tuple(
            record
            for record in completed_by_path.get(entry.path.identity, ())
            if record.evidence_digest == entry.expected_original_digest
        )
        if (
            len(pending) != 1
            or len(completed) != 1
            or not applied[0].order
            < pending[0].order
            < completed[0].order
            < rolled_back_order
        ):
            raise ValueError("transaction journal is invalid")
    if len(index_evidence) != 1:
        raise ValueError("transaction journal is invalid")


def _validate_record_sequence(
    records: tuple[JournalRecord, ...],
    plan: ApplyPlan,
) -> None:
    current_phase: ApplyPhase | None = None
    entries = {entry.path.identity: entry for entry in plan.entries}
    created_parent_owners = {
        parent.identity: entry
        for entry in plan.entries
        for parent in entry.created_parent_paths
    }
    for index, record in enumerate(records):
        if record.phase is not None and (
            record.path is not None
            or record.status is not JournalStatus.COMPLETED
            or record.stage is not _PHASE_STAGE[record.phase]
        ):
            raise ValueError("transaction journal is invalid")
        if record.phase in {
            ApplyPhase.PREPARING,
            ApplyPhase.BACKUP_READY,
            ApplyPhase.APPLIED,
            ApplyPhase.ROLLED_BACK,
        }:
            if record.evidence_digest != plan.digest:
                raise ValueError("transaction journal is invalid")
        elif record.phase is not None and record.evidence_digest is not None:
            raise ValueError("transaction journal is invalid")
        if record.phase is None:
            _validate_nonphase_record(
                record,
                current_phase,
                plan,
                entries,
                created_parent_owners,
            )
            continue
        if record.phase is current_phase:
            raise ValueError("transaction journal is invalid")
        if current_phase is None:
            valid = index == 0 and (
                (
                    record.phase is ApplyPhase.PREPARING
                    and record.stage is JournalStage.PREPARE
                )
                or (
                    record.phase is ApplyPhase.RECOVERY_REQUIRED
                    and record.stage is JournalStage.RECOVERY
                )
            )
        else:
            valid = current_phase in _PHASE_PREDECESSORS[record.phase]
        if not valid:
            raise ValueError("transaction journal is invalid")
        current_phase = record.phase
        if record.phase is ApplyPhase.BACKUP_READY:
            _validate_backup_evidence(records, plan, record.order)
        elif record.phase is ApplyPhase.APPLIED:
            _validate_applied_evidence(records, plan, record.order)
        elif record.phase is ApplyPhase.ROLLED_BACK:
            _validate_rolled_back_evidence(records, plan, record.order)


def _validate_nonphase_record(
    record: JournalRecord,
    current_phase: ApplyPhase | None,
    plan: ApplyPlan,
    entries: dict[str, ApplyPlanEntry],
    created_parent_owners: dict[str, ApplyPlanEntry],
) -> None:
    identity = None if record.path is None else record.path.identity
    entry = None if identity is None else entries.get(identity)
    owner = (
        None if identity is None else created_parent_owners.get(identity)
    )
    valid = False
    if record.stage is JournalStage.BACKUP:
        if current_phase is ApplyPhase.PREPARING and entry is not None:
            if record.status is JournalStatus.PENDING:
                valid = (
                    record.detail == "backup pending"
                    and record.evidence_digest is None
                )
            else:
                valid = (
                    record.detail == "backup verified"
                    and record.evidence_digest == entry.backup_digest
                )
    elif record.stage is JournalStage.APPLY:
        if current_phase is ApplyPhase.APPLYING and entry is not None:
            if record.status is JournalStatus.PENDING:
                valid = (
                    record.detail == "apply effect pending"
                    and record.evidence_digest is None
                )
            else:
                valid = (
                    record.detail == "apply effect verified"
                    and record.evidence_digest == entry.new_digest
                )
        elif current_phase is ApplyPhase.APPLYING and owner is not None:
            valid = (
                record.status is JournalStatus.COMPLETED
                and record.detail
                == "created parent for " + owner.path.canonical
                and record.evidence_digest is not None
            )
    elif record.stage is JournalStage.VERIFY:
        valid = (
            record.status is JournalStatus.COMPLETED
            and record.path is None
            and (
                current_phase is ApplyPhase.APPLYING
                and (
                    record.detail == "change set digest rechecked"
                    and record.evidence_digest == plan.changeset_digest
                    or record.detail == "index digest rechecked"
                    and record.evidence_digest == plan.index_digest_before
                )
                or current_phase is ApplyPhase.ROLLING_BACK
                and record.detail == "rollback index digest rechecked"
                and record.evidence_digest == plan.index_digest_before
            )
        )
    elif record.stage is JournalStage.ROLLBACK:
        if current_phase is ApplyPhase.ROLLING_BACK and entry is not None:
            if record.status is JournalStatus.PENDING:
                valid = (
                    record.detail == "rollback effect pending"
                    and record.evidence_digest is None
                )
            else:
                valid = (
                    record.detail == "rollback effect verified"
                    and record.evidence_digest
                    == entry.expected_original_digest
                )
    if not valid:
        raise ValueError("transaction journal is invalid")


class ApplyJournal:
    """One transaction directory containing an immutable plan and JSONL log."""

    def __init__(self, root: Path, transaction_id: str) -> None:
        self._root = _validate_directory(root)
        self._transaction_id = transaction_id
        if self._root.name != _transaction_name(transaction_id):
            raise ValueError("transaction journal is invalid")
        self._path = self._root / "journal.jsonl"
        self._plan_path = self._root / "plan.json"
        self._plan_cache: ApplyPlan | None = None
        self._plan_signature: tuple[int, int, int, int] | None = None
        self._records_cache: tuple[JournalRecord, ...] | None = None
        self._records_signature: tuple[int, int, int, int] | None = None
        self._latest_phase_cache: ApplyPhase | None = None
        self._entries_by_identity: dict[str, ApplyPlanEntry] = {}
        self._created_parent_owners: dict[str, ApplyPlanEntry] = {}

    @classmethod
    def create(
        cls,
        transaction_root: Path,
        transaction_id: str,
        plan: ApplyPlan,
    ) -> "ApplyJournal":
        if type(plan) is not ApplyPlan or plan.transaction_id != transaction_id:
            raise ValueError("transaction journal is invalid")
        parent = _ensure_transaction_root(transaction_root)
        root = parent / _transaction_name(transaction_id)
        serialized_plan = plan.serialize()
        if len(serialized_plan) > _MAX_PLAN_BYTES:
            raise ValueError("transaction journal is invalid")
        try:
            os.mkdir(root, 0o700)
            _fsync_directory(parent)
            _write_new_file(root / "plan.json", serialized_plan)
            _fsync_directory(root)
        except BaseException:
            raise
        journal = cls(root, transaction_id)
        journal.record(
            JournalStage.PREPARE,
            JournalStatus.COMPLETED,
            phase=ApplyPhase.PREPARING,
            detail="immutable apply plan persisted",
            evidence_digest=plan.digest,
        )
        return journal

    @classmethod
    def open_existing(
        cls,
        transaction_root: Path,
        transaction_id: str,
    ) -> "ApplyJournal":
        parent = _validate_directory(transaction_root.absolute())
        return cls(parent / _transaction_name(transaction_id), transaction_id)

    @classmethod
    def find_existing(
        cls,
        transaction_root: Path,
        transaction_id: str,
    ) -> "ApplyJournal | None":
        if not isinstance(transaction_root, Path):
            raise ValueError("transaction journal is invalid")
        _transaction_name(transaction_id)
        absolute = transaction_root.absolute()
        if not os.path.lexists(absolute):
            return None
        parent = _validate_directory(absolute)
        candidate = parent / _transaction_name(transaction_id)
        try:
            status = os.lstat(candidate)
        except FileNotFoundError:
            return None
        except OSError:
            raise ValueError("transaction journal is invalid") from None
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
            raise ValueError("transaction journal is invalid")
        return cls(candidate, transaction_id)

    @property
    def root(self) -> Path:
        return self._root

    @property
    def path(self) -> Path:
        return self._path

    @property
    def transaction_id(self) -> str:
        return self._transaction_id

    @property
    def plan(self) -> ApplyPlan:
        root_descriptor = _open_validated_directory(self._root)
        try:
            content, signature = _read_bounded_at(
                root_descriptor,
                "plan.json",
                _MAX_PLAN_BYTES,
            )
        except (OSError, ValueError):
            raise ValueError("transaction journal is invalid") from None
        finally:
            os.close(root_descriptor)
        if (
            self._plan_cache is not None
            and signature == self._plan_signature
        ):
            return self._plan_cache
        plan = parse_apply_plan(content)
        if plan.transaction_id != self._transaction_id:
            raise ValueError("transaction journal is invalid")
        self._plan_cache = plan
        self._plan_signature = signature
        self._entries_by_identity = {
            entry.path.identity: entry for entry in plan.entries
        }
        self._created_parent_owners = {
            parent.identity: entry
            for entry in plan.entries
            for parent in entry.created_parent_paths
        }
        return plan

    @property
    def records(self) -> tuple[JournalRecord, ...]:
        root_descriptor = _open_validated_directory(self._root)
        try:
            try:
                current_signature = _bounded_signature_at(
                    root_descriptor,
                    "journal.jsonl",
                    _MAX_JOURNAL_BYTES,
                )
            except FileNotFoundError:
                self._records_cache = ()
                self._records_signature = None
                self._latest_phase_cache = None
                return ()
            if (
                self._records_cache is not None
                and current_signature == self._records_signature
            ):
                return self._records_cache
            content, signature = _read_bounded_at(
                root_descriptor,
                "journal.jsonl",
                _MAX_JOURNAL_BYTES,
            )
        except (OSError, ValueError):
            raise ValueError("transaction journal is invalid") from None
        finally:
            os.close(root_descriptor)
        if content and not content.endswith(b"\n"):
            raise ValueError("transaction journal is invalid")
        lines = content.splitlines()
        if len(lines) > _MAX_RECORDS:
            raise ValueError("transaction journal is invalid")
        records = tuple(_parse_record(line) for line in lines)
        if tuple(record.order for record in records) != tuple(
            range(1, len(records) + 1)
        ):
            raise ValueError("transaction journal is invalid")
        _validate_record_sequence(records, self.plan)
        self._records_cache = records
        self._records_signature = signature
        self._latest_phase_cache = next(
            (
                record.phase
                for record in reversed(records)
                if record.phase is not None
            ),
            None,
        )
        return records

    @property
    def latest_phase(self) -> ApplyPhase | None:
        self.records
        return self._latest_phase_cache

    def record(
        self,
        stage: JournalStage,
        status: JournalStatus,
        *,
        phase: ApplyPhase | None = None,
        path: RepoPath | None = None,
        detail: str = "",
        evidence_digest: str | None = None,
    ) -> JournalRecord:
        records = self.records
        current_phase = self._latest_phase_cache
        if phase is not None and phase is not current_phase:
            predecessors = _PHASE_PREDECESSORS[phase]
            if current_phase is None:
                valid = not records and (
                    (
                        phase is ApplyPhase.PREPARING
                        and stage is JournalStage.PREPARE
                    )
                    or (
                        phase is ApplyPhase.RECOVERY_REQUIRED
                        and stage is JournalStage.RECOVERY
                    )
                )
            else:
                valid = current_phase in predecessors
            if not valid:
                raise ValueError("illegal apply phase transition")
        record = JournalRecord(
            order=len(records) + 1,
            stage=stage,
            status=status,
            phase=phase,
            path=path,
            detail=detail,
            evidence_digest=evidence_digest,
        )
        plan = self.plan
        if phase is None:
            _validate_nonphase_record(
                record,
                current_phase,
                plan,
                self._entries_by_identity,
                self._created_parent_owners,
            )
        else:
            _validate_record_sequence((*records, record), plan)
        content = _record_payload(record)
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        root_descriptor = _open_validated_directory(self._root)
        try:
            descriptor = os.open(
                "journal.jsonl",
                flags,
                0o600,
                dir_fd=root_descriptor,
            )
            try:
                current = os.fstat(descriptor)
                if not stat.S_ISREG(current.st_mode):
                    raise ValueError("transaction journal is invalid")
                current_signature = (
                    current.st_dev,
                    current.st_ino,
                    current.st_size,
                    current.st_mtime_ns,
                )
                if (
                    self._records_signature is not None
                    and current_signature != self._records_signature
                ):
                    raise ValueError("transaction journal is invalid")
                if (
                    self._records_signature is None
                    and records == ()
                    and current.st_size != 0
                ):
                    raise ValueError("transaction journal is invalid")
                _write_all(descriptor, content)
                os.fsync(descriptor)
                current = os.fstat(descriptor)
                signature = (
                    current.st_dev,
                    current.st_ino,
                    current.st_size,
                    current.st_mtime_ns,
                )
            finally:
                os.close(descriptor)
            os.fsync(root_descriptor)
        finally:
            os.close(root_descriptor)
        self._records_cache = (*records, record)
        self._records_signature = signature
        if phase is not None:
            self._latest_phase_cache = phase
        return record

    def write_blob(self, relative_path: str, content: bytes) -> str:
        if type(content) is not bytes or len(content) > _MAX_BLOB_BYTES:
            raise ValueError("transaction journal is invalid")
        parts = _relative_parts(relative_path)
        parent_descriptor = _open_relative_parent(
            self._root,
            parts[:-1],
            create=True,
        )
        try:
            _write_new_file_at(parent_descriptor, parts[-1], content)
        finally:
            os.close(parent_descriptor)
        digest = hashlib.sha256(content).hexdigest()
        if self.read_blob(relative_path) != content:
            raise ValueError("transaction journal is invalid")
        return digest

    def read_blob(self, relative_path: str) -> bytes:
        parts = _relative_parts(relative_path)
        parent_descriptor = _open_relative_parent(
            self._root,
            parts[:-1],
            create=False,
        )
        try:
            content, _ = _read_bounded_at(
                parent_descriptor,
                parts[-1],
                _MAX_BLOB_BYTES,
            )
            return content
        except (OSError, ValueError):
            raise ValueError("transaction journal is invalid") from None
        finally:
            os.close(parent_descriptor)


def has_blocking_transaction(transaction_root: Path) -> bool:
    if not os.path.lexists(transaction_root):
        return False
    root = _validate_directory(transaction_root.absolute())
    root_descriptor = _open_validated_directory(root)
    try:
        children = os.scandir(root_descriptor)
    except OSError:
        os.close(root_descriptor)
        raise ValueError("transaction journal is invalid") from None
    try:
        with children:
            inspected = 0
            for directory_entry in children:
                inspected += 1
                if inspected > _MAX_TRANSACTION_DIRECTORIES:
                    return True
                if not directory_entry.name.startswith("txn-"):
                    continue
                child = root / directory_entry.name
                try:
                    status = directory_entry.stat(follow_symlinks=False)
                    if (
                        stat.S_ISLNK(status.st_mode)
                        or not stat.S_ISDIR(status.st_mode)
                    ):
                        return True
                    child_descriptor = os.open(
                        directory_entry.name,
                        _DIRECTORY_FLAGS,
                        dir_fd=root_descriptor,
                    )
                    try:
                        current = os.fstat(child_descriptor)
                        if (
                            current.st_dev != status.st_dev
                            or current.st_ino != status.st_ino
                            or current.st_uid != os.geteuid()
                            or current.st_mode & 0o077
                        ):
                            return True
                        content, _ = _read_bounded_at(
                            child_descriptor,
                            "plan.json",
                            _MAX_PLAN_BYTES,
                        )
                    finally:
                        os.close(child_descriptor)
                    plan = parse_apply_plan(content)
                    journal = ApplyJournal(child, plan.transaction_id)
                    phase = journal.latest_phase
                except (OSError, ValueError):
                    return True
                if phase not in {
                    ApplyPhase.APPLIED,
                    ApplyPhase.ROLLED_BACK,
                }:
                    return True
    finally:
        os.close(root_descriptor)
    return False


def enumerate_apply_journals(
    transaction_root: Path,
    *,
    limit: int,
) -> tuple[JournalSnapshot, ...]:
    """Return validated journal metadata without changing disk state."""

    if (
        not isinstance(transaction_root, Path)
        or type(limit) is not int
        or limit < 1
        or limit > _MAX_TRANSACTION_DIRECTORIES
    ):
        raise ValueError("journal enumeration is invalid")
    if not os.path.lexists(transaction_root):
        return ()
    try:
        root = _validate_directory(transaction_root.absolute())
        root_descriptor = _open_validated_directory(root)
    except (OSError, ValueError):
        raise JournalEnumerationError(
            "transaction journal enumeration failed"
        ) from None
    try:
        try:
            entries = os.scandir(root_descriptor)
        except OSError:
            raise JournalEnumerationError(
                "transaction journal enumeration failed"
            ) from None
        names: list[str] = []
        inspected = 0
        try:
            with entries:
                for entry in entries:
                    inspected += 1
                    if inspected > _MAX_TRANSACTION_DIRECTORIES:
                        raise JournalEnumerationError(
                            "transaction journal enumeration is bounded"
                        )
                    if not entry.name.startswith("txn-"):
                        continue
                    names.append(entry.name)
                    if len(names) > limit:
                        raise JournalEnumerationError(
                            "transaction journal enumeration exceeds limit"
                        )
        except OSError:
            raise JournalEnumerationError(
                "transaction journal enumeration failed"
            ) from None

        snapshots: list[JournalSnapshot] = []
        transaction_ids: set[str] = set()
        for name in sorted(names):
            child = root / name
            try:
                status = os.stat(
                    name,
                    dir_fd=root_descriptor,
                    follow_symlinks=False,
                )
                if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(
                    status.st_mode
                ):
                    raise ValueError
                child_descriptor = os.open(
                    name,
                    _DIRECTORY_FLAGS,
                    dir_fd=root_descriptor,
                )
                try:
                    current = os.fstat(child_descriptor)
                    if (
                        current.st_dev != status.st_dev
                        or current.st_ino != status.st_ino
                        or current.st_uid != os.geteuid()
                        or current.st_mode & 0o077
                    ):
                        raise ValueError
                    content, _ = _read_bounded_at(
                        child_descriptor,
                        "plan.json",
                        _MAX_PLAN_BYTES,
                    )
                finally:
                    os.close(child_descriptor)
                plan = parse_apply_plan(content)
                if (
                    name != _transaction_name(plan.transaction_id)
                    or plan.transaction_id in transaction_ids
                ):
                    raise ValueError
                journal = ApplyJournal(child, plan.transaction_id)
                phase = journal.latest_phase
                if phase is None:
                    raise ValueError
            except (OSError, ValueError):
                raise JournalEnumerationError(
                    "transaction journal enumeration found invalid evidence"
                ) from None
            snapshots.append(
                JournalSnapshot(
                    transaction_id=plan.transaction_id,
                    journal_reference=name,
                    phase=phase,
                    plan_digest=plan.digest,
                    blocking=phase
                    not in {ApplyPhase.APPLIED, ApplyPhase.ROLLED_BACK},
                )
            )
            transaction_ids.add(plan.transaction_id)
        return tuple(snapshots)
    finally:
        os.close(root_descriptor)


__all__ = [
    "ApplyJournal",
    "JournalEnumerationError",
    "JournalSnapshot",
    "enumerate_apply_journals",
]
