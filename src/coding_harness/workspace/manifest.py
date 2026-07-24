"""Immutable task-start baseline snapshots for WP-10."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import os
from pathlib import Path
import selectors
import stat
import subprocess
import time

from coding_harness.workspace.file_model import (
    InspectionStatus,
    SupportedEntry,
    SupportedEntryKind,
    TrackingState,
    inspect_supported_entry,
)
from coding_harness.workspace.paths import RepoPath


_GIT_TIMEOUT_SECONDS = 5.0
_GIT_CLEANUP_TIMEOUT_SECONDS = 0.5
_MAX_GIT_OUTPUT_BYTES = 64 * 1024 * 1024
_MAX_GIT_TEXT_BYTES = 4096
_INVALID_BASELINE = "baseline construction failed"


def _is_digest(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_git_object_id(value: object) -> bool:
    return (
        type(value) is str
        and len(value) in {40, 64}
        and all(character in "0123456789abcdef" for character in value)
    )


def _update_field(digest: object, value: str | bytes) -> None:
    encoded = value if type(value) is bytes else value.encode("utf-8")
    digest.update(len(encoded).to_bytes(8, "big"))
    digest.update(encoded)


class BaselineEntryState(Enum):
    TRACKED_CLEAN = "TRACKED_CLEAN"
    TRACKED_STAGED = "TRACKED_STAGED"
    TRACKED_UNSTAGED = "TRACKED_UNSTAGED"
    TRACKED_MIXED = "TRACKED_MIXED"
    UNTRACKED = "UNTRACKED"

    def __bool__(self) -> bool:
        raise TypeError("BaselineEntryState has no truth value")


@dataclass(frozen=True, slots=True)
class BaselineEntry:
    """One immutable entry captured from the task-start filesystem state."""

    path: RepoPath
    content: bytes
    content_digest: str
    metadata_digest: str
    file_identity: str
    kind: SupportedEntryKind
    tracking: TrackingState
    state: BaselineEntryState
    executable: bool
    size: int
    count_contribution: int
    byte_contribution: int
    symlink_target: str | None
    symlink_chain: tuple[str, ...]

    def __post_init__(self) -> None:
        valid = (
            type(self.path) is RepoPath
            and type(self.content) is bytes
            and _is_digest(self.content_digest)
            and self.content_digest == hashlib.sha256(self.content).hexdigest()
            and _is_digest(self.metadata_digest)
            and _is_digest(self.file_identity)
            and type(self.kind) is SupportedEntryKind
            and type(self.tracking) is TrackingState
            and type(self.state) is BaselineEntryState
            and type(self.executable) is bool
            and type(self.size) is int
            and self.size >= 0
            and type(self.count_contribution) is int
            and self.count_contribution == 1
            and type(self.byte_contribution) is int
            and self.byte_contribution == self.size
            and type(self.symlink_chain) is tuple
            and all(type(item) is str for item in self.symlink_chain)
        )
        if not valid:
            raise ValueError("baseline entry is invalid")
        if (
            self.tracking is TrackingState.UNTRACKED
            and self.state is not BaselineEntryState.UNTRACKED
        ) or (
            self.tracking is TrackingState.TRACKED
            and self.state is BaselineEntryState.UNTRACKED
        ):
            raise ValueError("baseline entry is invalid")
        if self.kind is SupportedEntryKind.REGULAR_FILE:
            if (
                self.symlink_target is not None
                or self.symlink_chain
                or self.size != len(self.content)
            ):
                raise ValueError("baseline entry is invalid")
        elif (
            type(self.symlink_target) is not str
            or not self.symlink_target
            or len(self.symlink_chain) < 2
        ):
            raise ValueError("baseline entry is invalid")

    def __bool__(self) -> bool:
        raise TypeError("BaselineEntry has no truth value")


def _calculate_manifest_digest(
    entries: tuple[BaselineEntry, ...],
    source_head: str,
    source_branch: str,
    source_index_digest: str,
    source_status_digest: str,
) -> str:
    digest = hashlib.sha256(b"coding-harness:baseline-manifest:v1")
    _update_field(digest, source_head)
    _update_field(digest, source_branch)
    _update_field(digest, source_index_digest)
    _update_field(digest, source_status_digest)
    _update_field(digest, str(len(entries)))
    for entry in entries:
        for value in (
            entry.path.identity,
            entry.path.canonical,
            entry.file_identity,
            entry.content_digest,
            entry.metadata_digest,
            entry.kind.value,
            entry.tracking.value,
            entry.state.value,
            "executable" if entry.executable else "non-executable",
            str(entry.size),
            entry.symlink_target or "",
            *entry.symlink_chain,
        ):
            _update_field(digest, value)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class BaselineManifest:
    """A deterministic immutable snapshot of the user's task-start state."""

    entries: tuple[BaselineEntry, ...]
    digest: str
    source_head: str
    source_branch: str
    source_index_digest: str
    source_status_digest: str

    def __post_init__(self) -> None:
        if (
            type(self.entries) is not tuple
            or any(type(entry) is not BaselineEntry for entry in self.entries)
            or tuple(sorted(self.entries, key=lambda item: item.path.canonical))
            != self.entries
            or len({entry.path.identity for entry in self.entries})
            != len(self.entries)
            or not _is_git_object_id(self.source_head)
            or type(self.source_branch) is not str
            or not _is_digest(self.source_index_digest)
            or not _is_digest(self.source_status_digest)
            or not _is_digest(self.digest)
            or self.digest
            != _calculate_manifest_digest(
                self.entries,
                self.source_head,
                self.source_branch,
                self.source_index_digest,
                self.source_status_digest,
            )
        ):
            raise ValueError("baseline manifest is invalid")

    def __bool__(self) -> bool:
        raise TypeError("BaselineManifest has no truth value")


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


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    try:
        if process.poll() is not None:
            process.wait(timeout=_GIT_CLEANUP_TIMEOUT_SECONDS)
            return
        process.terminate()
        try:
            process.wait(timeout=_GIT_CLEANUP_TIMEOUT_SECONDS)
            return
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=_GIT_CLEANUP_TIMEOUT_SECONDS)
    except (OSError, subprocess.SubprocessError):
        try:
            process.kill()
            process.wait(timeout=_GIT_CLEANUP_TIMEOUT_SECONDS)
        except (OSError, subprocess.SubprocessError):
            return


