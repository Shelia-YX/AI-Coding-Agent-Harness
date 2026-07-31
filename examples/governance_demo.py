"""Deterministic demonstration of a permanent governance rejection."""

from __future__ import annotations

import json

from coding_harness.domain.enums import TaskState
from coding_harness.domain.policy import PolicyContext, PolicyEngine


def run_demo() -> dict[str, object]:
    context = PolicyContext(
        task_id="course-demo-governance",
        task_state=TaskState.INVESTIGATING,
        action_name="remote_git_write",
        action_identity="course-demo-action",
        action_digest="a" * 64,
        target_type="repository",
        target_identity="course-demo-repository",
        plan_identity="course-demo-plan",
        contract_identity="course-demo-contract",
        expected_state=TaskState.INVESTIGATING,
        idempotency_key="course-demo-governance-1",
        trusted_profile="python312",
        repository_capability_requests=frozenset(),
        user_approval_present=False,
        llm_suggested_decision="ALLOW",
    )
    record = PolicyEngine.decide(context=context)
    executor_calls = 0

    if record.tool_execution_permitted:
        executor_calls += 1

    return {
        "scenario": "governance_rejection",
        "decision": record.decision.value,
        "executor_calls": executor_calls,
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), sort_keys=True, separators=(",", ":")))
