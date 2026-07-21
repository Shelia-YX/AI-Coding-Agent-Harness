from __future__ import annotations

import importlib
import json
import socket
from collections.abc import Mapping

import pytest

from coding_harness.agent.actions import (
    ControlAction,
    StructuredAction,
    ToolAction,
    parse_action,
)
from coding_harness.agent.results import ToolResult, ToolResultStatus


WP03_REQUIREMENTS = ("AGT-007", "AGT-009", "AGT-012", "AGT-015")


def _load_wp03_api():
    try:
        adapters = importlib.import_module("coding_harness.agent.adapters")
        context = importlib.import_module("coding_harness.agent.context")
        mock_llm = importlib.import_module("coding_harness.agent.mock_llm")
    except ModuleNotFoundError:
        pytest.fail("WP-03 API unavailable", pytrace=False)
    return adapters, context, mock_llm


def _raw_action(
    action_id: str,
    action_type: str = "inspect_repository",
) -> dict[str, object]:
    parameters: dict[str, object]
    if action_type == "stop_without_safe_action":
        parameters = {
            "report": {
                "summary": "no safe action",
                "details": ["remaining actions exceed the boundary"],
            }
        }
    elif action_type == "run_validation":
        parameters = {"profile": "python312", "operation": "pytest"}
    else:
        parameters = {}
    return {
        "action_id": action_id,
        "action_type": action_type,
        "parameters": parameters,
        "budget_impact": {"action_proposals": 1},
        "expected_result_type": (
            "control_result"
            if action_type == "stop_without_safe_action"
            else "tool_result"
        ),
    }


def _result(
    action_id: str,
    status: ToolResultStatus = ToolResultStatus.FAILED,
    *,
    output: str = "",
    summary: str | None = None,
    error: str | None = None,
) -> ToolResult:
    failed = status in {ToolResultStatus.FAILED, ToolResultStatus.DENIED}
    return ToolResult(
        action_id=action_id,
        status=status,
        summary=summary or ("operation failed" if failed else "operation succeeded"),
        output=output,
        resource_counts={"tool_calls": 1},
        truncated=False,
        error=(error or "bounded failure") if failed else None,
    )


