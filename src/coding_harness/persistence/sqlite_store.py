"""Standard-library SQLite implementation of the narrow HarnessStore port."""

from __future__ import annotations

from dataclasses import asdict
from enum import Enum
import json
from pathlib import Path
import sqlite3

from coding_harness.domain.approvals import Approval, ApprovalType
from coding_harness.domain.budgets import (
    BudgetDimension,
    BudgetVersion,
    RunLimits,
)
from coding_harness.domain.enums import (
    TaskState,
    TransitionReason,
    TransitionTrigger,
)
from coding_harness.domain.events import (
    DomainEventKind,
    canonical_event_payload,
)
from coding_harness.domain.models import (
    ContractVersion,
    PlanVersion,
    TransitionAudit,
)
from coding_harness.persistence.ports import (
    ApplyObservation,
    AuditRecord,
    HarnessStore,
    RecoveryFindingRecord,
    StartupRecoveryCandidate,
)
from coding_harness.transaction.conflicts import ApplyConfirmation
from coding_harness.transaction.models import (
    ApplyDecision,
    ApplyPhase,
    ApplyResult,
    RecoveryState,
)


class PersistenceError(RuntimeError):
    pass


class PersistenceConflict(PersistenceError):
    pass


def _valid_text(value: object) -> bool:
    return type(value) is str and bool(value) and "\0" not in value


def _valid_time(value: object) -> bool:
    return type(value) is int and value >= 0


