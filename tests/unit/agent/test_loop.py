from __future__ import annotations

import importlib
import json
import math
import socket
from collections.abc import Callable

import pytest

from coding_harness.agent.actions import (
    ActionParseError,
    ControlAction,
    ToolAction,
    parse_action,
)
from coding_harness.agent.context import BuiltContext, ContextBuilder
from coding_harness.agent.mock_llm import MockLLM, MockScriptStep
from coding_harness.agent.results import ToolResult, ToolResultStatus


WP04_OWNER_PVS = (
    "PV-AGT-001",
    "PV-AGT-002",
    "PV-AGT-006",
    "PV-AGT-008",
    "PV-AGT-010",
    "PV-AGT-011",
    "PV-TST-001",
)

PROPOSAL = {
    "understanding": "inspect the repository and preserve its baseline",
    "scope": {"modify": ["src/feature.py"], "preserve": ["SPEC.md"]},
    "validation": ["run the approved unit tests"],
    "risks": ["a write could exceed the approved scope"],
    "budget": {"rounds": 4, "tool_calls": 3},
    "sensitive_actions": ["delete_file"],
}


class _StringSubclass(str):
    pass


class _IntegerSubclass(int):
    pass


def _load_wp04_api():
    try:
        ports = importlib.import_module("coding_harness.agent.ports")
        stopping = importlib.import_module("coding_harness.agent.stopping")
        loop = importlib.import_module("coding_harness.agent.loop")
    except ModuleNotFoundError:
        pytest.fail("WP-04 API unavailable", pytrace=False)
    return ports, stopping, loop


def _raw_action(
    action_id: str,
    action_type: str,
    parameters: dict[str, object] | None = None,
) -> dict[str, object]:
    control = action_type in {
        "request_clarification",
        "propose_plan",
        "request_budget_extension",
        "request_user_confirmation",
        "report_blocked",
        "stop_with_failure",
        "stop_without_safe_action",
    }
    if parameters is None:
        parameters = {}
    return {
        "action_id": action_id,
        "action_type": action_type,
        "parameters": parameters,
        "budget_impact": {"action_proposals": 1},
        "expected_result_type": "control_result" if control else "tool_result",
    }


def _proposal_action(action_id: str = "plan:1", proposal: object = PROPOSAL):
    return parse_action(_raw_action(action_id, "propose_plan", {"proposal": proposal}))


def _terminal_control_action(action_id: str, action_type: str):
    return parse_action(
        _raw_action(action_id, action_type, {"report": {"code": "SAFE_STOP"}})
    )


def _tool_action(action_id: str, action_type: str = "inspect_repository"):
    parameters: dict[str, object]
    if action_type == "create_file":
        parameters = {"path": "src/feature.py", "content": "value = 1\n"}
    elif action_type == "run_validation":
        parameters = {"profile": "python312", "operation": "pytest"}
    elif action_type in {"git_stage_paths", "git_unstage_paths"}:
        parameters = {"paths": ["src/feature.py"]}
    else:
        parameters = {}
    return parse_action(_raw_action(action_id, action_type, parameters))


def _read_file_action(
    action_id: str,
    path: str,
    *,
    reverse_keys: bool = False,
):
    items: tuple[tuple[str, object], ...] = (
        ("path", path),
        ("start_byte", 0),
        ("max_bytes", 1_024),
    )
    if reverse_keys:
        items = tuple(reversed(items))
    return parse_action(_raw_action(action_id, "read_file", dict(items)))


def _search_action(action_id: str, text: str):
    return parse_action(
        _raw_action(
            action_id,
            "search_text",
            {"text": text, "paths": ["src"], "limit": 10},
        )
    )


def _result(
    action_id: str,
    status: ToolResultStatus = ToolResultStatus.SUCCEEDED,
    *,
    error: str | None = None,
) -> ToolResult:
    failed = status in {ToolResultStatus.FAILED, ToolResultStatus.DENIED}
    return ToolResult(
        action_id=action_id,
        status=status,
        summary="bounded result",
        output="",
        resource_counts={"tool_calls": 1},
        truncated=False,
        error=(error or "closed failure") if failed else None,
    )


def _forge_flat_parameters(action: ToolAction, **updates: object) -> None:
    parameters = action.to_dict()["parameters"]
    assert type(parameters) is dict
    parameters.update(updates)
    frozen_object_type = type(action.parameters)
    object.__setattr__(
        action,
        "parameters",
        frozen_object_type((key, value) for key, value in sorted(parameters.items())),
    )


class _FakePolicy:
    def __init__(self, *, allowed: bool = True) -> None:
        self.allowed = allowed
        self.actions: list[str] = []
        self.action_objects: list[object] = []
        self.events: list[str] = []

    def allows(self, *, action: object) -> bool:
        self.actions.append(action.action_id)
        self.action_objects.append(action)
        self.events.append(f"policy:{action.action_id}")
        return self.allowed


