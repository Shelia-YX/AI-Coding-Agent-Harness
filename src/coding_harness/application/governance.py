from __future__ import annotations

from dataclasses import dataclass

from coding_harness.domain.approvals import (
    Approval,
    ApprovalExecutionContext,
    ApprovalResult,
    ApprovalType,
    PresentedApprovalReference,
    consume_approval,
    revoke_approval,
    validate_approval_creation,
)
from coding_harness.domain.budgets import BudgetDimension, BudgetVersion


@dataclass(frozen=True, slots=True)
class BudgetActivationResult:
    active_version: BudgetVersion
    changed: bool
    approval: Approval
    conflict: bool
    reason: str


def _budget_pairs(value: tuple[tuple[object, int], ...]) -> dict[BudgetDimension, int] | None:
    normalized: dict[BudgetDimension, int] = {}
    for item in value:
        if (
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not BudgetDimension
            or type(item[1]) is not int
            or item[1] < 0
            or item[0] in normalized
        ):
            return None
        normalized[item[0]] = item[1]
    return normalized if normalized else None


def _budget_binding_is_safe(approval: Approval) -> bool:
    dimensions = approval.affected_dimensions
    if not dimensions or any(type(item) is not BudgetDimension for item in dimensions):
        return False
    if len(set(dimensions)) != len(dimensions):
        return False
    current_usage = _budget_pairs(approval.current_usage)
    old_limits = _budget_pairs(approval.old_limits)
    new_limits = _budget_pairs(approval.new_limits)
    hard_limits = _budget_pairs(approval.hard_limits)
    if None in (current_usage, old_limits, new_limits, hard_limits):
        return False
    expected = set(dimensions)
    if any(set(mapping) != expected for mapping in (current_usage, old_limits, new_limits, hard_limits)):
        return False
    assert new_limits is not None
    assert hard_limits is not None
    return all(new_limits[dimension] <= hard_limits[dimension] for dimension in dimensions)


def _conflict(
    approval: Approval,
    reason: str = "APPROVAL_CONFLICT",
    *,
    expected_revision: int | None = None,
) -> ApprovalResult:
    return ApprovalResult(
        permitted=False,
        conflict=True,
        side_effect_permitted=False,
        reason=reason,
        approval=approval,
        previous_revision=approval.revision,
        expected_revision=(
            expected_revision if expected_revision is not None else approval.revision
        ),
        new_revision=None,
    )


class ApprovalService:
    def validate_creation(
        self,
        *,
        approval: object,
        trusted_policy_record: object,
        trusted_policy_record_identity: object,
    ) -> ApprovalResult:
        result = validate_approval_creation(
            approval=approval,
            trusted_policy_record=trusted_policy_record,
            trusted_policy_record_identity=trusted_policy_record_identity,
        )
        if not result.permitted:
            return result
        assert type(approval) is Approval
        if approval.approval_type is ApprovalType.BUDGET_APPROVAL:
            if not _budget_binding_is_safe(approval):
                return ApprovalResult(
                    permitted=False,
                    conflict=False,
                    side_effect_permitted=False,
                    reason="BUDGET_APPROVAL_REJECTED",
                    approval=approval,
                    previous_revision=approval.revision,
                    expected_revision=approval.revision,
                    new_revision=None,
                )
        return result

    def consume(self, **values: object) -> ApprovalResult:
        current_record = values.get("current_record")
        if type(current_record) is not Approval:
            raise ValueError("invalid approval")
        creation = self.validate_creation(
            approval=current_record,
            trusted_policy_record=values.get("trusted_policy_record"),
            trusted_policy_record_identity=values.get(
                "trusted_policy_record_identity"
            ),
        )
        if not creation.permitted:
            return _conflict(
                current_record,
                expected_revision=(
                    values.get("expected_revision")
                    if type(values.get("expected_revision")) is int
                    else None
                ),
            )
        return consume_approval(**values)

    def revoke(self, *, approval: Approval, revoked_at: int) -> ApprovalResult:
        return revoke_approval(approval=approval, revoked_at=revoked_at)

    def activate_budget(
        self,
        *,
        current: object,
        proposed: object,
        current_record: object,
        expected_revision: object,
        presented_reference: object,
        current_context: object,
        trusted_policy_record: object,
        trusted_policy_record_identity: object,
        approval_transaction_committed: object,
        committed_at: object | None = None,
    ) -> BudgetActivationResult:
        if (
            type(current) is not BudgetVersion
            or type(proposed) is not BudgetVersion
            or type(current_record) is not Approval
            or type(presented_reference) is not PresentedApprovalReference
            or type(current_context) is not ApprovalExecutionContext
            or type(approval_transaction_committed) is not bool
        ):
            raise ValueError("invalid budget activation")
        approval = current_record
        valid = self.validate_creation(
            approval=approval,
            trusted_policy_record=trusted_policy_record,
            trusted_policy_record_identity=trusted_policy_record_identity,
        ).permitted
        valid = valid and type(expected_revision) is int
        valid = valid and approval.approval_type is ApprovalType.BUDGET_APPROVAL
        valid = valid and current.task_id == proposed.task_id == approval.task_id
        valid = valid and proposed.sequence > current.sequence
        valid = valid and approval.target_identity == proposed.identity
        valid = valid and approval.budget_version_identity == current.identity
        valid = valid and current.limits.hard_limits == proposed.limits.hard_limits
        old_limits = _budget_pairs(approval.old_limits)
        new_limits = _budget_pairs(approval.new_limits)
        hard_limits = _budget_pairs(approval.hard_limits)
        if old_limits is None or new_limits is None or hard_limits is None:
            valid = False
        else:
            for dimension in approval.affected_dimensions:
                valid = valid and old_limits[dimension] == current.limits.soft_limits[dimension]
                valid = valid and new_limits[dimension] == proposed.limits.soft_limits[dimension]
                valid = valid and hard_limits[dimension] == current.limits.hard_limits[dimension]
        if not valid:
            return BudgetActivationResult(
                current,
                False,
                approval,
                True,
                "BUDGET_APPROVAL_CONFLICT",
            )
        if not approval_transaction_committed:
            return BudgetActivationResult(
                current,
                False,
                approval,
                False,
                "BUDGET_VERSION_PENDING",
            )
        if type(committed_at) is not int:
            return BudgetActivationResult(
                current,
                False,
                approval,
                True,
                "BUDGET_APPROVAL_CONFLICT",
            )
        consumed = consume_approval(
            current_record=approval,
            expected_revision=expected_revision,
            presented_reference=presented_reference,
            current_context=current_context,
            trusted_policy_record=trusted_policy_record,
            trusted_policy_record_identity=trusted_policy_record_identity,
            now=committed_at,
        )
        if not consumed.permitted:
            return BudgetActivationResult(
                current,
                False,
                approval,
                True,
                "BUDGET_APPROVAL_CONFLICT",
            )
        return BudgetActivationResult(
            proposed,
            True,
            consumed.approval,
            False,
            "BUDGET_VERSION_COMMITTED",
        )


__all__ = ["ApprovalService", "BudgetActivationResult"]
