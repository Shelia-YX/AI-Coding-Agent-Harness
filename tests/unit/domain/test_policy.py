from __future__ import annotations

import importlib
from collections.abc import Callable

import pytest


POLICY_DECISIONS = (
    "ALLOW",
    "REQUIRE_APPROVAL",
    "DENY",
    "BLOCKED_POLICY_ERROR",
)

HARD_BOUNDARY_ACTIONS = (
    "remote_git_write",
    "git_push",
    "create_pull_request",
    "create_merge_request",
    "deploy",
    "publish",
    "release",
    "cloud_resource_change",
    "production_resource_change",
    "production_database_write",
    "production_credential_injection",
    "expose_production_secret",
    "task_docker_build",
    "task_docker_run",
    "task_docker_control",
    "privileged_container",
    "host_network",
    "host_pid_namespace",
    "host_device",
    "arbitrary_volume",
    "docker_socket_access",
)

WP06_OWNER_PVS = (
    "PV-POL-001",
    "PV-POL-002",
    "PV-POL-003",
    "PV-POL-004",
    "PV-POL-005",
    "PV-POL-006",
    "PV-POL-007",
)


def _load_wp06_api():
    try:
        policy = importlib.import_module("coding_harness.domain.policy")
        errors = importlib.import_module("coding_harness.domain.errors")
        domain_enums = importlib.import_module("coding_harness.domain.enums")
    except ModuleNotFoundError:
        pytest.fail("WP-06 API unavailable", pytrace=False)
    return policy, errors, domain_enums


def _context(policy, domain_enums, default_action_name: str, **overrides: object):
    values = {
        "task_id": "task:1",
        "task_state": domain_enums.TaskState.EXECUTING,
        "action_name": default_action_name,
        "action_identity": f"action:{default_action_name}",
        "action_digest": "a" * 64,
        "target_type": "tool_action",
        "target_identity": f"target:{default_action_name}",
        "plan_identity": "plan:v1",
        "contract_identity": "contract:v1",
        "expected_state": domain_enums.TaskState.EXECUTING,
        "idempotency_key": f"policy:{default_action_name}",
        "trusted_profile": "safe-default",
        "repository_capability_requests": frozenset(),
        "user_approval_present": False,
        "llm_suggested_decision": None,
    }
    values.update(overrides)
    return policy.PolicyContext(**values)


def _decide(action_name: str, **overrides: object):
    policy, errors, domain_enums = _load_wp06_api()
    context = _context(policy, domain_enums, action_name, **overrides)
    record = policy.PolicyEngine.decide(context=context)
    return policy, errors, domain_enums, record


def _assert_record_decision(record, policy, expected: str) -> None:
    assert type(record) is policy.PolicyDecisionRecord
    assert type(record.decision) is policy.PolicyDecision
    assert record.decision is policy.PolicyDecision[expected]
    assert not isinstance(record, bool)
    assert not isinstance(record.decision, bool)


def _assert_blocked_record(record, policy, errors) -> None:
    _assert_record_decision(record, policy, "BLOCKED_POLICY_ERROR")
    assert record.reason is errors.PolicyReason.BLOCKED_POLICY_ERROR
    assert record.tool_execution_permitted is False
    assert record.approval_can_override is False


def _assert_hard_boundary_denied(action_name: str) -> None:
    policy, errors, _, record = _decide(
        action_name,
        repository_capability_requests=frozenset(
            {action_name, "privileged_container", "trusted-profile"}
        ),
        user_approval_present=True,
        llm_suggested_decision="ALLOW",
    )
    _assert_record_decision(record, policy, "DENY")
    assert record.reason is errors.PolicyReason.DENIED_CAPABILITY
    assert record.tool_execution_permitted is False
    assert record.approval_can_override is False


def _assert_decision_set_closed() -> None:
    policy, _, domain_enums = _load_wp06_api()
    assert tuple(decision.name for decision in policy.PolicyDecision) == POLICY_DECISIONS
    assert tuple(decision.value for decision in policy.PolicyDecision) == POLICY_DECISIONS
    assert len(policy.PolicyDecision.__members__) == 4
    assert policy.PolicyDecision is not domain_enums.TaskState
    assert set(POLICY_DECISIONS).isdisjoint(state.value for state in domain_enums.TaskState)

    _, _, _, record = _decide("read_file")
    _assert_record_decision(record, policy, "ALLOW")


