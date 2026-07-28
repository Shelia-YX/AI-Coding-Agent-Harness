"""Startup inspection and deterministic continuation of disk transactions."""

from __future__ import annotations

from pathlib import Path

from coding_harness.domain.enums import TaskState
from coding_harness.transaction.apply import (
    _created_parents_restored,
    _directory_exists,
    _directory_identity,
    _index_digest,
    _plan_filesystem_identity_matches,
    _restore_entry,
    _snapshot,
    _snapshot_matches,
    _resolve_transaction_artifacts,
    _transaction_artifacts_absent,
    _trusted_root,
    _verify_applied,
    _verify_restored,
)
from coding_harness.transaction.journal import ApplyJournal
from coding_harness.transaction.models import (
    ApplyDecision,
    ApplyPhase,
    ApplyResult,
    JournalStage,
    JournalStatus,
    RecoveryState,
)


def _recovery_required(
    transaction_id: str,
    journal: ApplyJournal,
    reason: str,
) -> ApplyResult:
    try:
        if journal.latest_phase is not ApplyPhase.RECOVERY_REQUIRED:
            journal.record(
                JournalStage.RECOVERY,
                JournalStatus.COMPLETED,
                phase=ApplyPhase.RECOVERY_REQUIRED,
                detail="startup evidence cannot prove a safe terminal state",
            )
    except BaseException:
        # A corrupt or unwriteable nonterminal log is itself blocking evidence.
        pass
    return ApplyResult(
        transaction_id=transaction_id,
        decision=ApplyDecision.APPLY,
        phase=ApplyPhase.RECOVERY_REQUIRED,
        task_state=TaskState.RECOVERY_REQUIRED,
        recovery_state=RecoveryState.RECOVERY_REQUIRED,
        plan=journal.plan,
        journal=journal,
        index_digest_after=None,
        reason=reason,
    )


def _all_created_parent_evidence(
    journal: ApplyJournal,
    plan,
) -> dict[str, dict[str, str]]:
    owners = {
        path.identity: entry
        for entry in plan.entries
        for path in entry.created_parent_paths
    }
    evidence: dict[str, dict[str, str]] = {
        entry.path.identity: {} for entry in plan.entries
    }
    for record in journal.records:
        if (
            record.stage is JournalStage.APPLY
            and record.status is JournalStatus.COMPLETED
            and record.path is not None
            and record.evidence_digest is not None
            and record.path.identity in owners
        ):
            owner = owners[record.path.identity]
            if record.detail != "created parent for " + owner.path.canonical:
                raise ValueError("created parent evidence is inconsistent")
            owner_evidence = evidence[owner.path.identity]
            previous = owner_evidence.get(record.path.identity)
            if previous is not None and previous != record.evidence_digest:
                raise ValueError("created parent evidence is inconsistent")
            owner_evidence[record.path.identity] = record.evidence_digest
    return evidence


def _created_parent_cleanup_needed(
    target: Path,
    entry,
    evidence: dict[str, str],
) -> bool:
    needed = False
    for path in entry.created_parent_paths:
        if not _directory_exists(target, path):
            continue
        needed = True
        expected = evidence.get(path.identity)
        if expected is None or _directory_identity(target, path) != expected:
            raise ValueError("created parent evidence is incomplete")
    return needed


