"""Persistent, CAS-protected execution ownership leases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import sqlite3

from coding_harness.domain.enums import TaskState


class LeasePurpose(StrEnum):
    EXECUTION = "EXECUTION"
    RECOVERY = "RECOVERY"


class LeaseStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RECOVERY_PENDING = "RECOVERY_PENDING"
    RELEASED = "RELEASED"


class LeaseError(RuntimeError):
    pass


class LeaseConflict(LeaseError):
    pass


class LeasePersistenceError(LeaseError):
    pass


@dataclass(frozen=True, slots=True)
class ReleaseEvidence:
    container_terminal: bool
    file_effects_terminal: bool
    cleanup_verified: bool

    def __post_init__(self) -> None:
        if any(
            type(value) is not bool
            for value in (
                self.container_terminal,
                self.file_effects_terminal,
                self.cleanup_verified,
            )
        ):
            raise ValueError("release evidence is invalid")

    @property
    def permits_release(self) -> bool:
        return (
            self.container_terminal
            and self.file_effects_terminal
            and self.cleanup_verified
        )


@dataclass(frozen=True, slots=True)
class ExecutionLease:
    lease_id: str
    slot_identity: str
    task_id: str
    run_id: str
    owner_identity: str
    purpose: LeasePurpose
    acquired_at: int
    last_progress_at: int
    phase: TaskState
    status: LeaseStatus
    revision: int


_LEASE_COLUMNS = (
    "lease_id, slot_identity, task_id, run_id, owner_identity, purpose, "
    "acquired_at, last_progress_at, phase, status, revision"
)
_GLOBAL_SLOT_IDENTITY = "execution:global"


def _valid_identity(value: object) -> bool:
    return type(value) is str and bool(value) and "\0" not in value


def _valid_time(value: object) -> bool:
    return type(value) is int and value >= 0


def _lease_from_row(row: tuple[object, ...]) -> ExecutionLease:
    try:
        lease = ExecutionLease(
            lease_id=row[0],
            slot_identity=row[1],
            task_id=row[2],
            run_id=row[3],
            owner_identity=row[4],
            purpose=LeasePurpose(row[5]),
            acquired_at=row[6],
            last_progress_at=row[7],
            phase=TaskState(row[8]),
            status=LeaseStatus(row[9]),
            revision=row[10],
        )
    except (IndexError, TypeError, ValueError):
        raise LeasePersistenceError("persisted lease is invalid") from None
    if (
        not _valid_identity(lease.lease_id)
        or not _valid_identity(lease.slot_identity)
        or not _valid_identity(lease.task_id)
        or not _valid_identity(lease.run_id)
        or not _valid_identity(lease.owner_identity)
        or not _valid_time(lease.acquired_at)
        or not _valid_time(lease.last_progress_at)
        or lease.last_progress_at < lease.acquired_at
        or type(lease.revision) is not int
        or lease.revision < 1
    ):
        raise LeasePersistenceError("persisted lease is invalid")
    return lease


class ExecutionLeaseService:
    """Own the single persistent execution slot without mutating Task state."""

    def __init__(
        self,
        *,
        database_path: Path,
        heartbeat_timeout: int,
    ) -> None:
        if (
            not isinstance(database_path, Path)
            or type(heartbeat_timeout) is not int
            or heartbeat_timeout < 1
        ):
            raise ValueError("execution lease service is invalid")
        self._database_path = database_path
        self._heartbeat_timeout = heartbeat_timeout
        self._slot_identity = _GLOBAL_SLOT_IDENTITY

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(self._database_path, timeout=5)
            connection.execute("PRAGMA foreign_keys = ON")
            return connection
        except sqlite3.Error:
            raise LeasePersistenceError(
                "execution lease persistence is unavailable"
            ) from None

    def _open_lease(
        self,
        connection: sqlite3.Connection,
    ) -> ExecutionLease | None:
        rows = connection.execute(
            f"SELECT {_LEASE_COLUMNS} FROM execution_leases "
            "WHERE slot_identity = ? "
            "AND status IN ('ACTIVE', 'RECOVERY_PENDING') "
            "ORDER BY acquired_at, lease_id LIMIT 2",
            (self._slot_identity,),
        ).fetchall()
        if len(rows) > 1:
            raise LeasePersistenceError("execution lease slot is invalid")
        return None if not rows else _lease_from_row(rows[0])

    @staticmethod
    def _audit(
        connection: sqlite3.Connection,
        *,
        task_id: str,
        event_kind: str,
        lease_id: str,
        occurred_at: int,
    ) -> None:
        connection.execute(
            "INSERT INTO audit_events"
            "(task_id, event_kind, subject_identity, occurred_at, "
            "source_state, target_state, transition_trigger, "
            "transition_reason, permitted) "
            "VALUES(?, ?, ?, ?, NULL, NULL, NULL, NULL, NULL)",
            (task_id, event_kind, lease_id, occurred_at),
        )

    @staticmethod
    def _begin(connection: sqlite3.Connection) -> None:
        connection.execute("BEGIN IMMEDIATE")

    @staticmethod
    def _rollback(connection: sqlite3.Connection) -> None:
        if connection.in_transaction:
            connection.rollback()

    def current(self) -> ExecutionLease | None:
        connection = self._connect()
        try:
            return self._open_lease(connection)
        except sqlite3.Error:
            raise LeasePersistenceError(
                "execution lease inspection failed"
            ) from None
        finally:
            connection.close()

    def inspect(self, *, lease_id: str) -> ExecutionLease | None:
        if not _valid_identity(lease_id):
            raise ValueError("execution lease query is invalid")
        connection = self._connect()
        try:
            row = connection.execute(
                f"SELECT {_LEASE_COLUMNS} FROM execution_leases "
                "WHERE lease_id = ?",
                (lease_id,),
            ).fetchone()
        except sqlite3.Error:
            raise LeasePersistenceError(
                "execution lease inspection failed"
            ) from None
        finally:
            connection.close()
        return None if row is None else _lease_from_row(row)

    def acquire(
        self,
        *,
        lease_id: str,
        task_id: str,
        run_id: str,
        owner_identity: str,
        purpose: LeasePurpose,
        phase: TaskState,
        now: int,
    ) -> ExecutionLease:
        if (
            not all(
                _valid_identity(value)
                for value in (lease_id, task_id, run_id, owner_identity)
            )
            or purpose is not LeasePurpose.EXECUTION
            or type(phase) is not TaskState
            or not _valid_time(now)
        ):
            raise ValueError("execution lease acquisition is invalid")
        connection = self._connect()
        try:
            self._begin(connection)
            if self._open_lease(connection) is not None:
                raise LeaseConflict("execution slot is busy")
            connection.execute(
                "INSERT INTO execution_leases"
                "(lease_id, slot_identity, task_id, run_id, owner_identity, "
                "purpose, acquired_at, last_progress_at, phase, status, "
                "revision) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
                (
                    lease_id,
                    self._slot_identity,
                    task_id,
                    run_id,
                    owner_identity,
                    purpose.value,
                    now,
                    now,
                    phase.value,
                    LeaseStatus.ACTIVE.value,
                ),
            )
            connection.commit()
            return ExecutionLease(
                lease_id=lease_id,
                slot_identity=self._slot_identity,
                task_id=task_id,
                run_id=run_id,
                owner_identity=owner_identity,
                purpose=purpose,
                acquired_at=now,
                last_progress_at=now,
                phase=phase,
                status=LeaseStatus.ACTIVE,
                revision=1,
            )
        except LeaseConflict:
            self._rollback(connection)
            raise
        except sqlite3.IntegrityError:
            self._rollback(connection)
            raise LeaseConflict("execution slot is busy") from None
        except sqlite3.Error:
            self._rollback(connection)
            raise LeasePersistenceError(
                "execution lease acquisition failed"
            ) from None
        finally:
            connection.close()

    def heartbeat(
        self,
        *,
        lease_id: str,
        owner_identity: str,
        expected_revision: int,
        phase: TaskState,
        now: int,
    ) -> ExecutionLease:
        if (
            not _valid_identity(lease_id)
            or not _valid_identity(owner_identity)
            or type(expected_revision) is not int
            or expected_revision < 1
            or type(phase) is not TaskState
            or not _valid_time(now)
        ):
            raise ValueError("execution lease heartbeat is invalid")
        connection = self._connect()
        try:
            self._begin(connection)
            current = self._open_lease(connection)
            if (
                current is None
                or current.status is not LeaseStatus.ACTIVE
                or current.lease_id != lease_id
                or current.owner_identity != owner_identity
                or current.revision != expected_revision
                or now < current.last_progress_at
            ):
                raise LeaseConflict("execution lease heartbeat conflict")
            cursor = connection.execute(
                "UPDATE execution_leases "
                "SET last_progress_at = ?, phase = ?, revision = revision + 1 "
                "WHERE lease_id = ? AND owner_identity = ? "
                "AND status = 'ACTIVE' AND revision = ?",
                (
                    now,
                    phase.value,
                    lease_id,
                    owner_identity,
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise LeaseConflict("execution lease heartbeat conflict")
            connection.commit()
            return ExecutionLease(
                lease_id=current.lease_id,
                slot_identity=current.slot_identity,
                task_id=current.task_id,
                run_id=current.run_id,
                owner_identity=current.owner_identity,
                purpose=current.purpose,
                acquired_at=current.acquired_at,
                last_progress_at=now,
                phase=phase,
                status=current.status,
                revision=current.revision + 1,
            )
        except LeaseConflict:
            self._rollback(connection)
            raise
        except sqlite3.Error:
            self._rollback(connection)
            raise LeasePersistenceError(
                "execution lease heartbeat failed"
            ) from None
        finally:
            connection.close()

    def mark_expired(self, *, now: int) -> ExecutionLease:
        if not _valid_time(now):
            raise ValueError("execution lease expiration intent is invalid")
        connection = self._connect()
        try:
            self._begin(connection)
            current = self._open_lease(connection)
            if (
                current is None
                or current.status is not LeaseStatus.ACTIVE
                or now - current.last_progress_at <= self._heartbeat_timeout
            ):
                raise LeaseConflict("execution lease is not expired")
            cursor = connection.execute(
                "UPDATE execution_leases "
                "SET status = 'RECOVERY_PENDING', revision = revision + 1 "
                "WHERE lease_id = ? AND status = 'ACTIVE' AND revision = ?",
                (current.lease_id, current.revision),
            )
            if cursor.rowcount != 1:
                raise LeaseConflict("execution lease expiration conflict")
            self._audit(
                connection,
                task_id=current.task_id,
                event_kind="EXECUTION_LEASE_STALE",
                lease_id=current.lease_id,
                occurred_at=now,
            )
            connection.commit()
            return ExecutionLease(
                lease_id=current.lease_id,
                slot_identity=current.slot_identity,
                task_id=current.task_id,
                run_id=current.run_id,
                owner_identity=current.owner_identity,
                purpose=current.purpose,
                acquired_at=current.acquired_at,
                last_progress_at=current.last_progress_at,
                phase=current.phase,
                status=LeaseStatus.RECOVERY_PENDING,
                revision=current.revision + 1,
            )
        except LeaseConflict:
            self._rollback(connection)
            raise
        except sqlite3.Error:
            self._rollback(connection)
            raise LeasePersistenceError(
                "execution lease expiration failed"
            ) from None
        finally:
            connection.close()

    def release(
        self,
        *,
        lease_id: str,
        owner_identity: str,
        expected_revision: int,
        evidence: ReleaseEvidence,
        now: int,
    ) -> ExecutionLease:
        if (
            not _valid_identity(lease_id)
            or not _valid_identity(owner_identity)
            or type(expected_revision) is not int
            or expected_revision < 1
            or type(evidence) is not ReleaseEvidence
            or not _valid_time(now)
        ):
            raise ValueError("execution lease release is invalid")
        if not evidence.permits_release:
            raise LeaseConflict("execution lease release evidence is unsafe")
        connection = self._connect()
        try:
            self._begin(connection)
            current = self._open_lease(connection)
            if (
                current is None
                or current.status is not LeaseStatus.ACTIVE
                or current.lease_id != lease_id
                or current.owner_identity != owner_identity
                or current.revision != expected_revision
                or now < current.last_progress_at
            ):
                raise LeaseConflict("execution lease release conflict")
            cursor = connection.execute(
                "UPDATE execution_leases "
                "SET status = 'RELEASED', revision = revision + 1 "
                "WHERE lease_id = ? AND owner_identity = ? "
                "AND status = 'ACTIVE' AND revision = ?",
                (lease_id, owner_identity, expected_revision),
            )
            if cursor.rowcount != 1:
                raise LeaseConflict("execution lease release conflict")
            self._audit(
                connection,
                task_id=current.task_id,
                event_kind="EXECUTION_LEASE_RELEASED",
                lease_id=current.lease_id,
                occurred_at=now,
            )
            connection.commit()
            return ExecutionLease(
                lease_id=current.lease_id,
                slot_identity=current.slot_identity,
                task_id=current.task_id,
                run_id=current.run_id,
                owner_identity=current.owner_identity,
                purpose=current.purpose,
                acquired_at=current.acquired_at,
                last_progress_at=current.last_progress_at,
                phase=current.phase,
                status=LeaseStatus.RELEASED,
                revision=current.revision + 1,
            )
        except LeaseConflict:
            self._rollback(connection)
            raise
        except sqlite3.Error:
            self._rollback(connection)
            raise LeasePersistenceError(
                "execution lease release failed"
            ) from None
        finally:
            connection.close()

    def acquire_recovery(
        self,
        *,
        lease_id: str,
        task_id: str,
        run_id: str,
        owner_identity: str,
        phase: TaskState,
        expected_pending_revision: int,
        now: int,
    ) -> ExecutionLease:
        if (
            not all(
                _valid_identity(value)
                for value in (lease_id, task_id, run_id, owner_identity)
            )
            or type(phase) is not TaskState
            or type(expected_pending_revision) is not int
            or expected_pending_revision < 1
            or not _valid_time(now)
        ):
            raise ValueError("recovery lease acquisition is invalid")
        connection = self._connect()
        try:
            self._begin(connection)
            pending = self._open_lease(connection)
            if (
                pending is None
                or pending.status is not LeaseStatus.RECOVERY_PENDING
                or pending.task_id != task_id
                or pending.run_id != run_id
                or pending.revision != expected_pending_revision
                or pending.lease_id == lease_id
            ):
                raise LeaseConflict("recovery lease acquisition conflict")
            cursor = connection.execute(
                "UPDATE execution_leases "
                "SET status = 'RELEASED', revision = revision + 1 "
                "WHERE lease_id = ? AND status = 'RECOVERY_PENDING' "
                "AND revision = ?",
                (pending.lease_id, expected_pending_revision),
            )
            if cursor.rowcount != 1:
                raise LeaseConflict("recovery lease acquisition conflict")
            connection.execute(
                "INSERT INTO execution_leases"
                "(lease_id, slot_identity, task_id, run_id, owner_identity, "
                "purpose, acquired_at, last_progress_at, phase, status, "
                "revision) VALUES(?, ?, ?, ?, ?, 'RECOVERY', ?, ?, ?, "
                "'ACTIVE', 1)",
                (
                    lease_id,
                    self._slot_identity,
                    task_id,
                    run_id,
                    owner_identity,
                    now,
                    now,
                    phase.value,
                ),
            )
            self._audit(
                connection,
                task_id=task_id,
                event_kind="EXECUTION_LEASE_RECOVERY_ACQUIRED",
                lease_id=lease_id,
                occurred_at=now,
            )
            connection.commit()
            return ExecutionLease(
                lease_id=lease_id,
                slot_identity=self._slot_identity,
                task_id=task_id,
                run_id=run_id,
                owner_identity=owner_identity,
                purpose=LeasePurpose.RECOVERY,
                acquired_at=now,
                last_progress_at=now,
                phase=phase,
                status=LeaseStatus.ACTIVE,
                revision=1,
            )
        except LeaseConflict:
            self._rollback(connection)
            raise
        except sqlite3.IntegrityError:
            self._rollback(connection)
            raise LeaseConflict("recovery lease acquisition conflict") from None
        except sqlite3.Error:
            self._rollback(connection)
            raise LeasePersistenceError(
                "recovery lease acquisition failed"
            ) from None
        finally:
            connection.close()


__all__ = [
    "ExecutionLease",
    "ExecutionLeaseService",
    "LeaseConflict",
    "LeaseError",
    "LeasePersistenceError",
    "LeasePurpose",
    "LeaseStatus",
    "ReleaseEvidence",
]
