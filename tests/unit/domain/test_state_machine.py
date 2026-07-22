from __future__ import annotations

import importlib
from collections.abc import Callable

import pytest


TASK_STATES = (
    "DRAFT",
    "INVESTIGATING",
    "AWAITING_CLARIFICATION",
    "AWAITING_PLAN_APPROVAL",
    "READY_TO_EXECUTE",
    "EXECUTING",
    "AWAITING_ACTION_APPROVAL",
    "AWAITING_BUDGET_APPROVAL",
    "VERIFYING",
    "AWAITING_USER_CONFIRMATION",
    "READY_TO_APPLY",
    "APPLYING",
    "ROLLING_BACK",
    "RECOVERY_REQUIRED",
    "AWAITING_PROVIDER_UNLOCK",
    "BLOCKED",
    "FAILED",
    "CANCELLED",
    "NOT_APPLIED",
    "COMPLETED",
)

TERMINAL_STATES = frozenset({"COMPLETED", "NOT_APPLIED", "FAILED", "CANCELLED"})

WP05_OWNER_PVS = (
    "PV-AGT-003",
    "PV-AGT-004",
    "PV-AGT-005",
    "PV-PST-004",
    "PV-PST-005",
    "PV-PST-006",
    "PV-TXN-001",
    "PV-TXN-002",
    "PV-TXN-003",
    "PV-TXN-004",
)


def _load_wp05_api():
    try:
        enums = importlib.import_module("coding_harness.domain.enums")
        models = importlib.import_module("coding_harness.domain.models")
        state_machine = importlib.import_module("coding_harness.domain.state_machine")
    except ModuleNotFoundError:
        pytest.fail("WP-05 API unavailable", pytrace=False)
    return enums, models, state_machine


def _request(models, key: str = "request:1", digest: str = "a" * 64):
    return models.IdempotencyRequest(key=key, request_digest=digest)


def _preconditions(models, **overrides: bool):
    values = {
        "frozen_checks_passed": True,
        "clarification_persisted": True,
        "provider_unlocked": True,
        "changeset_ready": True,
        "acceptance_ready": True,
        "apply_confirmation_valid": True,
        "writeback_verified": True,
        "rollback_verified": True,
        "recovery_evidence_valid": True,
    }
    values.update(overrides)
    return models.TransitionPreconditions(**values)


def _boundary_preconditions(models, **overrides: bool):
    values = {
        "frozen_checks_passed": True,
        "clarification_persisted": True,
        "provider_unlocked": True,
        "changeset_ready": True,
        "acceptance_ready": True,
        "apply_confirmation_valid": True,
        "writeback_verified": True,
        "rollback_verified": True,
        "recovery_evidence_valid": True,
        "safe_cleanup_completed": True,
        "active_execution_confirmed": True,
    }
    values.update(overrides)
    return models.TransitionPreconditions(**values)


def _command(
    enums,
    models,
    source: str,
    trigger: str,
    *,
    key: str = "request:1",
    digest: str = "a" * 64,
    uncertain_file_effect: bool = False,
    preconditions=None,
    **versions: object,
):
    return models.TransitionCommand(
        current_state=enums.TaskState[source],
        expected_state=enums.TaskState[source],
        trigger=enums.TransitionTrigger[trigger],
        idempotency=_request(models, key, digest),
        preconditions=preconditions or _preconditions(models),
        uncertain_file_effect=uncertain_file_effect,
        **versions,
    )


def _transition(source: str, trigger: str, **kwargs: object):
    enums, models, state_machine = _load_wp05_api()
    command = _command(enums, models, source, trigger, **kwargs)
    return enums, models, state_machine.StateMachine.transition(command)


def _assert_task_state_closed() -> None:
    enums, _, _ = _load_wp05_api()
    assert tuple(state.name for state in enums.TaskState) == TASK_STATES
    assert tuple(state.value for state in enums.TaskState) == TASK_STATES
    assert len(enums.TaskState.__members__) == 20
    assert {state.value for state in enums.TERMINAL_STATES} == TERMINAL_STATES
    assert "EXECUTION_SLOT_BUSY" not in enums.TaskState.__members__
    assert "RESUME" not in enums.TaskState.__members__


