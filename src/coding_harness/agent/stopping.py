"""Deterministic stopping and no-progress accounting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import unicodedata

from coding_harness.agent.actions import ControlAction, StructuredAction, ToolAction
from coding_harness.agent.results import ToolResultStatus


_MAX_SIGNATURE_BYTES = 65_536
_MAX_SAFE_TEXT_BYTES = 4_096
_MAX_SAFE_LIST_ITEMS = 256
_MAX_INTEGER = 2**63 - 1
_REDACTED = "<redacted>"
_TOOL_PARAMETER_RULES = {
    "inspect_repository": ({}, frozenset()),
    "list_files": (
        {"path": "text", "limit": "integer"},
        frozenset(),
    ),
    "read_file": (
        {"path": "text", "start_byte": "integer", "max_bytes": "integer"},
        frozenset(),
    ),
    "search_text": (
        {"text": "redacted", "paths": "text_list", "limit": "integer"},
        frozenset(),
    ),
    "git_repo_probe": ({}, frozenset()),
    "git_repo_root": ({}, frozenset()),
    "git_status": ({}, frozenset()),
    "git_diff_worktree": ({}, frozenset({"paths"})),
    "git_diff_index": ({}, frozenset({"paths"})),
    "git_list_tracked": ({}, frozenset({"paths"})),
    "git_list_untracked": ({}, frozenset({"paths"})),
}
_CONTROL_PARAMETER_FIELDS = {
    "request_clarification": "question",
    "propose_plan": "proposal",
    "request_budget_extension": "request",
    "request_user_confirmation": "condition",
    "report_blocked": "report",
    "stop_with_failure": "report",
    "stop_without_safe_action": "report",
}


class StopReason(StrEnum):
    INVALID_OR_OUT_OF_SCOPE = "INVALID_OR_OUT_OF_SCOPE"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    NO_PROGRESS = "NO_PROGRESS"
    CONTINUE = "CONTINUE"


class FailureCode(StrEnum):
    TOOL_FAILED = "TOOL_FAILED"
    TOOL_DENIED = "TOOL_DENIED"
    INVALID_RESULT = "INVALID_RESULT"


def _exact_nonnegative_integer(value: object, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a non-negative exact integer")
    return value


def _exact_positive_integer(value: object, field: str) -> int:
    normalized = _exact_nonnegative_integer(value, field)
    if normalized == 0:
        raise ValueError(f"{field} must be positive")
    return normalized


@dataclass(frozen=True, slots=True)
class StopLimits:
    max_rounds: int
    max_tool_calls: int
    no_progress_limit: int

    def __post_init__(self) -> None:
        _exact_positive_integer(self.max_rounds, "max_rounds")
        _exact_positive_integer(self.max_tool_calls, "max_tool_calls")
        _exact_positive_integer(self.no_progress_limit, "no_progress_limit")


@dataclass(frozen=True, slots=True)
class StopInputs:
    invalid_or_out_of_scope: bool
    awaiting_approval: bool
    completed: bool
    rounds: int
    tool_calls: int
    no_progress_count: int

    def __post_init__(self) -> None:
        for field in (
            "invalid_or_out_of_scope",
            "awaiting_approval",
            "completed",
        ):
            if type(getattr(self, field)) is not bool:
                raise ValueError(f"{field} must be an exact bool")
        _exact_nonnegative_integer(self.rounds, "rounds")
        _exact_nonnegative_integer(self.tool_calls, "tool_calls")
        _exact_nonnegative_integer(self.no_progress_count, "no_progress_count")


@dataclass(frozen=True, slots=True)
class StopDecision:
    reason: StopReason

    def __post_init__(self) -> None:
        if type(self.reason) is not StopReason:
            raise ValueError("reason must be a StopReason")


class StopController:
    def evaluate(self, *, state: StopInputs, limits: StopLimits) -> StopDecision:
        if type(state) is not StopInputs or type(limits) is not StopLimits:
            raise ValueError("state and limits must use the public stopping contracts")
        if state.invalid_or_out_of_scope:
            return StopDecision(StopReason.INVALID_OR_OUT_OF_SCOPE)
        if state.awaiting_approval:
            return StopDecision(StopReason.AWAITING_APPROVAL)
        if state.completed:
            return StopDecision(StopReason.COMPLETED)
        if state.rounds >= limits.max_rounds or state.tool_calls >= limits.max_tool_calls:
            return StopDecision(StopReason.BUDGET_EXHAUSTED)
        if state.no_progress_count >= limits.no_progress_limit:
            return StopDecision(StopReason.NO_PROGRESS)
        return StopDecision(StopReason.CONTINUE)


@dataclass(frozen=True, slots=True)
class ProgressState:
    acceptance_version: int
    budget_version: int
    approval_version: int

    def __post_init__(self) -> None:
        _exact_nonnegative_integer(self.acceptance_version, "acceptance_version")
        _exact_nonnegative_integer(self.budget_version, "budget_version")
        _exact_nonnegative_integer(self.approval_version, "approval_version")


@dataclass(frozen=True, slots=True)
class ProgressRecord:
    signature: str
    state: ProgressState
    count: int

    def __post_init__(self) -> None:
        if type(self.signature) is not str or not self.signature:
            raise ValueError("signature must be non-empty text")
        if type(self.state) is not ProgressState:
            raise ValueError("state must be a ProgressState")
        _exact_positive_integer(self.count, "count")


def _safe_text(value: object) -> str:
    if type(value) is not str or not value or "\0" in value:
        raise ValueError("safe text must be non-empty exact text")
    normalized = unicodedata.normalize("NFKC", value)
    encoding_failed = False
    try:
        size = len(normalized.encode("utf-8"))
    except UnicodeEncodeError:
        encoding_failed = True
        size = 0
    if encoding_failed:
        raise ValueError("safe text must be valid UTF-8")
    if not 1 <= size <= _MAX_SAFE_TEXT_BYTES:
        raise ValueError("safe text exceeds the byte limit")
    return normalized


def _safe_integer(value: object) -> int:
    if type(value) is not int or not 0 <= value <= _MAX_INTEGER:
        raise ValueError("safe integer is outside the allowed range")
    return value


def _safe_text_list(value: object) -> list[str]:
    if type(value) is not list or not 1 <= len(value) <= _MAX_SAFE_LIST_ITEMS:
        raise ValueError("safe text list is outside the item limit")
    return [_safe_text(item) for item in value]


def _apply_parameter_rule(rule: str, value: object) -> object:
    if rule == "text":
        return _safe_text(value)
    if rule == "integer":
        return _safe_integer(value)
    if rule == "text_list":
        return _safe_text_list(value)
    if rule == "redacted":
        return _REDACTED
    raise ValueError("unknown normalization rule")


def _normalize_budget(value: object) -> dict[str, int]:
    if type(value) is not dict or not 1 <= len(value) <= 16:
        raise ValueError("budget impact must be a bounded exact object")
    normalized: dict[str, int] = {}
    for key, item in value.items():
        if type(key) is not str or not key:
            raise ValueError("budget impact contains an invalid key")
        normalized[_safe_text(key)] = _safe_integer(item)
    return normalized


def _normalize_tool_parameters(action_type: str, value: object) -> dict[str, object]:
    if type(value) is not dict:
        raise ValueError("tool parameters must be an exact object")
    contract = _TOOL_PARAMETER_RULES.get(action_type)
    if contract is None:
        raise ValueError("tool is not allowed in an investigation signature")
    required_rules, optional_fields = contract
    allowed_fields = frozenset(required_rules) | optional_fields
    actual_fields = frozenset(value)
    if not frozenset(required_rules) <= actual_fields or not actual_fields <= allowed_fields:
        raise ValueError("tool parameters do not match the closed signature schema")

    normalized: dict[str, object] = {}
    for field in sorted(actual_fields):
        rule = required_rules.get(field, "text_list")
        normalized[field] = _apply_parameter_rule(rule, value[field])
    return normalized


def _normalize_control_parameters(action_type: str, value: object) -> dict[str, str]:
    field = _CONTROL_PARAMETER_FIELDS.get(action_type)
    if field is None or type(value) is not dict or frozenset(value) != {field}:
        raise ValueError("control parameters do not match the closed signature schema")
    return {field: _REDACTED}


def _normalize_action(action: StructuredAction) -> dict[str, object]:
    action_payload = action.to_dict()
    expected_fields = {
        "action_id",
        "action_type",
        "parameters",
        "budget_impact",
        "expected_result_type",
    }
    if type(action_payload) is not dict or set(action_payload) != expected_fields:
        raise ValueError("action payload does not match the public contract")
    action_type = action_payload["action_type"]
    expected_result_type = action_payload["expected_result_type"]
    if type(action_type) is not str or type(expected_result_type) is not str:
        raise ValueError("action metadata must be exact text")
    if type(action) is ToolAction:
        parameters = _normalize_tool_parameters(action_type, action_payload["parameters"])
    else:
        parameters = _normalize_control_parameters(action_type, action_payload["parameters"])
    return {
        "action_type": action_type,
        "budget_impact": _normalize_budget(action_payload["budget_impact"]),
        "expected_result_type": expected_result_type,
        "parameters": parameters,
    }


def observation_signature(
    *,
    action: StructuredAction,
    result_status: ToolResultStatus | None,
    failure_code: FailureCode | None,
    stop_signal: StopReason | None,
    progress_state: ProgressState,
) -> str:
    if type(action) not in (ToolAction, ControlAction):
        raise ValueError("action must be an exact structured action")
    if result_status is not None and type(result_status) is not ToolResultStatus:
        raise ValueError("result_status must be a ToolResultStatus or None")
    if failure_code is not None and type(failure_code) is not FailureCode:
        raise ValueError("failure_code must be a FailureCode or None")
    if type(progress_state) is not ProgressState:
        raise ValueError("progress_state must be a ProgressState")

    if stop_signal is not None and type(stop_signal) is not StopReason:
        raise ValueError("stop_signal must be a StopReason or None")
    normalization_failed = False
    try:
        payload = {
            "action": _normalize_action(action),
            "failure_code": failure_code.value if failure_code is not None else None,
            "result_status": result_status.value if result_status is not None else None,
            "stop_signal": stop_signal.value if stop_signal is not None else None,
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        if len(canonical.encode("utf-8")) > _MAX_SIGNATURE_BYTES:
            raise ValueError("observation signature exceeds the byte limit")
    except (RecursionError, TypeError, UnicodeEncodeError, ValueError):
        normalization_failed = True
        canonical = ""
    if normalization_failed:
        raise ValueError("observation could not be normalized")
    return canonical


def advance_no_progress(
    *,
    previous: ProgressRecord | None,
    signature: str,
    state: ProgressState,
) -> ProgressRecord:
    if previous is not None and type(previous) is not ProgressRecord:
        raise ValueError("previous must be a ProgressRecord or None")
    if type(signature) is not str or not signature:
        raise ValueError("signature must be non-empty text")
    if type(state) is not ProgressState:
        raise ValueError("state must be a ProgressState")
    count = 1
    if previous is not None and previous.signature == signature and previous.state == state:
        count = previous.count + 1
    return ProgressRecord(signature=signature, state=state, count=count)


__all__ = [
    "FailureCode",
    "ProgressRecord",
    "ProgressState",
    "StopController",
    "StopDecision",
    "StopInputs",
    "StopLimits",
    "StopReason",
    "advance_no_progress",
    "observation_signature",
]
