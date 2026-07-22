from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json

from coding_harness.domain.enums import TaskState
from coding_harness.domain.errors import PolicyReason
from coding_harness.domain.models import ContractVersion, PlanVersion
from coding_harness.domain.policy import PolicyDecision, PolicyDecisionRecord


class ApprovalType(StrEnum):
    PLAN_APPROVAL = "PLAN_APPROVAL"
    ACTION_APPROVAL = "ACTION_APPROVAL"
    BUDGET_APPROVAL = "BUDGET_APPROVAL"
    APPLY_APPROVAL = "APPLY_APPROVAL"


def _is_text(value: object) -> bool:
    return type(value) is str and bool(value) and "\0" not in value


def _is_digest(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _optional_text_is_valid(value: object) -> bool:
    return value is None or _is_text(value)


def _policy_value(value: object) -> object:
    if isinstance(value, StrEnum):
        return value.value
    return value


def policy_record_digest(record: object) -> str:
    if type(record) is not PolicyDecisionRecord:
        raise ValueError("invalid policy record")
    payload = [
        _policy_value(record.decision),
        _policy_value(record.reason),
        record.detail,
        _policy_value(record.error_code),
        record.action_identity,
        record.action_digest,
        record.tool_execution_permitted,
        record.approval_can_override,
        record.effective_profile,
        record.bound_task_id,
        record.bound_target_type,
        record.bound_target_identity,
        record.bound_digest,
        _policy_value(record.bound_expected_state),
        record.bound_idempotency_key,
    ]
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True, eq=False)
class Approval:
    identity: str
    revision: int
    display_text: str
    approval_type: ApprovalType
    task_id: str
    target_identity: str
    expected_state: TaskState
    plan_version: PlanVersion
    contract_version: ContractVersion | None
    request_digest: str
    policy_record_identity: str
    policy_record_digest: str
    reason_code: str
    created_at: int
    expires_at: int
    consumed: bool
    consumed_at: int | None
    revoked: bool
    revoked_at: int | None
    idempotency_key: str
    scope_digest: str | None
    action_kind: str | None
    action_id: str | None
    normalized_paths: tuple[str, ...]
    expected_content_digest: str | None
    baseline_manifest_digest: str | None
    action_payload_digest: str | None
    action_reason: str | None
    ignored_entries: tuple[tuple[str, str, int, str], ...]
    ignored_input_mode: str | None
    allowed_stages: tuple[str, ...]
    sandbox_manifest_identity: str | None
    exportable_to_llm: bool
    changeset_digest: str | None
    budget_version_identity: str | None
    affected_dimensions: tuple[object, ...]
    current_usage: tuple[tuple[object, int], ...]
    old_limits: tuple[tuple[object, int], ...]
    new_limits: tuple[tuple[object, int], ...]
    hard_limits: tuple[tuple[object, int], ...]
    extension_reason: str | None

    def __post_init__(self) -> None:
        if type(self.approval_type) is not ApprovalType:
            raise ValueError("invalid approval")
        if type(self.expected_state) is not TaskState:
            raise ValueError("invalid approval")
        if type(self.plan_version) is not PlanVersion:
            raise ValueError("invalid approval")
        if self.contract_version is not None and type(self.contract_version) is not ContractVersion:
            raise ValueError("invalid approval")
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("invalid approval")
        for value in (
            self.identity,
            self.display_text,
            self.task_id,
            self.target_identity,
            self.policy_record_identity,
            self.reason_code,
            self.idempotency_key,
        ):
            if not _is_text(value):
                raise ValueError("invalid approval")
        for value in (self.request_digest, self.policy_record_digest):
            if not _is_digest(value):
                raise ValueError("invalid approval")
        if type(self.created_at) is not int or self.created_at < 0:
            raise ValueError("invalid approval")
        if type(self.expires_at) is not int or self.expires_at <= self.created_at:
            raise ValueError("invalid approval")
        if type(self.consumed) is not bool or type(self.revoked) is not bool:
            raise ValueError("invalid approval")
        if type(self.exportable_to_llm) is not bool:
            raise ValueError("invalid approval")
        if self.consumed != (self.consumed_at is not None):
            raise ValueError("invalid approval")
        if self.revoked != (self.revoked_at is not None):
            raise ValueError("invalid approval")
        for timestamp in (self.consumed_at, self.revoked_at):
            if timestamp is not None and (type(timestamp) is not int or timestamp < 0):
                raise ValueError("invalid approval")
        for value in (
            self.scope_digest,
            self.expected_content_digest,
            self.baseline_manifest_digest,
            self.action_payload_digest,
            self.changeset_digest,
        ):
            if value is not None and not _is_digest(value):
                raise ValueError("invalid approval")
        for value in (
            self.action_kind,
            self.action_id,
            self.action_reason,
            self.ignored_input_mode,
            self.sandbox_manifest_identity,
            self.budget_version_identity,
            self.extension_reason,
        ):
            if not _optional_text_is_valid(value):
                raise ValueError("invalid approval")
        for value in (
            self.normalized_paths,
            self.ignored_entries,
            self.allowed_stages,
            self.affected_dimensions,
            self.current_usage,
            self.old_limits,
            self.new_limits,
            self.hard_limits,
        ):
            if type(value) is not tuple:
                raise ValueError("invalid approval")

    def __eq__(self, other: object) -> bool:
        if type(other) is not Approval:
            return NotImplemented
        return self.identity == other.identity and self.revision == other.revision

    def __hash__(self) -> int:
        return hash((Approval, self.identity, self.revision))


