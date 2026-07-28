"""WP-15 SQLite persistence and atomic audit integration contracts."""

from __future__ import annotations

import importlib
import inspect
from dataclasses import fields, replace
import hashlib
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from typing import Any, get_type_hints

import pytest

from coding_harness.domain.approvals import Approval, ApprovalType
from coding_harness.domain.budgets import (
    BudgetDimension,
    BudgetVersion,
    RunLimits,
)
from coding_harness.domain.enums import TaskState, TransitionReason, TransitionTrigger
from coding_harness.domain.models import (
    ContractVersion,
    PlanVersion,
    TransitionAudit,
)
from coding_harness.transaction.conflicts import ApplyConfirmation
from coding_harness.transaction.models import (
    ApplyDecision,
    ApplyPhase,
    ApplyResult,
    RecoveryState,
    make_apply_plan,
)
from coding_harness.transaction.journal import ApplyJournal


OWNED_REQUIREMENTS = (
    "PST-001",
    "PST-002",
    "PST-003",
    "PST-007",
    "PST-008",
    "PST-009",
    "PST-010",
    "PST-011",
    "PST-012",
)
_EXPECTED_RED = "WP-15 persistence contract is not implemented"


def _module(name: str):
    missing = False
    try:
        module = importlib.import_module(name)
    except ModuleNotFoundError as error:
        if error.name == name or name.startswith(error.name + "."):
            missing = True
        else:
            raise
    if missing:
        pytest.fail(f"{_EXPECTED_RED}: missing {name}", pytrace=False)
    return module


def _api() -> SimpleNamespace:
    modules = {
        "ports_module": _module("coding_harness.persistence.ports"),
        "migrations_module": _module("coding_harness.persistence.migrations"),
        "sqlite_store_module": _module(
            "coding_harness.persistence.sqlite_store"
        ),
    }
    required = {
        "HarnessStore": getattr(modules["ports_module"], "HarnessStore", None),
        "MigrationRunner": getattr(
            modules["migrations_module"], "MigrationRunner", None
        ),
        "SQLiteHarnessStore": getattr(
            modules["sqlite_store_module"], "SQLiteHarnessStore", None
        ),
    }
    missing = tuple(name for name, value in required.items() if value is None)
    if missing:
        pytest.fail(
            _EXPECTED_RED + ": missing " + ", ".join(missing),
            pytrace=False,
        )
    return SimpleNamespace(**modules, **required)


def _migration_api() -> SimpleNamespace:
    module = _module("coding_harness.persistence.migrations")
    runner = getattr(module, "MigrationRunner", None)
    if runner is None:
        pytest.fail(
            f"{_EXPECTED_RED}: missing MigrationRunner",
            pytrace=False,
        )
    return SimpleNamespace(MigrationRunner=runner)


def _sqlite_api() -> SimpleNamespace:
    module = _module("coding_harness.persistence.sqlite_store")
    store = getattr(module, "SQLiteHarnessStore", None)
    if store is None:
        pytest.fail(
            f"{_EXPECTED_RED}: missing SQLiteHarnessStore",
            pytrace=False,
        )
    return SimpleNamespace(
        SQLiteHarnessStore=store,
        sqlite_store_module=module,
    )


def _migration_directory(api: SimpleNamespace) -> Path:
    return Path(api.sqlite_store_module.__file__).parent / "sql"


def _store(api: SimpleNamespace, tmp_path: Path):
    database = tmp_path / "harness.sqlite3"
    api.MigrationRunner(
        database_path=database,
        migration_directory=_migration_directory(api),
    ).run()
    return api.SQLiteHarnessStore(database_path=database), database


def _plan() -> PlanVersion:
    return PlanVersion(
        identity="plan:wp15:1",
        task_id="task:wp15",
        sequence=1,
        content_digest="1" * 64,
        display_text="Plan version one",
    )


def _contract() -> ContractVersion:
    return ContractVersion(
        identity="contract:wp15:1",
        task_id="task:wp15",
        sequence=1,
        content_digest="2" * 64,
        display_text="Contract version one",
    )


