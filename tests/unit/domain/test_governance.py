from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace

import pytest


APPROVAL_TYPES = (
    "PLAN_APPROVAL",
    "ACTION_APPROVAL",
    "BUDGET_APPROVAL",
    "APPLY_APPROVAL",
)

BUDGET_DIMENSIONS = (
    "AGENT_ROUNDS",
    "LLM_CALLS",
    "TOOL_CALLS",
    "MODIFIED_FILES",
    "CHANGESET_BYTES",
    "COMMANDS",
    "ELAPSED_SECONDS",
    "OUTPUT_BYTES",
)

WP07_OWNER_PVS = (
    "PV-ACT-012",
    "PV-POL-008",
    "PV-POL-009",
    "PV-POL-010",
    "PV-POL-011",
    "PV-POL-012",
    "PV-POL-013",
    "PV-POL-014",
    "PV-POL-015",
    "PV-POL-016",
    "PV-POL-017",
    "PV-POL-018",
    "PV-POL-019",
    "PV-POL-020",
    "PV-POL-021",
    "PV-POL-022",
    "PV-POL-023",
    "PV-POL-024",
)


def _load_wp07_api():
    try:
        approvals = importlib.import_module("coding_harness.domain.approvals")
        budgets = importlib.import_module("coding_harness.domain.budgets")
        governance = importlib.import_module("coding_harness.application.governance")
        models = importlib.import_module("coding_harness.domain.models")
        enums = importlib.import_module("coding_harness.domain.enums")
        policy = importlib.import_module("coding_harness.domain.policy")
        stopping = importlib.import_module("coding_harness.agent.stopping")
    except ModuleNotFoundError:
        pytest.fail("WP-07 API unavailable", pytrace=False)
    return approvals, budgets, governance, models, enums, policy, stopping


def _plan(models, *, identity: str = "plan:1", display_text: str = "Plan"):
    return models.PlanVersion(
        identity=identity,
        task_id="task:1",
        sequence=1,
        content_digest="1" * 64,
        display_text=display_text,
    )


def _contract(
    models,
    *,
    identity: str = "contract:1",
    display_text: str = "Contract",
):
    return models.ContractVersion(
        identity=identity,
        task_id="task:1",
        sequence=1,
        content_digest="2" * 64,
        display_text=display_text,
    )


def _limits(budgets, *, soft_value: int = 10, hard_value: int = 20):
    soft_limits = {
        budgets.BudgetDimension[name]: soft_value for name in BUDGET_DIMENSIONS
    }
    hard_limits = {
        budgets.BudgetDimension[name]: hard_value for name in BUDGET_DIMENSIONS
    }
    return budgets.RunLimits(
        soft_limits=soft_limits,
        hard_limits=hard_limits,
        repeated_failure_limit=3,
        no_progress_limit=3,
    )


def _budget_version(
    budgets,
    *,
    identity: str = "budget:1",
    sequence: int = 1,
    limits=None,
    display_text: str = "Budget",
):
    return budgets.BudgetVersion(
        identity=identity,
        task_id="task:1",
        sequence=sequence,
        limits=limits if limits is not None else _limits(budgets),
        display_text=display_text,
    )


def _approval(
    approvals,
    models,
    enums,
    policy,
    *,
    approval_type: str = "PLAN_APPROVAL",
    identity: str = "approval:1",
    consumed: bool = False,
    consumed_at: int | None = None,
    revoked: bool = False,
    revoked_at: int | None = None,
    expires_at: int = 200,
    **overrides: object,
):
    approval_kind = approvals.ApprovalType[approval_type]
    expected_states = {
        "PLAN_APPROVAL": enums.TaskState.AWAITING_PLAN_APPROVAL,
        "ACTION_APPROVAL": enums.TaskState.AWAITING_ACTION_APPROVAL,
        "BUDGET_APPROVAL": enums.TaskState.AWAITING_BUDGET_APPROVAL,
        "APPLY_APPROVAL": enums.TaskState.READY_TO_APPLY,
    }
    values = {
        "identity": identity,
        "revision": 1,
        "display_text": "User-visible approval",
        "approval_type": approval_kind,
        "task_id": "task:1",
        "target_identity": "plan:1",
        "expected_state": expected_states[approval_type],
        "plan_version": _plan(models),
        "contract_version": _contract(models),
        "request_digest": "3" * 64,
        "policy_record_identity": "policy-record:1",
        "policy_record_digest": "0" * 64,
        "reason_code": "APPROVAL_REQUIRED",
        "created_at": 100,
        "expires_at": expires_at,
        "consumed": consumed,
        "consumed_at": consumed_at,
        "revoked": revoked,
        "revoked_at": revoked_at,
        "idempotency_key": "approval:key:1",
        "scope_digest": "4" * 64,
        "action_kind": None,
        "action_id": None,
        "normalized_paths": (),
        "expected_content_digest": None,
        "baseline_manifest_digest": None,
        "action_payload_digest": None,
        "action_reason": None,
        "ignored_entries": (),
        "ignored_input_mode": None,
        "allowed_stages": (),
        "sandbox_manifest_identity": None,
        "exportable_to_llm": False,
        "changeset_digest": None,
        "budget_version_identity": None,
        "affected_dimensions": (),
        "current_usage": (),
        "old_limits": (),
        "new_limits": (),
        "hard_limits": (),
        "extension_reason": None,
    }
    values.update(overrides)
    record = _policy_record_from_values(policy, values)
    values["policy_record_digest"] = approvals.policy_record_digest(record)
    return approvals.Approval(**values)


