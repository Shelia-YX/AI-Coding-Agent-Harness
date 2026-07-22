from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace

import pytest


CONDITION_KINDS = ("MACHINE", "USER_CONFIRMATION")
CONDITION_KIND_VALUES = ("machine", "user_confirmation")
CONDITION_STATUSES = ("NOT_RUN", "PASSED", "FAILED", "BLOCKED")
WP08_OWNER_PVS = (
    "PV-ACC-001",
    "PV-ACC-002",
    "PV-ACC-003",
    "PV-ACC-004",
    "PV-ACC-005",
    "PV-ACC-006",
    "PV-ACC-007",
)


def _load_wp08_api():
    try:
        acceptance = importlib.import_module("coding_harness.domain.acceptance")
        models = importlib.import_module("coding_harness.domain.models")
    except ModuleNotFoundError:
        pytest.fail("WP-08 API unavailable", pytrace=False)
    return acceptance, models


def _version(
    models,
    *,
    identity: str = "contract:1",
    sequence: int = 1,
    display_text: str = "Acceptance Contract",
):
    return models.ContractVersion(
        identity=identity,
        task_id="task:1",
        sequence=sequence,
        content_digest=("1" if sequence == 1 else "2") * 64,
        display_text=display_text,
    )


def _condition(
    acceptance,
    *,
    identity: str = "condition:machine",
    kind: str = "MACHINE",
    required: bool = True,
    status: str = "NOT_RUN",
    contract_version_identity: str = "contract:1",
):
    is_machine = kind == "MACHINE"
    return acceptance.AcceptanceCondition(
        identity=identity,
        display_text="Observable condition",
        kind=acceptance.AcceptanceConditionKind[kind],
        required=required,
        status=acceptance.ConditionStatus[status],
        expected_contract_version_identity=contract_version_identity,
        expected_evidence_kind=(
            acceptance.MachineEvidenceKind.VALIDATION if is_machine else None
        ),
        expected_producer_identity="tool:pytest" if is_machine else None,
        expected_command_identity="validation:pytest" if is_machine else None,
        expected_input_digest="3" * 64 if is_machine else None,
        expected_baseline_manifest_digest="4" * 64 if is_machine else None,
        expected_changeset_digest="5" * 64 if is_machine else None,
    )


def _contract(
    acceptance,
    models,
    *,
    version=None,
    conditions=None,
    approved: bool = True,
    history=(),
):
    selected_version = version if version is not None else _version(models)
    selected = conditions
    if selected is None:
        selected = [
            _condition(
                acceptance,
                contract_version_identity=selected_version.identity,
            )
        ]
    return acceptance.AcceptanceContract(
        task_id="task:1",
        version=selected_version,
        conditions=selected,
        approved=approved,
        history=history,
    )


def _next_version(models, *, identity: str = "contract:2"):
    return _version(
        models,
        identity=identity,
        sequence=2,
        display_text="Acceptance Contract",
    )


def _evidence(
    acceptance,
    *,
    condition_identity: str = "condition:machine",
    contract_version_identity: str = "contract:1",
    status: str = "PASSED",
    **overrides: object,
):
    values = {
        "identity": "evidence:1",
        "condition_identity": condition_identity,
        "contract_version_identity": contract_version_identity,
        "kind": acceptance.MachineEvidenceKind.VALIDATION,
        "producer_identity": "tool:pytest",
        "command_identity": "validation:pytest",
        "input_digest": "3" * 64,
        "baseline_manifest_digest": "4" * 64,
        "changeset_digest": "5" * 64,
        "result_digest": "6" * 64,
        "status": acceptance.ConditionStatus[status],
        "sequence": 1,
        "occurred_at": 100,
        "bounded_summary": "validation completed",
    }
    values.update(overrides)
    return acceptance.MachineEvidence(**values)


