"""Narrow domain-facing persistence boundary."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import PurePosixPath

from coding_harness.domain.approvals import Approval, ApprovalType
from coding_harness.domain.budgets import BudgetVersion
from coding_harness.domain.enums import (
    BlockedReason,
    TaskState,
    TransitionReason,
    TransitionTrigger,
)
from coding_harness.domain.models import (
    ContractVersion,
    PlanVersion,
    TransitionAudit,
)
from coding_harness.transaction.conflicts import ApplyConfirmation
from coding_harness.transaction.models import ApplyResult
from coding_harness.transaction.models import (
    ApplyDecision,
    ApplyPhase,
    RecoveryState,
)


def _bounded_text(value: object, *, maximum: int = 1024) -> bool:
    if type(value) is not str or not value or "\0" in value:
        return False
    try:
        return len(value.encode("utf-8", errors="strict")) <= maximum
    except UnicodeError:
        return False


def _optional_text(value: object) -> bool:
    return value is None or _bounded_text(value)


def _private_reference(value: object) -> bool:
    if not _bounded_text(value, maximum=4096) or "\\" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and tuple(path.parts)
        and all(part not in {"", ".", ".."} for part in path.parts)
        and str(path) == value
    )


@dataclass(frozen=True, slots=True)
class AuditRecord:
    order: int
    task_id: str
    event_kind: str
    subject_identity: str
    occurred_at: int
    source: TaskState | None
    target: TaskState | None
    trigger: TransitionTrigger | None
    reason: TransitionReason | None
    permitted: bool | None


@dataclass(frozen=True, slots=True)
class ApplyObservation:
    transaction_id: str
    task_id: str
    decision: ApplyDecision
    phase: ApplyPhase | None
    observed_task_state: TaskState
    recovery_state: RecoveryState | None
    plan_digest: str | None
    baseline_digest: str | None
    changeset_digest: str | None
    journal_reference: str | None
    index_digest_after: str | None
    reason: str
    occurred_at: int


@dataclass(frozen=True, slots=True)
class StartupRecoveryCandidate:
    task_id: str
    task_state: TaskState
    task_revision: int
    run_id: str | None
    transaction_id: str | None
    apply_phase: ApplyPhase | None
    journal_reference: str | None
    plan_version_identity: str | None
    contract_version_identity: str | None
    approval_identity: str | None
    approval_revision: int | None
    approval_plan_version_identity: str | None = None
    apply_plan_digest: str | None = None
    blocked_reason: BlockedReason | None = None
    workspace_reference: str | None = None
    workspace_identity: str | None = None
    container_cleanup_verified: bool = False
    file_effects_cleanup_verified: bool = False
    cleanup_verified: bool = False
    approval_type: ApprovalType | None = None
    approval_consumed: bool | None = None
    approval_revoked: bool | None = None
    approval_expires_at: int | None = None

    def __post_init__(self) -> None:
        if (
            not _bounded_text(self.task_id)
            or type(self.task_state) is not TaskState
            or type(self.task_revision) is not int
            or self.task_revision < 1
            or not _optional_text(self.run_id)
            or not _optional_text(self.transaction_id)
            or self.apply_phase is not None
            and type(self.apply_phase) is not ApplyPhase
            or self.journal_reference is not None
            and not _private_reference(self.journal_reference)
            or not _optional_text(self.plan_version_identity)
            or not _optional_text(self.contract_version_identity)
            or not _optional_text(self.approval_identity)
            or not _optional_text(self.approval_plan_version_identity)
            or not _optional_text(self.apply_plan_digest)
            or self.blocked_reason is not None
            and type(self.blocked_reason) is not BlockedReason
            or self.workspace_reference is not None
            and not _private_reference(self.workspace_reference)
            or (self.workspace_reference is None)
            != (self.workspace_identity is None)
            or self.workspace_identity is not None
            and (
                len(self.workspace_identity) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in self.workspace_identity
                )
            )
            or type(self.container_cleanup_verified) is not bool
            or type(self.file_effects_cleanup_verified) is not bool
            or type(self.cleanup_verified) is not bool
            or self.approval_type is not None
            and type(self.approval_type) is not ApprovalType
            or self.approval_consumed is not None
            and type(self.approval_consumed) is not bool
            or self.approval_revoked is not None
            and type(self.approval_revoked) is not bool
            or self.approval_expires_at is not None
            and (
                type(self.approval_expires_at) is not int
                or self.approval_expires_at < 0
            )
            or (self.approval_identity is None)
            != (self.approval_revision is None)
            or (self.approval_identity is None)
            != (self.approval_type is None)
            or (self.approval_identity is None)
            != (self.approval_consumed is None)
            or (self.approval_identity is None)
            != (self.approval_revoked is None)
            or (self.approval_identity is None)
            != (self.approval_expires_at is None)
            or self.approval_identity is None
            and self.approval_plan_version_identity is not None
            or self.approval_revision is not None
            and (
                type(self.approval_revision) is not int
                or self.approval_revision < 1
            )
            or self.transaction_id is None
            and (
                self.apply_phase is not None
                or self.journal_reference is not None
                or self.apply_plan_digest is not None
            )
        ):
            raise ValueError("startup recovery candidate is invalid")


@dataclass(frozen=True, slots=True)
class RecoveryFindingRecord:
    finding_id: str
    kind: str
    task_id: str
    run_id: str | None
    lease_id: str | None
    transaction_id: str | None
    journal_reference: str | None
    reason: str
    blocks_execution: bool

    def __post_init__(self) -> None:
        if (
            not _bounded_text(self.finding_id)
            or not _bounded_text(self.kind)
            or not _bounded_text(self.task_id)
            or not _optional_text(self.run_id)
            or not _optional_text(self.lease_id)
            or not _optional_text(self.transaction_id)
            or self.journal_reference is not None
            and not _private_reference(self.journal_reference)
            or not _bounded_text(self.reason, maximum=4096)
            or type(self.blocks_execution) is not bool
        ):
            raise ValueError("recovery finding record is invalid")


class HarnessStore(ABC):
    """Business-intent persistence operations used by the domain layer."""

    @abstractmethod
    def create_task(
        self,
        *,
        task_id: str,
        initial_state: TaskState,
        occurred_at: int,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_task_state(self, *, task_id: str) -> TaskState | None:
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def record_plan_version(
        self,
        *,
        plan: PlanVersion,
        occurred_at: int,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_plan_version(self, *, identity: str) -> PlanVersion | None:
        raise NotImplementedError

    @abstractmethod
    def record_contract_version(
        self,
        *,
        contract: ContractVersion,
        occurred_at: int,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_contract_version(
        self,
        *,
        identity: str,
    ) -> ContractVersion | None:
        raise NotImplementedError

    @abstractmethod
    def record_budget_version(
        self,
        *,
        budget: BudgetVersion,
        occurred_at: int,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_budget_version(self, *, identity: str) -> BudgetVersion | None:
        raise NotImplementedError

    @abstractmethod
    def record_approval(
        self,
        *,
        approval: Approval,
        occurred_at: int,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def update_approval(
        self,
        *,
        approval: Approval,
        expected_revision: int,
        occurred_at: int,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_approval(
        self,
        *,
        approval_identity: str,
        revision: int,
    ) -> Approval | None:
        raise NotImplementedError

    @abstractmethod
    def confirm_changeset(
        self,
        *,
        confirmation: ApplyConfirmation,
        occurred_at: int,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_changeset_confirmation(
        self,
        *,
        task_id: str,
        idempotency_key: str,
    ) -> ApplyConfirmation | None:
        raise NotImplementedError

    @abstractmethod
    def record_apply_observation(
        self,
        *,
        task_id: str,
        result: ApplyResult,
        journal_reference: str | None = None,
        occurred_at: int,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_apply_observation(
        self,
        *,
        transaction_id: str,
    ) -> ApplyObservation | None:
        raise NotImplementedError

    @abstractmethod
    def startup_recovery_candidates(
        self,
        *,
        limit: int,
    ) -> tuple[StartupRecoveryCandidate, ...]:
        raise NotImplementedError

    @abstractmethod
    def record_recovery_finding(
        self,
        *,
        finding: RecoveryFindingRecord,
        occurred_at: int,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def audit_events(self, *, task_id: str) -> tuple[AuditRecord, ...]:
        raise NotImplementedError


__all__ = [
    "ApplyObservation",
    "AuditRecord",
    "HarnessStore",
    "RecoveryFindingRecord",
    "StartupRecoveryCandidate",
]