def _policy_record_from_values(
    policy,
    values: dict[str, object],
    *,
    decision: str = "REQUIRE_APPROVAL",
    reason: str | None = None,
    **overrides: object,
):
    selected = policy.PolicyDecision[decision]
    selected_reason = reason or {
        "REQUIRE_APPROVAL": "APPROVAL_REQUIRED",
        "ALLOW": "ALLOWED",
        "DENY": "DENIED_CAPABILITY",
        "BLOCKED_POLICY_ERROR": "BLOCKED_POLICY_ERROR",
    }[decision]
    record_values = {
        "decision": selected,
        "reason": policy.PolicyReason[selected_reason],
        "detail": "trusted policy result",
        "error_code": (
            policy.PolicyErrorCode.INVALID_POLICY_CONTEXT
            if decision == "BLOCKED_POLICY_ERROR"
            else None
        ),
        "action_identity": values["target_identity"],
        "action_digest": values["request_digest"],
        "tool_execution_permitted": decision == "ALLOW",
        "approval_can_override": decision == "REQUIRE_APPROVAL",
        "effective_profile": "trusted-profile",
        "bound_task_id": values["task_id"],
        "bound_target_type": values["approval_type"].value,
        "bound_target_identity": values["target_identity"],
        "bound_digest": values["request_digest"],
        "bound_expected_state": values["expected_state"],
        "bound_idempotency_key": values["idempotency_key"],
    }
    record_values.update(overrides)
    return policy.PolicyDecisionRecord(**record_values)


def _trusted_policy_for(
    approval,
    policy,
    *,
    decision: str = "REQUIRE_APPROVAL",
    reason: str | None = None,
    **overrides: object,
):
    values = {
        "approval_type": approval.approval_type,
        "task_id": approval.task_id,
        "target_identity": approval.target_identity,
        "request_digest": approval.request_digest,
        "expected_state": approval.expected_state,
        "idempotency_key": approval.idempotency_key,
    }
    return _policy_record_from_values(
        policy,
        values,
        decision=decision,
        reason=reason,
        **overrides,
    )


def _context_for(approvals, approval, **overrides: object):
    values = {
        "approval_type": approval.approval_type,
        "task_id": approval.task_id,
        "target_identity": approval.target_identity,
        "expected_state": approval.expected_state,
        "plan_version_identity": approval.plan_version.identity,
        "contract_version_identity": (
            approval.contract_version.identity
            if approval.contract_version is not None
            else None
        ),
        "request_digest": approval.request_digest,
        "policy_record_identity": approval.policy_record_identity,
        "policy_record_digest": approval.policy_record_digest,
        "reason_code": approval.reason_code,
        "idempotency_key": approval.idempotency_key,
        "scope_digest": approval.scope_digest,
        "action_kind": approval.action_kind,
        "action_id": approval.action_id,
        "normalized_paths": approval.normalized_paths,
        "expected_content_digest": approval.expected_content_digest,
        "baseline_manifest_digest": approval.baseline_manifest_digest,
        "action_payload_digest": approval.action_payload_digest,
        "action_reason": approval.action_reason,
        "ignored_entries": approval.ignored_entries,
        "ignored_input_mode": approval.ignored_input_mode,
        "allowed_stages": approval.allowed_stages,
        "sandbox_manifest_identity": approval.sandbox_manifest_identity,
        "exportable_to_llm": approval.exportable_to_llm,
        "changeset_digest": approval.changeset_digest,
        "budget_version_identity": approval.budget_version_identity,
        "affected_dimensions": approval.affected_dimensions,
        "current_usage": approval.current_usage,
        "old_limits": approval.old_limits,
        "new_limits": approval.new_limits,
        "hard_limits": approval.hard_limits,
        "extension_reason": approval.extension_reason,
    }
    values.update(overrides)
    return approvals.ApprovalExecutionContext(**values)


