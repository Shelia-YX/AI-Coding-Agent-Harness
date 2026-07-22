from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from coding_harness.domain.enums import (
    TERMINAL_STATES,
    BlockedReason,
    IdempotencyStatus,
    TaskState,
    TransitionReason,
    TransitionTrigger,
    UnrecoverableFailureReason,
)
from coding_harness.domain.models import (
    IdempotencyRecord,
    TransitionAudit,
    TransitionCommand,
    TransitionResult,
)


_TRANSITIONS: Mapping[tuple[TaskState, TransitionTrigger], TaskState] = MappingProxyType(
    {
        (TaskState.DRAFT, TransitionTrigger.SUBMIT_TASK): TaskState.INVESTIGATING,
        (
            TaskState.INVESTIGATING,
            TransitionTrigger.REQUEST_CLARIFICATION,
        ): TaskState.AWAITING_CLARIFICATION,
        (
            TaskState.INVESTIGATING,
            TransitionTrigger.PERSIST_PLAN,
        ): TaskState.AWAITING_PLAN_APPROVAL,
        (
            TaskState.AWAITING_CLARIFICATION,
            TransitionTrigger.SUBMIT_CLARIFICATION,
        ): TaskState.INVESTIGATING,
        (
            TaskState.INVESTIGATING,
            TransitionTrigger.CONTINUE_INVESTIGATION,
        ): TaskState.INVESTIGATING,
        (
            TaskState.AWAITING_PLAN_APPROVAL,
            TransitionTrigger.APPROVE_PLAN,
        ): TaskState.READY_TO_EXECUTE,
        (
            TaskState.AWAITING_PLAN_APPROVAL,
            TransitionTrigger.REJECT_PLAN,
        ): TaskState.CANCELLED,
        (
            TaskState.READY_TO_EXECUTE,
            TransitionTrigger.CONTINUE_EXECUTION,
        ): TaskState.EXECUTING,
        (
            TaskState.READY_TO_EXECUTE,
            TransitionTrigger.PROVIDER_LOCKED,
        ): TaskState.AWAITING_PROVIDER_UNLOCK,
        (
            TaskState.EXECUTING,
            TransitionTrigger.REQUEST_ACTION_APPROVAL,
        ): TaskState.AWAITING_ACTION_APPROVAL,
        (
            TaskState.AWAITING_ACTION_APPROVAL,
            TransitionTrigger.APPROVE_ACTION,
        ): TaskState.READY_TO_EXECUTE,
        (
            TaskState.AWAITING_ACTION_APPROVAL,
            TransitionTrigger.REJECT_ACTION,
        ): TaskState.READY_TO_EXECUTE,
        (
            TaskState.EXECUTING,
            TransitionTrigger.REQUEST_BUDGET_REAPPROVAL,
        ): TaskState.AWAITING_BUDGET_APPROVAL,
        (
            TaskState.VERIFYING,
            TransitionTrigger.REQUEST_BUDGET_REAPPROVAL,
        ): TaskState.AWAITING_BUDGET_APPROVAL,
        (
            TaskState.AWAITING_BUDGET_APPROVAL,
            TransitionTrigger.APPROVE_BUDGET,
        ): TaskState.READY_TO_EXECUTE,
        (
            TaskState.AWAITING_BUDGET_APPROVAL,
            TransitionTrigger.REJECT_BUDGET,
        ): TaskState.BLOCKED,
        (
            TaskState.EXECUTING,
            TransitionTrigger.REVISE_PLAN,
        ): TaskState.AWAITING_PLAN_APPROVAL,
        (
            TaskState.EXECUTING,
            TransitionTrigger.START_VERIFICATION,
        ): TaskState.VERIFYING,
        (
            TaskState.VERIFYING,
            TransitionTrigger.REQUEST_USER_CONFIRMATION,
        ): TaskState.AWAITING_USER_CONFIRMATION,
        (
            TaskState.VERIFYING,
            TransitionTrigger.VERIFICATION_PASSED,
        ): TaskState.READY_TO_APPLY,
        (
            TaskState.VERIFYING,
            TransitionTrigger.VERIFICATION_FEEDBACK,
        ): TaskState.EXECUTING,
        (
            TaskState.AWAITING_USER_CONFIRMATION,
            TransitionTrigger.CONFIRM_USER_ACCEPTANCE,
        ): TaskState.READY_TO_APPLY,
        (
            TaskState.AWAITING_USER_CONFIRMATION,
            TransitionTrigger.REJECT_USER_ACCEPTANCE,
        ): TaskState.BLOCKED,
        (
            TaskState.READY_TO_APPLY,
            TransitionTrigger.CONFIRM_APPLY,
        ): TaskState.APPLYING,
        (
            TaskState.READY_TO_APPLY,
            TransitionTrigger.REJECT_APPLY,
        ): TaskState.NOT_APPLIED,
        (
            TaskState.APPLYING,
            TransitionTrigger.APPLY_SUCCEEDED,
        ): TaskState.COMPLETED,
        (
            TaskState.APPLYING,
            TransitionTrigger.APPLY_FAILED,
        ): TaskState.ROLLING_BACK,
        (
            TaskState.ROLLING_BACK,
            TransitionTrigger.ROLLBACK_SUCCEEDED,
        ): TaskState.FAILED,
        (
            TaskState.ROLLING_BACK,
            TransitionTrigger.ROLLBACK_RECOVERY_REQUIRED,
        ): TaskState.RECOVERY_REQUIRED,
        (
            TaskState.RECOVERY_REQUIRED,
            TransitionTrigger.REQUEST_RECOVERY,
        ): TaskState.ROLLING_BACK,
        (
            TaskState.AWAITING_PROVIDER_UNLOCK,
            TransitionTrigger.CONTINUE_PROVIDER_UNLOCK,
        ): TaskState.EXECUTING,
        (
            TaskState.BLOCKED,
            TransitionTrigger.CONTINUE_BLOCKED_EXECUTION,
        ): TaskState.EXECUTING,
        (
            TaskState.BLOCKED,
            TransitionTrigger.SUBMIT_BLOCKED_CLARIFICATION,
        ): TaskState.INVESTIGATING,
        (
            TaskState.BLOCKED,
            TransitionTrigger.CONTINUE_APPLY_CONFLICT,
        ): TaskState.INVESTIGATING,
    }
)

