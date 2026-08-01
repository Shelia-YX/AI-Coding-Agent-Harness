from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Final

import pytest
import yaml


ROOT: Final = Path(__file__).resolve().parents[2]
README: Final = ROOT / "README.md"
CI_CONFIG: Final = ROOT / ".gitlab-ci.yml"
GITHUB_ACTIONS_CONFIG: Final = ROOT / ".github" / "workflows" / "unit-test.yml"
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


def test_github_actions_runs_full_offline_suite() -> None:
    assert GITHUB_ACTIONS_CONFIG.is_file(), "EXPECTED_GITHUB_ACTIONS_MISSING"
    text = GITHUB_ACTIONS_CONFIG.read_text(encoding="utf-8")
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    assert isinstance(workflow, dict)
    assert workflow["name"] == "unit-test"

    triggers = workflow["on"]
    assert isinstance(triggers, dict)
    assert triggers["push"]["branches"] == [
        "main",
        "project-finalization-course-submission",
    ]
    assert triggers["pull_request"]["branches"] == ["main"]
    assert "workflow_dispatch" in triggers
    assert "pull_request_target" not in triggers
    assert workflow["permissions"] == {"contents": "read"}

    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    assert set(jobs) == {"unit-test"}
    job = jobs["unit-test"]
    assert job["runs-on"] == "ubuntu-latest"
    assert int(job["timeout-minutes"]) <= 30
    assert job["env"] == {"PYTHONDONTWRITEBYTECODE": "1"}
    assert "services" not in job

    steps = job["steps"]
    checkout = next(step for step in steps if step.get("uses") == "actions/checkout@v6")
    setup = next(step for step in steps if step.get("uses") == "actions/setup-python@v5")
    assert checkout == {"name": "Check out repository", "uses": "actions/checkout@v6"}
    assert setup["with"] == {"python-version": "3.12"}

    install = next(step for step in steps if step.get("name") == "Install dependencies")
    install_lines = [line.strip() for line in install["run"].splitlines() if line.strip()]
    assert install_lines == [
        "set -euo pipefail",
        'source_dir="$(mktemp -d "$RUNNER_TEMP/coding-harness-source.XXXXXX")"',
        'git archive --format=tar HEAD | tar -xf - -C "$source_dir"',
        'python -m pip install "$source_dir"',
        "python -m pip install pytest PyYAML",
    ]

    test_step = next(step for step in steps if step.get("name") == "Run full test suite")
    assert test_step["run"].strip() == "python -m pytest -p no:cacheprovider -q"

    used_actions = {step.get("uses") for step in steps if "uses" in step}
    assert used_actions == {"actions/checkout@v6", "actions/setup-python@v5"}


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