def _assert_unknown_context_blocks() -> None:
    policy, errors, domain_enums = _load_wp06_api()
    unknown_action = policy.PolicyEngine.decide(
        context=_context(policy, domain_enums, "unknown_action")
    )
    _assert_record_decision(unknown_action, policy, "BLOCKED_POLICY_ERROR")
    assert unknown_action.reason is errors.PolicyReason.BLOCKED_POLICY_ERROR
    assert unknown_action.tool_execution_permitted is False

    unknown_context = policy.PolicyEngine.decide(context=object())
    _assert_record_decision(unknown_context, policy, "BLOCKED_POLICY_ERROR")
    assert unknown_context.reason is errors.PolicyReason.BLOCKED_POLICY_ERROR
    assert unknown_context.tool_execution_permitted is False


def _assert_deny_not_approvable() -> None:
    policy, errors, _, record = _decide(
        "remote_git_write",
        user_approval_present=True,
        llm_suggested_decision="ALLOW",
    )
    _assert_record_decision(record, policy, "DENY")
    assert record.reason is errors.PolicyReason.DENIED_CAPABILITY
    assert record.tool_execution_permitted is False
    assert record.approval_can_override is False


def _assert_repo_config_cannot_grant() -> None:
    policy, errors, _, record = _decide(
        "deploy",
        repository_capability_requests=frozenset(
            {"deploy", "privileged_container", "trusted-profile"}
        ),
        trusted_profile="safe-default",
    )
    _assert_record_decision(record, policy, "DENY")
    assert record.reason is errors.PolicyReason.DENIED_CAPABILITY
    assert record.tool_execution_permitted is False
    assert record.effective_profile == "safe-default"


def _assert_network_read_unsupported() -> None:
    policy, errors, _, record = _decide("network_read")
    _assert_record_decision(record, policy, "DENY")
    assert record.reason is errors.PolicyReason.BLOCKED_UNSUPPORTED_CAPABILITY
    assert record.tool_execution_permitted is False
    assert record.approval_can_override is False


def _assert_llm_only_suggests() -> None:
    policy, _, _, safe = _decide(
        "read_file",
        llm_suggested_decision="DENY",
    )
    _assert_record_decision(safe, policy, "ALLOW")

    _, _, _, hard_boundary = _decide(
        "remote_git_write",
        llm_suggested_decision="ALLOW",
    )
    _assert_record_decision(hard_boundary, policy, "DENY")


def _assert_approval_binding_required() -> None:
    policy, errors, _, missing = _decide(
        "delete_file",
        target_identity=None,
    )
    _assert_record_decision(missing, policy, "BLOCKED_POLICY_ERROR")
    assert missing.reason is errors.PolicyReason.BLOCKED_POLICY_ERROR

    _, _, _, complete = _decide("delete_file")
    _assert_record_decision(complete, policy, "REQUIRE_APPROVAL")
    assert complete.tool_execution_permitted is False
    assert complete.approval_can_override is True
    assert complete.bound_task_id == "task:1"
    assert complete.bound_target_type == "tool_action"
    assert complete.bound_target_identity == "target:delete_file"
    assert complete.bound_digest == "a" * 64
    assert complete.bound_expected_state.value == "EXECUTING"
    assert complete.bound_idempotency_key == "policy:delete_file"


def _assert_hard_boundaries_denied() -> None:
    for action_name in HARD_BOUNDARY_ACTIONS:
        _assert_hard_boundary_denied(action_name)


def test_decision_set_closed() -> None:
    _assert_decision_set_closed()


def test_unknown_context_blocks() -> None:
    _assert_unknown_context_blocks()


def test_deny_not_approvable() -> None:
    _assert_deny_not_approvable()


@pytest.mark.parametrize(
    "action_name",
    HARD_BOUNDARY_ACTIONS[:4],
    ids=HARD_BOUNDARY_ACTIONS[:4],
)
def test_remote_git_denied(action_name: str) -> None:
    _assert_hard_boundary_denied(action_name)


@pytest.mark.parametrize(
    "action_name",
    HARD_BOUNDARY_ACTIONS[4:12],
    ids=HARD_BOUNDARY_ACTIONS[4:12],
)
def test_deploy_denied(action_name: str) -> None:
    _assert_hard_boundary_denied(action_name)