_ACTIVE_STATES = frozenset(
    {
        TaskState.INVESTIGATING,
        TaskState.EXECUTING,
        TaskState.VERIFYING,
        TaskState.APPLYING,
        TaskState.ROLLING_BACK,
    }
)

_CANCELLABLE_STATES = frozenset(TaskState) - TERMINAL_STATES - {
    TaskState.RECOVERY_REQUIRED
}

_BLOCKED_REASON_SOURCES: Mapping[BlockedReason, frozenset[TaskState]] = (
    MappingProxyType(
        {
            BlockedReason.BLOCKED_MISSING_DEPENDENCY: frozenset(
                {
                    TaskState.INVESTIGATING,
                    TaskState.EXECUTING,
                    TaskState.VERIFYING,
                }
            ),
            BlockedReason.BLOCKED_UNSUPPORTED_CAPABILITY: frozenset(
                {TaskState.INVESTIGATING, TaskState.EXECUTING}
            ),
            BlockedReason.DOCKER_UNAVAILABLE: frozenset(
                {
                    TaskState.INVESTIGATING,
                    TaskState.EXECUTING,
                    TaskState.VERIFYING,
                }
            ),
            BlockedReason.PROVIDER_UNAVAILABLE: frozenset(
                {TaskState.INVESTIGATING, TaskState.EXECUTING}
            ),
            BlockedReason.CONTEXT_EXPORT_DENIED: frozenset(
                {TaskState.INVESTIGATING, TaskState.EXECUTING}
            ),
            BlockedReason.APPLY_CONFLICT: frozenset({TaskState.APPLYING}),
            BlockedReason.BLOCKED_POLICY_ERROR: frozenset(
                {TaskState.INVESTIGATING, TaskState.EXECUTING}
            ),
            BlockedReason.PROVIDER_CONFIGURATION_ERROR: frozenset(
                {TaskState.INVESTIGATING, TaskState.EXECUTING}
            ),
            BlockedReason.PERSISTENCE_FAILED: _ACTIVE_STATES,
            # These two reasons have dedicated waiting-state transitions.
            BlockedReason.BUDGET_EXTENSION_REJECTED: frozenset(),
            BlockedReason.USER_ACCEPTANCE_REJECTED: frozenset(),
        }
    )
)