def _canonical_bytes(value: object) -> int:
    return len(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _attempt(action_id: str, status: ToolResultStatus = ToolResultStatus.FAILED):
    _, context, _ = _load_wp03_api()
    action = parse_action(_raw_action(action_id))
    return context.ContextAttempt(action=action, result=_result(action_id, status))


class _ExplodingHistory:
    def __init__(self) -> None:
        self.failure = RuntimeError("secret-token")

    def __iter__(self):
        raise self.failure


class _ExplodingScript:
    def __init__(self) -> None:
        self.failure = RuntimeError("secret-script")

    def __iter__(self):
        raise self.failure


def _forged_action(
    action_class: type[StructuredAction],
    source: StructuredAction,
) -> StructuredAction:
    action = object.__new__(action_class)
    for field in (
        "action_id",
        "action_type",
        "parameters",
        "budget_impact",
        "expected_result_type",
    ):
        object.__setattr__(action, field, getattr(source, field))
    return action


def _assert_mock_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    adapters, context, mock_llm = _load_wp03_api()
    first = mock_llm.MockScriptStep.from_raw(
        expected_latest_status=None,
        raw_action=_raw_action("inspect:1"),
    )
    left = mock_llm.MockLLM((first,))
    right = mock_llm.MockLLM((first,))
    built = context.ContextBuilder.build(task="inspect", history=(), max_bytes=1024)
    assert isinstance(left, adapters.LLMAdapter)
    left_action = left.complete(built)
    right_action = right.complete(built)
    assert left_action.to_dict() == right_action.to_dict()
    assert parse_action(left_action.to_dict()).to_dict() == left_action.to_dict()
    with pytest.raises(mock_llm.MockLLMFailure) as caught:
        left.complete(built)
    assert caught.value.code is mock_llm.MockFailureCode.SCRIPT_EXHAUSTED
    _assert_offline_contract(monkeypatch)


def _assert_feedback_contract() -> None:
    _, context, mock_llm = _load_wp03_api()
    inspect_action = parse_action(_raw_action("inspect:feedback"))
    inspect_result = _result("inspect:feedback", ToolResultStatus.FAILED)
    attempt = context.ContextAttempt(action=inspect_action, result=inspect_result)
    built = context.ContextBuilder.build(
        task="inspect",
        history=(attempt,),
        max_bytes=4096,
    )
    assert built.attempts == (attempt,)
    result_payload = built.to_dict()["attempts"][0]["result"]
    assert result_payload == inspect_result.to_dict()
    assert built.used_bytes == _canonical_bytes(built.to_dict())

    script = (
        mock_llm.MockScriptStep.from_raw(
            expected_latest_status=None,
            raw_action=_raw_action("inspect:feedback"),
        ),
        mock_llm.MockScriptStep.from_raw(
            expected_latest_status=ToolResultStatus.FAILED,
            raw_action=_raw_action("stop:feedback", "stop_without_safe_action"),
        ),
    )
    mock = mock_llm.MockLLM(script)
    empty = context.ContextBuilder.build(task="inspect", history=(), max_bytes=4096)
    first = mock.complete(empty)
    assert first.action_id == "inspect:feedback"
    second = mock.complete(built)
    assert second.action_id == "stop:feedback"

    validation_action = parse_action(
        _raw_action("validation:failed", "run_validation")
    )
    validation_result = _result(
        "validation:failed",
        ToolResultStatus.FAILED,
        summary="pytest validation failed",
        error="validation exit status was nonzero",
    )
    validation_attempt = context.ContextAttempt(
        action=validation_action,
        result=validation_result,
    )
    validation_context = context.ContextBuilder.build(
        task="validate",
        history=(validation_attempt,),
        max_bytes=4096,
    )
    validation_payload = validation_context.to_dict()["attempts"][0]
    assert validation_payload["action"] == validation_action.to_dict()
    assert validation_payload["result"] == validation_result.to_dict()
    assert validation_payload["result"]["status"] == "FAILED"
    assert validation_payload["result"]["summary"] == "pytest validation failed"
    assert validation_context.used_bytes == _canonical_bytes(
        validation_context.to_dict()
    )
    with pytest.raises(ValueError, match="action_id"):
        context.ContextAttempt(
            action=validation_action,
            result=_result("validation:other"),
        )


def _assert_budget_contract() -> None:
    _, context, _ = _load_wp03_api()
    old = _attempt("inspect:old")
    attempt = _attempt("inspect:budget")
    roomy = context.ContextBuilder.build(
        task="任务",
        history=(old, attempt),
        max_bytes=4096,
    )
    assert roomy.attempts == (old, attempt)
    assert roomy.truncated is False
    assert roomy.to_json() == json.dumps(
        roomy.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    one_payload = {
        "task": "任务",
        "attempts": [attempt.to_dict()],
        "truncated": True,
    }
    one_budget = _canonical_bytes(one_payload)
    exact = context.ContextBuilder.build(
        task="任务",
        history=(old, attempt),
        max_bytes=one_budget,
    )
    assert exact.used_bytes == len(exact.to_json().encode("utf-8"))
    assert exact.attempts == (attempt,)
    assert exact.to_dict()["attempts"] == [attempt.to_dict()]
    assert exact.truncated is True
    one_byte_short = context.ContextBuilder.build(
        task="任务",
        history=(old, attempt),
        max_bytes=one_budget - 1,
    )
    assert one_byte_short.attempts == ()
    assert one_byte_short.truncated is True

    huge_new = context.ContextAttempt(
        action=parse_action(_raw_action("inspect:huge")),
        result=_result("inspect:huge", output="界" * 500),
    )
    huge_budget = _canonical_bytes(
        {"task": "任务", "attempts": [huge_new.to_dict()], "truncated": True}
    )
    no_backfill = context.ContextBuilder.build(
        task="任务",
        history=(old, huge_new),
        max_bytes=huge_budget - 1,
    )
    assert no_backfill.attempts == ()
    assert no_backfill.truncated is True
    minimum = _canonical_bytes(
        {"task": "任务", "attempts": [], "truncated": False}
    )
    with pytest.raises(ValueError, match="budget"):
        context.ContextBuilder.build(task="任务", history=(), max_bytes=minimum - 1)

    many_attempts = tuple(_attempt(f"inspect:linear:{index}") for index in range(100))
    original_to_dict = context.ContextAttempt.to_dict
    to_dict_calls = 0

    def counted_to_dict(self):
        nonlocal to_dict_calls
        to_dict_calls += 1
        return original_to_dict(self)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(context.ContextAttempt, "to_dict", counted_to_dict)
        linear = context.ContextBuilder.build(
            task="linear",
            history=many_attempts,
            max_bytes=10_000_000,
        )
        assert to_dict_calls <= len(many_attempts)
    assert linear.attempts == many_attempts
    assert linear.used_bytes <= linear.max_bytes


def _assert_offline_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    _, context, mock_llm = _load_wp03_api()

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("offline MockLLM attempted external access")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(name, raising=False)
    step = mock_llm.MockScriptStep.from_raw(
        expected_latest_status=None,
        raw_action=_raw_action("inspect:offline"),
    )
    built = context.ContextBuilder.build(task="offline", history=(), max_bytes=1024)
    assert mock_llm.MockLLM((step,)).complete(built).action_id == "inspect:offline"


def test_mock_script_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    adapters, context, mock_llm = _load_wp03_api()
    assert adapters.LLMAdapter.__abstractmethods__ == frozenset()
    with pytest.raises(ValueError, match="invalid action"):
        mock_llm.MockScriptStep.from_raw(
            expected_latest_status=None,
            raw_action={"action_type": "unknown"},
        )

    exact_tool = parse_action(_raw_action("inspect:exact"))
    exact_control = parse_action(
        _raw_action("stop:exact", "stop_without_safe_action")
    )
    assert type(exact_tool) is ToolAction
    assert type(exact_control) is ControlAction
    assert (
        mock_llm.MockScriptStep(expected_latest_status=None, action=exact_tool).action
        is exact_tool
    )
    assert (
        mock_llm.MockScriptStep(
            expected_latest_status=None,
            action=exact_control,
        ).action
        is exact_control
    )

    class EvilAction(StructuredAction):
        pass

    class EvilToolAction(ToolAction):
        pass

    class EvilControlAction(ControlAction):
        pass

    evil = object.__new__(EvilAction)
    object.__setattr__(evil, "action_id", "evil:governance")
    object.__setattr__(evil, "action_type", "approve_plan")
    object.__setattr__(evil, "parameters", {"mutable": []})
    object.__setattr__(evil, "budget_impact", {"action_proposals": 1})
    object.__setattr__(evil, "expected_result_type", "governance_result")
    forged_actions = (
        evil,
        _forged_action(EvilToolAction, exact_tool),
        _forged_action(EvilControlAction, exact_control),
    )
    for forged in forged_actions:
        with pytest.raises(ValueError, match="exact ToolAction or ControlAction"):
            mock_llm.MockScriptStep(expected_latest_status=None, action=forged)
    evil.parameters["mutable"].append("changed")
    assert evil.parameters == {"mutable": ["changed"]}

    script = (
        mock_llm.MockScriptStep.from_raw(
            expected_latest_status=None,
            raw_action=_raw_action("inspect:1"),
        ),
        mock_llm.MockScriptStep.from_raw(
            expected_latest_status=ToolResultStatus.FAILED,
            raw_action=_raw_action("stop:2", "stop_without_safe_action"),
        ),
    )
    empty = context.ContextBuilder.build(task="inspect", history=(), max_bytes=4096)
    failed = context.ContextBuilder.build(
        task="inspect",
        history=(_attempt("inspect:1"),),
        max_bytes=4096,
    )
    succeeded = context.ContextBuilder.build(
        task="inspect",
        history=(_attempt("inspect:1", ToolResultStatus.SUCCEEDED),),
        max_bytes=4096,
    )
    left = mock_llm.MockLLM(script)
    right = mock_llm.MockLLM(script)
    assert left.complete(empty).to_dict() == right.complete(empty).to_dict()
    with pytest.raises(mock_llm.MockLLMFailure) as mismatch:
        left.complete(succeeded)
    assert mismatch.value.code is mock_llm.MockFailureCode.STATUS_MISMATCH
    assert not ({"context", "script", "task", "extra"} & set(vars(mismatch.value)))
    assert all(value is not succeeded for value in mismatch.value.args)
    assert left.complete(failed).to_dict() == right.complete(failed).to_dict()
    with pytest.raises(mock_llm.MockLLMFailure) as exhausted:
        left.complete(failed)
    assert exhausted.value.code is mock_llm.MockFailureCode.SCRIPT_EXHAUSTED
    _assert_offline_contract(monkeypatch)


def test_failure_enters_next_context() -> None:
    _, context, _ = _load_wp03_api()
    action = parse_action(_raw_action("inspect:failed"))
    failed = context.ContextAttempt(
        action=action,
        result=_result("inspect:failed", ToolResultStatus.FAILED),
    )
    denied_action = parse_action(_raw_action("inspect:denied"))
    denied = context.ContextAttempt(
        action=denied_action,
        result=_result("inspect:denied", ToolResultStatus.DENIED),
    )
    built = context.ContextBuilder.build(
        task="inspect",
        history=(failed, denied),
        max_bytes=8192,
    )
    payload = built.to_dict()
    assert [item["result"]["status"] for item in payload["attempts"]] == [
        "FAILED",
        "DENIED",
    ]
    assert payload["attempts"][0]["result"] == failed.result.to_dict()
    with pytest.raises(ValueError, match="action_id"):
        context.ContextAttempt(action=action, result=_result("other:id"))

    exploding_history = _ExplodingHistory()
    with pytest.raises(ValueError) as unreadable_history:
        context.ContextBuilder.build(
            task="x",
            history=exploding_history,
            max_bytes=1024,
        )
    assert str(unreadable_history.value) == "history could not be read"
    assert "secret-token" not in str(unreadable_history.value)
    assert unreadable_history.value.__context__ is None
    assert unreadable_history.value.__cause__ is None
    assert unreadable_history.value.__context__ is not exploding_history.failure


def test_failure_changes_next_action() -> None:
    _, context, mock_llm = _load_wp03_api()
    steps = (
        mock_llm.MockScriptStep.from_raw(
            expected_latest_status=None,
            raw_action=_raw_action("inspect:first"),
        ),
        mock_llm.MockScriptStep.from_raw(
            expected_latest_status=ToolResultStatus.FAILED,
            raw_action=_raw_action("stop:failed", "stop_without_safe_action"),
        ),
    )
    mock = mock_llm.MockLLM(steps)
    empty = context.ContextBuilder.build(task="inspect", history=(), max_bytes=4096)
    first = mock.complete(empty)
    mismatched_context = context.ContextBuilder.build(
        task="inspect",
        history=(
            context.ContextAttempt(
                action=first,
                result=_result(first.action_id, ToolResultStatus.SUCCEEDED),
            ),
        ),
        max_bytes=4096,
    )
    with pytest.raises(mock_llm.MockLLMFailure) as caught:
        mock.complete(mismatched_context)
    assert caught.value.code is mock_llm.MockFailureCode.STATUS_MISMATCH
    failed = context.ContextBuilder.build(
        task="inspect",
        history=(
            context.ContextAttempt(action=first, result=_result(first.action_id)),
        ),
        max_bytes=4096,
    )
    second = mock.complete(failed)
    assert isinstance(first, ToolAction)
    assert isinstance(second, ControlAction)
    assert (second.action_id, second.action_type) != (first.action_id, first.action_type)
    for mutate in (
        lambda failure: setattr(failure, "code", "UNBOUNDED"),
        lambda failure: setattr(failure, "extra", {"secret": "value"}),
        lambda failure: delattr(failure, "code"),
    ):
        immutable_failure = mock_llm.MockLLMFailure(
            mock_llm.MockFailureCode.STATUS_MISMATCH
        )
        with pytest.raises(AttributeError):
            mutate(immutable_failure)
        assert immutable_failure.code is mock_llm.MockFailureCode.STATUS_MISMATCH
        assert "extra" not in vars(immutable_failure)


def test_context_order_stable() -> None:
    _, context, _ = _load_wp03_api()
    history = (_attempt("inspect:old"), _attempt("inspect:new"))
    first = context.ContextBuilder.build(task="任务", history=history, max_bytes=8192)
    second = context.ContextBuilder.build(task="任务", history=list(history), max_bytes=8192)
    assert first.attempts == history
    assert first.to_json() == second.to_json()
    assert first.used_bytes == second.used_bytes == _canonical_bytes(first.to_dict())
    assert first.to_json() == json.dumps(
        first.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    with pytest.raises(ValueError, match="ContextAttempt"):
        context.ContextBuilder.build(task="x", history=({},), max_bytes=1024)

    assert context._encode_payload({"value": 1.5}) == b'{"value":1.5}'
    for value in (float("nan"), float("inf"), float("-inf")):
        payload = {"value": value, "secret": "do-not-reflect"}
        with pytest.raises(ValueError) as non_finite:
            context._encode_payload(payload)
        assert str(non_finite.value) == "payload could not be encoded"
        assert "do-not-reflect" not in str(non_finite.value)
        assert non_finite.value.__context__ is None
        assert non_finite.value.__cause__ is None


def test_context_budget_marks_truncation() -> None:
    _assert_budget_contract()


def test_mock_has_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    _assert_offline_contract(monkeypatch)
    _, _, mock_llm = _load_wp03_api()
    exploding_script = _ExplodingScript()
    with pytest.raises(ValueError) as unreadable_script:
        mock_llm.MockLLM(exploding_script)
    assert str(unreadable_script.value) == "mock script could not be read"
    assert "secret-script" not in str(unreadable_script.value)
    assert unreadable_script.value.__context__ is None
    assert unreadable_script.value.__cause__ is None
    assert unreadable_script.value.__context__ is not exploding_script.failure


def test_mock_needs_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _assert_offline_contract(monkeypatch)


@pytest.mark.parametrize("requirement_id", WP03_REQUIREMENTS, ids=WP03_REQUIREMENTS)
def test_spec_requirement(
    requirement_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if requirement_id == "AGT-007":
        _assert_mock_contract(monkeypatch)
    elif requirement_id == "AGT-009":
        _assert_feedback_contract()
    elif requirement_id == "AGT-012":
        _assert_budget_contract()
    elif requirement_id == "AGT-015":
        _assert_offline_contract(monkeypatch)
    else:  # pragma: no cover - the closed parameter list makes this unreachable.
        raise AssertionError("unknown WP-03 requirement")
