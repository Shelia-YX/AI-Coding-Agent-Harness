"""WP-16 persistent domain event and evidence delivery contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import importlib
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from coding_harness.domain.enums import (
    TaskState,
    TransitionReason,
    TransitionTrigger,
)
from coding_harness.domain.models import TransitionAudit
from coding_harness.persistence.ports import AuditRecord


OWNED_REQUIREMENTS = ("PST-013", "PST-014")
_EXPECTED_RED = "WP-16 event delivery contract is not implemented"


def _module(name: str):
    missing = False
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        if error.name == name or name.startswith(error.name + "."):
            missing = True
        else:
            raise
    if missing:
        pytest.fail(f"{_EXPECTED_RED}: missing {name}", pytrace=False)
    raise AssertionError("unreachable module loader state")


def _api() -> SimpleNamespace:
    events = _module("coding_harness.domain.events")
    evidence = _module("coding_harness.persistence.evidence")
    migrations = _module("coding_harness.persistence.migrations")
    sqlite_store = _module("coding_harness.persistence.sqlite_store")
    required = {
        "DomainEvent": getattr(events, "DomainEvent", None),
        "DomainEventKind": getattr(events, "DomainEventKind", None),
        "EvidenceKind": getattr(evidence, "EvidenceKind", None),
        "EvidenceLifecycle": getattr(evidence, "EvidenceLifecycle", None),
        "EvidenceRef": getattr(evidence, "EvidenceRef", None),
        "EventReader": getattr(evidence, "EventReader", None),
        "MigrationRunner": getattr(migrations, "MigrationRunner", None),
        "SQLiteHarnessStore": getattr(
            sqlite_store, "SQLiteHarnessStore", None
        ),
        "PersistenceError": getattr(sqlite_store, "PersistenceError", None),
    }
    missing = tuple(name for name, value in required.items() if value is None)
    if missing:
        pytest.fail(
            _EXPECTED_RED + ": missing " + ", ".join(missing),
            pytrace=False,
        )
    return SimpleNamespace(**required)


def _migration_directory() -> Path:
    module = _module("coding_harness.persistence.sqlite_store")
    return Path(module.__file__).parent / "sql"


def _store_and_reader(api: SimpleNamespace, tmp_path: Path):
    database = tmp_path / "harness.sqlite3"
    api.MigrationRunner(
        database_path=database,
        migration_directory=_migration_directory(),
    ).run()
    return (
        api.SQLiteHarnessStore(database_path=database),
        api.EventReader(database_path=database),
        database,
    )


def _transition(
    store,
    *,
    task_id: str = "task:wp16",
    source: TaskState = TaskState.DRAFT,
    target: TaskState = TaskState.BLOCKED,
    occurred_at: int = 2,
) -> None:
    store.transition_task(
        task_id=task_id,
        expected_state=source,
        target_state=target,
        audit=TransitionAudit(
            source=source,
            target=target,
            trigger=TransitionTrigger.ENTER_BLOCKED,
            permitted=True,
            reason=TransitionReason.PERMITTED,
        ),
        occurred_at=occurred_at,
    )


def _evidence_ref(api: SimpleNamespace):
    return api.EvidenceRef(
        kind=api.EvidenceKind.ARTIFACT,
        relative_path="evidence/result.txt",
        content_digest="a" * 64,
        size_bytes=6,
        lifecycle=api.EvidenceLifecycle.AVAILABLE,
    )


def _domain_event(
    api: SimpleNamespace,
    *,
    event_id: int = 1,
    payload=None,
    evidence_refs=(),
):
    return api.DomainEvent(
        event_id=event_id,
        event_kind=api.DomainEventKind.TASK_STATE_CHANGED,
        occurred_at=2,
        task_id="task:wp16",
        entity_identity="task:wp16",
        entity_revision=2,
        payload=(
            (
                ("source_state", TaskState.DRAFT.value),
                ("target_state", TaskState.BLOCKED.value),
            )
            if payload is None
            else payload
        ),
        evidence_refs=evidence_refs,
    )


def test_domain_event_model_contract() -> None:
    api = _api()
    event = _domain_event(api)
    assert event.event_id == 1
    assert event.event_kind is api.DomainEventKind.TASK_STATE_CHANGED
    assert event.occurred_at == 2
    assert event.task_id == "task:wp16"
    assert event.entity_identity == "task:wp16"
    assert event.entity_revision == 2
    assert event.payload == (
        ("source_state", "DRAFT"),
        ("target_state", "BLOCKED"),
    )
    with pytest.raises(FrozenInstanceError):
        event.event_id = 2
    with pytest.raises(ValueError, match="event"):
        _domain_event(api, event_id=0)


def test_event_payload_bounded() -> None:
    api = _api()
    with pytest.raises(ValueError, match="payload|event"):
        _domain_event(api, payload=(("detail", "x" * (1024 * 1024)),))


def test_domain_event_rejects_mutable_or_invalid_evidence_members() -> None:
    api = _api()
    reference = _evidence_ref(api)
    event = _domain_event(api, evidence_refs=(reference,))
    assert event.evidence_refs == (reference,)
    with pytest.raises(FrozenInstanceError):
        reference.size_bytes = 7
    for invalid in ([], object(), AuditRecord):
        with pytest.raises(ValueError, match="evidence|event"):
            _domain_event(api, evidence_refs=(invalid,))


def test_create_event_failure_rolls_back_three_writes(tmp_path: Path) -> None:
    api = _api()
    store, reader, database = _store_and_reader(api, tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TRIGGER reject_wp16_create_event "
            "BEFORE INSERT ON domain_events "
            "BEGIN SELECT RAISE(ABORT, 'event rejected'); END"
        )
    with pytest.raises(api.PersistenceError, match="event|persistence"):
        store.create_task(
            task_id="task:wp16:create-failure",
            initial_state=TaskState.DRAFT,
            occurred_at=1,
        )
    assert store.get_task_state(task_id="task:wp16:create-failure") is None
    assert store.audit_events(task_id="task:wp16:create-failure") == ()
    assert reader.after(event_id=0, limit=100) == ()


def test_event_state_atomic(tmp_path: Path) -> None:
    api = _api()
    store, reader, database = _store_and_reader(api, tmp_path)
    store.create_task(
        task_id="task:wp16",
        initial_state=TaskState.DRAFT,
        occurred_at=1,
    )
    audit_before = store.audit_events(task_id="task:wp16")
    before = reader.after(event_id=0, limit=100)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TRIGGER reject_wp16_event "
            "BEFORE INSERT ON domain_events "
            "BEGIN SELECT RAISE(ABORT, 'event rejected'); END"
        )
    with pytest.raises(api.PersistenceError, match="event|persistence"):
        _transition(store)
    assert store.get_task_state(task_id="task:wp16") is TaskState.DRAFT
    assert store.audit_events(task_id="task:wp16") == audit_before
    assert reader.after(event_id=0, limit=100) == before


def test_audit_failure_rolls_back_state_and_event(tmp_path: Path) -> None:
    api = _api()
    store, reader, database = _store_and_reader(api, tmp_path)
    store.create_task(
        task_id="task:wp16",
        initial_state=TaskState.DRAFT,
        occurred_at=1,
    )
    audit_before = store.audit_events(task_id="task:wp16")
    events_before = reader.after(event_id=0, limit=100)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TRIGGER reject_wp16_transition_audit "
            "BEFORE INSERT ON audit_events "
            "BEGIN SELECT RAISE(ABORT, 'audit rejected'); END"
        )
    with pytest.raises(api.PersistenceError, match="audit|persistence"):
        _transition(store)
    assert store.get_task_state(task_id="task:wp16") is TaskState.DRAFT
    assert store.audit_events(task_id="task:wp16") == audit_before
    assert reader.after(event_id=0, limit=100) == events_before


def test_event_id_monotonic(tmp_path: Path) -> None:
    api = _api()
    store, reader, database = _store_and_reader(api, tmp_path)
    store.create_task(
        task_id="task:wp16",
        initial_state=TaskState.DRAFT,
        occurred_at=1,
    )
    _transition(store)
    first_read = reader.after(event_id=0, limit=100)
    ids = tuple(event.event_id for event in first_read)
    assert len(ids) >= 2
    assert ids == tuple(sorted(ids))
    assert len(ids) == len(set(ids))
    reopened = api.EventReader(database_path=database)
    assert reopened.after(event_id=0, limit=100) == first_read


def test_event_reader_after(tmp_path: Path) -> None:
    api = _api()
    store, reader, _ = _store_and_reader(api, tmp_path)
    store.create_task(
        task_id="task:wp16",
        initial_state=TaskState.DRAFT,
        occurred_at=1,
    )
    _transition(store)
    all_events = reader.after(event_id=0, limit=100)
    assert len(all_events) >= 2
    cursor = all_events[0].event_id
    expected = tuple(
        event for event in all_events if event.event_id > cursor
    )[:1]
    assert reader.after(event_id=cursor, limit=1) == expected
    assert reader.after(event_id=cursor, limit=1) == expected
    with pytest.raises(ValueError, match="event|limit|reader"):
        reader.after(event_id=-1, limit=1)
    with pytest.raises(ValueError, match="event|limit|reader"):
        reader.after(event_id=0, limit=0)


def test_three_evidence_kinds() -> None:
    api = _api()
    audit = AuditRecord(
        order=1,
        task_id="task:wp16",
        event_kind="TASK_CREATED",
        subject_identity="task:wp16",
        occurred_at=1,
        source=None,
        target=None,
        trigger=None,
        reason=None,
        permitted=None,
    )
    event = _domain_event(api)
    temporary = _evidence_ref(api)
    assert type(audit) is AuditRecord
    assert type(event) is api.DomainEvent
    assert type(temporary) is api.EvidenceRef
    assert len({type(audit), type(event), type(temporary)}) == 3


def test_artifact_reference() -> None:
    api = _api()
    reference = _evidence_ref(api)
    assert reference.relative_path == "evidence/result.txt"
    assert not hasattr(reference, "content")
    with pytest.raises(ValueError, match="evidence|reference|path"):
        api.EvidenceRef(
            kind=api.EvidenceKind.ARTIFACT,
            relative_path="../outside.txt",
            content_digest="a" * 64,
            size_bytes=6,
            lifecycle=api.EvidenceLifecycle.AVAILABLE,
        )


@pytest.mark.parametrize(
    "invalid_path",
    (
        "evidence/\nresult.txt",
        "evidence/\tresult.txt",
        "evidence/" + "x" * 4097,
    ),
)
def test_evidence_path_bounded_and_control_free(invalid_path: str) -> None:
    api = _api()
    with pytest.raises(ValueError, match="evidence|reference|path"):
        api.EvidenceRef(
            kind=api.EvidenceKind.ARTIFACT,
            relative_path=invalid_path,
            content_digest="a" * 64,
            size_bytes=6,
            lifecycle=api.EvidenceLifecycle.AVAILABLE,
        )


def test_artifact_digest_size() -> None:
    api = _api()
    reference = _evidence_ref(api)
    assert reference.content_digest == "a" * 64
    assert reference.size_bytes == 6
    with pytest.raises(ValueError, match="digest|evidence"):
        api.EvidenceRef(
            kind=api.EvidenceKind.ARTIFACT,
            relative_path="evidence/result.txt",
            content_digest="not-a-digest",
            size_bytes=6,
            lifecycle=api.EvidenceLifecycle.AVAILABLE,
        )
    with pytest.raises(ValueError, match="size|evidence"):
        api.EvidenceRef(
            kind=api.EvidenceKind.ARTIFACT,
            relative_path="evidence/result.txt",
            content_digest="a" * 64,
            size_bytes=-1,
            lifecycle=api.EvidenceLifecycle.AVAILABLE,
        )


def test_publisher_reads_store(tmp_path: Path) -> None:
    api = _api()
    store, reader, database = _store_and_reader(api, tmp_path)
    store.create_task(
        task_id="task:wp16",
        initial_state=TaskState.DRAFT,
        occurred_at=1,
    )
    written = reader.after(event_id=0, limit=100)
    assert written
    del store
    del reader
    reopened = api.EventReader(database_path=database)
    assert reopened.after(event_id=0, limit=100) == written


def test_migration_001_to_002_preserves_data(tmp_path: Path) -> None:
    api = _api()
    migration_directory = tmp_path / "migrations"
    migration_directory.mkdir()
    source_migrations = _migration_directory()
    (migration_directory / "001_initial.sql").write_bytes(
        (source_migrations / "001_initial.sql").read_bytes()
    )
    database = tmp_path / "upgrade.sqlite3"
    runner = api.MigrationRunner(
        database_path=database,
        migration_directory=migration_directory,
    )
    runner.run()
    with sqlite3.connect(database) as connection:
        with connection:
            connection.execute(
                "INSERT INTO tasks"
                "(task_id, state, revision, created_at, updated_at) "
                "VALUES(?, ?, ?, ?, ?)",
                ("task:wp16:upgrade", TaskState.DRAFT.value, 1, 1, 1),
            )
            connection.execute(
                "INSERT INTO audit_events"
                "(task_id, event_kind, subject_identity, occurred_at) "
                "VALUES(?, ?, ?, ?)",
                (
                    "task:wp16:upgrade",
                    "TASK_CREATED",
                    "task:wp16:upgrade",
                    1,
                ),
            )
    (migration_directory / "002_events.sql").write_bytes(
        (source_migrations / "002_events.sql").read_bytes()
    )
    runner.run()
    store = api.SQLiteHarnessStore(database_path=database)
    reader = api.EventReader(database_path=database)
    assert (
        store.get_task_state(task_id="task:wp16:upgrade")
        is TaskState.DRAFT
    )
    assert len(store.audit_events(task_id="task:wp16:upgrade")) == 1
    assert reader.after(event_id=0, limit=100) == ()
    _transition(store, task_id="task:wp16:upgrade")
    events = reader.after(event_id=0, limit=100)
    assert len(events) == 1
    assert events[0].event_kind is api.DomainEventKind.TASK_STATE_CHANGED


def test_memory_not_truth(tmp_path: Path) -> None:
    api = _api()
    _, reader, _ = _store_and_reader(api, tmp_path)
    memory_only = _domain_event(api, event_id=999)
    assert memory_only.event_id == 999
    assert reader.after(event_id=0, limit=100) == ()


@pytest.mark.parametrize("requirement_id", OWNED_REQUIREMENTS)
def test_spec_requirement(requirement_id: str, tmp_path: Path) -> None:
    api = _api()
    store, reader, database = _store_and_reader(api, tmp_path)
    store.create_task(
        task_id="task:wp16",
        initial_state=TaskState.DRAFT,
        occurred_at=1,
    )
    if requirement_id == "PST-013":
        _transition(store)
        events = reader.after(event_id=0, limit=100)
        state_events = tuple(
            event
            for event in events
            if event.event_kind is api.DomainEventKind.TASK_STATE_CHANGED
        )
        assert state_events
        assert state_events[-1].entity_revision == 2
    elif requirement_id == "PST-014":
        first = reader.after(event_id=0, limit=100)
        assert first
        assert api.EventReader(
            database_path=database
        ).after(event_id=0, limit=100) == first
    else:
        raise AssertionError(f"unmapped WP-16 requirement: {requirement_id}")