def _assert_allowed_transition_matrix() -> None:
    cases = (
        ("DRAFT", "SUBMIT_TASK", "INVESTIGATING"),
        ("INVESTIGATING", "REQUEST_CLARIFICATION", "AWAITING_CLARIFICATION"),
        ("INVESTIGATING", "PERSIST_PLAN", "AWAITING_PLAN_APPROVAL"),
        ("AWAITING_CLARIFICATION", "SUBMIT_CLARIFICATION", "INVESTIGATING"),
        ("INVESTIGATING", "CONTINUE_INVESTIGATION", "INVESTIGATING"),
        ("AWAITING_PLAN_APPROVAL", "APPROVE_PLAN", "READY_TO_EXECUTE"),
        ("AWAITING_PLAN_APPROVAL", "REJECT_PLAN", "CANCELLED"),
        ("READY_TO_EXECUTE", "CONTINUE_EXECUTION", "EXECUTING"),
        ("READY_TO_EXECUTE", "PROVIDER_LOCKED", "AWAITING_PROVIDER_UNLOCK"),
        ("EXECUTING", "REQUEST_ACTION_APPROVAL", "AWAITING_ACTION_APPROVAL"),
        ("AWAITING_ACTION_APPROVAL", "APPROVE_ACTION", "READY_TO_EXECUTE"),
        ("AWAITING_ACTION_APPROVAL", "REJECT_ACTION", "READY_TO_EXECUTE"),
        ("EXECUTING", "REQUEST_BUDGET_REAPPROVAL", "AWAITING_BUDGET_APPROVAL"),
        ("VERIFYING", "REQUEST_BUDGET_REAPPROVAL", "AWAITING_BUDGET_APPROVAL"),
        ("AWAITING_BUDGET_APPROVAL", "APPROVE_BUDGET", "READY_TO_EXECUTE"),
        ("AWAITING_BUDGET_APPROVAL", "REJECT_BUDGET", "BLOCKED"),
        ("EXECUTING", "REVISE_PLAN", "AWAITING_PLAN_APPROVAL"),
        ("EXECUTING", "START_VERIFICATION", "VERIFYING"),
        ("VERIFYING", "REQUEST_USER_CONFIRMATION", "AWAITING_USER_CONFIRMATION"),
        ("VERIFYING", "VERIFICATION_PASSED", "READY_TO_APPLY"),
        ("VERIFYING", "VERIFICATION_FEEDBACK", "EXECUTING"),
        ("AWAITING_USER_CONFIRMATION", "CONFIRM_USER_ACCEPTANCE", "READY_TO_APPLY"),
        ("AWAITING_USER_CONFIRMATION", "REJECT_USER_ACCEPTANCE", "BLOCKED"),
        ("READY_TO_APPLY", "CONFIRM_APPLY", "APPLYING"),
        ("READY_TO_APPLY", "REJECT_APPLY", "NOT_APPLIED"),
        ("APPLYING", "APPLY_SUCCEEDED", "COMPLETED"),
        ("APPLYING", "APPLY_FAILED", "ROLLING_BACK"),
        ("ROLLING_BACK", "ROLLBACK_SUCCEEDED", "FAILED"),
        ("ROLLING_BACK", "ROLLBACK_RECOVERY_REQUIRED", "RECOVERY_REQUIRED"),
        ("RECOVERY_REQUIRED", "REQUEST_RECOVERY", "ROLLING_BACK"),
        ("AWAITING_PROVIDER_UNLOCK", "CONTINUE_PROVIDER_UNLOCK", "EXECUTING"),
        ("BLOCKED", "CONTINUE_BLOCKED_EXECUTION", "EXECUTING"),
        ("BLOCKED", "SUBMIT_BLOCKED_CLARIFICATION", "INVESTIGATING"),
        ("BLOCKED", "CONTINUE_APPLY_CONFLICT", "INVESTIGATING"),
    )
    for index, (source, trigger, target) in enumerate(cases):
        _, _, result = _transition(
            source,
            trigger,
            key=f"matrix:{index}",
            digest=f"{index + 1:064x}",
        )
        assert result.permitted is True, (source, trigger, result)
        assert result.source.value == source
        assert result.target.value == target
        assert result.should_apply is True
        assert result.audit.permitted is True
        assert result.audit.source is result.source
        assert result.audit.target is result.target


def _assert_illegal_transition_fails_closed() -> None:
    enums, _, result = _transition("DRAFT", "CONFIRM_APPLY")
    assert result.permitted is False
    assert result.target is enums.TaskState.DRAFT
    assert result.should_apply is False
    assert result.reason is enums.TransitionReason.ILLEGAL_TRANSITION
    assert result.audit.permitted is False
    assert result.audit.reason is result.reason