class RecoveryCoordinator:
    def __init__(self, transaction_root: Path) -> None:
        if not isinstance(transaction_root, Path):
            raise ValueError("recovery coordinator is invalid")
        self._transaction_root = transaction_root

    def recover(
        self,
        *,
        transaction_id: str,
        target_root: Path,
    ) -> ApplyResult:
        journal = ApplyJournal.open_existing(
            self._transaction_root,
            transaction_id,
        )
        plan = journal.plan
        target = _trusted_root(target_root)
        phase = journal.latest_phase
        if not _plan_filesystem_identity_matches(target, plan):
            return _recovery_required(
                transaction_id,
                journal,
                "target filesystem identity does not match the apply plan",
            )
        if phase is ApplyPhase.RECOVERY_REQUIRED:
            return _recovery_required(
                transaction_id,
                journal,
                "manual recovery evidence is required",
            )
        if phase is ApplyPhase.APPLIED:
            index_after = _index_digest(target)
            if (
                _verify_applied(target, plan)
                and _transaction_artifacts_absent(target, plan)
                and index_after == plan.index_digest_before
            ):
                return ApplyResult(
                    transaction_id=transaction_id,
                    decision=ApplyDecision.APPLY,
                    phase=ApplyPhase.APPLIED,
                    task_state=TaskState.COMPLETED,
                    recovery_state=RecoveryState.SUCCESS,
                    plan=plan,
                    journal=journal,
                    index_digest_after=index_after,
                    reason="applied transaction evidence verified",
                )
            return _recovery_required(
                transaction_id,
                journal,
                "terminal apply evidence is incomplete",
            )
        if phase is ApplyPhase.ROLLED_BACK:
            index_after = _index_digest(target)
            if (
                _verify_restored(target, plan.entries)
                and _created_parents_restored(target, plan.entries)
                and _transaction_artifacts_absent(target, plan)
                and index_after == plan.index_digest_before
            ):
                return ApplyResult(
                    transaction_id=transaction_id,
                    decision=ApplyDecision.APPLY,
                    phase=ApplyPhase.ROLLED_BACK,
                    task_state=TaskState.FAILED,
                    recovery_state=RecoveryState.FAILED,
                    plan=plan,
                    journal=journal,
                    index_digest_after=index_after,
                    reason="rolled back transaction evidence verified",
                )
            return _recovery_required(
                transaction_id,
                journal,
                "terminal rollback evidence is incomplete",
            )
        if phase not in {ApplyPhase.APPLYING, ApplyPhase.ROLLING_BACK}:
            return _recovery_required(
                transaction_id,
                journal,
                "transaction did not reach a provably recoverable effect phase",
            )

        completed_apply = {
            record.path.identity
            for record in journal.records
            if record.stage is JournalStage.APPLY
            and record.status is JournalStatus.COMPLETED
            and record.path is not None
        }
        pending_apply = {
            record.path.identity
            for record in journal.records
            if record.stage is JournalStage.APPLY
            and record.status is JournalStatus.PENDING
            and record.path is not None
        }
        completed_rollback = {
            record.path.identity
            for record in journal.records
            if record.stage is JournalStage.ROLLBACK
            and record.status is JournalStatus.COMPLETED
            and record.path is not None
        }
        pending_rollback = {
            record.path.identity
            for record in journal.records
            if record.stage is JournalStage.ROLLBACK
            and record.status is JournalStatus.PENDING
            and record.path is not None
        }
        affected = []
        try:
            for entry in plan.entries:
                _resolve_transaction_artifacts(
                    target,
                    entry,
                    transaction_id,
                    phase,
                )
            created_evidence = _all_created_parent_evidence(journal, plan)
            for entry in plan.entries:
                entry_evidence = created_evidence[entry.path.identity]
                created_cleanup = _created_parent_cleanup_needed(
                    target,
                    entry,
                    entry_evidence,
                )
                current = _snapshot(target, entry.path)
                if entry.path.identity in completed_rollback:
                    if (
                        not _snapshot_matches(current, entry, new=False)
                        or created_cleanup
                    ):
                        raise ValueError
                elif entry.path.identity in pending_rollback:
                    if _snapshot_matches(current, entry, new=False):
                        if created_cleanup:
                            affected.append(entry)
                        else:
                            affected.append(entry)
                        continue
                    if not _snapshot_matches(current, entry, new=True):
                        raise ValueError
                    affected.append(entry)
                elif entry.path.identity in completed_apply:
                    if not _snapshot_matches(current, entry, new=True):
                        raise ValueError
                    affected.append(entry)
                elif entry.path.identity in pending_apply:
                    if _snapshot_matches(current, entry, new=True):
                        affected.append(entry)
                    elif not _snapshot_matches(current, entry, new=False):
                        raise ValueError
                    elif created_cleanup:
                        affected.append(entry)
                elif not _snapshot_matches(current, entry, new=False):
                    raise ValueError
                elif created_cleanup:
                    raise ValueError
        except Exception:
            return _recovery_required(
                transaction_id,
                journal,
                "startup target state cannot be classified",
            )

        if phase is ApplyPhase.APPLYING:
            try:
                journal.record(
                    JournalStage.ROLLBACK,
                    JournalStatus.COMPLETED,
                    phase=ApplyPhase.ROLLING_BACK,
                    detail="startup rollback phase persisted",
                )
            except Exception:
                return _recovery_required(
                    transaction_id,
                    journal,
                    "startup rollback phase could not be persisted",
                )
        try:
            for entry in reversed(affected):
                current = _snapshot(target, entry.path)
                cleanup_needed = _created_parent_cleanup_needed(
                    target,
                    entry,
                    created_evidence.get(entry.path.identity, {}),
                )
                if (
                    _snapshot_matches(current, entry, new=False)
                    and not cleanup_needed
                ):
                    if entry.path.identity in pending_rollback:
                        journal.record(
                            JournalStage.ROLLBACK,
                            JournalStatus.COMPLETED,
                            path=entry.path,
                            detail="rollback effect verified",
                            evidence_digest=entry.expected_original_digest,
                        )
                    continue
                if entry.path.identity not in pending_rollback:
                    journal.record(
                        JournalStage.ROLLBACK,
                        JournalStatus.PENDING,
                        path=entry.path,
                        detail="rollback effect pending",
                    )
                _restore_entry(
                    target,
                    entry,
                    journal,
                    created_parent_evidence=created_evidence.get(
                        entry.path.identity
                    ),
                )
                if not _snapshot_matches(
                    _snapshot(target, entry.path),
                    entry,
                    new=False,
                ):
                    raise ValueError
                journal.record(
                    JournalStage.ROLLBACK,
                    JournalStatus.COMPLETED,
                    path=entry.path,
                    detail="rollback effect verified",
                    evidence_digest=entry.expected_original_digest,
                )
            if (
                not _verify_restored(target, tuple(affected))
                or not _transaction_artifacts_absent(target, plan)
            ):
                raise ValueError
            if not _created_parents_restored(target, tuple(affected)):
                raise ValueError
            index_after = _index_digest(target)
            if index_after != plan.index_digest_before:
                raise ValueError
            journal.record(
                JournalStage.VERIFY,
                JournalStatus.COMPLETED,
                detail="rollback index digest rechecked",
                evidence_digest=index_after,
            )
            journal.record(
                JournalStage.VERIFY,
                JournalStatus.COMPLETED,
                phase=ApplyPhase.ROLLED_BACK,
                detail="startup rollback verified",
                evidence_digest=plan.digest,
            )
            return ApplyResult(
                transaction_id=transaction_id,
                decision=ApplyDecision.APPLY,
                phase=ApplyPhase.ROLLED_BACK,
                task_state=TaskState.FAILED,
                recovery_state=RecoveryState.FAILED,
                plan=plan,
                journal=journal,
                index_digest_after=index_after,
                reason="startup rollback completed",
            )
        except Exception:
            return _recovery_required(
                transaction_id,
                journal,
                "startup rollback could not be proven",
            )


__all__ = ["RecoveryCoordinator"]