def _command(
    acceptance,
    *,
    condition_identity: str = "condition:user",
    contract_version_identity: str = "contract:1",
    action: str = "CONFIRM",
    **overrides: object,
):
    values = {
        "identity": "command:confirm:1",
        "task_id": "task:1",
        "contract_version_identity": contract_version_identity,
        "condition_identity": condition_identity,
        "expected_status": acceptance.ConditionStatus.NOT_RUN,
        "action": acceptance.UserConfirmationAction[action],
        "request_digest": "7" * 64,
        "idempotency_key": "confirmation:key:1",
        "occurred_at": 101,
    }
    values.update(overrides)
    return acceptance.UserConfirmationCommand(**values)


def _assert_contract_immutable() -> None:
    acceptance, models = _load_wp08_api()
    source_conditions = [_condition(acceptance)]
    contract = _contract(
        acceptance,
        models,
        conditions=source_conditions,
    )
    source_conditions.append(
        _condition(
            acceptance,
            identity="condition:late",
            required=False,
        )
    )
    assert len(contract.conditions) == 1
    assert type(contract.conditions) is tuple
    with pytest.raises((FrozenInstanceError, AttributeError)):
        contract.approved = False
    same_text_new_identity = _contract(
        acceptance,
        models,
        version=_version(
            models,
            identity="contract:other",
            display_text=contract.version.display_text,
        ),
    )
    assert contract.version != same_text_new_identity.version
    assert contract != same_text_new_identity


def _assert_condition_kinds_closed() -> None:
    acceptance, _ = _load_wp08_api()
    assert tuple(item.name for item in acceptance.AcceptanceConditionKind) == CONDITION_KINDS
    assert tuple(item.value for item in acceptance.AcceptanceConditionKind) == CONDITION_KIND_VALUES
    assert len(acceptance.AcceptanceConditionKind.__members__) == 2
    with pytest.raises(ValueError):
        acceptance.AcceptanceConditionKind("auto_approved")
    with pytest.raises(ValueError):
        acceptance.AcceptanceCondition(
            identity="condition:forged",
            display_text="forged",
            kind="machine",
            required=True,
            status=acceptance.ConditionStatus.NOT_RUN,
            expected_contract_version_identity="contract:1",
        )


def _assert_condition_statuses_closed() -> None:
    acceptance, _ = _load_wp08_api()
    assert tuple(item.name for item in acceptance.ConditionStatus) == CONDITION_STATUSES
    assert tuple(item.value for item in acceptance.ConditionStatus) == CONDITION_STATUSES
    assert len(acceptance.ConditionStatus.__members__) == 4
    for status in acceptance.ConditionStatus:
        with pytest.raises(TypeError):
            bool(status)
    with pytest.raises(ValueError):
        acceptance.ConditionStatus("UNKNOWN")


def _assert_llm_cannot_pass() -> None:
    acceptance, models = _load_wp08_api()
    contract = _contract(acceptance, models)
    evaluator = acceptance.AcceptanceEvaluator()
    update = evaluator.apply_machine_evidence(
        contract=contract,
        evidence="LLM says every test passed",
        new_version=_next_version(models),
    )
    assert update.accepted is False
    assert update.contract is contract
    result = evaluator.evaluate(
        contract=contract,
        expected_contract_version_identity=contract.version.identity,
        llm_recommendation="PASSED",
    )
    assert result.eligible_for_apply is False
    assert contract.conditions[0].status is acceptance.ConditionStatus.NOT_RUN


def _assert_machine_needs_evidence() -> None:
    acceptance, models = _load_wp08_api()
    contract = _contract(acceptance, models)
    evidence = _evidence(acceptance)
    result = acceptance.AcceptanceEvaluator().apply_machine_evidence(
        contract=contract,
        evidence=evidence,
        new_version=_next_version(models),
    )
    assert result.accepted is True
    assert result.conflict is False
    assert result.contract.version.identity == "contract:2"
    assert result.contract.conditions[0].status is acceptance.ConditionStatus.PASSED
    assert contract.conditions[0].status is acceptance.ConditionStatus.NOT_RUN