class _FakeTool:
    def __init__(
        self,
        result_factory: Callable[[ToolAction], ToolResult] | None = None,
    ) -> None:
        self._result_factory = result_factory or (
            lambda action: _result(action.action_id)
        )
        self.actions: list[str] = []
        self.action_objects: list[ToolAction] = []
        self.events: list[str] = []

    def execute(self, *, action: ToolAction) -> ToolResult:
        self.actions.append(action.action_id)
        self.action_objects.append(action)
        self.events.append(f"tool:{action.action_id}")
        return self._result_factory(action)


class _FakeStore:
    def __init__(self) -> None:
        self.records: list[tuple[int, str, float]] = []
        self.context_objects: list[BuiltContext] = []
        self.events: list[str] = []

    def record_attempt(
        self,
        *,
        attempt_number: int,
        context: BuiltContext,
        started_at: float,
    ) -> None:
        self.context_objects.append(context)
        self.records.append((attempt_number, context.to_json(), started_at))
        self.events.append(f"store:{attempt_number}")


class _FakeClock:
    def __init__(self, value: float = 10.0) -> None:
        self.value = value
        self.calls = 0

    def now(self) -> float:
        self.calls += 1
        return self.value


def _limits(stopping, *, rounds: int = 8, tools: int = 8, progress: int = 3):
    return stopping.StopLimits(
        max_rounds=rounds,
        max_tool_calls=tools,
        no_progress_limit=progress,
    )


def _make_loop(
    *,
    llm: object,
    policy: _FakePolicy | None = None,
    tool: _FakeTool | None = None,
    store: _FakeStore | None = None,
    clock: _FakeClock | None = None,
    limits: object | None = None,
):
    ports, stopping, loop = _load_wp04_api()
    policy = policy or _FakePolicy()
    tool = tool or _FakeTool()
    store = store or _FakeStore()
    clock = clock or _FakeClock()
    instance = loop.AgentLoop(
        llm=llm,
        policy=policy,
        tool=tool,
        store=store,
        clock=clock,
        stopper=stopping.StopController(),
        limits=limits or _limits(stopping),
        max_context_bytes=16_384,
    )
    assert isinstance(policy, ports.PolicyPort)
    assert isinstance(tool, ports.ToolPort)
    assert isinstance(store, ports.StorePort)
    assert isinstance(clock, ports.ClockPort)
    return instance, policy, tool, store, clock, stopping, loop


def _assert_loop_cycle() -> None:
    first = _tool_action("inspect:1")
    proposal = _proposal_action()
    llm = MockLLM(
        (
            MockScriptStep(expected_latest_status=None, action=first),
            MockScriptStep(
                expected_latest_status=ToolResultStatus.FAILED,
                action=proposal,
            ),
        )
    )
    tool = _FakeTool(lambda action: _result(action.action_id, ToolResultStatus.FAILED))
    agent, policy, tool, store, clock, _, _ = _make_loop(llm=llm, tool=tool)

    outcome = agent.run(task="inspect and plan")

    assert outcome.reason.value == "AWAITING_APPROVAL"
    assert outcome.rounds == 2
    assert outcome.tool_calls == 1
    assert len(outcome.attempts) == 1
    assert outcome.attempts[0].result.status is ToolResultStatus.FAILED
    assert tool.actions == ["inspect:1"]
    assert policy.actions == ["inspect:1", "plan:1"]
    assert [record[0] for record in store.records] == [1, 2]
    assert json.loads(store.records[1][1])["attempts"][0]["result"]["status"] == "FAILED"
    assert clock.calls == 2
    assert outcome.trace == (
        "context:1",
        "attempt:1:persisted",
        "llm:1",
        "policy:inspect:1",
        "tool:inspect:1",
        "feedback:inspect:1",
        "stop:CONTINUE",
        "context:2",
        "attempt:2:persisted",
        "llm:2",
        "policy:plan:1",
        "proposal:built",
        "stop:AWAITING_APPROVAL",
    )