def _validate(service, approval, policy, **overrides: object):
    values = {
        "approval": approval,
        "trusted_policy_record": _trusted_policy_for(approval, policy),
        "trusted_policy_record_identity": approval.policy_record_identity,
    }
    values.update(overrides)
    return service.validate_creation(**values)


def _consume(service, approval, *, now: int = 150, **overrides: object):
    approvals, _, _, _, _, policy, _ = _load_wp07_api()
    context_overrides: dict[str, object] = {}
    legacy_context_fields = {
        "requested_type": "approval_type",
        "task_id": "task_id",
        "expected_state": "expected_state",
        "request_digest": "request_digest",
        "target_identity": "target_identity",
        "idempotency_key": "idempotency_key",
    }
    for source, target in legacy_context_fields.items():
        if source in overrides:
            context_overrides[target] = overrides.pop(source)
    if "plan_version" in overrides:
        context_overrides["plan_version_identity"] = overrides.pop("plan_version").identity
    if "contract_version" in overrides:
        contract = overrides.pop("contract_version")
        context_overrides["contract_version_identity"] = (
            contract.identity if contract is not None else None
        )
    presented_identity = overrides.pop("expected_approval_identity", approval.identity)
    presented_revision = overrides.pop("presented_revision", approval.revision)
    values = {
        "current_record": approval,
        "expected_revision": approval.revision,
        "presented_reference": approvals.PresentedApprovalReference(
            identity=presented_identity,
            revision=presented_revision,
        ),
        "current_context": _context_for(approvals, approval, **context_overrides),
        "trusted_policy_record": _trusted_policy_for(approval, policy),
        "trusted_policy_record_identity": approval.policy_record_identity,
        "now": now,
    }
    values.update(overrides)
    return service.consume(**values)


def _assert_conflict(result) -> None:
    assert result.permitted is False
    assert result.conflict is True
    assert result.side_effect_permitted is False


def _assert_plan_binding() -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    service = governance.ApprovalService()
    approval = _approval(approvals, models, enums, policy)

    same_text_different_identity = _plan(
        models,
        identity="plan:2",
        display_text=approval.plan_version.display_text,
    )
    mismatch = _consume(service, approval, plan_version=same_text_different_identity)
    _assert_conflict(mismatch)
    same_text_different_approval = replace(approval, identity="approval:2")
    assert same_text_different_approval.display_text == approval.display_text
    assert same_text_different_approval != approval
    identity_mismatch = _consume(
        service,
        approval,
        expected_approval_identity=same_text_different_approval.identity,
    )
    _assert_conflict(identity_mismatch)

    result = _consume(service, approval)
    assert result.permitted is True
    assert result.side_effect_permitted is True
    assert result.approval.consumed is True
    assert result.approval.consumed_at == 150
    assert result.approval.plan_version.identity == "plan:1"
    assert result.approval.contract_version.identity == "contract:1"


def _assert_authorization_types_distinct() -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    assert tuple(item.name for item in approvals.ApprovalType) == APPROVAL_TYPES
    assert len(approvals.ApprovalType.__members__) == 4
    service = governance.ApprovalService()
    approval = _approval(approvals, models, enums, policy)
    wrong = _consume(
        service,
        approval,
        requested_type=approvals.ApprovalType.ACTION_APPROVAL,
    )
    _assert_conflict(wrong)
    with pytest.raises(ValueError):
        replace(approval, approval_type="PLAN_APPROVAL")


def _delete_approval(approvals, models, enums, policy):
    return _approval(
        approvals,
        models,
        enums,
        policy,
        approval_type="ACTION_APPROVAL",
        identity="approval:delete:1",
        target_identity="action:delete:1",
        contract_version=None,
        action_kind="delete_file",
        action_id="action:delete:1",
        normalized_paths=("src/obsolete.py",),
        expected_content_digest="5" * 64,
        baseline_manifest_digest="6" * 64,
        action_payload_digest="7" * 64,
        request_digest="7" * 64,
        action_reason="remove obsolete file",
    )


def _ignored_approval(approvals, models, enums, policy):
    return _approval(
        approvals,
        models,
        enums,
        policy,
        approval_type="ACTION_APPROVAL",
        identity="approval:ignored:1",
        target_identity="action:ignored:1",
        contract_version=None,
        action_kind="include_ignored_input",
        action_id="action:ignored:1",
        normalized_paths=("fixtures/input.dat",),
        action_payload_digest="8" * 64,
        request_digest="8" * 64,
        ignored_entries=(("fixtures/input.dat", "regular", 12, "9" * 64),),
        ignored_input_mode="read_only_input",
        allowed_stages=("EXECUTING",),
        sandbox_manifest_identity="sandbox-input:1",
        exportable_to_llm=False,
    )