def _assert_blocked_and_failure_guards() -> None:
    enums, models, state_machine = _load_wp05_api()

    def evaluate(
        source: str,
        trigger: str,
        *,
        key: str,
        blocked_reason=None,
        failure_reason=None,
        uncertain_file_effect: bool = False,
        preconditions=None,
    ):
        command = _command(
            enums,
            models,
            source,
            trigger,
            key=key,
            blocked_reason=blocked_reason,
            failure_reason=failure_reason,
            uncertain_file_effect=uncertain_file_effect,
            preconditions=preconditions or _boundary_preconditions(models),
        )
        return state_machine.StateMachine.transition(command)

    for key, reason in (
        ("block:missing", None),
        ("block:unknown", "UNKNOWN_BLOCKED_REASON"),
    ):
        denied = evaluate(
            "EXECUTING",
            "ENTER_BLOCKED",
            key=key,
            blocked_reason=reason,
        )
        assert denied.permitted is False
        assert denied.reason is enums.TransitionReason.INVALID_REASON

    incompatible = evaluate(
        "INVESTIGATING",
        "ENTER_BLOCKED",
        key="block:phase-mismatch",
        blocked_reason=enums.BlockedReason.APPLY_CONFLICT,
    )
    assert incompatible.permitted is False
    assert incompatible.reason is enums.TransitionReason.INVALID_REASON

    inactive = evaluate(
        "READY_TO_EXECUTE",
        "ENTER_BLOCKED",
        key="block:inactive-state",
        blocked_reason=enums.BlockedReason.BLOCKED_POLICY_ERROR,
    )
    assert inactive.permitted is False

    not_active_now = evaluate(
        "EXECUTING",
        "ENTER_BLOCKED",
        key="block:not-active-now",
        blocked_reason=enums.BlockedReason.BLOCKED_POLICY_ERROR,
        preconditions=_boundary_preconditions(
            models,
            active_execution_confirmed=False,
        ),
    )
    assert not_active_now.permitted is False
    assert not_active_now.reason is enums.TransitionReason.PRECONDITION_FAILED

    blocked = evaluate(
        "EXECUTING",
        "ENTER_BLOCKED",
        key="block:valid",
        blocked_reason=enums.BlockedReason.BLOCKED_POLICY_ERROR,
    )
    assert blocked.permitted is True
    assert blocked.target is enums.TaskState.BLOCKED

    for key, reason in (
        ("failure:missing", None),
        ("failure:unknown", "UNKNOWN_FAILURE_REASON"),
        ("failure:not-terminal", enums.BlockedReason.BLOCKED_POLICY_ERROR),
    ):
        denied = evaluate(
            "EXECUTING",
            "FAIL_UNRECOVERABLY",
            key=key,
            failure_reason=reason,
        )
        assert denied.permitted is False
        assert denied.reason is enums.TransitionReason.INVALID_REASON

    unsafe_cleanup = evaluate(
        "EXECUTING",
        "FAIL_UNRECOVERABLY",
        key="failure:cleanup-incomplete",
        failure_reason=enums.UnrecoverableFailureReason.HARD_LIMIT_REACHED,
        preconditions=_boundary_preconditions(
            models,
            safe_cleanup_completed=False,
        ),
    )
    assert unsafe_cleanup.permitted is False
    assert unsafe_cleanup.reason is enums.TransitionReason.PRECONDITION_FAILED

    wrong_phase = evaluate(
        "APPLYING",
        "FAIL_UNRECOVERABLY",
        key="failure:phase-mismatch",
        failure_reason=enums.UnrecoverableFailureReason.HARD_LIMIT_REACHED,
    )
    assert wrong_phase.permitted is False
    assert wrong_phase.reason is enums.TransitionReason.INVALID_REASON

    failed = evaluate(
        "EXECUTING",
        "FAIL_UNRECOVERABLY",
        key="failure:valid",
        failure_reason=enums.UnrecoverableFailureReason.HARD_LIMIT_REACHED,
    )
    assert failed.permitted is True
    assert failed.target is enums.TaskState.FAILED

    uncertain = evaluate(
        "EXECUTING",
        "FAIL_UNRECOVERABLY",
        key="failure:uncertain",
        failure_reason=enums.UnrecoverableFailureReason.HARD_LIMIT_REACHED,
        uncertain_file_effect=True,
    )
    assert uncertain.permitted is True
    assert uncertain.target is enums.TaskState.RECOVERY_REQUIRED
    assert uncertain.reason is enums.TransitionReason.UNCERTAIN_EFFECT_RECOVERY


