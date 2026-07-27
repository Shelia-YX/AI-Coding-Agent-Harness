"""WP-13 Change Set and conflict-detection integration contracts."""

from __future__ import annotations

import hashlib
import importlib
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from coding_harness.domain.enums import TaskState
from coding_harness.workspace.ignored import (
    IgnoredInputKind,
    IgnoredInputMode,
    SandboxInputEntry,
    SandboxInputManifest,
    _manifest_digest,
)
from coding_harness.workspace.manifest import BaselineManifest, build_baseline
from coding_harness.workspace.materialize import TaskWorkspace, materialize_workspace
from coding_harness.workspace.paths import RepoPath


OWNED_REQUIREMENTS = (
    "TXN-005",
    "TXN-006",
    "TXN-007",
    "TXN-008",
    "TXN-017",
    "TXN-018",
)
_EXPECTED_RED = "WP-13 production API is not implemented"


def _api() -> SimpleNamespace:
    required: dict[str, object] = {}
    missing_module: str | None = None
    for module_name, names in (
        (
            "coding_harness.workspace.changeset",
            (
                "ChangeOperation",
                "ChangeScope",
                "ChangeSet",
                "compute_changeset",
            ),
        ),
        (
            "coding_harness.transaction.conflicts",
            (
                "ApplyConfirmation",
                "ConflictType",
                "ConflictReport",
                "detect_conflicts",
            ),
        ),
    ):
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name == module_name:
                missing_module = module_name
                break
            raise
        required.update({name: getattr(module, name, None) for name in names})
    if missing_module is not None:
        pytest.fail(
            f"{_EXPECTED_RED}: {missing_module}",
            pytrace=False,
        )
    missing = tuple(name for name, value in required.items() if value is None)
    if missing:
        pytest.fail(
            _EXPECTED_RED + ": " + ", ".join(missing),
            pytrace=False,
        )
    return SimpleNamespace(**required)