def _assert_user_needs_bound_command() -> None:
    acceptance, models = _load_wp08_api()
    user_condition = _condition(
        acceptance,
        identity="condition:user",
        kind="USER_CONFIRMATION",
    )
    contract = _contract(acceptance, models, conditions=[user_condition])
    command = _command(acceptance)
    result = acceptance.AcceptanceEvaluator().apply_user_confirmation(
        contract=contract,
        command=command,
        new_version=_next_version(models),
    )
    assert result.accepted is True
    assert result.contract.conditions[0].status is acceptance.ConditionStatus.PASSED
    assert contract.conditions[0].status is acceptance.ConditionStatus.NOT_RUN
    event = result.contract.history[-1]
    assert event.source_identity == command.identity
    assert event.request_digest == command.request_digest
    assert event.idempotency_key == command.idempotency_key


def _assert_history_preserved() -> None:
    acceptance, models = _load_wp08_api()
    contract = _contract(acceptance, models)
    result = acceptance.AcceptanceEvaluator().apply_machine_evidence(
        contract=contract,
        evidence=_evidence(acceptance),
        new_version=_next_version(models),
    )
    assert contract.history == ()
    assert result.contract is not contract
    assert result.contract.version.identity == "contract:2"
    assert len(result.contract.history) == 1
    event = result.contract.history[0]
    assert event.previous_contract_version_identity == "contract:1"
    assert event.new_contract_version_identity == "contract:2"
    assert event.previous_status is acceptance.ConditionStatus.NOT_RUN
    assert event.new_status is acceptance.ConditionStatus.PASSED
    assert event.source_identity == "evidence:1"


def _assert_required_incomplete_blocks_apply() -> None:
    acceptance, models = _load_wp08_api()
    contract = _contract(acceptance, models)
    result = acceptance.AcceptanceEvaluator().evaluate(
        contract=contract,
        expected_contract_version_identity=contract.version.identity,
        llm_recommendation=None,
    )
    assert result.eligible_for_apply is False
    assert result.contract_version_identity == contract.version.identity
    assert result.condition_results[0].condition_identity == "condition:machine"
    assert result.condition_results[0].required is True
    assert result.condition_results[0].satisfied is False


def _assert_candidate_contract_requires_approval() -> None:
    acceptance, models = _load_wp08_api()
    condition = _condition(acceptance, status="PASSED")
    candidate = _contract(
        acceptance,
        models,
        conditions=[condition],
        approved=False,
    )
    result = acceptance.AcceptanceEvaluator().evaluate(
        contract=candidate,
        expected_contract_version_identity=candidate.version.identity,
        llm_recommendation=None,
    )
    assert result.eligible_for_apply is False
    assert result.reason == "CONTRACT_APPROVAL_REQUIRED"


def test_contract_immutable() -> None:
    _assert_contract_immutable()


def test_condition_kinds_closed() -> None:
    _assert_condition_kinds_closed()


def test_condition_statuses_closed() -> None:
    _assert_condition_statuses_closed()


def test_llm_cannot_pass() -> None:
    _assert_llm_cannot_pass()


def test_machine_needs_evidence() -> None:
    _assert_machine_needs_evidence()


@pytest.mark.parametrize(
    ("field", "changed_value"),
    (
        ("contract_version_identity", "contract:old"),
        ("condition_identity", "condition:other"),
        ("producer_identity", "tool:other"),
        ("command_identity", "validation:other"),
        ("input_digest", "a" * 64),
        ("baseline_manifest_digest", "b" * 64),
        ("changeset_digest", "c" * 64),
    ),
    ids=(
        "contract-version",
        "condition",
        "producer",
        "command",
        "input-digest",
        "baseline-digest",
        "changeset-digest",
    ),
)
def test_machine_evidence_binding_drift_rejected(
    field: str,
    changed_value: object,
) -> None:
    acceptance, models = _load_wp08_api()
    contract = _contract(acceptance, models)
    evidence = _evidence(acceptance, **{field: changed_value})
    result = acceptance.AcceptanceEvaluator().apply_machine_evidence(
        contract=contract,
        evidence=evidence,
        new_version=_next_version(models),
    )
    assert result.accepted is False
    assert result.contract is contract