@dataclass(frozen=True, slots=True)
class PresentedApprovalReference:
    identity: str
    revision: int

    def __post_init__(self) -> None:
        if not _is_text(self.identity):
            raise ValueError("invalid approval reference")
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("invalid approval reference")


@dataclass(frozen=True, slots=True)
class ApprovalExecutionContext:
    approval_type: ApprovalType
    task_id: str
    target_identity: str
    expected_state: TaskState
    plan_version_identity: str
    contract_version_identity: str | None
    request_digest: str
    policy_record_identity: str
    policy_record_digest: str
    reason_code: str
    idempotency_key: str
    scope_digest: str | None
    action_kind: str | None
    action_id: str | None
    normalized_paths: tuple[str, ...]
    expected_content_digest: str | None
    baseline_manifest_digest: str | None
    action_payload_digest: str | None
    action_reason: str | None
    ignored_entries: tuple[tuple[str, str, int, str], ...]
    ignored_input_mode: str | None
    allowed_stages: tuple[str, ...]
    sandbox_manifest_identity: str | None
    exportable_to_llm: bool
    changeset_digest: str | None
    budget_version_identity: str | None
    affected_dimensions: tuple[object, ...]
    current_usage: tuple[tuple[object, int], ...]
    old_limits: tuple[tuple[object, int], ...]
    new_limits: tuple[tuple[object, int], ...]
    hard_limits: tuple[tuple[object, int], ...]
    extension_reason: str | None

    def __post_init__(self) -> None:
        if type(self.approval_type) is not ApprovalType:
            raise ValueError("invalid approval context")
        if type(self.expected_state) is not TaskState:
            raise ValueError("invalid approval context")
        for value in (
            self.task_id,
            self.target_identity,
            self.plan_version_identity,
            self.policy_record_identity,
            self.reason_code,
            self.idempotency_key,
        ):
            if not _is_text(value):
                raise ValueError("invalid approval context")
        if not _optional_text_is_valid(self.contract_version_identity):
            raise ValueError("invalid approval context")
        for value in (self.request_digest, self.policy_record_digest):
            if not _is_digest(value):
                raise ValueError("invalid approval context")
        for value in (
            self.normalized_paths,
            self.ignored_entries,
            self.allowed_stages,
            self.affected_dimensions,
            self.current_usage,
            self.old_limits,
            self.new_limits,
            self.hard_limits,
        ):
            if type(value) is not tuple:
                raise ValueError("invalid approval context")


@dataclass(frozen=True, slots=True)
class ApprovalResult:
    permitted: bool
    conflict: bool
    side_effect_permitted: bool
    reason: str
    approval: Approval
    previous_revision: int
    expected_revision: int
    new_revision: int | None


_ACTION_APPROVAL_KINDS = frozenset({"delete_file", "include_ignored_input"})


def _pairs_are_valid(value: tuple[tuple[object, int], ...]) -> bool:
    return bool(value) and all(
        type(item) is tuple
        and len(item) == 2
        and type(item[1]) is int
        and item[1] >= 0
        for item in value
    )


def _ignored_entries_are_valid(value: tuple[tuple[str, str, int, str], ...]) -> bool:
    return bool(value) and all(
        type(item) is tuple
        and len(item) == 4
        and _is_text(item[0])
        and _is_text(item[1])
        and type(item[2]) is int
        and item[2] >= 0
        and _is_digest(item[3])
        for item in value
    )