def _budget() -> BudgetVersion:
    soft = {dimension: 10 for dimension in BudgetDimension}
    hard = {dimension: 20 for dimension in BudgetDimension}
    return BudgetVersion(
        identity="budget:wp15:1",
        task_id="task:wp15",
        sequence=1,
        limits=RunLimits(
            soft_limits=soft,
            hard_limits=hard,
            repeated_failure_limit=3,
            no_progress_limit=3,
        ),
        display_text="Budget version one",
    )


def _approval(*, revision: int = 1, consumed: bool = False) -> Approval:
    return Approval(
        identity="approval:wp15:1",
        revision=revision,
        display_text="Apply approval",
        approval_type=ApprovalType.APPLY_APPROVAL,
        task_id="task:wp15",
        target_identity="changeset:wp15:1",
        expected_state=TaskState.READY_TO_APPLY,
        plan_version=_plan(),
        contract_version=_contract(),
        request_digest="3" * 64,
        policy_record_identity="policy:wp15:1",
        policy_record_digest="4" * 64,
        reason_code="APPROVAL_REQUIRED",
        created_at=10,
        expires_at=100,
        consumed=consumed,
        consumed_at=20 if consumed else None,
        revoked=False,
        revoked_at=None,
        idempotency_key="approval:wp15:1",
        scope_digest="5" * 64,
        action_kind=None,
        action_id=None,
        normalized_paths=(),
        expected_content_digest=None,
        baseline_manifest_digest="6" * 64,
        action_payload_digest=None,
        action_reason=None,
        ignored_entries=(),
        ignored_input_mode=None,
        allowed_stages=(),
        sandbox_manifest_identity=None,
        exportable_to_llm=False,
        changeset_digest="7" * 64,
        budget_version_identity=_budget().identity,
        affected_dimensions=(BudgetDimension.CHANGESET_BYTES,),
        current_usage=((BudgetDimension.CHANGESET_BYTES, 1),),
        old_limits=((BudgetDimension.CHANGESET_BYTES, 10),),
        new_limits=((BudgetDimension.CHANGESET_BYTES, 11),),
        hard_limits=((BudgetDimension.CHANGESET_BYTES, 20),),
        extension_reason="Bound test lifecycle",
    )


def _wp14_result(
    tmp_path: Path,
    *,
    transaction_id: str = "transaction:wp15:real",
) -> ApplyResult:
    tmp_path.mkdir(parents=True, exist_ok=True)
    tmp_path.chmod(0o700)
    plan = make_apply_plan(
        transaction_id=transaction_id,
        baseline_digest="8" * 64,
        changeset_digest="9" * 64,
        index_digest_before="a" * 64,
        target_root_identity="b" * 64,
        entries=(),
    )
    journal = ApplyJournal.create(
        tmp_path / "transactions",
        plan.transaction_id,
        plan,
    )
    return ApplyResult(
        transaction_id=plan.transaction_id,
        decision=ApplyDecision.APPLY,
        phase=ApplyPhase.APPLIED,
        task_state=TaskState.COMPLETED,
        recovery_state=RecoveryState.SUCCESS,
        plan=plan,
        journal=journal,
        index_digest_after="a" * 64,
        reason="WP-14 verified the filesystem effect",
    )


def test_harness_store_interface_missing() -> None:
    ports = _module("coding_harness.persistence.ports")
    store = getattr(ports, "HarnessStore", None)
    assert store is not None, "HarnessStore interface is missing"
    assert inspect.isabstract(store), "HarnessStore must be an abstract boundary"


def test_no_execute_sql() -> None:
    api = _api()
    for store_type in (api.HarnessStore, api.SQLiteHarnessStore):
        public = {
            name
            for name, _ in inspect.getmembers(store_type)
            if not name.startswith("_")
        }
        assert "execute_sql" not in public
        assert not any(name.endswith("connection") for name in public)


def test_domain_models_only() -> None:
    api = _api()
    forbidden = {dict, sqlite3.Connection, sqlite3.Cursor, sqlite3.Row, Any}
    permitted_models = {
        Approval,
        ApplyConfirmation,
        ApplyResult,
        TaskState,
        TransitionAudit,
    }
    observed_models: set[object] = set()
    for name, method in inspect.getmembers(
        api.HarnessStore, predicate=inspect.isfunction
    ):
        if name.startswith("_"):
            continue
        hints = get_type_hints(method)
        assert not forbidden.intersection(hints.values()), (
            f"{name} leaks a persistence representation"
        )
        observed_models.update(permitted_models.intersection(hints.values()))
    assert observed_models == permitted_models


