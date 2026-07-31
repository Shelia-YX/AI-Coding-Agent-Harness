"""Deterministic demonstration of fail-closed apply recovery evidence."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

from coding_harness.domain.enums import TaskState
from coding_harness.transaction.apply import ApplyCoordinator
from coding_harness.transaction.conflicts import ApplyConfirmation
from coding_harness.transaction.journal import ApplyJournal
from coding_harness.transaction.models import ApplyDecision, ApplyPhase
from coding_harness.workspace.changeset import compute_changeset
from coding_harness.workspace.manifest import build_baseline
from coding_harness.workspace.materialize import materialize_workspace


def _git(root: Path, *arguments: str) -> None:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "LC_ALL": "C",
        }
    )
    subprocess.run(
        ["git", *arguments],
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def run_demo() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="coding-harness-recovery-demo-") as temp:
        root = Path(temp)
        repository = root / "repository"
        repository.mkdir()
        originals = {
            "a.txt": b"a:baseline\n",
            "z.txt": b"z:baseline\n",
        }
        for relative, content in originals.items():
            destination = repository / relative
            destination.write_bytes(content)

        _git(repository, "init", "-q")
        _git(repository, "add", "--", *sorted(originals))
        _git(
            repository,
            "-c",
            "user.name=Course Demo",
            "-c",
            "user.email=course-demo@example.invalid",
            "commit",
            "-q",
            "-m",
            "baseline",
        )

        baseline = build_baseline(repository)
        workspace = materialize_workspace(baseline, root / "workspace")
        (workspace.root / "a.txt").write_bytes(b"agent:a\n")
        (workspace.root / "z.txt").write_bytes(b"agent:z\n")
        changeset = compute_changeset(baseline, workspace)
        confirmation = ApplyConfirmation(
            task_id="course-demo-task",
            changeset_digest=changeset.digest,
            baseline_manifest_digest=baseline.digest,
            plan_version_identity="course-demo-plan",
            acceptance_contract_version_identity="course-demo-contract",
            expected_state=TaskState.READY_TO_APPLY,
            idempotency_key="course-demo-apply-1",
        )

        original_record = ApplyJournal.record

        def inject_prepare_failure(
            journal: ApplyJournal,
            stage: object,
            status: object,
            **kwargs: object,
        ) -> object:
            if kwargs.get("phase") is ApplyPhase.PREPARING:
                raise OSError("deterministic demo journal persistence failure")
            return original_record(journal, stage, status, **kwargs)

        with patch.object(ApplyJournal, "record", inject_prepare_failure):
            result = ApplyCoordinator(root / "transactions").apply(
                transaction_id="course-demo-transaction",
                baseline=baseline,
                changeset=changeset,
                workspace=workspace,
                target_root=repository,
                decision=ApplyDecision.APPLY,
                confirmation=confirmation,
                current_task_id="course-demo-task",
                current_plan_version_identity="course-demo-plan",
                current_acceptance_contract_version_identity="course-demo-contract",
                current_state=TaskState.READY_TO_APPLY,
                current_idempotency_key="course-demo-apply-1",
                acceptance_satisfied=True,
                nonterminal_apply_transaction=False,
                recovery_required=False,
                policy_denied=False,
            )

        partial_effect = any(
            (repository / relative).read_bytes() != content
            for relative, content in originals.items()
        )
        return {
            "scenario": "recovery_rollback",
            "result": result.phase.value,
            "partial_effect": partial_effect,
        }


if __name__ == "__main__":
    print(json.dumps(run_demo(), sort_keys=True, separators=(",", ":")))
