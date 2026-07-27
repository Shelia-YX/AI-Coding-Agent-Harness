"""WP-12 Synthetic Baseline Anchor and Synthetic Git conformance tests.

The suite consumes only the approved test-only conformance fixture. Production
constructor, factory, request, enum, result, exception, storage, and output
representations are deliberately outside this contract.

The fixture must delegate acquisition and invocation to the real WP-12
boundaries. The test-owned observations below are non-authoritative normalized
facts; direct filesystem and origin-repository assertions remain outside the
fixture.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Protocol

import pytest

from coding_harness.workspace.manifest import BaselineManifest, build_baseline
from coding_harness.workspace.materialize import TaskWorkspace, materialize_workspace
from coding_harness.workspace.synthetic_git import (
    GitOperation,
    SyntheticGit,
    SyntheticGitAcquisition,
    SyntheticGitDisposition,
    SyntheticGitFeedback,
    SyntheticGitResult,
    acquire_synthetic_git,
)


class Disposition(Enum):
    """Test-only normalization of a real production boundary outcome."""

    ACCEPTED = auto()
    REJECTED = auto()
    INTERNAL_FAILURE = auto()


class SemanticOperation(Enum):
    """Test semantics; these values do not represent production operations."""

    STATUS = auto()
    DIFF = auto()
    CACHED_DIFF = auto()
    STAGE = auto()
    UNSTAGE = auto()
    COMMIT = auto()
    BRANCH = auto()
    TAG = auto()
    REMOTE = auto()
    MERGE = auto()
    RESET = auto()
    CHECKOUT = auto()
    RESTORE_WORKTREE = auto()
    REBASE = auto()
    FILTER_BRANCH = auto()
    CHERRY_PICK = auto()
    CLEAN = auto()
    REFS_MUTATION = auto()
    CONFIG = auto()


_ALLOWED_OPERATION_CASES = (
    SemanticOperation.STATUS,
    SemanticOperation.DIFF,
    SemanticOperation.CACHED_DIFF,
    SemanticOperation.STAGE,
    SemanticOperation.UNSTAGE,
)
_ALLOWED_OPERATIONS = frozenset(_ALLOWED_OPERATION_CASES)

_FORBIDDEN_OPERATIONS = (
    SemanticOperation.TAG,
    SemanticOperation.MERGE,
    SemanticOperation.RESET,
    SemanticOperation.CHECKOUT,
    SemanticOperation.RESTORE_WORKTREE,
    SemanticOperation.REBASE,
    SemanticOperation.FILTER_BRANCH,
    SemanticOperation.CHERRY_PICK,
    SemanticOperation.REFS_MUTATION,
)

_OPERATION_TRANSLATION = {
    SemanticOperation.STATUS: GitOperation.STATUS,
    SemanticOperation.DIFF: GitOperation.DIFF,
    SemanticOperation.CACHED_DIFF: GitOperation.CACHED_DIFF,
    SemanticOperation.STAGE: GitOperation.STAGE,
    SemanticOperation.UNSTAGE: GitOperation.UNSTAGE,
}

_PRODUCTION_CAPABILITIES = (
    GitOperation.STATUS,
    GitOperation.DIFF,
    GitOperation.CACHED_DIFF,
    GitOperation.STAGE,
    GitOperation.UNSTAGE,
)

_DISPOSITION_TRANSLATION = {
    SyntheticGitDisposition.ACCEPTED: Disposition.ACCEPTED,
    SyntheticGitDisposition.REJECTED: Disposition.REJECTED,
    SyntheticGitDisposition.INTERNAL_FAILURE: Disposition.INTERNAL_FAILURE,
}


@dataclass(frozen=True, slots=True)
class CompatibilityFeedback:
    """Test-only semantic facts derived from real compatibility feedback."""

    paths: frozenset[str] = frozenset()
    added_lines: frozenset[str] = frozenset()
    removed_lines: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ConformanceObservation:
    """Non-authoritative normalization returned by the test-only binding."""

    disposition: Disposition
    context: object | None = None
    feedback: CompatibilityFeedback = CompatibilityFeedback()


@dataclass(frozen=True, slots=True)
class OperationProbe:
    """A semantic probe, not a production request or serialized Git command."""

    operation: SemanticOperation
    paths: tuple[str, ...] = ()
    options: tuple[str, ...] = ()


class SyntheticGitConformance(Protocol):
    """Approved test-only behavioral conformance surface."""

    def acquire(
        self,
        baseline: object,
        workspace: TaskWorkspace,
    ) -> ConformanceObservation:
        """Delegate to the real WP-12 context acquisition boundary."""

    def operation_capabilities(self) -> frozenset[SemanticOperation]:
        """Return the exhaustive public production semantic capabilities."""

    def invoke(
        self,
        context: object,
        probe: OperationProbe,
    ) -> ConformanceObservation:
        """Delegate the semantic probe to the real SyntheticGit.run boundary."""


def _normalize_feedback(
    feedback: SyntheticGitFeedback,
) -> CompatibilityFeedback:
    return CompatibilityFeedback(
        paths=feedback.paths,
        added_lines=feedback.added_lines,
        removed_lines=feedback.removed_lines,
    )


def _normalize_acquisition(
    outcome: SyntheticGitAcquisition,
) -> ConformanceObservation:
    return ConformanceObservation(
        disposition=_DISPOSITION_TRANSLATION[outcome.disposition],
        context=outcome.context,
        feedback=_normalize_feedback(outcome.feedback),
    )


def _normalize_result(outcome: SyntheticGitResult) -> ConformanceObservation:
    return ConformanceObservation(
        disposition=_DISPOSITION_TRANSLATION[outcome.disposition],
        feedback=_normalize_feedback(outcome.feedback),
    )


class _StaticWP12Conformance:
    """Static translation to the real WP-12 production boundaries."""

    def acquire(
        self,
        baseline: object,
        workspace: TaskWorkspace,
    ) -> ConformanceObservation:
        return _normalize_acquisition(
            acquire_synthetic_git(baseline, workspace),
        )

    def operation_capabilities(self) -> frozenset[SemanticOperation]:
        if SyntheticGit.operation_capabilities() != _PRODUCTION_CAPABILITIES:
            pytest.fail(
                "BINDING_NOT_READY: production capability catalog mismatch",
                pytrace=False,
            )
        return frozenset(_OPERATION_TRANSLATION)

    def invoke(
        self,
        context: object,
        probe: OperationProbe,
    ) -> ConformanceObservation:
        production_operation: object = _OPERATION_TRANSLATION.get(
            probe.operation,
            probe.operation,
        )
        return _normalize_result(
            SyntheticGit.run(
                context,
                production_operation,
                paths=probe.paths,
                options=probe.options,
            ),
        )


@pytest.fixture
def wp12_synthetic_git_conformance() -> SyntheticGitConformance:
    """Stable test locator statically wired to real WP-12 production."""

    return _StaticWP12Conformance()


@dataclass(frozen=True, slots=True)
class _Scenario:
    origin: Path
    baseline: BaselineManifest
    workspace: TaskWorkspace


def _git(repo: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    git_home = repo.parent / f".{repo.name}-git-test-home"
    git_home.mkdir(exist_ok=True)
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "HOME": str(git_home),
            "LC_ALL": "C",
        }
    )
    return subprocess.run(
        ["git", *arguments],
        cwd=repo,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def _repository(parent: Path, name: str = "origin") -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    root = parent / name
    root.mkdir()
    (root / "directory").mkdir()
    (root / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    (root / "other.txt").write_text("other baseline\n", encoding="utf-8")
    (root / "directory" / "nested.txt").write_text(
        "nested\n",
        encoding="utf-8",
    )
    _git(root, "init", "-q")
    _git(
        root,
        "add",
        "--",
        "tracked.txt",
        "other.txt",
        "directory/nested.txt",
    )
    _git(
        root,
        "-c",
        "user.name=WP12 Test",
        "-c",
        "user.email=wp12@example.invalid",
        "commit",
        "-q",
        "-m",
        "fixture baseline",
    )
    return root


def _scenario(tmp_path: Path, name: str = "case") -> _Scenario:
    case_root = tmp_path / name
    origin = _repository(case_root)
    baseline = build_baseline(origin)
    workspace = materialize_workspace(baseline, case_root / "workspace")
    return _Scenario(origin, baseline, workspace)


def _origin_state(origin: Path) -> tuple[str, str, str, bytes]:
    git_dir = Path(_git(origin, "rev-parse", "--git-dir").stdout.strip())
    if not git_dir.is_absolute():
        git_dir = origin / git_dir
    return (
        _git(origin, "status", "--porcelain=v1", "--untracked-files=all").stdout,
        _git(origin, "rev-parse", "HEAD").stdout,
        _git(origin, "branch", "--show-current").stdout,
        (git_dir / "index").read_bytes(),
    )


def _workspace_files(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.parts
    }


def _baseline_facts(
    baseline: BaselineManifest,
) -> tuple[str, tuple[tuple[str, bytes], ...]]:
    return (
        baseline.digest,
        tuple(
            (entry.path.canonical, entry.content)
            for entry in baseline.entries
        ),
    )


def _accepted_context(
    binding: SyntheticGitConformance,
    scenario: _Scenario,
) -> object:
    observation = binding.acquire(scenario.baseline, scenario.workspace)
    assert observation.disposition is Disposition.ACCEPTED
    assert observation.context is not None
    return observation.context


def _accepted_feedback(
    binding: SyntheticGitConformance,
    context: object,
    probe: OperationProbe,
) -> CompatibilityFeedback:
    observation = binding.invoke(context, probe)
    assert observation.disposition is Disposition.ACCEPTED
    return observation.feedback


def _assert_accepted(
    binding: SyntheticGitConformance,
    context: object,
    probe: OperationProbe,
) -> None:
    observation = binding.invoke(context, probe)
    assert observation.disposition is Disposition.ACCEPTED


def _compatibility_state(
    binding: SyntheticGitConformance,
    context: object,
) -> tuple[CompatibilityFeedback, CompatibilityFeedback, CompatibilityFeedback]:
    return (
        _accepted_feedback(
            binding,
            context,
            OperationProbe(SemanticOperation.STATUS),
        ),
        _accepted_feedback(
            binding,
            context,
            OperationProbe(SemanticOperation.DIFF),
        ),
        _accepted_feedback(
            binding,
            context,
            OperationProbe(SemanticOperation.CACHED_DIFF),
        ),
    )


def _assert_rejected_without_side_effect(
    binding: SyntheticGitConformance,
    scenario: _Scenario,
    context: object,
    probe: OperationProbe,
) -> None:
    origin_before = _origin_state(scenario.origin)
    workspace_before = _workspace_files(scenario.workspace.root)
    compatibility_before = _compatibility_state(binding, context)

    observation = binding.invoke(context, probe)

    assert observation.disposition is Disposition.REJECTED
    assert _origin_state(scenario.origin) == origin_before
    assert _workspace_files(scenario.workspace.root) == workspace_before
    assert _compatibility_state(binding, context) == compatibility_before


def test_verified_wp10_binding_acquires_non_mutating_compatibility_context(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
) -> None:
    scenario = _scenario(tmp_path)
    origin_before = _origin_state(scenario.origin)
    baseline_before = _baseline_facts(scenario.baseline)
    workspace_before = _workspace_files(scenario.workspace.root)

    context = _accepted_context(wp12_synthetic_git_conformance, scenario)

    assert _origin_state(scenario.origin) == origin_before
    assert _baseline_facts(scenario.baseline) == baseline_before
    assert _workspace_files(scenario.workspace.root) == workspace_before
    _assert_accepted(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.STATUS),
    )


def test_workspace_snapshot_rejected_as_anchor_provenance(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
) -> None:
    scenario = _scenario(tmp_path)
    snapshot = _workspace_files(scenario.workspace.root)
    origin_before = _origin_state(scenario.origin)
    workspace_before = _workspace_files(scenario.workspace.root)

    observation = wp12_synthetic_git_conformance.acquire(
        snapshot,
        scenario.workspace,
    )

    assert observation.disposition is Disposition.REJECTED
    assert observation.context is None
    assert _origin_state(scenario.origin) == origin_before
    assert _workspace_files(scenario.workspace.root) == workspace_before


def test_workspace_binding_mismatch_rejected(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
) -> None:
    first = _scenario(tmp_path, "first")
    second_root = tmp_path / "second"
    second_origin = _repository(second_root)
    (second_origin / "tracked.txt").write_text(
        "different WP10 baseline\n",
        encoding="utf-8",
    )
    second_baseline = build_baseline(second_origin)
    second = _Scenario(
        origin=second_origin,
        baseline=second_baseline,
        workspace=materialize_workspace(
            second_baseline,
            second_root / "workspace",
        ),
    )
    first_origin_before = _origin_state(first.origin)
    second_origin_before = _origin_state(second.origin)
    second_workspace_before = _workspace_files(second.workspace.root)

    assert first.baseline.digest != second.workspace.baseline_digest
    observation = wp12_synthetic_git_conformance.acquire(
        first.baseline,
        second.workspace,
    )

    assert observation.disposition is Disposition.REJECTED
    assert observation.context is None
    assert _origin_state(first.origin) == first_origin_before
    assert _origin_state(second.origin) == second_origin_before
    assert _workspace_files(second.workspace.root) == second_workspace_before


def test_stage_and_unstage_do_not_mutate_anchor(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)
    origin_before = _origin_state(scenario.origin)
    tracked = scenario.workspace.root / "tracked.txt"
    tracked.write_text("staged version\n", encoding="utf-8")

    _assert_accepted(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.STAGE, paths=("tracked.txt",)),
    )
    cached = _accepted_feedback(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.CACHED_DIFF),
    )
    tracked.write_text("worktree version\n", encoding="utf-8")
    _assert_accepted(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.UNSTAGE, paths=("tracked.txt",)),
    )
    worktree = _accepted_feedback(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.DIFF),
    )

    assert "baseline" in cached.removed_lines
    assert "staged version" in cached.added_lines
    assert "baseline" in worktree.removed_lines
    assert "worktree version" in worktree.added_lines
    assert _origin_state(scenario.origin) == origin_before


def test_unstage_does_not_restore_worktree(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)
    origin_before = _origin_state(scenario.origin)
    tracked = scenario.workspace.root / "tracked.txt"
    tracked.write_text("agent change\n", encoding="utf-8")
    _assert_accepted(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.STAGE, paths=("tracked.txt",)),
    )

    _assert_accepted(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.UNSTAGE, paths=("tracked.txt",)),
    )

    assert tracked.read_text(encoding="utf-8") == "agent change\n"
    assert (
        _accepted_feedback(
            wp12_synthetic_git_conformance,
            context,
            OperationProbe(SemanticOperation.CACHED_DIFF),
        ).paths
        == frozenset()
    )
    assert "tracked.txt" in _accepted_feedback(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.DIFF),
    ).paths
    assert _origin_state(scenario.origin) == origin_before


def test_index_and_anchor_are_behaviorally_separate(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)
    origin_before = _origin_state(scenario.origin)
    tracked = scenario.workspace.root / "tracked.txt"
    tracked.write_text("index version\n", encoding="utf-8")
    _assert_accepted(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.STAGE, paths=("tracked.txt",)),
    )
    tracked.write_text("worktree version\n", encoding="utf-8")

    cached = _accepted_feedback(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.CACHED_DIFF),
    )
    worktree = _accepted_feedback(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.DIFF),
    )

    assert "index version" in cached.added_lines
    assert "worktree version" not in cached.added_lines
    assert "index version" in worktree.removed_lines
    assert "worktree version" in worktree.added_lines
    assert _origin_state(scenario.origin) == origin_before


def test_sanitized_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
) -> None:
    scenario = _scenario(tmp_path)
    origin_before = _origin_state(scenario.origin)
    hostile_home = tmp_path / "hostile-home"
    hostile_home.mkdir()
    (hostile_home / ".gitconfig").write_text(
        "[core]\n\tbare = true\n[alias]\n\tstatus = !false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HOME", str(hostile_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(hostile_home))
    monkeypatch.setenv("GIT_DIR", str(scenario.origin / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(scenario.origin))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.bare")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")

    context = _accepted_context(wp12_synthetic_git_conformance, scenario)
    _assert_accepted(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.STATUS),
    )

    assert _origin_state(scenario.origin) == origin_before


def test_exact_allowlist(
    wp12_synthetic_git_conformance: SyntheticGitConformance,
) -> None:
    assert (
        wp12_synthetic_git_conformance.operation_capabilities()
        == _ALLOWED_OPERATIONS
    )


@pytest.mark.parametrize("operation", _ALLOWED_OPERATION_CASES)
def test_allowed_operations_are_observable(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
    operation: SemanticOperation,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)
    origin_before = _origin_state(scenario.origin)
    (scenario.workspace.root / "tracked.txt").write_text(
        "agent change\n",
        encoding="utf-8",
    )
    paths = (
        ("tracked.txt",)
        if operation in {SemanticOperation.STAGE, SemanticOperation.UNSTAGE}
        else ()
    )

    _assert_accepted(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(operation, paths=paths),
    )
    assert _origin_state(scenario.origin) == origin_before


@pytest.mark.parametrize("operation", _FORBIDDEN_OPERATIONS)
def test_forbidden_operations_are_rejected_without_side_effect(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
    operation: SemanticOperation,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)

    _assert_rejected_without_side_effect(
        wp12_synthetic_git_conformance,
        scenario,
        context,
        OperationProbe(operation),
    )


def test_commit_branch_remote_clean_rejected(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)

    for operation in (
        SemanticOperation.COMMIT,
        SemanticOperation.BRANCH,
        SemanticOperation.REMOTE,
        SemanticOperation.CLEAN,
    ):
        _assert_rejected_without_side_effect(
            wp12_synthetic_git_conformance,
            scenario,
            context,
            OperationProbe(operation),
        )


def test_config_rejected(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)

    _assert_rejected_without_side_effect(
        wp12_synthetic_git_conformance,
        scenario,
        context,
        OperationProbe(SemanticOperation.CONFIG),
    )


def test_status_allowed(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)
    (scenario.workspace.root / "tracked.txt").write_text(
        "agent change\n",
        encoding="utf-8",
    )

    feedback = _accepted_feedback(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.STATUS),
    )

    assert "tracked.txt" in feedback.paths


def test_diff_allowed(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)
    (scenario.workspace.root / "tracked.txt").write_text(
        "agent change\n",
        encoding="utf-8",
    )

    feedback = _accepted_feedback(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.DIFF),
    )

    assert "tracked.txt" in feedback.paths
    assert "baseline" in feedback.removed_lines
    assert "agent change" in feedback.added_lines


def test_cached_diff_allowed(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)
    (scenario.workspace.root / "tracked.txt").write_text(
        "agent change\n",
        encoding="utf-8",
    )
    _assert_accepted(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.STAGE, paths=("tracked.txt",)),
    )

    feedback = _accepted_feedback(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.CACHED_DIFF),
    )

    assert "tracked.txt" in feedback.paths
    assert "baseline" in feedback.removed_lines
    assert "agent change" in feedback.added_lines


def test_explicit_files(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)
    origin_before = _origin_state(scenario.origin)
    (scenario.workspace.root / "tracked.txt").write_text(
        "tracked change\n",
        encoding="utf-8",
    )
    (scenario.workspace.root / "other.txt").write_text(
        "other change\n",
        encoding="utf-8",
    )

    _assert_accepted(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.STAGE, paths=("tracked.txt",)),
    )

    cached = _accepted_feedback(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.CACHED_DIFF),
    )
    worktree = _accepted_feedback(
        wp12_synthetic_git_conformance,
        context,
        OperationProbe(SemanticOperation.DIFF),
    )
    assert cached.paths == frozenset({"tracked.txt"})
    assert "other.txt" in worktree.paths
    assert _origin_state(scenario.origin) == origin_before


@pytest.mark.parametrize("paths", ((), ("directory",), (".",)))
def test_required_path_rejections(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
    paths: tuple[str, ...],
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)

    _assert_rejected_without_side_effect(
        wp12_synthetic_git_conformance,
        scenario,
        context,
        OperationProbe(SemanticOperation.STAGE, paths=paths),
    )


@pytest.mark.parametrize(
    "path",
    ("../escape.txt", "/absolute.txt", "directory/../../escape.txt"),
)
def test_path_traversal_rejected(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
    path: str,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)

    _assert_rejected_without_side_effect(
        wp12_synthetic_git_conformance,
        scenario,
        context,
        OperationProbe(SemanticOperation.STAGE, paths=(path,)),
    )


@pytest.mark.parametrize(
    "path",
    ("*.txt", "tracked?.txt", ":(glob)**/*.py", ":(exclude)tracked.txt"),
)
def test_glob_magic_rejected(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
    path: str,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)

    _assert_rejected_without_side_effect(
        wp12_synthetic_git_conformance,
        scenario,
        context,
        OperationProbe(SemanticOperation.STAGE, paths=(path,)),
    )


@pytest.mark.parametrize(
    "option",
    ("--git-dir=/tmp/other", "--work-tree=/tmp/other", "-c", "--config-env"),
)
def test_global_options_rejected(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
    option: str,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)

    _assert_rejected_without_side_effect(
        wp12_synthetic_git_conformance,
        scenario,
        context,
        OperationProbe(
            SemanticOperation.STAGE,
            paths=("tracked.txt",),
            options=(option,),
        ),
    )


@pytest.mark.parametrize("option", ("--all", "-A", "--update"))
def test_range_style_index_options_rejected(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
    option: str,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)

    _assert_rejected_without_side_effect(
        wp12_synthetic_git_conformance,
        scenario,
        context,
        OperationProbe(SemanticOperation.STAGE, options=(option,)),
    )


@pytest.mark.parametrize("requirement", ("WS-003", "WS-004", "WS-005"))
def test_spec_requirement(
    tmp_path: Path,
    wp12_synthetic_git_conformance: SyntheticGitConformance,
    requirement: str,
) -> None:
    scenario = _scenario(tmp_path)
    context = _accepted_context(wp12_synthetic_git_conformance, scenario)
    if requirement == "WS-003":
        probe = OperationProbe(
            SemanticOperation.STAGE,
            paths=("tracked.txt",),
            options=("-c",),
        )
    elif requirement == "WS-004":
        probe = OperationProbe(SemanticOperation.COMMIT)
    else:
        probe = OperationProbe(
            SemanticOperation.STAGE,
            paths=("directory",),
        )

    _assert_rejected_without_side_effect(
        wp12_synthetic_git_conformance,
        scenario,
        context,
        probe,
    )