def test_machine_evidence_cannot_update_user_condition() -> None:
    acceptance, models = _load_wp08_api()
    condition = _condition(
        acceptance,
        identity="condition:user",
        kind="USER_CONFIRMATION",
    )
    contract = _contract(acceptance, models, conditions=[condition])
    result = acceptance.AcceptanceEvaluator().apply_machine_evidence(
        contract=contract,
        evidence=_evidence(acceptance, condition_identity="condition:user"),
        new_version=_next_version(models),
    )
    assert result.accepted is False
    assert result.contract is contract


def test_unstructured_exception_text_is_not_machine_evidence() -> None:
    acceptance, models = _load_wp08_api()
    contract = _contract(acceptance, models)
    result = acceptance.AcceptanceEvaluator().apply_machine_evidence(
        contract=contract,
        evidence=RuntimeError("SECRET raw validation failure"),
        new_version=_next_version(models),
    )
    assert result.accepted is False
    assert "SECRET" not in result.reason


def test_incomplete_machine_evidence_fails_closed() -> None:
    acceptance, models = _load_wp08_api()
    contract = _contract(acceptance, models)
    result = acceptance.AcceptanceEvaluator().apply_machine_evidence(
        contract=contract,
        evidence={"condition_identity": "condition:machine"},
        new_version=_next_version(models),
    )
    assert result.accepted is False
    assert result.contract is contract


def test_user_needs_bound_command() -> None:
    _assert_user_needs_bound_command()


@pytest.mark.parametrize(
    ("field", "changed_value"),
    (
        ("task_id", "task:other"),
        ("contract_version_identity", "contract:old"),
        ("condition_identity", "condition:other"),
        ("expected_status", "PASSED"),
    ),
    ids=(
        "task",
        "contract-version",
        "condition",
        "expected-status",
    ),
)
def test_user_confirmation_binding_drift_rejected(
    field: str,
    changed_value: object,
) -> None:
    acceptance, models = _load_wp08_api()
    condition = _condition(
        acceptance,
        identity="condition:user",
        kind="USER_CONFIRMATION",
    )
    contract = _contract(acceptance, models, conditions=[condition])
    overrides: dict[str, object] = {field: changed_value}
    if field == "expected_status":
        overrides[field] = acceptance.ConditionStatus[changed_value]
    command = _command(acceptance, **overrides)
    result = acceptance.AcceptanceEvaluator().apply_user_confirmation(
        contract=contract,
        command=command,
        new_version=_next_version(models),
    )
    assert result.accepted is False
    assert result.contract is contract


@pytest.mark.parametrize(
    "forged_authority",
    ("LLM confirms", "tool result confirms"),
    ids=("llm", "tool-result"),
)
def test_non_user_authority_cannot_confirm(forged_authority: str) -> None:
    acceptance, models = _load_wp08_api()
    condition = _condition(
        acceptance,
        identity="condition:user",
        kind="USER_CONFIRMATION",
    )
    contract = _contract(acceptance, models, conditions=[condition])
    result = acceptance.AcceptanceEvaluator().apply_user_confirmation(
        contract=contract,
        command=forged_authority,
        new_version=_next_version(models),
    )
    assert result.accepted is False
    assert result.contract is contract


def test_user_confirmation_cannot_update_machine_condition() -> None:
    acceptance, models = _load_wp08_api()
    contract = _contract(acceptance, models)
    command = _command(acceptance, condition_identity="condition:machine")
    result = acceptance.AcceptanceEvaluator().apply_user_confirmation(
        contract=contract,
        command=command,
        new_version=_next_version(models),
    )
    assert result.accepted is False
    assert result.contract is contract