def test_migration_runner_contract_missing(tmp_path: Path) -> None:
    api = _migration_api()
    runner = api.MigrationRunner(
        database_path=tmp_path / "harness.sqlite3",
        migration_directory=tmp_path / "migrations",
    )
    assert callable(getattr(runner, "run", None))


def test_sqlite_store_contract_missing(tmp_path: Path) -> None:
    api = _sqlite_api()
    store = api.SQLiteHarnessStore(database_path=tmp_path / "harness.sqlite3")
    required = {
        "create_task",
        "get_task_state",
        "transition_task",
        "record_approval",
        "get_approval",
        "confirm_changeset",
        "get_changeset_confirmation",
        "record_apply_observation",
        "get_apply_observation",
        "audit_events",
    }
    assert not required.difference(dir(store))


def test_ordered_migrations(tmp_path: Path) -> None:
    api = _migration_api()
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "002_second.sql").write_text(
        "CREATE TABLE second_table(value TEXT);\n",
        encoding="utf-8",
    )
    (migrations / "001_first.sql").write_text(
        "CREATE TABLE first_table(value TEXT);\n",
        encoding="utf-8",
    )
    database = tmp_path / "ordered.sqlite3"
    api.MigrationRunner(
        database_path=database,
        migration_directory=migrations,
    ).run()
    with sqlite3.connect(database) as connection:
        versions = connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
    assert versions == [(1,), (2,)]


def test_checksum_drift(tmp_path: Path) -> None:
    api = _migration_api()
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    migration = migrations / "001_initial.sql"
    migration.write_text(
        "CREATE TABLE stable(value TEXT);\n",
        encoding="utf-8",
    )
    database = tmp_path / "drift.sqlite3"
    runner = api.MigrationRunner(
        database_path=database,
        migration_directory=migrations,
    )
    runner.run()
    migration.write_text(
        "CREATE TABLE changed(value TEXT);\n",
        encoding="utf-8",
    )
    with pytest.raises(Exception, match="checksum|drift"):
        runner.run()


def test_migration_failure(tmp_path: Path) -> None:
    api = _migration_api()
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_broken.sql").write_text(
        "THIS IS NOT SQL;\n",
        encoding="utf-8",
    )
    database = tmp_path / "broken.sqlite3"
    with pytest.raises(Exception, match="migration|schema"):
        api.MigrationRunner(
            database_path=database,
            migration_directory=migrations,
        ).run()
    if database.exists():
        with sqlite3.connect(database) as connection:
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name != 'schema_migrations'"
            ).fetchall()
        assert tables == []


def test_no_downgrade(tmp_path: Path) -> None:
    api = _migration_api()
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_initial.sql").write_text(
        "CREATE TABLE stable(value TEXT);\n",
        encoding="utf-8",
    )
    database = tmp_path / "newer.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations("
            "version INTEGER PRIMARY KEY, name TEXT NOT NULL, "
            "checksum TEXT NOT NULL, applied_at INTEGER NOT NULL)"
        )
        connection.execute(
            "INSERT INTO schema_migrations VALUES(2, 'future', ?, 1)",
            ("f" * 64,),
        )
    with pytest.raises(Exception, match="version|downgrade|incompatible"):
        api.MigrationRunner(
            database_path=database,
            migration_directory=migrations,
        ).run()


def test_audit_append_only(tmp_path: Path) -> None:
    api = _api()
    store, database = _store(api, tmp_path)
    store.create_task(
        task_id="task:wp15",
        initial_state=TaskState.DRAFT,
        occurred_at=1,
    )
    before = store.audit_events(task_id="task:wp15")
    assert before
    with sqlite3.connect(database) as connection:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(
                "UPDATE audit_events SET event_kind = 'FORGED'"
            )
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("DELETE FROM audit_events")
    assert store.audit_events(task_id="task:wp15") == before


