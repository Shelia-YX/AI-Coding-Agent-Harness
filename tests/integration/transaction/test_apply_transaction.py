"""WP-14 durable Apply Transaction integration contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
from types import SimpleNamespace

import pytest

from coding_harness.domain.enums import TaskState
from coding_harness.transaction.conflicts import ApplyConfirmation
from coding_harness.workspace.changeset import compute_changeset
from coding_harness.workspace.manifest import build_baseline
from coding_harness.workspace.materialize import materialize_workspace


OWNED_REQUIREMENTS = (
    "TXN-009",
    "TXN-010",
    "TXN-011",
    "TXN-012",
    "TXN-013",
    "TXN-014",
    "TXN-015",
    "TXN-016",
    "TXN-019",
)
FOUNDATIONAL_REQUIREMENTS = ("TXN-001", "TXN-002", "TXN-003", "TXN-004")
_EXPECTED_RED = "WP-14 production API is not implemented"


def _api() -> SimpleNamespace:
    required: dict[str, object] = {}
    modules: dict[str, object] = {}
    missing_module: str | None = None
    for module_name, names in (
        (
            "coding_harness.transaction.models",
            (
                "ApplyDecision",
                "ApplyPhase",
                "ApplyPlan",
                "ApplyResult",
                "JournalStage",
                "JournalStatus",
                "RecoveryState",
            ),
        ),
        (
            "coding_harness.transaction.journal",
            ("ApplyJournal",),
        ),
        (
            "coding_harness.transaction.apply",
            ("ApplyCoordinator", "UncertainEffectError"),
        ),
        (
            "coding_harness.transaction.recovery",
            ("RecoveryCoordinator",),
        ),
    ):
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name == module_name:
                missing_module = module_name
                break
            raise
        modules[module_name.rsplit(".", 1)[-1] + "_module"] = module
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
    return SimpleNamespace(**required, **modules)


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
) -> SimpleNamespace:
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q")
    for relative, content in files.items():
        destination = origin / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    _git(origin, "add", "--", *sorted(files))
    _git(
        origin,
        "-c",
        "user.name=WP14 Test",
        "-c",
        "user.email=wp14@example.invalid",
        "commit",
        "-q",
        "-m",
        "fixture",
    )
    baseline = build_baseline(origin)
    workspace = materialize_workspace(baseline, tmp_path / "workspace")
    return SimpleNamespace(
        origin=origin,
        baseline=baseline,
        workspace=workspace,
        transaction_root=tmp_path / "private-transactions",
    )


def _confirmation(scenario: SimpleNamespace, changeset) -> ApplyConfirmation:
    return ApplyConfirmation(
        task_id="task:wp14",
        changeset_digest=changeset.digest,
        baseline_manifest_digest=scenario.baseline.digest,
        plan_version_identity="plan:wp14:1",
        acceptance_contract_version_identity="contract:wp14:1",
        expected_state=TaskState.READY_TO_APPLY,
        idempotency_key="apply:wp14:1",
    )


def _changeset(scenario: SimpleNamespace):
    return compute_changeset(scenario.baseline, scenario.workspace)


def _apply(
    api: SimpleNamespace,
    scenario: SimpleNamespace,
    changeset,
    *,
    decision=None,
    transaction_id: str = "txn:wp14:1",
):
    coordinator = api.ApplyCoordinator(scenario.transaction_root)
    selected_decision = (
        api.ApplyDecision.APPLY if decision is None else decision
    )
    return coordinator.apply(
        transaction_id=transaction_id,
        baseline=scenario.baseline,
        changeset=changeset,
        workspace=scenario.workspace,
        target_root=scenario.origin,
        decision=selected_decision,
        confirmation=(
            _confirmation(scenario, changeset)
            if selected_decision is api.ApplyDecision.APPLY
            else None
        ),
        current_task_id="task:wp14",
        current_plan_version_identity="plan:wp14:1",
        current_acceptance_contract_version_identity="contract:wp14:1",
        current_state=TaskState.READY_TO_APPLY,
        current_idempotency_key="apply:wp14:1",
        acceptance_satisfied=True,
        nonterminal_apply_transaction=False,
        recovery_required=False,
        policy_denied=False,
    )


def _modified(
    tmp_path: Path,
    files: dict[str, bytes] | None = None,
) -> tuple[SimpleNamespace, object]:
    originals = files or {"target.txt": b"baseline\n"}
    scenario = _scenario(tmp_path, originals)
    for relative in sorted(originals):
        (scenario.workspace.root / relative).write_bytes(
            b"agent:" + relative.encode("utf-8") + b"\n"
        )
    return scenario, _changeset(scenario)


def _records(result, *, stage=None, status=None, path: str | None = None):
    records = result.journal.records
    return tuple(
        record
        for record in records
        if (stage is None or record.stage is stage)
        and (status is None or record.status is status)
        and (
            path is None
            or (
                record.path is not None
                and record.path.canonical == path
            )
        )
    )


def test_successful_apply(tmp_path: Path) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)

    result = _apply(api, scenario, changeset)

    assert (scenario.origin / "target.txt").read_bytes() == b"agent:target.txt\n"
    assert result.phase is api.ApplyPhase.APPLIED
    assert result.task_state is TaskState.COMPLETED
    assert result.recovery_state is api.RecoveryState.SUCCESS


def test_transaction_journal_records_required_stages(tmp_path: Path) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)

    result = _apply(api, scenario, changeset)

    assert tuple(dict.fromkeys(record.stage for record in result.journal.records)) == (
        api.JournalStage.PREPARE,
        api.JournalStage.BACKUP,
        api.JournalStage.APPLY,
        api.JournalStage.VERIFY,
    )
    assert result.journal.path.is_file()
    assert result.journal.path.read_bytes().endswith(b"\n")
    assert tuple(record.order for record in result.journal.records) == tuple(
        range(1, len(result.journal.records) + 1)
    )


def test_plan_immutable(tmp_path: Path) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    result = _apply(api, scenario, changeset)

    assert type(result.plan) is api.ApplyPlan
    with pytest.raises(FrozenInstanceError):
        result.plan.transaction_id = "txn:tampered"


def test_backup_before_write(tmp_path: Path) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)

    result = _apply(api, scenario, changeset)

    backup_completed = _records(
        result,
        stage=api.JournalStage.BACKUP,
        status=api.JournalStatus.COMPLETED,
        path="target.txt",
    )[0]
    apply_pending = _records(
        result,
        stage=api.JournalStage.APPLY,
        status=api.JournalStatus.PENDING,
        path="target.txt",
    )[0]
    assert backup_completed.order < apply_pending.order


def test_backup_digest(tmp_path: Path) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)

    result = _apply(api, scenario, changeset)

    entry = result.plan.entries[0]
    backup = result.journal.root / entry.backup_relative_path
    assert backup.read_bytes() == b"baseline\n"
    assert entry.backup_digest == hashlib.sha256(b"baseline\n").hexdigest()


def test_phase_before_effect(tmp_path: Path) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)

    result = _apply(api, scenario, changeset)

    phase_record = next(
        record
        for record in result.journal.records
        if record.stage is api.JournalStage.APPLY
        and record.path is None
        and record.phase is api.ApplyPhase.APPLYING
    )
    effect_record = _records(
        result,
        stage=api.JournalStage.APPLY,
        status=api.JournalStatus.PENDING,
        path="target.txt",
    )[0]
    assert phase_record.order < effect_record.order


def test_pending_completed(tmp_path: Path) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)

    result = _apply(api, scenario, changeset)

    pending = _records(
        result,
        stage=api.JournalStage.APPLY,
        status=api.JournalStatus.PENDING,
        path="target.txt",
    )[0]
    completed = _records(
        result,
        stage=api.JournalStage.APPLY,
        status=api.JournalStatus.COMPLETED,
        path="target.txt",
    )[0]
    assert pending.order < completed.order


def test_success_rechecks(tmp_path: Path) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)

    result = _apply(api, scenario, changeset)

    verify = _records(
        result,
        stage=api.JournalStage.VERIFY,
        status=api.JournalStatus.COMPLETED,
    )
    assert len(verify) >= 2
    assert result.plan.changeset_digest == changeset.digest
    assert result.plan.baseline_digest == scenario.baseline.digest
    assert result.plan.index_digest_before == result.index_digest_after


def test_unstaged_write(tmp_path: Path) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    index_before = _git(
        scenario.origin,
        "ls-files",
        "--stage",
        "-z",
    ).stdout

    result = _apply(api, scenario, changeset)

    index_after = _git(
        scenario.origin,
        "ls-files",
        "--stage",
        "-z",
    ).stdout
    assert result.phase is api.ApplyPhase.APPLIED
    assert index_after == index_before
    assert _git(scenario.origin, "diff", "--cached", "--quiet").returncode == 0


def test_second_write_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = _api()
    scenario, changeset = _modified(
        tmp_path,
        {"a.txt": b"a:baseline\n", "b.txt": b"b:baseline\n"},
    )
    original_publish = api.apply_module._publish_entry
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected second write failure")
        return original_publish(*args, **kwargs)

    monkeypatch.setattr(api.apply_module, "_publish_entry", fail_second)

    result = _apply(api, scenario, changeset)

    assert result.phase is api.ApplyPhase.ROLLED_BACK
    assert result.task_state is TaskState.FAILED
    assert result.recovery_state is api.RecoveryState.FAILED
    assert (scenario.origin / "a.txt").read_bytes() == b"a:baseline\n"
    assert (scenario.origin / "b.txt").read_bytes() == b"b:baseline\n"


def test_reverse_rollback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    api = _api()
    scenario, changeset = _modified(
        tmp_path,
        {
            "a.txt": b"a:baseline\n",
            "b.txt": b"b:baseline\n",
            "c.txt": b"c:baseline\n",
        },
    )
    original_publish = api.apply_module._publish_entry
    original_restore = api.apply_module._restore_entry
    publish_calls = 0
    restored: list[str] = []

    def fail_third(*args, **kwargs):
        nonlocal publish_calls
        publish_calls += 1
        if publish_calls == 3:
            raise OSError("injected third write failure")
        return original_publish(*args, **kwargs)

    def record_restore(*args, **kwargs):
        entry = args[1]
        restored.append(entry.path.canonical)
        return original_restore(*args, **kwargs)

    monkeypatch.setattr(api.apply_module, "_publish_entry", fail_third)
    monkeypatch.setattr(api.apply_module, "_restore_entry", record_restore)

    result = _apply(api, scenario, changeset)

    assert result.phase is api.ApplyPhase.ROLLED_BACK
    assert restored == ["b.txt", "a.txt"]


def test_rollback_failure_requires_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(
        tmp_path,
        {"a.txt": b"a:baseline\n", "b.txt": b"b:baseline\n"},
    )
    original_publish = api.apply_module._publish_entry
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected apply failure")
        return original_publish(*args, **kwargs)

    def fail_restore(*args, **kwargs):
        raise OSError("injected rollback failure")

    monkeypatch.setattr(api.apply_module, "_publish_entry", fail_second)
    monkeypatch.setattr(api.apply_module, "_restore_entry", fail_restore)

    result = _apply(api, scenario, changeset)

    assert result.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert result.task_state is TaskState.RECOVERY_REQUIRED
    assert result.recovery_state is api.RecoveryState.RECOVERY_REQUIRED
    assert (scenario.origin / "a.txt").read_bytes() == b"agent:a.txt\n"


def test_original_repository_protection(tmp_path: Path) -> None:
    scenario = _scenario(tmp_path, {"target.txt": b"baseline\n"})
    (scenario.workspace.root / "target.txt").write_bytes(b"agent\n")

    assert (scenario.origin / "target.txt").read_bytes() == b"baseline\n"
    assert (scenario.workspace.root / "target.txt").read_bytes() == b"agent\n"


def test_verification_failure_rolls_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    monkeypatch.setattr(api.apply_module, "_verify_applied", lambda *args: False)

    result = _apply(api, scenario, changeset)

    assert result.phase is api.ApplyPhase.ROLLED_BACK
    assert result.task_state is TaskState.FAILED
    assert (scenario.origin / "target.txt").read_bytes() == b"baseline\n"


def test_user_rejection_is_not_applied(tmp_path: Path) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)

    result = _apply(
        api,
        scenario,
        changeset,
        decision=api.ApplyDecision.REJECT,
    )

    assert result.phase is None
    assert result.task_state is TaskState.NOT_APPLIED
    assert result.recovery_state is None
    assert result.journal is None
    assert (scenario.origin / "target.txt").read_bytes() == b"baseline\n"


def test_unprovable_requires_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    original_publish = api.apply_module._publish_entry

    def publish_then_lose_certainty(*args, **kwargs):
        original_publish(*args, **kwargs)
        raise api.UncertainEffectError("injected uncertain effect")

    monkeypatch.setattr(
        api.apply_module,
        "_publish_entry",
        publish_then_lose_certainty,
    )

    result = _apply(api, scenario, changeset)
    recovery = api.RecoveryCoordinator(scenario.transaction_root).recover(
        transaction_id=result.transaction_id,
        target_root=scenario.origin,
    )

    assert result.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert result.task_state is TaskState.RECOVERY_REQUIRED
    assert result.recovery_state is api.RecoveryState.RECOVERY_REQUIRED
    assert recovery.recovery_state is api.RecoveryState.RECOVERY_REQUIRED
    assert recovery.task_state is TaskState.RECOVERY_REQUIRED


def test_changeset_digest_mismatch_rejected_before_write(tmp_path: Path) -> None:
    api = _api()
    scenario, approved = _modified(tmp_path)
    (scenario.workspace.root / "target.txt").write_bytes(b"changed-after-approval\n")

    result = _apply(api, scenario, approved)

    assert result.phase is None
    assert result.task_state is TaskState.READY_TO_APPLY
    assert result.recovery_state is None
    assert result.journal is None
    assert (scenario.origin / "target.txt").read_bytes() == b"baseline\n"


def test_external_change_between_writes_rolls_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(
        tmp_path,
        {"a.txt": b"a:baseline\n", "b.txt": b"b:baseline\n"},
    )
    original_record = api.ApplyJournal.record

    def change_second_target(self, stage, status, **kwargs):
        record = original_record(self, stage, status, **kwargs)
        path = kwargs.get("path")
        if (
            stage is api.JournalStage.APPLY
            and status is api.JournalStatus.COMPLETED
            and path is not None
            and path.canonical == "a.txt"
        ):
            (scenario.origin / "b.txt").write_bytes(b"external\n")
        return record

    monkeypatch.setattr(api.ApplyJournal, "record", change_second_target)

    result = _apply(api, scenario, changeset)

    assert result.phase is api.ApplyPhase.ROLLED_BACK
    assert result.task_state is TaskState.FAILED
    assert (scenario.origin / "a.txt").read_bytes() == b"a:baseline\n"
    assert (scenario.origin / "b.txt").read_bytes() == b"external\n"


def test_rollback_does_not_overwrite_external_change_to_applied_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(
        tmp_path,
        {"a.txt": b"a:baseline\n", "b.txt": b"b:baseline\n"},
    )
    original_publish = api.apply_module._publish_entry
    calls = 0

    def change_first_then_fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            (scenario.origin / "a.txt").write_bytes(
                b"external-after-apply\n"
            )
            raise OSError("injected second write failure")
        return original_publish(*args, **kwargs)

    monkeypatch.setattr(
        api.apply_module,
        "_publish_entry",
        change_first_then_fail_second,
    )

    result = _apply(api, scenario, changeset)

    assert result.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert result.task_state is TaskState.RECOVERY_REQUIRED
    assert (scenario.origin / "a.txt").read_bytes() == b"external-after-apply\n"
    assert (scenario.origin / "b.txt").read_bytes() == b"b:baseline\n"


def test_parent_symlink_swap_cannot_write_outside_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"dir/target.txt": b"baseline\n"})
    (scenario.workspace.root / "dir" / "target.txt").unlink()
    changeset = _changeset(scenario)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "target.txt").write_bytes(b"outside\n")
    checked_parent = scenario.origin / "dir"
    displaced_parent = scenario.origin / "displaced-dir"
    original_unlink = os.unlink
    swapped = False

    def swap_parent_before_unlink(path, *args, **kwargs):
        nonlocal swapped
        if not swapped and Path(path).name == "target.txt":
            swapped = True
            os.rename(checked_parent, displaced_parent)
            os.symlink(outside, checked_parent, target_is_directory=True)
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(
        api.apply_module.os,
        "unlink",
        swap_parent_before_unlink,
    )

    result = _apply(api, scenario, changeset)

    assert swapped
    assert (outside / "target.txt").read_bytes() == b"outside\n"
    assert result.task_state is not TaskState.COMPLETED


def test_concurrent_leaf_write_during_publish_is_not_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    original_write = api.apply_module._write_regular_atomic
    raced = False

    def write_external_before_publish(*args, **kwargs):
        nonlocal raced
        if not raced:
            raced = True
            (scenario.origin / "target.txt").write_bytes(b"external-race\n")
        return original_write(*args, **kwargs)

    monkeypatch.setattr(
        api.apply_module,
        "_write_regular_atomic",
        write_external_before_publish,
    )

    result = _apply(api, scenario, changeset)

    assert raced
    assert result.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert result.task_state is TaskState.RECOVERY_REQUIRED
    assert (scenario.origin / "target.txt").read_bytes() == b"external-race\n"


def test_created_parent_rename_during_publish_requires_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"z.txt": b"baseline\n"})
    nested = scenario.workspace.root / "nested" / "deep" / "new.txt"
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b"agent:new\n")
    (scenario.workspace.root / "z.txt").write_bytes(b"agent:z\n")
    changeset = _changeset(scenario)
    original_link = os.link
    swapped = False

    def rename_created_parent_before_link(
        source,
        destination,
        *args,
        **kwargs,
    ):
        nonlocal swapped
        if not swapped and Path(destination).name == "new.txt":
            swapped = True
            os.rename(
                scenario.origin / "nested",
                scenario.origin / "displaced",
            )
            (scenario.origin / "nested" / "deep").mkdir(parents=True)
        return original_link(source, destination, *args, **kwargs)

    monkeypatch.setattr(
        api.apply_module.os,
        "link",
        rename_created_parent_before_link,
    )

    result = _apply(api, scenario, changeset)

    assert swapped
    assert result.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert result.task_state is TaskState.RECOVERY_REQUIRED
    assert (
        scenario.origin / "displaced" / "deep" / "new.txt"
    ).read_bytes() == b"agent:new\n"
    assert (scenario.origin / "nested" / "deep").is_dir()


def test_parent_rename_during_rollback_cannot_write_displaced_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario = _scenario(
        tmp_path,
        {
            "dir/a.txt": b"a:baseline\n",
            "z.txt": b"z:baseline\n",
        },
    )
    (scenario.workspace.root / "dir" / "a.txt").write_bytes(b"a:agent\n")
    (scenario.workspace.root / "z.txt").write_bytes(b"z:agent\n")
    changeset = _changeset(scenario)
    original_publish = api.apply_module._publish_entry
    original_write = api.apply_module._write_regular_atomic
    publish_calls = 0
    rollback_raced = False

    def fail_second_publish(*args, **kwargs):
        nonlocal publish_calls
        publish_calls += 1
        if publish_calls == 2:
            raise OSError("injected second publish failure")
        return original_publish(*args, **kwargs)

    def move_parent_before_restore(
        parent_descriptor,
        name,
        content,
        executable,
        temporary,
    ):
        nonlocal rollback_raced
        if content == b"a:baseline\n" and not rollback_raced:
            rollback_raced = True
            displaced = tmp_path / "displaced-dir"
            os.rename(scenario.origin / "dir", displaced)
            (displaced / "a.txt").write_bytes(b"external-displaced\n")
            (scenario.origin / "dir").mkdir()
            (scenario.origin / "dir" / "a.txt").write_bytes(b"a:baseline\n")
        return original_write(
            parent_descriptor,
            name,
            content,
            executable,
            temporary,
        )

    monkeypatch.setattr(api.apply_module, "_publish_entry", fail_second_publish)
    monkeypatch.setattr(
        api.apply_module,
        "_write_regular_atomic",
        move_parent_before_restore,
    )

    result = _apply(api, scenario, changeset)

    assert rollback_raced
    assert result.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert result.task_state is TaskState.RECOVERY_REQUIRED
    assert (tmp_path / "displaced-dir" / "a.txt").read_bytes() == (
        b"external-displaced\n"
    )


def test_terminal_recovery_failure_is_durably_blocking(tmp_path: Path) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    applied = _apply(api, scenario, changeset)
    (scenario.origin / "target.txt").write_bytes(b"unprovable-after-crash\n")

    recovered = api.RecoveryCoordinator(scenario.transaction_root).recover(
        transaction_id=applied.transaction_id,
        target_root=scenario.origin,
    )

    assert recovered.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert recovered.task_state is TaskState.RECOVERY_REQUIRED
    assert applied.journal.latest_phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert api.journal_module.has_blocking_transaction(
        scenario.transaction_root
    )


def test_nested_add_rollback_removes_created_parents(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"z.txt": b"baseline\n"})
    nested = scenario.workspace.root / "nested" / "deep" / "new.txt"
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b"agent:new\n")
    (scenario.workspace.root / "z.txt").write_bytes(b"agent:z\n")
    changeset = _changeset(scenario)
    original_publish = api.apply_module._publish_entry
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected failure after nested add")
        return original_publish(*args, **kwargs)

    monkeypatch.setattr(api.apply_module, "_publish_entry", fail_second)

    result = _apply(api, scenario, changeset)

    assert result.phase is api.ApplyPhase.ROLLED_BACK
    assert not (scenario.origin / "nested").exists()
    assert (scenario.origin / "z.txt").read_bytes() == b"baseline\n"


def test_terminal_rollback_recheck_requires_created_parents_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"z.txt": b"baseline\n"})
    nested = scenario.workspace.root / "nested" / "deep" / "new.txt"
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b"agent:new\n")
    (scenario.workspace.root / "z.txt").write_bytes(b"agent:z\n")
    changeset = _changeset(scenario)
    original_publish = api.apply_module._publish_entry
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected failure after nested add")
        return original_publish(*args, **kwargs)

    monkeypatch.setattr(api.apply_module, "_publish_entry", fail_second)
    rolled_back = _apply(api, scenario, changeset)
    assert rolled_back.phase is api.ApplyPhase.ROLLED_BACK
    (scenario.origin / "nested" / "deep").mkdir(parents=True)

    recovered = api.RecoveryCoordinator(scenario.transaction_root).recover(
        transaction_id=rolled_back.transaction_id,
        target_root=scenario.origin,
    )

    assert recovered.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert recovered.task_state is TaskState.RECOVERY_REQUIRED


def test_populated_transaction_parent_requires_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"z.txt": b"baseline\n"})
    nested = scenario.workspace.root / "nested" / "deep" / "new.txt"
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b"agent:new\n")
    (scenario.workspace.root / "z.txt").write_bytes(b"agent:z\n")
    changeset = _changeset(scenario)
    original_publish = api.apply_module._publish_entry
    calls = 0

    def populate_parent_then_fail(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            external = scenario.origin / "nested" / "deep" / "external.txt"
            external.write_bytes(b"external\n")
            raise OSError("injected failure after external directory change")
        return original_publish(*args, **kwargs)

    monkeypatch.setattr(
        api.apply_module,
        "_publish_entry",
        populate_parent_then_fail,
    )

    result = _apply(api, scenario, changeset)

    assert result.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert result.task_state is TaskState.RECOVERY_REQUIRED
    assert (
        scenario.origin / "nested" / "deep" / "external.txt"
    ).read_bytes() == b"external\n"


def test_pre_replace_failure_removes_transaction_temp_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)

    def fail_mode_update(*args, **kwargs):
        raise OSError("injected pre-replace failure")

    monkeypatch.setattr(api.apply_module.os, "fchmod", fail_mode_update)

    result = _apply(api, scenario, changeset)

    assert result.phase is api.ApplyPhase.ROLLED_BACK
    assert (scenario.origin / "target.txt").read_bytes() == b"baseline\n"
    assert tuple(scenario.origin.glob(".coding-harness-*")) == ()


@pytest.mark.parametrize("kind", ("delete", "symlink"))
def test_namespace_effect_fsyncs_repository_parent(
    kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"target.txt": b"baseline\n"})
    if kind == "delete":
        (scenario.workspace.root / "target.txt").unlink()
    else:
        os.symlink("target.txt", scenario.workspace.root / "link")
    changeset = _changeset(scenario)
    original_fsync = os.fsync
    fsynced_directories: set[Path] = set()

    def track_fsync(descriptor: int) -> None:
        status = os.fstat(descriptor)
        if stat.S_ISDIR(status.st_mode):
            try:
                fsynced_directories.add(
                    Path(os.readlink(f"/proc/self/fd/{descriptor}")).resolve()
                )
            except OSError:
                pass
        original_fsync(descriptor)

    monkeypatch.setattr(api.apply_module.os, "fsync", track_fsync)

    result = _apply(api, scenario, changeset)

    assert result.phase is api.ApplyPhase.APPLIED
    assert scenario.origin.resolve() in fsynced_directories


def test_supported_add_delete_symlink_and_mode_apply(tmp_path: Path) -> None:
    api = _api()
    scenario = _scenario(
        tmp_path,
        {
            "delete.txt": b"delete\n",
            "mode.sh": b"#!/bin/sh\n",
        },
    )
    (scenario.workspace.root / "delete.txt").unlink()
    (scenario.workspace.root / "added.txt").write_bytes(b"added\n")
    os.symlink("added.txt", scenario.workspace.root / "link")
    (scenario.workspace.root / "mode.sh").chmod(0o755)
    changeset = _changeset(scenario)

    result = _apply(api, scenario, changeset)

    assert result.phase is api.ApplyPhase.APPLIED
    assert not (scenario.origin / "delete.txt").exists()
    assert (scenario.origin / "added.txt").read_bytes() == b"added\n"
    assert os.readlink(scenario.origin / "link") == "added.txt"
    assert (scenario.origin / "mode.sh").stat().st_mode & 0o111


def test_corrupt_phase_sequence_is_rejected_and_blocks_apply(
    tmp_path: Path,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    result = _apply(api, scenario, changeset)
    lines = result.journal.path.read_bytes().splitlines()
    first = json.loads(lines[0])
    first["phase"] = api.ApplyPhase.APPLIED.value
    first["stage"] = api.JournalStage.VERIFY.value
    lines[0] = json.dumps(
        first,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    result.journal.path.write_bytes(b"\n".join(lines) + b"\n")

    with pytest.raises(ValueError, match="transaction journal is invalid"):
        _ = result.journal.records
    assert api.journal_module.has_blocking_transaction(
        scenario.transaction_root
    )


def test_terminal_journal_missing_file_completion_is_rejected(
    tmp_path: Path,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    result = _apply(api, scenario, changeset)
    payloads = [
        json.loads(line)
        for line in result.journal.path.read_bytes().splitlines()
    ]
    payloads = [
        payload
        for payload in payloads
        if not (
            payload["stage"] == api.JournalStage.APPLY.value
            and payload["status"] == api.JournalStatus.COMPLETED.value
            and payload["path"] == "target.txt"
            and payload["detail"] == "apply effect verified"
        )
    ]
    for order, payload in enumerate(payloads, 1):
        payload["order"] = order
    result.journal.path.write_bytes(
        b"".join(
            (
                json.dumps(
                    payload,
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8")
            for payload in payloads
        )
    )

    with pytest.raises(ValueError, match="transaction journal is invalid"):
        _ = result.journal.records
    assert api.journal_module.has_blocking_transaction(
        scenario.transaction_root
    )


def test_applied_journal_missing_backup_completion_is_rejected(
    tmp_path: Path,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    result = _apply(api, scenario, changeset)
    payloads = [
        json.loads(line)
        for line in result.journal.path.read_bytes().splitlines()
    ]
    payloads = [
        payload
        for payload in payloads
        if not (
            payload["stage"] == api.JournalStage.BACKUP.value
            and payload["status"] == api.JournalStatus.COMPLETED.value
            and payload["path"] == "target.txt"
        )
    ]
    for order, payload in enumerate(payloads, 1):
        payload["order"] = order
    result.journal.path.write_bytes(
        b"".join(
            (
                json.dumps(
                    payload,
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8")
            for payload in payloads
        )
    )

    with pytest.raises(ValueError, match="transaction journal is invalid"):
        _ = result.journal.records
    assert api.journal_module.has_blocking_transaction(
        scenario.transaction_root
    )


def test_rolled_back_journal_missing_restore_completion_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(
        tmp_path,
        {"a.txt": b"a:baseline\n", "b.txt": b"b:baseline\n"},
    )
    original_publish = api.apply_module._publish_entry
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected second write failure")
        return original_publish(*args, **kwargs)

    monkeypatch.setattr(api.apply_module, "_publish_entry", fail_second)
    result = _apply(api, scenario, changeset)
    assert result.phase is api.ApplyPhase.ROLLED_BACK
    payloads = [
        json.loads(line)
        for line in result.journal.path.read_bytes().splitlines()
    ]
    payloads = [
        payload
        for payload in payloads
        if not (
            payload["stage"] == api.JournalStage.ROLLBACK.value
            and payload["status"] == api.JournalStatus.COMPLETED.value
            and payload["path"] == "a.txt"
        )
    ]
    for order, payload in enumerate(payloads, 1):
        payload["order"] = order
    result.journal.path.write_bytes(
        b"".join(
            (
                json.dumps(
                    payload,
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8")
            for payload in payloads
        )
    )

    with pytest.raises(ValueError, match="transaction journal is invalid"):
        _ = result.journal.records
    assert api.journal_module.has_blocking_transaction(
        scenario.transaction_root
    )


def test_oversized_plan_is_rejected_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    result = _apply(api, scenario, changeset)
    plan_path = result.journal.root / "plan.json"
    with plan_path.open("wb") as stream:
        stream.truncate(16 * 1024 * 1024 + 1)
    original_read_bytes = Path.read_bytes

    def forbid_oversized_read(path: Path) -> bytes:
        if path == plan_path and path.stat().st_size > 16 * 1024 * 1024:
            raise AssertionError("oversized plan was read")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", forbid_oversized_read)

    with pytest.raises(ValueError, match="transaction journal is invalid"):
        _ = result.journal.plan
    assert api.journal_module.has_blocking_transaction(
        scenario.transaction_root
    )


def test_oversized_blob_is_rejected_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    result = _apply(api, scenario, changeset)
    relative_path = result.plan.entries[0].payload_relative_path
    assert relative_path is not None
    blob_path = result.journal.root / relative_path
    with blob_path.open("wb") as stream:
        stream.truncate(8 * 1024 * 1024 + 1)
    original_read_bytes = Path.read_bytes

    def forbid_oversized_read(path: Path) -> bytes:
        if path == blob_path and path.stat().st_size > 8 * 1024 * 1024:
            raise AssertionError("oversized blob was read")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", forbid_oversized_read)

    with pytest.raises(ValueError, match="transaction journal is invalid"):
        result.journal.read_blob(relative_path)


def test_journal_append_validation_is_incremental(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(
        tmp_path,
        {
            f"file-{index:03d}.txt": f"baseline:{index}\n".encode("ascii")
            for index in range(20)
        },
    )
    original_parse_record = api.journal_module._parse_record
    original_read_bounded = api.journal_module._read_bounded_at
    parse_calls = 0
    journal_bytes_read = 0

    def count_parse_record(line: bytes):
        nonlocal parse_calls
        parse_calls += 1
        return original_parse_record(line)

    def count_journal_bytes(parent_descriptor, name, limit):
        nonlocal journal_bytes_read
        result = original_read_bounded(parent_descriptor, name, limit)
        if name == "journal.jsonl":
            journal_bytes_read += len(result[0])
        return result

    monkeypatch.setattr(
        api.journal_module,
        "_parse_record",
        count_parse_record,
    )
    monkeypatch.setattr(
        api.journal_module,
        "_read_bounded_at",
        count_journal_bytes,
    )

    result = _apply(api, scenario, changeset)
    record_count = len(result.journal.records)

    assert result.phase is api.ApplyPhase.APPLIED
    assert parse_calls <= record_count * 5
    assert journal_bytes_read <= result.journal.path.stat().st_size * 2


def test_non_private_transaction_root_is_rejected(tmp_path: Path) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    scenario.transaction_root.mkdir(mode=0o777)
    scenario.transaction_root.chmod(0o777)

    result = _apply(api, scenario, changeset)

    assert result.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert result.task_state is TaskState.RECOVERY_REQUIRED
    assert (scenario.origin / "target.txt").read_bytes() == b"baseline\n"


def test_plan_swap_to_symlink_is_rejected(tmp_path: Path) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    result = _apply(api, scenario, changeset)
    plan_path = result.journal.root / "plan.json"
    displaced = result.journal.root / "plan.original"
    outside = tmp_path / "outside-plan.json"
    outside.write_bytes(plan_path.read_bytes())
    os.rename(plan_path, displaced)
    os.symlink(outside, plan_path)

    with pytest.raises(ValueError, match="transaction journal is invalid"):
        _ = result.journal.plan
    assert plan_path.is_symlink()


def test_payload_swap_to_symlink_is_rejected_before_repository_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    original_record = api.ApplyJournal.record
    swapped = False

    def swap_payload_after_apply_header(self, stage, status, **kwargs):
        nonlocal swapped
        record = original_record(self, stage, status, **kwargs)
        if kwargs.get("phase") is api.ApplyPhase.APPLYING and not swapped:
            entry = self.plan.entries[0]
            assert entry.payload_relative_path is not None
            payload = self.root / entry.payload_relative_path
            displaced = payload.with_name(payload.name + ".original")
            outside = tmp_path / "outside-payload"
            outside.write_bytes(payload.read_bytes())
            os.rename(payload, displaced)
            os.symlink(outside, payload)
            swapped = True
        return record

    monkeypatch.setattr(api.ApplyJournal, "record", swap_payload_after_apply_header)

    result = _apply(api, scenario, changeset)

    assert swapped
    assert result.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert result.task_state is TaskState.RECOVERY_REQUIRED
    assert (scenario.origin / "target.txt").read_bytes() == b"baseline\n"


def test_crash_before_prepare_header_returns_recovery_required(
    tmp_path: Path,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    result = _apply(api, scenario, changeset)
    result.journal.path.write_bytes(b"")

    recovered = api.RecoveryCoordinator(scenario.transaction_root).recover(
        transaction_id=result.transaction_id,
        target_root=scenario.origin,
    )

    assert recovered.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert recovered.task_state is TaskState.RECOVERY_REQUIRED
    assert recovered.journal.latest_phase is api.ApplyPhase.RECOVERY_REQUIRED


def test_startup_recovery_rolls_back_valid_apply_prefix(tmp_path: Path) -> None:
    api = _api()
    scenario, changeset = _modified(
        tmp_path,
        {"a.txt": b"a:baseline\n", "b.txt": b"b:baseline\n"},
    )
    applied = _apply(api, scenario, changeset)
    records = applied.journal.records
    first_completed = next(
        record
        for record in records
        if record.stage is api.JournalStage.APPLY
        and record.status is api.JournalStatus.COMPLETED
        and record.path is not None
        and record.path.canonical == "a.txt"
        and record.detail == "apply effect verified"
    )
    prefix = records[: first_completed.order]
    applied.journal.path.write_bytes(
        b"".join(api.journal_module._record_payload(record) for record in prefix)
    )
    (scenario.origin / "b.txt").write_bytes(b"b:baseline\n")

    recovered = api.RecoveryCoordinator(scenario.transaction_root).recover(
        transaction_id=applied.transaction_id,
        target_root=scenario.origin,
    )

    assert recovered.phase is api.ApplyPhase.ROLLED_BACK
    assert recovered.task_state is TaskState.FAILED
    assert (scenario.origin / "a.txt").read_bytes() == b"a:baseline\n"
    assert (scenario.origin / "b.txt").read_bytes() == b"b:baseline\n"


def test_startup_recovery_completes_pending_rollback_prefix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(
        tmp_path,
        {"a.txt": b"a:baseline\n", "b.txt": b"b:baseline\n"},
    )
    original_publish = api.apply_module._publish_entry
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected second write failure")
        return original_publish(*args, **kwargs)

    monkeypatch.setattr(api.apply_module, "_publish_entry", fail_second)
    rolled_back = _apply(api, scenario, changeset)
    rollback_pending = next(
        record
        for record in rolled_back.journal.records
        if record.stage is api.JournalStage.ROLLBACK
        and record.status is api.JournalStatus.PENDING
        and record.path is not None
        and record.path.canonical == "a.txt"
    )
    prefix = rolled_back.journal.records[: rollback_pending.order]
    rolled_back.journal.path.write_bytes(
        b"".join(api.journal_module._record_payload(record) for record in prefix)
    )

    recovered = api.RecoveryCoordinator(scenario.transaction_root).recover(
        transaction_id=rolled_back.transaction_id,
        target_root=scenario.origin,
    )

    assert recovered.phase is api.ApplyPhase.ROLLED_BACK
    assert recovered.task_state is TaskState.FAILED
    assert recovered.journal.latest_phase is api.ApplyPhase.ROLLED_BACK


def test_startup_recovery_removes_deterministic_publish_temporary(
    tmp_path: Path,
) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"seed.txt": b"baseline\n"})
    (scenario.workspace.root / "added.txt").write_bytes(b"agent:add\n")
    changeset = _changeset(scenario)
    applied = _apply(api, scenario, changeset)
    entry = applied.plan.entries[0]
    pending = next(
        record
        for record in applied.journal.records
        if record.stage is api.JournalStage.APPLY
        and record.status is api.JournalStatus.PENDING
        and record.path == entry.path
    )
    applied.journal.path.write_bytes(
        b"".join(
            api.journal_module._record_payload(record)
            for record in applied.journal.records[: pending.order]
        )
    )
    (scenario.origin / "added.txt").unlink()
    temporary_name = api.apply_module._temporary_name(
        applied.transaction_id,
        entry.path,
        entry.new_digest,
    )
    temporary = scenario.origin / temporary_name
    temporary.write_bytes(b"agent:add\n")

    recovered = api.RecoveryCoordinator(scenario.transaction_root).recover(
        transaction_id=applied.transaction_id,
        target_root=scenario.origin,
    )

    assert recovered.phase is api.ApplyPhase.ROLLED_BACK
    assert recovered.task_state is TaskState.FAILED
    assert not temporary.exists()
    assert not (scenario.origin / "added.txt").exists()


def test_startup_recovery_removes_deterministic_rollback_quarantine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    monkeypatch.setattr(api.apply_module, "_verify_applied", lambda *_: False)
    rolled_back = _apply(api, scenario, changeset)
    entry = rolled_back.plan.entries[0]
    pending = next(
        record
        for record in rolled_back.journal.records
        if record.stage is api.JournalStage.ROLLBACK
        and record.status is api.JournalStatus.PENDING
        and record.path == entry.path
    )
    rolled_back.journal.path.write_bytes(
        b"".join(
            api.journal_module._record_payload(record)
            for record in rolled_back.journal.records[: pending.order]
        )
    )
    quarantine_name = api.apply_module._quarantine_name(
        rolled_back.transaction_id,
        entry.path,
    )
    quarantine = scenario.origin / quarantine_name
    quarantine.write_bytes(b"agent:target.txt\n")

    recovered = api.RecoveryCoordinator(scenario.transaction_root).recover(
        transaction_id=rolled_back.transaction_id,
        target_root=scenario.origin,
    )

    assert recovered.phase is api.ApplyPhase.ROLLED_BACK
    assert recovered.task_state is TaskState.FAILED
    assert not quarantine.exists()
    assert (scenario.origin / "target.txt").read_bytes() == b"baseline\n"


def test_startup_recovery_rejects_replaced_target_parent_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario = _scenario(tmp_path, {"dir/a.txt": b"baseline\n"})
    (scenario.workspace.root / "dir" / "a.txt").write_bytes(b"agent\n")
    changeset = _changeset(scenario)
    monkeypatch.setattr(api.apply_module, "_verify_applied", lambda *_: False)
    rolled_back = _apply(api, scenario, changeset)
    displaced = scenario.origin / "displaced-dir"
    os.rename(scenario.origin / "dir", displaced)
    (scenario.origin / "dir").mkdir()
    (scenario.origin / "dir" / "a.txt").write_bytes(b"baseline\n")

    recovered = api.RecoveryCoordinator(scenario.transaction_root).recover(
        transaction_id=rolled_back.transaction_id,
        target_root=scenario.origin,
    )

    assert rolled_back.phase is api.ApplyPhase.ROLLED_BACK
    assert recovered.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert recovered.task_state is TaskState.RECOVERY_REQUIRED


def test_startup_recovery_rejects_replaced_target_root_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    monkeypatch.setattr(api.apply_module, "_verify_applied", lambda *_: False)
    rolled_back = _apply(api, scenario, changeset)
    displaced = tmp_path / "displaced-origin"
    os.rename(scenario.origin, displaced)
    shutil.copytree(displaced, scenario.origin, symlinks=True)

    recovered = api.RecoveryCoordinator(scenario.transaction_root).recover(
        transaction_id=rolled_back.transaction_id,
        target_root=scenario.origin,
    )

    assert rolled_back.phase is api.ApplyPhase.ROLLED_BACK
    assert recovered.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert recovered.task_state is TaskState.RECOVERY_REQUIRED


def test_apply_phase_journal_failure_prevents_repository_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    original_record = api.ApplyJournal.record

    def fail_apply_phase(self, stage, status, **kwargs):
        if kwargs.get("phase") is api.ApplyPhase.APPLYING:
            raise OSError("injected journal fsync failure")
        return original_record(self, stage, status, **kwargs)

    monkeypatch.setattr(api.ApplyJournal, "record", fail_apply_phase)

    result = _apply(api, scenario, changeset)

    assert result.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert result.task_state is TaskState.RECOVERY_REQUIRED
    assert (scenario.origin / "target.txt").read_bytes() == b"baseline\n"
    assert api.journal_module.has_blocking_transaction(
        scenario.transaction_root
    )


def test_prepare_header_failure_returns_recovery_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    original_record = api.ApplyJournal.record

    def fail_prepare_header(self, stage, status, **kwargs):
        if kwargs.get("phase") is api.ApplyPhase.PREPARING:
            raise OSError("injected prepare header fsync failure")
        return original_record(self, stage, status, **kwargs)

    monkeypatch.setattr(api.ApplyJournal, "record", fail_prepare_header)

    result = _apply(api, scenario, changeset)

    assert result.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert result.task_state is TaskState.RECOVERY_REQUIRED
    assert result.journal is not None
    assert (scenario.origin / "target.txt").read_bytes() == b"baseline\n"
    assert api.journal_module.has_blocking_transaction(
        scenario.transaction_root
    )


def test_user_rejection_cannot_downgrade_existing_recovery_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    original_publish = api.apply_module._publish_entry

    def publish_then_lose_certainty(*args, **kwargs):
        original_publish(*args, **kwargs)
        raise api.UncertainEffectError("injected uncertain effect")

    monkeypatch.setattr(
        api.apply_module,
        "_publish_entry",
        publish_then_lose_certainty,
    )
    uncertain = _apply(api, scenario, changeset)
    assert uncertain.task_state is TaskState.RECOVERY_REQUIRED

    rejected = _apply(
        api,
        scenario,
        changeset,
        decision=api.ApplyDecision.REJECT,
        transaction_id="txn:wp14:reject",
    )

    assert rejected.task_state is TaskState.RECOVERY_REQUIRED
    assert rejected.phase is api.ApplyPhase.RECOVERY_REQUIRED
    assert rejected.recovery_state is api.RecoveryState.RECOVERY_REQUIRED


def test_same_transaction_id_replays_verified_applied_result(
    tmp_path: Path,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    first = _apply(api, scenario, changeset)

    repeated_apply = _apply(api, scenario, changeset)
    repeated_reject = _apply(
        api,
        scenario,
        changeset,
        decision=api.ApplyDecision.REJECT,
    )

    assert first.phase is api.ApplyPhase.APPLIED
    assert repeated_apply.phase is api.ApplyPhase.APPLIED
    assert repeated_apply.task_state is TaskState.COMPLETED
    assert repeated_apply.transaction_id == first.transaction_id
    assert repeated_reject.phase is None
    assert repeated_reject.task_state is TaskState.NOT_APPLIED
    assert repeated_reject.decision is api.ApplyDecision.REJECT
    assert (scenario.origin / "target.txt").read_bytes() == b"agent:target.txt\n"


def test_same_transaction_id_mismatch_returns_explicit_conflict(
    tmp_path: Path,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)
    first = _apply(api, scenario, changeset)
    (scenario.workspace.root / "target.txt").write_bytes(b"different\n")
    different = _changeset(scenario)

    repeated = _apply(api, scenario, different)

    assert first.phase is api.ApplyPhase.APPLIED
    assert repeated.phase is None
    assert repeated.task_state is TaskState.NOT_APPLIED
    assert repeated.recovery_state is None
    assert repeated.decision is api.ApplyDecision.APPLY
    assert "transaction id" in repeated.reason
    assert (scenario.origin / "target.txt").read_bytes() == b"agent:target.txt\n"


@pytest.mark.parametrize(
    "requirement_id",
    FOUNDATIONAL_REQUIREMENTS + OWNED_REQUIREMENTS,
)
def test_spec_requirement(
    requirement_id: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    scenario, changeset = _modified(tmp_path)

    if requirement_id in {"TXN-001", "TXN-013"}:
        result = _apply(api, scenario, changeset)
        assert result.task_state is TaskState.COMPLETED
        assert result.phase is api.ApplyPhase.APPLIED
    elif requirement_id == "TXN-002":
        result = _apply(
            api,
            scenario,
            changeset,
            decision=api.ApplyDecision.REJECT,
        )
        assert result.task_state is TaskState.NOT_APPLIED
        assert (scenario.origin / "target.txt").read_bytes() == b"baseline\n"
    elif requirement_id == "TXN-003":
        assert (scenario.origin / "target.txt").read_bytes() == b"baseline\n"
    elif requirement_id in {"TXN-004", "TXN-014"}:
        original_publish = api.apply_module._publish_entry

        def uncertain(*args, **kwargs):
            original_publish(*args, **kwargs)
            raise api.UncertainEffectError("uncertain")

        monkeypatch.setattr(api.apply_module, "_publish_entry", uncertain)
        result = _apply(api, scenario, changeset)
        assert result.task_state is TaskState.RECOVERY_REQUIRED
    elif requirement_id == "TXN-009":
        result = _apply(api, scenario, changeset)
        entry = result.plan.entries[0]
        assert result.plan.changeset_digest == changeset.digest
        assert entry.expected_original_digest == hashlib.sha256(
            b"baseline\n"
        ).hexdigest()
        assert entry.new_digest == hashlib.sha256(
            b"agent:target.txt\n"
        ).hexdigest()
    elif requirement_id == "TXN-010":
        result = _apply(api, scenario, changeset)
        assert result.journal.path.is_file()
        assert (result.journal.root / result.plan.entries[0].backup_relative_path).is_file()
    elif requirement_id == "TXN-011":
        result = _apply(api, scenario, changeset)
        phase = next(
            record
            for record in result.journal.records
            if record.phase is api.ApplyPhase.APPLYING and record.path is None
        )
        pending = _records(
            result,
            stage=api.JournalStage.APPLY,
            status=api.JournalStatus.PENDING,
            path="target.txt",
        )[0]
        assert phase.order < pending.order
    elif requirement_id in {"TXN-012", "TXN-016"}:
        original_publish = api.apply_module._publish_entry

        def fail(*args, **kwargs):
            original_publish(*args, **kwargs)
            raise OSError("deterministic failure")

        monkeypatch.setattr(api.apply_module, "_publish_entry", fail)
        result = _apply(api, scenario, changeset)
        assert result.phase is api.ApplyPhase.ROLLED_BACK
        assert (scenario.origin / "target.txt").read_bytes() == b"baseline\n"
    elif requirement_id == "TXN-015":
        index_before = _git(
            scenario.origin,
            "ls-files",
            "--stage",
            "-z",
        ).stdout
        result = _apply(api, scenario, changeset)
        index_after = _git(
            scenario.origin,
            "ls-files",
            "--stage",
            "-z",
        ).stdout
        assert result.phase is api.ApplyPhase.APPLIED
        assert index_after == index_before
    else:
        result = _apply(api, scenario, changeset)
        assert {
            record.phase for record in result.journal.records
        }.issubset(set(api.ApplyPhase) | {None})
        assert all(record.order > 0 for record in result.journal.records)