_FAILURE_REASON_SOURCES: Mapping[
    UnrecoverableFailureReason, frozenset[TaskState]
] = MappingProxyType(
    {
        UnrecoverableFailureReason.INVALID_ACTION: frozenset(
            {TaskState.INVESTIGATING, TaskState.EXECUTING}
        ),
        UnrecoverableFailureReason.HARD_LIMIT_REACHED: frozenset(
            {
                TaskState.INVESTIGATING,
                TaskState.EXECUTING,
                TaskState.VERIFYING,
            }
        ),
        UnrecoverableFailureReason.PROVIDER_RESPONSE_INVALID: frozenset(
            {TaskState.INVESTIGATING, TaskState.EXECUTING}
        ),
        UnrecoverableFailureReason.OUTPUT_LIMIT: frozenset(
            {TaskState.EXECUTING, TaskState.VERIFYING}
        ),
        UnrecoverableFailureReason.CREATE_FAILED: frozenset(
            {TaskState.EXECUTING, TaskState.VERIFYING}
        ),
        UnrecoverableFailureReason.START_FAILED: frozenset(
            {TaskState.EXECUTING, TaskState.VERIFYING}
        ),
        UnrecoverableFailureReason.RESOURCE_LIMIT: frozenset(
            {TaskState.EXECUTING, TaskState.VERIFYING}
        ),
    }
)

_LEASE_ACQUISITION_TRIGGERS = frozenset(
    {
        TransitionTrigger.SUBMIT_TASK,
        TransitionTrigger.CONTINUE_INVESTIGATION,
        TransitionTrigger.CONTINUE_EXECUTION,
        TransitionTrigger.CONFIRM_APPLY,
        TransitionTrigger.REQUEST_RECOVERY,
        TransitionTrigger.CONTINUE_PROVIDER_UNLOCK,
        TransitionTrigger.CONTINUE_BLOCKED_EXECUTION,
        TransitionTrigger.CONTINUE_APPLY_CONFLICT,
    }
)

_AGENT_LOOP_TRIGGERS = frozenset(
    {
        TransitionTrigger.SUBMIT_TASK,
        TransitionTrigger.CONTINUE_INVESTIGATION,
        TransitionTrigger.CONTINUE_EXECUTION,
        TransitionTrigger.CONTINUE_PROVIDER_UNLOCK,
        TransitionTrigger.CONTINUE_BLOCKED_EXECUTION,
        TransitionTrigger.CONTINUE_APPLY_CONFLICT,
    }
)

_REQUIRED_PRECONDITIONS: Mapping[TransitionTrigger, tuple[str, ...]] = MappingProxyType(
    {
        TransitionTrigger.SUBMIT_CLARIFICATION: ("clarification_persisted",),
        TransitionTrigger.CONTINUE_INVESTIGATION: (
            "clarification_persisted",
            "frozen_checks_passed",
        ),
        TransitionTrigger.CONTINUE_EXECUTION: ("frozen_checks_passed",),
        TransitionTrigger.CONTINUE_PROVIDER_UNLOCK: (
            "provider_unlocked",
            "frozen_checks_passed",
        ),
        TransitionTrigger.CONTINUE_BLOCKED_EXECUTION: ("frozen_checks_passed",),
        TransitionTrigger.SUBMIT_BLOCKED_CLARIFICATION: (
            "clarification_persisted",
        ),
        TransitionTrigger.CONTINUE_APPLY_CONFLICT: ("frozen_checks_passed",),
        TransitionTrigger.VERIFICATION_PASSED: (
            "acceptance_ready",
            "changeset_ready",
        ),
        TransitionTrigger.CONFIRM_USER_ACCEPTANCE: (
            "acceptance_ready",
            "changeset_ready",
        ),
        TransitionTrigger.CONFIRM_APPLY: (
            "frozen_checks_passed",
            "changeset_ready",
            "apply_confirmation_valid",
        ),
        TransitionTrigger.APPLY_SUCCEEDED: ("writeback_verified",),
        TransitionTrigger.ROLLBACK_SUCCEEDED: ("rollback_verified",),
        TransitionTrigger.REQUEST_RECOVERY: ("recovery_evidence_valid",),
    }
)