def _assert_investigation_plan_contract() -> None:
    _, stopping, _ = _load_wp04_api()
    inspect = _tool_action("inspect:allowed")
    plan = _proposal_action("plan:after-inspection")
    read_tool = _FakeTool()
    investigated, policy, read_tool, store, _, _, _ = _make_loop(
        llm=MockLLM(
            (
                MockScriptStep(expected_latest_status=None, action=inspect),
                MockScriptStep(
                    expected_latest_status=ToolResultStatus.SUCCEEDED,
                    action=plan,
                ),
            )
        ),
        tool=read_tool,
    )
    investigated_outcome = investigated.run(task="investigate before proposing")
    assert investigated_outcome.reason is stopping.StopReason.AWAITING_APPROVAL
    assert read_tool.actions == ["inspect:allowed"]
    assert policy.actions == ["inspect:allowed", "plan:after-inspection"]
    assert len(store.records) == 2

    write = _tool_action("write:blocked", "create_file")
    tool = _FakeTool()
    blocked, _, tool, _, _, _, _ = _make_loop(
        llm=MockLLM((MockScriptStep(expected_latest_status=None, action=write),)),
        tool=tool,
    )
    outcome = blocked.run(task="investigate first")
    assert outcome.reason is stopping.StopReason.INVALID_OR_OUT_OF_SCOPE
    assert tool.actions == []

    raw = json.loads(json.dumps(PROPOSAL))
    proposed, _, tool, _, _, _, _ = _make_loop(
        llm=MockLLM(
            (MockScriptStep(expected_latest_status=None, action=_proposal_action(proposal=raw)),)
        ),
        tool=_FakeTool(),
    )
    proposal_outcome = proposed.run(task="produce a plan")
    assert proposal_outcome.reason is stopping.StopReason.AWAITING_APPROVAL
    assert proposal_outcome.proposal is not None
    assert proposal_outcome.proposal.to_dict() == PROPOSAL
    raw["scope"]["modify"].append("src/escape.py")
    leaked = proposal_outcome.proposal.to_dict()
    leaked["risks"].append("mutated")
    assert proposal_outcome.proposal.to_dict() == PROPOSAL

    for bad in (
        {key: value for key, value in PROPOSAL.items() if key != "budget"},
        {**PROPOSAL, "extra": "not allowed"},
        {**PROPOSAL, "risks": []},
    ):
        invalid, _, _, _, _, _, _ = _make_loop(
            llm=MockLLM(
                (MockScriptStep(expected_latest_status=None, action=_proposal_action(proposal=bad)),)
            )
        )
        assert invalid.run(task="bad plan").reason is stopping.StopReason.INVALID_OR_OUT_OF_SCOPE


def _assert_investigation_path_gate() -> None:
    _, stopping, _ = _load_wp04_api()
    unsafe_paths = (
        "../secret",
        "/etc/passwd",
        "a/../b",
        "control\nname",
        "control\x1fname",
        "control\x7fname",
        "ｓｒｃ／file.py",
        "\\\\server\\share",
        "C:/Windows/system.ini",
        "a//b",
        "-option",
        "src/*.py",
        "a" * 4_096,
    )
    for index, path in enumerate(unsafe_paths):
        action = _read_file_action(f"path:unsafe:{index}", path)
        tool = _FakeTool()
        agent, _, tool, _, _, _, _ = _make_loop(
            llm=MockLLM(
                (MockScriptStep(expected_latest_status=None, action=action),)
            ),
            tool=tool,
        )
        outcome = agent.run(task="reject unsafe investigation path")
        assert outcome.reason is stopping.StopReason.INVALID_OR_OUT_OF_SCOPE
        assert outcome.tool_calls == 0
        assert tool.actions == []

    for suffix, forged_path in (
        ("nul", "src/safe.py\0secret"),
        ("over-limit", "a" * 4_097),
    ):
        forged_action = _read_file_action(f"path:unsafe:{suffix}", "src/safe.py")
        _forge_flat_parameters(forged_action, path=forged_path)
        forged_tool = _FakeTool()
        forged_agent, _, forged_tool, _, _, _, _ = _make_loop(
            llm=MockLLM(
                (MockScriptStep(expected_latest_status=None, action=forged_action),)
            ),
            tool=forged_tool,
        )
        forged_outcome = forged_agent.run(task="reject a forged unsafe path")
        assert forged_outcome.reason is stopping.StopReason.INVALID_OR_OUT_OF_SCOPE
        assert forged_outcome.tool_calls == 0
        assert forged_tool.actions == []

    unsafe_search = _search_action("path:unsafe:list", "needle")
    _forge_flat_parameters(unsafe_search, paths=["src", "../secret"])
    search_tool = _FakeTool()
    search_agent, _, search_tool, _, _, _, _ = _make_loop(
        llm=MockLLM(
            (MockScriptStep(expected_latest_status=None, action=unsafe_search),)
        ),
        tool=search_tool,
    )
    search_outcome = search_agent.run(task="reject an unsafe path list")
    assert search_outcome.reason is stopping.StopReason.INVALID_OR_OUT_OF_SCOPE
    assert search_outcome.tool_calls == 0
    assert search_tool.actions == []


def _assert_llm_adapter_boundary() -> None:
    _, stopping, _ = _load_wp04_api()
    proposed_write = _tool_action("adapter:write-proposal", "create_file")
    agent, policy, tool, store, _, _, _ = _make_loop(
        llm=MockLLM(
            (MockScriptStep(expected_latest_status=None, action=proposed_write),)
        )
    )
    outcome = agent.run(task="adapter may only propose an action")
    assert outcome.reason is stopping.StopReason.INVALID_OR_OUT_OF_SCOPE
    assert policy.actions == ["adapter:write-proposal"]
    assert tool.actions == []
    assert len(store.records) == 1
    assert outcome.trace == (
        "context:1",
        "attempt:1:persisted",
        "llm:1",
        "policy:adapter:write-proposal",
    )

    proposal = _proposal_action("adapter:plan-proposal")
    agent, policy, tool, store, _, _, _ = _make_loop(
        llm=MockLLM((MockScriptStep(expected_latest_status=None, action=proposal),))
    )
    outcome = agent.run(task="adapter cannot approve its proposal")
    assert outcome.reason is stopping.StopReason.AWAITING_APPROVAL
    assert outcome.proposal is not None
    assert policy.actions == ["adapter:plan-proposal"]
    assert tool.actions == []
    assert len(store.records) == 1