def _assert_clarification_pauses() -> None:
    enums, _, submitted = _transition("AWAITING_CLARIFICATION", "SUBMIT_CLARIFICATION")
    assert submitted.target is enums.TaskState.INVESTIGATING
    assert submitted.agent_loop_resume_permitted is False
    assert submitted.lease_acquisition_required is False

    _, models, state_machine = _load_wp05_api()
    blocked_command = _command(
        enums,
        models,
        "INVESTIGATING",
        "CONTINUE_INVESTIGATION",
        key="clarification:blocked",
        digest="b" * 64,
        preconditions=_preconditions(models, clarification_persisted=False),
    )
    blocked = state_machine.StateMachine.transition(blocked_command)
    assert blocked.permitted is False
    assert blocked.reason is enums.TransitionReason.PRECONDITION_FAILED


def _assert_continue_requires_lease() -> None:
    for source, trigger in (
        ("INVESTIGATING", "CONTINUE_INVESTIGATION"),
        ("READY_TO_EXECUTE", "CONTINUE_EXECUTION"),
        ("AWAITING_PROVIDER_UNLOCK", "CONTINUE_PROVIDER_UNLOCK"),
        ("BLOCKED", "CONTINUE_BLOCKED_EXECUTION"),
    ):
        _, _, result = _transition(source, trigger, key=f"continue:{source}")
        assert result.permitted is True
        assert result.lease_acquisition_required is True
        assert result.agent_loop_resume_permitted is True
        assert not hasattr(result, "lease")


def _assert_terminal_rejects_effect() -> None:
    enums, _, _ = _load_wp05_api()
    for terminal in TERMINAL_STATES:
        _, _, result = _transition(terminal, "SUBMIT_TASK", key=f"terminal:{terminal}")
        assert result.permitted is False
        assert result.target.value == terminal
        assert result.reason is enums.TransitionReason.TERMINAL_STATE
        assert result.should_apply is False
        assert result.lease_acquisition_required is False


def _assert_cancel_guards() -> None:
    enums, models, state_machine = _load_wp05_api()

    def cancel(*, key: str, cleanup: bool, uncertain: bool = False):
        command = _command(
            enums,
            models,
            "READY_TO_EXECUTE",
            "CANCEL_TASK",
            key=key,
            uncertain_file_effect=uncertain,
            preconditions=_boundary_preconditions(
                models,
                safe_cleanup_completed=cleanup,
            ),
        )
        return state_machine.StateMachine.transition(command)

    cleanup_incomplete = cancel(key="cancel:unsafe", cleanup=False)
    assert cleanup_incomplete.permitted is False
    assert cleanup_incomplete.reason is enums.TransitionReason.PRECONDITION_FAILED

    uncertain = cancel(key="cancel:uncertain", cleanup=True, uncertain=True)
    assert uncertain.permitted is True
    assert uncertain.target is enums.TaskState.RECOVERY_REQUIRED
    assert uncertain.reason is enums.TransitionReason.UNCERTAIN_EFFECT_RECOVERY

    cancelled = cancel(key="cancel:valid", cleanup=True)
    assert cancelled.permitted is True
    assert cancelled.target is enums.TaskState.CANCELLED

    recovery_cancel = _command(
        enums,
        models,
        "RECOVERY_REQUIRED",
        "CANCEL_TASK",
        key="cancel:recovery",
        preconditions=_boundary_preconditions(models),
    )
    denied = state_machine.StateMachine.transition(recovery_cancel)
    assert denied.permitted is False
    assert denied.reason is enums.TransitionReason.ILLEGAL_TRANSITION


