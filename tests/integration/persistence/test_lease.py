"""WP-17 process lock and SQLite execution lease contracts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import importlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from threading import Barrier
from types import SimpleNamespace

import pytest

from coding_harness.domain.enums import TaskState
from coding_harness.persistence.migrations import MigrationRunner
from coding_harness.persistence.sqlite_store import SQLiteHarnessStore


OWNED_REQUIREMENTS = (
    "PST-015",
    "PST-016",
    "PST-017",
    "PST-019",
    "PST-020",
)
_EXPECTED_INTERFACE = (
    "EXPECTED_INTERFACE_MISSING: WP-17 lock and lease contract"
)
_EXPECTED_BEHAVIOR = (
    "EXPECTED_BEHAVIOR_MISSING: WP-17 lock and lease contract"
)


def _module(name: str):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        if error.name == name or name.startswith(error.name + "."):
            pytest.fail(
                f"{_EXPECTED_INTERFACE}: missing {name}",
                pytrace=False,
            )
        raise


def _api() -> SimpleNamespace:
    process_lock = _module("coding_harness.persistence.process_lock")
    lease = _module("coding_harness.persistence.lease")
    required = {
        "ProcessLock": getattr(process_lock, "ProcessLock", None),
        "ProcessLockOutcome": getattr(
            process_lock,
            "ProcessLockOutcome",
            None,
        ),
        "ExecutionLeaseService": getattr(
            lease,
            "ExecutionLeaseService",
            None,
        ),
        "ExecutionLease": getattr(lease, "ExecutionLease", None),
        "LeasePurpose": getattr(lease, "LeasePurpose", None),
        "LeaseStatus": getattr(lease, "LeaseStatus", None),
        "LeaseConflict": getattr(lease, "LeaseConflict", None),
        "ReleaseEvidence": getattr(lease, "ReleaseEvidence", None),
    }
    missing = tuple(name for name, value in required.items() if value is None)
    if missing:
        pytest.fail(
            _EXPECTED_INTERFACE + ": missing " + ", ".join(missing),
            pytrace=False,
        )
    return SimpleNamespace(**required)


def _migration_directory() -> Path:
    module = importlib.import_module(
        "coding_harness.persistence.sqlite_store"
    )
    return Path(module.__file__).parent / "sql"


def _runtime(
    api: SimpleNamespace,
    tmp_path: Path,
    *,
    task_ids: tuple[str, ...] = ("task:wp17",),
):
    database = tmp_path / "harness.sqlite3"
    MigrationRunner(
        database_path=database,
        migration_directory=_migration_directory(),
    ).run()
    store = SQLiteHarnessStore(database_path=database)
    for order, task_id in enumerate(task_ids, start=1):
        store.create_task(
            task_id=task_id,
            initial_state=TaskState.DRAFT,
            occurred_at=order,
        )
    service = api.ExecutionLeaseService(
        database_path=database,
        heartbeat_timeout=10,
    )
    return store, service, database


def _acquire_execution(
    api: SimpleNamespace,
    service,
    *,
    lease_id: str = "lease:wp17:a",
    task_id: str = "task:wp17",
    run_id: str = "run:wp17:1",
    owner_identity: str = "owner:wp17:a",
    now: int = 10,
    phase: TaskState = TaskState.EXECUTING,
):
    return service.acquire(
        lease_id=lease_id,
        task_id=task_id,
        run_id=run_id,
        owner_identity=owner_identity,
        purpose=api.LeasePurpose.EXECUTION,
        phase=phase,
        now=now,
    )


def _safe_release(api: SimpleNamespace):
    return api.ReleaseEvidence(
        container_terminal=True,
        file_effects_terminal=True,
        cleanup_verified=True,
    )


def _unsafe_release(api: SimpleNamespace):
    return api.ReleaseEvidence(
        container_terminal=True,
        file_effects_terminal=False,
        cleanup_verified=True,
    )


def _expire(api: SimpleNamespace, service):
    active = _acquire_execution(api, service)
    pending = service.mark_expired(now=21)
    assert active.revision == 1
    assert pending.revision == 2
    assert pending.status is api.LeaseStatus.RECOVERY_PENDING
    return pending


def test_single_serve(tmp_path: Path) -> None:
    api = _api()
    lock_path = tmp_path / "serve.lock"
    lock_path.write_text("forged owner metadata", encoding="utf-8")
    first = api.ProcessLock(lock_path=lock_path)
    second = api.ProcessLock(lock_path=lock_path)
    first_held = False
    successor = None
    successor_held = False
    try:
        assert first.acquire() is api.ProcessLockOutcome.ACQUIRED
        first_held = True
        assert second.acquire() is api.ProcessLockOutcome.BUSY
        first.release()
        first_held = False
        successor = api.ProcessLock(lock_path=lock_path)
        assert successor.acquire() is api.ProcessLockOutcome.ACQUIRED
        successor_held = True
    finally:
        if successor_held:
            successor.release()
        if first_held:
            first.release()


def test_lock_contention_does_not_change_task_state(
    tmp_path: Path,
) -> None:
    api = _api()
    store, _, _ = _runtime(api, tmp_path)
    lock_path = tmp_path / "serve.lock"
    first = api.ProcessLock(lock_path=lock_path)
    second = api.ProcessLock(lock_path=lock_path)
    held = False
    try:
        assert first.acquire() is api.ProcessLockOutcome.ACQUIRED
        held = True
        assert second.acquire() is api.ProcessLockOutcome.BUSY
        assert (
            store.get_task_state(task_id="task:wp17")
            is TaskState.DRAFT
        )
    finally:
        if held:
            first.release()


def test_lock_lease_separate(tmp_path: Path) -> None:
    api = _api()
    _, service, _ = _runtime(api, tmp_path)
    lock_path = tmp_path / "serve.lock"
    process_lock = api.ProcessLock(lock_path=lock_path)
    competitor = api.ProcessLock(lock_path=lock_path)
    held = False
    try:
        assert process_lock.acquire() is api.ProcessLockOutcome.ACQUIRED
        held = True
        lease = _acquire_execution(api, service)
        assert type(lease) is api.ExecutionLease
        assert lease.owner_identity == "owner:wp17:a"
        assert competitor.acquire() is api.ProcessLockOutcome.BUSY
    finally:
        if held:
            process_lock.release()


def test_single_execution_lease(tmp_path: Path) -> None:
    api = _api()
    _, first_service, database = _runtime(api, tmp_path)
    first = _acquire_execution(api, first_service)
    competing_service = api.ExecutionLeaseService(
        database_path=database,
        heartbeat_timeout=10,
    )
    with pytest.raises(api.LeaseConflict):
        _acquire_execution(
            api,
            competing_service,
            lease_id="lease:wp17:b",
            task_id="task:wp17",
            run_id="run:wp17:2",
            owner_identity="owner:wp17:b",
            now=11,
        )
    assert competing_service.current() == first


def test_lease_binding(tmp_path: Path) -> None:
    api = _api()
    _, service, _ = _runtime(api, tmp_path)
    lease = _acquire_execution(api, service)
    assert type(lease) is api.ExecutionLease
    assert lease.lease_id == "lease:wp17:a"
    assert lease.task_id == "task:wp17"
    assert lease.run_id == "run:wp17:1"
    assert lease.owner_identity == "owner:wp17:a"
    assert lease.purpose is api.LeasePurpose.EXECUTION
    assert lease.acquired_at == 10
    assert lease.last_progress_at == 10
    assert lease.phase is TaskState.EXECUTING
    assert lease.status is api.LeaseStatus.ACTIVE
    assert lease.revision == 1


def test_heartbeat(tmp_path: Path) -> None:
    api = _api()
    _, service, _ = _runtime(api, tmp_path)
    active = _acquire_execution(api, service)
    with pytest.raises(api.LeaseConflict):
        service.heartbeat(
            lease_id=active.lease_id,
            owner_identity="owner:wp17:b",
            expected_revision=active.revision,
            phase=TaskState.VERIFYING,
            now=12,
        )
    updated = service.heartbeat(
        lease_id=active.lease_id,
        owner_identity=active.owner_identity,
        expected_revision=active.revision,
        phase=TaskState.VERIFYING,
        now=12,
    )
    assert updated.revision == 2
    assert updated.last_progress_at == 12
    assert updated.phase is TaskState.VERIFYING
    with pytest.raises(api.LeaseConflict):
        service.heartbeat(
            lease_id=active.lease_id,
            owner_identity=active.owner_identity,
            expected_revision=active.revision,
            phase=TaskState.VERIFYING,
            now=13,
        )
    assert service.current() == updated


def test_stale_owner_cannot_release(tmp_path: Path) -> None:
    api = _api()
    _, service, _ = _runtime(api, tmp_path)
    active = _acquire_execution(api, service)
    updated = service.heartbeat(
        lease_id=active.lease_id,
        owner_identity=active.owner_identity,
        expected_revision=active.revision,
        phase=TaskState.VERIFYING,
        now=12,
    )
    with pytest.raises(api.LeaseConflict):
        service.release(
            lease_id=updated.lease_id,
            owner_identity="owner:wp17:b",
            expected_revision=updated.revision,
            evidence=_safe_release(api),
            now=13,
        )
    with pytest.raises(api.LeaseConflict):
        service.release(
            lease_id=active.lease_id,
            owner_identity=active.owner_identity,
            expected_revision=active.revision,
            evidence=_safe_release(api),
            now=13,
        )
    assert service.current() == updated


def test_stale_audit_only(tmp_path: Path) -> None:
    api = _api()
    store, service, _ = _runtime(api, tmp_path)
    active = _acquire_execution(api, service)
    before = store.audit_events(task_id=active.task_id)
    pending = service.mark_expired(now=21)
    after = store.audit_events(task_id=active.task_id)
    assert pending.status is api.LeaseStatus.RECOVERY_PENDING
    assert pending.task_id == active.task_id
    assert pending.run_id == active.run_id
    assert pending.owner_identity == active.owner_identity
    assert pending.revision == active.revision + 1
    assert after[:-1] == before
    assert after[-1].event_kind == "EXECUTION_LEASE_STALE"
    assert after[-1].subject_identity == active.lease_id
    assert (
        store.get_task_state(task_id=active.task_id)
        is TaskState.DRAFT
    )
    with pytest.raises(api.LeaseConflict):
        _acquire_execution(
            api,
            service,
            lease_id="lease:wp17:b",
            run_id="run:wp17:2",
            owner_identity="owner:wp17:b",
            now=22,
        )
    assert service.current() == pending


def test_safe_release(tmp_path: Path) -> None:
    api = _api()
    store, service, _ = _runtime(api, tmp_path)
    active = _acquire_execution(api, service)
    with pytest.raises(api.LeaseConflict):
        service.release(
            lease_id=active.lease_id,
            owner_identity=active.owner_identity,
            expected_revision=active.revision,
            evidence=_unsafe_release(api),
            now=11,
        )
    assert service.current() == active
    released = service.release(
        lease_id=active.lease_id,
        owner_identity=active.owner_identity,
        expected_revision=active.revision,
        evidence=_safe_release(api),
        now=11,
    )
    assert released.status is api.LeaseStatus.RELEASED
    assert service.current() is None
    assert (
        store.get_task_state(task_id=active.task_id)
        is TaskState.DRAFT
    )


def test_recovery_priority(tmp_path: Path) -> None:
    api = _api()
    _, service, _ = _runtime(
        api,
        tmp_path,
        task_ids=("task:wp17", "task:wp17:other"),
    )
    pending = _expire(api, service)
    with pytest.raises(api.LeaseConflict):
        service.acquire_recovery(
            lease_id="lease:wp17:recovery-wrong-run",
            task_id=pending.task_id,
            run_id="run:wp17:other",
            owner_identity="owner:wp17:recovery",
            phase=TaskState.ROLLING_BACK,
            expected_pending_revision=pending.revision,
            now=22,
        )
    with pytest.raises(api.LeaseConflict):
        service.acquire_recovery(
            lease_id="lease:wp17:recovery-wrong-task",
            task_id="task:wp17:other",
            run_id=pending.run_id,
            owner_identity="owner:wp17:recovery",
            phase=TaskState.ROLLING_BACK,
            expected_pending_revision=pending.revision,
            now=22,
        )
    recovery = service.acquire_recovery(
        lease_id="lease:wp17:recovery",
        task_id=pending.task_id,
        run_id=pending.run_id,
        owner_identity="owner:wp17:recovery",
        phase=TaskState.ROLLING_BACK,
        expected_pending_revision=pending.revision,
        now=22,
    )
    assert recovery.purpose is api.LeasePurpose.RECOVERY
    assert recovery.task_id == pending.task_id
    assert recovery.run_id == pending.run_id
    assert recovery.owner_identity == "owner:wp17:recovery"
    assert recovery.status is api.LeaseStatus.ACTIVE


def test_recovery_blocks_execution(tmp_path: Path) -> None:
    api = _api()
    _, service, _ = _runtime(
        api,
        tmp_path,
        task_ids=("task:wp17", "task:wp17:other"),
    )
    pending = _expire(api, service)
    with pytest.raises(api.LeaseConflict):
        _acquire_execution(
            api,
            service,
            lease_id="lease:wp17:other",
            task_id="task:wp17:other",
            run_id="run:wp17:other",
            owner_identity="owner:wp17:other",
            now=22,
        )
    recovery = service.acquire_recovery(
        lease_id="lease:wp17:recovery",
        task_id=pending.task_id,
        run_id=pending.run_id,
        owner_identity="owner:wp17:recovery",
        phase=TaskState.ROLLING_BACK,
        expected_pending_revision=pending.revision,
        now=22,
    )
    with pytest.raises(api.LeaseConflict):
        _acquire_execution(
            api,
            service,
            lease_id="lease:wp17:late",
            task_id="task:wp17:other",
            run_id="run:wp17:late",
            owner_identity="owner:wp17:late",
            now=23,
        )
    assert recovery.purpose is api.LeasePurpose.RECOVERY
    assert service.current() == recovery


def test_migration_003_required(tmp_path: Path) -> None:
    migration = _migration_directory() / "003_execution_lease.sql"
    assert migration.is_file(), (
        f"{_EXPECTED_BEHAVIOR}: missing {migration.name}"
    )
    database = tmp_path / "migration.sqlite3"
    MigrationRunner(
        database_path=database,
        migration_directory=_migration_directory(),
    ).run()
    with sqlite3.connect(database) as connection:
        applied = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        table = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name = 'execution_leases'"
        ).fetchone()
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(execution_leases)"
            ).fetchall()
        }
    assert applied == [(1,), (2,), (3,)]
    assert table == ("execution_leases",)
    assert {
        "lease_id",
        "task_id",
        "run_id",
        "owner_identity",
        "purpose",
        "acquired_at",
        "last_progress_at",
        "phase",
        "status",
        "revision",
    } <= columns


def test_global_slot_identity_cannot_be_overridden(
    tmp_path: Path,
) -> None:
    api = _api()
    _, _, database = _runtime(api, tmp_path)
    with pytest.raises(TypeError):
        api.ExecutionLeaseService(
            database_path=database,
            heartbeat_timeout=10,
            slot_identity="execution:alternate",
        )


def test_database_rejects_a_second_open_slot_identity(
    tmp_path: Path,
) -> None:
    api = _api()
    _, service, database = _runtime(api, tmp_path)
    active = _acquire_execution(api, service)
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO execution_leases"
                "(lease_id, slot_identity, task_id, run_id, "
                "owner_identity, purpose, acquired_at, "
                "last_progress_at, phase, status, revision) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "lease:wp17:forged-slot",
                    "execution:alternate",
                    active.task_id,
                    "run:wp17:forged-slot",
                    "owner:wp17:forged-slot",
                    "EXECUTION",
                    11,
                    11,
                    TaskState.EXECUTING.value,
                    "ACTIVE",
                    1,
                ),
            )
    assert service.current() == active


def test_concurrent_acquire_has_one_owner(tmp_path: Path) -> None:
    api = _api()
    _, _, database = _runtime(api, tmp_path)
    barrier = Barrier(2)

    def acquire(index: int) -> tuple[str, object | None]:
        service = api.ExecutionLeaseService(
            database_path=database,
            heartbeat_timeout=10,
        )
        barrier.wait(timeout=5)
        try:
            lease = _acquire_execution(
                api,
                service,
                lease_id=f"lease:wp17:concurrent:{index}",
                run_id=f"run:wp17:concurrent:{index}",
                owner_identity=f"owner:wp17:concurrent:{index}",
            )
        except api.LeaseConflict:
            return ("BUSY", None)
        return ("ACQUIRED", lease)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = tuple(executor.map(acquire, (1, 2)))
    outcomes = sorted(result[0] for result in results)
    assert outcomes == ["ACQUIRED", "BUSY"]
    winner = next(result[1] for result in results if result[1] is not None)
    service = api.ExecutionLeaseService(
        database_path=database,
        heartbeat_timeout=10,
    )
    assert service.current() == winner


def test_process_lock_is_released_after_process_crash(
    tmp_path: Path,
) -> None:
    api = _api()
    lock_path = tmp_path / "serve.lock"
    script = (
        "import os, sys\n"
        "from pathlib import Path\n"
        "from coding_harness.persistence.process_lock import ProcessLock\n"
        "lock = ProcessLock(lock_path=Path(sys.argv[1]))\n"
        "print(lock.acquire().value, flush=True)\n"
        "os._exit(17)\n"
    )
    child = subprocess.run(
        (sys.executable, "-c", script, str(lock_path)),
        check=False,
        capture_output=True,
        env={
            **os.environ,
            "PYTHONPATH": str(_migration_directory().parents[2]),
        },
        text=True,
        timeout=10,
    )
    assert child.returncode == 17
    assert child.stdout.strip() == "ACQUIRED"
    successor = api.ProcessLock(lock_path=lock_path)
    held = False
    try:
        assert successor.acquire() is api.ProcessLockOutcome.ACQUIRED
        held = True
    finally:
        if held:
            successor.release()


def test_old_owner_is_rejected_after_recovery_takeover(
    tmp_path: Path,
) -> None:
    api = _api()
    _, service, _ = _runtime(api, tmp_path)
    pending = _expire(api, service)
    recovery = service.acquire_recovery(
        lease_id="lease:wp17:recovery",
        task_id=pending.task_id,
        run_id=pending.run_id,
        owner_identity="owner:wp17:recovery",
        phase=TaskState.ROLLING_BACK,
        expected_pending_revision=pending.revision,
        now=22,
    )
    with pytest.raises(api.LeaseConflict):
        service.heartbeat(
            lease_id=pending.lease_id,
            owner_identity=pending.owner_identity,
            expected_revision=pending.revision,
            phase=TaskState.VERIFYING,
            now=23,
        )
    with pytest.raises(api.LeaseConflict):
        service.release(
            lease_id=pending.lease_id,
            owner_identity=pending.owner_identity,
            expected_revision=pending.revision,
            evidence=_safe_release(api),
            now=23,
        )
    assert service.current() == recovery


def _copy_migrations(
    *,
    target: Path,
    versions: tuple[int, ...],
) -> None:
    source = _migration_directory()
    target.mkdir()
    for version in versions:
        migration = next(source.glob(f"{version:03d}_*.sql"))
        (target / migration.name).write_bytes(migration.read_bytes())


def _seed_version_002(database: Path) -> None:
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO tasks"
            "(task_id, state, revision, created_at, updated_at) "
            "VALUES('task:wp17:upgrade', 'DRAFT', 1, 1, 1)"
        )
        connection.execute(
            "INSERT INTO audit_events"
            "(task_id, event_kind, subject_identity, occurred_at) "
            "VALUES('task:wp17:upgrade', 'TASK_CREATED', "
            "'task:wp17:upgrade', 1)"
        )
        connection.execute(
            "INSERT INTO domain_events"
            "(event_kind, occurred_at, task_id, entity_identity, "
            "entity_revision, payload, evidence_refs) "
            "VALUES('TASK_CREATED', 1, 'task:wp17:upgrade', "
            "'task:wp17:upgrade', 1, '[[\"initial_state\",\"DRAFT\"]]', "
            "'[]')"
        )


def test_migration_002_to_003_preserves_existing_data(
    tmp_path: Path,
) -> None:
    migrations = tmp_path / "migrations"
    _copy_migrations(target=migrations, versions=(1, 2))
    database = tmp_path / "upgrade.sqlite3"
    MigrationRunner(
        database_path=database,
        migration_directory=migrations,
    ).run()
    _seed_version_002(database)
    source_003 = _migration_directory() / "003_execution_lease.sql"
    (migrations / source_003.name).write_bytes(source_003.read_bytes())

    MigrationRunner(
        database_path=database,
        migration_directory=migrations,
    ).run()

    with sqlite3.connect(database) as connection:
        task = connection.execute(
            "SELECT task_id, state, revision FROM tasks"
        ).fetchall()
        audit = connection.execute(
            "SELECT task_id, event_kind, subject_identity "
            "FROM audit_events"
        ).fetchall()
        event = connection.execute(
            "SELECT task_id, event_kind, entity_identity "
            "FROM domain_events"
        ).fetchall()
        versions = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
    assert task == [("task:wp17:upgrade", "DRAFT", 1)]
    assert audit == [
        ("task:wp17:upgrade", "TASK_CREATED", "task:wp17:upgrade")
    ]
    assert event == [
        ("task:wp17:upgrade", "TASK_CREATED", "task:wp17:upgrade")
    ]
    assert versions == [(1,), (2,), (3,)]


def test_migration_003_failure_rolls_back_completely(
    tmp_path: Path,
) -> None:
    migrations = tmp_path / "migrations"
    _copy_migrations(target=migrations, versions=(1, 2))
    database = tmp_path / "rollback.sqlite3"
    MigrationRunner(
        database_path=database,
        migration_directory=migrations,
    ).run()
    _seed_version_002(database)
    (migrations / "003_execution_lease.sql").write_text(
        "CREATE TABLE execution_leases(partial INTEGER);\n"
        "INSERT INTO table_that_does_not_exist VALUES(1);\n",
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="migration"):
        MigrationRunner(
            database_path=database,
            migration_directory=migrations,
        ).run()

    with sqlite3.connect(database) as connection:
        versions = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        partial = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name = 'execution_leases'"
        ).fetchone()
        old_data = connection.execute(
            "SELECT task_id FROM tasks"
        ).fetchall()
    assert versions == [(1,), (2,)]
    assert partial is None
    assert old_data == [("task:wp17:upgrade",)]


@pytest.mark.parametrize("requirement_id", OWNED_REQUIREMENTS)
def test_spec_requirement(requirement_id: str, tmp_path: Path) -> None:
    api = _api()
    if requirement_id == "PST-015":
        first = api.ProcessLock(lock_path=tmp_path / "serve.lock")
        second = api.ProcessLock(lock_path=tmp_path / "serve.lock")
        held = False
        try:
            assert first.acquire() is api.ProcessLockOutcome.ACQUIRED
            held = True
            assert second.acquire() is api.ProcessLockOutcome.BUSY
        finally:
            if held:
                first.release()
        return

    task_ids = (
        ("task:wp17", "task:wp17:other")
        if requirement_id == "PST-020"
        else ("task:wp17",)
    )
    store, service, _ = _runtime(api, tmp_path, task_ids=task_ids)
    active = _acquire_execution(api, service)

    if requirement_id == "PST-016":
        assert (
            active.task_id,
            active.run_id,
            active.owner_identity,
            active.acquired_at,
            active.last_progress_at,
            active.phase,
        ) == (
            "task:wp17",
            "run:wp17:1",
            "owner:wp17:a",
            10,
            10,
            TaskState.EXECUTING,
        )
        with pytest.raises(api.LeaseConflict):
            _acquire_execution(
                api,
                service,
                lease_id="lease:wp17:b",
                owner_identity="owner:wp17:b",
                now=11,
            )
        return

    if requirement_id == "PST-017":
        before = store.audit_events(task_id=active.task_id)
        pending = service.mark_expired(now=21)
        after = store.audit_events(task_id=active.task_id)
        assert pending.status is api.LeaseStatus.RECOVERY_PENDING
        assert after[:-1] == before
        assert after[-1].event_kind == "EXECUTION_LEASE_STALE"
        assert pending.owner_identity == active.owner_identity
        assert service.current() == pending
        return

    if requirement_id == "PST-019":
        with pytest.raises(api.LeaseConflict):
            service.release(
                lease_id=active.lease_id,
                owner_identity=active.owner_identity,
                expected_revision=active.revision,
                evidence=_unsafe_release(api),
                now=11,
            )
        assert service.current() == active
        return

    if requirement_id == "PST-020":
        pending = service.mark_expired(now=21)
        with pytest.raises(api.LeaseConflict):
            _acquire_execution(
                api,
                service,
                lease_id="lease:wp17:other",
                task_id="task:wp17:other",
                run_id="run:wp17:other",
                owner_identity="owner:wp17:other",
                now=22,
            )
        recovery = service.acquire_recovery(
            lease_id="lease:wp17:recovery",
            task_id=pending.task_id,
            run_id=pending.run_id,
            owner_identity="owner:wp17:recovery",
            phase=TaskState.ROLLING_BACK,
            expected_pending_revision=pending.revision,
            now=22,
        )
        assert recovery.purpose is api.LeasePurpose.RECOVERY
        assert recovery.task_id == pending.task_id
        assert recovery.run_id == pending.run_id
        return

    raise AssertionError(f"unhandled requirement: {requirement_id}")