def _assert_delete_zero_effect() -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    service = governance.ApprovalService()
    approval = _delete_approval(approvals, models, enums, policy)
    pending = _validate(service, approval, policy)
    assert pending.permitted is True
    assert pending.side_effect_permitted is False
    assert approval.consumed is False
    consumed = _consume(service, approval)
    assert consumed.side_effect_permitted is True


def _assert_ignored_zero_effect() -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    service = governance.ApprovalService()
    approval = _ignored_approval(approvals, models, enums, policy)
    pending = _validate(service, approval, policy)
    assert pending.permitted is True
    assert pending.side_effect_permitted is False
    assert approval.exportable_to_llm is False
    assert approval.ignored_entries == (
        ("fixtures/input.dat", "regular", 12, "9" * 64),
    )


def _assert_payload_change_invalidates() -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    service = governance.ApprovalService()
    approval = _delete_approval(approvals, models, enums, policy)
    changed = _consume(service, approval, request_digest="a" * 64)
    _assert_conflict(changed)


def _assert_consume_once() -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    service = governance.ApprovalService()
    approval = _delete_approval(approvals, models, enums, policy)
    first = _consume(service, approval)
    assert first.permitted is True
    second = _consume(service, first.approval)
    _assert_conflict(second)


def _assert_budget_dimensions() -> None:
    _, budgets, _, _, _, _, stopping = _load_wp07_api()
    assert tuple(item.name for item in budgets.BudgetDimension) == BUDGET_DIMENSIONS
    assert len(budgets.BudgetDimension.__members__) == 8
    assert budgets.RunLimits is not stopping.StopLimits
    assert not issubclass(budgets.RunLimits, stopping.StopLimits)
    limits = _limits(budgets)
    assert frozenset(limits.soft_limits) == frozenset(budgets.BudgetDimension)
    assert frozenset(limits.hard_limits) == frozenset(budgets.BudgetDimension)


def _assert_soft_limit_reapproval() -> None:
    _, budgets, _, _, _, _, _ = _load_wp07_api()
    version = _budget_version(budgets)
    usage = {dimension: 0 for dimension in budgets.BudgetDimension}
    usage[budgets.BudgetDimension.TOOL_CALLS] = 9
    cost = {budgets.BudgetDimension.TOOL_CALLS: 1}
    result = budgets.check_before_effect(
        budget_version=version,
        expected_budget_identity=version.identity,
        usage=usage,
        proposed_cost=cost,
    )
    assert result.decision is budgets.BudgetDecision.REQUIRE_APPROVAL
    assert result.side_effect_permitted is False
    assert result.dimension is budgets.BudgetDimension.TOOL_CALLS
    assert result.budget_version_identity == version.identity


def _assert_hard_limit_fixed() -> None:
    approvals, budgets, governance, models, enums, policy, _ = _load_wp07_api()
    version = _budget_version(budgets)
    usage = {dimension: 0 for dimension in budgets.BudgetDimension}
    usage[budgets.BudgetDimension.OUTPUT_BYTES] = 19
    result = budgets.check_before_effect(
        budget_version=version,
        expected_budget_identity=version.identity,
        usage=usage,
        proposed_cost={budgets.BudgetDimension.OUTPUT_BYTES: 1},
    )
    assert result.decision is budgets.BudgetDecision.HARD_LIMIT_REACHED
    assert result.side_effect_permitted is False

    approval = _approval(
        approvals,
        models,
        enums,
        policy,
        approval_type="BUDGET_APPROVAL",
        target_identity="budget:2",
        contract_version=None,
        budget_version_identity="budget:1",
        affected_dimensions=(budgets.BudgetDimension.OUTPUT_BYTES,),
        current_usage=((budgets.BudgetDimension.OUTPUT_BYTES, 19),),
        old_limits=((budgets.BudgetDimension.OUTPUT_BYTES, 10),),
        new_limits=((budgets.BudgetDimension.OUTPUT_BYTES, 30),),
        hard_limits=((budgets.BudgetDimension.OUTPUT_BYTES, 20),),
        extension_reason="more output",
    )
    raised_hard = _validate(
        governance.ApprovalService(),
        approval,
        policy,
    )
    assert raised_hard.permitted is False
    assert raised_hard.side_effect_permitted is False


def _assert_budget_before_effect() -> None:
    _, budgets, _, _, _, _, _ = _load_wp07_api()
    version = _budget_version(budgets)
    usage = {dimension: 0 for dimension in budgets.BudgetDimension}
    usage[budgets.BudgetDimension.COMMANDS] = 20
    before = dict(usage)
    result = budgets.check_before_effect(
        budget_version=version,
        expected_budget_identity=version.identity,
        usage=usage,
        proposed_cost={budgets.BudgetDimension.COMMANDS: 1},
    )
    assert result.checked_before_effect is True
    assert result.side_effect_permitted is False
    assert usage == before
    assert result.usage_before == 20
    assert result.proposed_usage == 21