def test_user_confirmation_idempotency_and_conflict() -> None:
    acceptance, models = _load_wp08_api()
    condition = _condition(
        acceptance,
        identity="condition:user",
        kind="USER_CONFIRMATION",
    )
    contract = _contract(acceptance, models, conditions=[condition])
    command = _command(acceptance)
    evaluator = acceptance.AcceptanceEvaluator()
    first = evaluator.apply_user_confirmation(
        contract=contract,
        command=command,
        new_version=_next_version(models),
    )
    duplicate = evaluator.apply_user_confirmation(
        contract=first.contract,
        command=command,
        new_version=_version(models, identity="contract:3", sequence=3),
    )
    conflicting = evaluator.apply_user_confirmation(
        contract=first.contract,
        command=replace(command, request_digest="f" * 64),
        new_version=_version(models, identity="contract:3", sequence=3),
    )
    assert first.accepted is True
    assert duplicate.accepted is True
    assert duplicate.duplicate is True
    assert duplicate.contract is first.contract
    assert conflicting.accepted is False
    assert conflicting.conflict is True


def test_user_rejection_cannot_be_overridden_by_llm() -> None:
    acceptance, models = _load_wp08_api()
    condition = _condition(
        acceptance,
        identity="condition:user",
        kind="USER_CONFIRMATION",
    )
    contract = _contract(acceptance, models, conditions=[condition])
    rejected = acceptance.AcceptanceEvaluator().apply_user_confirmation(
        contract=contract,
        command=_command(acceptance, action="REJECT"),
        new_version=_next_version(models),
    )
    evaluated = acceptance.AcceptanceEvaluator().evaluate(
        contract=rejected.contract,
        expected_contract_version_identity=rejected.contract.version.identity,
        llm_recommendation="PASSED",
    )
    assert rejected.contract.conditions[0].status is acceptance.ConditionStatus.FAILED
    assert evaluated.eligible_for_apply is False


def test_history_preserved() -> None:
    _assert_history_preserved()


@pytest.mark.parametrize(
    "status",
    ("NOT_RUN", "FAILED", "BLOCKED"),
    ids=("not-run", "failed", "blocked"),
)
def test_required_incomplete_blocks_apply(status: str) -> None:
    acceptance, models = _load_wp08_api()
    contract = _contract(
        acceptance,
        models,
        conditions=[_condition(acceptance, status=status)],
    )
    result = acceptance.AcceptanceEvaluator().evaluate(
        contract=contract,
        expected_contract_version_identity=contract.version.identity,
        llm_recommendation="PASSED",
    )
    assert result.eligible_for_apply is False
    assert result.condition_results[0].satisfied is False


def test_optional_incomplete_does_not_block_apply() -> None:
    acceptance, models = _load_wp08_api()
    conditions = [
        _condition(acceptance, status="PASSED"),
        _condition(
            acceptance,
            identity="condition:optional",
            required=False,
            status="FAILED",
        ),
    ]
    contract = _contract(acceptance, models, conditions=conditions)
    result = acceptance.AcceptanceEvaluator().evaluate(
        contract=contract,
        expected_contract_version_identity=contract.version.identity,
        llm_recommendation=None,
    )
    assert result.eligible_for_apply is True
    assert result.condition_results[1].required is False
    assert result.condition_results[1].satisfied is False


def test_contract_version_drift_invalidates_eligibility() -> None:
    acceptance, models = _load_wp08_api()
    contract = _contract(
        acceptance,
        models,
        conditions=[_condition(acceptance, status="PASSED")],
    )
    result = acceptance.AcceptanceEvaluator().evaluate(
        contract=contract,
        expected_contract_version_identity="contract:old",
        llm_recommendation=None,
    )
    assert result.eligible_for_apply is False
    assert result.reason == "CONTRACT_VERSION_CONFLICT"


def test_candidate_contract_requires_approval() -> None:
    _assert_candidate_contract_requires_approval()