@pytest.mark.parametrize(
    "action_name",
    HARD_BOUNDARY_ACTIONS[12:15],
    ids=HARD_BOUNDARY_ACTIONS[12:15],
)
def test_task_docker_denied(action_name: str) -> None:
    _assert_hard_boundary_denied(action_name)


@pytest.mark.parametrize(
    "action_name",
    HARD_BOUNDARY_ACTIONS[15:],
    ids=HARD_BOUNDARY_ACTIONS[15:],
)
def test_privileged_denied(action_name: str) -> None:
    _assert_hard_boundary_denied(action_name)


def test_repo_config_cannot_grant() -> None:
    _assert_repo_config_cannot_grant()


def test_network_read_unsupported() -> None:
    _assert_network_read_unsupported()


def test_direct_policy_context_misuse_raises_fixed_error() -> None:
    policy, _, domain_enums = _load_wp06_api()
    with pytest.raises(ValueError, match=r"^invalid policy context$"):
        _context(
            policy,
            domain_enums,
            "read_file",
            repository_capability_requests=["SECRET-repository-request"],
        )


@pytest.mark.parametrize(
    "malformed_context",
    (
        {"unknown_field": "SECRET-token"},
        object(),
    ),
    ids=("unknown-field", "unknown-object"),
)
def test_malformed_untrusted_context_blocks_without_leaking(
    malformed_context: object,
) -> None:
    policy, errors, _ = _load_wp06_api()
    record = policy.PolicyEngine.decide(context=malformed_context)
    _assert_blocked_record(record, policy, errors)
    rendered_authority = f"{record.reason.value} {record.detail}"
    assert "SECRET" not in rendered_authority
    assert "token" not in rendered_authority


@pytest.mark.parametrize(
    "overrides",
    (
        {"target_identity": None},
        {"expected_state": "SECRET-unknown-state"},
        {"action_name": "SECRET-unknown-action"},
    ),
    ids=("missing-required-field", "illegal-state-combination", "unknown-value"),
)
def test_invalid_context_values_block_without_leaking(
    overrides: dict[str, object],
) -> None:
    policy, errors, domain_enums = _load_wp06_api()
    context = _context(policy, domain_enums, "read_file", **overrides)
    record = policy.PolicyEngine.decide(context=context)
    _assert_blocked_record(record, policy, errors)
    rendered_authority = f"{record.reason.value} {record.detail}"
    assert "SECRET" not in rendered_authority


def test_internal_policy_evaluation_error_blocks_without_leaking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy, errors, domain_enums = _load_wp06_api()
    context = _context(policy, domain_enums, "read_file")

    def fail_evaluation(_context: object) -> bool:
        raise RuntimeError("SECRET-token /SECRET/path")

    monkeypatch.setattr(policy.PolicyEngine, "_context_is_valid", fail_evaluation)
    record = policy.PolicyEngine.decide(context=context)
    _assert_blocked_record(record, policy, errors)
    assert record.error_code is errors.PolicyErrorCode.POLICY_EVALUATION_FAILURE
    rendered_authority = f"{record.reason.value} {record.detail}"
    assert "SECRET" not in rendered_authority
    assert "token" not in rendered_authority
    assert "/SECRET/path" not in rendered_authority


@pytest.mark.parametrize("decision_name", POLICY_DECISIONS, ids=POLICY_DECISIONS)
def test_policy_decision_is_not_bool(decision_name: str) -> None:
    policy, _, _ = _load_wp06_api()
    decision = policy.PolicyDecision[decision_name]
    assert type(decision) is policy.PolicyDecision
    assert not isinstance(decision, bool)


@pytest.mark.parametrize("pv_id", WP06_OWNER_PVS, ids=WP06_OWNER_PVS)
def test_spec_requirement(pv_id: str) -> None:
    assertions: dict[str, Callable[[], None]] = {
        "PV-POL-001": _assert_llm_only_suggests,
        "PV-POL-002": _assert_decision_set_closed,
        "PV-POL-003": _assert_deny_not_approvable,
        "PV-POL-004": _assert_approval_binding_required,
        "PV-POL-005": _assert_unknown_context_blocks,
        "PV-POL-006": _assert_hard_boundaries_denied,
        "PV-POL-007": _assert_repo_config_cannot_grant,
    }
    assertions[pv_id]()