def _run_git(
    root: Path,
    *arguments: str,
    max_output_bytes: int | None = None,
) -> bytes:
    limit = _MAX_GIT_OUTPUT_BYTES if max_output_bytes is None else max_output_bytes
    if type(limit) is not int or limit < 0:
        raise ValueError(_INVALID_BASELINE)
    try:
        process = subprocess.Popen(
            ["git", "-c", "safe.directory=*", *arguments],
            cwd=root,
            env=_git_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
            bufsize=0,
        )
    except OSError:
        raise ValueError(_INVALID_BASELINE) from None
    assert process.stdout is not None
    selector = selectors.DefaultSelector()
    output = bytearray()
    deadline = time.monotonic() + _GIT_TIMEOUT_SECONDS
    completed = False
    try:
        selector.register(process.stdout, selectors.EVENT_READ)
        while selector.get_map():
            remaining_time = deadline - time.monotonic()
            if remaining_time <= 0:
                raise ValueError(_INVALID_BASELINE)
            events = selector.select(timeout=min(0.1, remaining_time))
            if not events:
                continue
            for key, _ in events:
                remaining = limit + 1 - len(output)
                if remaining <= 0:
                    raise ValueError(_INVALID_BASELINE)
                try:
                    chunk = os.read(key.fd, min(64 * 1024, remaining))
                except OSError:
                    raise ValueError(_INVALID_BASELINE) from None
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                output.extend(chunk)
                if len(output) > limit:
                    raise ValueError(_INVALID_BASELINE)
        remaining_time = deadline - time.monotonic()
        if remaining_time <= 0:
            raise ValueError(_INVALID_BASELINE)
        try:
            returncode = process.wait(timeout=remaining_time)
        except subprocess.SubprocessError:
            raise ValueError(_INVALID_BASELINE) from None
        completed = True
        if returncode != 0:
            raise ValueError(_INVALID_BASELINE)
        return bytes(output)
    finally:
        try:
            selector.close()
        finally:
            try:
                process.stdout.close()
            finally:
                if not completed:
                    _stop_process(process)


def _git_text(root: Path, *arguments: str) -> str:
    try:
        return _run_git(
            root,
            *arguments,
            max_output_bytes=_MAX_GIT_TEXT_BYTES,
        ).decode("utf-8", errors="strict").strip()
    except UnicodeError:
        raise ValueError(_INVALID_BASELINE) from None


def _parse_paths(output: bytes) -> tuple[RepoPath, ...]:
    raw_names = output.split(b"\0")
    if raw_names and raw_names[-1] == b"":
        raw_names.pop()
    try:
        parsed = tuple(
            RepoPath.parse(name.decode("utf-8", errors="strict"))
            for name in raw_names
        )
    except (UnicodeError, ValueError):
        raise ValueError(_INVALID_BASELINE) from None
    if len({item.identity for item in parsed}) != len(parsed):
        raise ValueError(_INVALID_BASELINE)
    return tuple(sorted(parsed, key=lambda item: item.canonical))


@dataclass(frozen=True, slots=True)
class _GitState:
    source_head: str
    source_branch: str
    candidates: tuple[RepoPath, ...]
    index_state: bytes
    status_state: bytes
    staged_paths: frozenset[str]
    unstaged_paths: frozenset[str]


