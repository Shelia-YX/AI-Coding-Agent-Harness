"""WP-11 ignored-input governance contract tests.

Production imports are deferred until test execution so the pre-implementation
suite collects successfully and fails at the missing WP-11 API boundary.
All repositories and materialized workspaces live below pytest ``tmp_path``.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import importlib
import os
from pathlib import Path
import stat
import subprocess
from types import SimpleNamespace

import pytest

from coding_harness.domain.approvals import (
    Approval,
    ApprovalExecutionContext,
    ApprovalType,
    PresentedApprovalReference,
    policy_record_digest,
)
from coding_harness.domain.enums import TaskState
from coding_harness.domain.errors import PolicyReason
from coding_harness.domain.models import PlanVersion
from coding_harness.domain.policy import PolicyDecision, PolicyDecisionRecord
from coding_harness.workspace.manifest import BaselineManifest, build_baseline
from coding_harness.workspace.materialize import TaskWorkspace, materialize_workspace


OWNED_REQUIREMENTS = ("WS-010", "WS-011", "WS-012", "WS-015", "WS-016")
_READ_ONLY = "read_only_input"
_EPHEMERAL = "writable_ephemeral"
_EXPECTED_RED = "WP-11 production API is not implemented"


def _api() -> SimpleNamespace:
    try:
        module = importlib.import_module("coding_harness.workspace.ignored")
    except ModuleNotFoundError as exc:
        if exc.name == "coding_harness.workspace.ignored":
            pytest.fail(_EXPECTED_RED, pytrace=False)
        raise
    required = {
        "IgnoredInputMode": getattr(module, "IgnoredInputMode", None),
        "SandboxInputManifest": getattr(module, "SandboxInputManifest", None),
        "materialize_ignored_input": getattr(
            module,
            "materialize_ignored_input",
            None,
        ),
    }
    missing = tuple(name for name, value in required.items() if value is None)
    if missing:
        pytest.fail(
            _EXPECTED_RED + ": " + ", ".join(missing),
            pytrace=False,
        )
    return SimpleNamespace(**required)


def _git(repo: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "HOME": str(repo.parent / ".git-home"),
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


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _repository(tmp_path: Path) -> SimpleNamespace:
    root = tmp_path / "origin"
    root.mkdir()
    _git(root, "init", "-q")
    (root / ".gitignore").write_text("ignored/\n.env\n", encoding="utf-8")
    (root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(root, "add", "--", ".gitignore", "tracked.txt")
    _git(
        root,
        "-c",
        "user.name=WP11 Test",
        "-c",
        "user.email=wp11@example.invalid",
        "commit",
        "-q",
        "-m",
        "fixture",
    )
    ignored = root / "ignored" / "input.txt"
    ignored.parent.mkdir()
    ignored.write_bytes(b"ignored-input\n")
    return SimpleNamespace(root=root, ignored=ignored)


def _workspace(tmp_path: Path, root: Path) -> tuple[BaselineManifest, TaskWorkspace]:
    baseline = build_baseline(root)
    workspace = materialize_workspace(baseline, tmp_path / "task-workspace")
    return baseline, workspace


def _policy_record(
    *,
    action_id: str,
    request_digest: str,
    idempotency_key: str,
) -> PolicyDecisionRecord:
    return PolicyDecisionRecord(
        decision=PolicyDecision.REQUIRE_APPROVAL,
        reason=PolicyReason.APPROVAL_REQUIRED,
        detail="trusted policy result",
        error_code=None,
        action_identity=action_id,
        action_digest=request_digest,
        tool_execution_permitted=False,
        approval_can_override=True,
        effective_profile="trusted-profile",
        bound_task_id="task:1",
        bound_target_type=ApprovalType.ACTION_APPROVAL.value,
        bound_target_identity=action_id,
        bound_digest=request_digest,
        bound_expected_state=TaskState.AWAITING_ACTION_APPROVAL,
        bound_idempotency_key=idempotency_key,
    )


def _authority(
    *,
    baseline: BaselineManifest,
    path: str,
    kind: str,
    size: int,
    content_digest: str,
    mode: str = _READ_ONLY,
    manifest_identity: str = "sandbox-manifest:1",
    action_id: str = "action:ignored:1",
) -> SimpleNamespace:
    request_digest = _digest(
        "\0".join(
            (
                action_id,
                path,
                kind,
                str(size),
                content_digest,
                mode,
                manifest_identity,
            )
        ).encode()
    )
    idempotency_key = "ignored:key:" + action_id
    policy = _policy_record(
        action_id=action_id,
        request_digest=request_digest,
        idempotency_key=idempotency_key,
    )
    plan = PlanVersion(
        identity="plan:1",
        task_id="task:1",
        sequence=1,
        content_digest="1" * 64,
        display_text="Plan",
    )
    values = {
        "identity": "approval:" + action_id,
        "revision": 1,
        "display_text": "Include one ignored input",
        "approval_type": ApprovalType.ACTION_APPROVAL,
        "task_id": "task:1",
        "target_identity": action_id,
        "expected_state": TaskState.AWAITING_ACTION_APPROVAL,
        "plan_version": plan,
        "contract_version": None,
        "request_digest": request_digest,
        "policy_record_identity": "policy-record:" + action_id,
        "policy_record_digest": policy_record_digest(policy),
        "reason_code": PolicyReason.APPROVAL_REQUIRED.value,
        "created_at": 100,
        "expires_at": 200,
        "consumed": False,
        "consumed_at": None,
        "revoked": False,
        "revoked_at": None,
        "idempotency_key": idempotency_key,
        "scope_digest": None,
        "action_kind": "include_ignored_input",
        "action_id": action_id,
        "normalized_paths": (path,),
        "expected_content_digest": None,
        "baseline_manifest_digest": baseline.digest,
        "action_payload_digest": request_digest,
        "action_reason": "required task input",
        "ignored_entries": ((path, kind, size, content_digest),),
        "ignored_input_mode": mode,
        "allowed_stages": ("EXECUTING",),
        "sandbox_manifest_identity": manifest_identity,
        "exportable_to_llm": False,
        "changeset_digest": None,
        "budget_version_identity": None,
        "affected_dimensions": (),
        "current_usage": (),
        "old_limits": (),
        "new_limits": (),
        "hard_limits": (),
        "extension_reason": None,
    }
    approval = Approval(**values)
    context = ApprovalExecutionContext(
        approval_type=approval.approval_type,
        task_id=approval.task_id,
        target_identity=approval.target_identity,
        expected_state=approval.expected_state,
        plan_version_identity=approval.plan_version.identity,
        contract_version_identity=None,
        request_digest=approval.request_digest,
        policy_record_identity=approval.policy_record_identity,
        policy_record_digest=approval.policy_record_digest,
        reason_code=approval.reason_code,
        idempotency_key=approval.idempotency_key,
        scope_digest=approval.scope_digest,
        action_kind=approval.action_kind,
        action_id=approval.action_id,
        normalized_paths=approval.normalized_paths,
        expected_content_digest=approval.expected_content_digest,
        baseline_manifest_digest=approval.baseline_manifest_digest,
        action_payload_digest=approval.action_payload_digest,
        action_reason=approval.action_reason,
        ignored_entries=approval.ignored_entries,
        ignored_input_mode=approval.ignored_input_mode,
        allowed_stages=approval.allowed_stages,
        sandbox_manifest_identity=approval.sandbox_manifest_identity,
        exportable_to_llm=approval.exportable_to_llm,
        changeset_digest=approval.changeset_digest,
        budget_version_identity=approval.budget_version_identity,
        affected_dimensions=approval.affected_dimensions,
        current_usage=approval.current_usage,
        old_limits=approval.old_limits,
        new_limits=approval.new_limits,
        hard_limits=approval.hard_limits,
        extension_reason=approval.extension_reason,
    )
    return SimpleNamespace(approval=approval, context=context, policy=policy)


def _invoke(
    api: SimpleNamespace,
    *,
    source_root: Path,
    baseline: BaselineManifest,
    workspace: TaskWorkspace,
    authority: SimpleNamespace,
    current_manifest: object = None,
    **overrides: object,
):
    values = {
        "source_root": source_root,
        "baseline": baseline,
        "workspace": workspace,
        "current_manifest": current_manifest,
        "current_record": authority.approval,
        "expected_revision": authority.approval.revision,
        "presented_reference": PresentedApprovalReference(
            identity=authority.approval.identity,
            revision=authority.approval.revision,
        ),
        "current_context": authority.context,
        "trusted_policy_record": authority.policy,
        "trusted_policy_record_identity": authority.approval.policy_record_identity,
        "now": 150,
        "max_input_count": 16,
        "max_input_bytes": 64 * 1024,
    }
    values.update(overrides)
    return api.materialize_ignored_input(**values)


def _valid_case(
    tmp_path: Path,
    *,
    mode: str = _READ_ONLY,
    manifest_identity: str = "sandbox-manifest:1",
) -> SimpleNamespace:
    api = _api()
    repository = _repository(tmp_path)
    baseline, workspace = _workspace(tmp_path, repository.root)
    content = repository.ignored.read_bytes()
    authority = _authority(
        baseline=baseline,
        path="ignored/input.txt",
        kind="regular_file",
        size=len(content),
        content_digest=_digest(content),
        mode=mode,
        manifest_identity=manifest_identity,
    )
    return SimpleNamespace(
        api=api,
        repository=repository,
        baseline=baseline,
        workspace=workspace,
        authority=authority,
    )


def _assert_denied(result: object) -> None:
    assert result.permitted is False
    assert result.side_effect_permitted is False
    assert result.manifest is None


def test_ignored_default_excluded(tmp_path: Path) -> None:
    case = _valid_case(tmp_path)
    assert all(
        entry.path.canonical != "ignored/input.txt"
        for entry in case.baseline.entries
    )
    assert not (case.workspace.root / "ignored" / "input.txt").exists()


def test_unapproved_not_materialized(tmp_path: Path) -> None:
    case = _valid_case(tmp_path)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
        expected_revision=case.authority.approval.revision + 1,
    )
    _assert_denied(result)
    assert not (case.workspace.root / "ignored" / "input.txt").exists()


def test_approval_freezes_manifest(tmp_path: Path) -> None:
    case = _valid_case(tmp_path)
    case.repository.ignored.write_bytes(b"changed-after-approval\n")
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )
    _assert_denied(result)
    assert result.reason == "IGNORED_INPUT_BINDING_MISMATCH"


def test_baseline_unchanged(tmp_path: Path) -> None:
    case = _valid_case(tmp_path)
    before = (case.baseline, case.baseline.digest, case.baseline.entries)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )
    assert result.permitted is True
    assert (case.baseline, case.baseline.digest, case.baseline.entries) == before
    assert result.manifest.baseline_digest == case.baseline.digest


def test_readonly_rejects_write(tmp_path: Path) -> None:
    case = _valid_case(tmp_path, mode=_READ_ONLY)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )
    target = result.workspace.root / "ignored" / "input.txt"
    assert result.permitted is True
    assert stat.S_IMODE(target.stat().st_mode) & stat.S_IWUSR == 0
    assert result.manifest.entries[0].mode is case.api.IgnoredInputMode.READ_ONLY_INPUT


def test_ephemeral_copy_only(tmp_path: Path) -> None:
    case = _valid_case(tmp_path, mode=_EPHEMERAL)
    source_before = case.repository.ignored.read_bytes()
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )
    target = result.workspace.root / "ignored" / "input.txt"
    assert target.read_bytes() == source_before
    assert os.stat(target).st_ino != os.stat(case.repository.ignored).st_ino
    target.write_bytes(b"ephemeral-change\n")
    assert case.repository.ignored.read_bytes() == source_before


def test_source_not_changeset(tmp_path: Path) -> None:
    case = _valid_case(tmp_path)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )
    assert result.manifest.entries[0].changeset_eligible is False
    assert result.changeset_eligible_paths == ()


def test_derived_not_writeback(tmp_path: Path) -> None:
    case = _valid_case(tmp_path, mode=_EPHEMERAL)
    source_before = case.repository.ignored.read_bytes()
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )
    target = result.workspace.root / "ignored" / "input.txt"
    target.write_bytes(b"derived\n")
    assert result.manifest.entries[0].writeback_permitted is False
    assert result.writeback_paths == ()
    assert case.repository.ignored.read_bytes() == source_before


def test_never_exportable(tmp_path: Path) -> None:
    case = _valid_case(tmp_path)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )
    assert result.manifest.exportable_to_llm is False
    assert all(entry.exportable_to_llm is False for entry in result.manifest.entries)


def test_forged_approval_result_rejected(tmp_path: Path) -> None:
    case = _valid_case(tmp_path)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
        current_record=SimpleNamespace(
            permitted=True,
            side_effect_permitted=True,
        ),
    )
    _assert_denied(result)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("task_id", "task:other"),
        ("target_identity", "action:other"),
        ("expected_state", TaskState.EXECUTING),
        ("plan_version_identity", "plan:other"),
        ("request_digest", "a" * 64),
        ("policy_record_identity", "policy-record:other"),
        ("action_payload_digest", "b" * 64),
        ("normalized_paths", ("ignored/other.txt",)),
        ("ignored_entries", (("ignored/other.txt", "regular_file", 14, "c" * 64),)),
        ("ignored_input_mode", "unknown-mode"),
        ("allowed_stages", ("VERIFYING",)),
        ("sandbox_manifest_identity", "sandbox-manifest:other"),
        ("idempotency_key", "ignored:key:other"),
    ),
    ids=(
        "task",
        "action",
        "state",
        "plan-version",
        "request-digest",
        "policy-record",
        "payload-digest",
        "path",
        "entry",
        "mode",
        "stage",
        "manifest-version",
        "idempotency",
    ),
)
def test_approval_binding_drift_fails_closed(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    case = _valid_case(tmp_path)
    context = replace(case.authority.context, **{field: value})
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
        current_context=context,
    )
    _assert_denied(result)
    assert not (case.workspace.root / "ignored" / "input.txt").exists()


def test_manifest_version_changes_after_consumption(tmp_path: Path) -> None:
    case = _valid_case(tmp_path, manifest_identity="sandbox-manifest:1")
    first = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )
    second_source = case.repository.root / "ignored" / "second.txt"
    second_source.write_bytes(b"second\n")
    second_authority = _authority(
        baseline=case.baseline,
        path="ignored/second.txt",
        kind="regular_file",
        size=len(second_source.read_bytes()),
        content_digest=_digest(second_source.read_bytes()),
        mode=_READ_ONLY,
        manifest_identity="sandbox-manifest:2",
        action_id="action:ignored:2",
    )
    second = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=first.workspace,
        authority=second_authority,
        current_manifest=first.manifest,
    )
    assert second.manifest.identity != first.manifest.identity
    assert second.manifest.revision == first.manifest.revision + 1
    assert first.manifest.revision == 1


def test_failed_materialization_does_not_advance_version(tmp_path: Path) -> None:
    case = _valid_case(tmp_path)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
        max_input_bytes=1,
    )
    _assert_denied(result)
    assert result.approval_result.side_effect_permitted is False
    assert not (case.workspace.root / "ignored" / "input.txt").exists()


def test_materialization_result_binds_consumed_revision(tmp_path: Path) -> None:
    case = _valid_case(tmp_path)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )
    assert result.permitted is True
    assert result.side_effect_permitted is True
    assert result.approval_result.previous_revision == 1
    assert result.approval_result.expected_revision == 1
    assert result.approval_result.new_revision == 2
    assert result.approval_result.approval.consumed is True


@pytest.mark.parametrize(
    "category",
    ("sensitive", "out-of-bounds", "over-limit", "unknown-purpose", "special-file"),
)
def test_invalid_ignored_input_fails_closed(
    tmp_path: Path,
    category: str,
) -> None:
    case = _valid_case(tmp_path)
    overrides: dict[str, object] = {}
    authority = case.authority
    if category == "sensitive":
        secret = case.repository.root / ".env"
        secret.write_bytes(b"PRIVATE=value\n")
        authority = _authority(
            baseline=case.baseline,
            path=".env",
            kind="regular_file",
            size=len(secret.read_bytes()),
            content_digest=_digest(secret.read_bytes()),
        )
    elif category == "out-of-bounds":
        authority = _authority(
            baseline=case.baseline,
            path="../outside.txt",
            kind="regular_file",
            size=1,
            content_digest=_digest(b"x"),
        )
    elif category == "over-limit":
        overrides["max_input_bytes"] = 1
    elif category == "unknown-purpose":
        invalid_context = replace(
            case.authority.context,
            ignored_input_mode="unknown-purpose",
        )
        overrides["current_context"] = invalid_context
    else:
        special = case.repository.root / "ignored" / "pipe"
        os.mkfifo(special)
        authority = _authority(
            baseline=case.baseline,
            path="ignored/pipe",
            kind="fifo",
            size=0,
            content_digest=_digest(b""),
        )
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=authority,
        **overrides,
    )
    _assert_denied(result)


def test_sandbox_manifest_immutable(tmp_path: Path) -> None:
    case = _valid_case(tmp_path)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )
    with pytest.raises(FrozenInstanceError):
        result.manifest.revision = 99
    with pytest.raises(TypeError):
        result.manifest.entries[0] = result.manifest.entries[0]


@pytest.mark.parametrize("requirement_id", OWNED_REQUIREMENTS)
def test_spec_requirement(tmp_path: Path, requirement_id: str) -> None:
    case = _valid_case(
        tmp_path,
        mode=_EPHEMERAL if requirement_id == "WS-016" else _READ_ONLY,
    )
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )
    if requirement_id == "WS-010":
        assert result.manifest.entries[0].mode in {
            case.api.IgnoredInputMode.READ_ONLY_INPUT,
            case.api.IgnoredInputMode.WRITABLE_EPHEMERAL,
        }
    elif requirement_id == "WS-011":
        assert result.changeset_eligible_paths == ()
    elif requirement_id == "WS-012":
        assert result.reason == "IGNORED_INPUT_MATERIALIZED"
        assert result.manifest.entries[0].kind.value == "regular_file"
    elif requirement_id == "WS-015":
        assert result.approval_result.approval.consumed is True
        assert result.manifest.baseline_digest == case.baseline.digest
    else:
        assert result.manifest.entries[0].writeback_permitted is False
        assert result.manifest.entries[0].exportable_to_llm is False
