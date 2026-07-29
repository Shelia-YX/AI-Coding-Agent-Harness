"""WP-18 startup recovery orchestration contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import importlib
import os
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace

import pytest

from coding_harness.domain.approvals import ApprovalType
from coding_harness.domain.enums import BlockedReason, TaskState
from coding_harness.persistence.lease import (
    ExecutionLeaseService,
    LeasePurpose,
    LeaseStatus,
)
from coding_harness.persistence.migrations import MigrationRunner
from coding_harness.persistence.process_lock import ProcessLockOutcome
from coding_harness.persistence.sqlite_store import SQLiteHarnessStore
from coding_harness.transaction.journal import ApplyJournal
from coding_harness.transaction.recovery import RecoveryCoordinator
from coding_harness.transaction.models import (
    ApplyPhase,
    JournalStage,
    JournalStatus,
    make_apply_plan,
)


OWNED_REQUIREMENTS = (
    "PST-018",
    "PST-025",
    "PST-026",
    "PST-027",
    "PST-028",
    "TST-002",
)
_EXPECTED_INTERFACE = (
    "EXPECTED_INTERFACE_MISSING: WP-18 startup recovery contract"
)
_EXPECTED_BEHAVIOR = (
    "EXPECTED_BEHAVIOR_MISSING: WP-18 startup recovery contract"
)


def _module(name: str):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        if error.name == name or name.startswith(error.name + "."):
            pytest.fail(
                f"{_EXPECTED_INTERFACE}: missing {name}",
                pytrace=False,
            )
        raise


def _api() -> SimpleNamespace:
    startup = _module("coding_harness.application.startup_recovery")
    ports = _module("coding_harness.persistence.ports")
    journal = _module("coding_harness.transaction.journal")
    required = {
        "StartupRecovery": getattr(startup, "StartupRecovery", None),
        "RecoveryFinding": getattr(startup, "RecoveryFinding", None),
        "RecoveryFindingKind": getattr(
            startup,
            "RecoveryFindingKind",
            None,
        ),
        "RecoveryDecision": getattr(startup, "RecoveryDecision", None),
        "StartupRecoveryReport": getattr(
            startup,
            "StartupRecoveryReport",
            None,
        ),
        "ContainerObservation": getattr(
            startup,
            "ContainerObservation",
            None,
        ),
        "StartupRecoveryCandidate": getattr(
            ports,
            "StartupRecoveryCandidate",
            None,
        ),
        "RecoveryFindingRecord": getattr(
            ports,
            "RecoveryFindingRecord",
            None,
        ),
        "enumerate_apply_journals": getattr(
            journal,
            "enumerate_apply_journals",
            None,
        ),
        "JournalEnumerationError": getattr(
            journal,
            "JournalEnumerationError",
            None,
        ),
    }
    missing = tuple(name for name, value in required.items() if value is None)
    if missing:
        pytest.fail(
            _EXPECTED_INTERFACE + ": missing " + ", ".join(missing),
            pytrace=False,
        )
    return SimpleNamespace(**required)


def _migration_directory() -> Path:
    module = importlib.import_module(
        "coding_harness.persistence.sqlite_store"
    )
    return Path(module.__file__).parent / "sql"


def _database(tmp_path: Path) -> tuple[SQLiteHarnessStore, Path]:
    path = tmp_path / "harness.sqlite3"
    MigrationRunner(
        database_path=path,
        migration_directory=_migration_directory(),
    ).run()
    store = SQLiteHarnessStore(database_path=path)
    store.create_task(
        task_id="task:wp18",
        initial_state=TaskState.APPLYING,
        occurred_at=1,
    )
    return store, path


def _candidate(api: SimpleNamespace, **changes):
    transaction_id = changes.get(
        "transaction_id",
        "transaction:wp18:1",
    )
    values = {
        "task_id": "task:wp18",
        "task_state": TaskState.APPLYING,
        "task_revision": 1,
        "run_id": "run:wp18:1",
        "transaction_id": transaction_id,
        "apply_phase": ApplyPhase.PREPARING,
        "journal_reference": (
            None
            if transaction_id is None
            else "txn-"
            + hashlib.sha256(transaction_id.encode("utf-8")).hexdigest()
        ),
        "apply_plan_digest": (
            None if transaction_id is None else _plan(transaction_id).digest
        ),
        "plan_version_identity": "plan:wp18:1",
        "contract_version_identity": "contract:wp18:1",
        "approval_identity": "approval:wp18:1",
        "approval_revision": 1,
        "approval_plan_version_identity": "plan:wp18:1",
        "approval_type": ApprovalType.PLAN_APPROVAL,
        "approval_consumed": False,
        "approval_revoked": False,
        "approval_expires_at": 1000,
    }
    values.update(changes)
    if values["approval_identity"] is None:
        values.update(
            approval_type=None,
            approval_consumed=None,
            approval_revoked=None,
            approval_expires_at=None,
        )
    return api.StartupRecoveryCandidate(**values)


def _plan(transaction_id: str):
    return make_apply_plan(
        transaction_id=transaction_id,
        baseline_digest="a" * 64,
        changeset_digest="b" * 64,
        index_digest_before="c" * 64,
        target_root_identity="d" * 64,
        entries=(),
    )


def _journal(
    root: Path,
    transaction_id: str = "transaction:wp18:1",
) -> ApplyJournal:
    return ApplyJournal.create(root, transaction_id, _plan(transaction_id))


class _Store:
    def __init__(self, candidates=()) -> None:
        self.candidates = tuple(candidates)
        self.recorded = []
        self.apply_observations = []

    def startup_recovery_candidates(self, *, limit: int):
        assert 1 <= limit <= 1000
        return self.candidates[:limit]

    def record_recovery_finding(self, *, finding, occurred_at: int) -> None:
        self.recorded.append((finding, occurred_at))

    def record_apply_observation(
        self,
        *,
        task_id: str,
        result,
        journal_reference: str | None,
        occurred_at: int,
    ) -> None:
        self.apply_observations.append(
            (task_id, result, journal_reference, occurred_at)
        )


class _LeasePort:
    def __init__(self, current=None) -> None:
        self.current_lease = current
        self.recovery_requests = []

    def current(self):
        return self.current_lease

    def mark_expired(self, *, now: int):
        self.current_lease = SimpleNamespace(
            **{
                **vars(self.current_lease),
                "status": LeaseStatus.RECOVERY_PENDING,
                "revision": self.current_lease.revision + 1,
            }
        )
        return self.current_lease

    def acquire_recovery(self, **request):
        self.recovery_requests.append(request)
        self.current_lease = SimpleNamespace(
            lease_id=request["lease_id"],
            task_id=request["task_id"],
            run_id=request["run_id"],
            owner_identity=request["owner_identity"],
            purpose=LeasePurpose.RECOVERY,
            status=LeaseStatus.ACTIVE,
            revision=1,
        )
        return self.current_lease


class _ContainerProbe:
    def __init__(self, observations=()) -> None:
        self.observations = tuple(observations)
        self.calls = 0

    def scan(self, *, limit: int):
        self.calls += 1
        return self.observations[:limit]


class _RecoveryDelegate:
    def __init__(self, result=None) -> None:
        self.result = result
        self.calls = []

    def recover(self, **request):
        self.calls.append(request)
        return self.result


class _EventReader:
    def __init__(self, events=()) -> None:
        self.events = tuple(events)

    def after(self, *, event_id: int, limit: int):
        return self.events[:limit]


def _orchestrator(
    api: SimpleNamespace,
    tmp_path: Path,
    *,
    candidates=(),
    lease=None,
    containers=(),
    delegate_result=None,
    events=(),
):
    store = _Store(candidates)
    lease_port = _LeasePort(lease)
    probe = _ContainerProbe(containers)
    delegate = _RecoveryDelegate(delegate_result)
    orchestrator = api.StartupRecovery(
        store=store,
        lease_service=lease_port,
        transaction_root=tmp_path / "transactions",
        task_root=tmp_path / "tasks",
        container_probe=probe,
        recovery_delegate=delegate,
        event_reader=_EventReader(events),
        candidate_limit=32,
    )
    return orchestrator, store, lease_port, probe, delegate


def _scan(orchestrator, *, lock=ProcessLockOutcome.ACQUIRED):
    return orchestrator.scan(
        now=100,
        owner_identity="owner:wp18:startup",
        process_lock_outcome=lock,
    )


def _finding(report, kind):
    matches = tuple(
        finding for finding in report.findings if finding.kind is kind
    )
    assert len(matches) == 1
    return matches[0]


def test_scan_lease(tmp_path: Path) -> None:
    api = _api()
    stale = SimpleNamespace(
        lease_id="lease:wp18:old",
        task_id="task:wp18",
        run_id="run:wp18:1",
        owner_identity="owner:wp18:old",
        purpose=LeasePurpose.EXECUTION,
        acquired_at=1,
        last_progress_at=1,
        phase=TaskState.APPLYING,
        status=LeaseStatus.RECOVERY_PENDING,
        revision=2,
    )
    orchestrator, _, _, _, _ = _orchestrator(
        api,
        tmp_path,
        lease=stale,
    )
    report = _scan(orchestrator)
    finding = _finding(report, api.RecoveryFindingKind.STALE_LEASE)
    assert finding.task_id == "task:wp18"
    assert finding.run_id == "run:wp18:1"
    assert finding.blocks_execution is True
    assert report.execution_permitted is False


def test_scan_container(tmp_path: Path) -> None:
    api = _api()
    container = api.ContainerObservation(
        container_id="container:wp18:1",
        task_id="task:wp18",
        run_id="run:wp18:1",
        terminal=False,
    )
    orchestrator, _, _, probe, _ = _orchestrator(
        api,
        tmp_path,
        containers=(container,),
    )
    report = _scan(orchestrator)
    finding = _finding(
        report,
        api.RecoveryFindingKind.RESIDUAL_CONTAINER,
    )
    assert probe.calls == 1
    assert finding.blocks_execution is True
    assert finding.decision is api.RecoveryDecision.MANUAL_RECOVERY_REQUIRED


def test_scan_apply(tmp_path: Path) -> None:
    api = _api()
    journal = _journal(tmp_path / "transactions")
    candidate = _candidate(api)
    orchestrator, _, _, _, delegate = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
        delegate_result=SimpleNamespace(
            transaction_id=candidate.transaction_id,
            phase=ApplyPhase.ROLLED_BACK,
        ),
    )
    report = _scan(orchestrator)
    finding = _finding(
        report,
        api.RecoveryFindingKind.NONTERMINAL_APPLY,
    )
    assert journal.latest_phase is ApplyPhase.PREPARING
    assert finding.transaction_id == candidate.transaction_id
    assert finding.blocks_execution is True
    assert len(delegate.calls) <= 1


def test_check_journal(tmp_path: Path) -> None:
    api = _api()
    transaction_root = tmp_path / "transactions"
    journal = _journal(transaction_root)
    journal.record(
        JournalStage.BACKUP,
        JournalStatus.COMPLETED,
        phase=ApplyPhase.BACKUP_READY,
        detail="all backups verified",
        evidence_digest=journal.plan.digest,
    )
    journal.record(
        JournalStage.APPLY,
        JournalStatus.COMPLETED,
        phase=ApplyPhase.APPLYING,
        detail="effect phase entered",
    )
    snapshots = api.enumerate_apply_journals(
        transaction_root,
        limit=8,
    )
    assert tuple(item.transaction_id for item in snapshots) == (
        "transaction:wp18:1",
    )
    assert snapshots[0].phase is ApplyPhase.APPLYING
    assert snapshots[0].blocking is True


def test_journal_enumeration_is_bounded_and_read_only(
    tmp_path: Path,
) -> None:
    api = _api()
    transaction_root = tmp_path / "transactions"
    first = _journal(transaction_root, "transaction:wp18:1")
    _journal(transaction_root, "transaction:wp18:2")
    before = {
        path.relative_to(transaction_root): path.read_bytes()
        for path in transaction_root.rglob("*")
        if path.is_file()
    }
    with pytest.raises(api.JournalEnumerationError, match="limit|bounded"):
        api.enumerate_apply_journals(transaction_root, limit=1)
    after = {
        path.relative_to(transaction_root): path.read_bytes()
        for path in transaction_root.rglob("*")
        if path.is_file()
    }
    assert first.latest_phase is ApplyPhase.PREPARING
    assert after == before


def test_domain_event_is_not_candidate_authority(
    tmp_path: Path,
) -> None:
    api = _api()
    forged_event = SimpleNamespace(
        event_id=999,
        task_id="task:forged",
        entity_identity="transaction:forged",
        payload=(("phase", "APPLYING"),),
    )
    orchestrator, _, _, _, delegate = _orchestrator(
        api,
        tmp_path,
        candidates=(),
        events=(forged_event,),
    )
    report = _scan(orchestrator)
    assert report.findings == ()
    assert report.execution_permitted is True
    assert delegate.calls == []


def test_orchestration_delegates_without_modifying_target(
    tmp_path: Path,
) -> None:
    api = _api()
    target = tmp_path / "repository"
    target.mkdir()
    protected = target / "protected.txt"
    protected.write_bytes(b"original")
    candidate = _candidate(api)
    _journal(tmp_path / "transactions")
    orchestrator, _, _, _, delegate = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
        delegate_result=SimpleNamespace(
            transaction_id=candidate.transaction_id,
            phase=ApplyPhase.RECOVERY_REQUIRED,
        ),
    )
    _scan(orchestrator)
    assert protected.read_bytes() == b"original"
    assert len(delegate.calls) <= 1


def test_stale_lease_requests_recovery_ownership(
    tmp_path: Path,
) -> None:
    api = _api()
    pending = SimpleNamespace(
        lease_id="lease:wp18:pending",
        task_id="task:wp18",
        run_id="run:wp18:1",
        owner_identity="owner:wp18:old",
        purpose=LeasePurpose.EXECUTION,
        acquired_at=1,
        last_progress_at=1,
        phase=TaskState.APPLYING,
        status=LeaseStatus.RECOVERY_PENDING,
        revision=2,
    )
    orchestrator, _, lease, _, _ = _orchestrator(
        api,
        tmp_path,
        candidates=(_candidate(api),),
        lease=pending,
    )
    report = _scan(orchestrator)
    assert len(lease.recovery_requests) == 1
    request = lease.recovery_requests[0]
    assert request["task_id"] == pending.task_id
    assert request["run_id"] == pending.run_id
    assert request["expected_pending_revision"] == pending.revision
    assert report.execution_permitted is False


def test_recovery_pending_blocks_normal_execution(
    tmp_path: Path,
) -> None:
    api = _api()
    pending = SimpleNamespace(
        lease_id="lease:wp18:pending",
        task_id="task:wp18",
        run_id="run:wp18:1",
        owner_identity="owner:wp18:old",
        purpose=LeasePurpose.EXECUTION,
        acquired_at=1,
        last_progress_at=1,
        phase=TaskState.APPLYING,
        status=LeaseStatus.RECOVERY_PENDING,
        revision=2,
    )
    orchestrator, _, _, _, _ = _orchestrator(
        api,
        tmp_path,
        lease=pending,
    )
    report = _scan(orchestrator)
    assert report.execution_permitted is False
    assert report.normal_execution_blocked is True


def test_missing_journal_fails_closed(tmp_path: Path) -> None:
    api = _api()
    candidate = _candidate(api)
    orchestrator, store, _, _, delegate = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
    )
    report = _scan(orchestrator)
    finding = _finding(report, api.RecoveryFindingKind.MISSING_JOURNAL)
    assert finding.decision is api.RecoveryDecision.MANUAL_RECOVERY_REQUIRED
    assert finding.blocks_execution is True
    assert delegate.calls == []
    assert store.recorded


def test_database_disk_mismatch_fails_closed(
    tmp_path: Path,
) -> None:
    api = _api()
    _journal(tmp_path / "transactions", "transaction:wp18:disk")
    candidate = _candidate(
        api,
        transaction_id="transaction:wp18:database",
    )
    orchestrator, _, _, _, delegate = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
    )
    report = _scan(orchestrator)
    findings = tuple(
        finding
        for finding in report.findings
        if finding.kind is api.RecoveryFindingKind.EVIDENCE_MISMATCH
    )
    assert findings
    assert all(finding.blocks_execution for finding in findings)
    assert report.execution_permitted is False
    assert delegate.calls == []


@pytest.mark.parametrize(
    ("change", "value"),
    (
        ("apply_phase", ApplyPhase.BACKUP_READY),
        ("journal_reference", "txn-" + "0" * 64),
        ("apply_plan_digest", "0" * 64),
    ),
)
def test_same_transaction_conflicting_evidence_fails_closed(
    tmp_path: Path,
    change: str,
    value,
) -> None:
    api = _api()
    candidate = _candidate(api, **{change: value})
    _journal(tmp_path / "transactions", candidate.transaction_id)
    orchestrator, _, _, _, delegate = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
    )
    report = _scan(orchestrator)
    finding = _finding(report, api.RecoveryFindingKind.EVIDENCE_MISMATCH)
    assert finding.blocks_execution is True
    assert report.execution_permitted is False
    assert delegate.calls == []


def test_incomplete_evidence_fails_closed(tmp_path: Path) -> None:
    api = _api()
    transaction_root = tmp_path / "transactions"
    journal = _journal(transaction_root)
    journal.path.unlink()
    orchestrator, _, _, _, delegate = _orchestrator(
        api,
        tmp_path,
        candidates=(_candidate(api),),
    )
    report = _scan(orchestrator)
    assert report.execution_permitted is False
    assert any(
        finding.decision
        is api.RecoveryDecision.MANUAL_RECOVERY_REQUIRED
        for finding in report.findings
    )
    assert delegate.calls == []


def test_duplicate_startup_is_blocked(tmp_path: Path) -> None:
    api = _api()
    orchestrator, _, lease, probe, delegate = _orchestrator(
        api,
        tmp_path,
    )
    report = _scan(orchestrator, lock=ProcessLockOutcome.BUSY)
    assert report.execution_permitted is False
    assert report.normal_execution_blocked is True
    assert lease.recovery_requests == []
    assert probe.calls == 0
    assert delegate.calls == []


def test_uncertain_effect_recovers(tmp_path: Path) -> None:
    api = _api()
    candidate = _candidate(api, apply_phase=ApplyPhase.APPLYING)
    _journal(tmp_path / "transactions")
    orchestrator, _, _, _, delegate = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
        delegate_result=SimpleNamespace(
            transaction_id=candidate.transaction_id,
            phase=ApplyPhase.RECOVERY_REQUIRED,
        ),
    )
    report = _scan(orchestrator)
    assert report.execution_permitted is False
    assert len(delegate.calls) <= 1
    assert all(
        finding.decision is not api.RecoveryDecision.CONTINUE_EXECUTION
        for finding in report.findings
    )


def test_clarification_paused(tmp_path: Path) -> None:
    api = _api()
    candidate = _candidate(
        api,
        task_state=TaskState.AWAITING_CLARIFICATION,
        transaction_id=None,
        apply_phase=None,
        journal_reference=None,
    )
    orchestrator, _, lease, _, delegate = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
    )
    report = _scan(orchestrator)
    finding = _finding(report, api.RecoveryFindingKind.SAFE_WAITING)
    assert finding.decision is api.RecoveryDecision.PAUSE
    assert finding.blocks_execution is False
    assert lease.recovery_requests == []
    assert delegate.calls == []


def test_approval_cleanup_release(tmp_path: Path) -> None:
    api = _api()
    workspace = tmp_path / "tasks" / "task-wp18"
    workspace.mkdir(parents=True)
    status = workspace.stat()
    workspace_identity = hashlib.sha256(
        f"{status.st_dev}:{status.st_ino}".encode("ascii")
    ).hexdigest()
    candidate = _candidate(
        api,
        task_state=TaskState.AWAITING_PLAN_APPROVAL,
        transaction_id=None,
        apply_phase=None,
        journal_reference=None,
        apply_plan_digest=None,
        workspace_reference="task-wp18",
        workspace_identity=workspace_identity,
        container_cleanup_verified=True,
        file_effects_cleanup_verified=True,
        cleanup_verified=True,
        approval_type=ApprovalType.PLAN_APPROVAL,
        approval_consumed=False,
        approval_revoked=False,
        approval_expires_at=1000,
    )
    orchestrator, _, _, _, delegate = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
    )
    report = _scan(orchestrator)
    finding = _finding(report, api.RecoveryFindingKind.SAFE_WAITING)
    assert finding.cleanup_safe is True
    assert finding.decision is api.RecoveryDecision.RELEASE_ALLOWED
    assert delegate.calls == []


def test_approval_without_cleanup_evidence_cannot_release(
    tmp_path: Path,
) -> None:
    api = _api()
    candidate = _candidate(
        api,
        task_state=TaskState.AWAITING_PLAN_APPROVAL,
        transaction_id=None,
        apply_phase=None,
        journal_reference=None,
        apply_plan_digest=None,
    )
    orchestrator, _, _, _, _ = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
    )
    finding = _finding(
        _scan(orchestrator),
        api.RecoveryFindingKind.EVIDENCE_MISMATCH,
    )
    assert finding.cleanup_safe is False
    assert finding.blocks_execution is True
    assert finding.decision is api.RecoveryDecision.MANUAL_RECOVERY_REQUIRED


def test_blocked_finding_preserves_closed_reason(tmp_path: Path) -> None:
    api = _api()
    candidate = _candidate(
        api,
        task_state=TaskState.BLOCKED,
        transaction_id=None,
        apply_phase=None,
        journal_reference=None,
        apply_plan_digest=None,
        blocked_reason=BlockedReason.PERSISTENCE_FAILED,
    )
    orchestrator, _, _, _, _ = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
    )
    finding = _finding(
        _scan(orchestrator),
        api.RecoveryFindingKind.SAFE_WAITING,
    )
    assert finding.blocked_reason is BlockedReason.PERSISTENCE_FAILED
    assert finding.next_command == "repair_persistence"


def test_duplicate_transaction_journals_fail_closed(
    tmp_path: Path,
) -> None:
    api = _api()
    root = tmp_path / "transactions"
    journal = _journal(root)
    duplicate = root / ("txn-" + "f" * 64)
    shutil.copytree(journal.path.parent, duplicate)
    orchestrator, _, _, _, delegate = _orchestrator(
        api,
        tmp_path,
        candidates=(_candidate(api),),
    )
    report = _scan(orchestrator)
    finding = _finding(report, api.RecoveryFindingKind.EVIDENCE_MISMATCH)
    assert finding.blocks_execution is True
    assert delegate.calls == []


def test_container_probe_overflow_fails_closed(tmp_path: Path) -> None:
    api = _api()
    observation = api.ContainerObservation(
        container_id="container:overflow",
        task_id="task:wp18",
        run_id="run:wp18:1",
        terminal=True,
    )
    orchestrator, _, _, _, _ = _orchestrator(api, tmp_path)
    orchestrator._container_probe = SimpleNamespace(
        scan=lambda *, limit: tuple(observation for _ in range(limit + 1))
    )
    with pytest.raises(ValueError, match="bounded|inventory"):
        _scan(orchestrator)


def test_recovery_coordinator_adapter_uses_real_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    adapter_type = getattr(
        importlib.import_module(
            "coding_harness.application.startup_recovery"
        ),
        "RecoveryCoordinatorAdapter",
        None,
    )
    assert adapter_type is not None, _EXPECTED_INTERFACE
    calls = []

    def recover(self, *, transaction_id: str, target_root: Path):
        calls.append((self, transaction_id, target_root))
        return "result"

    monkeypatch.setattr(RecoveryCoordinator, "recover", recover)
    coordinator = RecoveryCoordinator(tmp_path / "transactions")
    target = tmp_path / "target"
    target.mkdir()
    adapter = adapter_type(coordinator=coordinator, target_root=target)
    assert adapter.recover(transaction_id="transaction:wp18:1") == "result"
    assert calls == [(coordinator, "transaction:wp18:1", target)]


def test_active_stale_lease_uses_wp17_expiration_authority(
    tmp_path: Path,
) -> None:
    api = _api()
    active = SimpleNamespace(
        lease_id="lease:wp18:active",
        task_id="task:wp18",
        run_id="run:wp18:1",
        owner_identity="owner:old",
        purpose=LeasePurpose.EXECUTION,
        acquired_at=1,
        last_progress_at=1,
        phase=TaskState.APPLYING,
        status=LeaseStatus.ACTIVE,
        revision=1,
    )
    _journal(tmp_path / "transactions")
    orchestrator, _, lease, _, _ = _orchestrator(
        api,
        tmp_path,
        candidates=(_candidate(api),),
        lease=active,
    )
    _scan(orchestrator)
    assert lease.current_lease.status is LeaseStatus.ACTIVE
    assert len(lease.recovery_requests) == 1
    assert lease.recovery_requests[0]["expected_pending_revision"] == 2


def test_new_startup_cannot_reuse_old_active_recovery_lease(
    tmp_path: Path,
) -> None:
    api = _api()
    candidate = _candidate(api)
    _journal(tmp_path / "transactions")
    old_recovery = SimpleNamespace(
        lease_id="lease:wp18:old-recovery",
        task_id=candidate.task_id,
        run_id=candidate.run_id,
        owner_identity="owner:wp18:old",
        purpose=LeasePurpose.RECOVERY,
        acquired_at=1,
        last_progress_at=1,
        phase=TaskState.ROLLING_BACK,
        status=LeaseStatus.ACTIVE,
        revision=4,
    )
    orchestrator, _, lease, _, delegate = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
        lease=old_recovery,
        delegate_result=SimpleNamespace(
            transaction_id=candidate.transaction_id,
            phase=ApplyPhase.ROLLED_BACK,
        ),
    )
    report = _scan(orchestrator)
    assert len(lease.recovery_requests) == 1
    request = lease.recovery_requests[0]
    assert request["lease_id"] != old_recovery.lease_id
    assert request["owner_identity"] == "owner:wp18:startup"
    assert request["expected_pending_revision"] == 5
    assert lease.current_lease.lease_id == request["lease_id"]
    assert lease.current_lease.owner_identity == request["owner_identity"]
    assert report.execution_permitted is False
    finding = _finding(report, api.RecoveryFindingKind.STALE_LEASE)
    assert finding.lease_id == old_recovery.lease_id
    assert finding.blocks_execution is True


@pytest.mark.parametrize(
    ("field", "bad_value"),
    (
        ("lease_id", "lease:wp18:old-recovery"),
        ("owner_identity", "owner:wp18:old"),
        ("purpose", LeasePurpose.EXECUTION),
        ("status", LeaseStatus.RECOVERY_PENDING),
        ("revision", 2),
    ),
)
def test_invalid_recovery_ownership_proof_blocks_delegate(
    tmp_path: Path,
    field: str,
    bad_value,
) -> None:
    api = _api()
    candidate = _candidate(api)
    _journal(tmp_path / "transactions")
    old_recovery = SimpleNamespace(
        lease_id="lease:wp18:old-recovery",
        task_id=candidate.task_id,
        run_id=candidate.run_id,
        owner_identity="owner:wp18:old",
        purpose=LeasePurpose.RECOVERY,
        acquired_at=1,
        last_progress_at=1,
        phase=TaskState.ROLLING_BACK,
        status=LeaseStatus.ACTIVE,
        revision=4,
    )

    class AdversarialLeasePort(_LeasePort):
        def acquire_recovery(self, **request):
            self.recovery_requests.append(request)
            values = {
                "lease_id": request["lease_id"],
                "task_id": request["task_id"],
                "run_id": request["run_id"],
                "owner_identity": request["owner_identity"],
                "purpose": LeasePurpose.RECOVERY,
                "status": LeaseStatus.ACTIVE,
                "revision": 1,
            }
            values[field] = bad_value
            return SimpleNamespace(**values)

    store = _Store((candidate,))
    lease = AdversarialLeasePort(old_recovery)
    delegate = _RecoveryDelegate(
        SimpleNamespace(
            transaction_id=candidate.transaction_id,
            phase=ApplyPhase.ROLLED_BACK,
        )
    )
    orchestrator = api.StartupRecovery(
        store=store,
        lease_service=lease,
        transaction_root=tmp_path / "transactions",
        task_root=tmp_path / "tasks",
        container_probe=_ContainerProbe(),
        recovery_delegate=delegate,
        event_reader=_EventReader(),
        candidate_limit=32,
    )
    report = _scan(orchestrator)
    assert delegate.calls == []
    assert report.execution_permitted is False
    assert any(
        finding.kind is api.RecoveryFindingKind.EVIDENCE_MISMATCH
        and finding.blocks_execution
        for finding in report.findings
    )


@pytest.mark.parametrize(
    "changes",
    (
        {"approval_consumed": True},
        {"approval_revoked": True},
        {"approval_expires_at": 99},
        {"approval_type": ApprovalType.ACTION_APPROVAL},
    ),
)
def test_invalid_approval_lifecycle_cannot_release(
    tmp_path: Path,
    changes: dict[str, object],
) -> None:
    api = _api()
    workspace = tmp_path / "tasks" / "task-wp18"
    workspace.mkdir(parents=True)
    status = workspace.stat()
    lifecycle = {
        "approval_type": ApprovalType.PLAN_APPROVAL,
        "approval_consumed": False,
        "approval_revoked": False,
        "approval_expires_at": 1000,
    }
    lifecycle.update(changes)
    candidate = _candidate(
        api,
        task_state=TaskState.AWAITING_PLAN_APPROVAL,
        transaction_id=None,
        apply_phase=None,
        journal_reference=None,
        apply_plan_digest=None,
        workspace_reference="task-wp18",
        workspace_identity=hashlib.sha256(
            f"{status.st_dev}:{status.st_ino}".encode("ascii")
        ).hexdigest(),
        container_cleanup_verified=True,
        file_effects_cleanup_verified=True,
        cleanup_verified=True,
        **lifecycle,
    )
    orchestrator, _, _, _, _ = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
    )
    report = _scan(orchestrator)
    finding = _finding(report, api.RecoveryFindingKind.EVIDENCE_MISMATCH)
    assert finding.blocks_execution is True
    assert finding.decision is api.RecoveryDecision.MANUAL_RECOVERY_REQUIRED
    assert report.execution_permitted is False


def test_missing_plan_version_binding_cannot_release(
    tmp_path: Path,
) -> None:
    api = _api()
    workspace = tmp_path / "tasks" / "task-wp18"
    workspace.mkdir(parents=True)
    status = workspace.stat()
    candidate = _candidate(
        api,
        task_state=TaskState.AWAITING_PLAN_APPROVAL,
        transaction_id=None,
        apply_phase=None,
        journal_reference=None,
        apply_plan_digest=None,
        plan_version_identity=None,
        approval_plan_version_identity=None,
        workspace_reference="task-wp18",
        workspace_identity=hashlib.sha256(
            f"{status.st_dev}:{status.st_ino}".encode("ascii")
        ).hexdigest(),
        container_cleanup_verified=True,
        file_effects_cleanup_verified=True,
        cleanup_verified=True,
    )
    orchestrator, _, _, _, _ = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
    )
    report = _scan(orchestrator)
    finding = _finding(report, api.RecoveryFindingKind.EVIDENCE_MISMATCH)
    assert finding.blocks_execution is True
    assert finding.decision is api.RecoveryDecision.MANUAL_RECOVERY_REQUIRED
    assert report.execution_permitted is False


def test_production_candidate_without_cleanup_evidence_cannot_release(
    tmp_path: Path,
) -> None:
    api = _api()
    store, database = _database(tmp_path)
    with sqlite3.connect(database) as connection:
        with connection:
            connection.execute(
                "UPDATE tasks SET state = ? WHERE task_id = ?",
                (TaskState.AWAITING_PLAN_APPROVAL.value, "task:wp18"),
            )
    candidates = store.startup_recovery_candidates(limit=8)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.workspace_reference is None
    assert candidate.workspace_identity is None
    assert candidate.container_cleanup_verified is False
    assert candidate.file_effects_cleanup_verified is False
    assert candidate.cleanup_verified is False
    orchestrator = api.StartupRecovery(
        store=store,
        lease_service=_LeasePort(),
        transaction_root=tmp_path / "transactions",
        task_root=tmp_path / "tasks",
        container_probe=_ContainerProbe(),
        recovery_delegate=_RecoveryDelegate(),
        event_reader=_EventReader(),
        candidate_limit=8,
    )
    report = _scan(orchestrator)
    assert report.execution_permitted is False
    assert all(
        finding.decision is not api.RecoveryDecision.RELEASE_ALLOWED
        for finding in report.findings
    )


def test_workspace_intermediate_symlink_escape_fails_closed(
    tmp_path: Path,
) -> None:
    api = _api()
    task_root = tmp_path / "tasks"
    task_root.mkdir()
    outside = tmp_path / "outside"
    workspace = outside / "workspace"
    workspace.mkdir(parents=True)
    os.symlink(outside, task_root / "escape")
    status = workspace.stat()
    candidate = _candidate(
        api,
        task_state=TaskState.AWAITING_PLAN_APPROVAL,
        transaction_id=None,
        apply_phase=None,
        journal_reference=None,
        apply_plan_digest=None,
        workspace_reference="escape/workspace",
        workspace_identity=hashlib.sha256(
            f"{status.st_dev}:{status.st_ino}".encode("ascii")
        ).hexdigest(),
        container_cleanup_verified=True,
        file_effects_cleanup_verified=True,
        cleanup_verified=True,
        approval_type=ApprovalType.PLAN_APPROVAL,
        approval_consumed=False,
        approval_revoked=False,
        approval_expires_at=1000,
    )
    orchestrator, _, _, _, _ = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
    )
    finding = _finding(
        _scan(orchestrator),
        api.RecoveryFindingKind.EVIDENCE_MISMATCH,
    )
    assert finding.blocks_execution is True
    assert finding.cleanup_safe is False


@pytest.mark.parametrize(
    "failure_point",
    ("candidate_query", "finding_write", "observation_write"),
)
def test_persistence_failure_never_reports_recovery_success(
    tmp_path: Path,
    failure_point: str,
) -> None:
    api = _api()
    candidate = _candidate(api)
    _journal(tmp_path / "transactions")
    pending = SimpleNamespace(
        lease_id="lease:wp18:pending",
        task_id=candidate.task_id,
        run_id=candidate.run_id,
        owner_identity="owner:old",
        purpose=LeasePurpose.EXECUTION,
        acquired_at=1,
        last_progress_at=1,
        phase=TaskState.APPLYING,
        status=LeaseStatus.RECOVERY_PENDING,
        revision=2,
    )
    orchestrator, store, _, _, delegate = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
        lease=pending,
        delegate_result=SimpleNamespace(
            transaction_id=candidate.transaction_id,
            phase=ApplyPhase.ROLLED_BACK,
        ),
    )
    if failure_point == "candidate_query":
        store.startup_recovery_candidates = (
            lambda *, limit: (_ for _ in ()).throw(
                RuntimeError("candidate persistence failure")
            )
        )
    elif failure_point == "finding_write":
        store.record_recovery_finding = (
            lambda **kwargs: (_ for _ in ()).throw(
                RuntimeError("finding persistence failure")
            )
        )
    else:
        store.record_apply_observation = (
            lambda **kwargs: (_ for _ in ()).throw(
                RuntimeError("observation persistence failure")
            )
        )
    with pytest.raises(RuntimeError, match="persistence failure"):
        _scan(orchestrator)
    if failure_point != "observation_write":
        assert delegate.calls == []


def test_revision_history(tmp_path: Path) -> None:
    api = _api()
    current = _candidate(
        api,
        plan_version_identity="plan:wp18:2",
        approval_identity="approval:wp18:2",
        approval_revision=2,
        approval_plan_version_identity="plan:wp18:2",
    )
    orchestrator, store, _, _, _ = _orchestrator(
        api,
        tmp_path,
        candidates=(current,),
    )
    report = _scan(orchestrator)
    assert store.candidates == (current,)
    assert all(
        finding.decision is not api.RecoveryDecision.DELETE_HISTORY
        for finding in report.findings
    )


def test_old_approval_invalidated(tmp_path: Path) -> None:
    api = _api()
    stale = _candidate(
        api,
        plan_version_identity="plan:wp18:2",
        approval_identity="approval:wp18:1",
        approval_revision=1,
        approval_plan_version_identity="plan:wp18:1",
        transaction_id=None,
        apply_phase=None,
        journal_reference=None,
    )
    orchestrator, _, _, _, _ = _orchestrator(
        api,
        tmp_path,
        candidates=(stale,),
    )
    report = _scan(orchestrator)
    finding = _finding(report, api.RecoveryFindingKind.STALE_APPROVAL)
    assert finding.decision is api.RecoveryDecision.INVALIDATE_AUTHORIZATION
    assert finding.blocks_execution is True


def test_unapproved_revision_no_write(tmp_path: Path) -> None:
    api = _api()
    target = tmp_path / "workspace"
    target.mkdir()
    existing = target / "kept.txt"
    existing.write_bytes(b"workspace change")
    candidate = _candidate(
        api,
        task_state=TaskState.AWAITING_PLAN_APPROVAL,
        plan_version_identity="plan:wp18:2",
        approval_identity=None,
        approval_revision=None,
        approval_plan_version_identity=None,
        transaction_id=None,
        apply_phase=None,
        journal_reference=None,
    )
    orchestrator, _, lease, _, delegate = _orchestrator(
        api,
        tmp_path,
        candidates=(candidate,),
    )
    report = _scan(orchestrator)
    assert existing.read_bytes() == b"workspace change"
    assert report.normal_execution_blocked is True
    assert lease.recovery_requests == []
    assert delegate.calls == []


def test_startup_recovery_candidate_query_uses_persisted_facts(
    tmp_path: Path,
) -> None:
    api = _api()
    store, database = _database(tmp_path)
    with sqlite3.connect(database) as connection:
        with connection:
            connection.execute(
                "INSERT INTO apply_observations"
                "(transaction_id, task_id, decision, phase, "
                "observed_task_state, recovery_state, plan_digest, "
                "baseline_digest, changeset_digest, journal_reference, "
                "index_digest_after, reason, occurred_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "transaction:wp18:1",
                    "task:wp18",
                    "APPLY",
                    "APPLYING",
                    TaskState.APPLYING.value,
                    "RECOVERY_REQUIRED",
                    "a" * 64,
                    "b" * 64,
                    "c" * 64,
                    "transactions/transaction-wp18-1",
                    None,
                    "startup recovery required",
                    2,
                ),
            )
    query = getattr(store, "startup_recovery_candidates", None)
    if query is None:
        pytest.fail(
            _EXPECTED_INTERFACE
            + ": missing HarnessStore.startup_recovery_candidates",
            pytrace=False,
        )
    candidates = query(limit=10)
    assert len(candidates) == 1
    assert type(candidates[0]) is api.StartupRecoveryCandidate
    assert candidates[0].transaction_id == "transaction:wp18:1"
    assert candidates[0].task_id == "task:wp18"


def test_recovery_finding_persistence_is_append_only(
    tmp_path: Path,
) -> None:
    api = _api()
    store, _ = _database(tmp_path)
    finding = api.RecoveryFindingRecord(
        finding_id="finding:wp18:1",
        kind="MISSING_JOURNAL",
        task_id="task:wp18",
        run_id="run:wp18:1",
        lease_id="lease:wp18:1",
        transaction_id="transaction:wp18:1",
        journal_reference=None,
        reason="journal evidence is missing",
        blocks_execution=True,
    )
    record = getattr(store, "record_recovery_finding", None)
    if record is None:
        pytest.fail(
            _EXPECTED_INTERFACE
            + ": missing HarnessStore.record_recovery_finding",
            pytrace=False,
        )
    record(finding=finding, occurred_at=10)
    record(finding=finding, occurred_at=10)
    events = store.audit_events(task_id="task:wp18")
    matching = tuple(
        event
        for event in events
        if event.subject_identity == "finding:wp18:1"
    )
    assert len(matching) == 1
    assert matching[0].event_kind == "STARTUP_RECOVERY_FINDING"


@pytest.mark.parametrize("requirement_id", OWNED_REQUIREMENTS)
def test_spec_requirement(requirement_id: str, tmp_path: Path) -> None:
    api = _api()
    if requirement_id == "PST-018":
        candidate = _candidate(api)
        _journal(tmp_path / "transactions")
        orchestrator, _, _, _, _ = _orchestrator(
            api,
            tmp_path,
            candidates=(candidate,),
        )
        report = _scan(orchestrator)
        assert report.findings
        assert report.execution_permitted is False
        return
    if requirement_id == "PST-025":
        candidate = _candidate(
            api,
            task_state=TaskState.BLOCKED,
            transaction_id=None,
            apply_phase=None,
            journal_reference=None,
        )
        orchestrator, _, _, _, _ = _orchestrator(
            api,
            tmp_path,
            candidates=(candidate,),
        )
        report = _scan(orchestrator)
        assert all(finding.next_command for finding in report.findings)
        return
    if requirement_id == "PST-026":
        test_approval_cleanup_release(tmp_path)
        return
    if requirement_id == "PST-027":
        test_old_approval_invalidated(tmp_path)
        return
    if requirement_id == "PST-028":
        test_unapproved_revision_no_write(tmp_path)
        return
    if requirement_id == "TST-002":
        store, database = _database(tmp_path)
        assert database.is_file()
        assert (
            store.get_task_state(task_id="task:wp18")
            is TaskState.APPLYING
        )
        _journal(tmp_path / "transactions")
        assert (tmp_path / "transactions").is_dir()
        return
    raise AssertionError(f"unmapped WP-18 requirement: {requirement_id}")