def _binding_is_valid(approval: Approval) -> bool:
    if approval.plan_version.task_id != approval.task_id:
        return False
    if approval.contract_version is not None and approval.contract_version.task_id != approval.task_id:
        return False
    if approval.approval_type is ApprovalType.PLAN_APPROVAL:
        return (
            approval.expected_state is TaskState.AWAITING_PLAN_APPROVAL
            and approval.target_identity == approval.plan_version.identity
            and approval.contract_version is not None
            and approval.scope_digest is not None
        )
    if approval.approval_type is ApprovalType.ACTION_APPROVAL:
        if (
            approval.expected_state is not TaskState.AWAITING_ACTION_APPROVAL
            or approval.contract_version is not None
            or approval.action_kind not in _ACTION_APPROVAL_KINDS
            or approval.action_id != approval.target_identity
            or approval.action_payload_digest != approval.request_digest
            or len(approval.normalized_paths) != 1
            or any(not _is_text(path) for path in approval.normalized_paths)
        ):
            return False
        if approval.action_kind == "delete_file":
            return (
                approval.expected_content_digest is not None
                and approval.baseline_manifest_digest is not None
                and approval.action_reason is not None
            )
        return (
            _ignored_entries_are_valid(approval.ignored_entries)
            and tuple(item[0] for item in approval.ignored_entries) == approval.normalized_paths
            and approval.ignored_input_mode in {"read_only_input", "writable_ephemeral"}
            and bool(approval.allowed_stages)
            and all(_is_text(stage) for stage in approval.allowed_stages)
            and approval.sandbox_manifest_identity is not None
            and approval.exportable_to_llm is False
        )
    if approval.approval_type is ApprovalType.BUDGET_APPROVAL:
        return (
            approval.expected_state is TaskState.AWAITING_BUDGET_APPROVAL
            and approval.contract_version is None
            and approval.budget_version_identity is not None
            and bool(approval.affected_dimensions)
            and _pairs_are_valid(approval.current_usage)
            and _pairs_are_valid(approval.old_limits)
            and _pairs_are_valid(approval.new_limits)
            and _pairs_are_valid(approval.hard_limits)
            and approval.extension_reason is not None
        )
    return (
        approval.expected_state is TaskState.READY_TO_APPLY
        and approval.contract_version is not None
        and approval.changeset_digest is not None
        and approval.baseline_manifest_digest is not None
        and approval.target_identity == approval.changeset_digest
    )


def _policy_binding_is_valid(
    approval: Approval,
    trusted_policy_record: object,
    trusted_policy_record_identity: object,
) -> bool:
    if type(trusted_policy_record) is not PolicyDecisionRecord:
        return False
    if not _is_text(trusted_policy_record_identity):
        return False
    return (
        approval.policy_record_identity == trusted_policy_record_identity
        and approval.policy_record_digest == policy_record_digest(trusted_policy_record)
        and trusted_policy_record.decision is PolicyDecision.REQUIRE_APPROVAL
        and trusted_policy_record.reason is PolicyReason.APPROVAL_REQUIRED
        and trusted_policy_record.tool_execution_permitted is False
        and trusted_policy_record.approval_can_override is True
        and trusted_policy_record.error_code is None
        and approval.reason_code == trusted_policy_record.reason.value
        and trusted_policy_record.action_identity == approval.target_identity
        and trusted_policy_record.action_digest == approval.request_digest
        and trusted_policy_record.bound_task_id == approval.task_id
        and trusted_policy_record.bound_target_type == approval.approval_type.value
        and trusted_policy_record.bound_target_identity == approval.target_identity
        and trusted_policy_record.bound_digest == approval.request_digest
        and trusted_policy_record.bound_expected_state is approval.expected_state
        and trusted_policy_record.bound_idempotency_key == approval.idempotency_key
    )


def _context_matches_record(
    context: ApprovalExecutionContext,
    record: Approval,
) -> bool:
    return (
        context.approval_type is record.approval_type
        and context.task_id == record.task_id
        and context.target_identity == record.target_identity
        and context.expected_state is record.expected_state
        and context.plan_version_identity == record.plan_version.identity
        and context.contract_version_identity
        == (record.contract_version.identity if record.contract_version is not None else None)
        and context.request_digest == record.request_digest
        and context.policy_record_identity == record.policy_record_identity
        and context.policy_record_digest == record.policy_record_digest
        and context.reason_code == record.reason_code
        and context.idempotency_key == record.idempotency_key
        and context.scope_digest == record.scope_digest
        and context.action_kind == record.action_kind
        and context.action_id == record.action_id
        and context.normalized_paths == record.normalized_paths
        and context.expected_content_digest == record.expected_content_digest
        and context.baseline_manifest_digest == record.baseline_manifest_digest
        and context.action_payload_digest == record.action_payload_digest
        and context.action_reason == record.action_reason
        and context.ignored_entries == record.ignored_entries
        and context.ignored_input_mode == record.ignored_input_mode
        and context.allowed_stages == record.allowed_stages
        and context.sandbox_manifest_identity == record.sandbox_manifest_identity
        and context.exportable_to_llm is record.exportable_to_llm
        and context.changeset_digest == record.changeset_digest
        and context.budget_version_identity == record.budget_version_identity
        and context.affected_dimensions == record.affected_dimensions
        and context.current_usage == record.current_usage
        and context.old_limits == record.old_limits
        and context.new_limits == record.new_limits
        and context.hard_limits == record.hard_limits
        and context.extension_reason == record.extension_reason
    )