def _assert_attempt_persistence() -> None:
    _, stopping, _ = _load_wp04_api()
    store = _FakeStore()
    llm = MockLLM(
        (MockScriptStep(expected_latest_status=ToolResultStatus.FAILED, action=_tool_action("never")),)
    )
    agent, _, tool, store, _, _, _ = _make_loop(llm=llm, store=store)
    outcome = agent.run(task="persist before provider")
    assert outcome.reason is stopping.StopReason.INVALID_OR_OUT_OF_SCOPE
    assert len(store.records) == 1
    assert store.records[0][0] == 1
    assert tool.actions == []
    assert "mock LLM" not in repr(outcome)

    class InvalidStore(_FakeStore):
        def record_attempt(
            self,
            *,
            attempt_number: int,
            context: BuiltContext,
            started_at: float,
        ) -> object:
            super().record_attempt(
                attempt_number=attempt_number,
                context=context,
                started_at=started_at,
            )
            return "not-none"

    invalid_store = InvalidStore()
    invalid, _, invalid_tool, _, _, _, _ = _make_loop(
        llm=MockLLM(
            (MockScriptStep(expected_latest_status=None, action=_tool_action("never:store")),)
        ),
        store=invalid_store,
    )
    assert invalid.run(task="reject bad store result").reason is stopping.StopReason.INVALID_OR_OUT_OF_SCOPE
    assert invalid_tool.actions == []

    invalid_clock = _FakeClock(value=10)  # type: ignore[arg-type]
    invalid, _, invalid_tool, _, _, _, _ = _make_loop(
        llm=MockLLM(
            (MockScriptStep(expected_latest_status=None, action=_tool_action("never:clock")),)
        ),
        clock=invalid_clock,
    )
    assert invalid.run(task="reject bad clock result").reason is stopping.StopReason.INVALID_OR_OUT_OF_SCOPE
    assert invalid_tool.actions == []


