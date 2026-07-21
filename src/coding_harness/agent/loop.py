"""A small deterministic agent-loop orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import math
import unicodedata

from coding_harness.agent.actions import (
    ControlAction,
    StructuredAction,
    ToolAction,
    parse_action,
)
from coding_harness.agent.adapters import LLMAdapter
from coding_harness.agent.context import ContextAttempt, ContextBuilder
from coding_harness.agent.ports import ClockPort, PolicyPort, StorePort, ToolPort
from coding_harness.agent.results import ToolResult, ToolResultStatus
from coding_harness.agent.stopping import (
    FailureCode,
    ProgressRecord,
    ProgressState,
    StopController,
    StopInputs,
    StopLimits,
    StopReason,
    advance_no_progress,
    observation_signature,
)


_INVESTIGATION_TOOLS = frozenset(
    {
        "inspect_repository",
        "list_files",
        "read_file",
        "search_text",
        "git_repo_probe",
        "git_repo_root",
        "git_status",
        "git_diff_worktree",
        "git_diff_index",
        "git_list_tracked",
        "git_list_untracked",
    }
)
_PROPOSAL_FIELDS = frozenset(
    {"understanding", "scope", "validation", "risks", "budget", "sensitive_actions"}
)
_TERMINAL_CONTROL_REASONS = {
    "report_blocked": StopReason.BLOCKED,
    "stop_with_failure": StopReason.FAILED,
    "stop_without_safe_action": StopReason.CANCELLED,
}
_INVESTIGATION_SCALAR_PATH_FIELDS = {
    "list_files": ("path",),
    "read_file": ("path",),
}
_INVESTIGATION_LIST_PATH_FIELDS = {
    "search_text": ("paths",),
    "git_diff_worktree": ("paths",),
    "git_diff_index": ("paths",),
    "git_list_tracked": ("paths",),
    "git_list_untracked": ("paths",),
}
# The frozen public action contract permits ordinary strings through 4096 bytes;
# the execution gate treats that value itself as the forbidden path boundary.
_REPO_PATH_FORBIDDEN_BYTES = 4_096
_GLOB_MARKERS = frozenset("*?[")


class _LoopSignal(StrEnum):
    INVALID = "INVALID"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    ACCEPTANCE_COMPLETE = "ACCEPTANCE_COMPLETE"


@dataclass(frozen=True, slots=True)
class _LoopSnapshot:
    signal: _LoopSignal | None = None


@dataclass(frozen=True, slots=True, init=False)
class PlanProposal:
    _canonical: str

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("PlanProposal instances are constructed by AgentLoop")

    def to_dict(self) -> dict[str, object]:
        return json.loads(self._canonical)


def _build_proposal(value: object) -> PlanProposal:
    if type(value) is not dict or frozenset(value) != _PROPOSAL_FIELDS:
        raise ValueError("proposal must contain exactly the six approved fields")
    try:
        canonical = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        if len(canonical.encode("utf-8")) > 65_536:
            raise ValueError("proposal exceeds the byte limit")
        normalized = json.loads(canonical)
    except (RecursionError, TypeError, UnicodeEncodeError, ValueError):
        raise ValueError("proposal must be bounded pure JSON") from None
    if type(normalized) is not dict or frozenset(normalized) != _PROPOSAL_FIELDS:
        raise ValueError("proposal could not be normalized")
    if any(
        item is None
        or (type(item) in (str, list, dict) and len(item) == 0)
        for item in normalized.values()
    ):
        raise ValueError("proposal fields must not be empty")
    proposal = object.__new__(PlanProposal)
    object.__setattr__(proposal, "_canonical", canonical)
    return proposal


def _snapshot_action(value: object) -> StructuredAction:
    if type(value) not in (ToolAction, ControlAction):
        raise ValueError("action must use the public structured action contract")
    return parse_action(value.to_dict())


def _snapshot_result(value: object, *, action_id: str) -> ToolResult:
    if type(value) is not ToolResult or value.action_id != action_id:
        raise ValueError("tool returned an invalid result")
    resource_counts_failed = False
    try:
        resource_counts = dict(value.resource_counts)
    except Exception:
        resource_counts_failed = True
        resource_counts = {}
    if resource_counts_failed:
        raise ValueError("tool returned an invalid result")
    return ToolResult(
        action_id=value.action_id,
        status=value.status,
        summary=value.summary,
        output=value.output,
        resource_counts=resource_counts,
        truncated=value.truncated,
        error=value.error,
    )


def _validate_lexical_repo_path(value: object) -> None:
    if type(value) is not str or not value:
        raise ValueError("repository path is invalid")
    encoding_failed = False
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        encoding_failed = True
        encoded = b""
    if encoding_failed or not len(encoded) < _REPO_PATH_FORBIDDEN_BYTES:
        raise ValueError("repository path is invalid")
    if unicodedata.normalize("NFKC", value) != value:
        raise ValueError("repository path is invalid")
    if any(unicodedata.category(character).startswith("C") for character in value):
        raise ValueError("repository path is invalid")
    if value.startswith(("/", "\\")) or "\\" in value:
        raise ValueError("repository path is invalid")
    if len(value) >= 2 and value[0].isascii() and value[0].isalpha() and value[1] == ":":
        raise ValueError("repository path is invalid")
    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValueError("repository path is invalid")
    if value.startswith(("-", ":")) or any(marker in value for marker in _GLOB_MARKERS):
        raise ValueError("repository path is invalid")


def _validate_investigation_paths(action: StructuredAction) -> None:
    """WP-04 lexical gate; WP-09 will own RepoPath and filesystem/symlink checks."""

    payload = action.to_dict()
    parameters = payload.get("parameters")
    if type(parameters) is not dict:
        raise ValueError("action parameters are invalid")
    for field in _INVESTIGATION_SCALAR_PATH_FIELDS.get(action.action_type, ()):
        _validate_lexical_repo_path(parameters.get(field))
    for field in _INVESTIGATION_LIST_PATH_FIELDS.get(action.action_type, ()):
        paths = parameters.get(field, [])
        if type(paths) is not list:
            raise ValueError("repository path list is invalid")
        for path in paths:
            _validate_lexical_repo_path(path)


@dataclass(frozen=True, slots=True)
class LoopResult:
    reason: StopReason
    rounds: int
    tool_calls: int
    attempts: tuple[ContextAttempt, ...]
    trace: tuple[str, ...]
    proposal: PlanProposal | None


def _decision(
    stopper: StopController,
    limits: StopLimits,
    *,
    snapshot: _LoopSnapshot,
    rounds: int,
    tool_calls: int,
    no_progress_count: int,
) -> StopReason:
    return stopper.evaluate(
        state=StopInputs(
            invalid_or_out_of_scope=snapshot.signal is _LoopSignal.INVALID,
            awaiting_approval=snapshot.signal is _LoopSignal.APPROVAL_PENDING,
            completed=snapshot.signal is _LoopSignal.ACCEPTANCE_COMPLETE,
            rounds=rounds,
            tool_calls=tool_calls,
            no_progress_count=no_progress_count,
        ),
        limits=limits,
    ).reason


class AgentLoop:
    __slots__ = (
        "_llm",
        "_policy",
        "_tool",
        "_store",
        "_clock",
        "_stopper",
        "_limits",
        "_max_context_bytes",
    )

    def __init__(
        self,
        *,
        llm: LLMAdapter,
        policy: PolicyPort,
        tool: ToolPort,
        store: StorePort,
        clock: ClockPort,
        stopper: StopController,
        limits: StopLimits,
        max_context_bytes: int,
    ) -> None:
        if not isinstance(llm, LLMAdapter):
            raise ValueError("llm must implement LLMAdapter")
        if not isinstance(policy, PolicyPort):
            raise ValueError("policy must implement PolicyPort")
        if not isinstance(tool, ToolPort):
            raise ValueError("tool must implement ToolPort")
        if not isinstance(store, StorePort):
            raise ValueError("store must implement StorePort")
        if not isinstance(clock, ClockPort):
            raise ValueError("clock must implement ClockPort")
        if type(stopper) is not StopController or type(limits) is not StopLimits:
            raise ValueError("stopper and limits must use the public stopping contracts")
        if type(max_context_bytes) is not int or max_context_bytes <= 0:
            raise ValueError("max_context_bytes must be a positive exact integer")
        self._llm = llm
        self._policy = policy
        self._tool = tool
        self._store = store
        self._clock = clock
        self._stopper = stopper
        self._limits = limits
        self._max_context_bytes = max_context_bytes

    def run(
        self,
        *,
        task: str,
        progress_state: ProgressState | None = None,
        acceptance_complete: bool = False,
    ) -> LoopResult:
        if progress_state is None:
            progress_state = ProgressState(0, 0, 0)
        if type(progress_state) is not ProgressState or type(acceptance_complete) is not bool:
            raise ValueError("run inputs are invalid")

        attempts: list[ContextAttempt] = []
        trace: list[str] = []
        rounds = 0
        tool_calls = 0
        progress: ProgressRecord | None = None
        snapshot = _LoopSnapshot(
            _LoopSignal.ACCEPTANCE_COMPLETE if acceptance_complete else None
        )

        def outcome(reason: StopReason, proposal: PlanProposal | None = None) -> LoopResult:
            return LoopResult(
                reason=reason,
                rounds=rounds,
                tool_calls=tool_calls,
                attempts=tuple(attempts),
                trace=tuple(trace),
                proposal=proposal,
            )

        while True:
            reason = _decision(
                self._stopper,
                self._limits,
                snapshot=snapshot,
                rounds=rounds,
                tool_calls=tool_calls,
                no_progress_count=progress.count if progress is not None else 0,
            )
            if reason is not StopReason.CONTINUE:
                return outcome(reason)

            try:
                store_context = ContextBuilder.build(
                    task=task,
                    history=attempts[-1:],
                    max_bytes=self._max_context_bytes,
                )
                llm_context = ContextBuilder.build(
                    task=task,
                    history=attempts[-1:],
                    max_bytes=self._max_context_bytes,
                )
                rounds += 1
                trace.append(f"context:{rounds}")
                started_at = self._clock.now()
                if type(started_at) is not float or not math.isfinite(started_at):
                    raise ValueError("clock returned an invalid timestamp")
                stored = self._store.record_attempt(
                    attempt_number=rounds,
                    context=store_context,
                    started_at=started_at,
                )
                if stored is not None:
                    raise ValueError("store returned an invalid result")
                trace.append(f"attempt:{rounds}:persisted")
                proposed_action = self._llm.complete(llm_context)
                trace.append(f"llm:{rounds}")
                action = _snapshot_action(proposed_action)
                _validate_investigation_paths(action)
                policy_snapshot = _snapshot_action(action)
                allowed = self._policy.allows(action=policy_snapshot)
                trace.append(f"policy:{action.action_id}")
                if type(allowed) is not bool or not allowed:
                    raise ValueError("policy did not allow the action")
            except Exception:
                return outcome(StopReason.INVALID_OR_OUT_OF_SCOPE)

            if type(action) is ControlAction:
                if action.action_type == "propose_plan":
                    try:
                        parameters = action.to_dict()["parameters"]
                        if type(parameters) is not dict or frozenset(parameters) != {"proposal"}:
                            raise ValueError("invalid proposal parameters")
                        proposal = _build_proposal(parameters["proposal"])
                    except Exception:
                        return outcome(StopReason.INVALID_OR_OUT_OF_SCOPE)
                    trace.append("proposal:built")
                    reason = _decision(
                        self._stopper,
                        self._limits,
                        snapshot=_LoopSnapshot(_LoopSignal.APPROVAL_PENDING),
                        rounds=rounds,
                        tool_calls=tool_calls,
                        no_progress_count=progress.count if progress is not None else 0,
                    )
                    trace.append(f"stop:{reason.value}")
                    return outcome(reason, proposal)
                if action.action_type in {
                    "request_clarification",
                    "request_budget_extension",
                    "request_user_confirmation",
                }:
                    return outcome(StopReason.AWAITING_APPROVAL)
                terminal_reason = _TERMINAL_CONTROL_REASONS.get(action.action_type)
                if terminal_reason is not None:
                    trace.append(f"stop:{terminal_reason.value}")
                    return outcome(terminal_reason)
                return outcome(StopReason.INVALID_OR_OUT_OF_SCOPE)

            if action.action_type not in _INVESTIGATION_TOOLS:
                return outcome(StopReason.INVALID_OR_OUT_OF_SCOPE)
            try:
                tool_snapshot = _snapshot_action(action)
                if type(tool_snapshot) is not ToolAction:
                    raise ValueError("tool action snapshot is invalid")
                trace.append(f"tool:{action.action_id}")
                tool_calls += 1
                raw_result = self._tool.execute(action=tool_snapshot)
                result = _snapshot_result(raw_result, action_id=action.action_id)
                history_snapshot = _snapshot_action(action)
                if type(history_snapshot) is not ToolAction:
                    raise ValueError("history action snapshot is invalid")
                attempt = ContextAttempt(action=history_snapshot, result=result)
            except Exception:
                return outcome(StopReason.INVALID_OR_OUT_OF_SCOPE)
            attempts.append(attempt)
            trace.append(f"feedback:{action.action_id}")

            failure_code = None
            if result.status is ToolResultStatus.FAILED:
                failure_code = FailureCode.TOOL_FAILED
            elif result.status is ToolResultStatus.DENIED:
                failure_code = FailureCode.TOOL_DENIED
            try:
                signature = observation_signature(
                    action=action,
                    result_status=result.status,
                    failure_code=failure_code,
                    stop_signal=None,
                    progress_state=progress_state,
                )
                progress = advance_no_progress(
                    previous=progress,
                    signature=signature,
                    state=progress_state,
                )
                reason = _decision(
                    self._stopper,
                    self._limits,
                    snapshot=_LoopSnapshot(),
                    rounds=rounds,
                    tool_calls=tool_calls,
                    no_progress_count=progress.count,
                )
            except Exception:
                return outcome(StopReason.INVALID_OR_OUT_OF_SCOPE)
            trace.append(f"stop:{reason.value}")
            if reason is not StopReason.CONTINUE:
                return outcome(reason)


__all__ = ["AgentLoop", "LoopResult", "PlanProposal"]