def _valid_private_reference(value: object) -> bool:
    if type(value) is not str or not value or "\\" in value or "\0" in value:
        return False
    path = Path(value)
    return (
        not path.is_absolute()
        and tuple(path.parts)
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return value


def _approval_payload(approval: Approval) -> str:
    return json.dumps(
        _json_value(asdict(approval)),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _approval_from_payload(payload: str) -> Approval:
    try:
        values = json.loads(payload)
        plan = values["plan_version"]
        contract = values["contract_version"]
        values["approval_type"] = ApprovalType(values["approval_type"])
        values["expected_state"] = TaskState(values["expected_state"])
        values["plan_version"] = PlanVersion(**plan)
        values["contract_version"] = (
            None if contract is None else ContractVersion(**contract)
        )
        for name in (
            "normalized_paths",
            "ignored_entries",
            "allowed_stages",
        ):
            values[name] = tuple(
                tuple(item) if isinstance(item, list) else item
                for item in values[name]
            )
        values["affected_dimensions"] = tuple(
            BudgetDimension(item) for item in values["affected_dimensions"]
        )
        for name in (
            "current_usage",
            "old_limits",
            "new_limits",
            "hard_limits",
        ):
            values[name] = tuple(
                (BudgetDimension(item[0]), item[1])
                for item in values[name]
            )
        return Approval(**values)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise PersistenceError("persisted approval is invalid") from None


def _budget_payload(budget: BudgetVersion) -> str:
    return json.dumps(
        {
            "display_text": budget.display_text,
            "soft_limits": {
                dimension.value: value
                for dimension, value in budget.limits.soft_limits.items()
            },
            "hard_limits": {
                dimension.value: value
                for dimension, value in budget.limits.hard_limits.items()
            },
            "repeated_failure_limit": budget.limits.repeated_failure_limit,
            "no_progress_limit": budget.limits.no_progress_limit,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _budget_from_payload(
    *,
    identity: str,
    task_id: str,
    sequence: int,
    payload: str,
) -> BudgetVersion:
    try:
        values = json.loads(payload)
        limits = RunLimits(
            soft_limits={
                BudgetDimension(name): value
                for name, value in values["soft_limits"].items()
            },
            hard_limits={
                BudgetDimension(name): value
                for name, value in values["hard_limits"].items()
            },
            repeated_failure_limit=values["repeated_failure_limit"],
            no_progress_limit=values["no_progress_limit"],
        )
        return BudgetVersion(
            identity=identity,
            task_id=task_id,
            sequence=sequence,
            limits=limits,
            display_text=values["display_text"],
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise PersistenceError("persisted budget version is invalid") from None


class SQLiteHarnessStore(HarnessStore):
    def __init__(self, *, database_path: Path) -> None:
        if not isinstance(database_path, Path):
            raise ValueError("SQLite store is invalid")
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(self._database_path, timeout=5)
            connection.execute("PRAGMA foreign_keys = ON")
            return connection
        except sqlite3.Error:
            raise PersistenceError("persistence connection failed") from None

    @staticmethod
    def _audit(
        connection: sqlite3.Connection,
        *,
        task_id: str,
        event_kind: str,
        subject_identity: str,
        occurred_at: int,
        transition: TransitionAudit | None = None,
    ) -> None:
        connection.execute(
            "INSERT INTO audit_events"
            "(task_id, event_kind, subject_identity, occurred_at, "
            "source_state, target_state, transition_trigger, "
            "transition_reason, permitted) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                task_id,
                event_kind,
                subject_identity,
                occurred_at,
                None if transition is None else transition.source.value,
                None if transition is None else transition.target.value,
                None if transition is None else transition.trigger.value,
                None if transition is None else transition.reason.value,
                None if transition is None else int(transition.permitted),
            ),
        )

    @staticmethod
    def _event(
        connection: sqlite3.Connection,
        *,
        event_kind: DomainEventKind,
        occurred_at: int,
        task_id: str,
        entity_identity: str,
        entity_revision: int,
        payload: tuple[tuple[str, str], ...],
    ) -> None:
        connection.execute(
            "INSERT INTO domain_events"
            "(event_kind, occurred_at, task_id, entity_identity, "
            "entity_revision, payload, evidence_refs) "
            "VALUES(?, ?, ?, ?, ?, ?, ?)",
            (
                event_kind.value,
                occurred_at,
                task_id,
                entity_identity,
                entity_revision,
                canonical_event_payload(payload),
                "[]",
            ),
        )

    def create_task(
        self,
        *,
        task_id: str,
        initial_state: TaskState,
        occurred_at: int,
    ) -> None:
        if (
            not _valid_text(task_id)
            or type(initial_state) is not TaskState
            or not _valid_time(occurred_at)
        ):
            raise ValueError("task persistence intent is invalid")
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    "INSERT INTO tasks"
                    "(task_id, state, revision, created_at, updated_at) "
                    "VALUES(?, ?, 1, ?, ?)",
                    (task_id, initial_state.value, occurred_at, occurred_at),
                )
                self._audit(
                    connection,
                    task_id=task_id,
                    event_kind="TASK_CREATED",
                    subject_identity=task_id,
                    occurred_at=occurred_at,
                )
                self._event(
                    connection,
                    event_kind=DomainEventKind.TASK_CREATED,
                    occurred_at=occurred_at,
                    task_id=task_id,
                    entity_identity=task_id,
                    entity_revision=1,
                    payload=(("initial_state", initial_state.value),),
                )
        except sqlite3.Error:
            raise PersistenceError("task and audit persistence failed") from None
        finally:
            connection.close()

    def get_task_state(self, *, task_id: str) -> TaskState | None:
        if not _valid_text(task_id):
            raise ValueError("task persistence query is invalid")
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT state FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        except sqlite3.Error:
            raise PersistenceError("task persistence query failed") from None
        finally:
            connection.close()
        if row is None:
            return None
        try:
            return TaskState(row[0])
        except (TypeError, ValueError):
            raise PersistenceError("persisted task state is invalid") from None

    def transition_task(
        self,
        *,
        task_id: str,
        expected_state: TaskState,
        target_state: TaskState,
        audit: TransitionAudit,
        occurred_at: int,
        expected_revision: int | None = None,
    ) -> None:
        if (
            not _valid_text(task_id)
            or type(expected_state) is not TaskState
            or type(target_state) is not TaskState
            or type(audit) is not TransitionAudit
            or audit.source is not expected_state
            or audit.target is not target_state
            or not audit.permitted
            or not _valid_time(occurred_at)
            or expected_revision is not None
            and (type(expected_revision) is not int or expected_revision < 1)
        ):
            raise ValueError("state transition persistence intent is invalid")
        connection = self._connect()
        try:
            with connection:
                if expected_revision is None:
                    cursor = connection.execute(
                        "UPDATE tasks SET state = ?, revision = revision + 1, "
                        "updated_at = ? WHERE task_id = ? AND state = ?",
                        (
                            target_state.value,
                            occurred_at,
                            task_id,
                            expected_state.value,
                        ),
                    )
                else:
                    cursor = connection.execute(
                        "UPDATE tasks SET state = ?, revision = revision + 1, "
                        "updated_at = ? WHERE task_id = ? AND state = ? "
                        "AND revision = ?",
                        (
                            target_state.value,
                            occurred_at,
                            task_id,
                            expected_state.value,
                            expected_revision,
                        ),
                    )
                if cursor.rowcount != 1:
                    raise PersistenceConflict(
                        "expected task state or revision conflict"
                    )
                revision_row = connection.execute(
                    "SELECT revision FROM tasks WHERE task_id = ?",
                    (task_id,),
                ).fetchone()
                if (
                    revision_row is None
                    or type(revision_row[0]) is not int
                    or revision_row[0] < 2
                ):
                    raise PersistenceError(
                        "persisted task revision is invalid"
                    )
                self._audit(
                    connection,
                    task_id=task_id,
                    event_kind="TASK_STATE_TRANSITION",
                    subject_identity=task_id,
                    occurred_at=occurred_at,
                    transition=audit,
                )
                self._event(
                    connection,
                    event_kind=DomainEventKind.TASK_STATE_CHANGED,
                    occurred_at=occurred_at,
                    task_id=task_id,
                    entity_identity=task_id,
                    entity_revision=revision_row[0],
                    payload=(
                        ("permitted", "true"),
                        ("reason", audit.reason.value),
                        ("source_state", expected_state.value),
                        ("target_state", target_state.value),
                        ("trigger", audit.trigger.value),
                    ),
                )
        except PersistenceConflict:
            raise
        except sqlite3.Error:
            raise PersistenceError(
                "state transition and audit persistence failed"
            ) from None
        finally:
            connection.close()

    def _record_text_version(
        self,
        *,
        table: str,
        identity: str,
        task_id: str,
        sequence: int,
        content_digest: str,
        display_text: str,
        event_kind: str,
        occurred_at: int,
    ) -> None:
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    f"INSERT INTO {table}"
                    "(identity, task_id, sequence, content_digest, display_text) "
                    "VALUES(?, ?, ?, ?, ?)",
                    (
                        identity,
                        task_id,
                        sequence,
                        content_digest,
                        display_text,
                    ),
                )
                self._audit(
                    connection,
                    task_id=task_id,
                    event_kind=event_kind,
                    subject_identity=identity,
                    occurred_at=occurred_at,
                )
        except sqlite3.Error:
            raise PersistenceError(
                "version and audit persistence failed"
            ) from None
        finally:
            connection.close()

    def record_plan_version(
        self,
        *,
        plan: PlanVersion,
        occurred_at: int,
    ) -> None:
        if type(plan) is not PlanVersion or not _valid_time(occurred_at):
            raise ValueError("Plan Version persistence intent is invalid")
        self._record_text_version(
            table="plan_versions",
            identity=plan.identity,
            task_id=plan.task_id,
            sequence=plan.sequence,
            content_digest=plan.content_digest,
            display_text=plan.display_text,
            event_kind="PLAN_VERSION_RECORDED",
            occurred_at=occurred_at,
        )

    def get_plan_version(self, *, identity: str) -> PlanVersion | None:
        if not _valid_text(identity):
            raise ValueError("Plan Version query is invalid")
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT identity, task_id, sequence, content_digest, "
                "display_text FROM plan_versions WHERE identity = ?",
                (identity,),
            ).fetchone()
        except sqlite3.Error:
            raise PersistenceError("Plan Version query failed") from None
        finally:
            connection.close()
        if row is None:
            return None
        try:
            return PlanVersion(*row)
        except (TypeError, ValueError):
            raise PersistenceError("persisted Plan Version is invalid") from None

    def record_contract_version(
        self,
        *,
        contract: ContractVersion,
        occurred_at: int,
    ) -> None:
        if type(contract) is not ContractVersion or not _valid_time(occurred_at):
            raise ValueError(
                "Acceptance Contract Version persistence intent is invalid"
            )
        self._record_text_version(
            table="contract_versions",
            identity=contract.identity,
            task_id=contract.task_id,
            sequence=contract.sequence,
            content_digest=contract.content_digest,
            display_text=contract.display_text,
            event_kind="CONTRACT_VERSION_RECORDED",
            occurred_at=occurred_at,
        )

    def get_contract_version(
        self,
        *,
        identity: str,
    ) -> ContractVersion | None:
        if not _valid_text(identity):
            raise ValueError("Acceptance Contract Version query is invalid")
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT identity, task_id, sequence, content_digest, "
                "display_text FROM contract_versions WHERE identity = ?",
                (identity,),
            ).fetchone()
        except sqlite3.Error:
            raise PersistenceError(
                "Acceptance Contract Version query failed"
            ) from None
        finally:
            connection.close()
        if row is None:
            return None
        try:
            return ContractVersion(*row)
        except (TypeError, ValueError):
            raise PersistenceError(
                "persisted Acceptance Contract Version is invalid"
            ) from None

    def record_budget_version(
        self,
        *,
        budget: BudgetVersion,
        occurred_at: int,
    ) -> None:
        if type(budget) is not BudgetVersion or not _valid_time(occurred_at):
            raise ValueError("Budget Version persistence intent is invalid")
        connection = self._connect()
        try:
            with connection:
                connection.execute(
                    "INSERT INTO budget_versions"
                    "(identity, task_id, sequence, payload) VALUES(?, ?, ?, ?)",
                    (
                        budget.identity,
                        budget.task_id,
                        budget.sequence,
                        _budget_payload(budget),
                    ),
                )
                self._audit(
                    connection,
                    task_id=budget.task_id,
                    event_kind="BUDGET_VERSION_RECORDED",
                    subject_identity=budget.identity,
                    occurred_at=occurred_at,
                )
        except sqlite3.Error:
            raise PersistenceError(
                "Budget Version and audit persistence failed"
            ) from None
        finally:
            connection.close()

    def get_budget_version(self, *, identity: str) -> BudgetVersion | None:
        if not _valid_text(identity):
            raise ValueError("Budget Version query is invalid")
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT identity, task_id, sequence, payload "
                "FROM budget_versions WHERE identity = ?",
                (identity,),
            ).fetchone()
        except sqlite3.Error:
            raise PersistenceError("Budget Version query failed") from None
        finally:
            connection.close()
        if row is None:
            return None
        return _budget_from_payload(
            identity=row[0],
            task_id=row[1],
            sequence=row[2],
            payload=row[3],
        )

    def record_approval(
        self,
        *,
        approval: Approval,
        occurred_at: int,
    ) -> None:
        if type(approval) is not Approval or not _valid_time(occurred_at):
            raise ValueError("approval persistence intent is invalid")
        payload = _approval_payload(approval)
        connection = self._connect()
        try:
            with connection:
                existing = connection.execute(
                    "SELECT request_digest, approval_identity, revision "
                    "FROM approvals WHERE task_id = ? AND idempotency_key = ? "
                    "ORDER BY revision LIMIT 1",
                    (approval.task_id, approval.idempotency_key),
                ).fetchone()
                if existing is not None:
                    if existing != (
                        approval.request_digest,
                        approval.identity,
                        approval.revision,
                    ):
                        raise PersistenceConflict(
                            "approval idempotency digest conflict"
                        )
                    return
                connection.execute(
                    "INSERT INTO approvals"
                    "(approval_identity, revision, task_id, idempotency_key, "
                    "request_digest, payload) VALUES(?, ?, ?, ?, ?, ?)",
                    (
                        approval.identity,
                        approval.revision,
                        approval.task_id,
                        approval.idempotency_key,
                        approval.request_digest,
                        payload,
                    ),
                )
                self._audit(
                    connection,
                    task_id=approval.task_id,
                    event_kind="APPROVAL_RECORDED",
                    subject_identity=approval.identity,
                    occurred_at=occurred_at,
                )
        except PersistenceConflict:
            raise
        except sqlite3.Error:
            raise PersistenceError(
                "approval and audit persistence failed"
            ) from None
        finally:
            connection.close()

    def update_approval(
        self,
        *,
        approval: Approval,
        expected_revision: int,
        occurred_at: int,
    ) -> None:
        if (
            type(approval) is not Approval
            or type(expected_revision) is not int
            or expected_revision < 1
            or approval.revision != expected_revision + 1
            or not _valid_time(occurred_at)
        ):
            raise ValueError("approval lifecycle persistence intent is invalid")
        connection = self._connect()
        try:
            with connection:
                current = connection.execute(
                    "SELECT task_id, idempotency_key, request_digest, revision "
                    "FROM approvals WHERE approval_identity = ? "
                    "ORDER BY revision DESC LIMIT 1",
                    (approval.identity,),
                ).fetchone()
                if current != (
                    approval.task_id,
                    approval.idempotency_key,
                    approval.request_digest,
                    expected_revision,
                ):
                    raise PersistenceConflict(
                        "approval expected revision conflict"
                    )
                connection.execute(
                    "INSERT INTO approvals"
                    "(approval_identity, revision, task_id, idempotency_key, "
                    "request_digest, payload) VALUES(?, ?, ?, ?, ?, ?)",
                    (
                        approval.identity,
                        approval.revision,
                        approval.task_id,
                        approval.idempotency_key,
                        approval.request_digest,
                        _approval_payload(approval),
                    ),
                )
                self._audit(
                    connection,
                    task_id=approval.task_id,
                    event_kind="APPROVAL_LIFECYCLE_UPDATED",
                    subject_identity=approval.identity,
                    occurred_at=occurred_at,
                )
        except PersistenceConflict:
            raise
        except sqlite3.Error:
            raise PersistenceError(
                "approval lifecycle and audit persistence failed"
            ) from None
        finally:
            connection.close()

    def get_approval(
        self,
        *,
        approval_identity: str,
        revision: int,
    ) -> Approval | None:
        if (
            not _valid_text(approval_identity)
            or type(revision) is not int
            or revision < 1
        ):
            raise ValueError("approval persistence query is invalid")
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT payload FROM approvals "
                "WHERE approval_identity = ? AND revision = ?",
                (approval_identity, revision),
            ).fetchone()
        except sqlite3.Error:
            raise PersistenceError("approval persistence query failed") from None
        finally:
            connection.close()
        return None if row is None else _approval_from_payload(row[0])

    def confirm_changeset(
        self,
        *,
        confirmation: ApplyConfirmation,
        occurred_at: int,
    ) -> None:
        if (
            type(confirmation) is not ApplyConfirmation
            or not _valid_time(occurred_at)
        ):
            raise ValueError("ChangeSet confirmation intent is invalid")
        connection = self._connect()
        try:
            with connection:
                existing = connection.execute(
                    "SELECT changeset_digest, baseline_manifest_digest, "
                    "plan_version_identity, "
                    "acceptance_contract_version_identity, expected_state "
                    "FROM changeset_confirmations "
                    "WHERE task_id = ? AND idempotency_key = ?",
                    (confirmation.task_id, confirmation.idempotency_key),
                ).fetchone()
                requested = (
                    confirmation.changeset_digest,
                    confirmation.baseline_manifest_digest,
                    confirmation.plan_version_identity,
                    confirmation.acceptance_contract_version_identity,
                    confirmation.expected_state.value,
                )
                if existing is not None:
                    if existing != requested:
                        raise PersistenceConflict(
                            "ChangeSet confirmation idempotency digest conflict"
                        )
                    return
                connection.execute(
                    "INSERT INTO changeset_confirmations"
                    "(task_id, idempotency_key, changeset_digest, "
                    "baseline_manifest_digest, plan_version_identity, "
                    "acceptance_contract_version_identity, expected_state, "
                    "occurred_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        confirmation.task_id,
                        confirmation.idempotency_key,
                        *requested,
                        occurred_at,
                    ),
                )
                self._audit(
                    connection,
                    task_id=confirmation.task_id,
                    event_kind="CHANGESET_CONFIRMED",
                    subject_identity=confirmation.changeset_digest,
                    occurred_at=occurred_at,
                )
        except PersistenceConflict:
            raise
        except sqlite3.Error:
            raise PersistenceError(
                "ChangeSet confirmation and audit persistence failed"
            ) from None
        finally:
            connection.close()

    def get_changeset_confirmation(
        self,
        *,
        task_id: str,
        idempotency_key: str,
    ) -> ApplyConfirmation | None:
        if not _valid_text(task_id) or not _valid_text(idempotency_key):
            raise ValueError("ChangeSet confirmation query is invalid")
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT changeset_digest, baseline_manifest_digest, "
                "plan_version_identity, "
                "acceptance_contract_version_identity, expected_state "
                "FROM changeset_confirmations "
                "WHERE task_id = ? AND idempotency_key = ?",
                (task_id, idempotency_key),
            ).fetchone()
        except sqlite3.Error:
            raise PersistenceError(
                "ChangeSet confirmation query failed"
            ) from None
        finally:
            connection.close()
        if row is None:
            return None
        try:
            return ApplyConfirmation(
                task_id=task_id,
                changeset_digest=row[0],
                baseline_manifest_digest=row[1],
                plan_version_identity=row[2],
                acceptance_contract_version_identity=row[3],
                expected_state=TaskState(row[4]),
                idempotency_key=idempotency_key,
            )
        except (TypeError, ValueError):
            raise PersistenceError(
                "persisted ChangeSet confirmation is invalid"
            ) from None

    def record_apply_observation(
        self,
        *,
        task_id: str,
        result: ApplyResult,
        journal_reference: str | None = None,
        occurred_at: int,
    ) -> None:
        if (
            not _valid_text(task_id)
            or type(result) is not ApplyResult
            or not _valid_time(occurred_at)
            or (result.journal is None) != (journal_reference is None)
            or journal_reference is not None
            and not _valid_private_reference(journal_reference)
            or result.plan is not None
            and result.plan.transaction_id != result.transaction_id
            or result.journal is not None
            and result.journal.transaction_id != result.transaction_id
        ):
            raise ValueError("apply observation intent is invalid")
        values = (
            result.transaction_id,
            task_id,
            result.decision.value,
            None if result.phase is None else result.phase.value,
            result.task_state.value,
            (
                None
                if result.recovery_state is None
                else result.recovery_state.value
            ),
            None if result.plan is None else result.plan.digest,
            None if result.plan is None else result.plan.baseline_digest,
            None if result.plan is None else result.plan.changeset_digest,
            journal_reference,
            result.index_digest_after,
            result.reason,
            occurred_at,
        )
        connection = self._connect()
        try:
            with connection:
                existing = connection.execute(
                    "SELECT transaction_id, task_id, decision, phase, "
                    "observed_task_state, recovery_state, plan_digest, "
                    "baseline_digest, changeset_digest, journal_reference, "
                    "index_digest_after, reason, occurred_at "
                    "FROM apply_observations "
                    "WHERE transaction_id = ?",
                    (result.transaction_id,),
                ).fetchone()
                if existing is not None:
                    if existing != values:
                        raise PersistenceConflict(
                            "apply observation identity conflict"
                        )
                    return
                connection.execute(
                    "INSERT INTO apply_observations"
                    "(transaction_id, task_id, decision, phase, "
                    "observed_task_state, recovery_state, plan_digest, "
                    "baseline_digest, changeset_digest, journal_reference, "
                    "index_digest_after, reason, occurred_at) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    values,
                )
                self._audit(
                    connection,
                    task_id=task_id,
                    event_kind="APPLY_OBSERVED",
                    subject_identity=result.transaction_id,
                    occurred_at=occurred_at,
                )
        except PersistenceConflict:
            raise
        except sqlite3.Error:
            raise PersistenceError(
                "apply observation and audit persistence failed"
            ) from None
        finally:
            connection.close()

    def get_apply_observation(
        self,
        *,
        transaction_id: str,
    ) -> ApplyObservation | None:
        if not _valid_text(transaction_id):
            raise ValueError("apply observation query is invalid")
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT task_id, decision, phase, observed_task_state, "
                "recovery_state, plan_digest, baseline_digest, "
                "changeset_digest, journal_reference, index_digest_after, "
                "reason, occurred_at FROM apply_observations "
                "WHERE transaction_id = ?",
                (transaction_id,),
            ).fetchone()
        except sqlite3.Error:
            raise PersistenceError(
                "apply observation query failed"
            ) from None
        finally:
            connection.close()
        if row is None:
            return None
        try:
            return ApplyObservation(
                transaction_id=transaction_id,
                task_id=row[0],
                decision=ApplyDecision(row[1]),
                phase=None if row[2] is None else ApplyPhase(row[2]),
                observed_task_state=TaskState(row[3]),
                recovery_state=(
                    None if row[4] is None else RecoveryState(row[4])
                ),
                plan_digest=row[5],
                baseline_digest=row[6],
                changeset_digest=row[7],
                journal_reference=row[8],
                index_digest_after=row[9],
                reason=row[10],
                occurred_at=row[11],
            )
        except (TypeError, ValueError):
            raise PersistenceError(
                "persisted apply observation is invalid"
            ) from None

    def startup_recovery_candidates(
        self,
        *,
        limit: int,
    ) -> tuple[StartupRecoveryCandidate, ...]:
        if type(limit) is not int or limit < 1 or limit > 1000:
            raise ValueError("startup recovery candidate query is invalid")
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT t.task_id, t.state, t.revision, "
                "(SELECT l.run_id FROM execution_leases AS l "
                " WHERE l.task_id = t.task_id "
                " AND l.status IN ('ACTIVE', 'RECOVERY_PENDING') "
                " ORDER BY l.acquired_at DESC, l.lease_id DESC LIMIT 1), "
                "a.transaction_id, a.phase, a.journal_reference, "
                "a.plan_digest, "
                "(SELECT p.identity FROM plan_versions AS p "
                " WHERE p.task_id = t.task_id "
                " ORDER BY p.sequence DESC, p.identity DESC LIMIT 1), "
                "(SELECT c.identity FROM contract_versions AS c "
                " WHERE c.task_id = t.task_id "
                " ORDER BY c.sequence DESC, c.identity DESC LIMIT 1), "
                "(SELECT ap.approval_identity FROM approvals AS ap "
                " WHERE ap.task_id = t.task_id "
                " ORDER BY ap.rowid DESC LIMIT 1), "
                "(SELECT ap.revision FROM approvals AS ap "
                " WHERE ap.task_id = t.task_id "
                " ORDER BY ap.rowid DESC LIMIT 1), "
                "(SELECT ap.payload FROM approvals AS ap "
                " WHERE ap.task_id = t.task_id "
                " ORDER BY ap.rowid DESC LIMIT 1) "
                "FROM tasks AS t "
                "LEFT JOIN apply_observations AS a "
                "ON a.transaction_id = ("
                " SELECT selected.transaction_id "
                " FROM apply_observations AS selected "
                " WHERE selected.task_id = t.task_id "
                " ORDER BY selected.occurred_at DESC, "
                " selected.transaction_id DESC LIMIT 1"
                ") "
                "WHERE t.state NOT IN "
                "('COMPLETED', 'NOT_APPLIED', 'FAILED', 'CANCELLED') "
                "ORDER BY t.task_id LIMIT ?",
                (limit + 1,),
            ).fetchall()
        except sqlite3.Error:
            raise PersistenceError(
                "startup recovery candidate query failed"
            ) from None
        finally:
            connection.close()
        if len(rows) > limit:
            raise PersistenceError(
                "startup recovery candidate query exceeds limit"
            )
        try:
            candidates = []
            for row in rows:
                approval = (
                    None
                    if row[12] is None
                    else _approval_from_payload(row[12])
                )
                if approval is not None and (
                    approval.identity != row[10]
                    or approval.revision != row[11]
                    or approval.task_id != row[0]
                ):
                    raise ValueError
                candidates.append(
                    StartupRecoveryCandidate(
                    task_id=row[0],
                    task_state=TaskState(row[1]),
                    task_revision=row[2],
                    run_id=row[3],
                    transaction_id=row[4],
                    apply_phase=(
                        None if row[5] is None else ApplyPhase(row[5])
                    ),
                    journal_reference=row[6],
                    plan_version_identity=row[8],
                    contract_version_identity=row[9],
                    approval_identity=row[10],
                    approval_revision=row[11],
                    approval_plan_version_identity=(
                        None
                        if approval is None
                        else approval.plan_version.identity
                    ),
                    apply_plan_digest=row[7],
                    approval_type=(
                        None if approval is None else approval.approval_type
                    ),
                    approval_consumed=(
                        None if approval is None else approval.consumed
                    ),
                    approval_revoked=(
                        None if approval is None else approval.revoked
                    ),
                    approval_expires_at=(
                        None if approval is None else approval.expires_at
                    ),
                )
                )
            return tuple(candidates)
        except (TypeError, ValueError, PersistenceError):
            raise PersistenceError(
                "persisted startup recovery candidate is invalid"
            ) from None

    def record_recovery_finding(
        self,
        *,
        finding: RecoveryFindingRecord,
        occurred_at: int,
    ) -> None:
        if (
            type(finding) is not RecoveryFindingRecord
            or not _valid_time(occurred_at)
        ):
            raise ValueError("recovery finding persistence intent is invalid")
        connection = self._connect()
        try:
            with connection:
                existing = connection.execute(
                    "SELECT task_id FROM audit_events "
                    "WHERE event_kind = 'STARTUP_RECOVERY_FINDING' "
                    "AND subject_identity = ? "
                    "ORDER BY audit_order LIMIT 2",
                    (finding.finding_id,),
                ).fetchall()
                if existing:
                    if len(existing) != 1 or existing[0][0] != finding.task_id:
                        raise PersistenceConflict(
                            "recovery finding identity conflict"
                        )
                    return
                self._audit(
                    connection,
                    task_id=finding.task_id,
                    event_kind="STARTUP_RECOVERY_FINDING",
                    subject_identity=finding.finding_id,
                    occurred_at=occurred_at,
                )
        except PersistenceConflict:
            raise
        except sqlite3.Error:
            raise PersistenceError(
                "recovery finding persistence failed"
            ) from None
        finally:
            connection.close()

    def audit_events(self, *, task_id: str) -> tuple[AuditRecord, ...]:
        if not _valid_text(task_id):
            raise ValueError("audit query is invalid")
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT audit_order, task_id, event_kind, subject_identity, "
                "occurred_at, source_state, target_state, transition_trigger, "
                "transition_reason, permitted FROM audit_events "
                "WHERE task_id = ? "
                "ORDER BY audit_order",
                (task_id,),
            ).fetchall()
        except sqlite3.Error:
            raise PersistenceError("audit query failed") from None
        finally:
            connection.close()
        try:
            return tuple(
                AuditRecord(
                    order=row[0],
                    task_id=row[1],
                    event_kind=row[2],
                    subject_identity=row[3],
                    occurred_at=row[4],
                    source=None if row[5] is None else TaskState(row[5]),
                    target=None if row[6] is None else TaskState(row[6]),
                    trigger=(
                        None
                        if row[7] is None
                        else TransitionTrigger(row[7])
                    ),
                    reason=(
                        None
                        if row[8] is None
                        else TransitionReason(row[8])
                    ),
                    permitted=None if row[9] is None else bool(row[9]),
                )
                for row in rows
            )
        except (TypeError, ValueError):
            raise PersistenceError("persisted audit is invalid") from None


__all__ = [
    "PersistenceConflict",
    "PersistenceError",
    "SQLiteHarnessStore",
]