def test_state_audit_atomic(tmp_path: Path) -> None:
    api = _api()
    store, database = _store(api, tmp_path)
    store.create_task(
        task_id="task:wp15",
        initial_state=TaskState.DRAFT,
        occurred_at=1,
    )
    before = store.audit_events(task_id="task:wp15")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TRIGGER reject_wp15_audit "
            "BEFORE INSERT ON audit_events "
            "BEGIN SELECT RAISE(ABORT, 'audit rejected'); END"
        )
    with pytest.raises(Exception, match="audit|persistence"):
        store.transition_task(
            task_id="task:wp15",
            expected_state=TaskState.DRAFT,
            target_state=TaskState.BLOCKED,
            audit=TransitionAudit(
                source=TaskState.DRAFT,
                target=TaskState.BLOCKED,
                trigger=TransitionTrigger.ENTER_BLOCKED,
                permitted=True,
                reason=TransitionReason.PERMITTED,
            ),
            occurred_at=2,
        )
    assert store.get_task_state(task_id="task:wp15") is TaskState.DRAFT
    assert store.audit_events(task_id="task:wp15") == before


def test_governance_audit_atomic_contract(tmp_path: Path) -> None:
    api = _api()
    store, database = _store(api, tmp_path)
    store.create_task(
        task_id="task:wp15",
        initial_state=TaskState.READY_TO_APPLY,
        occurred_at=1,
    )
    before = store.audit_events(task_id="task:wp15")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TRIGGER reject_governance_audit "
            "BEFORE INSERT ON audit_events "
            "BEGIN SELECT RAISE(ABORT, 'audit rejected'); END"
        )
    confirmation = ApplyConfirmation(
        task_id="task:wp15",
        changeset_digest="6" * 64,
        baseline_manifest_digest="5" * 64,
        plan_version_identity="plan:wp15:1",
        acceptance_contract_version_identity="contract:wp15:1",
        expected_state=TaskState.READY_TO_APPLY,
        idempotency_key="apply:wp15:1",
    )
    with pytest.raises(Exception, match="audit|persistence"):
        store.confirm_changeset(
            confirmation=confirmation,
            occurred_at=2,
        )
    assert (
        store.get_changeset_confirmation(
            task_id=confirmation.task_id,
            idempotency_key=confirmation.idempotency_key,
        )
        is None
    )
    assert store.audit_events(task_id="task:wp15") == before


def test_approval_and_change_confirmation_contract() -> None:
    api = _api()
    approval_hints = get_type_hints(api.HarnessStore.record_approval)
    confirmation_hints = get_type_hints(api.HarnessStore.confirm_changeset)
    assert Approval in approval_hints.values()
    assert ApplyConfirmation in confirmation_hints.values()


def test_pst009_versions_approval_lifecycle_and_budget_are_atomic(
    tmp_path: Path,
) -> None:
    api = _api()
    store, database = _store(api, tmp_path)
    store.create_task(
        task_id="task:wp15",
        initial_state=TaskState.READY_TO_APPLY,
        occurred_at=1,
    )
    plan = _plan()
    contract = _contract()
    budget = _budget()
    approval = _approval()

    store.record_plan_version(plan=plan, occurred_at=2)
    store.record_contract_version(contract=contract, occurred_at=3)
    store.record_budget_version(budget=budget, occurred_at=4)
    store.record_approval(approval=approval, occurred_at=5)
    consumed = replace(
        approval,
        revision=2,
        consumed=True,
        consumed_at=20,
    )
    store.update_approval(
        approval=consumed,
        expected_revision=1,
        occurred_at=6,
    )

    assert store.get_plan_version(identity=plan.identity) == plan
    assert store.get_contract_version(identity=contract.identity) == contract
    restored_budget = store.get_budget_version(identity=budget.identity)
    assert restored_budget is not None
    assert restored_budget.limits.soft_limits == budget.limits.soft_limits
    assert restored_budget.limits.hard_limits == budget.limits.hard_limits
    assert store.get_approval(
        approval_identity=approval.identity,
        revision=2,
    ).consumed

    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TRIGGER reject_version_audit "
            "BEFORE INSERT ON audit_events "
            "BEGIN SELECT RAISE(ABORT, 'audit rejected'); END"
        )
    rejected = replace(
        plan,
        identity="plan:wp15:2",
        sequence=2,
        content_digest="8" * 64,
    )
    with pytest.raises(Exception, match="audit|persistence"):
        store.record_plan_version(plan=rejected, occurred_at=7)
    assert store.get_plan_version(identity=rejected.identity) is None

    kinds = {event.event_kind for event in store.audit_events(task_id="task:wp15")}
    assert {
        "PLAN_VERSION_RECORDED",
        "CONTRACT_VERSION_RECORDED",
        "BUDGET_VERSION_RECORDED",
        "APPROVAL_RECORDED",
        "APPROVAL_LIFECYCLE_UPDATED",
    }.issubset(kinds)