def _assert_expected_state_and_version_conflicts() -> None:
    enums, models, state_machine = _load_wp05_api()
    wrong_state = _command(enums, models, "DRAFT", "SUBMIT_TASK", key="state:conflict")
    object.__setattr__(wrong_state, "expected_state", enums.TaskState.INVESTIGATING)
    state_result = state_machine.StateMachine.transition(wrong_state)
    assert state_result.permitted is False
    assert state_result.reason is enums.TransitionReason.EXPECTED_STATE_CONFLICT

    plan = models.PlanVersion(
        identity="plan:v2",
        task_id="task:1",
        sequence=2,
        content_digest="2" * 64,
        display_text="same display",
    )
    other_identity = models.PlanVersion(
        identity="plan:v1",
        task_id="task:1",
        sequence=1,
        content_digest="1" * 64,
        display_text="same display",
    )
    assert plan != other_identity
    command = _command(
        enums,
        models,
        "AWAITING_PLAN_APPROVAL",
        "APPROVE_PLAN",
        key="version:conflict",
        current_plan_version=plan,
        expected_plan_identity=other_identity.identity,
    )
    version_result = state_machine.StateMachine.transition(command)
    assert version_result.permitted is False
    assert version_result.reason is enums.TransitionReason.EXPECTED_VERSION_CONFLICT

    contract = models.ContractVersion(
        identity="contract:v2",
        task_id="task:1",
        sequence=2,
        content_digest="4" * 64,
        display_text="same contract display",
    )
    other_contract_identity = models.ContractVersion(
        identity="contract:v1",
        task_id="task:1",
        sequence=1,
        content_digest="3" * 64,
        display_text="same contract display",
    )
    contract_command = _command(
        enums,
        models,
        "AWAITING_PLAN_APPROVAL",
        "APPROVE_PLAN",
        key="contract-version:conflict",
        current_contract_version=contract,
        expected_contract_identity=other_contract_identity.identity,
    )
    contract_result = state_machine.StateMachine.transition(contract_command)
    assert contract_result.permitted is False
    assert contract_result.reason is enums.TransitionReason.EXPECTED_VERSION_CONFLICT


def _assert_idempotency_contract() -> None:
    enums, models, state_machine = _load_wp05_api()
    command = _command(enums, models, "DRAFT", "SUBMIT_TASK", key="idem:1", digest="1" * 64)
    first = state_machine.StateMachine.transition(command)
    assert first.permitted is True
    assert first.idempotency_status is enums.IdempotencyStatus.NEW
    assert first.idempotency_record is not None

    replay_command = _command(
        enums,
        models,
        "DRAFT",
        "SUBMIT_TASK",
        key="idem:1",
        digest="1" * 64,
        prior_idempotency=first.idempotency_record,
    )
    replay = state_machine.StateMachine.transition(replay_command)
    assert replay.permitted is True
    assert replay.target is first.target
    assert replay.should_apply is False
    assert replay.idempotency_status is enums.IdempotencyStatus.REPLAYED

    conflict_command = _command(
        enums,
        models,
        "DRAFT",
        "SUBMIT_TASK",
        key="idem:1",
        digest="2" * 64,
        prior_idempotency=first.idempotency_record,
    )
    conflict = state_machine.StateMachine.transition(conflict_command)
    assert conflict.permitted is False
    assert conflict.reason is enums.TransitionReason.IDEMPOTENCY_CONFLICT
    assert conflict.idempotency_status is enums.IdempotencyStatus.CONFLICT


def _assert_uncertain_effect_recovers() -> None:
    enums, _, result = _transition(
        "APPLYING",
        "APPLY_FAILED",
        key="uncertain:1",
        uncertain_file_effect=True,
    )
    assert result.permitted is True
    assert result.target is enums.TaskState.RECOVERY_REQUIRED
    assert result.reason is enums.TransitionReason.UNCERTAIN_EFFECT_RECOVERY
    assert result.agent_loop_resume_permitted is False
    assert result.lease_acquisition_required is False
    assert result.changed is True

    _, _, repeated = _transition(
        "RECOVERY_REQUIRED",
        "ROLLBACK_RECOVERY_REQUIRED",
        key="uncertain:already-recovering",
        uncertain_file_effect=True,
    )
    assert repeated.permitted is True
    assert repeated.target is enums.TaskState.RECOVERY_REQUIRED
    assert repeated.reason is enums.TransitionReason.RECOVERY_ALREADY_REQUIRED
    assert repeated.changed is False
    assert repeated.should_apply is False


def _assert_restart_is_reentrant() -> None:
    enums, models, state_machine = _load_wp05_api()
    command = _command(enums, models, "READY_TO_EXECUTE", "CONTINUE_EXECUTION")
    before_restart = state_machine.StateMachine().transition(command)
    after_restart = state_machine.StateMachine().transition(command)
    assert before_restart == after_restart
    assert not vars(state_machine.StateMachine())