def _assert_policy_cannot_be_overridden() -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    service = governance.ApprovalService()
    approval = _approval(approvals, models, enums, policy)
    for decision in (
        "DENY",
        "BLOCKED_POLICY_ERROR",
        "ALLOW",
    ):
        trusted = _trusted_policy_for(approval, policy, decision=decision)
        result = _validate(
            service,
            approval,
            policy,
            trusted_policy_record=trusted,
        )
        assert result.permitted is False
        assert result.side_effect_permitted is False

    result = _validate(service, approval, policy)
    assert result.permitted is True
    assert result.side_effect_permitted is False


def _assert_budget_activation_requires_commit() -> None:
    approvals, budgets, governance, models, enums, policy, _ = _load_wp07_api()
    service = governance.ApprovalService()
    current = _budget_version(budgets)
    proposed = _budget_version(
        budgets,
        identity="budget:2",
        sequence=2,
        limits=_limits(budgets, soft_value=15, hard_value=20),
        display_text=current.display_text,
    )
    approval = _approval(
        approvals,
        models,
        enums,
        policy,
        approval_type="BUDGET_APPROVAL",
        target_identity=proposed.identity,
        contract_version=None,
        budget_version_identity=current.identity,
        affected_dimensions=(budgets.BudgetDimension.TOOL_CALLS,),
        current_usage=((budgets.BudgetDimension.TOOL_CALLS, 9),),
        old_limits=((budgets.BudgetDimension.TOOL_CALLS, 10),),
        new_limits=((budgets.BudgetDimension.TOOL_CALLS, 15),),
        hard_limits=((budgets.BudgetDimension.TOOL_CALLS, 20),),
        extension_reason="additional validation",
    )
    pending = service.activate_budget(
        current=current,
        proposed=proposed,
        current_record=approval,
        expected_revision=approval.revision,
        presented_reference=approvals.PresentedApprovalReference(
            approval.identity,
            approval.revision,
        ),
        current_context=_context_for(approvals, approval),
        trusted_policy_record=_trusted_policy_for(approval, policy),
        trusted_policy_record_identity=approval.policy_record_identity,
        approval_transaction_committed=False,
    )
    assert pending.active_version.identity == current.identity
    assert pending.changed is False
    assert proposed.display_text == current.display_text
    assert proposed != current
    with pytest.raises((FrozenInstanceError, AttributeError)):
        proposed.identity = "budget:forged"

    committed = service.activate_budget(
        current=current,
        proposed=proposed,
        current_record=approval,
        expected_revision=approval.revision,
        presented_reference=approvals.PresentedApprovalReference(
            approval.identity,
            approval.revision,
        ),
        current_context=_context_for(approvals, approval),
        trusted_policy_record=_trusted_policy_for(approval, policy),
        trusted_policy_record_identity=approval.policy_record_identity,
        approval_transaction_committed=True,
        committed_at=150,
    )
    assert committed.active_version.identity == proposed.identity
    assert committed.changed is True
    assert committed.approval.consumed is True


def _assert_stopping_thresholds() -> None:
    _, budgets, _, _, _, _, _ = _load_wp07_api()
    limits = _limits(budgets)
    repeated = limits.evaluate_stop(repeated_failures=3, no_progress_count=0)
    assert repeated.should_stop is True
    assert repeated.reason == "REPEATED_FAILURE_LIMIT"
    no_progress = limits.evaluate_stop(repeated_failures=0, no_progress_count=3)
    assert no_progress.should_stop is True
    assert no_progress.reason == "NO_PROGRESS_LIMIT"


def _assert_action_set_closed() -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    service = governance.ApprovalService()
    allowed = {
        _delete_approval(approvals, models, enums, policy).action_kind,
        _ignored_approval(approvals, models, enums, policy).action_kind,
    }
    assert allowed == {"delete_file", "include_ignored_input"}
    forged = _approval(
        approvals,
        models,
        enums,
        policy,
        approval_type="ACTION_APPROVAL",
        action_kind="replace_file",
        action_id="action:replace:1",
        target_identity="action:replace:1",
        contract_version=None,
    )
    result = _validate(service, forged, policy)
    assert result.permitted is False
    assert result.side_effect_permitted is False


def test_plan_binding() -> None:
    _assert_plan_binding()