def _git(repo: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    git_home = repo.parent / ".git-test-home"
    git_home.mkdir(exist_ok=True)
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
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


def _scenario(
    tmp_path: Path,
    files: dict[str, bytes],
    *,
    symlinks: dict[str, str] | None = None,
    executable: tuple[str, ...] = (),
) -> SimpleNamespace:
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q")
    for relative, content in files.items():
        destination = origin / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    for relative, target in (symlinks or {}).items():
        destination = origin / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(target)
    for relative in executable:
        (origin / relative).chmod(0o755)
    _git(origin, "add", "--", *sorted((*files, *(symlinks or {}))))
    _git(
        origin,
        "-c",
        "user.name=WP13 Test",
        "-c",
        "user.email=wp13@example.invalid",
        "commit",
        "-q",
        "-m",
        "fixture",
    )
    baseline = build_baseline(origin)
    workspace = materialize_workspace(baseline, tmp_path / "workspace")
    return SimpleNamespace(origin=origin, baseline=baseline, workspace=workspace)


def _compute(
    api: SimpleNamespace,
    scenario: SimpleNamespace,
    *,
    target_paths: tuple[str, ...] | None = None,
):
    targets = (
        None
        if target_paths is None
        else tuple(RepoPath.parse(path) for path in target_paths)
    )
    return api.compute_changeset(
        scenario.baseline,
        scenario.workspace,
        target_paths=targets,
    )


def _changes_by_path(changeset) -> dict[str, object]:
    return {change.path.canonical: change for change in changeset.changed_files}


def _conflict_types(report) -> set[object]:
    return {conflict.conflict_type for conflict in report.conflicts}


def _confirmation(
    api: SimpleNamespace,
    scenario: SimpleNamespace,
    changeset,
    **overrides: object,
):
    values = {
        "task_id": "task:wp13",
        "changeset_digest": changeset.digest,
        "baseline_manifest_digest": scenario.baseline.digest,
        "plan_version_identity": "plan:wp13:1",
        "acceptance_contract_version_identity": "contract:wp13:1",
        "expected_state": TaskState.READY_TO_APPLY,
        "idempotency_key": "apply:wp13:1",
    }
    values.update(overrides)
    return api.ApplyConfirmation(**values)


def _detect(
    api: SimpleNamespace,
    scenario: SimpleNamespace,
    changeset,
    *,
    confirmation=None,
    acceptance_satisfied: bool = True,
    nonterminal_apply_transaction: bool = False,
    recovery_required: bool = False,
    policy_denied: bool = False,
):
    return api.detect_conflicts(
        scenario.baseline,
        changeset,
        scenario.workspace,
        scenario.origin,
        confirmation=(
            _confirmation(api, scenario, changeset)
            if confirmation is None
            else confirmation
        ),
        current_task_id="task:wp13",
        current_plan_version_identity="plan:wp13:1",
        current_acceptance_contract_version_identity="contract:wp13:1",
        current_state=TaskState.READY_TO_APPLY,
        current_idempotency_key="apply:wp13:1",
        acceptance_satisfied=acceptance_satisfied,
        nonterminal_apply_transaction=nonterminal_apply_transaction,
        recovery_required=recovery_required,
        policy_denied=policy_denied,
    )


def _sandbox_manifest(
    scenario: SimpleNamespace,
    *,
    path: str,
    content: bytes,
) -> SandboxInputManifest:
    entry = SandboxInputEntry(
        path=RepoPath.parse(path),
        kind=IgnoredInputKind.REGULAR_FILE,
        size=len(content),
        content_digest=hashlib.sha256(content).hexdigest(),
        mode=IgnoredInputMode.WRITABLE_EPHEMERAL,
        allowed_stages=("EXECUTING",),
    )
    identity = "1" * 64
    approval_intent_digest = "2" * 64
    workspace_logical_identity = "3" * 64
    entries = (entry,)
    return SandboxInputManifest(
        identity=identity,
        revision=1,
        baseline_digest=scenario.baseline.digest,
        entries=entries,
        digest=_manifest_digest(
            identity=identity,
            revision=1,
            baseline_digest=scenario.baseline.digest,
            approval_intent_digest=approval_intent_digest,
            workspace_logical_identity=workspace_logical_identity,
            entries=entries,
        ),
        approval_intent_digest=approval_intent_digest,
        workspace_logical_identity=workspace_logical_identity,
    )


def test_create_modify_delete(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(
        tmp_path,
        {
            "modify.txt": b"baseline-modify\n",
            "delete.txt": b"baseline-delete\n",
        },
    )
    (scenario.workspace.root / "modify.txt").write_bytes(b"agent-modify\n")
    (scenario.workspace.root / "delete.txt").unlink()
    (scenario.workspace.root / "add.txt").write_bytes(b"agent-add\n")

    changeset = _compute(api, scenario)

    assert type(changeset) is api.ChangeSet
    changes = _changes_by_path(changeset)
    assert tuple(changes) == ("add.txt", "delete.txt", "modify.txt")
    assert changes["add.txt"].operation is api.ChangeOperation.ADD
    assert changes["add.txt"].baseline_digest is None
    assert changes["add.txt"].current_digest == hashlib.sha256(
        b"agent-add\n"
    ).hexdigest()
    assert changes["delete.txt"].operation is api.ChangeOperation.DELETE
    assert changes["delete.txt"].baseline_digest == hashlib.sha256(
        b"baseline-delete\n"
    ).hexdigest()
    assert changes["delete.txt"].current_digest is None
    assert changes["modify.txt"].operation is api.ChangeOperation.MODIFY
    assert changes["modify.txt"].baseline_digest == hashlib.sha256(
        b"baseline-modify\n"
    ).hexdigest()
    assert changes["modify.txt"].current_digest == hashlib.sha256(
        b"agent-modify\n"
    ).hexdigest()
    assert all(type(change.path) is RepoPath for change in changes.values())


def test_mode_symlink(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(
        tmp_path,
        {
            "one.txt": b"one\n",
            "two.txt": b"two\n",
            "script.sh": b"#!/bin/sh\nexit 0\n",
        },
        symlinks={"selected.txt": "one.txt"},
    )
    (scenario.workspace.root / "script.sh").chmod(0o755)
    (scenario.workspace.root / "selected.txt").unlink()
    (scenario.workspace.root / "selected.txt").symlink_to("two.txt")

    changeset = _compute(api, scenario)

    changes = _changes_by_path(changeset)
    assert tuple(changes) == ("script.sh", "selected.txt")
    assert changes["script.sh"].operation is api.ChangeOperation.MODIFY
    assert changes["script.sh"].baseline_digest == changes["script.sh"].current_digest
    assert changes["script.sh"].baseline_executable is False
    assert changes["script.sh"].current_executable is True
    assert changes["selected.txt"].operation is api.ChangeOperation.MODIFY
    assert changes["selected.txt"].baseline_symlink_target == "one.txt"
    assert changes["selected.txt"].current_symlink_target == "two.txt"


def test_digest_changes(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"target.txt": b"baseline\n"})
    target = scenario.workspace.root / "target.txt"
    target.write_bytes(b"first\n")

    first = _compute(api, scenario)
    repeated = _compute(api, scenario)
    target.write_bytes(b"second\n")
    second = _compute(api, scenario)

    assert first.serialize() == repeated.serialize()
    assert first.digest == repeated.digest
    assert first.digest == hashlib.sha256(first.serialize()).hexdigest()
    assert second.digest == hashlib.sha256(second.serialize()).hexdigest()
    assert second.digest != first.digest


def test_fake_manifest_cannot_bypass_authority_boundary(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"target.txt": b"baseline\n"})
    agent_content = b"agent-created\n"
    agent_path = scenario.workspace.root / "agent-secret.txt"
    agent_path.write_bytes(agent_content)
    fake_manifest = _sandbox_manifest(
        scenario,
        path="agent-secret.txt",
        content=agent_content,
    )

    with pytest.raises(TypeError):
        api.compute_changeset(
            scenario.baseline,
            scenario.workspace,
            sandbox_input_manifest=fake_manifest,
        )


def test_workspace_snapshot_max_files_is_bounded(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"anchor.txt": b"anchor\n"})
    for index in range(10_001):
        (scenario.workspace.root / f"generated-{index:05d}.txt").touch()

    with pytest.raises(
        ValueError,
        match=r"^workspace snapshot limit exceeded: MAX_FILES$",
    ):
        _compute(api, scenario)