def test_apply_observation_is_not_apply_authority(tmp_path: Path) -> None:
    api = _api()
    store, _ = _store(api, tmp_path)
    store.create_task(
        task_id="task:wp15",
        initial_state=TaskState.READY_TO_APPLY,
        occurred_at=1,
    )
    result = ApplyResult(
        transaction_id="transaction:wp15:1",
        decision=ApplyDecision.APPLY,
        phase=ApplyPhase.APPLIED,
        task_state=TaskState.COMPLETED,
        recovery_state=RecoveryState.SUCCESS,
        plan=None,
        journal=None,
        index_digest_after="7" * 64,
        reason="WP-14 verified the filesystem effect",
    )
    store.record_apply_observation(
        task_id="task:wp15",
        result=result,
        occurred_at=2,
    )
    observation = store.get_apply_observation(
        transaction_id=result.transaction_id
    )
    assert observation.transaction_id == result.transaction_id
    assert observation.phase is result.phase
    assert observation.observed_task_state is result.task_state
    assert (
        store.get_task_state(task_id="task:wp15")
        is TaskState.READY_TO_APPLY
    )


def test_real_wp14_apply_result_is_observed_without_authority(
    tmp_path: Path,
) -> None:
    api = _api()
    store, _ = _store(api, tmp_path)
    store.create_task(
        task_id="task:wp15",
        initial_state=TaskState.READY_TO_APPLY,
        occurred_at=1,
    )
    result = _wp14_result(tmp_path)
    store.record_apply_observation(
        task_id="task:wp15",
        result=result,
        journal_reference="transactions/txn-transaction_wp15_real",
        occurred_at=2,
    )
    observation = store.get_apply_observation(
        transaction_id=result.transaction_id
    )
    assert observation.transaction_id == result.transaction_id
    assert observation.phase is ApplyPhase.APPLIED
    assert observation.journal_reference == (
        "transactions/txn-transaction_wp15_real"
    )
    assert (
        store.get_task_state(task_id="task:wp15")
        is TaskState.READY_TO_APPLY
    )


def test_apply_evidence_and_audit_are_persisted_atomically(
    tmp_path: Path,
) -> None:
    api = _api()
    store, database = _store(api, tmp_path)
    store.create_task(
        task_id="task:wp15",
        initial_state=TaskState.READY_TO_APPLY,
        occurred_at=1,
    )
    result = _wp14_result(tmp_path)
    journal_reference = "transactions/txn-transaction_wp15_real"
    store.record_apply_observation(
        task_id="task:wp15",
        result=result,
        journal_reference=journal_reference,
        occurred_at=2,
    )
    observation = store.get_apply_observation(
        transaction_id=result.transaction_id
    )
    assert observation.plan_digest == result.plan.digest
    assert observation.baseline_digest == result.plan.baseline_digest
    assert observation.changeset_digest == result.plan.changeset_digest
    assert observation.journal_reference == journal_reference

    second = _wp14_result(
        tmp_path / "second",
        transaction_id="transaction:wp15:rejected",
    )
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TRIGGER reject_apply_audit "
            "BEFORE INSERT ON audit_events "
            "BEGIN SELECT RAISE(ABORT, 'audit rejected'); END"
        )
    with pytest.raises(Exception, match="audit|persistence"):
        store.record_apply_observation(
            task_id="task:wp15",
            result=second,
            journal_reference="transactions/txn-transaction_wp15_rejected",
            occurred_at=3,
        )
    assert (
        store.get_apply_observation(transaction_id=second.transaction_id)
        is None
    )