@pytest.mark.parametrize(
    ("source_type", "requested_type"),
    (
        ("PLAN_APPROVAL", "ACTION_APPROVAL"),
        ("ACTION_APPROVAL", "BUDGET_APPROVAL"),
        ("BUDGET_APPROVAL", "APPLY_APPROVAL"),
        ("APPLY_APPROVAL", "PLAN_APPROVAL"),
    ),
    ids=("plan-as-action", "action-as-budget", "budget-as-apply", "apply-as-plan"),
)
def test_authorization_types_distinct(source_type: str, requested_type: str) -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    service = governance.ApprovalService()
    approval = _approval(
        approvals,
        models,
        enums,
        policy,
        approval_type=source_type,
    )
    result = _consume(
        service,
        approval,
        requested_type=approvals.ApprovalType[requested_type],
    )
    _assert_conflict(result)


def test_delete_zero_effect() -> None:
    _assert_delete_zero_effect()


def test_ignored_zero_effect() -> None:
    _assert_ignored_zero_effect()


@pytest.mark.parametrize(
    "changed_field",
    ("state", "plan", "contract", "digest"),
    ids=("state", "plan-version", "contract-version", "request-digest"),
)
def test_payload_change_invalidates(changed_field: str) -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    service = governance.ApprovalService()
    approval = _approval(approvals, models, enums, policy)
    overrides: dict[str, object] = {}
    if changed_field == "state":
        overrides["expected_state"] = enums.TaskState.READY_TO_EXECUTE
    elif changed_field == "plan":
        overrides["plan_version"] = _plan(models, identity="plan:changed")
    elif changed_field == "contract":
        overrides["contract_version"] = _contract(
            models,
            identity="contract:changed",
        )
    else:
        overrides["request_digest"] = "a" * 64
    _assert_conflict(_consume(service, approval, **overrides))


@pytest.mark.parametrize(
    "invalid_status",
    ("consumed", "revoked", "expired"),
    ids=("already-consumed", "revoked", "expired"),
)
def test_consume_once(invalid_status: str) -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    service = governance.ApprovalService()
    approval = _delete_approval(approvals, models, enums, policy)
    if invalid_status == "consumed":
        first = _consume(service, approval)
        assert first.permitted is True
        candidate = first.approval
        now = 151
    elif invalid_status == "revoked":
        candidate = replace(approval, revoked=True, revoked_at=120)
        now = 150
    else:
        candidate = approval
        now = approval.expires_at
    _assert_conflict(_consume(service, candidate, now=now))


@pytest.mark.parametrize("dimension_name", BUDGET_DIMENSIONS, ids=BUDGET_DIMENSIONS)
def test_budget_dimensions(dimension_name: str) -> None:
    _, budgets, _, _, _, _, stopping = _load_wp07_api()
    assert tuple(item.name for item in budgets.BudgetDimension) == BUDGET_DIMENSIONS
    assert budgets.BudgetDimension[dimension_name].value == dimension_name
    assert budgets.RunLimits is not stopping.StopLimits
    version = _budget_version(budgets)
    invalid = budgets.check_before_effect(
        budget_version=version,
        expected_budget_identity=version.identity,
        usage={"UNKNOWN_DIMENSION": 0},
        proposed_cost={budgets.BudgetDimension[dimension_name]: 1},
    )
    assert invalid.decision is budgets.BudgetDecision.INVALID
    assert invalid.side_effect_permitted is False
    with pytest.raises(ValueError):
        _limits(budgets, soft_value=-1)


def test_soft_limit_reapproval() -> None:
    _assert_soft_limit_reapproval()


def test_hard_limit_fixed() -> None:
    _assert_hard_limit_fixed()


def test_budget_before_effect() -> None:
    _assert_budget_before_effect()


@pytest.mark.parametrize(
    "trusted_decision",
    ("DENY", "BLOCKED_POLICY_ERROR", "ALLOW"),
    ids=("trusted-deny", "trusted-policy-error", "trusted-allow"),
)
def test_policy_authority_rejects_forged_approval_requirement(
    trusted_decision: str,
) -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    approval = _approval(approvals, models, enums, policy)
    trusted = _trusted_policy_for(approval, policy, decision=trusted_decision)

    result = _validate(
        governance.ApprovalService(),
        approval,
        policy,
        trusted_policy_record=trusted,
    )

    assert result.permitted is False
    assert result.side_effect_permitted is False


def test_policy_authority_rejects_reason_mismatch() -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    approval = replace(
        _approval(approvals, models, enums, policy),
        reason_code="DENIED_CAPABILITY",
    )

    result = _validate(governance.ApprovalService(), approval, policy)

    assert result.permitted is False
    assert result.side_effect_permitted is False