def test_workspace_snapshot_wide_directories_are_bounded(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"anchor.txt": b"anchor\n"})
    for index in range(10_001):
        (scenario.workspace.root / f"directory-{index:05d}").mkdir()

    with pytest.raises(
        ValueError,
        match=r"^workspace snapshot limit exceeded: MAX_FILES$",
    ):
        _compute(api, scenario)


def test_workspace_snapshot_max_bytes_is_bounded(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"anchor.txt": b"anchor\n"})
    chunk = b"x" * (8 * 1024 * 1024)
    for index in range(9):
        (scenario.workspace.root / f"large-{index}.bin").write_bytes(chunk)

    with pytest.raises(
        ValueError,
        match=r"^workspace snapshot limit exceeded: MAX_BYTES$",
    ):
        _compute(api, scenario)


def test_workspace_snapshot_uses_remaining_byte_budget(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"anchor.txt": b"anchor\n"})
    content = b"x" * (9 * 1024 * 1024)
    (scenario.workspace.root / "nine-megabytes.bin").write_bytes(content)

    changeset = _compute(api, scenario)

    change = _changes_by_path(changeset)["nine-megabytes.bin"]
    assert change.current_digest == hashlib.sha256(content).hexdigest()


def test_workspace_snapshot_max_depth_is_bounded(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"anchor.txt": b"anchor\n"})
    deep = scenario.workspace.root
    for index in range(41):
        deep /= f"d{index}"
    deep.mkdir(parents=True)
    (deep / "too-deep.txt").write_bytes(b"deep\n")

    with pytest.raises(
        ValueError,
        match=r"^workspace snapshot limit exceeded: MAX_DEPTH$",
    ):
        _compute(api, scenario)


