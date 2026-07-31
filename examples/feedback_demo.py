"""Deterministic demonstration that failed feedback changes the next action."""

from __future__ import annotations

import json

from coding_harness.agent.actions import parse_action
from coding_harness.agent.context import ContextAttempt, ContextBuilder
from coding_harness.agent.mock_llm import MockLLM, MockScriptStep
from coding_harness.agent.results import ToolResult, ToolResultStatus


def _raw_action(
    action_id: str,
    action_type: str,
) -> dict[str, object]:
    parameters: dict[str, object] = {}
    if action_type == "stop_without_safe_action":
        parameters = {
            "report": {
                "summary": "validation failed",
                "details": ["no safe follow-up action remains"],
            }
        }
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


def run_demo() -> dict[str, object]:
    script = (
        MockScriptStep.from_raw(
            expected_latest_status=None,
            raw_action=_raw_action("demo:inspect", "inspect_repository"),
        ),
        MockScriptStep.from_raw(
            expected_latest_status=ToolResultStatus.FAILED,
            raw_action=_raw_action("demo:stop", "stop_without_safe_action"),
        ),
    )
    adapter = MockLLM(script)
    initial_context = ContextBuilder.build(
        task="inspect course fixture",
        history=(),
        max_bytes=4096,
    )
    first_action = adapter.complete(initial_context)
    parsed_first = parse_action(first_action.to_dict())
    failed_result = ToolResult(
        action_id=parsed_first.action_id,
        status=ToolResultStatus.FAILED,
        summary="inspection failed",
        output="",
        resource_counts={"tool_calls": 1},
        truncated=False,
        error="deterministic injected failure",
    )
    feedback_context = ContextBuilder.build(
        task="inspect course fixture",
        history=(
            ContextAttempt(
                action=parsed_first,
                result=failed_result,
            ),
        ),
        max_bytes=4096,
    )
    next_action = adapter.complete(feedback_context)

    return {
        "scenario": "feedback_loop",
        "failure_observed": (
            feedback_context.latest_result_status is ToolResultStatus.FAILED
        ),
        "action_changed": (
            first_action.action_id,
            first_action.action_type,
        )
        != (
            next_action.action_id,
            next_action.action_type,
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), sort_keys=True, separators=(",", ":")))