@pytest.mark.parametrize(
    "digest_field",
    ("action_digest", "bound_digest"),
    ids=("policy-action-digest", "policy-bound-digest"),
)
def test_policy_authority_rejects_digest_mismatch(digest_field: str) -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    approval = _approval(approvals, models, enums, policy)
    trusted = _trusted_policy_for(
        approval,
        policy,
        **{digest_field: "f" * 64},
    )

    result = _validate(
        governance.ApprovalService(),
        approval,
        policy,
        trusted_policy_record=trusted,
    )

    assert result.permitted is False
    assert result.side_effect_permitted is False


def _budget_approval(approvals, budgets, models, enums, policy):
    return _approval(
        approvals,
        models,
        enums,
        policy,
        approval_type="BUDGET_APPROVAL",
        target_identity="budget:2",
        contract_version=None,
        budget_version_identity="budget:1",
        affected_dimensions=(budgets.BudgetDimension.TOOL_CALLS,),
        current_usage=((budgets.BudgetDimension.TOOL_CALLS, 9),),
        old_limits=((budgets.BudgetDimension.TOOL_CALLS, 10),),
        new_limits=((budgets.BudgetDimension.TOOL_CALLS, 15),),
        hard_limits=((budgets.BudgetDimension.TOOL_CALLS, 20),),
        extension_reason="additional validation",
    )


def _apply_approval(approvals, models, enums, policy):
    return _approval(
        approvals,
        models,
        enums,
        policy,
        approval_type="APPLY_APPROVAL",
        target_identity="a" * 64,
        changeset_digest="a" * 64,
        baseline_manifest_digest="b" * 64,
    )


@pytest.mark.parametrize(
    ("approval_kind", "field", "changed_value"),
    (
        ("delete", "normalized_paths", ("src/different.py",)),
        ("delete", "action_payload_digest", "a" * 64),
        ("delete", "expected_content_digest", "b" * 64),
        ("delete", "baseline_manifest_digest", "c" * 64),
        (
            "ignored",
            "ignored_entries",
            (("fixtures/other.dat", "regular", 12, "9" * 64),),
        ),
        ("ignored", "sandbox_manifest_identity", "sandbox-input:2"),
        ("plan", "scope_digest", "d" * 64),
        ("apply", "changeset_digest", "d" * 64),
        ("apply", "baseline_manifest_digest", "d" * 64),
        ("budget", "budget_version_identity", "budget:changed"),
        ("budget", "current_usage", ()),
        ("budget", "new_limits", ()),
    ),
    ids=(
        "delete-path",
        "action-payload-digest",
        "delete-expected-digest",
        "delete-baseline",
        "ignored-input-list",
        "ignored-manifest",
        "plan-scope",
        "apply-changeset",
        "apply-baseline",
        "budget-version",
        "budget-current-usage",
        "budget-new-limits",
    ),
)
def test_type_specific_binding_drift_is_rejected(
    approval_kind: str,
    field: str,
    changed_value: object,
) -> None:
    approvals, budgets, governance, models, enums, policy, _ = _load_wp07_api()
    candidates = {
        "delete": lambda: _delete_approval(approvals, models, enums, policy),
        "ignored": lambda: _ignored_approval(approvals, models, enums, policy),
        "plan": lambda: _approval(approvals, models, enums, policy),
        "apply": lambda: _apply_approval(approvals, models, enums, policy),
        "budget": lambda: _budget_approval(
            approvals,
            budgets,
            models,
            enums,
            policy,
        ),
    }
    current_record = candidates[approval_kind]()
    current_context = _context_for(
        approvals,
        current_record,
        **{field: changed_value},
    )

    result = _consume(
        governance.ApprovalService(),
        current_record,
        current_context=current_context,
    )

    _assert_conflict(result)


def test_presented_rebuilt_approval_cannot_replace_trusted_record() -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    current_record = _delete_approval(approvals, models, enums, policy)
    rebuilt = replace(
        current_record,
        display_text="rebuilt display",
        normalized_paths=("src/different.py",),
    )

    result = _consume(
        governance.ApprovalService(),
        current_record,
        presented_reference=rebuilt,
    )

    _assert_conflict(result)
    assert result.approval is current_record


def test_consumption_returns_revision_for_persistence_cas() -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    current_record = _delete_approval(approvals, models, enums, policy)

    first = _consume(governance.ApprovalService(), current_record)

    assert first.permitted is True
    assert first.previous_revision == 1
    assert first.expected_revision == 1
    assert first.new_revision == 2
    assert first.approval.revision == 2
    assert first.approval.consumed is True
    assert current_record.revision == 1
    assert current_record.consumed is False
    with pytest.raises((FrozenInstanceError, AttributeError)):
        current_record.revision = 2
    _assert_conflict(_consume(governance.ApprovalService(), first.approval))
    _assert_conflict(
        _consume(
            governance.ApprovalService(),
            current_record,
            expected_revision=0,
        )
    )