def test_machine_new_version_approval_reset_requires_reapproval() -> None:
    acceptance, models = _load_wp08_api()
    original = _contract(acceptance, models, approved=True)
    updated = acceptance.AcceptanceEvaluator().apply_machine_evidence(
        contract=original,
        evidence=_evidence(acceptance),
        new_version=_next_version(models),
    )

    assert updated.accepted is True
    assert updated.contract is not original
    assert original.approved is True
    assert original.version.identity == "contract:1"
    assert original.conditions[0].status is acceptance.ConditionStatus.NOT_RUN
    assert updated.contract.version.identity == "contract:2"
    assert updated.contract.version.display_text == original.version.display_text
    assert updated.contract.conditions[0].status is acceptance.ConditionStatus.PASSED
    assert updated.contract.approved is False
    assert original.approval_version_identity == original.version.identity
    assert updated.contract.approval_version_identity is None

    pending = acceptance.AcceptanceEvaluator().evaluate(
        contract=updated.contract,
        expected_contract_version_identity=updated.contract.version.identity,
        llm_recommendation="PASSED",
    )
    assert pending.eligible_for_apply is False
    assert pending.should_apply is False
    assert pending.reason == "CONTRACT_REAPPROVAL_REQUIRED"

    reapproved = replace(updated.contract, approved=True)
    assert reapproved.version is updated.contract.version
    assert reapproved.approval_version_identity == reapproved.version.identity
    eligible = acceptance.AcceptanceEvaluator().evaluate(
        contract=reapproved,
        expected_contract_version_identity=reapproved.version.identity,
        llm_recommendation=None,
    )
    assert eligible.eligible_for_apply is True
    assert eligible.should_apply is True


def test_user_new_version_approval_reset_requires_reapproval() -> None:
    acceptance, models = _load_wp08_api()
    condition = _condition(
        acceptance,
        identity="condition:user",
        kind="USER_CONFIRMATION",
    )
    original = _contract(
        acceptance,
        models,
        conditions=[condition],
        approved=True,
    )
    updated = acceptance.AcceptanceEvaluator().apply_user_confirmation(
        contract=original,
        command=_command(acceptance),
        new_version=_next_version(models),
    )

    assert updated.accepted is True
    assert updated.contract is not original
    assert updated.contract.version.identity != original.version.identity
    assert original.approved is True
    assert updated.contract.approved is False
    assert updated.contract.approval_version_identity is None
    pending = acceptance.AcceptanceEvaluator().evaluate(
        contract=updated.contract,
        expected_contract_version_identity=updated.contract.version.identity,
        llm_recommendation=None,
    )
    assert pending.eligible_for_apply is False
    assert pending.should_apply is False
    assert pending.reason == "CONTRACT_REAPPROVAL_REQUIRED"


def test_evaluation_is_auditable_and_not_agentloop_bool() -> None:
    acceptance, models = _load_wp08_api()
    contract = _contract(
        acceptance,
        models,
        conditions=[_condition(acceptance, status="PASSED")],
    )
    result = acceptance.AcceptanceEvaluator().evaluate(
        contract=contract,
        expected_contract_version_identity=contract.version.identity,
        llm_recommendation=None,
    )
    assert result.eligible_for_apply is True
    assert result.contract_version_identity == contract.version.identity
    assert len(result.condition_results) == 1
    assert len(result.audit_digest) == 64
    assert getattr(result, "apply_approval", None) is None
    with pytest.raises(TypeError):
        bool(result)


def test_malformed_input_fails_closed() -> None:
    acceptance, _ = _load_wp08_api()
    result = acceptance.AcceptanceEvaluator().evaluate(
        contract={"conditions": "PASSED"},
        expected_contract_version_identity="contract:1",
        llm_recommendation="PASSED",
    )
    assert result.eligible_for_apply is False
    assert result.reason == "INVALID_ACCEPTANCE_INPUT"


@pytest.mark.parametrize("pv_id", WP08_OWNER_PVS, ids=WP08_OWNER_PVS)
def test_spec_requirement(pv_id: str) -> None:
    assertions: dict[str, Callable[[], None]] = {
        "PV-ACC-001": _assert_llm_cannot_pass,
        "PV-ACC-002": _assert_required_incomplete_blocks_apply,
        "PV-ACC-003": _assert_candidate_contract_requires_approval,
        "PV-ACC-004": _assert_condition_kinds_closed,
        "PV-ACC-005": _assert_history_preserved,
        "PV-ACC-006": _assert_machine_needs_evidence,
        "PV-ACC-007": _assert_condition_statuses_closed,
    }
    assertions[pv_id]()
