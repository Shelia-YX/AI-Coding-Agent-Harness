"""Governed materialization of approved ignored inputs for WP-11."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

from coding_harness.domain.approvals import (
    Approval,
    ApprovalExecutionContext,
    ApprovalResult,
    ApprovalType,
    PresentedApprovalReference,
    consume_approval,
)
from coding_harness.domain.policy import PolicyDecisionRecord
from coding_harness.workspace.manifest import BaselineManifest
from coding_harness.workspace.materialize import TaskWorkspace
from coding_harness.workspace.paths import RepoPath


_APPROVAL_CONFLICT = "IGNORED_INPUT_APPROVAL_CONFLICT"
_BINDING_MISMATCH = "IGNORED_INPUT_BINDING_MISMATCH"
_LIMIT_EXCEEDED = "IGNORED_INPUT_LIMIT"
_MATERIALIZATION_FAILED = "IGNORED_INPUT_MATERIALIZATION_FAILED"
_MATERIALIZED = "IGNORED_INPUT_MATERIALIZED"
_GIT_TIMEOUT_SECONDS = 2.0


class IgnoredInputMode(StrEnum):
    READ_ONLY_INPUT = "read_only_input"
    WRITABLE_EPHEMERAL = "writable_ephemeral"

    def __bool__(self) -> bool:
        raise TypeError("IgnoredInputMode has no truth value")


class IgnoredInputKind(StrEnum):
    REGULAR_FILE = "regular_file"

    def __bool__(self) -> bool:
        raise TypeError("IgnoredInputKind has no truth value")


def _is_digest(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _update_digest(digest: object, value: object) -> None:
    encoded = str(value).encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "big"))
    digest.update(encoded)


@dataclass(frozen=True, slots=True)
class SandboxInputEntry:
    path: RepoPath
    kind: IgnoredInputKind
    size: int
    content_digest: str
    mode: IgnoredInputMode
    allowed_stages: tuple[str, ...]
    changeset_eligible: bool = False
    writeback_permitted: bool = False
    exportable_to_llm: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.path) is not RepoPath
            or type(self.kind) is not IgnoredInputKind
            or type(self.size) is not int
            or self.size < 0
            or not _is_digest(self.content_digest)
            or type(self.mode) is not IgnoredInputMode
            or type(self.allowed_stages) is not tuple
            or not self.allowed_stages
            or any(type(stage) is not str or not stage for stage in self.allowed_stages)
            or self.changeset_eligible is not False
            or self.writeback_permitted is not False
            or self.exportable_to_llm is not False
        ):
            raise ValueError("sandbox input entry is invalid")

    def __bool__(self) -> bool:
        raise TypeError("SandboxInputEntry has no truth value")


def _manifest_digest(
    *,
    identity: str,
    revision: int,
    baseline_digest: str,
    entries: tuple[SandboxInputEntry, ...],
) -> str:
    digest = hashlib.sha256(b"coding-harness:sandbox-input-manifest:v1")
    for value in (identity, revision, baseline_digest, len(entries)):
        _update_digest(digest, value)
    for entry in entries:
        for value in (
            entry.path.identity,
            entry.path.canonical,
            entry.kind.value,
            entry.size,
            entry.content_digest,
            entry.mode.value,
            *entry.allowed_stages,
            entry.changeset_eligible,
            entry.writeback_permitted,
            entry.exportable_to_llm,
        ):
            _update_digest(digest, value)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class SandboxInputManifest:
    identity: str
    revision: int
    baseline_digest: str
    entries: tuple[SandboxInputEntry, ...]
    digest: str
    exportable_to_llm: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.identity) is not str
            or not self.identity
            or type(self.revision) is not int
            or self.revision < 1
            or not _is_digest(self.baseline_digest)
            or type(self.entries) is not tuple
            or not self.entries
            or any(type(entry) is not SandboxInputEntry for entry in self.entries)
            or tuple(sorted(self.entries, key=lambda item: item.path.canonical))
            != self.entries
            or len({entry.path.identity for entry in self.entries}) != len(self.entries)
            or not _is_digest(self.digest)
            or self.digest
            != _manifest_digest(
                identity=self.identity,
                revision=self.revision,
                baseline_digest=self.baseline_digest,
                entries=self.entries,
            )
            or self.exportable_to_llm is not False
        ):
            raise ValueError("sandbox input manifest is invalid")

    def __bool__(self) -> bool:
        raise TypeError("SandboxInputManifest has no truth value")


@dataclass(frozen=True, slots=True)
class IgnoredInputMaterializationResult:
    permitted: bool
    side_effect_permitted: bool
    reason: str
    approval_result: ApprovalResult
    manifest: SandboxInputManifest | None
    workspace: TaskWorkspace
    changeset_eligible_paths: tuple[str, ...] = ()
    writeback_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.permitted) is not bool
            or type(self.side_effect_permitted) is not bool
            or type(self.reason) is not str
            or not self.reason
            or type(self.approval_result) is not ApprovalResult
            or type(self.workspace) is not TaskWorkspace
            or (
                self.manifest is not None
                and type(self.manifest) is not SandboxInputManifest
            )
            or type(self.changeset_eligible_paths) is not tuple
            or type(self.writeback_paths) is not tuple
            or self.changeset_eligible_paths
            or self.writeback_paths
            or self.permitted is not self.side_effect_permitted
            or self.permitted != (self.manifest is not None)
        ):
            raise ValueError("ignored input result is invalid")

    def __bool__(self) -> bool:
        raise TypeError("IgnoredInputMaterializationResult has no truth value")


def _approval_failure(record: object, expected_revision: object) -> ApprovalResult:
    revision = (
        record.revision
        if type(record) is Approval
        else expected_revision
        if type(expected_revision) is int and expected_revision >= 1
        else 1
    )
    return ApprovalResult(
        permitted=False,
        conflict=True,
        side_effect_permitted=False,
        reason="APPROVAL_CONFLICT",
        approval=record,  # type: ignore[arg-type]
        previous_revision=revision,
        expected_revision=revision,
        new_revision=None,
    )


def _denied(
    *,
    reason: str,
    approval_result: ApprovalResult,
    workspace: TaskWorkspace,
) -> IgnoredInputMaterializationResult:
    denied_approval = replace(
        approval_result,
        permitted=False,
        side_effect_permitted=False,
        reason=reason,
    )
    return IgnoredInputMaterializationResult(
        permitted=False,
        side_effect_permitted=False,
        reason=reason,
        approval_result=denied_approval,
        manifest=None,
        workspace=workspace,
    )


def _workspace_matches_baseline(
    workspace: TaskWorkspace,
    baseline: BaselineManifest,
) -> bool:
    return (
        workspace.baseline_digest == baseline.digest
        and workspace.source_head == baseline.source_head
        and workspace.source_branch == baseline.source_branch
        and workspace.source_index_digest == baseline.source_index_digest
        and workspace.source_status_digest == baseline.source_status_digest
    )


def _git_environment() -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "LC_ALL": "C",
        }
    )
    return environment


def _is_ignored(root: Path, path: RepoPath) -> bool:
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", "--", path.canonical],
            cwd=root,
            env=_git_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _safe_root(root: object) -> Path | None:
    if not isinstance(root, Path):
        return None
    try:
        status = os.lstat(root)
        resolved = root.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
        return None
    return resolved


def _sensitive(path: RepoPath) -> bool:
    return any(segment.casefold() == ".env" for segment in path.segments)


def _read_bound_regular(
    root: Path,
    path: RepoPath,
    *,
    max_bytes: int,
) -> bytes | None:
    current = root
    try:
        for segment in path.segments[:-1]:
            current /= segment
            status = os.lstat(current)
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
                return None
        candidate = current / path.segments[-1]
        status = os.lstat(candidate)
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
            return None
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(candidate, flags)
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_dev != status.st_dev
                or opened.st_ino != status.st_ino
            ):
                return None
            content = bytearray()
            while len(content) <= max_bytes:
                chunk = os.read(descriptor, min(64 * 1024, max_bytes + 1 - len(content)))
                if not chunk:
                    break
                content.extend(chunk)
            if len(content) > max_bytes:
                return None
            final = os.fstat(descriptor)
            if (
                final.st_dev != opened.st_dev
                or final.st_ino != opened.st_ino
                or final.st_size != opened.st_size
                or final.st_mtime_ns != opened.st_mtime_ns
            ):
                return None
            return bytes(content)
        finally:
            os.close(descriptor)
    except (OSError, ValueError):
        return None


def _make_manifest(
    *,
    current: SandboxInputManifest | None,
    identity: str,
    baseline_digest: str,
    entry: SandboxInputEntry,
) -> SandboxInputManifest | None:
    if current is None:
        revision = 1
        entries = (entry,)
    else:
        if (
            current.baseline_digest != baseline_digest
            or current.identity == identity
            or any(existing.path.identity == entry.path.identity for existing in current.entries)
        ):
            return None
        revision = current.revision + 1
        entries = tuple(
            sorted((*current.entries, entry), key=lambda item: item.path.canonical)
        )
    return SandboxInputManifest(
        identity=identity,
        revision=revision,
        baseline_digest=baseline_digest,
        entries=entries,
        digest=_manifest_digest(
            identity=identity,
            revision=revision,
            baseline_digest=baseline_digest,
            entries=entries,
        ),
    )


def _write_copy(
    *,
    workspace: TaskWorkspace,
    path: RepoPath,
    content: bytes,
    mode: IgnoredInputMode,
) -> bool:
    root = workspace.root
    target = root.joinpath(*path.segments)
    created_directories: list[Path] = []
    try:
        current = root
        for segment in path.segments[:-1]:
            current /= segment
            if not os.path.lexists(current):
                current.mkdir(mode=0o700)
                created_directories.append(current)
            status = os.lstat(current)
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
                return False
        if os.path.lexists(target):
            return False
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(target, flags, 0o600)
        try:
            remaining = memoryview(content)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise OSError("write failed")
                remaining = remaining[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.chmod(
            target,
            0o400 if mode is IgnoredInputMode.READ_ONLY_INPUT else 0o600,
        )
        return target.read_bytes() == content
    except OSError:
        try:
            if os.path.lexists(target):
                target.unlink()
        except OSError:
            pass
        for directory in reversed(created_directories):
            try:
                directory.rmdir()
            except OSError:
                break
        return False


def materialize_ignored_input(
    *,
    source_root: Path,
    baseline: BaselineManifest,
    workspace: TaskWorkspace,
    current_manifest: SandboxInputManifest | None,
    current_record: Approval,
    expected_revision: int,
    presented_reference: PresentedApprovalReference,
    current_context: ApprovalExecutionContext,
    trusted_policy_record: PolicyDecisionRecord,
    trusted_policy_record_identity: str,
    now: int,
    max_input_count: int,
    max_input_bytes: int,
) -> IgnoredInputMaterializationResult:
    """Consume one trusted approval and copy one ignored input fail-closed."""

    fallback = _approval_failure(current_record, expected_revision)
    if (
        type(baseline) is not BaselineManifest
        or type(workspace) is not TaskWorkspace
        or (
            current_manifest is not None
            and type(current_manifest) is not SandboxInputManifest
        )
        or type(max_input_count) is not int
        or max_input_count < 0
        or type(max_input_bytes) is not int
        or max_input_bytes < 0
        or not _workspace_matches_baseline(workspace, baseline)
    ):
        return _denied(
            reason=_BINDING_MISMATCH,
            approval_result=fallback,
            workspace=workspace,
        )

    try:
        approval_result = consume_approval(
            current_record=current_record,
            expected_revision=expected_revision,
            presented_reference=presented_reference,
            current_context=current_context,
            trusted_policy_record=trusted_policy_record,
            trusted_policy_record_identity=trusted_policy_record_identity,
            now=now,
        )
    except (TypeError, ValueError):
        return _denied(
            reason=_APPROVAL_CONFLICT,
            approval_result=fallback,
            workspace=workspace,
        )
    if not approval_result.permitted or not approval_result.side_effect_permitted:
        return _denied(
            reason=_APPROVAL_CONFLICT,
            approval_result=approval_result,
            workspace=workspace,
        )

    approval = approval_result.approval
    if (
        approval.approval_type is not ApprovalType.ACTION_APPROVAL
        or approval.action_kind != "include_ignored_input"
        or approval.baseline_manifest_digest != baseline.digest
        or approval.exportable_to_llm is not False
        or len(approval.ignored_entries) != 1
        or len(approval.normalized_paths) != 1
        or approval.sandbox_manifest_identity is None
        or "EXECUTING" not in approval.allowed_stages
    ):
        return _denied(
            reason=_BINDING_MISMATCH,
            approval_result=approval_result,
            workspace=workspace,
        )
    try:
        mode = IgnoredInputMode(approval.ignored_input_mode)
        path = RepoPath.parse(approval.normalized_paths[0])
    except (TypeError, ValueError):
        return _denied(
            reason=_BINDING_MISMATCH,
            approval_result=approval_result,
            workspace=workspace,
        )
    if _sensitive(path):
        return _denied(
            reason=_BINDING_MISMATCH,
            approval_result=approval_result,
            workspace=workspace,
        )
    approved_path, approved_kind, approved_size, approved_digest = (
        approval.ignored_entries[0]
    )
    if (
        approved_path != path.canonical
        or approved_kind != IgnoredInputKind.REGULAR_FILE.value
        or type(approved_size) is not int
        or approved_size < 0
        or not _is_digest(approved_digest)
    ):
        return _denied(
            reason=_BINDING_MISMATCH,
            approval_result=approval_result,
            workspace=workspace,
        )
    existing_count = 0 if current_manifest is None else len(current_manifest.entries)
    existing_bytes = (
        0
        if current_manifest is None
        else sum(entry.size for entry in current_manifest.entries)
    )
    if (
        existing_count + 1 > max_input_count
        or existing_bytes + approved_size > max_input_bytes
    ):
        return _denied(
            reason=_LIMIT_EXCEEDED,
            approval_result=approval_result,
            workspace=workspace,
        )
    trusted_root = _safe_root(source_root)
    if trusted_root is None or not _is_ignored(trusted_root, path):
        return _denied(
            reason=_BINDING_MISMATCH,
            approval_result=approval_result,
            workspace=workspace,
        )
    content = _read_bound_regular(
        trusted_root,
        path,
        max_bytes=max_input_bytes - existing_bytes,
    )
    if (
        content is None
        or len(content) != approved_size
        or hashlib.sha256(content).hexdigest() != approved_digest
    ):
        return _denied(
            reason=_BINDING_MISMATCH,
            approval_result=approval_result,
            workspace=workspace,
        )

    entry = SandboxInputEntry(
        path=path,
        kind=IgnoredInputKind.REGULAR_FILE,
        size=len(content),
        content_digest=approved_digest,
        mode=mode,
        allowed_stages=tuple(approval.allowed_stages),
    )
    manifest = _make_manifest(
        current=current_manifest,
        identity=approval.sandbox_manifest_identity,
        baseline_digest=baseline.digest,
        entry=entry,
    )
    if manifest is None:
        return _denied(
            reason=_BINDING_MISMATCH,
            approval_result=approval_result,
            workspace=workspace,
        )
    if not _write_copy(
        workspace=workspace,
        path=path,
        content=content,
        mode=mode,
    ):
        return _denied(
            reason=_MATERIALIZATION_FAILED,
            approval_result=approval_result,
            workspace=workspace,
        )
    return IgnoredInputMaterializationResult(
        permitted=True,
        side_effect_permitted=True,
        reason=_MATERIALIZED,
        approval_result=approval_result,
        manifest=manifest,
        workspace=workspace,
    )


__all__ = [
    "IgnoredInputMaterializationResult",
    "IgnoredInputMode",
    "SandboxInputEntry",
    "SandboxInputManifest",
    "materialize_ignored_input",
]