def _assert_result_routing() -> None:
    _, stopping, _ = _load_wp04_api()
    action = _tool_action("inspect:mismatch")
    bad_tool = _FakeTool(lambda _: _result("different:id"))
    agent, _, bad_tool, _, _, _, _ = _make_loop(
        llm=MockLLM((MockScriptStep(expected_latest_status=None, action=action),)),
        tool=bad_tool,
    )
    outcome = agent.run(task="reject mismatched result")
    assert outcome.reason is stopping.StopReason.INVALID_OR_OUT_OF_SCOPE
    assert outcome.attempts == ()
    assert bad_tool.actions == ["inspect:mismatch"]

    def assert_attempt_trees_are_independent(
        left: object,
        right: object,
    ) -> None:
        assert left is not right
        assert left.action is not right.action
        assert left.result is not right.result
        assert left.action.parameters is not right.action.parameters
        assert left.result.resource_counts is not right.result.resource_counts

    class CapturingLLM:
        def __init__(self, *, mutate_second_context: bool = False) -> None:
            self.contexts: list[BuiltContext] = []
            self.mutate_second_context = mutate_second_context
            self.actions = (
                _tool_action("history:first"),
                _proposal_action("history:plan"),
            )

        def complete(self, context: BuiltContext, /):
            self.contexts.append(context)
            if self.mutate_second_context and len(self.contexts) == 2:
                object.__setattr__(
                    context.attempts[0].action,
                    "action_id",
                    "history:llm-forged",
                )
                object.__setattr__(
                    context.attempts[0].result,
                    "summary",
                    "LLM-HISTORY-SECRET",
                )
            return self.actions[len(self.contexts) - 1]

    class MutatingStore(_FakeStore):
        def record_attempt(
            self,
            *,
            attempt_number: int,
            context: BuiltContext,
            started_at: float,
        ) -> None:
            if attempt_number == 2:
                object.__setattr__(
                    context.attempts[0].action,
                    "action_id",
                    "history:store-forged",
                )
                object.__setattr__(
                    context.attempts[0].result,
                    "summary",
                    "STORE-HISTORY-SECRET",
                )
            super().record_attempt(
                attempt_number=attempt_number,
                context=context,
                started_at=started_at,
            )

    store_attacker = MutatingStore()
    store_target_llm = CapturingLLM()
    store_target, _, _, _, _, _, _ = _make_loop(
        llm=store_target_llm,
        store=store_attacker,
    )
    store_outcome = store_target.run(task="isolate Store from canonical history")
    assert store_outcome.reason is stopping.StopReason.AWAITING_APPROVAL
    canonical_after_store = store_outcome.attempts[0]
    store_snapshot = store_attacker.context_objects[1].attempts[0]
    llm_after_store = store_target_llm.contexts[1].attempts[0]
    assert store_snapshot.action.action_id == "history:store-forged"
    assert store_snapshot.result.summary == "STORE-HISTORY-SECRET"
    assert canonical_after_store.action.action_id == "history:first"
    assert canonical_after_store.result.summary == "bounded result"
    assert llm_after_store.action.action_id == "history:first"
    assert llm_after_store.result.summary == "bounded result"
    assert store_attacker.context_objects[1] is not store_target_llm.contexts[1]
    assert_attempt_trees_are_independent(store_snapshot, llm_after_store)
    assert_attempt_trees_are_independent(store_snapshot, canonical_after_store)
    assert_attempt_trees_are_independent(llm_after_store, canonical_after_store)

    llm_attacker = CapturingLLM(mutate_second_context=True)
    llm_target_store = _FakeStore()
    llm_target, _, _, _, _, _, _ = _make_loop(
        llm=llm_attacker,
        store=llm_target_store,
    )
    llm_outcome = llm_target.run(task="isolate LLM from canonical history")
    assert llm_outcome.reason is stopping.StopReason.AWAITING_APPROVAL
    canonical_after_llm = llm_outcome.attempts[0]
    store_before_llm = llm_target_store.context_objects[1].attempts[0]
    llm_snapshot = llm_attacker.contexts[1].attempts[0]
    assert llm_snapshot.action.action_id == "history:llm-forged"
    assert llm_snapshot.result.summary == "LLM-HISTORY-SECRET"
    assert canonical_after_llm.action.action_id == "history:first"
    assert canonical_after_llm.result.summary == "bounded result"
    assert store_before_llm.action.action_id == "history:first"
    assert store_before_llm.result.summary == "bounded result"
    assert llm_target_store.context_objects[1] is not llm_attacker.contexts[1]
    assert_attempt_trees_are_independent(store_before_llm, llm_snapshot)
    assert_attempt_trees_are_independent(store_before_llm, canonical_after_llm)
    assert_attempt_trees_are_independent(llm_snapshot, canonical_after_llm)

    class MutatingPolicy(_FakePolicy):
        def allows(self, *, action: object) -> bool:
            allowed = super().allows(action=action)
            replacement = _read_file_action("policy:replacement", "../POLICY-BYPASS")
            object.__setattr__(action, "parameters", replacement.parameters)
            return allowed

    original = _read_file_action("snapshot:identity", "src/original.py")
    mutating_policy = MutatingPolicy()
    snapshot_tool = _FakeTool()
    isolated, _, snapshot_tool, _, _, _, _ = _make_loop(
        llm=MockLLM((MockScriptStep(expected_latest_status=None, action=original),)),
        policy=mutating_policy,
        tool=snapshot_tool,
        limits=_limits(stopping, rounds=2, tools=1, progress=2),
    )
    isolated_outcome = isolated.run(task="isolate the policy and tool snapshots")
    assert isolated_outcome.reason is stopping.StopReason.BUDGET_EXHAUSTED
    assert snapshot_tool.actions == ["snapshot:identity"]
    assert original is not mutating_policy.action_objects[0]
    assert mutating_policy.action_objects[0] is not snapshot_tool.action_objects[0]
    history_action = isolated_outcome.attempts[0].action
    assert original is not snapshot_tool.action_objects[0]
    assert original is not history_action
    assert history_action is not mutating_policy.action_objects[0]
    assert history_action is not snapshot_tool.action_objects[0]
    assert original.parameters is not mutating_policy.action_objects[0].parameters
    assert original.parameters is not snapshot_tool.action_objects[0].parameters
    assert original.parameters is not history_action.parameters
    assert (
        mutating_policy.action_objects[0].parameters
        is not snapshot_tool.action_objects[0].parameters
    )
    assert mutating_policy.action_objects[0].parameters is not history_action.parameters
    assert snapshot_tool.action_objects[0].parameters is not history_action.parameters
    assert snapshot_tool.action_objects[0].to_dict()["parameters"]["path"] == "src/original.py"

    forged_action = _read_file_action("snapshot:forged-action", "src/original.py")
    _forge_flat_parameters(
        forged_action,
        path=_StringSubclass("src/original.py"),
        max_bytes=_IntegerSubclass(1_024),
    )
    forged_action_tool = _FakeTool()
    invalid_action, _, forged_action_tool, _, _, _, _ = _make_loop(
        llm=MockLLM(
            (MockScriptStep(expected_latest_status=None, action=forged_action),)
        ),
        tool=forged_action_tool,
    )
    forged_action_outcome = invalid_action.run(task="reject forged action internals")
    assert forged_action_outcome.reason is stopping.StopReason.INVALID_OR_OUT_OF_SCOPE
    assert forged_action_outcome.tool_calls == 0
    assert forged_action_tool.actions == []

    forged_proposal = _proposal_action("snapshot:forged-proposal")
    object.__setattr__(
        forged_proposal,
        "action_id",
        _StringSubclass("snapshot:forged-proposal"),
    )
    proposal_tool = _FakeTool()
    invalid_proposal, proposal_policy, proposal_tool, _, _, _, _ = _make_loop(
        llm=MockLLM(
            (MockScriptStep(expected_latest_status=None, action=forged_proposal),)
        ),
        tool=proposal_tool,
    )
    proposal_outcome = invalid_proposal.run(task="reject forged proposal scalar")
    assert proposal_outcome.reason is stopping.StopReason.INVALID_OR_OUT_OF_SCOPE
    assert proposal_outcome.tool_calls == 0
    assert proposal_policy.actions == []
    assert proposal_tool.actions == []

    class RecordingLLM:
        def __init__(self) -> None:
            self.contexts: list[str] = []
            self.actions = (
                _tool_action("snapshot:forged-result"),
                _proposal_action("snapshot:after-forged-result"),
            )

        def complete(self, context: BuiltContext, /):
            self.contexts.append(context.to_json())
            return self.actions[len(self.contexts) - 1]

    forged_result = _result("snapshot:forged-result")
    object.__setattr__(forged_result, "summary", _StringSubclass("RESULT-SECRET"))
    object.__setattr__(forged_result, "output", _StringSubclass("OUTPUT-SECRET"))
    recording_llm = RecordingLLM()
    forged_result_tool = _FakeTool(lambda _action: forged_result)
    invalid_result, _, forged_result_tool, store, _, _, _ = _make_loop(
        llm=recording_llm,
        tool=forged_result_tool,
    )
    forged_result_outcome = invalid_result.run(task="reject forged result internals")
    assert forged_result_outcome.reason is stopping.StopReason.INVALID_OR_OUT_OF_SCOPE
    assert forged_result_tool.actions == ["snapshot:forged-result"]
    assert len(recording_llm.contexts) == 1
    observed_context = "|".join(recording_llm.contexts)
    stored_context = "|".join(record[1] for record in store.records)
    assert "RESULT-SECRET" not in observed_context + stored_context
    assert "OUTPUT-SECRET" not in observed_context + stored_context