def _result(
    record: Approval,
    *,
    permitted: bool,
    conflict: bool,
    side_effect_permitted: bool,
    reason: str,
    expected_revision: int | None = None,
    new_record: Approval | None = None,
) -> ApprovalResult:
    return ApprovalResult(
        permitted=permitted,
        conflict=conflict,
        side_effect_permitted=side_effect_permitted,
        reason=reason,
        approval=new_record if new_record is not None else record,
        previous_revision=record.revision,
        expected_revision=(
            expected_revision if type(expected_revision) is int else record.revision
        ),
        new_revision=new_record.revision if new_record is not None else None,
    )


def validate_approval_creation(
    *,
    approval: object,
    trusted_policy_record: object,
    trusted_policy_record_identity: object,
) -> ApprovalResult:
    if type(approval) is not Approval:
        raise ValueError("invalid approval")
    permitted = (
        not approval.consumed
        and not approval.revoked
        and _binding_is_valid(approval)
        and _policy_binding_is_valid(
            approval,
            trusted_policy_record,
            trusted_policy_record_identity,
        )
    )
    return _result(
        approval,
        permitted=permitted,
        conflict=False,
        side_effect_permitted=False,
        reason="APPROVAL_PENDING" if permitted else "APPROVAL_REJECTED",
    )


def consume_approval(
    *,
    current_record: object,
    expected_revision: object,
    presented_reference: object,
    current_context: object,
    trusted_policy_record: object,
    trusted_policy_record_identity: object,
    now: object,
) -> ApprovalResult:
    if type(current_record) is not Approval:
        raise ValueError("invalid approval")
    valid = validate_approval_creation(
        approval=current_record,
        trusted_policy_record=trusted_policy_record,
        trusted_policy_record_identity=trusted_policy_record_identity,
    ).permitted
    valid = valid and type(expected_revision) is int
    valid = valid and type(presented_reference) is PresentedApprovalReference
    valid = valid and type(current_context) is ApprovalExecutionContext
    valid = valid and type(now) is int
    if type(presented_reference) is PresentedApprovalReference:
        valid = valid and presented_reference.identity == current_record.identity
        valid = valid and presented_reference.revision == current_record.revision
    valid = valid and expected_revision == current_record.revision
    if type(current_context) is ApprovalExecutionContext:
        valid = valid and _context_matches_record(current_context, current_record)
    valid = valid and not current_record.consumed and not current_record.revoked
    if type(now) is int:
        valid = valid and current_record.created_at <= now < current_record.expires_at
    if not valid:
        return _result(
            current_record,
            permitted=False,
            conflict=True,
            side_effect_permitted=False,
            reason="APPROVAL_CONFLICT",
            expected_revision=(
                expected_revision if type(expected_revision) is int else None
            ),
        )
    consumed = replace(
        current_record,
        revision=current_record.revision + 1,
        consumed=True,
        consumed_at=now,
    )
    return _result(
        current_record,
        permitted=True,
        conflict=False,
        side_effect_permitted=True,
        reason="APPROVAL_CONSUMED",
        expected_revision=expected_revision,
        new_record=consumed,
    )


def revoke_approval(*, approval: Approval, revoked_at: int) -> ApprovalResult:
    if type(approval) is not Approval or type(revoked_at) is not int or revoked_at < 0:
        raise ValueError("invalid approval revocation")
    if approval.consumed or approval.revoked:
        return _result(
            approval,
            permitted=False,
            conflict=True,
            side_effect_permitted=False,
            reason="APPROVAL_CONFLICT",
        )
    revoked = replace(
        approval,
        revision=approval.revision + 1,
        revoked=True,
        revoked_at=revoked_at,
    )
    return _result(
        approval,
        permitted=True,
        conflict=False,
        side_effect_permitted=False,
        reason="APPROVAL_REVOKED",
        new_record=revoked,
    )


__all__ = [
    "Approval",
    "ApprovalExecutionContext",
    "ApprovalResult",
    "ApprovalType",
    "PresentedApprovalReference",
    "consume_approval",
    "policy_record_digest",
    "revoke_approval",
    "validate_approval_creation",
]
