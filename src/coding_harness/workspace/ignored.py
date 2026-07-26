"""Governed materialization of approved ignored inputs for WP-11."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
import errno
import hashlib
import os
from pathlib import Path
import stat

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
_WORKSPACE_BINDING_MISMATCH = "IGNORED_INPUT_WORKSPACE_BINDING_MISMATCH"
_SOURCE_CONTAINMENT_FAILED = "IGNORED_INPUT_SOURCE_CONTAINMENT_FAILED"
_DESTINATION_CONTAINMENT_FAILED = "IGNORED_INPUT_DESTINATION_CONTAINMENT_FAILED"
_HARDLINK_REJECTED = "IGNORED_INPUT_HARDLINK_REJECTED"
_SOURCE_CHANGED = "IGNORED_INPUT_SOURCE_CHANGED"
_LIMIT_EXCEEDED = "IGNORED_INPUT_LIMIT"
_MATERIALIZATION_FAILED = "IGNORED_INPUT_MATERIALIZATION_FAILED"
_CLEANUP_FAILED = "IGNORED_INPUT_CLEANUP_FAILED"
_NO_CLOBBER_UNSUPPORTED = "IGNORED_INPUT_NO_CLOBBER_UNSUPPORTED"
_TARGET_CONFLICT = "IGNORED_INPUT_TARGET_CONFLICT"
_MATERIALIZED = "IGNORED_INPUT_MATERIALIZED"


class IgnoredInputMode(StrEnum):
    READ_ONLY_INPUT = "read_only_input"
    WRITABLE_EPHEMERAL = "writable_ephemeral"

    def __bool__(self) -> bool:
        raise TypeError("IgnoredInputMode has no truth value")


class IgnoredInputKind(StrEnum):
    REGULAR_FILE = "regular_file"

    def __bool__(self) -> bool:
        raise TypeError("IgnoredInputKind has no truth value")


class IgnoredInputPublicationState(StrEnum):
    DENIED = "DENIED"
    PUBLISHED_PENDING_COMMIT = "PUBLISHED_PENDING_COMMIT"

    def __bool__(self) -> bool:
        raise TypeError("IgnoredInputPublicationState has no truth value")


class ExpectedManifestIdentityReason(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_IDENTIFIER = "INVALID_IDENTIFIER"
    INVALID_DIGEST = "INVALID_DIGEST"
    INVALID_REPO_PATH = "INVALID_REPO_PATH"
    INVALID_ENTRY_TYPE = "INVALID_ENTRY_TYPE"
    INVALID_MODE = "INVALID_MODE"
    INVALID_STAGE_SET = "INVALID_STAGE_SET"
    DUPLICATE_SOURCE = "DUPLICATE_SOURCE"
    INVALID_SIZE = "INVALID_SIZE"
    INVALID_LIMIT = "INVALID_LIMIT"
    INVALID_REVISION = "INVALID_REVISION"
    INVALID_PREVIOUS_MANIFEST = "INVALID_PREVIOUS_MANIFEST"
    COUNT_LIMIT_EXCEEDED = "COUNT_LIMIT_EXCEEDED"
    BYTE_LIMIT_EXCEEDED = "BYTE_LIMIT_EXCEEDED"


class ExpectedManifestIdentityError(ValueError):
    def __init__(self, reason: ExpectedManifestIdentityReason) -> None:
        self.reason = reason
        super().__init__("expected manifest identity request is invalid")


@dataclass(frozen=True, slots=True)
class PreviousSandboxInputManifestRef:
    revision: int
    identity: str
    digest: str


@dataclass(frozen=True, slots=True)
class ExpectedManifestEntry:
    source: RepoPath
    kind: IgnoredInputKind
    approved_size: int
    content_digest: str
    mode: IgnoredInputMode
    allowed_stages: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExpectedManifestIdentityRequest:
    task_id: str
    plan_version_identity: str
    baseline_digest: str
    previous_manifest: PreviousSandboxInputManifestRef | None
    new_revision: int
    entries: tuple[ExpectedManifestEntry, ...]
    idempotency_key: str
    max_input_count: int
    max_input_bytes: int


@dataclass(frozen=True, slots=True)
class ExpectedManifestIdentityResult:
    workspace_logical_identity: str
    expected_manifest_identity: str


_TYPE_UTF8 = 1
_TYPE_UINT = 2
_TYPE_ENUM = 4
_TYPE_DIGEST = 5
_TYPE_REPO_PATH = 6
_TYPE_LIST = 8
_TYPE_STRUCT = 9
_TYPE_VARIANT = 10
_IDENTITY_SCHEMA_V1 = b"\x01"
_WORKSPACE_IDENTITY_DOMAIN = b"coding-harness:workspace-logical-identity"
_EXPECTED_IDENTITY_DOMAIN = b"coding-harness:sandbox-input-expected-identity"
_VALID_STAGE_SETS = {
    ("EXECUTING",),
    ("EXECUTING", "VERIFYING"),
}


def _identity_error(
    reason: ExpectedManifestIdentityReason,
) -> ExpectedManifestIdentityError:
    return ExpectedManifestIdentityError(reason)


def _varuint(value: int) -> bytes:
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            encoded.append(byte | 0x80)
        else:
            encoded.append(byte)
            return bytes(encoded)


def _typed(type_code: int, payload: bytes) -> bytes:
    return bytes((type_code,)) + _varuint(len(payload)) + payload


def _field(tag: int, value: bytes) -> bytes:
    return _varuint(tag) + value


def _struct(*fields: tuple[int, bytes]) -> bytes:
    payload = _varuint(len(fields)) + b"".join(
        _field(tag, value) for tag, value in fields
    )
    return _typed(_TYPE_STRUCT, payload)


def _list(*values: bytes) -> bytes:
    return _typed(_TYPE_LIST, _varuint(len(values)) + b"".join(values))


def _variant(tag: int, value: bytes) -> bytes:
    return _typed(_TYPE_VARIANT, _varuint(tag) + value)


def _utf8(value: str) -> bytes:
    return _typed(_TYPE_UTF8, value.encode("utf-8", errors="strict"))


def _enum(value: str) -> bytes:
    return _typed(_TYPE_ENUM, value.encode("ascii", errors="strict"))


def _uint(value: int) -> bytes:
    return _typed(_TYPE_UINT, _varuint(value))


def _digest_value(value: str) -> bytes:
    return _typed(_TYPE_DIGEST, bytes.fromhex(value))


def _repo_path_value(value: RepoPath) -> bytes:
    return _typed(
        _TYPE_REPO_PATH,
        value.canonical.encode("utf-8", errors="strict"),
    )


def _identity_stream(domain: bytes, root: bytes) -> bytes:
    return _varuint(len(domain)) + domain + _IDENTITY_SCHEMA_V1 + root


def _valid_identifier(value: object) -> bool:
    if type(value) is not str or not value:
        return False
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError:
        return False
    return True


def _validate_expected_identity_request(
    request: object,
) -> ExpectedManifestIdentityRequest:
    if type(request) is not ExpectedManifestIdentityRequest:
        raise _identity_error(ExpectedManifestIdentityReason.INVALID_REQUEST)
    if type(request.entries) is not tuple:
        raise _identity_error(ExpectedManifestIdentityReason.INVALID_REQUEST)
    if any(type(entry) is not ExpectedManifestEntry for entry in request.entries):
        raise _identity_error(ExpectedManifestIdentityReason.INVALID_REQUEST)
    if request.previous_manifest is not None and (
        type(request.previous_manifest) is not PreviousSandboxInputManifestRef
    ):
        raise _identity_error(ExpectedManifestIdentityReason.INVALID_REQUEST)
    for value in (
        request.task_id,
        request.plan_version_identity,
        request.idempotency_key,
    ):
        if not _valid_identifier(value):
            raise _identity_error(ExpectedManifestIdentityReason.INVALID_IDENTIFIER)
    if not _is_digest(request.baseline_digest):
        raise _identity_error(ExpectedManifestIdentityReason.INVALID_DIGEST)
    if type(request.new_revision) is not int or request.new_revision < 1:
        raise _identity_error(ExpectedManifestIdentityReason.INVALID_REVISION)
    previous = request.previous_manifest
    if previous is None:
        if request.new_revision != 1:
            raise _identity_error(ExpectedManifestIdentityReason.INVALID_REVISION)
    elif (
        type(previous.revision) is not int
        or previous.revision < 1
        or not _is_digest(previous.identity)
        or not _is_digest(previous.digest)
    ):
        raise _identity_error(
            ExpectedManifestIdentityReason.INVALID_PREVIOUS_MANIFEST
        )
    elif request.new_revision != previous.revision + 1:
        raise _identity_error(ExpectedManifestIdentityReason.INVALID_REVISION)
    if (
        type(request.max_input_count) is not int
        or request.max_input_count < 0
        or type(request.max_input_bytes) is not int
        or request.max_input_bytes < 0
    ):
        raise _identity_error(ExpectedManifestIdentityReason.INVALID_LIMIT)
    if len(request.entries) > request.max_input_count:
        raise _identity_error(ExpectedManifestIdentityReason.COUNT_LIMIT_EXCEEDED)
    total_bytes = 0
    sources: set[str] = set()
    for entry in request.entries:
        if type(entry.source) is not RepoPath:
            raise _identity_error(ExpectedManifestIdentityReason.INVALID_REPO_PATH)
        if type(entry.kind) is not IgnoredInputKind:
            raise _identity_error(ExpectedManifestIdentityReason.INVALID_ENTRY_TYPE)
        if entry.kind is not IgnoredInputKind.REGULAR_FILE:
            raise _identity_error(ExpectedManifestIdentityReason.INVALID_ENTRY_TYPE)
        if type(entry.approved_size) is not int or entry.approved_size < 0:
            raise _identity_error(ExpectedManifestIdentityReason.INVALID_SIZE)
        if not _is_digest(entry.content_digest):
            raise _identity_error(ExpectedManifestIdentityReason.INVALID_DIGEST)
        if type(entry.mode) is not IgnoredInputMode:
            raise _identity_error(ExpectedManifestIdentityReason.INVALID_MODE)
        if type(entry.allowed_stages) is not tuple:
            raise _identity_error(ExpectedManifestIdentityReason.INVALID_REQUEST)
        if entry.allowed_stages not in _VALID_STAGE_SETS:
            raise _identity_error(ExpectedManifestIdentityReason.INVALID_STAGE_SET)
        if entry.source.canonical in sources:
            raise _identity_error(ExpectedManifestIdentityReason.DUPLICATE_SOURCE)
        sources.add(entry.source.canonical)
        total_bytes += entry.approved_size
    if total_bytes > request.max_input_bytes:
        raise _identity_error(ExpectedManifestIdentityReason.BYTE_LIMIT_EXCEEDED)
    return request


def _workspace_identity_v1(request: ExpectedManifestIdentityRequest) -> str:
    root = _struct(
        (1, _utf8(request.task_id)),
        (2, _utf8(request.plan_version_identity)),
        (3, _digest_value(request.baseline_digest)),
    )
    return hashlib.sha256(
        _identity_stream(_WORKSPACE_IDENTITY_DOMAIN, root)
    ).hexdigest()


def _previous_value(
    previous: PreviousSandboxInputManifestRef | None,
) -> bytes:
    if previous is None:
        return _variant(0, _struct())
    return _variant(
        1,
        _struct(
            (1, _digest_value(previous.identity)),
            (2, _digest_value(previous.digest)),
        ),
    )


def _expected_entry_value(entry: ExpectedManifestEntry) -> bytes:
    return _struct(
        (1, _repo_path_value(entry.source)),
        (2, _enum(entry.kind.value)),
        (3, _uint(entry.approved_size)),
        (4, _digest_value(entry.content_digest)),
        (5, _enum(entry.mode.value)),
        (6, _list(*(_enum(stage) for stage in entry.allowed_stages))),
        (7, _repo_path_value(entry.source)),
    )


def compute_expected_manifest_identity(
    request: ExpectedManifestIdentityRequest,
) -> ExpectedManifestIdentityResult:
    validated = _validate_expected_identity_request(request)
    workspace_identity = _workspace_identity_v1(validated)
    entries = tuple(
        sorted(
            validated.entries,
            key=lambda entry: entry.source.canonical.encode(
                "utf-8",
                errors="strict",
            ),
        )
    )
    root = _struct(
        (1, _utf8(validated.task_id)),
        (2, _utf8(validated.plan_version_identity)),
        (3, _digest_value(validated.baseline_digest)),
        (4, _digest_value(workspace_identity)),
        (5, _previous_value(validated.previous_manifest)),
        (6, _uint(validated.new_revision)),
        (7, _list(*(_expected_entry_value(entry) for entry in entries))),
        (8, _utf8(validated.idempotency_key)),
    )
    expected_identity = hashlib.sha256(
        _identity_stream(_EXPECTED_IDENTITY_DOMAIN, root)
    ).hexdigest()
    return ExpectedManifestIdentityResult(
        workspace_logical_identity=workspace_identity,
        expected_manifest_identity=expected_identity,
    )


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


def _hash(namespace: bytes, *values: object) -> str:
    digest = hashlib.sha256(namespace)
    for value in values:
        _update_digest(digest, value)
    return digest.hexdigest()


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


def _entry_values(entry: SandboxInputEntry) -> tuple[object, ...]:
    return (
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
    )


def _manifest_digest(
    *,
    identity: str,
    revision: int,
    baseline_digest: str,
    approval_intent_digest: str,
    workspace_logical_identity: str,
    entries: tuple[SandboxInputEntry, ...],
) -> str:
    digest = hashlib.sha256(b"coding-harness:sandbox-input-manifest:v2")
    for value in (
        identity,
        revision,
        baseline_digest,
        approval_intent_digest,
        workspace_logical_identity,
        False,
        len(entries),
    ):
        _update_digest(digest, value)
    for entry in entries:
        for value in _entry_values(entry):
            _update_digest(digest, value)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class SandboxInputManifest:
    identity: str
    revision: int
    baseline_digest: str
    entries: tuple[SandboxInputEntry, ...]
    digest: str
    approval_intent_digest: str
    workspace_logical_identity: str
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
            or not _is_digest(self.approval_intent_digest)
            or not _is_digest(self.workspace_logical_identity)
            or not _is_digest(self.digest)
            or self.digest
            != _manifest_digest(
                identity=self.identity,
                revision=self.revision,
                baseline_digest=self.baseline_digest,
                approval_intent_digest=self.approval_intent_digest,
                workspace_logical_identity=self.workspace_logical_identity,
                entries=self.entries,
            )
            or self.exportable_to_llm is not False
        ):
            raise ValueError("sandbox input manifest is invalid")

    def __bool__(self) -> bool:
        raise TypeError("SandboxInputManifest has no truth value")


@dataclass(frozen=True, slots=True)
class ApprovalCASIntent:
    approval_identity: str
    previous_revision: int
    expected_revision: int
    new_revision: int
    candidate_approval: Approval
    digest: str

    def __post_init__(self) -> None:
        if (
            type(self.approval_identity) is not str
            or not self.approval_identity
            or type(self.previous_revision) is not int
            or type(self.expected_revision) is not int
            or type(self.new_revision) is not int
            or self.previous_revision < 1
            or self.expected_revision != self.previous_revision
            or self.new_revision != self.previous_revision + 1
            or type(self.candidate_approval) is not Approval
            or self.candidate_approval.identity != self.approval_identity
            or self.candidate_approval.revision != self.new_revision
            or self.candidate_approval.consumed is not True
            or not _is_digest(self.digest)
            or self.digest
            != _hash(
                b"coding-harness:approval-cas-intent:v1",
                self.approval_identity,
                self.previous_revision,
                self.expected_revision,
                self.new_revision,
                self.candidate_approval.request_digest,
                self.candidate_approval.policy_record_identity,
                self.candidate_approval.policy_record_digest,
                self.candidate_approval.idempotency_key,
            )
        ):
            raise ValueError("approval CAS intent is invalid")


@dataclass(frozen=True, slots=True)
class PublicationReceipt:
    workspace_device: int
    workspace_inode: int
    parent_device: int
    parent_inode: int
    target_device: int
    target_inode: int
    target_size: int
    target_digest: str
    relative_path: str

    def __post_init__(self) -> None:
        if (
            any(
                type(value) is not int or value < 0
                for value in (
                    self.workspace_device,
                    self.workspace_inode,
                    self.parent_device,
                    self.parent_inode,
                    self.target_device,
                    self.target_inode,
                    self.target_size,
                )
            )
            or not _is_digest(self.target_digest)
            or type(self.relative_path) is not str
            or not self.relative_path
        ):
            raise ValueError("publication receipt is invalid")


@dataclass(frozen=True, slots=True)
class IgnoredInputMaterializationResult:
    permitted: bool
    side_effect_permitted: bool
    reason: str
    approval_result: ApprovalResult
    manifest: SandboxInputManifest | None
    workspace: TaskWorkspace
    state: IgnoredInputPublicationState
    candidate_manifest: SandboxInputManifest | None = None
    active_manifest: SandboxInputManifest | None = None
    approval_cas_intent: ApprovalCASIntent | None = None
    publication_receipt: PublicationReceipt | None = None
    persistence_committed: bool = False
    execution_permitted: bool = False
    changeset_permitted: bool = False
    export_permitted: bool = False
    cleanup_complete: bool = True
    cleanup_reason: str | None = None
    operation_reason: str | None = None
    expected_manifest_identity: str | None = None
    workspace_logical_identity: str | None = None
    changeset_eligible_paths: tuple[str, ...] = ()
    writeback_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        pending = self.state is IgnoredInputPublicationState.PUBLISHED_PENDING_COMMIT
        if (
            type(self.permitted) is not bool
            or type(self.side_effect_permitted) is not bool
            or type(self.reason) is not str
            or not self.reason
            or type(self.approval_result) is not ApprovalResult
            or type(self.workspace) is not TaskWorkspace
            or type(self.state) is not IgnoredInputPublicationState
            or self.active_manifest is not None
            or self.persistence_committed is not False
            or self.execution_permitted is not False
            or self.changeset_permitted is not False
            or self.export_permitted is not False
            or type(self.cleanup_complete) is not bool
            or (
                self.cleanup_reason is not None
                and (type(self.cleanup_reason) is not str or not self.cleanup_reason)
            )
            or (
                self.operation_reason is not None
                and (type(self.operation_reason) is not str or not self.operation_reason)
            )
            or (
                self.expected_manifest_identity is not None
                and (
                    type(self.expected_manifest_identity) is not str
                    or not self.expected_manifest_identity
                )
            )
            or (
                self.workspace_logical_identity is not None
                and not _is_digest(self.workspace_logical_identity)
            )
            or type(self.changeset_eligible_paths) is not tuple
            or type(self.writeback_paths) is not tuple
            or self.changeset_eligible_paths
            or self.writeback_paths
            or self.permitted is not self.side_effect_permitted
            or self.permitted != pending
            or self.permitted != (self.manifest is not None)
            or self.manifest is not self.candidate_manifest
            or pending != (self.approval_cas_intent is not None)
            or pending != (self.publication_receipt is not None)
            or (not pending and self.candidate_manifest is not None)
            or (not self.cleanup_complete and self.cleanup_reason != _CLEANUP_FAILED)
        ):
            raise ValueError("ignored input result is invalid")

    def __bool__(self) -> bool:
        raise TypeError("IgnoredInputMaterializationResult has no truth value")


@dataclass(frozen=True, slots=True)
class _ReadResult:
    content: bytes | None
    reason: str | None


@dataclass(frozen=True, slots=True)
class _PublishResult:
    receipt: PublicationReceipt | None
    reason: str | None
    cleanup_complete: bool
    cleanup_reason: str | None


@dataclass(frozen=True, slots=True)
class _OwnedObjectReceipt:
    parent_fd: int
    name: str
    device: int
    inode: int
    object_type: int
    phase: str


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


def _original_approval_result(
    record: Approval,
    *,
    expected_revision: int,
    reason: str,
) -> ApprovalResult:
    return ApprovalResult(
        permitted=False,
        conflict=reason == _APPROVAL_CONFLICT,
        side_effect_permitted=False,
        reason=reason,
        approval=record,
        previous_revision=record.revision,
        expected_revision=expected_revision,
        new_revision=None,
    )


def _denied(
    *,
    reason: str,
    approval_result: ApprovalResult,
    workspace: TaskWorkspace,
    expected_manifest_identity: str | None = None,
    workspace_logical_identity: str | None = None,
    cleanup_complete: bool = True,
    cleanup_reason: str | None = None,
    operation_reason: str | None = None,
) -> IgnoredInputMaterializationResult:
    denied_approval = replace(
        approval_result,
        permitted=False,
        side_effect_permitted=False,
        reason=reason,
        new_revision=None,
    )
    return IgnoredInputMaterializationResult(
        permitted=False,
        side_effect_permitted=False,
        reason=reason,
        approval_result=denied_approval,
        manifest=None,
        workspace=workspace,
        state=IgnoredInputPublicationState.DENIED,
        cleanup_complete=cleanup_complete,
        cleanup_reason=cleanup_reason,
        operation_reason=operation_reason,
        expected_manifest_identity=expected_manifest_identity,
        workspace_logical_identity=workspace_logical_identity,
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


def _workspace_identity(
    *,
    task_id: str,
    plan_version_identity: str,
    baseline_digest: str,
) -> str:
    return _hash(
        b"coding-harness:workspace-logical-identity:v1",
        task_id,
        plan_version_identity,
        baseline_digest,
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


def _is_ignored(root_fd: int, path: RepoPath) -> bool:
    descriptor_path = f"/proc/self/fd/{root_fd}"
    was_inheritable = False
    try:
        was_inheritable = os.get_inheritable(root_fd)
        os.set_inheritable(root_fd, True)
        process = os.posix_spawnp(
            "git",
            [
                "git",
                "-C",
                descriptor_path,
                "check-ignore",
                "-q",
                "--",
                path.canonical,
            ],
            _git_environment(),
        )
        _, status = os.waitpid(process, 0)
    except (AttributeError, OSError):
        return False
    finally:
        try:
            os.set_inheritable(root_fd, was_inheritable)
        except OSError:
            pass
    return os.waitstatus_to_exitcode(status) == 0


def _sensitive(path: RepoPath) -> bool:
    return any(segment.casefold() == ".env" for segment in path.segments)


def _platform_supported() -> bool:
    return (
        hasattr(os, "O_NOFOLLOW")
        and hasattr(os, "O_DIRECTORY")
        and bool(os.supports_dir_fd)
        and bool(os.supports_follow_symlinks)
        and hasattr(os, "link")
    )


def _open_root(root: Path) -> tuple[int, os.stat_result] | None:
    descriptor: int | None = None
    try:
        before = os.lstat(root)
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
            return None
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        opened = os.fstat(descriptor)
        after = os.lstat(root)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
            or (after.st_dev, after.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            os.close(descriptor)
            return None
        return descriptor, opened
    except OSError:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        return None


def _read_bound_regular(
    root_fd: int,
    root_status: os.stat_result,
    path: RepoPath,
    *,
    approved_size: int,
) -> _ReadResult:
    descriptors: list[int] = []
    result = _ReadResult(None, _SOURCE_CHANGED)
    try:
        current_fd = root_fd
        for segment in path.segments[:-1]:
            descriptor = os.open(
                segment,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=current_fd,
            )
            descriptors.append(descriptor)
            current_fd = descriptor
        descriptor = os.open(
            path.segments[-1],
            os.O_RDONLY | os.O_NOFOLLOW,
            dir_fd=current_fd,
        )
        descriptors.append(descriptor)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            result = _ReadResult(None, _SOURCE_CONTAINMENT_FAILED)
        elif opened.st_nlink > 1:
            result = _ReadResult(None, _HARDLINK_REJECTED)
        elif opened.st_size != approved_size:
            result = _ReadResult(None, _BINDING_MISMATCH)
        else:
            content = bytearray()
            digest = hashlib.sha256()
            while len(content) <= approved_size:
                remaining = approved_size + 1 - len(content)
                if remaining <= 0:
                    break
                chunk = os.read(descriptor, remaining)
                if not chunk:
                    break
                content.extend(chunk)
                digest.update(chunk)
            final = os.fstat(descriptor)
            root_final = os.fstat(root_fd)
            if (
                len(content) > approved_size
                or (final.st_dev, final.st_ino) != (opened.st_dev, opened.st_ino)
                or final.st_size != opened.st_size
                or final.st_mtime_ns != opened.st_mtime_ns
                or final.st_ctime_ns != opened.st_ctime_ns
                or final.st_nlink != opened.st_nlink
                or len(content) != approved_size
                or digest.hexdigest() != hashlib.sha256(content).hexdigest()
            ):
                result = _ReadResult(None, _SOURCE_CHANGED)
            elif (root_final.st_dev, root_final.st_ino) != (
                root_status.st_dev,
                root_status.st_ino,
            ):
                result = _ReadResult(None, _SOURCE_CONTAINMENT_FAILED)
            else:
                result = _ReadResult(bytes(content), None)
    except OSError:
        result = _ReadResult(None, _SOURCE_CONTAINMENT_FAILED)
    finally:
        close_failed = False
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                close_failed = True
        if close_failed:
            result = _ReadResult(None, _SOURCE_CHANGED)
    return result


def _cas_intent(result: ApprovalResult) -> ApprovalCASIntent:
    approval = result.approval
    digest = _hash(
        b"coding-harness:approval-cas-intent:v1",
        approval.identity,
        result.previous_revision,
        result.expected_revision,
        result.new_revision,
        approval.request_digest,
        approval.policy_record_identity,
        approval.policy_record_digest,
        approval.idempotency_key,
    )
    return ApprovalCASIntent(
        approval_identity=approval.identity,
        previous_revision=result.previous_revision,
        expected_revision=result.expected_revision,
        new_revision=result.new_revision,  # type: ignore[arg-type]
        candidate_approval=approval,
        digest=digest,
    )


def _expected_identity(
    *,
    approval: Approval,
    current: SandboxInputManifest | None,
    workspace_logical_identity: str,
    entry: SandboxInputEntry,
) -> str:
    if current is None:
        return approval.sandbox_manifest_identity or ""
    return _hash(
        b"coding-harness:sandbox-input-expected-identity:v1",
        approval.sandbox_manifest_identity,
        approval.task_id,
        approval.plan_version.identity,
        approval.baseline_manifest_digest,
        workspace_logical_identity,
        current.identity,
        current.digest,
        current.revision + 1,
        *_entry_values(entry),
        approval.idempotency_key,
    )


def _make_manifest(
    *,
    current: SandboxInputManifest | None,
    identity: str,
    baseline_digest: str,
    workspace_logical_identity: str,
    approval_intent_digest: str,
    entry: SandboxInputEntry,
) -> SandboxInputManifest | None:
    if current is None:
        revision = 1
        entries = (entry,)
    else:
        if (
            current.baseline_digest != baseline_digest
            or current.workspace_logical_identity != workspace_logical_identity
            or current.identity == identity
            or any(existing.path.identity == entry.path.identity for existing in current.entries)
        ):
            return None
        revision = current.revision + 1
        entries = tuple(
            sorted((*current.entries, entry), key=lambda item: item.path.canonical)
        )
    digest = _manifest_digest(
        identity=identity,
        revision=revision,
        baseline_digest=baseline_digest,
        approval_intent_digest=approval_intent_digest,
        workspace_logical_identity=workspace_logical_identity,
        entries=entries,
    )
    return SandboxInputManifest(
        identity=identity,
        revision=revision,
        baseline_digest=baseline_digest,
        entries=entries,
        digest=digest,
        approval_intent_digest=approval_intent_digest,
        workspace_logical_identity=workspace_logical_identity,
    )


def _owned_receipt(
    *,
    parent_fd: int,
    name: str,
    status: os.stat_result,
    phase: str,
) -> _OwnedObjectReceipt:
    return _OwnedObjectReceipt(
        parent_fd=parent_fd,
        name=name,
        device=status.st_dev,
        inode=status.st_ino,
        object_type=stat.S_IFMT(status.st_mode),
        phase=phase,
    )


def _receipt_matches(receipt: _OwnedObjectReceipt) -> bool:
    try:
        current = os.stat(
            receipt.name,
            dir_fd=receipt.parent_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return False
    except OSError:
        return False
    return (
        current.st_dev == receipt.device
        and current.st_ino == receipt.inode
        and stat.S_IFMT(current.st_mode) == receipt.object_type
    )


def _remove_owned(receipt: _OwnedObjectReceipt) -> bool:
    if not _receipt_matches(receipt):
        return False
    try:
        if receipt.object_type == stat.S_IFDIR:
            os.rmdir(receipt.name, dir_fd=receipt.parent_fd)
        else:
            os.unlink(receipt.name, dir_fd=receipt.parent_fd)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True


def _cleanup_owned(
    *,
    published: _OwnedObjectReceipt | None,
    temporary: _OwnedObjectReceipt | None,
    created_directories: list[_OwnedObjectReceipt],
) -> bool:
    complete = True
    if published is not None and not _remove_owned(published):
        complete = False
    if temporary is not None and not _remove_owned(temporary):
        complete = False
    for directory in reversed(created_directories):
        if not _remove_owned(directory):
            complete = False
            break
    return complete


def _close_descriptors(descriptors: list[int]) -> bool:
    complete = True
    while descriptors:
        descriptor = descriptors.pop()
        try:
            os.close(descriptor)
        except OSError:
            complete = False
    return complete


def _publish_copy(
    *,
    workspace: TaskWorkspace,
    source_root_status: os.stat_result,
    path: RepoPath,
    content: bytes,
    mode: IgnoredInputMode,
) -> _PublishResult:
    opened_root = _open_root(workspace.root)
    if opened_root is None:
        return _PublishResult(None, _DESTINATION_CONTAINMENT_FAILED, True, None)
    root_fd, root_status = opened_root
    if (root_status.st_dev, root_status.st_ino) == (
        source_root_status.st_dev,
        source_root_status.st_ino,
    ):
        close_complete = _close_descriptors([root_fd])
        return _PublishResult(
            None,
            (
                _WORKSPACE_BINDING_MISMATCH
                if close_complete
                else _CLEANUP_FAILED
            ),
            close_complete,
            None if close_complete else _CLEANUP_FAILED,
        )
    descriptors = [root_fd]
    created_directories: list[_OwnedObjectReceipt] = []
    temporary: _OwnedObjectReceipt | None = None
    published: _OwnedObjectReceipt | None = None
    operation_reason = _MATERIALIZATION_FAILED
    result: _PublishResult
    try:
        try:
            os.stat(".git", dir_fd=root_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            operation_reason = _WORKSPACE_BINDING_MISMATCH
            raise OSError(errno.EPERM, "workspace contains git metadata")
        current_fd = root_fd
        for segment in path.segments[:-1]:
            created = False
            try:
                os.mkdir(segment, mode=0o700, dir_fd=current_fd)
                created = True
            except FileExistsError:
                pass
            except OSError:
                operation_reason = _DESTINATION_CONTAINMENT_FAILED
                raise
            try:
                descriptor = os.open(
                    segment,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=current_fd,
                )
            except OSError:
                operation_reason = _DESTINATION_CONTAINMENT_FAILED
                raise
            descriptors.append(descriptor)
            opened = os.fstat(descriptor)
            if not stat.S_ISDIR(opened.st_mode):
                operation_reason = _DESTINATION_CONTAINMENT_FAILED
                raise OSError(errno.ENOTDIR, "unsafe destination parent")
            if created:
                created_directories.append(
                    _owned_receipt(
                        parent_fd=current_fd,
                        name=segment,
                        status=opened,
                        phase="directory",
                    )
                )
            current_fd = descriptor
        parent_fd = current_fd
        parent_status = os.fstat(parent_fd)
        target_name = path.segments[-1]
        temporary_name = ".wp11-ignored-" + _hash(
            b"coding-harness:ignored-temp:v1",
            path.identity,
            hashlib.sha256(content).hexdigest(),
        )[:20]
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        temporary_fd = os.open(temporary_name, flags, 0o600, dir_fd=parent_fd)
        descriptors.append(temporary_fd)
        temporary_status = os.fstat(temporary_fd)
        temporary = _owned_receipt(
            parent_fd=parent_fd,
            name=temporary_name,
            status=temporary_status,
            phase="temporary",
        )
        remaining = memoryview(content)
        written_digest = hashlib.sha256()
        while remaining:
            written = os.write(temporary_fd, remaining)
            if written <= 0:
                raise OSError(errno.EIO, "bounded write failed")
            written_digest.update(remaining[:written])
            remaining = remaining[written:]
        if written_digest.hexdigest() != hashlib.sha256(content).hexdigest():
            raise OSError(errno.EIO, "destination digest mismatch")
        os.fchmod(
            temporary_fd,
            0o400 if mode is IgnoredInputMode.READ_ONLY_INPUT else 0o600,
        )
        os.fsync(temporary_fd)
        temporary_status = os.fstat(temporary_fd)
        temporary = _owned_receipt(
            parent_fd=parent_fd,
            name=temporary_name,
            status=temporary_status,
            phase="temporary",
        )
        try:
            os.link(
                temporary_name,
                target_name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
        except FileExistsError:
            operation_reason = _TARGET_CONFLICT
            raise
        except (NotImplementedError, TypeError):
            operation_reason = _NO_CLOBBER_UNSUPPORTED
            raise
        except OSError:
            operation_reason = _MATERIALIZATION_FAILED
            raise
        published = _owned_receipt(
            parent_fd=parent_fd,
            name=target_name,
            status=temporary_status,
            phase="published",
        )
        os.fsync(parent_fd)
        if not _remove_owned(temporary):
            operation_reason = _CLEANUP_FAILED
            raise OSError(errno.ESTALE, "temporary ownership changed")
        temporary = None
        os.fsync(parent_fd)
        target_status = os.stat(target_name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            (target_status.st_dev, target_status.st_ino)
            != (temporary_status.st_dev, temporary_status.st_ino)
            or target_status.st_size != len(content)
            or not stat.S_ISREG(target_status.st_mode)
        ):
            operation_reason = _DESTINATION_CONTAINMENT_FAILED
            raise OSError(errno.ESTALE, "published target changed")
        root_final = os.fstat(root_fd)
        if (root_final.st_dev, root_final.st_ino) != (
            root_status.st_dev,
            root_status.st_ino,
        ):
            operation_reason = _DESTINATION_CONTAINMENT_FAILED
            raise OSError(errno.ESTALE, "workspace root changed")
        receipt = PublicationReceipt(
            workspace_device=root_status.st_dev,
            workspace_inode=root_status.st_ino,
            parent_device=parent_status.st_dev,
            parent_inode=parent_status.st_ino,
            target_device=target_status.st_dev,
            target_inode=target_status.st_ino,
            target_size=target_status.st_size,
            target_digest=hashlib.sha256(content).hexdigest(),
            relative_path=path.canonical,
        )
        published = None
        result = _PublishResult(receipt, None, True, None)
    except (OSError, ValueError):
        cleanup_complete = _cleanup_owned(
            published=published,
            temporary=temporary,
            created_directories=created_directories,
        )
        result = _PublishResult(
            None,
            (
                operation_reason
                if operation_reason == _TARGET_CONFLICT or cleanup_complete
                else _CLEANUP_FAILED
            ),
            cleanup_complete,
            None if cleanup_complete else _CLEANUP_FAILED,
        )
    close_complete = _close_descriptors(descriptors)
    if not close_complete:
        return _PublishResult(
            None,
            (
                _TARGET_CONFLICT
                if result.reason == _TARGET_CONFLICT
                else _CLEANUP_FAILED
            ),
            False,
            _CLEANUP_FAILED,
        )
    return result


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
    """Publish one approved ignored input, pending persistence CAS commit."""

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
    ):
        return _denied(
            reason=_BINDING_MISMATCH,
            approval_result=fallback,
            workspace=workspace,
        )
    if not _workspace_matches_baseline(workspace, baseline):
        return _denied(
            reason=_WORKSPACE_BINDING_MISMATCH,
            approval_result=fallback,
            workspace=workspace,
        )
    if not _platform_supported():
        return _denied(
            reason=_NO_CLOBBER_UNSUPPORTED,
            approval_result=fallback,
            workspace=workspace,
        )
    if type(current_record) is not Approval:
        return _denied(
            reason=_APPROVAL_CONFLICT,
            approval_result=fallback,
            workspace=workspace,
        )
    try:
        mode = IgnoredInputMode(current_record.ignored_input_mode)
        path = RepoPath.parse(current_record.normalized_paths[0])
        approved_path, approved_kind, approved_size, approved_digest = (
            current_record.ignored_entries[0]
        )
        expected_result = compute_expected_manifest_identity(
            ExpectedManifestIdentityRequest(
                task_id=current_record.task_id,
                plan_version_identity=current_record.plan_version.identity,
                baseline_digest=baseline.digest,
                previous_manifest=(
                    None
                    if current_manifest is None
                    else PreviousSandboxInputManifestRef(
                        revision=current_manifest.revision,
                        identity=current_manifest.identity,
                        digest=current_manifest.digest,
                    )
                ),
                new_revision=(
                    1 if current_manifest is None else current_manifest.revision + 1
                ),
                entries=(
                    ExpectedManifestEntry(
                        source=path,
                        kind=IgnoredInputKind(approved_kind),
                        approved_size=approved_size,
                        content_digest=approved_digest,
                        mode=mode,
                        allowed_stages=tuple(current_record.allowed_stages),
                    ),
                ),
                idempotency_key=current_record.idempotency_key,
                max_input_count=max_input_count,
                max_input_bytes=max_input_bytes,
            )
        )
    except (
        ExpectedManifestIdentityError,
        IndexError,
        TypeError,
        ValueError,
    ):
        return _denied(
            reason=_BINDING_MISMATCH,
            approval_result=_original_approval_result(
                current_record,
                expected_revision=expected_revision,
                reason=_BINDING_MISMATCH,
            ),
            workspace=workspace,
        )
    expected_identity = expected_result.expected_manifest_identity
    workspace_logical_identity = expected_result.workspace_logical_identity
    if current_record.sandbox_manifest_identity != expected_identity:
        return _denied(
            reason=_BINDING_MISMATCH,
            approval_result=_original_approval_result(
                current_record,
                expected_revision=expected_revision,
                reason=_BINDING_MISMATCH,
            ),
            workspace=workspace,
            expected_manifest_identity=expected_identity,
            workspace_logical_identity=workspace_logical_identity,
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
            approval_result=_original_approval_result(
                current_record,
                expected_revision=expected_revision,
                reason=_APPROVAL_CONFLICT,
            ),
            workspace=workspace,
            expected_manifest_identity=expected_identity,
            workspace_logical_identity=workspace_logical_identity,
        )
    if not approval_result.permitted or not approval_result.side_effect_permitted:
        return _denied(
            reason=_APPROVAL_CONFLICT,
            approval_result=_original_approval_result(
                current_record,
                expected_revision=expected_revision,
                reason=_APPROVAL_CONFLICT,
            ),
            workspace=workspace,
            expected_manifest_identity=expected_identity,
            workspace_logical_identity=workspace_logical_identity,
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
        or _sensitive(path)
    ):
        return _denied(
            reason=_BINDING_MISMATCH,
            approval_result=_original_approval_result(
                current_record,
                expected_revision=expected_revision,
                reason=_BINDING_MISMATCH,
            ),
            workspace=workspace,
            workspace_logical_identity=workspace_logical_identity,
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
            approval_result=_original_approval_result(
                current_record,
                expected_revision=expected_revision,
                reason=_BINDING_MISMATCH,
            ),
            workspace=workspace,
            workspace_logical_identity=workspace_logical_identity,
        )
    existing_count = 0 if current_manifest is None else len(current_manifest.entries)
    existing_bytes = (
        0 if current_manifest is None else sum(entry.size for entry in current_manifest.entries)
    )
    if (
        existing_count + 1 > max_input_count
        or existing_bytes + approved_size > max_input_bytes
    ):
        return _denied(
            reason=_LIMIT_EXCEEDED,
            approval_result=_original_approval_result(
                current_record,
                expected_revision=expected_revision,
                reason=_LIMIT_EXCEEDED,
            ),
            workspace=workspace,
            workspace_logical_identity=workspace_logical_identity,
        )
    opened_source = _open_root(source_root)
    if opened_source is None:
        return _denied(
            reason=_SOURCE_CONTAINMENT_FAILED,
            approval_result=_original_approval_result(
                current_record,
                expected_revision=expected_revision,
                reason=_SOURCE_CONTAINMENT_FAILED,
            ),
            workspace=workspace,
            workspace_logical_identity=workspace_logical_identity,
        )
    source_root_fd, source_root_status = opened_source
    source_close_failed = False
    try:
        read_result = _read_bound_regular(
            source_root_fd,
            source_root_status,
            path,
            approved_size=approved_size,
        )
        ignored_by_same_authority = (
            read_result.content is not None
            and _is_ignored(source_root_fd, path)
        )
    finally:
        try:
            os.close(source_root_fd)
        except OSError:
            source_close_failed = True
    if source_close_failed:
        return _denied(
            reason=_SOURCE_CHANGED,
            approval_result=_original_approval_result(
                current_record,
                expected_revision=expected_revision,
                reason=_SOURCE_CHANGED,
            ),
            workspace=workspace,
            workspace_logical_identity=workspace_logical_identity,
        )
    if read_result.content is None:
        return _denied(
            reason=read_result.reason or _BINDING_MISMATCH,
            approval_result=_original_approval_result(
                current_record,
                expected_revision=expected_revision,
                reason=read_result.reason or _BINDING_MISMATCH,
            ),
            workspace=workspace,
            workspace_logical_identity=workspace_logical_identity,
        )
    content = read_result.content
    if (
        not ignored_by_same_authority
        or hashlib.sha256(content).hexdigest() != approved_digest
    ):
        return _denied(
            reason=_BINDING_MISMATCH,
            approval_result=_original_approval_result(
                current_record,
                expected_revision=expected_revision,
                reason=_BINDING_MISMATCH,
            ),
            workspace=workspace,
            workspace_logical_identity=workspace_logical_identity,
        )
    entry = SandboxInputEntry(
        path=path,
        kind=IgnoredInputKind.REGULAR_FILE,
        size=len(content),
        content_digest=approved_digest,
        mode=mode,
        allowed_stages=tuple(approval.allowed_stages),
    )
    intent = _cas_intent(approval_result)
    manifest = _make_manifest(
        current=current_manifest,
        identity=expected_identity,
        baseline_digest=baseline.digest,
        workspace_logical_identity=workspace_logical_identity,
        approval_intent_digest=intent.digest,
        entry=entry,
    )
    if manifest is None:
        return _denied(
            reason=_BINDING_MISMATCH,
            approval_result=_original_approval_result(
                current_record,
                expected_revision=expected_revision,
                reason=_BINDING_MISMATCH,
            ),
            workspace=workspace,
            workspace_logical_identity=workspace_logical_identity,
        )
    publish = _publish_copy(
        workspace=workspace,
        source_root_status=source_root_status,
        path=path,
        content=content,
        mode=mode,
    )
    if publish.receipt is None:
        operation_reason = (
            _MATERIALIZATION_FAILED
            if publish.reason == _CLEANUP_FAILED
            else publish.reason
        )
        return _denied(
            reason=publish.reason or _MATERIALIZATION_FAILED,
            approval_result=_original_approval_result(
                current_record,
                expected_revision=expected_revision,
                reason=publish.reason or _MATERIALIZATION_FAILED,
            ),
            workspace=workspace,
            cleanup_complete=publish.cleanup_complete,
            cleanup_reason=publish.cleanup_reason,
            operation_reason=operation_reason,
            workspace_logical_identity=workspace_logical_identity,
        )
    return IgnoredInputMaterializationResult(
        permitted=True,
        side_effect_permitted=True,
        reason=_MATERIALIZED,
        approval_result=approval_result,
        manifest=manifest,
        workspace=workspace,
        state=IgnoredInputPublicationState.PUBLISHED_PENDING_COMMIT,
        candidate_manifest=manifest,
        approval_cas_intent=intent,
        publication_receipt=publish.receipt,
        expected_manifest_identity=expected_identity,
        workspace_logical_identity=workspace_logical_identity,
    )


__all__ = [
    "ApprovalCASIntent",
    "IgnoredInputMaterializationResult",
    "IgnoredInputMode",
    "IgnoredInputPublicationState",
    "PublicationReceipt",
    "SandboxInputEntry",
    "SandboxInputManifest",
    "materialize_ignored_input",
]