def test_workspace_snapshot_allows_exact_max_depth(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"anchor.txt": b"anchor\n"})
    deep = scenario.workspace.root
    for index in range(40):
        deep /= f"d{index}"
    deep.mkdir(parents=True)
    (deep / "at-boundary.txt").write_bytes(b"boundary\n")

    changeset = _compute(api, scenario)

    assert changeset.changed_files[0].path.canonical.endswith("at-boundary.txt")


def test_workspace_snapshot_invalid_filename_fails_deterministically(
    tmp_path: Path,
) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"anchor.txt": b"anchor\n"})
    invalid_path = os.fsencode(scenario.workspace.root) + b"/invalid-\xff"
    descriptor = os.open(invalid_path, os.O_WRONLY | os.O_CREAT, 0o600)
    os.close(descriptor)

    with pytest.raises(ValueError, match=r"^change set calculation failed$"):
        _compute(api, scenario)


def test_confirmation_binds_digest(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"target.txt": b"baseline\n"})
    (scenario.workspace.root / "target.txt").write_bytes(b"agent\n")
    changeset = _compute(api, scenario)

    report = _detect(api, scenario, changeset)

    assert type(report) is api.ConflictReport
    assert report.conflicts == ()
    assert report.apply_permitted is True


def test_unrelated_change(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(
        tmp_path,
        {"target.txt": b"target\n", "outside.txt": b"outside\n"},
    )
    (scenario.workspace.root / "target.txt").write_bytes(b"agent-target\n")
    (scenario.workspace.root / "outside.txt").write_bytes(b"agent-outside\n")

    changeset = _compute(api, scenario, target_paths=("target.txt",))
    report = _detect(api, scenario, changeset)

    changes = _changes_by_path(changeset)
    assert changes["target.txt"].scope is api.ChangeScope.TARGET
    assert changes["outside.txt"].scope is api.ChangeScope.UNRELATED
    assert report.unrelated_paths == (RepoPath.parse("outside.txt"),)
    assert api.ConflictType.TARGET_CHANGED not in _conflict_types(report)
    assert report.apply_permitted is False


def test_target_conflict(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"target.txt": b"baseline\n"})
    (scenario.workspace.root / "target.txt").write_bytes(b"agent\n")
    changeset = _compute(api, scenario)
    (scenario.origin / "target.txt").write_bytes(b"external\n")

    report = _detect(api, scenario, changeset)

    assert report.apply_permitted is False
    assert len(report.conflicts) == 1
    conflict = report.conflicts[0]
    assert conflict.conflict_type is api.ConflictType.TARGET_CHANGED
    assert conflict.affected_paths == (RepoPath.parse("target.txt"),)
    assert conflict.reason == "target path changed since baseline"


@pytest.mark.parametrize("replacement", ("directory", "fifo", "dangling-symlink"))
def test_unsupported_target_change_is_explicit_conflict(
    replacement: str,
    tmp_path: Path,
) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"target.txt": b"baseline\n"})
    (scenario.workspace.root / "target.txt").write_bytes(b"agent\n")
    changeset = _compute(api, scenario)
    origin_target = scenario.origin / "target.txt"
    origin_target.unlink()
    if replacement == "directory":
        origin_target.mkdir()
    elif replacement == "fifo":
        os.mkfifo(origin_target)
    else:
        origin_target.symlink_to("missing.txt")

    report = _detect(api, scenario, changeset)

    assert report.apply_permitted is False
    assert len(report.conflicts) == 1
    conflict = report.conflicts[0]
    assert conflict.conflict_type is api.ConflictType.TARGET_CHANGED
    assert conflict.affected_paths == (RepoPath.parse("target.txt"),)
    assert conflict.reason == "target path is unsupported or unreadable"


