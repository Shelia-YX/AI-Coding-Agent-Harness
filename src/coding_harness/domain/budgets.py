from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Mapping


class BudgetDimension(StrEnum):
    AGENT_ROUNDS = "AGENT_ROUNDS"
    LLM_CALLS = "LLM_CALLS"
    TOOL_CALLS = "TOOL_CALLS"
    MODIFIED_FILES = "MODIFIED_FILES"
    CHANGESET_BYTES = "CHANGESET_BYTES"
    COMMANDS = "COMMANDS"
    ELAPSED_SECONDS = "ELAPSED_SECONDS"
    OUTPUT_BYTES = "OUTPUT_BYTES"


class BudgetDecision(StrEnum):
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    HARD_LIMIT_REACHED = "HARD_LIMIT_REACHED"
    INVALID = "INVALID"


def _is_nonnegative_integer(value: object) -> bool:
    return type(value) is int and value >= 0


def _closed_limits(value: object) -> dict[BudgetDimension, int] | None:
    if type(value) is not dict:
        return None
    if frozenset(value) != frozenset(BudgetDimension):
        return None
    normalized: dict[BudgetDimension, int] = {}
    for dimension, limit in value.items():
        if type(dimension) is not BudgetDimension or not _is_nonnegative_integer(limit):
            return None
        normalized[dimension] = limit
    return normalized


@dataclass(frozen=True, slots=True)
class StopEvaluation:
    should_stop: bool
    reason: str


@dataclass(frozen=True, slots=True)
class RunLimits:
    soft_limits: Mapping[BudgetDimension, int]
    hard_limits: Mapping[BudgetDimension, int]
    repeated_failure_limit: int
    no_progress_limit: int

    def __post_init__(self) -> None:
        soft = _closed_limits(self.soft_limits)
        hard = _closed_limits(self.hard_limits)
        if soft is None or hard is None:
            raise ValueError("invalid run limits")
        if any(soft[dimension] > hard[dimension] for dimension in BudgetDimension):
            raise ValueError("invalid run limits")
        if not _is_nonnegative_integer(self.repeated_failure_limit):
            raise ValueError("invalid run limits")
        if not _is_nonnegative_integer(self.no_progress_limit):
            raise ValueError("invalid run limits")
        if self.repeated_failure_limit == 0 or self.no_progress_limit == 0:
            raise ValueError("invalid run limits")
        object.__setattr__(self, "soft_limits", MappingProxyType(soft))
        object.__setattr__(self, "hard_limits", MappingProxyType(hard))

    def evaluate_stop(
        self,
        *,
        repeated_failures: object,
        no_progress_count: object,
    ) -> StopEvaluation:
        if not _is_nonnegative_integer(repeated_failures):
            raise ValueError("invalid run progress")
        if not _is_nonnegative_integer(no_progress_count):
            raise ValueError("invalid run progress")
        if repeated_failures >= self.repeated_failure_limit:
            return StopEvaluation(True, "REPEATED_FAILURE_LIMIT")
        if no_progress_count >= self.no_progress_limit:
            return StopEvaluation(True, "NO_PROGRESS_LIMIT")
        return StopEvaluation(False, "CONTINUE")


@dataclass(frozen=True, slots=True, eq=False)
class BudgetVersion:
    identity: str
    task_id: str
    sequence: int
    limits: RunLimits
    display_text: str

    def __post_init__(self) -> None:
        for value in (self.identity, self.task_id, self.display_text):
            if type(value) is not str or not value or "\0" in value:
                raise ValueError("invalid budget version")
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError("invalid budget version")
        if type(self.limits) is not RunLimits:
            raise ValueError("invalid budget version")

    def __eq__(self, other: object) -> bool:
        if type(other) is not BudgetVersion:
            return NotImplemented
        return self.identity == other.identity

    def __hash__(self) -> int:
        return hash((BudgetVersion, self.identity))