def _assert_provider_unlock_is_explicit() -> None:
    enums, models, state_machine = _load_wp05_api()
    wrong_trigger = _command(
        enums,
        models,
        "AWAITING_PROVIDER_UNLOCK",
        "CONTINUE_EXECUTION",
        key="provider:auto",
    )
    denied = state_machine.StateMachine.transition(wrong_trigger)
    assert denied.permitted is False

    locked = _command(
        enums,
        models,
        "AWAITING_PROVIDER_UNLOCK",
        "CONTINUE_PROVIDER_UNLOCK",
        key="provider:locked",
        preconditions=_preconditions(models, provider_unlocked=False),
    )
    assert state_machine.StateMachine.transition(locked).permitted is False
    _, _, continued = _transition(
        "AWAITING_PROVIDER_UNLOCK",
        "CONTINUE_PROVIDER_UNLOCK",
        key="provider:continued",
    )
    assert continued.target is enums.TaskState.EXECUTING
    assert continued.lease_acquisition_required is True


def _assert_versions_have_persistent_identity() -> None:
    _, models, _ = _load_wp05_api()
    left = models.ContractVersion(
        identity="contract:left",
        task_id="task:1",
        sequence=1,
        content_digest="a" * 64,
        display_text="identical display",
    )
    right = models.ContractVersion(
        identity="contract:right",
        task_id="task:1",
        sequence=1,
        content_digest="a" * 64,
        display_text="identical display",
    )
    assert left != right
    assert left.identity != right.identity
    same_identity = models.ContractVersion(
        identity=left.identity,
        task_id="task:1",
        sequence=99,
        content_digest="f" * 64,
        display_text="different display",
    )
    assert left == same_identity
    with pytest.raises((AttributeError, TypeError)):
        left.identity = "contract:mutated"


def _assert_txn_completed_only_after_verified_writeback() -> None:
    enums, models, state_machine = _load_wp05_api()
    denied = _command(
        enums,
        models,
        "APPLYING",
        "APPLY_SUCCEEDED",
        key="apply:not-verified",
        preconditions=_preconditions(models, writeback_verified=False),
    )
    assert state_machine.StateMachine.transition(denied).permitted is False
    _, _, completed = _transition("APPLYING", "APPLY_SUCCEEDED", key="apply:verified")
    assert completed.target is enums.TaskState.COMPLETED


def _assert_txn_rejection_is_not_applied() -> None:
    enums, _, result = _transition("READY_TO_APPLY", "REJECT_APPLY")
    assert result.target is enums.TaskState.NOT_APPLIED
    assert result.target is not enums.TaskState.COMPLETED


def _assert_changes_cannot_bypass_apply_gate() -> None:
    enums, models, state_machine = _load_wp05_api()
    command = _command(
        enums,
        models,
        "READY_TO_APPLY",
        "CONFIRM_APPLY",
        preconditions=_preconditions(models, changeset_ready=False),
    )
    denied = state_machine.StateMachine.transition(command)
    assert denied.permitted is False
    assert denied.target is enums.TaskState.READY_TO_APPLY
    assert denied.should_apply is False


def test_task_state_closed() -> None:
    _assert_task_state_closed()


def test_allowed_transition_matrix() -> None:
    _assert_allowed_transition_matrix()


def test_illegal_transition_fails_closed() -> None:
    _assert_illegal_transition_fails_closed()
    _assert_blocked_and_failure_guards()


def test_clarification_pauses() -> None:
    _assert_clarification_pauses()


def test_continue_acquires_lease() -> None:
    _assert_continue_requires_lease()


def test_terminal_rejects_effect() -> None:
    _assert_terminal_rejects_effect()
    _assert_cancel_guards()


def test_expected_state_conflict() -> None:
    _assert_expected_state_and_version_conflicts()


def test_idempotency_digest_conflict() -> None:
    _assert_idempotency_contract()


def test_uncertain_effect_recovers() -> None:
    _assert_uncertain_effect_recovers()


@pytest.mark.parametrize("pv_id", WP05_OWNER_PVS, ids=WP05_OWNER_PVS)
def test_spec_requirement(pv_id: str) -> None:
    assertions: dict[str, Callable[[], None]] = {
        "PV-AGT-003": _assert_illegal_transition_fails_closed,
        "PV-AGT-004": _assert_restart_is_reentrant,
        "PV-AGT-005": _assert_provider_unlock_is_explicit,
        "PV-PST-004": _assert_versions_have_persistent_identity,
        "PV-PST-005": _assert_idempotency_contract,
        "PV-PST-006": _assert_expected_state_and_version_conflicts,
        "PV-TXN-001": _assert_txn_completed_only_after_verified_writeback,
        "PV-TXN-002": _assert_txn_rejection_is_not_applied,
        "PV-TXN-003": _assert_changes_cannot_bypass_apply_gate,
        "PV-TXN-004": _assert_uncertain_effect_recovers,
    }
    assertions[pv_id]()