def _capture_git_state(root: Path) -> _GitState:
    candidates = _parse_paths(
        _run_git(
            root,
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
        )
    )
    index_state = _run_git(root, "ls-files", "--stage", "-z")
    status_state = _run_git(
        root,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    staged = _parse_paths(
        _run_git(root, "diff", "--cached", "--name-only", "-z", "--")
    )
    unstaged = _parse_paths(
        _run_git(root, "diff", "--name-only", "-z", "--")
    )
    return _GitState(
        source_head=_git_text(root, "rev-parse", "--verify", "HEAD"),
        source_branch=_git_text(root, "branch", "--show-current"),
        candidates=candidates,
        index_state=index_state,
        status_state=status_state,
        staged_paths=frozenset(item.identity for item in staged),
        unstaged_paths=frozenset(item.identity for item in unstaged),
    )


def _entry_state(path: RepoPath, tracking: TrackingState, state: _GitState) -> BaselineEntryState:
    if tracking is TrackingState.UNTRACKED:
        return BaselineEntryState.UNTRACKED
    staged = path.identity in state.staged_paths
    unstaged = path.identity in state.unstaged_paths
    if staged and unstaged:
        return BaselineEntryState.TRACKED_MIXED
    if staged:
        return BaselineEntryState.TRACKED_STAGED
    if unstaged:
        return BaselineEntryState.TRACKED_UNSTAGED
    return BaselineEntryState.TRACKED_CLEAN


def _read_regular(root: Path, supported: SupportedEntry) -> bytes:
    candidate = root.joinpath(*supported.path.segments)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(candidate, flags)
        try:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode):
                raise ValueError(_INVALID_BASELINE)
            remaining = supported.size + 1
            chunks: list[bytes] = []
            while remaining:
                chunk = os.read(descriptor, min(64 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
        finally:
            os.close(descriptor)
    except OSError:
        raise ValueError(_INVALID_BASELINE) from None
    content = b"".join(chunks)
    if (
        len(content) != supported.size
        or hashlib.sha256(content).hexdigest() != supported.content_digest
    ):
        raise ValueError(_INVALID_BASELINE)
    return content


def _read_symlink(root: Path, supported: SupportedEntry) -> bytes:
    candidate = root.joinpath(*supported.path.segments)
    try:
        target = os.readlink(candidate)
        encoded = target.encode("utf-8", errors="strict")
    except (OSError, UnicodeError):
        raise ValueError(_INVALID_BASELINE) from None
    if target != supported.symlink_target:
        raise ValueError(_INVALID_BASELINE)
    return encoded


def _capture_entry(
    root: Path,
    path: RepoPath,
    git_state: _GitState,
) -> BaselineEntry:
    inspected = inspect_supported_entry(root, path)
    if (
        inspected.status is not InspectionStatus.SUPPORTED
        or type(inspected.entry) is not SupportedEntry
    ):
        raise ValueError(_INVALID_BASELINE)
    supported = inspected.entry
    content = (
        _read_regular(root, supported)
        if supported.kind is SupportedEntryKind.REGULAR_FILE
        else _read_symlink(root, supported)
    )
    repeated = inspect_supported_entry(root, path)
    if (
        repeated.status is not InspectionStatus.SUPPORTED
        or repeated.entry != supported
    ):
        raise ValueError(_INVALID_BASELINE)
    return BaselineEntry(
        path=supported.path,
        content=content,
        content_digest=hashlib.sha256(content).hexdigest(),
        metadata_digest=supported.metadata_digest,
        file_identity=supported.file_identity,
        kind=supported.kind,
        tracking=supported.tracking,
        state=_entry_state(path, supported.tracking, git_state),
        executable=supported.executable,
        size=len(content),
        count_contribution=supported.count_contribution,
        byte_contribution=len(content),
        symlink_target=supported.symlink_target,
        symlink_chain=supported.symlink_chain,
    )


def build_baseline(root: Path) -> BaselineManifest:
    """Capture the current supported Git worktree state without modifying it."""

    if not isinstance(root, Path):
        raise ValueError(_INVALID_BASELINE)
    try:
        root_status = os.lstat(root)
        if stat.S_ISLNK(root_status.st_mode) or not stat.S_ISDIR(root_status.st_mode):
            raise ValueError(_INVALID_BASELINE)
        trusted_root = root.resolve(strict=True)
    except (OSError, RuntimeError):
        raise ValueError(_INVALID_BASELINE) from None

    initial_state = _capture_git_state(trusted_root)
    entries = tuple(
        _capture_entry(trusted_root, path, initial_state)
        for path in initial_state.candidates
        if os.path.lexists(trusted_root.joinpath(*path.segments))
    )
    repeated_entries = tuple(
        _capture_entry(trusted_root, entry.path, initial_state)
        for entry in entries
    )
    final_state = _capture_git_state(trusted_root)
    if initial_state != final_state or entries != repeated_entries:
        raise ValueError(_INVALID_BASELINE)
    source_index_digest = hashlib.sha256(initial_state.index_state).hexdigest()
    source_status_digest = hashlib.sha256(initial_state.status_state).hexdigest()
    digest = _calculate_manifest_digest(
        entries,
        initial_state.source_head,
        initial_state.source_branch,
        source_index_digest,
        source_status_digest,
    )
    return BaselineManifest(
        entries=entries,
        digest=digest,
        source_head=initial_state.source_head,
        source_branch=initial_state.source_branch,
        source_index_digest=source_index_digest,
        source_status_digest=source_status_digest,
    )