def test_transition_audit_details_are_persisted(tmp_path: Path) -> None:
    api = _api()
    store, _ = _store(api, tmp_path)
    store.create_task(
        task_id="task:wp15",
        initial_state=TaskState.DRAFT,
        occurred_at=1,
    )
    audit = TransitionAudit(
        source=TaskState.DRAFT,
        target=TaskState.BLOCKED,
        trigger=TransitionTrigger.ENTER_BLOCKED,
        permitted=True,
        reason=TransitionReason.PERMITTED,
    )
    store.transition_task(
        task_id="task:wp15",
        expected_state=TaskState.DRAFT,
        target_state=TaskState.BLOCKED,
        audit=audit,
        occurred_at=2,
    )
    event = store.audit_events(task_id="task:wp15")[-1]
    assert event.source is audit.source
    assert event.target is audit.target
    assert event.trigger is audit.trigger
    assert event.reason is audit.reason
    assert event.permitted is audit.permitted


def test_approval_round_trip_preserves_every_field_and_enum(
    tmp_path: Path,
) -> None:
    api = _api()
    store, _ = _store(api, tmp_path)
    store.create_task(
        task_id="task:wp15",
        initial_state=TaskState.READY_TO_APPLY,
        occurred_at=1,
    )
    approval = _approval()
    store.record_approval(approval=approval, occurred_at=2)
    restored = store.get_approval(
        approval_identity=approval.identity,
        revision=approval.revision,
    )
    assert restored is not None
    for field in fields(Approval):
        assert getattr(restored, field.name) == getattr(approval, field.name)
    assert type(restored.affected_dimensions[0]) is BudgetDimension
    assert type(restored.current_usage[0][0]) is BudgetDimension


def test_migration_history_must_be_a_contiguous_prefix(
    tmp_path: Path,
) -> None:
    api = _migration_api()
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    first = b"CREATE TABLE first_table(value TEXT);\n"
    second = b"CREATE TABLE second_table(value TEXT);\n"
    (migrations / "001_first.sql").write_bytes(first)
    (migrations / "002_second.sql").write_bytes(second)
    database = tmp_path / "gap.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE schema_migrations("
            "version INTEGER PRIMARY KEY, name TEXT NOT NULL, "
            "checksum TEXT NOT NULL, applied_at INTEGER NOT NULL)"
        )
        connection.execute(
            "INSERT INTO schema_migrations VALUES(2, 'second', ?, 1)",
            (hashlib.sha256(second).hexdigest(),),
        )
    with pytest.raises(Exception, match="prefix|order|history"):
        api.MigrationRunner(
            database_path=database,
            migration_directory=migrations,
        ).run()


def test_audit_survives_store_instance(tmp_path: Path) -> None:
    api = _api()
    store, database = _store(api, tmp_path)
    store.create_task(
        task_id="task:wp15",
        initial_state=TaskState.DRAFT,
        occurred_at=1,
    )
    reopened = api.SQLiteHarnessStore(database_path=database)
    events = reopened.audit_events(task_id="task:wp15")
    assert len(events) == 1
    assert events[0].event_kind == "TASK_CREATED"


@pytest.mark.parametrize("requirement_id", OWNED_REQUIREMENTS)
def test_spec_requirement(requirement_id: str, tmp_path: Path) -> None:
    evidence = {
        "PST-001": test_real_wp14_apply_result_is_observed_without_authority,
        "PST-002": test_audit_survives_store_instance,
        "PST-003": lambda _: (test_no_execute_sql(), test_domain_models_only()),
        "PST-007": test_ordered_migrations,
        "PST-008": test_state_audit_atomic,
        "PST-009": test_pst009_versions_approval_lifecycle_and_budget_are_atomic,
        "PST-010": test_audit_append_only,
        "PST-011": test_migration_history_must_be_a_contiguous_prefix,
        "PST-012": test_checksum_drift,
    }
    evidence[requirement_id](tmp_path)