def test_parallel_pending_snapshots_expose_same_cas_precondition() -> None:
    approvals, _, governance, models, enums, policy, _ = _load_wp07_api()
    current_record = _delete_approval(approvals, models, enums, policy)
    service = governance.ApprovalService()

    first = _consume(service, current_record)
    concurrent = _consume(service, current_record)

    assert first.permitted is True
    assert concurrent.permitted is True
    assert (first.previous_revision, first.new_revision) == (1, 2)
    assert (concurrent.previous_revision, concurrent.new_revision) == (1, 2)
    assert current_record.consumed is False


INVALID_NUMERIC_VALUES = (
    pytest.param(True, id="bool"),
    pytest.param(1.5, id="float"),
    pytest.param(float("nan"), id="nan"),
    pytest.param(float("inf"), id="infinity"),
    pytest.param(-1, id="negative"),
)


@pytest.mark.parametrize("invalid_value", INVALID_NUMERIC_VALUES)
@pytest.mark.parametrize(
    "numeric_entry",
    ("soft-limit", "hard-limit", "usage", "proposed-cost", "sequence"),
)
def test_budget_numeric_inputs_fail_closed(
    invalid_value: object,
    numeric_entry: str,
) -> None:
    _, budgets, _, _, _, _, _ = _load_wp07_api()
    if numeric_entry in {"soft-limit", "hard-limit"}:
        soft = {dimension: 10 for dimension in budgets.BudgetDimension}
        hard = {dimension: 20 for dimension in budgets.BudgetDimension}
        target = soft if numeric_entry == "soft-limit" else hard
        target[budgets.BudgetDimension.TOOL_CALLS] = invalid_value
        with pytest.raises(ValueError):
            budgets.RunLimits(
                soft_limits=soft,
                hard_limits=hard,
                repeated_failure_limit=3,
                no_progress_limit=3,
            )
        return
    if numeric_entry == "sequence":
        with pytest.raises(ValueError):
            _budget_version(budgets, sequence=invalid_value)
        return
    version = _budget_version(budgets)
    usage = {dimension: 0 for dimension in budgets.BudgetDimension}
    cost: dict[object, object] = {budgets.BudgetDimension.TOOL_CALLS: 1}
    if numeric_entry == "usage":
        usage[budgets.BudgetDimension.TOOL_CALLS] = invalid_value
    else:
        cost[budgets.BudgetDimension.TOOL_CALLS] = invalid_value
    result = budgets.check_before_effect(
        budget_version=version,
        expected_budget_identity=version.identity,
        usage=usage,
        proposed_cost=cost,
    )
    assert result.decision is budgets.BudgetDecision.INVALID
    assert result.side_effect_permitted is False


def test_budget_below_limits_permits_effect_without_approval() -> None:
    _, budgets, _, _, _, _, _ = _load_wp07_api()
    version = _budget_version(budgets)
    usage = {dimension: 0 for dimension in budgets.BudgetDimension}
    before = dict(usage)

    result = budgets.check_before_effect(
        budget_version=version,
        expected_budget_identity=version.identity,
        usage=usage,
        proposed_cost={budgets.BudgetDimension.TOOL_CALLS: 1},
    )

    assert result.decision is budgets.BudgetDecision.ALLOW
    assert result.side_effect_permitted is True
    assert result.approval_required is False
    assert usage == before


@pytest.mark.parametrize("pv_id", WP07_OWNER_PVS, ids=WP07_OWNER_PVS)
def test_spec_requirement(pv_id: str) -> None:
    assertions: dict[str, Callable[[], None]] = {
        "PV-ACT-012": _assert_delete_zero_effect,
        "PV-POL-008": _assert_plan_binding,
        "PV-POL-009": _assert_consume_once,
        "PV-POL-010": _assert_payload_change_invalidates,
        "PV-POL-011": _assert_budget_dimensions,
        "PV-POL-012": _assert_hard_limit_fixed,
        "PV-POL-013": _assert_budget_before_effect,
        "PV-POL-014": _assert_stopping_thresholds,
        "PV-POL-015": _assert_action_set_closed,
        "PV-POL-016": _assert_delete_zero_effect,
        "PV-POL-017": _assert_payload_change_invalidates,
        "PV-POL-018": _assert_ignored_zero_effect,
        "PV-POL-019": _assert_ignored_zero_effect,
        "PV-POL-020": _assert_authorization_types_distinct,
        "PV-POL-021": _assert_budget_activation_requires_commit,
        "PV-POL-022": _assert_hard_limit_fixed,
        "PV-POL-023": _assert_budget_activation_requires_commit,
        "PV-POL-024": _assert_policy_cannot_be_overridden,
    }
    assertions[pv_id]()
