from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Final

import pytest

from coding_harness.agent.context import ContextBuilder
from coding_harness.agent.mock_llm import MockLLM
from coding_harness.domain.policy import PolicyEngine
from coding_harness.transaction.apply import ApplyCoordinator
from coding_harness.transaction.journal import ApplyJournal


ROOT: Final = Path(__file__).resolve().parents[2]


def _load(name: str) -> ModuleType:
    path = ROOT / "examples" / f"{name}.py"
    assert path.is_file(), f"EXPECTED_ARTIFACT_MISSING: {path.relative_to(ROOT)}"
    spec = importlib.util.spec_from_file_location(f"course_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_governance_demo_uses_policy_engine_and_denies_execution() -> None:
    module = _load("governance_demo")
    assert module.PolicyEngine is PolicyEngine
    assert module.run_demo() == {
        "scenario": "governance_rejection",
        "decision": "DENY",
        "executor_calls": 0,
    }


def test_feedback_demo_uses_mock_llm_and_context_builder() -> None:
    module = _load("feedback_demo")
    assert module.MockLLM is MockLLM
    assert module.ContextBuilder is ContextBuilder
    assert module.run_demo() == {
        "scenario": "feedback_loop",
        "failure_observed": True,
        "action_changed": True,
    }


def test_recovery_demo_uses_apply_coordinator_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load("recovery_demo")
    assert module.ApplyCoordinator is ApplyCoordinator
    assert module.ApplyJournal is ApplyJournal

    def reject_permission_fault_injection(*args: object, **kwargs: object) -> None:
        raise AssertionError("recovery demo must not depend on chmod")

    monkeypatch.setattr(Path, "chmod", reject_permission_fault_injection)
    result = module.run_demo()
    assert result == {
        "scenario": "recovery_rollback",
        "result": "RECOVERY_REQUIRED",
        "partial_effect": False,
    }