class StateMachine:
    @staticmethod
    def transition(command: TransitionCommand) -> TransitionResult:
        replay = StateMachine._idempotency_replay(command)
        if replay is not None:
            return replay

        if command.expected_state is not command.current_state:
            return StateMachine._denied(
                command,
                TransitionReason.EXPECTED_STATE_CONFLICT,
            )

        if not StateMachine._versions_match(command):
            return StateMachine._denied(
                command,
                TransitionReason.EXPECTED_VERSION_CONFLICT,
            )

        if command.current_state in TERMINAL_STATES:
            return StateMachine._denied(command, TransitionReason.TERMINAL_STATE)

        if command.uncertain_file_effect:
            if command.current_state is TaskState.RECOVERY_REQUIRED:
                return StateMachine._recovery_noop(command)
            return StateMachine._permitted(
                command,
                TaskState.RECOVERY_REQUIRED,
                TransitionReason.UNCERTAIN_EFFECT_RECOVERY,
                lease_acquisition_required=False,
                agent_loop_resume_permitted=False,
            )

        if command.trigger is TransitionTrigger.CANCEL_TASK:
            return StateMachine._cancel(command)
        if command.trigger is TransitionTrigger.ENTER_BLOCKED:
            return StateMachine._block(command)
        if command.trigger is TransitionTrigger.FAIL_UNRECOVERABLY:
            return StateMachine._fail(command)

        target = StateMachine._target_for(command)
        if target is None:
            return StateMachine._denied(command, TransitionReason.ILLEGAL_TRANSITION)

        required = _REQUIRED_PRECONDITIONS.get(command.trigger, ())
        if any(not getattr(command.preconditions, name) for name in required):
            return StateMachine._denied(command, TransitionReason.PRECONDITION_FAILED)

        return StateMachine._permitted(
            command,
            target,
            TransitionReason.PERMITTED,
            lease_acquisition_required=(
                command.trigger in _LEASE_ACQUISITION_TRIGGERS
            ),
            agent_loop_resume_permitted=command.trigger in _AGENT_LOOP_TRIGGERS,
        )

    @staticmethod
    def _target_for(command: TransitionCommand) -> TaskState | None:
        return _TRANSITIONS.get((command.current_state, command.trigger))

    @staticmethod
    def _cancel(command: TransitionCommand) -> TransitionResult:
        if command.current_state not in _CANCELLABLE_STATES:
            return StateMachine._denied(command, TransitionReason.ILLEGAL_TRANSITION)
        if not command.preconditions.safe_cleanup_completed:
            return StateMachine._denied(command, TransitionReason.PRECONDITION_FAILED)
        return StateMachine._permitted(
            command,
            TaskState.CANCELLED,
            TransitionReason.PERMITTED,
            lease_acquisition_required=False,
            agent_loop_resume_permitted=False,
        )

    @staticmethod
    def _block(command: TransitionCommand) -> TransitionResult:
        reason = command.blocked_reason
        if type(reason) is not BlockedReason:
            return StateMachine._denied(command, TransitionReason.INVALID_REASON)
        if command.current_state not in _BLOCKED_REASON_SOURCES[reason]:
            return StateMachine._denied(command, TransitionReason.INVALID_REASON)
        if (
            not command.preconditions.active_execution_confirmed
            or not command.preconditions.safe_cleanup_completed
        ):
            return StateMachine._denied(command, TransitionReason.PRECONDITION_FAILED)
        return StateMachine._permitted(
            command,
            TaskState.BLOCKED,
            TransitionReason.PERMITTED,
            lease_acquisition_required=False,
            agent_loop_resume_permitted=False,
        )

    @staticmethod
    def _fail(command: TransitionCommand) -> TransitionResult:
        reason = command.failure_reason
        if type(reason) is not UnrecoverableFailureReason:
            return StateMachine._denied(command, TransitionReason.INVALID_REASON)
        if command.current_state not in _FAILURE_REASON_SOURCES[reason]:
            return StateMachine._denied(command, TransitionReason.INVALID_REASON)
        if (
            not command.preconditions.active_execution_confirmed
            or not command.preconditions.safe_cleanup_completed
        ):
            return StateMachine._denied(command, TransitionReason.PRECONDITION_FAILED)
        return StateMachine._permitted(
            command,
            TaskState.FAILED,
            TransitionReason.PERMITTED,
            lease_acquisition_required=False,
            agent_loop_resume_permitted=False,
        )

    @staticmethod
    def _recovery_noop(command: TransitionCommand) -> TransitionResult:
        return StateMachine._result(
            command,
            target=TaskState.RECOVERY_REQUIRED,
            permitted=True,
            should_apply=False,
            changed=False,
            reason=TransitionReason.RECOVERY_ALREADY_REQUIRED,
            lease_acquisition_required=False,
            agent_loop_resume_permitted=False,
            idempotency_status=IdempotencyStatus.NEW,
            idempotency_record=None,
        )

    @staticmethod
    def _versions_match(command: TransitionCommand) -> bool:
        if command.expected_plan_identity is not None:
            if command.current_plan_version is None:
                return False
            if command.current_plan_version.identity != command.expected_plan_identity:
                return False
        if command.expected_contract_identity is not None:
            if command.current_contract_version is None:
                return False
            if (
                command.current_contract_version.identity
                != command.expected_contract_identity
            ):
                return False
        return True

    @staticmethod
    def _idempotency_replay(command: TransitionCommand) -> TransitionResult | None:
        prior = command.prior_idempotency
        if prior is None or prior.key != command.idempotency.key:
            return None
        if prior.request_digest != command.idempotency.request_digest:
            return StateMachine._denied(
                command,
                TransitionReason.IDEMPOTENCY_CONFLICT,
                idempotency_status=IdempotencyStatus.CONFLICT,
                idempotency_record=prior,
            )
        audit = TransitionAudit(
            source=prior.source,
            target=prior.target,
            trigger=prior.trigger,
            permitted=prior.permitted,
            reason=prior.reason,
        )
        return TransitionResult(
            source=prior.source,
            target=prior.target,
            permitted=prior.permitted,
            should_apply=False,
            changed=False,
            reason=prior.reason,
            audit=audit,
            lease_acquisition_required=False,
            agent_loop_resume_permitted=False,
            idempotency_status=IdempotencyStatus.REPLAYED,
            idempotency_record=prior,
        )

    @staticmethod
    def _denied(
        command: TransitionCommand,
        reason: TransitionReason,
        *,
        idempotency_status: IdempotencyStatus = IdempotencyStatus.NEW,
        idempotency_record: IdempotencyRecord | None = None,
    ) -> TransitionResult:
        return StateMachine._result(
            command,
            target=command.current_state,
            permitted=False,
            should_apply=False,
            changed=False,
            reason=reason,
            lease_acquisition_required=False,
            agent_loop_resume_permitted=False,
            idempotency_status=idempotency_status,
            idempotency_record=idempotency_record,
        )

    @staticmethod
    def _permitted(
        command: TransitionCommand,
        target: TaskState,
        reason: TransitionReason,
        *,
        lease_acquisition_required: bool,
        agent_loop_resume_permitted: bool,
    ) -> TransitionResult:
        return StateMachine._result(
            command,
            target=target,
            permitted=True,
            should_apply=True,
            changed=target is not command.current_state,
            reason=reason,
            lease_acquisition_required=lease_acquisition_required,
            agent_loop_resume_permitted=agent_loop_resume_permitted,
            idempotency_status=IdempotencyStatus.NEW,
            idempotency_record=None,
        )

    @staticmethod
    def _result(
        command: TransitionCommand,
        *,
        target: TaskState,
        permitted: bool,
        should_apply: bool,
        changed: bool,
        reason: TransitionReason,
        lease_acquisition_required: bool,
        agent_loop_resume_permitted: bool,
        idempotency_status: IdempotencyStatus,
        idempotency_record: IdempotencyRecord | None,
    ) -> TransitionResult:
        audit = TransitionAudit(
            source=command.current_state,
            target=target,
            trigger=command.trigger,
            permitted=permitted,
            reason=reason,
        )
        record = idempotency_record
        if record is None and idempotency_status is IdempotencyStatus.NEW:
            record = IdempotencyRecord(
                key=command.idempotency.key,
                request_digest=command.idempotency.request_digest,
                source=command.current_state,
                target=target,
                trigger=command.trigger,
                permitted=permitted,
                reason=reason,
            )
        return TransitionResult(
            source=command.current_state,
            target=target,
            permitted=permitted,
            should_apply=should_apply,
            changed=changed,
            reason=reason,
            audit=audit,
            lease_acquisition_required=lease_acquisition_required,
            agent_loop_resume_permitted=agent_loop_resume_permitted,
            idempotency_status=idempotency_status,
            idempotency_record=record,
        )
