"""WP-11 ignored-input governance contract tests.

Production imports are deferred until test execution so the pre-implementation
suite collects successfully and fails at the missing WP-11 API boundary.
All repositories and materialized workspaces live below pytest ``tmp_path``.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import importlib
import json
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
from coding_harness.workspace.paths import RepoPath


OWNED_REQUIREMENTS = ("WS-010", "WS-011", "WS-012", "WS-015", "WS-016")
_READ_ONLY = "read_only_input"
_EPHEMERAL = "writable_ephemeral"
_EXPECTED_RED = "WP-11 production API is not implemented"
_IDENTITY_EXPECTED_RED = "WP-11 public identity builder API is not implemented"
_VECTOR_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "fixtures"
    / "workspace"
    / "wp11_identity_v1_vectors.json"
)
_MANIFEST_DIGEST_VECTOR_INPUT = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "fixtures"
    / "workspace"
    / "wp11_manifest_digest_v1_vectors.input.json"
)
_MANIFEST_DIGEST_VECTOR_OUTPUT = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "fixtures"
    / "workspace"
    / "wp11_manifest_digest_v1_vectors.json"
)


def _manifest_digest_vector_cases() -> tuple[pytest.ParameterSet, ...]:
    inputs = json.loads(_MANIFEST_DIGEST_VECTOR_INPUT.read_text(encoding="utf-8"))
    outputs = json.loads(_MANIFEST_DIGEST_VECTOR_OUTPUT.read_text(encoding="utf-8"))
    expected_by_id = {
        vector["id"]: vector["sha256"] for vector in outputs["vectors"]
    }
    return tuple(
        pytest.param(vector, expected_by_id[vector["id"]], id=vector["id"])
        for vector in inputs["vectors"]
    )


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


@pytest.mark.parametrize(("vector", "expected_digest"), _manifest_digest_vector_cases())
def test_manifest_digest_v1_matches_frozen_vector(
    vector: dict[str, object],
    expected_digest: str,
) -> None:
    module = importlib.import_module("coding_harness.workspace.ignored")
    entries = tuple(
        module.SandboxInputEntry(
            path=RepoPath.parse(entry["path"]),
            kind=module.IgnoredInputKind(entry["kind"]),
            size=entry["size"],
            content_digest=entry["content_digest"],
            mode=module.IgnoredInputMode(entry["mode"]),
            allowed_stages=tuple(entry["allowed_stages"]),
            changeset_eligible=entry["changeset_eligible"],
            writeback_permitted=entry["writeback_permitted"],
            exportable_to_llm=entry["exportable_to_llm"],
        )
        for entry in vector["entries"]
    )

    actual = module._manifest_digest(
        identity=vector["identity"],
        revision=vector["revision"],
        baseline_digest=vector["baseline_digest"],
        approval_intent_digest=vector["approval_intent_digest"],
        workspace_logical_identity=vector["workspace_logical_identity"],
        entries=entries,
    )

    assert actual == expected_digest


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


def _canonical_expected_identity(
    *,
    baseline: BaselineManifest,
    path: str,
    kind: str,
    size: int,
    content_digest: str,
    mode: str,
    idempotency_key: str,
    previous_manifest: object = None,
) -> str:
    module = importlib.import_module("coding_harness.workspace.ignored")
    previous = (
        None
        if previous_manifest is None
        else module.PreviousSandboxInputManifestRef(
            revision=previous_manifest.revision,
            identity=previous_manifest.identity,
            digest=previous_manifest.digest,
        )
    )
    result = module.compute_expected_manifest_identity(
        module.ExpectedManifestIdentityRequest(
            task_id="task:1",
            plan_version_identity="plan:1",
            baseline_digest=baseline.digest,
            previous_manifest=previous,
            new_revision=1 if previous is None else previous.revision + 1,
            entries=(
                module.ExpectedManifestEntry(
                    source=RepoPath.parse(path),
                    kind=module.IgnoredInputKind(kind),
                    approved_size=size,
                    content_digest=content_digest,
                    mode=module.IgnoredInputMode(mode),
                    allowed_stages=("EXECUTING",),
                ),
            ),
            idempotency_key=idempotency_key,
            max_input_count=1,
            max_input_bytes=size,
        )
    )
    return result.expected_manifest_identity


def _authority(
    *,
    baseline: BaselineManifest,
    path: str,
    kind: str,
    size: int,
    content_digest: str,
    mode: str = _READ_ONLY,
    manifest_identity: str | None = None,
    action_id: str = "action:ignored:1",
    previous_manifest: object = None,
) -> SimpleNamespace:
    idempotency_key = "ignored:key:" + action_id
    if manifest_identity is None:
        manifest_identity = _canonical_expected_identity(
            baseline=baseline,
            path=path,
            kind=kind,
            size=size,
            content_digest=content_digest,
            mode=mode,
            idempotency_key=idempotency_key,
            previous_manifest=previous_manifest,
        )
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
    manifest_identity: str | None = None,
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
    case = _valid_case(tmp_path)
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
        action_id="action:ignored:2",
        previous_manifest=first.manifest,
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
            manifest_identity="sandbox-manifest:invalid-out-of-bounds",
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
            manifest_identity="sandbox-manifest:invalid-special-file",
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


def _assert_pending_persistence_contract(result: object, authority: object) -> None:
    state = result.state.value if hasattr(result.state, "value") else result.state
    assert state == "PUBLISHED_PENDING_COMMIT"
    assert result.persistence_committed is False
    assert result.active_manifest is None
    assert result.candidate_manifest is not None
    assert (
        result.candidate_manifest.identity
        == authority.approval.sandbox_manifest_identity
    )
    assert result.approval_cas_intent.previous_revision == authority.approval.revision
    assert result.approval_cas_intent.expected_revision == authority.approval.revision
    assert result.approval_cas_intent.new_revision == authority.approval.revision + 1


def test_remediation_i1_materialization_failure_preserves_original_approval_revision(
    tmp_path: Path,
) -> None:
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
    assert result.approval_result.approval is case.authority.approval
    assert result.approval_result.approval.revision == 1
    assert result.approval_result.new_revision is None


def test_remediation_i1_materialization_failure_does_not_return_consumed_approval(
    tmp_path: Path,
) -> None:
    case = _valid_case(tmp_path)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
        max_input_count=0,
    )

    _assert_denied(result)
    assert result.approval_result.approval.consumed is False
    assert result.approval_cas_intent is None


def test_remediation_i1_success_returns_pending_commit_with_exact_cas_binding(
    tmp_path: Path,
) -> None:
    case = _valid_case(tmp_path)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    _assert_pending_persistence_contract(result, case.authority)


def test_remediation_i1_replay_or_stale_revision_fails_closed(
    tmp_path: Path,
) -> None:
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
    assert result.persistence_committed is False
    assert result.active_manifest is None
    assert result.candidate_manifest is None
    assert result.approval_cas_intent is None


def test_remediation_i1_candidate_manifest_not_active_before_persistence_commit(
    tmp_path: Path,
) -> None:
    case = _valid_case(tmp_path)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    _assert_pending_persistence_contract(result, case.authority)
    assert result.candidate_manifest.exportable_to_llm is False
    assert result.active_manifest is None
    assert result.execution_permitted is False
    assert result.changeset_permitted is False
    assert result.export_permitted is False


def test_remediation_i2_failure_after_directory_creation_removes_only_owned_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    source = case.repository.root / "ignored" / "new" / "deep" / "input.txt"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"nested\n")
    authority = _authority(
        baseline=case.baseline,
        path="ignored/new/deep/input.txt",
        kind="regular_file",
        size=len(source.read_bytes()),
        content_digest=_digest(source.read_bytes()),
    )
    module = importlib.import_module("coding_harness.workspace.ignored")
    original_open = module.os.open

    def fail_destination_open(path: object, flags: int, *args: object, **kwargs: object):
        if flags & os.O_CREAT:
            raise OSError("injected destination open failure")
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(module.os, "open", fail_destination_open)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=authority,
    )

    _assert_denied(result)
    assert not os.path.lexists(case.workspace.root / "ignored")
    assert result.cleanup_complete is True
    assert result.cleanup_reason is None


def test_remediation_i2_failure_after_write_removes_owned_temporary_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    existing = case.workspace.root / "preexisting.txt"
    existing.write_bytes(b"keep\n")
    target = case.workspace.root / "ignored" / "input.txt"
    original_fsync = module.os.fsync
    injected = False

    def fail_temporary_sync(descriptor: int) -> None:
        nonlocal injected
        status = os.fstat(descriptor)
        if stat.S_ISREG(status.st_mode) and not injected:
            injected = True
            raise OSError("injected temporary sync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(module.os, "fsync", fail_temporary_sync)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    assert injected is True
    _assert_denied(result)
    assert not os.path.lexists(target)
    assert not tuple(case.workspace.root.rglob(".wp11-ignored-*"))
    assert existing.read_bytes() == b"keep\n"
    assert result.cleanup_complete is True


def test_remediation_i2_cleanup_failure_returns_stable_fail_closed_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    original_unlink = module.os.unlink
    original_open = module.os.open
    replacement_name: str | None = None
    replacement_content = b"replacement-non-owned\n"
    replacement_status: os.stat_result | None = None

    def fail_temporary_fchmod(descriptor: int, mode: int) -> None:
        del descriptor, mode
        raise OSError("injected descriptor-safe mode failure")

    def replace_before_cleanup(
        path: object,
        *args: object,
        **kwargs: object,
    ) -> None:
        nonlocal replacement_name, replacement_status
        name = os.fspath(path)
        parent_fd = kwargs.get("dir_fd")
        if (
            replacement_name is None
            and name.startswith(".wp11-ignored-")
            and type(parent_fd) is int
        ):
            replacement_status = _descriptor_replace(
                original_unlink=original_unlink,
                original_open=original_open,
                parent_fd=parent_fd,
                name=name,
                content=replacement_content,
            )
            replacement_name = name
            raise OSError("injected descriptor-relative cleanup failure")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(module.os, "fchmod", fail_temporary_fchmod)
    monkeypatch.setattr(module.os, "unlink", replace_before_cleanup)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    _assert_denied(result)
    assert result.reason == "IGNORED_INPUT_CLEANUP_FAILED"
    assert result.cleanup_complete is False
    assert result.operation_reason == "IGNORED_INPUT_MATERIALIZATION_FAILED"
    assert result.active_manifest is None
    assert replacement_name is not None
    assert replacement_status is not None
    replacement = case.workspace.root / "ignored" / replacement_name
    assert replacement.read_bytes() == replacement_content
    assert replacement.stat().st_ino == replacement_status.st_ino


def test_remediation_i2_preexisting_directory_is_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    existing = case.workspace.root / "ignored"
    existing.mkdir()
    marker = existing / "preexisting.txt"
    marker.write_bytes(b"keep\n")
    module = importlib.import_module("coding_harness.workspace.ignored")
    original_open = module.os.open

    def fail_destination_open(path: object, flags: int, *args: object, **kwargs: object):
        if flags & os.O_CREAT:
            raise OSError("injected destination open failure")
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(module.os, "open", fail_destination_open)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    _assert_denied(result)
    assert existing.is_dir()
    assert marker.read_bytes() == b"keep\n"
    assert result.cleanup_complete is True


def test_remediation_i3_previous_manifest_drift_changes_expected_identity(
    tmp_path: Path,
) -> None:
    case = _valid_case(tmp_path)
    genesis = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )
    second_source = case.repository.root / "ignored" / "second.txt"
    second_source.write_bytes(b"second\n")
    authority = _authority(
        baseline=case.baseline,
        path="ignored/second.txt",
        kind="regular_file",
        size=len(second_source.read_bytes()),
        content_digest=_digest(second_source.read_bytes()),
        action_id="action:ignored:next",
        previous_manifest=genesis.manifest,
    )
    second_workspace = materialize_workspace(
        case.baseline,
        tmp_path / "second-task-workspace",
    )
    with_previous = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=authority,
        current_manifest=genesis.manifest,
    )
    without_previous = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=second_workspace,
        authority=authority,
    )

    assert (
        with_previous.expected_manifest_identity
        != without_previous.expected_manifest_identity
    )


def test_remediation_i3_approval_revision_drift_rejected_without_identity_rewrite(
    tmp_path: Path,
) -> None:
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
    assert (
        result.expected_manifest_identity
        == case.authority.approval.sandbox_manifest_identity
    )
    assert result.candidate_manifest is None


def test_remediation_i3_workspace_logical_binding_drift_fails_closed(
    tmp_path: Path,
) -> None:
    case = _valid_case(tmp_path)
    drifted = TaskWorkspace(
        root=case.workspace.root,
        baseline_digest=case.workspace.baseline_digest,
        source_head=case.workspace.source_head,
        source_branch=case.workspace.source_branch,
        source_index_digest=case.workspace.source_index_digest,
        source_status_digest="f" * 64,
    )
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=drifted,
        authority=case.authority,
    )

    _assert_denied(result)
    assert result.reason == "IGNORED_INPUT_WORKSPACE_BINDING_MISMATCH"
    assert result.candidate_manifest is None


def test_remediation_i3_rematerialized_workspace_keeps_logical_identity(
    tmp_path: Path,
) -> None:
    case = _valid_case(tmp_path)
    rematerialized = materialize_workspace(
        case.baseline,
        tmp_path / "rematerialized-task-workspace",
    )
    first = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )
    second = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=rematerialized,
        authority=case.authority,
    )

    assert first.workspace_logical_identity == second.workspace_logical_identity


def test_remediation_i3_failed_materialization_produces_no_manifest_version(
    tmp_path: Path,
) -> None:
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
    assert result.candidate_manifest is None
    assert result.active_manifest is None
    assert result.expected_manifest_identity is None


def test_remediation_i3_actual_manifest_digest_binds_approval_cas_intent(
    tmp_path: Path,
) -> None:
    case = _valid_case(tmp_path)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    _assert_pending_persistence_contract(result, case.authority)
    assert (
        result.candidate_manifest.approval_intent_digest
        == result.approval_cas_intent.digest
    )
    assert result.candidate_manifest.digest != result.expected_manifest_identity


def test_remediation_i4_intermediate_source_symlink_rejected(tmp_path: Path) -> None:
    case = _valid_case(tmp_path)
    real = case.repository.root / "real-ignored"
    real.mkdir()
    source = real / "input.txt"
    source.write_bytes(b"linked-source\n")
    alias = case.repository.root / "ignored" / "alias"
    alias.symlink_to(real, target_is_directory=True)
    authority = _authority(
        baseline=case.baseline,
        path="ignored/alias/input.txt",
        kind="regular_file",
        size=len(source.read_bytes()),
        content_digest=_digest(source.read_bytes()),
    )
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=authority,
    )

    _assert_denied(result)
    assert result.reason == "IGNORED_INPUT_SOURCE_CONTAINMENT_FAILED"


def test_remediation_i4_destination_parent_replacement_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    destination_parent = case.workspace.root / "ignored"
    moved_parent = case.workspace.root / "ignored-original"
    outside = tmp_path / "outside"
    outside.mkdir()
    original_open = module.os.open
    replaced = False
    workspace_root_fds: set[int] = set()
    traversal_calls: list[tuple[str, int]] = []

    def replace_at_openat_boundary(
        path: object,
        flags: int,
        *args: object,
        **kwargs: object,
    ) -> int:
        nonlocal replaced
        name = os.fspath(path)
        parent_fd = kwargs.get("dir_fd")
        descriptor = original_open(path, flags, *args, **kwargs)
        if Path(path) == case.workspace.root:
            workspace_root_fds.add(descriptor)
        if name == "ignored" and parent_fd in workspace_root_fds:
            traversal_calls.append((name, parent_fd))
        if name == "ignored" and parent_fd in workspace_root_fds and not replaced:
            os.close(descriptor)
            replaced = True
            destination_parent.rename(moved_parent)
            destination_parent.symlink_to(outside, target_is_directory=True)
            return original_open(path, flags, *args, **kwargs)
        return descriptor

    monkeypatch.setattr(module.os, "open", replace_at_openat_boundary)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    assert replaced is True
    assert traversal_calls
    _assert_denied(result)
    assert not (outside / "input.txt").exists()
    assert not tuple(outside.iterdir())
    assert not (moved_parent / "input.txt").exists()
    assert result.reason == "IGNORED_INPUT_DESTINATION_CONTAINMENT_FAILED"
    assert result.cleanup_complete is True


def test_remediation_i4_hardlink_source_rejected(tmp_path: Path) -> None:
    case = _valid_case(tmp_path)
    outside = tmp_path / "outside-secret.txt"
    outside.write_bytes(b"outside-secret\n")
    hardlink = case.repository.root / "ignored" / "hardlink.txt"
    os.link(outside, hardlink)
    authority = _authority(
        baseline=case.baseline,
        path="ignored/hardlink.txt",
        kind="regular_file",
        size=len(hardlink.read_bytes()),
        content_digest=_digest(hardlink.read_bytes()),
    )
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=authority,
    )

    _assert_denied(result)
    assert result.reason == "IGNORED_INPUT_HARDLINK_REJECTED"
    assert not (case.workspace.root / "ignored" / "hardlink.txt").exists()


def test_remediation_i4_source_mutation_during_read_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    original_read = module.os.read
    mutated = False

    def mutate_after_read(descriptor: int, size: int) -> bytes:
        nonlocal mutated
        chunk = original_read(descriptor, size)
        if chunk and not mutated:
            mutated = True
            case.repository.ignored.write_bytes(b"mutated-input\n")
        return chunk

    monkeypatch.setattr(module.os, "read", mutate_after_read)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    _assert_denied(result)
    assert result.reason == "IGNORED_INPUT_SOURCE_CHANGED"


def test_remediation_i4_oversized_or_replaced_source_read_is_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    original_read = module.os.read
    requested: list[int] = []

    def record_read_size(descriptor: int, size: int) -> bytes:
        requested.append(size)
        return original_read(descriptor, size)

    monkeypatch.setattr(module.os, "read", record_read_size)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    assert requested
    assert max(requested) <= len(case.repository.ignored.read_bytes()) + 1
    _assert_pending_persistence_contract(result, case.authority)


def test_remediation_i4_concurrent_target_creation_never_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    target = case.workspace.root / "ignored" / "input.txt"
    original_open = module.os.open
    injected = False

    def create_competing_target(
        path: object,
        flags: int,
        *args: object,
        **kwargs: object,
    ):
        nonlocal injected
        if flags & os.O_CREAT and not injected:
            injected = True
            target.write_bytes(b"competitor\n")
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(module.os, "open", create_competing_target)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    _assert_denied(result)
    assert target.read_bytes() == b"competitor\n"
    assert result.reason == "IGNORED_INPUT_TARGET_CONFLICT"


def test_remediation_i4_existing_target_inode_and_content_preserved(
    tmp_path: Path,
) -> None:
    case = _valid_case(tmp_path)
    target = case.workspace.root / "ignored" / "input.txt"
    target.parent.mkdir()
    target.write_bytes(b"existing\n")
    before = target.stat()
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    _assert_denied(result)
    after = target.stat()
    assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)
    assert target.read_bytes() == b"existing\n"
    assert result.reason == "IGNORED_INPUT_TARGET_CONFLICT"


def test_remediation_i4_publish_failure_removes_owned_temporary_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    link_calls = 0

    def fail_link(*args: object, **kwargs: object) -> None:
        nonlocal link_calls
        link_calls += 1
        raise OSError("injected no-clobber publish failure")

    monkeypatch.setattr(module.os, "link", fail_link)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    _assert_denied(result)
    assert link_calls == 1
    assert not tuple(case.workspace.root.rglob(".wp11-ignored-*"))
    assert not (case.workspace.root / "ignored" / "input.txt").exists()
    assert result.cleanup_complete is True


def test_remediation_i4_unsupported_no_clobber_primitive_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    monkeypatch.setattr(module.os, "supports_dir_fd", set())
    monkeypatch.setattr(module.os, "supports_follow_symlinks", set())
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    _assert_denied(result)
    assert result.reason == "IGNORED_INPUT_NO_CLOBBER_UNSUPPORTED"
    assert not (case.workspace.root / "ignored" / "input.txt").exists()


def _authority_with_stable_binding(
    *,
    baseline: BaselineManifest,
    path: str,
    content: bytes,
    manifest_identity: str,
    mode: str = _READ_ONLY,
    task_id: str = "task:1",
    plan_identity: str = "plan:1",
    idempotency_key: str = "ignored:key:action:ignored:1",
) -> SimpleNamespace:
    authority = _authority(
        baseline=baseline,
        path=path,
        kind="regular_file",
        size=len(content),
        content_digest=_digest(content),
        mode=mode,
        manifest_identity=manifest_identity,
    )
    plan = PlanVersion(
        identity=plan_identity,
        task_id=task_id,
        sequence=1,
        content_digest="1" * 64,
        display_text="Plan",
    )
    policy = replace(
        authority.policy,
        bound_task_id=task_id,
        bound_idempotency_key=idempotency_key,
    )
    approval = replace(
        authority.approval,
        task_id=task_id,
        plan_version=plan,
        idempotency_key=idempotency_key,
        policy_record_digest=policy_record_digest(policy),
    )
    context = replace(
        authority.context,
        task_id=task_id,
        plan_version_identity=plan_identity,
        idempotency_key=idempotency_key,
        policy_record_digest=approval.policy_record_digest,
    )
    return SimpleNamespace(approval=approval, context=context, policy=policy)


def _replacement_repository(tmp_path: Path, content: bytes) -> SimpleNamespace:
    parent = tmp_path / "replacement-fixture"
    parent.mkdir()
    repository = _repository(parent)
    repository.ignored.write_bytes(content)
    return repository


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate fixture key")
        result[key] = value
    return result


def _reject_nonfinite_json(value: str) -> object:
    raise ValueError("non-finite fixture number: " + value)


def _frozen_identity_vectors() -> dict[str, dict[str, object]]:
    document = json.loads(
        _VECTOR_FIXTURE.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_json_keys,
        parse_constant=_reject_nonfinite_json,
    )
    assert type(document) is dict
    assert document.get("fixture_schema") == "wp11-identity-v1-evidence:1"
    algorithm = document.get("identity_algorithm")
    assert type(algorithm) is dict
    assert algorithm == {
        "name": "typed-length-prefixed-binary-sha256",
        "status": "approved",
        "version": 1,
    }
    vectors = document.get("vectors")
    assert type(vectors) is list
    indexed: dict[str, dict[str, object]] = {}
    for vector in vectors:
        assert type(vector) is dict
        vector_id = vector.get("id")
        assert type(vector_id) is str and vector_id
        assert vector_id not in indexed
        assert type(vector.get("input")) is dict
        assert type(vector.get("derived")) is dict
        expected = vector.get("expected")
        assert type(expected) is dict
        for field in ("workspace_logical_identity", "expected_manifest_identity"):
            value = expected.get(field)
            assert (
                type(value) is str
                and len(value) == 64
                and set(value) <= set("0123456789abcdef")
            )
        for field in ("workspace_canonical_stream_length", "canonical_stream_length"):
            value = expected.get(field)
            assert type(value) is int and value > 0
        indexed[vector_id] = vector
    assert set(indexed) == {
        "genesis-minimal",
        "genesis-multi",
        "continuation-single-entry",
    }
    return indexed


def _identity_api() -> SimpleNamespace:
    module = importlib.import_module("coding_harness.workspace.ignored")
    names = (
        "compute_expected_manifest_identity",
        "ExpectedManifestIdentityRequest",
        "ExpectedManifestEntry",
        "PreviousSandboxInputManifestRef",
        "ExpectedManifestIdentityResult",
        "ExpectedManifestIdentityError",
        "ExpectedManifestIdentityReason",
    )
    missing = tuple(name for name in names if getattr(module, name, None) is None)
    if missing:
        pytest.fail(
            _IDENTITY_EXPECTED_RED + ": " + ", ".join(missing),
            pytrace=False,
        )
    values = {name: getattr(module, name) for name in names}
    values["IgnoredInputKind"] = module.IgnoredInputKind
    values["IgnoredInputMode"] = module.IgnoredInputMode
    return SimpleNamespace(**values)


def _request_from_vector(
    api: SimpleNamespace,
    vector: dict[str, object],
):
    data = vector["input"]
    assert type(data) is dict
    previous_data = data["previous"]
    assert type(previous_data) is dict
    if previous_data["variant"] == "genesis":
        previous = None
    else:
        assert previous_data["variant"] == "continuation"
        previous = api.PreviousSandboxInputManifestRef(
            revision=previous_data["revision"],
            identity=previous_data["identity"],
            digest=previous_data["digest"],
        )
    raw_entries = data["entries"]
    assert type(raw_entries) is list
    entries = tuple(
        api.ExpectedManifestEntry(
            source=RepoPath.parse(raw["source_repo_path"]),
            kind=api.IgnoredInputKind(raw["file_type"]),
            approved_size=raw["approved_size"],
            content_digest=raw["content_digest"],
            mode=api.IgnoredInputMode(raw["mode"]),
            allowed_stages=tuple(raw["allowed_stages"]),
        )
        for raw in raw_entries
    )
    limits = data["validation_limits"]
    assert type(limits) is dict
    return api.ExpectedManifestIdentityRequest(
        task_id=data["task_id"],
        plan_version_identity=data["plan_version_identity"],
        baseline_digest=data["baseline_digest"],
        previous_manifest=previous,
        new_revision=data["new_revision"],
        entries=entries,
        idempotency_key=data["idempotency_key"],
        max_input_count=limits["max_input_count"],
        max_input_bytes=limits["max_input_bytes"],
    )


def _runtime_request(
    api: SimpleNamespace,
    *,
    baseline: BaselineManifest,
    path: str,
    content: bytes,
    task_id: str = "task:1",
    plan_identity: str = "plan:1",
    mode: str = _READ_ONLY,
    stages: tuple[str, ...] = ("EXECUTING",),
    idempotency_key: str = "ignored:key:action:ignored:1",
):
    return api.ExpectedManifestIdentityRequest(
        task_id=task_id,
        plan_version_identity=plan_identity,
        baseline_digest=baseline.digest,
        previous_manifest=None,
        new_revision=1,
        entries=(
            api.ExpectedManifestEntry(
                source=RepoPath.parse(path),
                kind=api.IgnoredInputKind.REGULAR_FILE,
                approved_size=len(content),
                content_digest=_digest(content),
                mode=api.IgnoredInputMode(mode),
                allowed_stages=stages,
            ),
        ),
        idempotency_key=idempotency_key,
        max_input_count=1,
        max_input_bytes=len(content),
    )


def _mutate_hex(value: str) -> str:
    return ("0" if value[0] != "0" else "1") + value[1:]


def _descriptor_replace(
    *,
    original_unlink: object,
    original_open: object,
    parent_fd: int,
    name: str,
    content: bytes,
) -> os.stat_result:
    original_unlink(name, dir_fd=parent_fd)
    descriptor = original_open(
        name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
        dir_fd=parent_fd,
    )
    try:
        view = memoryview(content)
        while view:
            written = os.write(descriptor, view)
            assert written > 0
            view = view[written:]
        return os.fstat(descriptor)
    finally:
        os.close(descriptor)


def test_cleanup_refuses_replaced_owned_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    original_link = module.os.link
    original_unlink = module.os.unlink
    original_open = module.os.open
    original_fsync = module.os.fsync
    replacement = b"replacement-object\n"
    replacement_status: os.stat_result | None = None
    published = False

    def replace_after_link(
        source: object,
        target: object,
        *args: object,
        **kwargs: object,
    ) -> None:
        nonlocal published, replacement_status
        original_link(source, target, *args, **kwargs)
        parent_fd = kwargs["dst_dir_fd"]
        replacement_status = _descriptor_replace(
            original_unlink=original_unlink,
            original_open=original_open,
            parent_fd=parent_fd,
            name=os.fspath(target),
            content=replacement,
        )
        published = True

    def fail_after_replacement(descriptor: int) -> None:
        if published:
            raise OSError("controlled descriptor-safe failure")
        original_fsync(descriptor)

    monkeypatch.setattr(module.os, "link", replace_after_link)
    monkeypatch.setattr(module.os, "fsync", fail_after_replacement)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    _assert_denied(result)
    target = case.workspace.root / "ignored" / "input.txt"
    assert replacement_status is not None
    assert target.exists()
    assert target.read_bytes() == replacement
    assert target.stat().st_ino == replacement_status.st_ino
    assert result.reason == "IGNORED_INPUT_CLEANUP_FAILED"
    assert result.cleanup_complete is False


def test_enotempty_is_cleanup_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    original_fsync = module.os.fsync
    original_rmdir = module.os.rmdir
    injected_write_failure = False
    rmdir_calls: list[tuple[object, object]] = []

    def fail_first_file_sync(descriptor: int) -> None:
        nonlocal injected_write_failure
        status = os.fstat(descriptor)
        if stat.S_ISREG(status.st_mode) and not injected_write_failure:
            injected_write_failure = True
            raise OSError("controlled owned temporary sync failure")
        original_fsync(descriptor)

    def fail_directory_cleanup(
        path: object,
        *args: object,
        **kwargs: object,
    ) -> None:
        rmdir_calls.append((path, kwargs.get("dir_fd")))
        raise OSError(getattr(os, "ENOTEMPTY", 39), "controlled nonempty")

    monkeypatch.setattr(module.os, "fsync", fail_first_file_sync)
    monkeypatch.setattr(module.os, "rmdir", fail_directory_cleanup)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    assert injected_write_failure is True
    assert rmdir_calls
    _assert_denied(result)
    assert result.reason == "IGNORED_INPUT_CLEANUP_FAILED"
    assert result.cleanup_complete is False
    monkeypatch.setattr(module.os, "rmdir", original_rmdir)


def test_cleanup_never_deletes_replacement_object(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    original_unlink = module.os.unlink
    original_open = module.os.open
    replacement_name: str | None = None
    replacement_content = b"replacement-temporary\n"

    def replace_owned_temporary(
        path: object,
        *args: object,
        **kwargs: object,
    ) -> None:
        nonlocal replacement_name
        name = os.fspath(path)
        parent_fd = kwargs.get("dir_fd")
        if (
            replacement_name is None
            and name.startswith(".wp11-ignored-")
            and type(parent_fd) is int
        ):
            _descriptor_replace(
                original_unlink=original_unlink,
                original_open=original_open,
                parent_fd=parent_fd,
                name=name,
                content=replacement_content,
            )
            replacement_name = name
            raise OSError("controlled descriptor-relative cleanup failure")
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(module.os, "unlink", replace_owned_temporary)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    _assert_denied(result)
    assert replacement_name is not None
    replacement_path = case.workspace.root / "ignored" / replacement_name
    assert replacement_path.exists()
    assert replacement_path.read_bytes() == replacement_content
    assert result.reason == "IGNORED_INPUT_CLEANUP_FAILED"
    assert result.cleanup_complete is False


def test_cleanup_close_failure_cannot_report_complete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    original_open = module.os.open
    original_close = module.os.close
    workspace_descriptors: set[int] = set()
    injected = False

    def track_workspace_root(
        path: object,
        flags: int,
        *args: object,
        **kwargs: object,
    ) -> int:
        descriptor = original_open(path, flags, *args, **kwargs)
        if Path(path) == case.workspace.root:
            workspace_descriptors.add(descriptor)
        return descriptor

    def fail_owned_descriptor_close(descriptor: int) -> None:
        nonlocal injected
        if descriptor in workspace_descriptors and not injected:
            injected = True
            original_close(descriptor)
            raise OSError("controlled descriptor close failure")
        original_close(descriptor)

    monkeypatch.setattr(module.os, "open", track_workspace_root)
    monkeypatch.setattr(module.os, "close", fail_owned_descriptor_close)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    assert injected is True
    _assert_denied(result)
    assert result.reason == "IGNORED_INPUT_CLEANUP_FAILED"
    assert result.cleanup_complete is False


def test_genesis_expected_identity_is_deterministic(tmp_path: Path) -> None:
    del tmp_path
    vectors = _frozen_identity_vectors()
    api = _identity_api()
    for vector_id in (
        "genesis-minimal",
        "genesis-multi",
        "continuation-single-entry",
    ):
        vector = vectors[vector_id]
        request = _request_from_vector(api, vector)
        result = api.compute_expected_manifest_identity(request)
        expected = vector["expected"]
        assert type(expected) is dict
        assert type(result) is api.ExpectedManifestIdentityResult
        assert (
            result.workspace_logical_identity
            == expected["workspace_logical_identity"]
        )
        assert (
            result.expected_manifest_identity
            == expected["expected_manifest_identity"]
        )

    continuation = _request_from_vector(
        api,
        vectors["continuation-single-entry"],
    )
    previous = continuation.previous_manifest
    assert type(previous) is api.PreviousSandboxInputManifestRef
    for changed_previous in (
        replace(previous, identity=_mutate_hex(previous.identity)),
        replace(previous, digest=_mutate_hex(previous.digest)),
    ):
        changed = api.compute_expected_manifest_identity(
            replace(continuation, previous_manifest=changed_previous)
        )
        original = api.compute_expected_manifest_identity(continuation)
        assert changed.expected_manifest_identity != original.expected_manifest_identity

    with pytest.raises(api.ExpectedManifestIdentityError) as invalid:
        api.compute_expected_manifest_identity(object())
    assert invalid.value.reason is api.ExpectedManifestIdentityReason.INVALID_REQUEST
    with pytest.raises(TypeError):
        api.compute_expected_manifest_identity(continuation, schema=1)


@pytest.mark.parametrize(
    "field",
    (
        "task",
        "plan-version",
        "baseline",
        "source-path",
        "source-digest",
        "mode",
        "stages",
        "idempotency-key",
    ),
)
def test_genesis_identity_binds_stable_request_field(
    tmp_path: Path,
    field: str,
) -> None:
    del tmp_path
    vector = _frozen_identity_vectors()["genesis-minimal"]
    api = _identity_api()
    request = _request_from_vector(api, vector)
    entry = request.entries[0]
    if field == "task":
        changed = replace(request, task_id=request.task_id + ":variant")
    elif field == "plan-version":
        changed = replace(
            request,
            plan_version_identity=request.plan_version_identity + ":variant",
        )
    elif field == "baseline":
        changed = replace(request, baseline_digest=_mutate_hex(request.baseline_digest))
    elif field == "source-path":
        changed_entry = replace(
            entry,
            source=RepoPath.parse("ignored/variant.txt"),
        )
        changed = replace(request, entries=(changed_entry,))
    elif field == "source-digest":
        changed_entry = replace(
            entry,
            content_digest=_mutate_hex(entry.content_digest),
        )
        changed = replace(request, entries=(changed_entry,))
    elif field == "mode":
        changed_entry = replace(
            entry,
            mode=api.IgnoredInputMode.WRITABLE_EPHEMERAL,
        )
        changed = replace(request, entries=(changed_entry,))
    elif field == "stages":
        changed_entry = replace(
            entry,
            allowed_stages=("EXECUTING", "VERIFYING"),
        )
        changed = replace(request, entries=(changed_entry,))
    else:
        changed = replace(
            request,
            idempotency_key=request.idempotency_key + ":variant",
        )

    original_result = api.compute_expected_manifest_identity(request)
    changed_result = api.compute_expected_manifest_identity(changed)
    assert (
        changed_result.expected_manifest_identity
        != original_result.expected_manifest_identity
    )


def test_approval_manifest_identity_must_match_computed_genesis_identity(
    tmp_path: Path,
) -> None:
    case = _valid_case(tmp_path)
    api = _identity_api()
    content = case.repository.ignored.read_bytes()
    request = _runtime_request(
        api,
        baseline=case.baseline,
        path="ignored/input.txt",
        content=content,
    )
    computed = api.compute_expected_manifest_identity(request)
    wrong_identity = _mutate_hex(computed.expected_manifest_identity)
    authority = _authority_with_stable_binding(
        baseline=case.baseline,
        path="ignored/input.txt",
        content=content,
        manifest_identity=wrong_identity,
    )
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=authority,
    )

    _assert_denied(result)
    assert result.approval_cas_intent is None
    assert result.candidate_manifest is None
    assert result.approval_result.approval is authority.approval
    assert result.approval_result.approval.consumed is False
    assert not (case.workspace.root / "ignored" / "input.txt").exists()


def test_shared_approval_identity_cannot_collapse_distinct_genesis_requests(
    tmp_path: Path,
) -> None:
    del tmp_path
    vectors = _frozen_identity_vectors()
    api = _identity_api()
    minimal = _request_from_vector(api, vectors["genesis-minimal"])
    changed_entry = replace(
        minimal.entries[0],
        source=RepoPath.parse("ignored/other.txt"),
    )
    other = replace(minimal, entries=(changed_entry,))
    first = api.compute_expected_manifest_identity(minimal)
    second = api.compute_expected_manifest_identity(other)
    assert first.expected_manifest_identity != second.expected_manifest_identity

    multi = _request_from_vector(api, vectors["genesis-multi"])
    reordered = replace(multi, entries=tuple(reversed(multi.entries)))
    relaxed_limits = replace(
        multi,
        max_input_count=multi.max_input_count + 10,
        max_input_bytes=multi.max_input_bytes + 10_000,
    )
    assert (
        api.compute_expected_manifest_identity(reordered)
        == api.compute_expected_manifest_identity(multi)
    )
    assert (
        api.compute_expected_manifest_identity(relaxed_limits)
        == api.compute_expected_manifest_identity(multi)
    )


def test_source_root_path_replacement_cannot_change_opened_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    replacement = _replacement_repository(
        tmp_path,
        case.repository.ignored.read_bytes(),
    )
    module = importlib.import_module("coding_harness.workspace.ignored")
    original_open = module.os.open
    source_root_opens = 0
    replaced = False
    saved = tmp_path / "original-authority"

    def replace_after_descriptor_open(
        path: object,
        flags: int,
        *args: object,
        **kwargs: object,
    ) -> int:
        nonlocal source_root_opens, replaced
        descriptor = original_open(path, flags, *args, **kwargs)
        if Path(path) == case.repository.root:
            source_root_opens += 1
            if not replaced:
                replaced = True
                os.rename(case.repository.root, saved)
                os.rename(replacement.root, case.repository.root)
        return descriptor

    monkeypatch.setattr(module.os, "open", replace_after_descriptor_open)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    assert replaced is True
    assert source_root_opens == 1
    _assert_denied(result)
    assert not (case.workspace.root / "ignored" / "input.txt").exists()


def test_ignore_validation_uses_same_descriptor_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    original_open = module.os.open
    original_close = module.os.close
    original_spawn = module.os.posix_spawnp
    live_source_roots: set[int] = set()
    authority_seen = False

    def track_source_descriptor(
        path: object,
        flags: int,
        *args: object,
        **kwargs: object,
    ) -> int:
        descriptor = original_open(path, flags, *args, **kwargs)
        if Path(path) == case.repository.root:
            live_source_roots.add(descriptor)
        return descriptor

    def track_close(descriptor: int) -> None:
        live_source_roots.discard(descriptor)
        original_close(descriptor)

    def require_live_authority(*args: object, **kwargs: object) -> int:
        nonlocal authority_seen
        authority_seen = any(
            stat.S_ISDIR(os.fstat(descriptor).st_mode)
            for descriptor in live_source_roots
        )
        return original_spawn(*args, **kwargs)

    monkeypatch.setattr(module.os, "open", track_source_descriptor)
    monkeypatch.setattr(module.os, "close", track_close)
    monkeypatch.setattr(module.os, "posix_spawnp", require_live_authority)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    assert authority_seen is True
    _assert_pending_persistence_contract(result, case.authority)


def test_post_publish_mode_change_never_targets_replacement_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    original_link = module.os.link
    original_unlink = module.os.unlink
    original_open = module.os.open
    original_fchmod = module.os.fchmod
    replacement = b"replacement-after-link\n"
    replacement_status: os.stat_result | None = None
    fchmod_before_link = False
    linked = False

    def record_fchmod(descriptor: int, mode: int) -> None:
        nonlocal fchmod_before_link
        assert linked is False
        fchmod_before_link = True
        original_fchmod(descriptor, mode)

    def replace_after_link(
        source: object,
        target: object,
        *args: object,
        **kwargs: object,
    ) -> None:
        nonlocal linked, replacement_status
        original_link(source, target, *args, **kwargs)
        linked = True
        replacement_status = _descriptor_replace(
            original_unlink=original_unlink,
            original_open=original_open,
            parent_fd=kwargs["dst_dir_fd"],
            name=os.fspath(target),
            content=replacement,
        )

    monkeypatch.setattr(module.os, "fchmod", record_fchmod)
    monkeypatch.setattr(module.os, "link", replace_after_link)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    target = case.workspace.root / "ignored" / "input.txt"
    assert fchmod_before_link is True
    assert replacement_status is not None
    assert target.exists()
    assert target.read_bytes() == replacement
    assert target.stat().st_ino == replacement_status.st_ino
    _assert_denied(result)


def test_cleanup_unlink_requires_parent_fd_and_inode_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    original_link = module.os.link
    original_unlink = module.os.unlink
    original_open = module.os.open
    original_fsync = module.os.fsync
    replacement = b"replacement-before-cleanup\n"
    replacement_status: os.stat_result | None = None
    published = False
    unlink_calls: list[tuple[object, object]] = []

    def replace_published_inode(
        source: object,
        target: object,
        *args: object,
        **kwargs: object,
    ) -> None:
        nonlocal published, replacement_status
        original_link(source, target, *args, **kwargs)
        replacement_status = _descriptor_replace(
            original_unlink=original_unlink,
            original_open=original_open,
            parent_fd=kwargs["dst_dir_fd"],
            name=os.fspath(target),
            content=replacement,
        )
        published = True

    def fail_after_publish(descriptor: int) -> None:
        if published:
            raise OSError("controlled post-publish failure")
        original_fsync(descriptor)

    def record_descriptor_unlink(
        path: object,
        *args: object,
        **kwargs: object,
    ) -> None:
        unlink_calls.append((path, kwargs.get("dir_fd")))
        original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(module.os, "link", replace_published_inode)
    monkeypatch.setattr(module.os, "fsync", fail_after_publish)
    monkeypatch.setattr(module.os, "unlink", record_descriptor_unlink)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    target = case.workspace.root / "ignored" / "input.txt"
    _assert_denied(result)
    assert replacement_status is not None
    assert target.exists()
    assert target.read_bytes() == replacement
    assert target.stat().st_ino == replacement_status.st_ino
    assert all(dir_fd is not None for _, dir_fd in unlink_calls)
    assert result.cleanup_complete is False


def test_directory_cleanup_cannot_follow_replaced_parent_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    module = importlib.import_module("coding_harness.workspace.ignored")
    parent = case.workspace.root / "ignored"
    moved_parent = case.workspace.root / "owned-parent-moved"
    replacement_marker = parent / "replacement.txt"
    original_open = module.os.open
    replaced = False

    def replace_parent_at_descriptor_boundary(
        path: object,
        flags: int,
        *args: object,
        **kwargs: object,
    ) -> int:
        nonlocal replaced
        if flags & os.O_CREAT and kwargs.get("dir_fd") is not None and not replaced:
            replaced = True
            os.rename(parent, moved_parent)
            os.mkdir(parent)
            replacement_marker.write_bytes(b"replacement-tree\n")
            raise OSError("controlled descriptor-relative open failure")
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(module.os, "open", replace_parent_at_descriptor_boundary)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    _assert_denied(result)
    assert replaced is True
    assert replacement_marker.read_bytes() == b"replacement-tree\n"
    assert result.reason == "IGNORED_INPUT_CLEANUP_FAILED"
    assert result.cleanup_complete is False


def test_root_descriptor_authority_remains_continuous(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _valid_case(tmp_path)
    original_content = case.repository.ignored.read_bytes()
    replacement_content = b"replacement-root-content\n"
    replacement = _replacement_repository(tmp_path, replacement_content)
    saved = tmp_path / "original-root-authority"
    module = importlib.import_module("coding_harness.workspace.ignored")
    original_open = module.os.open
    original_close = module.os.close
    original_spawn = module.os.posix_spawnp
    original_waitpid = module.os.waitpid
    authority_descriptors: set[int] = set()
    events: list[tuple[str, int]] = []
    source_root_fd: int | None = None
    source_root_live = False
    ignore_pid: int | None = None
    replaced = False

    def track_source_root(
        path: object,
        flags: int,
        *args: object,
        **kwargs: object,
    ) -> int:
        nonlocal replaced, source_root_fd, source_root_live
        parent_fd = kwargs.get("dir_fd")
        if (
            parent_fd in authority_descriptors
            and not replaced
        ):
            replaced = True
            os.rename(case.repository.root, saved)
            os.rename(replacement.root, case.repository.root)
        descriptor = original_open(path, flags, *args, **kwargs)
        if Path(path) == case.repository.root:
            source_root_fd = descriptor
            source_root_live = True
            authority_descriptors.add(descriptor)
            events.append(("root_open", descriptor))
        elif parent_fd in authority_descriptors:
            authority_descriptors.add(descriptor)
            events.append(("root_authority_use", int(parent_fd)))
        return descriptor

    def track_source_close(descriptor: int) -> None:
        nonlocal source_root_live
        if descriptor == source_root_fd and source_root_live:
            events.append(("root_close", descriptor))
            source_root_live = False
        authority_descriptors.discard(descriptor)
        original_close(descriptor)

    def track_ignore_start(*args: object, **kwargs: object) -> int:
        nonlocal ignore_pid
        assert source_root_fd is not None
        events.append(("ignore_validation_start", source_root_fd))
        ignore_pid = original_spawn(*args, **kwargs)
        return ignore_pid

    def track_ignore_completion(
        process: int,
        options: int,
    ) -> tuple[int, int]:
        waited = original_waitpid(process, options)
        if process == ignore_pid:
            assert source_root_fd is not None
            events.append(("ignore_validation_complete", source_root_fd))
            events.append(("root_authority_use", source_root_fd))
        return waited

    monkeypatch.setattr(module.os, "open", track_source_root)
    monkeypatch.setattr(module.os, "close", track_source_close)
    monkeypatch.setattr(module.os, "posix_spawnp", track_ignore_start)
    monkeypatch.setattr(module.os, "waitpid", track_ignore_completion)
    result = _invoke(
        case.api,
        source_root=case.repository.root,
        baseline=case.baseline,
        workspace=case.workspace,
        authority=case.authority,
    )

    assert source_root_fd is not None
    root_events = [
        (position, kind)
        for position, (kind, descriptor) in enumerate(events)
        if descriptor == source_root_fd
    ]
    assert [kind for _, kind in root_events].count("root_open") == 1
    assert [kind for _, kind in root_events].count("root_close") == 1
    root_open = next(
        position for position, kind in root_events if kind == "root_open"
    )
    ignore_complete = next(
        position
        for position, kind in root_events
        if kind == "ignore_validation_complete"
    )
    last_authority_use = max(
        position
        for position, kind in root_events
        if kind == "root_authority_use"
    )
    root_close = next(
        position for position, kind in root_events if kind == "root_close"
    )
    assert root_open < ignore_complete <= last_authority_use < root_close
    assert replaced is True
    target = case.workspace.root / "ignored" / "input.txt"
    assert target.read_bytes() == original_content
    assert target.read_bytes() != replacement_content
    assert case.repository.ignored.read_bytes() == replacement_content
    _assert_pending_persistence_contract(result, case.authority)