@dataclass(frozen=True, slots=True)
class BudgetCheckResult:
    decision: BudgetDecision
    reason: str
    side_effect_permitted: bool
    approval_required: bool
    dimension: BudgetDimension | None
    budget_version_identity: str | None
    usage_snapshot_digest: str | None
    proposed_cost: tuple[tuple[BudgetDimension, int], ...]
    checked_before_effect: bool
    usage_before: int | None
    proposed_usage: int | None


def _invalid_result(budget_version: object) -> BudgetCheckResult:
    identity = budget_version.identity if type(budget_version) is BudgetVersion else None
    return BudgetCheckResult(
        decision=BudgetDecision.INVALID,
        reason="INVALID_BUDGET_INPUT",
        side_effect_permitted=False,
        approval_required=False,
        dimension=None,
        budget_version_identity=identity,
        usage_snapshot_digest=None,
        proposed_cost=(),
        checked_before_effect=True,
        usage_before=None,
        proposed_usage=None,
    )


def _usage_snapshot(value: object) -> dict[BudgetDimension, int] | None:
    if type(value) is not dict or frozenset(value) != frozenset(BudgetDimension):
        return None
    normalized: dict[BudgetDimension, int] = {}
    for dimension, usage in value.items():
        if type(dimension) is not BudgetDimension or not _is_nonnegative_integer(usage):
            return None
        normalized[dimension] = usage
    return normalized


def _cost_snapshot(value: object) -> dict[BudgetDimension, int] | None:
    if type(value) is not dict or not value:
        return None
    normalized: dict[BudgetDimension, int] = {}
    for dimension, cost in value.items():
        if type(dimension) is not BudgetDimension or not _is_nonnegative_integer(cost):
            return None
        normalized[dimension] = cost
    return normalized


def _usage_digest(usage: Mapping[BudgetDimension, int]) -> str:
    payload = {dimension.value: usage[dimension] for dimension in BudgetDimension}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def check_before_effect(
    *,
    budget_version: object,
    expected_budget_identity: object,
    usage: object,
    proposed_cost: object,
) -> BudgetCheckResult:
    if type(budget_version) is not BudgetVersion:
        return _invalid_result(budget_version)
    if type(expected_budget_identity) is not str:
        return _invalid_result(budget_version)
    if budget_version.identity != expected_budget_identity:
        return _invalid_result(budget_version)
    normalized_usage = _usage_snapshot(usage)
    normalized_cost = _cost_snapshot(proposed_cost)
    if normalized_usage is None or normalized_cost is None:
        return _invalid_result(budget_version)

    digest = _usage_digest(normalized_usage)
    cost_record = tuple(
        (dimension, normalized_cost[dimension])
        for dimension in BudgetDimension
        if dimension in normalized_cost
    )
    predicted = {
        dimension: normalized_usage[dimension] + normalized_cost.get(dimension, 0)
        for dimension in BudgetDimension
    }
    for dimension in BudgetDimension:
        if predicted[dimension] >= budget_version.limits.hard_limits[dimension]:
            return BudgetCheckResult(
                BudgetDecision.HARD_LIMIT_REACHED,
                "HARD_LIMIT_REACHED",
                False,
                False,
                dimension,
                budget_version.identity,
                digest,
                cost_record,
                True,
                normalized_usage[dimension],
                predicted[dimension],
            )
    for dimension in BudgetDimension:
        if predicted[dimension] >= budget_version.limits.soft_limits[dimension]:
            return BudgetCheckResult(
                BudgetDecision.REQUIRE_APPROVAL,
                "BUDGET_REAPPROVAL_REQUIRED",
                False,
                True,
                dimension,
                budget_version.identity,
                digest,
                cost_record,
                True,
                normalized_usage[dimension],
                predicted[dimension],
            )
    return BudgetCheckResult(
        BudgetDecision.ALLOW,
        "BUDGET_AVAILABLE",
        True,
        False,
        None,
        budget_version.identity,
        digest,
        cost_record,
        True,
        None,
        None,
    )


__all__ = [
    "BudgetCheckResult",
    "BudgetDecision",
    "BudgetDimension",
    "BudgetVersion",
    "RunLimits",
    "StopEvaluation",
    "check_before_effect",
]