@pytest.mark.parametrize("operation", ("modify", "add", "delete"))
def test_compatible_target_convergence(operation: str, tmp_path: Path) -> None:
    api = _api()
    baseline_files = (
        {"anchor.txt": b"anchor\n"}
        if operation == "add"
        else {"target.txt": b"baseline\n"}
    )
    scenario = _scenario(tmp_path, baseline_files)
    workspace_target = scenario.workspace.root / "target.txt"
    origin_target = scenario.origin / "target.txt"
    if operation == "delete":
        workspace_target.unlink()
        origin_target.unlink()
    else:
        workspace_target.write_bytes(b"same-final\n")
        origin_target.write_bytes(b"same-final\n")
    changeset = _compute(api, scenario)

    report = _detect(api, scenario, changeset)

    assert api.ConflictType.TARGET_CHANGED not in _conflict_types(report)
    assert report.apply_permitted is True


def test_confirmation_invalidated(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"target.txt": b"baseline\n"})
    target = scenario.workspace.root / "target.txt"
    target.write_bytes(b"approved\n")
    approved = _compute(api, scenario)
    target.write_bytes(b"changed-after-confirmation\n")
    report = _detect(
        api,
        scenario,
        approved,
        confirmation=_confirmation(api, scenario, approved),
    )

    assert api.ConflictType.DIGEST_MISMATCH in _conflict_types(report)
    assert report.apply_permitted is False


def test_confirmation_full_binding(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"target.txt": b"baseline\n"})
    (scenario.workspace.root / "target.txt").write_bytes(b"agent\n")
    changeset = _compute(api, scenario)
    invalid_bindings = (
        {"task_id": "task:other"},
        {"changeset_digest": "4" * 64},
        {"baseline_manifest_digest": "5" * 64},
        {"plan_version_identity": "plan:other"},
        {"acceptance_contract_version_identity": "contract:other"},
        {"expected_state": TaskState.APPLYING},
        {"idempotency_key": "apply:other"},
    )

    for override in invalid_bindings:
        report = _detect(
            api,
            scenario,
            changeset,
            confirmation=_confirmation(api, scenario, changeset, **override),
        )
        assert api.ConflictType.CONFIRMATION_INVALID in _conflict_types(report)
        assert report.apply_permitted is False


@pytest.mark.parametrize(
    ("keyword", "conflict_name"),
    (
        ("acceptance_satisfied", "ACCEPTANCE_INVALID"),
        ("nonterminal_apply_transaction", "APPLY_TRANSACTION_ACTIVE"),
        ("recovery_required", "RECOVERY_REQUIRED"),
        ("policy_denied", "POLICY_DENIED"),
    ),
)
def test_confirmation_cannot_override_blockers(
    keyword: str,
    conflict_name: str,
    tmp_path: Path,
) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"target.txt": b"baseline\n"})
    (scenario.workspace.root / "target.txt").write_bytes(b"agent\n")
    changeset = _compute(api, scenario)
    arguments = {
        "acceptance_satisfied": True,
        "nonterminal_apply_transaction": False,
        "recovery_required": False,
        "policy_denied": False,
    }
    arguments[keyword] = (
        False if keyword == "acceptance_satisfied" else True
    )

    report = _detect(api, scenario, changeset, **arguments)

    assert getattr(api.ConflictType, conflict_name) in _conflict_types(report)
    assert report.apply_permitted is False


