from __future__ import annotations

from dataclasses import dataclass

from coding_harness.domain.enums import (
    BlockedReason,
    IdempotencyStatus,
    TaskState,
    TransitionReason,
    TransitionTrigger,
    UnrecoverableFailureReason,
)


@dataclass(frozen=True, slots=True, eq=False)
class PlanVersion:
    identity: str
    task_id: str
    sequence: int
    content_digest: str
    display_text: str

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return self.identity == other.identity

    def __hash__(self) -> int:
        return hash((type(self), self.identity))


@dataclass(frozen=True, slots=True, eq=False)
class ContractVersion:
    identity: str
    task_id: str
    sequence: int
    content_digest: str
    display_text: str

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return NotImplemented
        return self.identity == other.identity

    def __hash__(self) -> int:
        return hash((type(self), self.identity))


@dataclass(frozen=True, slots=True)
class IdempotencyRequest:
    key: str
    request_digest: str


@dataclass(frozen=True, slots=True)
class TransitionPreconditions:
    frozen_checks_passed: bool
    clarification_persisted: bool
    provider_unlocked: bool
    changeset_ready: bool
    acceptance_ready: bool
    apply_confirmation_valid: bool
    writeback_verified: bool
    rollback_verified: bool
    recovery_evidence_valid: bool
    safe_cleanup_completed: bool = False
    active_execution_confirmed: bool = False


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    key: str
    request_digest: str
    source: TaskState
    target: TaskState
    trigger: TransitionTrigger
    permitted: bool
    reason: TransitionReason


@dataclass(frozen=True, slots=True)
class TransitionCommand:
    current_state: TaskState
    expected_state: TaskState
    trigger: TransitionTrigger
    idempotency: IdempotencyRequest
    preconditions: TransitionPreconditions
    uncertain_file_effect: bool = False
    current_plan_version: PlanVersion | None = None
    expected_plan_identity: str | None = None
    current_contract_version: ContractVersion | None = None
    expected_contract_identity: str | None = None
    prior_idempotency: IdempotencyRecord | None = None
    blocked_reason: BlockedReason | None = None
    failure_reason: UnrecoverableFailureReason | None = None


@dataclass(frozen=True, slots=True)
class TransitionAudit:
    source: TaskState
    target: TaskState
    trigger: TransitionTrigger
    permitted: bool
    reason: TransitionReason


@dataclass(frozen=True, slots=True)
class TransitionResult:
    source: TaskState
    target: TaskState
    permitted: bool
    should_apply: bool
    changed: bool
    reason: TransitionReason
    audit: TransitionAudit
    lease_acquisition_required: bool
    agent_loop_resume_permitted: bool
    idempotency_status: IdempotencyStatus
    idempotency_record: IdempotencyRecord | None