def _assert_terminal_controls() -> None:
    _, stopping, _ = _load_wp04_api()
    expected_reasons = {
        "report_blocked": "BLOCKED",
        "stop_with_failure": "FAILED",
        "stop_without_safe_action": "CANCELLED",
    }
    observed: set[str] = set()
    for action_type, expected_reason in expected_reasons.items():
        action = _terminal_control_action(f"stop:{action_type}", action_type)
        agent, _, tool, store, clock, _, _ = _make_loop(
            llm=MockLLM((MockScriptStep(expected_latest_status=None, action=action),))
        )
        outcome = agent.run(task=f"handle {action_type}")
        assert outcome.reason.value == expected_reason
        observed.add(outcome.reason.value)
        assert outcome.reason is not stopping.StopReason.INVALID_OR_OUT_OF_SCOPE
        assert outcome.rounds == 1
        assert outcome.tool_calls == 0
        assert tool.actions == []
        assert len(store.records) == 1
        assert clock.calls == 1
        assert outcome.trace.count("llm:1") == 1
        assert outcome.trace[-1] == f"stop:{expected_reason}"
        assert "SAFE_STOP" not in "|".join(outcome.trace)
    assert observed == {"BLOCKED", "FAILED", "CANCELLED"}


def _assert_stop_priority() -> None:
    _, stopping, _ = _load_wp04_api()
    limits = _limits(stopping, rounds=1, tools=1, progress=1)
    evaluate = stopping.StopController().evaluate

    def decision(**overrides: object):
        values = {
            "invalid_or_out_of_scope": False,
            "awaiting_approval": False,
            "completed": False,
            "rounds": 0,
            "tool_calls": 0,
            "no_progress_count": 0,
        }
        values.update(overrides)
        return evaluate(state=stopping.StopInputs(**values), limits=limits)

    assert decision(
        invalid_or_out_of_scope=True,
        awaiting_approval=True,
        completed=True,
        rounds=1,
        no_progress_count=1,
    ).reason is stopping.StopReason.INVALID_OR_OUT_OF_SCOPE
    assert decision(
        awaiting_approval=True,
        completed=True,
        rounds=1,
        no_progress_count=1,
    ).reason is stopping.StopReason.AWAITING_APPROVAL
    assert decision(completed=True, rounds=1, no_progress_count=1).reason is stopping.StopReason.COMPLETED
    assert decision(rounds=1, no_progress_count=1).reason is stopping.StopReason.BUDGET_EXHAUSTED
    assert decision(no_progress_count=1).reason is stopping.StopReason.NO_PROGRESS
    assert decision().reason is stopping.StopReason.CONTINUE


