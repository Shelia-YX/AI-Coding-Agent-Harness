from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Final

import pytest


ROOT: Final = Path(__file__).resolve().parents[2]
README: Final = ROOT / "README.md"
CI_CONFIG: Final = ROOT / ".gitlab-ci.yml"
REFLECTION: Final = ROOT / "REFLECTION.md"
PROCESS: Final = ROOT / "SPEC_PROCESS.md"


def _load_example(relative_path: str) -> ModuleType:
    path = ROOT / relative_path
    assert path.is_file(), f"EXPECTED_ARTIFACT_MISSING: {relative_path}"
    module_name = "finalization_" + path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_readme_documents_course_execution_and_deferred_scope() -> None:
    assert README.is_file(), "EXPECTED_DOCUMENTATION_MISSING: README.md"
    text = README.read_text(encoding="utf-8")
    required = (
        "Python 3.12",
        "pytest tests/finalization",
        "pytest tests/demos",
        "Threat Model",
        "Deferred Scope",
        "Recovery",
        "Uninstall",
    )
    assert all(item in text for item in required)


def test_ci_has_offline_unit_test_job_without_external_authority() -> None:
    assert CI_CONFIG.is_file(), "EXPECTED_ARTIFACT_MISSING: .gitlab-ci.yml"
    text = CI_CONFIG.read_text(encoding="utf-8")
    assert "\nunit-test:\n" in "\n" + text
    assert "pytest" in text
    assert "PYTHONDONTWRITEBYTECODE" in text
    forbidden = ("API_KEY", "docker ", "curl ", "wget ", "services:")
    assert not any(item in text for item in forbidden)


def test_reflection_contains_final_course_closeout() -> None:
    text = REFLECTION.read_text(encoding="utf-8")
    required = (
        "# 项目最终反思",
        "TDD",
        "worktree",
        "authority boundary",
        "scope reduction",
    )
    assert all(item in text for item in required), (
        "EXPECTED_DOCUMENTATION_MISSING: final reflection"
    )


def test_scope_deviation_record_is_explicit() -> None:
    text = PROCESS.read_text(encoding="utf-8")
    required = (
        "Project Finalization Scope Decision",
        "Evidence-first Course Closeout",
        "WP-23 API",
        "WP-24 SSE",
        "WP-25 WebUI",
        "SPEC.md",
        "PLAN.md",
        "APPROVED_FOR_RED",
    )
    assert all(item in text for item in required)


@pytest.mark.parametrize(
    ("relative_path", "expected"),
    (
        (
            "examples/governance_demo.py",
            {
                "scenario": "governance_rejection",
                "decision": "DENY",
                "executor_calls": 0,
            },
        ),
        (
            "examples/feedback_demo.py",
            {
                "scenario": "feedback_loop",
                "failure_observed": True,
                "action_changed": True,
            },
        ),
        (
            "examples/recovery_demo.py",
            {
                "scenario": "recovery_rollback",
                "result": "RECOVERY_REQUIRED",
                "partial_effect": False,
            },
        ),
    ),
)
def test_deterministic_example_contract(
    relative_path: str,
    expected: dict[str, object],
) -> None:
    module = _load_example(relative_path)
    runner = getattr(module, "run_demo", None)
    assert callable(runner), f"EXPECTED_INTERFACE_MISSING: {relative_path}:run_demo"
    assert runner() == expected