def test_no_auto_merge(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"target.txt": b"baseline\n"})
    workspace_target = scenario.workspace.root / "target.txt"
    origin_target = scenario.origin / "target.txt"
    workspace_target.write_bytes(b"agent\n")
    changeset = _compute(api, scenario)
    origin_target.write_bytes(b"external\n")

    report = _detect(api, scenario, changeset)

    assert report.apply_permitted is False
    assert origin_target.read_bytes() == b"external\n"
    assert workspace_target.read_bytes() == b"agent\n"


def test_acceptance_blocks(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"target.txt": b"baseline\n"})
    (scenario.workspace.root / "target.txt").write_bytes(b"agent\n")
    changeset = _compute(api, scenario)

    report = _detect(
        api,
        scenario,
        changeset,
        acceptance_satisfied=False,
    )

    assert api.ConflictType.ACCEPTANCE_INVALID in _conflict_types(report)
    assert report.apply_permitted is False


@pytest.mark.parametrize("requirement_id", OWNED_REQUIREMENTS)
def test_spec_requirement(requirement_id: str, tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(
        tmp_path,
        {
            "target.txt": b"baseline\n",
            "delete.txt": b"delete\n",
            "script.sh": b"#!/bin/sh\n",
            "one.txt": b"one\n",
            "two.txt": b"two\n",
        },
        symlinks={"selected.txt": "one.txt"},
    )
    workspace_target = scenario.workspace.root / "target.txt"
    workspace_target.write_bytes(b"agent\n")
    changeset = _compute(api, scenario)

    if requirement_id == "TXN-005":
        (scenario.workspace.root / "add.txt").write_bytes(b"add\n")
        (scenario.workspace.root / "delete.txt").unlink()
        (scenario.workspace.root / "script.sh").chmod(0o755)
        (scenario.workspace.root / "selected.txt").unlink()
        (scenario.workspace.root / "selected.txt").symlink_to("two.txt")
        complete = _compute(api, scenario)
        changes = _changes_by_path(complete)
        assert {
            change.operation for change in changes.values()
        } == {
            api.ChangeOperation.ADD,
            api.ChangeOperation.MODIFY,
            api.ChangeOperation.DELETE,
        }
        assert changes["script.sh"].current_executable is True
        assert changes["selected.txt"].current_symlink_target == "two.txt"
    elif requirement_id == "TXN-006":
        workspace_target.write_bytes(b"post-confirmation\n")
        report = _detect(
            api,
            scenario,
            changeset,
            confirmation=_confirmation(api, scenario, changeset),
        )
        assert api.ConflictType.DIGEST_MISMATCH in _conflict_types(report)
    elif requirement_id == "TXN-007":
        (scenario.origin / "target.txt").write_bytes(b"external\n")
        report = _detect(api, scenario, changeset)
        assert api.ConflictType.TARGET_CHANGED in _conflict_types(report)
    elif requirement_id == "TXN-008":
        origin_target = scenario.origin / "target.txt"
        origin_target.write_bytes(b"external\n")
        report = _detect(api, scenario, changeset)
        assert report.apply_permitted is False
        assert origin_target.read_bytes() == b"external\n"
    elif requirement_id == "TXN-017":
        overrides = (
            {"task_id": "task:other"},
            {"changeset_digest": "4" * 64},
            {"baseline_manifest_digest": "5" * 64},
            {"plan_version_identity": "plan:other"},
            {"acceptance_contract_version_identity": "contract:other"},
            {"expected_state": TaskState.APPLYING},
            {"idempotency_key": "apply:other"},
        )
        for override in overrides:
            report = _detect(
                api,
                scenario,
                changeset,
                confirmation=_confirmation(
                    api,
                    scenario,
                    changeset,
                    **override,
                ),
            )
            assert api.ConflictType.CONFIRMATION_INVALID in _conflict_types(report)
    else:
        blockers = (
            {"acceptance_satisfied": False},
            {"nonterminal_apply_transaction": True},
            {"recovery_required": True},
            {"policy_denied": True},
        )
        for blocker in blockers:
            report = _detect(api, scenario, changeset, **blocker)
            assert report.apply_permitted is False