def _assert_budget_gate() -> None:
    _, stopping, _ = _load_wp04_api()
    for field in ("max_rounds", "max_tool_calls", "no_progress_limit"):
        values = {"max_rounds": 2, "max_tool_calls": 2, "no_progress_limit": 2}
        for invalid in (False, 0, -1):
            values[field] = invalid
            with pytest.raises(ValueError):
                stopping.StopLimits(**values)
        values[field] = 2

    class IntSubclass(int):
        pass

    with pytest.raises(ValueError):
        stopping.StopLimits(max_rounds=IntSubclass(2), max_tool_calls=2, no_progress_limit=2)

    actions = tuple(
        MockScriptStep(expected_latest_status=None, action=_tool_action(f"inspect:{index}"))
        for index in range(3)
    )
    tool = _FakeTool()
    agent, _, tool, _, _, _, _ = _make_loop(
        llm=MockLLM(actions),
        tool=tool,
        limits=_limits(stopping, rounds=3, tools=1, progress=3),
    )
    outcome = agent.run(task="bounded tools")
    assert outcome.reason is stopping.StopReason.BUDGET_EXHAUSTED
    assert outcome.tool_calls == 1
    assert tool.actions == ["inspect:0"]


def _assert_no_progress_contract() -> None:
    _, stopping, _ = _load_wp04_api()
    first = parse_action(
        _raw_action(
            "plan:a",
            "propose_plan",
            {"proposal": {"z": ["秘密"], "a": {"x": 1}}},
        )
    )
    second = parse_action(
        _raw_action(
            "plan:b",
            "propose_plan",
            {"proposal": {"a": {"x": 9}, "z": ["不同秘密"]}},
        )
    )
    state = stopping.ProgressState(
        acceptance_version=0,
        budget_version=0,
        approval_version=0,
    )
    left = stopping.observation_signature(
        action=first,
        result_status=ToolResultStatus.FAILED,
        failure_code=stopping.FailureCode.TOOL_FAILED,
        stop_signal=None,
        progress_state=state,
    )
    right = stopping.observation_signature(
        action=second,
        result_status=ToolResultStatus.FAILED,
        failure_code=stopping.FailureCode.TOOL_FAILED,
        stop_signal=None,
        progress_state=state,
    )
    assert left == right
    assert "秘密" not in left
    assert left == left.encode("utf-8").decode("utf-8")
    assert math.isfinite(float(len(left)))

    read_a = _read_file_action("read:a", "src/a.py")
    read_a_reordered = _read_file_action(
        "read:a-reordered",
        "src/a.py",
        reverse_keys=True,
    )
    read_b = _read_file_action("read:b", "src/b.py")

    def tool_signature(action: ToolAction) -> str:
        return stopping.observation_signature(
            action=action,
            result_status=ToolResultStatus.FAILED,
            failure_code=stopping.FailureCode.TOOL_FAILED,
            stop_signal=None,
            progress_state=state,
        )

    signature_a = tool_signature(read_a)
    signature_a_reordered = tool_signature(read_a_reordered)
    signature_b = tool_signature(read_b)
    assert signature_a == signature_a_reordered
    assert signature_a != signature_b
    assert "src/a.py" in signature_a
    assert len(signature_a.encode("utf-8")) <= 65_536

    progress = stopping.advance_no_progress(
        previous=None,
        signature=signature_a,
        state=state,
    )
    progress = stopping.advance_no_progress(
        previous=progress,
        signature=signature_a_reordered,
        state=state,
    )
    assert progress.count == 2
    changed_action = stopping.advance_no_progress(
        previous=progress,
        signature=signature_b,
        state=state,
    )
    assert changed_action.count == 1

    secret_left = tool_signature(_search_action("search:a", "TOKEN-ONE"))
    secret_right = tool_signature(_search_action("search:b", "TOKEN-TWO"))
    assert secret_left == secret_right
    assert "TOKEN-ONE" not in secret_left
    assert "TOKEN-TWO" not in secret_right
    assert "<redacted>" in secret_left

    with pytest.raises(ValueError):
        tool_signature(_tool_action("write:not-signable", "create_file"))

    invalid_read = _raw_action(
        "read:unknown-field",
        "read_file",
        {
            "path": "src/a.py",
            "start_byte": 0,
            "max_bytes": 1_024,
            "unknown": "must fail closed",
        },
    )
    with pytest.raises(ActionParseError):
        parse_action(invalid_read)

    record = stopping.advance_no_progress(previous=None, signature=left, state=state)
    record = stopping.advance_no_progress(previous=record, signature=right, state=state)
    assert record.count == 2
    for changed_state in (
        stopping.ProgressState(acceptance_version=1, budget_version=0, approval_version=0),
        stopping.ProgressState(acceptance_version=0, budget_version=1, approval_version=0),
        stopping.ProgressState(acceptance_version=0, budget_version=0, approval_version=1),
    ):
        reset = stopping.advance_no_progress(
            previous=record,
            signature=right,
            state=changed_state,
        )
        assert reset.count == 1

    actions = (
        MockScriptStep(expected_latest_status=None, action=_tool_action("repeat:1")),
        MockScriptStep(
            expected_latest_status=ToolResultStatus.FAILED,
            action=_tool_action("repeat:2"),
        ),
    )
    tool = _FakeTool(
        lambda action: _result(action.action_id, ToolResultStatus.FAILED)
    )
    agent, _, tool, _, _, _, _ = _make_loop(
        llm=MockLLM(actions),
        tool=tool,
        limits=_limits(stopping, rounds=4, tools=4, progress=2),
    )
    outcome = agent.run(task="stop after repeated observations")
    assert outcome.reason is stopping.StopReason.NO_PROGRESS
    assert outcome.rounds == 2
    assert tool.actions == ["repeat:1", "repeat:2"]


