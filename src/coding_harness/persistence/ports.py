"""Narrow domain-facing persistence boundary."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from coding_harness.domain.approvals import Approval
from coding_harness.domain.budgets import BudgetVersion
from coding_harness.domain.enums import (
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
    def audit_events(self, *, task_id: str) -> tuple[AuditRecord, ...]:
        raise NotImplementedError


__all__ = ["ApplyObservation", "AuditRecord", "HarnessStore"]
