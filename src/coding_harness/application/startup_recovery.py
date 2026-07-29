"""Deterministic startup recovery discovery and authority orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import stat

from coding_harness.domain.approvals import ApprovalType
from coding_harness.domain.enums import BlockedReason, TaskState
from coding_harness.persistence.lease import (
    LeaseError,
    LeasePurpose,
    LeaseStatus,
)
from coding_harness.persistence.ports import (
    RecoveryFindingRecord,
    StartupRecoveryCandidate,
)
from coding_harness.persistence.process_lock import ProcessLockOutcome
from coding_harness.transaction.journal import (
    JournalEnumerationError,
    JournalSnapshot,
    enumerate_apply_journals,
)
from coding_harness.transaction.recovery import RecoveryCoordinator


_MAX_TEXT_BYTES = 4096
_SYSTEM_TASK = "system:startup"


class _ClosedEnum(Enum):
    def __bool__(self) -> bool:
        raise TypeError(f"{type(self).__name__} has no truth value")


class RecoveryFindingKind(_ClosedEnum):
    STALE_LEASE = "STALE_LEASE"
    RESIDUAL_CONTAINER = "RESIDUAL_CONTAINER"
    NONTERMINAL_APPLY = "NONTERMINAL_APPLY"
    MISSING_JOURNAL = "MISSING_JOURNAL"
    EVIDENCE_MISMATCH = "EVIDENCE_MISMATCH"
    SAFE_WAITING = "SAFE_WAITING"
    STALE_APPROVAL = "STALE_APPROVAL"
    DUPLICATE_STARTUP = "DUPLICATE_STARTUP"


class RecoveryDecision(_ClosedEnum):
    MANUAL_RECOVERY_REQUIRED = "MANUAL_RECOVERY_REQUIRED"
    REQUEST_RECOVERY_OWNERSHIP = "REQUEST_RECOVERY_OWNERSHIP"
    DELEGATE_RECOVERY = "DELEGATE_RECOVERY"
    PAUSE = "PAUSE"
    RELEASE_ALLOWED = "RELEASE_ALLOWED"
    CONTINUE_EXECUTION = "CONTINUE_EXECUTION"
    DELETE_HISTORY = "DELETE_HISTORY"
    INVALIDATE_AUTHORIZATION = "INVALIDATE_AUTHORIZATION"


class RecoveryEvidenceStatus(_ClosedEnum):
    VERIFIED = "VERIFIED"
    MISSING = "MISSING"
    MISMATCH = "MISMATCH"
    INCOMPLETE = "INCOMPLETE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


def _valid_text(value: object, *, optional: bool = False) -> bool:
    if value is None:
        return optional
    if type(value) is not str or not value or "\0" in value:
        return False
    try:
        return len(value.encode("utf-8", errors="strict")) <= _MAX_TEXT_BYTES
    except UnicodeError:
        return False


@dataclass(frozen=True, slots=True)
class ContainerObservation:
    container_id: str
    task_id: str
    run_id: str
    terminal: bool

    def __post_init__(self) -> None:
        if (
            not _valid_text(self.container_id)
            or not _valid_text(self.task_id)
            or not _valid_text(self.run_id)
            or type(self.terminal) is not bool
        ):
            raise ValueError("container observation is invalid")


@dataclass(frozen=True, slots=True)
class RecoveryFinding:
    kind: RecoveryFindingKind
    task_id: str
    run_id: str | None
    lease_id: str | None
    transaction_id: str | None
    journal_reference: str | None
    evidence_status: RecoveryEvidenceStatus
    decision: RecoveryDecision
    blocks_execution: bool
    reason: str
    cleanup_safe: bool = False
    next_command: str | None = None
    blocked_reason: BlockedReason | None = None
    finding_id: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.kind) is not RecoveryFindingKind
            or not _valid_text(self.task_id)
            or not _valid_text(self.run_id, optional=True)
            or not _valid_text(self.lease_id, optional=True)
            or not _valid_text(self.transaction_id, optional=True)
            or not _valid_text(self.journal_reference, optional=True)
            or type(self.evidence_status) is not RecoveryEvidenceStatus
            or type(self.decision) is not RecoveryDecision
            or type(self.blocks_execution) is not bool
            or not _valid_text(self.reason)
            or type(self.cleanup_safe) is not bool
            or not _valid_text(self.next_command, optional=True)
            or self.blocked_reason is not None
            and type(self.blocked_reason) is not BlockedReason
        ):
            raise ValueError("recovery finding is invalid")
        canonical = json.dumps(
            (
                self.kind.value,
                self.task_id,
                self.run_id,
                self.lease_id,
                self.transaction_id,
                self.journal_reference,
                self.evidence_status.value,
                self.decision.value,
                self.blocks_execution,
                self.reason,
                self.cleanup_safe,
                self.next_command,
                (
                    None
                    if self.blocked_reason is None
                    else self.blocked_reason.value
                ),
            ),
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        object.__setattr__(
            self,
            "finding_id",
            "recovery-finding:" + hashlib.sha256(canonical).hexdigest(),
        )

    def to_record(self) -> RecoveryFindingRecord:
        return RecoveryFindingRecord(
            finding_id=self.finding_id,
            kind=self.kind.value,
            task_id=self.task_id,
            run_id=self.run_id,
            lease_id=self.lease_id,
            transaction_id=self.transaction_id,
            journal_reference=self.journal_reference,
            reason=self.reason,
            blocks_execution=self.blocks_execution,
        )


@dataclass(frozen=True, slots=True)
class StartupRecoveryReport:
    findings: tuple[RecoveryFinding, ...]
    execution_permitted: bool
    normal_execution_blocked: bool

    def __post_init__(self) -> None:
        if (
            type(self.findings) is not tuple
            or len(self.findings) > 1000
            or any(type(item) is not RecoveryFinding for item in self.findings)
            or type(self.execution_permitted) is not bool
            or type(self.normal_execution_blocked) is not bool
            or self.execution_permitted == self.normal_execution_blocked
            or self.normal_execution_blocked
            != any(item.blocks_execution for item in self.findings)
        ):
            raise ValueError("startup recovery report is invalid")


class RecoveryCoordinatorAdapter:
    """Bind a trusted target root to the existing WP-14 authority."""

    def __init__(
        self,
        *,
        coordinator: RecoveryCoordinator,
        target_root: Path,
    ) -> None:
        if (
            type(coordinator) is not RecoveryCoordinator
            or not isinstance(target_root, Path)
        ):
            raise ValueError("recovery coordinator adapter is invalid")
        self._coordinator = coordinator
        self._target_root = target_root

    def recover(self, *, transaction_id: str):
        if not _valid_text(transaction_id):
            raise ValueError("recovery delegation is invalid")
        return self._coordinator.recover(
            transaction_id=transaction_id,
            target_root=self._target_root,
        )


def _finding_sort_key(finding: RecoveryFinding) -> tuple[str, ...]:
    return (
        finding.kind.value,
        finding.task_id,
        finding.run_id or "",
        finding.transaction_id or "",
        finding.finding_id,
    )


class StartupRecovery:
    """Scan trusted facts and delegate effects to their existing authorities."""

    def __init__(
        self,
        *,
        store,
        lease_service,
        transaction_root: Path,
        task_root: Path,
        container_probe,
        recovery_delegate,
        event_reader,
        candidate_limit: int,
    ) -> None:
        if (
            not isinstance(transaction_root, Path)
            or not isinstance(task_root, Path)
            or type(candidate_limit) is not int
            or candidate_limit < 1
            or candidate_limit > 1000
        ):
            raise ValueError("startup recovery coordinator is invalid")
        self._store = store
        self._lease_service = lease_service
        self._transaction_root = transaction_root
        self._task_root = task_root
        self._container_probe = container_probe
        self._recovery_delegate = recovery_delegate
        self._event_reader = event_reader
        self._candidate_limit = candidate_limit
        self._task_root_identity = self._directory_identity(task_root)

    @staticmethod
    def _directory_identity(path: Path) -> tuple[int, int] | None:
        try:
            status = os.lstat(path)
        except OSError:
            return None
        if (
            stat.S_ISLNK(status.st_mode)
            or not stat.S_ISDIR(status.st_mode)
            or status.st_uid != os.geteuid()
        ):
            return None
        return (status.st_dev, status.st_ino)

    @staticmethod
    def _report(findings: list[RecoveryFinding]) -> StartupRecoveryReport:
        ordered = tuple(sorted(findings, key=_finding_sort_key))
        blocked = any(item.blocks_execution for item in ordered)
        return StartupRecoveryReport(
            findings=ordered,
            execution_permitted=not blocked,
            normal_execution_blocked=blocked,
        )

    def _persist(self, finding: RecoveryFinding, *, now: int) -> None:
        if finding.task_id == _SYSTEM_TASK:
            return
        self._store.record_recovery_finding(
            finding=finding.to_record(),
            occurred_at=now,
        )

    def _waiting_finding(
        self,
        candidate: StartupRecoveryCandidate,
        *,
        now: int,
    ) -> RecoveryFinding | None:
        if (
            candidate.approval_plan_version_identity is not None
            and candidate.plan_version_identity is not None
            and candidate.approval_plan_version_identity
            != candidate.plan_version_identity
        ):
            return RecoveryFinding(
                kind=RecoveryFindingKind.STALE_APPROVAL,
                task_id=candidate.task_id,
                run_id=candidate.run_id,
                lease_id=None,
                transaction_id=None,
                journal_reference=None,
                evidence_status=RecoveryEvidenceStatus.MISMATCH,
                decision=RecoveryDecision.INVALIDATE_AUTHORIZATION,
                blocks_execution=True,
                reason="approval is bound to an older plan version",
                cleanup_safe=False,
                next_command="continue_task",
            )
        if candidate.task_state is TaskState.AWAITING_CLARIFICATION:
            return RecoveryFinding(
                kind=RecoveryFindingKind.SAFE_WAITING,
                task_id=candidate.task_id,
                run_id=candidate.run_id,
                lease_id=None,
                transaction_id=None,
                journal_reference=None,
                evidence_status=RecoveryEvidenceStatus.NOT_APPLICABLE,
                decision=RecoveryDecision.PAUSE,
                blocks_execution=False,
                reason="clarification remains paused until explicit continue",
                cleanup_safe=True,
                next_command="submit_clarification",
            )
        if candidate.task_state is TaskState.AWAITING_PLAN_APPROVAL:
            plan_binding_present = (
                candidate.approval_plan_version_identity is not None
                and candidate.plan_version_identity is not None
            )
            lifecycle_valid = (
                candidate.approval_identity is not None
                and candidate.approval_type is ApprovalType.PLAN_APPROVAL
                and candidate.approval_consumed is False
                and candidate.approval_revoked is False
                and candidate.approval_expires_at is not None
                and now < candidate.approval_expires_at
                and plan_binding_present
            )
            if candidate.approval_identity is not None and not lifecycle_valid:
                return RecoveryFinding(
                    kind=RecoveryFindingKind.EVIDENCE_MISMATCH,
                    task_id=candidate.task_id,
                    run_id=candidate.run_id,
                    lease_id=None,
                    transaction_id=None,
                    journal_reference=None,
                    evidence_status=RecoveryEvidenceStatus.MISMATCH,
                    decision=RecoveryDecision.MANUAL_RECOVERY_REQUIRED,
                    blocks_execution=True,
                    reason="plan approval lifecycle evidence is invalid",
                    cleanup_safe=False,
                    next_command="request_plan_approval",
                )
            approved = (
                lifecycle_valid
                and candidate.approval_plan_version_identity
                == candidate.plan_version_identity
            )
            cleanup_safe = (
                approved
                and candidate.container_cleanup_verified
                and candidate.file_effects_cleanup_verified
                and candidate.cleanup_verified
                and self._workspace_matches(candidate)
            )
            if approved and not cleanup_safe:
                return RecoveryFinding(
                    kind=RecoveryFindingKind.EVIDENCE_MISMATCH,
                    task_id=candidate.task_id,
                    run_id=candidate.run_id,
                    lease_id=None,
                    transaction_id=None,
                    journal_reference=None,
                    evidence_status=RecoveryEvidenceStatus.INCOMPLETE,
                    decision=RecoveryDecision.MANUAL_RECOVERY_REQUIRED,
                    blocks_execution=True,
                    reason="approval wait cleanup evidence is incomplete",
                    cleanup_safe=False,
                    next_command="inspect_cleanup",
                )
            return RecoveryFinding(
                kind=RecoveryFindingKind.SAFE_WAITING,
                task_id=candidate.task_id,
                run_id=candidate.run_id,
                lease_id=None,
                transaction_id=None,
                journal_reference=None,
                evidence_status=RecoveryEvidenceStatus.VERIFIED,
                decision=(
                    RecoveryDecision.RELEASE_ALLOWED
                    if cleanup_safe
                    else RecoveryDecision.PAUSE
                ),
                blocks_execution=not cleanup_safe,
                reason=(
                    "approval wait is safely cleaned up"
                    if cleanup_safe
                    else "unapproved plan revision cannot execute"
                ),
                cleanup_safe=cleanup_safe,
                next_command=(
                    "continue_task" if cleanup_safe else "approve_plan"
                ),
            )
        if candidate.task_state is TaskState.BLOCKED:
            if candidate.blocked_reason is None:
                return RecoveryFinding(
                    kind=RecoveryFindingKind.EVIDENCE_MISMATCH,
                    task_id=candidate.task_id,
                    run_id=candidate.run_id,
                    lease_id=None,
                    transaction_id=None,
                    journal_reference=None,
                    evidence_status=RecoveryEvidenceStatus.INCOMPLETE,
                    decision=RecoveryDecision.MANUAL_RECOVERY_REQUIRED,
                    blocks_execution=True,
                    reason="blocked task reason evidence is missing",
                    next_command="inspect_blocked_reason",
                )
            commands = {
                BlockedReason.PERSISTENCE_FAILED: "repair_persistence",
                BlockedReason.DOCKER_UNAVAILABLE: "repair_docker",
                BlockedReason.PROVIDER_UNAVAILABLE: "repair_provider",
                BlockedReason.PROVIDER_CONFIGURATION_ERROR:
                    "configure_provider",
                BlockedReason.APPLY_CONFLICT: "resolve_apply_conflict",
            }
            return RecoveryFinding(
                kind=RecoveryFindingKind.SAFE_WAITING,
                task_id=candidate.task_id,
                run_id=candidate.run_id,
                lease_id=None,
                transaction_id=None,
                journal_reference=None,
                evidence_status=RecoveryEvidenceStatus.VERIFIED,
                decision=RecoveryDecision.PAUSE,
                blocks_execution=False,
                reason=(
                    "blocked task remains paused: "
                    + candidate.blocked_reason.value
                ),
                cleanup_safe=True,
                next_command=commands.get(
                    candidate.blocked_reason,
                    "reinvestigate_blocker",
                ),
                blocked_reason=candidate.blocked_reason,
            )
        return None

    def _workspace_matches(
        self,
        candidate: StartupRecoveryCandidate,
    ) -> bool:
        if (
            candidate.workspace_reference is None
            or candidate.workspace_identity is None
        ):
            return False
        path = PurePosixPath(candidate.workspace_reference)
        if (
            path.is_absolute()
            or not path.parts
            or any(part in {"", ".", ".."} for part in path.parts)
            or str(path) != candidate.workspace_reference
        ):
            return False
        if self._task_root_identity is None:
            return False
        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptors: list[int] = []
        try:
            descriptor = os.open(self._task_root, flags)
            descriptors.append(descriptor)
            root_status = os.fstat(descriptor)
            if (
                (root_status.st_dev, root_status.st_ino)
                != self._task_root_identity
                or root_status.st_uid != os.geteuid()
            ):
                return False
            for part in path.parts:
                descriptor = os.open(part, flags, dir_fd=descriptor)
                descriptors.append(descriptor)
            status = os.fstat(descriptor)
        except OSError:
            return False
        finally:
            for descriptor in reversed(descriptors):
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if (
            not stat.S_ISDIR(status.st_mode)
            or status.st_uid != os.geteuid()
        ):
            return False
        identity = hashlib.sha256(
            f"{status.st_dev}:{status.st_ino}".encode("ascii")
        ).hexdigest()
        return identity == candidate.workspace_identity

    def scan(
        self,
        *,
        now: int,
        owner_identity: str,
        process_lock_outcome: ProcessLockOutcome,
    ) -> StartupRecoveryReport:
        if (
            type(now) is not int
            or now < 0
            or not _valid_text(owner_identity)
            or type(process_lock_outcome) is not ProcessLockOutcome
        ):
            raise ValueError("startup recovery scan is invalid")
        if process_lock_outcome is not ProcessLockOutcome.ACQUIRED:
            return self._report(
                [
                    RecoveryFinding(
                        kind=RecoveryFindingKind.DUPLICATE_STARTUP,
                        task_id=_SYSTEM_TASK,
                        run_id=None,
                        lease_id=None,
                        transaction_id=None,
                        journal_reference=None,
                        evidence_status=RecoveryEvidenceStatus.VERIFIED,
                        decision=(
                            RecoveryDecision.MANUAL_RECOVERY_REQUIRED
                        ),
                        blocks_execution=True,
                        reason="serve process lock is held elsewhere",
                    )
                ]
            )

        candidates = self._store.startup_recovery_candidates(
            limit=self._candidate_limit,
        )
        if (
            type(candidates) is not tuple
            or any(
                type(candidate) is not StartupRecoveryCandidate
                for candidate in candidates
            )
        ):
            raise ValueError("startup recovery candidates are invalid")
        findings: list[RecoveryFinding] = []
        try:
            journals = enumerate_apply_journals(
                self._transaction_root,
                limit=self._candidate_limit,
            )
        except JournalEnumerationError:
            task = candidates[0] if candidates else None
            finding = RecoveryFinding(
                kind=RecoveryFindingKind.EVIDENCE_MISMATCH,
                task_id=_SYSTEM_TASK if task is None else task.task_id,
                run_id=None if task is None else task.run_id,
                lease_id=None,
                transaction_id=(
                    None if task is None else task.transaction_id
                ),
                journal_reference=None,
                evidence_status=RecoveryEvidenceStatus.INCOMPLETE,
                decision=RecoveryDecision.MANUAL_RECOVERY_REQUIRED,
                blocks_execution=True,
                reason="transaction journal evidence is invalid",
            )
            findings.append(finding)
            self._persist(finding, now=now)
            return self._report(findings)

        journals_by_transaction = {}
        for journal in journals:
            if journal.transaction_id in journals_by_transaction:
                finding = RecoveryFinding(
                    kind=RecoveryFindingKind.EVIDENCE_MISMATCH,
                    task_id=_SYSTEM_TASK,
                    run_id=None,
                    lease_id=None,
                    transaction_id=journal.transaction_id,
                    journal_reference=journal.journal_reference,
                    evidence_status=RecoveryEvidenceStatus.MISMATCH,
                    decision=RecoveryDecision.MANUAL_RECOVERY_REQUIRED,
                    blocks_execution=True,
                    reason="duplicate transaction journal evidence",
                )
                return self._report([finding])
            journals_by_transaction[journal.transaction_id] = journal
        current_lease = self._lease_service.current()
        candidate_by_task_run = {
            (candidate.task_id, candidate.run_id): candidate
            for candidate in candidates
        }
        recovery_lease = None
        if current_lease is not None:
            previous_lease_id = current_lease.lease_id
            lease_finding = RecoveryFinding(
                kind=RecoveryFindingKind.STALE_LEASE,
                task_id=current_lease.task_id,
                run_id=current_lease.run_id,
                lease_id=current_lease.lease_id,
                transaction_id=None,
                journal_reference=None,
                evidence_status=RecoveryEvidenceStatus.VERIFIED,
                decision=RecoveryDecision.REQUEST_RECOVERY_OWNERSHIP,
                blocks_execution=True,
                reason="nonterminal execution lease requires startup review",
            )
            findings.append(lease_finding)
            self._persist(lease_finding, now=now)
            if (
                current_lease.status is LeaseStatus.ACTIVE
            ):
                try:
                    current_lease = self._lease_service.mark_expired(now=now)
                except LeaseError:
                    pass
            if (
                current_lease.status is LeaseStatus.RECOVERY_PENDING
                and (
                    current_lease.task_id,
                    current_lease.run_id,
                )
                in candidate_by_task_run
            ):
                lease_seed = (
                    current_lease.task_id
                    + "\0"
                    + current_lease.run_id
                    + "\0"
                    + str(current_lease.revision)
                ).encode("utf-8")
                requested_lease_id = (
                    "recovery:" + hashlib.sha256(lease_seed).hexdigest()
                )
                try:
                    recovery_lease = self._lease_service.acquire_recovery(
                        lease_id=requested_lease_id,
                        task_id=current_lease.task_id,
                        run_id=current_lease.run_id,
                        owner_identity=owner_identity,
                        phase=TaskState.ROLLING_BACK,
                        expected_pending_revision=current_lease.revision,
                        now=now,
                    )
                except LeaseError:
                    recovery_lease = None
                if recovery_lease is not None and not (
                    getattr(recovery_lease, "lease_id", None)
                    == requested_lease_id
                    and recovery_lease.lease_id != previous_lease_id
                    and getattr(recovery_lease, "task_id", None)
                    == current_lease.task_id
                    and getattr(recovery_lease, "run_id", None)
                    == current_lease.run_id
                    and getattr(recovery_lease, "owner_identity", None)
                    == owner_identity
                    and getattr(recovery_lease, "purpose", None)
                    is LeasePurpose.RECOVERY
                    and getattr(recovery_lease, "status", None)
                    is LeaseStatus.ACTIVE
                    and type(getattr(recovery_lease, "revision", None))
                    is int
                    and recovery_lease.revision == 1
                ):
                    proof_finding = RecoveryFinding(
                        kind=RecoveryFindingKind.EVIDENCE_MISMATCH,
                        task_id=current_lease.task_id,
                        run_id=current_lease.run_id,
                        lease_id=previous_lease_id,
                        transaction_id=None,
                        journal_reference=None,
                        evidence_status=RecoveryEvidenceStatus.MISMATCH,
                        decision=(
                            RecoveryDecision.MANUAL_RECOVERY_REQUIRED
                        ),
                        blocks_execution=True,
                        reason="recovery lease ownership proof is invalid",
                    )
                    findings.append(proof_finding)
                    self._persist(proof_finding, now=now)
                    recovery_lease = None
            # ACTIVE ownership is never inherited across startup. WP-17 must
            # first expire it and grant a new identity/revision-bound lease.

        containers = self._container_probe.scan(
            limit=self._candidate_limit,
        )
        if (
            type(containers) is not tuple
            or len(containers) > self._candidate_limit
        ):
            raise ValueError("container inventory is not bounded")
        for container in containers:
            if type(container) is not ContainerObservation:
                raise ValueError("container inventory is invalid")
            if container.terminal:
                continue
            finding = RecoveryFinding(
                kind=RecoveryFindingKind.RESIDUAL_CONTAINER,
                task_id=container.task_id,
                run_id=container.run_id,
                lease_id=None,
                transaction_id=None,
                journal_reference=None,
                evidence_status=RecoveryEvidenceStatus.VERIFIED,
                decision=RecoveryDecision.MANUAL_RECOVERY_REQUIRED,
                blocks_execution=True,
                reason="residual container requires its owning authority",
            )
            findings.append(finding)
            self._persist(finding, now=now)

        matched_transactions: set[str] = set()
        for candidate in candidates:
            if candidate.transaction_id is None:
                finding = self._waiting_finding(candidate, now=now)
                if finding is not None:
                    findings.append(finding)
                    self._persist(finding, now=now)
                continue
            snapshot = journals_by_transaction.get(
                candidate.transaction_id
            )
            if snapshot is None:
                kind = (
                    RecoveryFindingKind.EVIDENCE_MISMATCH
                    if journals
                    else RecoveryFindingKind.MISSING_JOURNAL
                )
                finding = RecoveryFinding(
                    kind=kind,
                    task_id=candidate.task_id,
                    run_id=candidate.run_id,
                    lease_id=(
                        None
                        if current_lease is None
                        else current_lease.lease_id
                    ),
                    transaction_id=candidate.transaction_id,
                    journal_reference=candidate.journal_reference,
                    evidence_status=(
                        RecoveryEvidenceStatus.MISMATCH
                        if journals
                        else RecoveryEvidenceStatus.MISSING
                    ),
                    decision=RecoveryDecision.MANUAL_RECOVERY_REQUIRED,
                    blocks_execution=True,
                    reason="database and journal evidence do not match",
                )
                findings.append(finding)
                self._persist(finding, now=now)
                continue
            matched_transactions.add(candidate.transaction_id)
            evidence_matches = (
                candidate.journal_reference == snapshot.journal_reference
                and candidate.apply_phase is snapshot.phase
                and (
                    candidate.apply_plan_digest is None
                    or candidate.apply_plan_digest == snapshot.plan_digest
                )
            )
            if not evidence_matches:
                finding = RecoveryFinding(
                    kind=RecoveryFindingKind.EVIDENCE_MISMATCH,
                    task_id=candidate.task_id,
                    run_id=candidate.run_id,
                    lease_id=(
                        None
                        if current_lease is None
                        else current_lease.lease_id
                    ),
                    transaction_id=candidate.transaction_id,
                    journal_reference=candidate.journal_reference,
                    evidence_status=RecoveryEvidenceStatus.MISMATCH,
                    decision=RecoveryDecision.MANUAL_RECOVERY_REQUIRED,
                    blocks_execution=True,
                    reason="database and journal evidence contradict",
                )
                findings.append(finding)
                self._persist(finding, now=now)
                continue
            delegated = (
                recovery_lease is not None
                and recovery_lease.task_id == candidate.task_id
                and recovery_lease.run_id == candidate.run_id
                and snapshot.blocking
            )
            decision = (
                RecoveryDecision.DELEGATE_RECOVERY
                if delegated
                else RecoveryDecision.REQUEST_RECOVERY_OWNERSHIP
            )
            finding = RecoveryFinding(
                kind=RecoveryFindingKind.NONTERMINAL_APPLY,
                task_id=candidate.task_id,
                run_id=candidate.run_id,
                lease_id=(
                    None
                    if recovery_lease is None
                    else recovery_lease.lease_id
                ),
                transaction_id=candidate.transaction_id,
                journal_reference=snapshot.journal_reference,
                evidence_status=RecoveryEvidenceStatus.VERIFIED,
                decision=decision,
                blocks_execution=snapshot.blocking,
                reason="nonterminal apply transaction requires recovery",
            )
            findings.append(finding)
            self._persist(finding, now=now)
            if delegated:
                result = self._recovery_delegate.recover(
                    transaction_id=candidate.transaction_id,
                )
                self._store.record_apply_observation(
                    task_id=candidate.task_id,
                    result=result,
                    journal_reference=snapshot.journal_reference,
                    occurred_at=now,
                )

        for transaction_id, snapshot in journals_by_transaction.items():
            if transaction_id in matched_transactions:
                continue
            finding = RecoveryFinding(
                kind=RecoveryFindingKind.EVIDENCE_MISMATCH,
                task_id=_SYSTEM_TASK,
                run_id=None,
                lease_id=None,
                transaction_id=transaction_id,
                journal_reference=snapshot.journal_reference,
                evidence_status=RecoveryEvidenceStatus.MISMATCH,
                decision=RecoveryDecision.MANUAL_RECOVERY_REQUIRED,
                blocks_execution=True,
                reason="journal has no authoritative database candidate",
            )
            findings.append(finding)

        return self._report(findings)


__all__ = [
    "ContainerObservation",
    "RecoveryDecision",
    "RecoveryEvidenceStatus",
    "RecoveryFinding",
    "RecoveryFindingKind",
    "RecoveryCoordinatorAdapter",
    "StartupRecovery",
    "StartupRecoveryReport",
]