def _assert_sensitive_exception_hygiene() -> None:
    _, stopping, _ = _load_wp04_api()
    secret = "SECRET-\ud800"
    with pytest.raises(ValueError) as task_error:
        ContextBuilder.build(task=secret, history=(), max_bytes=1_024)
    assert str(task_error.value) == "task must be non-empty UTF-8 text without NUL"
    assert task_error.value.__cause__ is None
    assert task_error.value.__context__ is None
    assert "SECRET" not in str(task_error.value)

    forged_path = _read_file_action("exception:forged-path", "src/safe.py")
    _forge_flat_parameters(forged_path, path=secret)
    state = stopping.ProgressState(
        acceptance_version=0,
        budget_version=0,
        approval_version=0,
    )
    with pytest.raises(ValueError) as path_error:
        stopping.observation_signature(
            action=forged_path,
            result_status=ToolResultStatus.FAILED,
            failure_code=stopping.FailureCode.TOOL_FAILED,
            stop_signal=None,
            progress_state=state,
        )
    assert str(path_error.value) == "observation could not be normalized"
    assert path_error.value.__cause__ is None
    assert path_error.value.__context__ is None
    assert "SECRET" not in str(path_error.value)


def _assert_offline_determinism(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LLM_PROVIDER"):
        monkeypatch.delenv(name, raising=False)

    def execute_once():
        llm = MockLLM(
            (
                MockScriptStep(expected_latest_status=None, action=_tool_action("inspect:stable")),
                MockScriptStep(
                    expected_latest_status=ToolResultStatus.SUCCEEDED,
                    action=_proposal_action("plan:stable"),
                ),
            )
        )
        agent, _, _, _, _, _, _ = _make_loop(llm=llm)
        return agent.run(task="deterministic")

    left = execute_once()
    right = execute_once()
    assert left == right
    assert left.reason.value == "AWAITING_APPROVAL"


def test_loop_order() -> None:
    _assert_loop_cycle()


def test_investigation_read_only() -> None:
    _assert_investigation_plan_contract()
    _assert_investigation_path_gate()


def test_attempt_persisted_before_call() -> None:
    _assert_attempt_persistence()


def test_complete_stops() -> None:
    _assert_stop_priority()


def test_waiting_stops() -> None:
    _assert_investigation_plan_contract()


def test_blocked_failed_cancelled_stop() -> None:
    _assert_terminal_controls()


def test_loop_limit() -> None:
    _assert_budget_gate()


def test_repeated_failure() -> None:
    _assert_no_progress_contract()
    _assert_sensitive_exception_hygiene()


def test_no_progress() -> None:
    _assert_no_progress_contract()


@pytest.mark.parametrize("pv_id", WP04_OWNER_PVS, ids=WP04_OWNER_PVS)
def test_spec_requirement(pv_id: str, monkeypatch: pytest.MonkeyPatch) -> None:
    assertions: dict[str, Callable[[], None]] = {
        "PV-AGT-001": _assert_loop_cycle,
        "PV-AGT-002": _assert_llm_adapter_boundary,
        "PV-AGT-006": lambda: (_assert_loop_cycle(), _assert_result_routing()),
        "PV-AGT-008": lambda: (
            _assert_loop_cycle(),
            _assert_investigation_plan_contract(),
            _assert_investigation_path_gate(),
            _assert_stop_priority(),
        ),
        "PV-AGT-010": lambda: (_assert_attempt_persistence(), _assert_budget_gate()),
        "PV-AGT-011": lambda: (
            _assert_stop_priority(),
            _assert_terminal_controls(),
            _assert_no_progress_contract(),
            _assert_sensitive_exception_hygiene(),
        ),
        "PV-TST-001": lambda: _assert_offline_determinism(monkeypatch),
    }
    assertions[pv_id]()
