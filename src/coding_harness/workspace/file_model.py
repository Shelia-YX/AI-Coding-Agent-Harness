"""Read-only supported-entry inspection for WP-09.

Returned objects are point-in-time snapshots.  They do not authorize later
use, and callers must revalidate at the use boundary.
"""

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
from typing import Callable, Iterable

from coding_harness.workspace.paths import RepoPath


_MAX_CONTENT_BYTES = 8 * 1024 * 1024
_MAX_METADATA_BYTES = 64 * 1024
_MAX_GIT_MARKER_BYTES = 4096
_MAX_GIT_OUTPUT_BYTES = 64 * 1024
_GIT_TIMEOUT_SECONDS = 2.0
_MAX_REPOSITORY_SCAN_ENTRIES = 10_000
_MAX_ALLOWED_PATHS = 10_000
_MAX_SYMLINK_DEPTH = 40
_PROCESS_WAIT_SECONDS = 0.5
_PATH_POLICY_VIOLATION = "PATH_POLICY_VIOLATION"

# Private, immutable-by-convention seams allow controlled system-type tests
# without granting production callers authority through the public API.
_LSTAT: Callable[[Path], os.stat_result] = os.lstat
_READLINK: Callable[[Path], str] = os.readlink
_PIPE_READ: Callable[[int, int], bytes] = os.read
_GIT_EXECUTABLE = "git"


class _InspectionFailure(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__("inspection failed")
        self.detail = detail


class _ClosedEnum(Enum):
    def __bool__(self) -> bool:
        raise TypeError(f"{type(self).__name__} has no truth value")


class InspectionStatus(_ClosedEnum):
    SUPPORTED = "SUPPORTED"
    REJECTED = "REJECTED"


class SupportedEntryKind(_ClosedEnum):
    REGULAR_FILE = "REGULAR_FILE"
    SYMLINK = "SYMLINK"


class TrackingState(_ClosedEnum):
    TRACKED = "TRACKED"
    UNTRACKED = "UNTRACKED"


class InspectionReason(_ClosedEnum):
    PATH_POLICY_VIOLATION = _PATH_POLICY_VIOLATION


@dataclass(frozen=True, slots=True)
class SupportedEntry:
    path: RepoPath
    file_identity: str
    content_digest: str
    metadata_digest: str
    baseline_digest: str | None
    kind: SupportedEntryKind
    tracking: TrackingState
    executable: bool
    size: int
    count_contribution: int
    byte_contribution: int
    symlink_target: str | None
    symlink_chain: tuple[str, ...]
    lexical_safe: bool = True
    physical_safe: bool = True
    requires_use_time_revalidation: bool = True

    def __post_init__(self) -> None:
        if type(self.path) is not RepoPath:
            raise ValueError("supported entry is invalid")
        if not _is_digest(self.file_identity) or not _is_digest(self.content_digest):
            raise ValueError("supported entry is invalid")
        if not _is_digest(self.metadata_digest):
            raise ValueError("supported entry is invalid")
        if self.baseline_digest is not None and not _is_digest(self.baseline_digest):
            raise ValueError("supported entry is invalid")
        if type(self.kind) is not SupportedEntryKind:
            raise ValueError("supported entry is invalid")
        if type(self.tracking) is not TrackingState:
            raise ValueError("supported entry is invalid")
        if (
            type(self.executable) is not bool
            or type(self.size) is not int
            or self.size < 0
            or type(self.count_contribution) is not int
            or self.count_contribution != 1
            or type(self.byte_contribution) is not int
            or self.byte_contribution != self.size
            or type(self.symlink_chain) is not tuple
            or any(type(item) is not str for item in self.symlink_chain)
            or type(self.lexical_safe) is not bool
            or type(self.physical_safe) is not bool
            or type(self.requires_use_time_revalidation) is not bool
            or not self.lexical_safe
            or not self.physical_safe
            or not self.requires_use_time_revalidation
        ):
            raise ValueError("supported entry is invalid")
        if self.kind is SupportedEntryKind.SYMLINK:
            if (
                type(self.symlink_target) is not str
                or not self.symlink_target
                or len(self.symlink_chain) < 2
                or self.executable
            ):
                raise ValueError("supported entry is invalid")
        elif self.symlink_target is not None or self.symlink_chain:
            raise ValueError("supported entry is invalid")

    def __bool__(self) -> bool:
        raise TypeError("SupportedEntry has no truth value")


@dataclass(frozen=True, slots=True)
class InspectionResult:
    status: InspectionStatus
    reason_code: InspectionReason | None
    detail: str
    entry: SupportedEntry | None
    inspected_path_identity: str | None
    lexical_safe: bool
    physical_safe: bool
    count_contribution: int
    byte_contribution: int
    requires_use_time_revalidation: bool = True

    def __post_init__(self) -> None:
        if type(self.status) is not InspectionStatus:
            raise ValueError("inspection result is invalid")
        if type(self.detail) is not str or len(self.detail.encode("utf-8")) > 256:
            raise ValueError("inspection result is invalid")
        if (
            type(self.lexical_safe) is not bool
            or type(self.physical_safe) is not bool
            or type(self.count_contribution) is not int
            or type(self.byte_contribution) is not int
            or self.count_contribution < 0
            or self.byte_contribution < 0
            or type(self.requires_use_time_revalidation) is not bool
            or not self.requires_use_time_revalidation
        ):
            raise ValueError("inspection result is invalid")
        if self.status is InspectionStatus.SUPPORTED:
            if (
                self.reason_code is not None
                or type(self.entry) is not SupportedEntry
                or self.count_contribution != self.entry.count_contribution
                or self.byte_contribution != self.entry.byte_contribution
            ):
                raise ValueError("inspection result is invalid")
        elif (
            self.reason_code is not InspectionReason.PATH_POLICY_VIOLATION
            or self.entry is not None
            or self.count_contribution != 0
            or self.byte_contribution != 0
        ):
            raise ValueError("inspection result is invalid")

    def __bool__(self) -> bool:
        raise TypeError("InspectionResult has no truth value")


@dataclass(frozen=True, slots=True)
class _GitResult:
    returncode: int
    output: bytes
    error: bytes
    valid: bool
    failure_reason: str | None
    cleanup_failure_reason: str | None
    max_output_bytes_retained: int
    max_error_bytes_retained: int
    reaped: bool


@dataclass(frozen=True, slots=True)
class _ProcessCleanup:
    reaped: bool
    returncode: int | None
    failure_reason: str | None


@dataclass(frozen=True, slots=True)
class _GitDirs:
    worktree: Path
    common: Path


@dataclass(frozen=True, slots=True)
class _ResolvedPath:
    content_path: Path
    entry_stat: os.stat_result
    content_stat: os.stat_result
    kind: SupportedEntryKind
    symlink_target: str | None
    symlink_chain: tuple[str, ...]


def _is_digest(value: object) -> bool:
    if type(value) is not str or len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value)


def _digest(label: bytes, *values: str) -> str:
    digest = hashlib.sha256()
    digest.update(label)
    for value in values:
        digest.update(b"\0")
        digest.update(value.encode("utf-8"))
    return digest.hexdigest()


def _rejected(
    detail: str,
    path: RepoPath | None = None,
    *,
    lexical_safe: bool = False,
    physical_safe: bool = False,
) -> InspectionResult:
    return InspectionResult(
        status=InspectionStatus.REJECTED,
        reason_code=InspectionReason.PATH_POLICY_VIOLATION,
        detail=detail[:128],
        entry=None,
        inspected_path_identity=path.identity if type(path) is RepoPath else None,
        lexical_safe=lexical_safe,
        physical_safe=physical_safe,
        count_contribution=0,
        byte_contribution=0,
    )


def _read_bounded_regular(path: Path, limit: int) -> bytes | None:
    if type(limit) is not int or limit < 0:
        return None
    try:
        before = _LSTAT(path)
    except OSError:
        return None
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
        return None
    flags = os.O_RDONLY
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return None
    try:
        current = os.fstat(descriptor)
        if (
            not stat.S_ISREG(current.st_mode)
            or current.st_dev != before.st_dev
            or current.st_ino != before.st_ino
            or current.st_size > limit
        ):
            return None
        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(descriptor, min(8192, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        content = b"".join(chunks)
        return content if len(content) <= limit else None
    except OSError:
        return None
    finally:
        os.close(descriptor)


def _read_bounded_metadata(path: Path, limit: int) -> bytes | None:
    """Read a regular metadata file without following symlinks."""

    return _read_bounded_regular(path, limit)


def _decode_metadata_text(content: bytes) -> str:
    try:
        return content.decode("utf-8", errors="strict")
    except UnicodeError:
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE") from None


def _read_required_text(path: Path, limit: int) -> str:
    content = _read_bounded_metadata(path, limit)
    if content is None:
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE")
    return _decode_metadata_text(content)


def _read_optional_metadata(path: Path, limit: int) -> bytes | None:
    try:
        _LSTAT(path)
    except FileNotFoundError:
        return b""
    except OSError:
        return None
    return _read_bounded_metadata(path, limit)


def _read_optional_text(path: Path, limit: int) -> str:
    content = _read_optional_metadata(path, limit)
    if content is None:
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE")
    return _decode_metadata_text(content)


def _close_streams(streams: Iterable[object]) -> str | None:
    close_failed = False
    for stream in streams:
        if getattr(stream, "closed", False):
            continue
        try:
            stream.close()
        except OSError:
            close_failed = True
    return "GIT_STREAM_CLOSE_FAILURE" if close_failed else None


def _finalize_process(process: object) -> _ProcessCleanup:
    """Terminate, escalate if needed, and deterministically attempt to reap."""

    cleanup_error = False
    kill_error = False
    try:
        returncode = process.poll()
    except (OSError, subprocess.SubprocessError):
        cleanup_error = True
        returncode = None

    if returncode is not None:
        try:
            returncode = process.wait(timeout=_PROCESS_WAIT_SECONDS)
        except (OSError, subprocess.SubprocessError):
            return _ProcessCleanup(False, None, "GIT_REAP_FAILURE")
        return _ProcessCleanup(
            True,
            returncode,
            "GIT_CLEANUP_ERROR" if cleanup_error else None,
        )

    try:
        process.terminate()
    except (OSError, subprocess.SubprocessError):
        cleanup_error = True
        try:
            process.kill()
        except (OSError, subprocess.SubprocessError):
            kill_error = True
    else:
        try:
            returncode = process.wait(timeout=_PROCESS_WAIT_SECONDS)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except (OSError, subprocess.SubprocessError):
                kill_error = True
        except (OSError, subprocess.SubprocessError):
            cleanup_error = True
            try:
                process.kill()
            except (OSError, subprocess.SubprocessError):
                kill_error = True
        else:
            return _ProcessCleanup(
                True,
                returncode,
                "GIT_CLEANUP_ERROR" if cleanup_error else None,
            )

    try:
        returncode = process.wait(timeout=_PROCESS_WAIT_SECONDS)
    except (OSError, subprocess.SubprocessError):
        return _ProcessCleanup(False, None, "GIT_REAP_FAILURE")
    return _ProcessCleanup(
        True,
        returncode,
        (
            "GIT_KILL_FAILURE"
            if kill_error
            else "GIT_CLEANUP_ERROR" if cleanup_error else None
        ),
    )


def _run_git_read_only(root: Path, arguments: tuple[str, ...]) -> _GitResult:
    command = (_GIT_EXECUTABLE, "-c", "safe.directory=*", *arguments)
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
    try:
        process = subprocess.Popen(
            command,
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            bufsize=0,
        )
    except OSError:
        return _GitResult(
            returncode=-1,
            output=b"",
            error=b"",
            valid=False,
            failure_reason="GIT_STARTUP_ERROR",
            cleanup_failure_reason=None,
            max_output_bytes_retained=0,
            max_error_bytes_retained=0,
            reaped=True,
        )
    assert process.stdout is not None
    assert process.stderr is not None

    output = bytearray()
    error = bytearray()
    stream_buffers = {
        process.stdout.fileno(): output,
        process.stderr.fileno(): error,
    }
    selector = None
    try:
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        selector.register(process.stderr, selectors.EVENT_READ)
    except (OSError, ValueError):
        cleanup = _finalize_process(process)
        selector_close_failure = None
        if selector is not None:
            try:
                selector.close()
            except OSError:
                selector_close_failure = "GIT_SELECTOR_CLOSE_FAILURE"
        close_failure = _close_streams((process.stdout, process.stderr))
        return _GitResult(
            returncode=cleanup.returncode if cleanup.returncode is not None else -1,
            output=b"",
            error=b"",
            valid=False,
            failure_reason="GIT_SELECTOR_ERROR",
            cleanup_failure_reason=(
                cleanup.failure_reason
                or selector_close_failure
                or close_failure
            ),
            max_output_bytes_retained=0,
            max_error_bytes_retained=0,
            reaped=cleanup.reaped,
        )
    assert selector is not None
    deadline = time.monotonic() + _GIT_TIMEOUT_SECONDS
    failure_reason: str | None = None
    cleanup = _ProcessCleanup(False, None, None)
    try:
        while selector.get_map():
            remaining_time = deadline - time.monotonic()
            if remaining_time <= 0:
                failure_reason = "GIT_TIMEOUT"
                break
            try:
                events = selector.select(remaining_time)
            except (OSError, ValueError):
                failure_reason = "GIT_SELECTOR_ERROR"
                break
            if not events:
                failure_reason = "GIT_TIMEOUT"
                break
            for key, _ in events:
                descriptor = key.fileobj.fileno()
                destination = stream_buffers[descriptor]
                remaining_capacity = (
                    _MAX_GIT_OUTPUT_BYTES + 1 - len(destination)
                )
                if remaining_capacity <= 0:
                    failure_reason = "GIT_OUTPUT_LIMIT"
                    break
                try:
                    chunk = _PIPE_READ(
                        descriptor,
                        min(8192, remaining_capacity),
                    )
                except OSError:
                    failure_reason = "GIT_READ_ERROR"
                    break
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                destination.extend(chunk)
                if len(destination) > _MAX_GIT_OUTPUT_BYTES:
                    failure_reason = "GIT_OUTPUT_LIMIT"
                    break
            if failure_reason is not None:
                break
        if failure_reason is None:
            remaining_time = deadline - time.monotonic()
            if remaining_time <= 0:
                failure_reason = "GIT_TIMEOUT"
            else:
                try:
                    returncode = process.wait(timeout=remaining_time)
                except subprocess.TimeoutExpired:
                    failure_reason = "GIT_TIMEOUT"
                except (OSError, subprocess.SubprocessError):
                    failure_reason = "GIT_PROCESS_ERROR"
                else:
                    cleanup = _ProcessCleanup(True, returncode, None)
    finally:
        selector_close_failure = None
        try:
            selector.close()
        except OSError:
            selector_close_failure = "GIT_SELECTOR_CLOSE_FAILURE"
        if failure_reason is not None:
            cleanup = _finalize_process(process)
        close_failure = _close_streams((process.stdout, process.stderr))

    cleanup_failure_reason = (
        cleanup.failure_reason or selector_close_failure or close_failure
    )
    if failure_reason is not None or cleanup_failure_reason is not None:
        return _GitResult(
            returncode=cleanup.returncode if cleanup.returncode is not None else -1,
            output=b"",
            error=b"",
            valid=False,
            failure_reason=failure_reason or "GIT_CLEANUP_ERROR",
            cleanup_failure_reason=cleanup_failure_reason,
            max_output_bytes_retained=len(output),
            max_error_bytes_retained=len(error),
            reaped=cleanup.reaped,
        )
    return _GitResult(
        returncode=cleanup.returncode if cleanup.returncode is not None else -1,
        output=bytes(output),
        error=bytes(error),
        valid=True,
        failure_reason=None,
        cleanup_failure_reason=None,
        max_output_bytes_retained=len(output),
        max_error_bytes_retained=len(error),
        reaped=True,
    )


def _git_dirs(root: Path) -> _GitDirs | None:
    marker = root / ".git"
    try:
        marker_stat = _LSTAT(marker)
    except FileNotFoundError:
        return None
    except OSError:
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE") from None

    if stat.S_ISDIR(marker_stat.st_mode):
        return _GitDirs(worktree=marker, common=marker)
    if not stat.S_ISREG(marker_stat.st_mode):
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE")

    marker_text = _read_required_text(marker, _MAX_GIT_MARKER_BYTES)
    marker_lines = marker_text.splitlines()
    if len(marker_lines) != 1 or not marker_lines[0].startswith("gitdir: "):
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE")
    raw_git_dir = marker_lines[0][8:].strip()
    if not raw_git_dir or "\x00" in raw_git_dir or "\\" in raw_git_dir:
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE")
    worktree_git_dir = Path(raw_git_dir)
    if not worktree_git_dir.is_absolute():
        worktree_git_dir = marker.parent / worktree_git_dir
    try:
        worktree_git_dir = worktree_git_dir.resolve(strict=True)
    except (OSError, RuntimeError):
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE") from None
    if not worktree_git_dir.is_dir():
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE")

    common_text = _read_required_text(
        worktree_git_dir / "commondir",
        _MAX_GIT_MARKER_BYTES,
    ).strip()
    if (
        not common_text
        or "\x00" in common_text
        or "\\" in common_text
        or Path(common_text).is_absolute()
    ):
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE")
    try:
        common_git_dir = (worktree_git_dir / common_text).resolve(strict=True)
    except (OSError, RuntimeError):
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE") from None
    if (
        not common_git_dir.is_dir()
        or worktree_git_dir.parent != common_git_dir / "worktrees"
    ):
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE")
    return _GitDirs(worktree=worktree_git_dir, common=common_git_dir)


def _metadata_exists(path: Path) -> bool:
    try:
        _LSTAT(path)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE") from None


def _scan_repository_tree(root: Path) -> bool:
    pending = [root]
    inspected = 0
    uses_lfs = False
    while pending:
        current = pending.pop()
        try:
            iterator = os.scandir(current)
        except OSError:
            raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE") from None
        with iterator:
            for entry in iterator:
                inspected += 1
                if inspected > _MAX_REPOSITORY_SCAN_ENTRIES:
                    raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE")
                if current == root and entry.name == ".git":
                    continue
                try:
                    entry_stat = entry.stat(follow_symlinks=False)
                except OSError:
                    raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE") from None
                if entry.name == ".git":
                    raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE")
                entry_path = Path(entry.path)
                if stat.S_ISDIR(entry_stat.st_mode):
                    pending.append(entry_path)
                if entry.name == ".gitattributes":
                    attributes = _read_required_text(
                        entry_path,
                        _MAX_METADATA_BYTES,
                    )
                    if "filter=lfs" in attributes:
                        uses_lfs = True
    return uses_lfs


def _config_uses_sparse(path: Path, *, required: bool) -> bool:
    if required:
        content = _read_bounded_metadata(path, _MAX_METADATA_BYTES)
        if content is None:
            raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE")
    else:
        content = _read_optional_metadata(path, _MAX_METADATA_BYTES)
        if content is None:
            raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE")
        if not content:
            return False
    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeError:
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE") from None
    compact = "".join(text.lower().split())
    return "sparsecheckout=true" in compact


def _unsupported_repository_state(root: Path, git_dirs: _GitDirs | None) -> bool:
    tree_uses_lfs = _scan_repository_tree(root)
    if git_dirs is None:
        return tree_uses_lfs

    marker_names = (
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "BISECT_LOG",
        "rebase-merge",
        "rebase-apply",
    )
    for git_dir in {git_dirs.worktree, git_dirs.common}:
        if any(_metadata_exists(git_dir / name) for name in marker_names):
            return True
        if _metadata_exists(git_dir / "info" / "sparse-checkout"):
            return True

    if _config_uses_sparse(git_dirs.common / "config", required=True):
        return True
    if _config_uses_sparse(git_dirs.worktree / "config.worktree", required=False):
        return True

    info_attributes = _read_optional_text(
        git_dirs.common / "info" / "attributes",
        _MAX_METADATA_BYTES,
    )
    if tree_uses_lfs or "filter=lfs" in info_attributes:
        return True

    index = _run_git_read_only(root, ("ls-files", "--stage"))
    if not index.valid or index.returncode != 0:
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE")
    return any(line.startswith(b"160000 ") for line in index.output.splitlines())


def _tracking_state(
    root: Path,
    path: RepoPath,
    git_dirs: _GitDirs | None,
) -> TrackingState | None:
    if git_dirs is None:
        return TrackingState.UNTRACKED
    tracked = _run_git_read_only(
        root,
        ("ls-files", "--error-unmatch", "--", path.canonical),
    )
    if not tracked.valid or tracked.returncode not in {0, 1}:
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE")
    if tracked.returncode == 0:
        return TrackingState.TRACKED
    ignored = _run_git_read_only(
        root,
        ("check-ignore", "-q", "--", path.canonical),
    )
    if not ignored.valid or ignored.returncode not in {0, 1}:
        raise _InspectionFailure("UNSUPPORTED_REPOSITORY_STATE")
    return None if ignored.returncode == 0 else TrackingState.UNTRACKED


def _relative_to_root(root: Path, candidate: Path) -> str | None:
    try:
        return candidate.relative_to(root).as_posix()
    except ValueError:
        return None


def _resolve_supported_path(root: Path, path: RepoPath) -> _ResolvedPath:
    candidate = root.joinpath(*path.segments)
    current = root
    for segment in path.segments[:-1]:
        current /= segment
        try:
            mode = _LSTAT(current).st_mode
        except OSError:
            raise _InspectionFailure("UNSAFE_PHYSICAL_PATH") from None
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise _InspectionFailure("UNSAFE_PHYSICAL_PATH")

    try:
        initial = _LSTAT(candidate)
    except OSError:
        raise _InspectionFailure("UNSAFE_PHYSICAL_PATH") from None
    if not stat.S_ISLNK(initial.st_mode):
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            raise _InspectionFailure("UNSAFE_PHYSICAL_PATH") from None
        if _relative_to_root(root, resolved) is None:
            raise _InspectionFailure("UNSAFE_PHYSICAL_PATH")
        return _ResolvedPath(
            content_path=resolved,
            entry_stat=initial,
            content_stat=initial,
            kind=SupportedEntryKind.REGULAR_FILE,
            symlink_target=None,
            symlink_chain=(),
        )

    visited: set[Path] = set()
    chain = [path.canonical]
    current = candidate
    first_target: str | None = None
    followed = 0
    while True:
        if current in visited:
            raise _InspectionFailure("UNSAFE_PHYSICAL_PATH")
        visited.add(current)
        try:
            current_stat = _LSTAT(current)
        except OSError:
            raise _InspectionFailure("UNSAFE_PHYSICAL_PATH") from None
        if not stat.S_ISLNK(current_stat.st_mode):
            if _relative_to_root(root, current) is None:
                raise _InspectionFailure("UNSAFE_PHYSICAL_PATH")
            return _ResolvedPath(
                content_path=current,
                entry_stat=initial,
                content_stat=current_stat,
                kind=SupportedEntryKind.SYMLINK,
                symlink_target=first_target,
                symlink_chain=tuple(chain),
            )
        if followed >= _MAX_SYMLINK_DEPTH:
            raise _InspectionFailure("UNSAFE_PHYSICAL_PATH")
        try:
            raw_target = _READLINK(current)
            target = RepoPath.parse(raw_target)
        except (OSError, ValueError, TypeError):
            raise _InspectionFailure("INVALID_SYMLINK_TARGET") from None
        if first_target is None:
            first_target = target.canonical
        next_path = current.parent.joinpath(*target.segments)
        relative = _relative_to_root(root, next_path)
        if relative is None:
            raise _InspectionFailure("UNSAFE_PHYSICAL_PATH")
        chain.append(relative)
        current = next_path
        followed += 1


def _copy_allowed_paths(
    allowed_paths: Iterable[RepoPath],
) -> tuple[RepoPath, ...] | None:
    copied: list[RepoPath] = []
    try:
        iterator = iter(allowed_paths)
        for item in iterator:
            if len(copied) >= _MAX_ALLOWED_PATHS or type(item) is not RepoPath:
                return None
            copied.append(item)
    except (TypeError, ValueError):
        return None
    return tuple(copied)


def inspect_supported_entry(
    root: Path,
    path: RepoPath,
    *,
    baseline_digest: str | None = None,
    max_bytes: int = _MAX_CONTENT_BYTES,
    allowed_paths: Iterable[RepoPath] | None = None,
) -> InspectionResult:
    """Inspect one entry without modifying the filesystem or repository."""

    if type(path) is not RepoPath:
        return _rejected("INVALID_LEXICAL_PATH")
    if not isinstance(root, Path):
        return _rejected("INVALID_ROOT", path, lexical_safe=True)
    if (
        type(max_bytes) is not int
        or max_bytes < 0
        or (baseline_digest is not None and not _is_digest(baseline_digest))
    ):
        return _rejected("INVALID_INSPECTION_INPUT", path, lexical_safe=True)
    if allowed_paths is not None:
        copied_allowed = _copy_allowed_paths(allowed_paths)
        if copied_allowed is None or not any(
            item.identity == path.identity for item in copied_allowed
        ):
            return _rejected("PATH_OUTSIDE_APPROVED_SCOPE", path, lexical_safe=True)

    try:
        root_stat = _LSTAT(root)
    except OSError:
        return _rejected("INVALID_ROOT", path, lexical_safe=True)
    if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
        return _rejected("INVALID_ROOT", path, lexical_safe=True)
    try:
        trusted_root = root.resolve(strict=True)
    except (OSError, RuntimeError):
        return _rejected("INVALID_ROOT", path, lexical_safe=True)

    try:
        git_dirs = _git_dirs(trusted_root)
        if _unsupported_repository_state(trusted_root, git_dirs):
            return _rejected(
                "UNSUPPORTED_REPOSITORY_STATE",
                path,
                lexical_safe=True,
            )
        resolved = _resolve_supported_path(trusted_root, path)
        if not stat.S_ISREG(resolved.content_stat.st_mode):
            return _rejected(
                "UNSUPPORTED_FILE_TYPE",
                path,
                lexical_safe=True,
            )
        content = _read_bounded_regular(resolved.content_path, max_bytes)
        if content is None:
            return _rejected(
                "CONTENT_LIMIT_OR_READ_FAILURE",
                path,
                lexical_safe=True,
                physical_safe=True,
            )
        tracking = _tracking_state(trusted_root, path, git_dirs)
        if tracking is None:
            return _rejected(
                "IGNORED_OR_UNINSPECTABLE_ENTRY",
                path,
                lexical_safe=True,
                physical_safe=True,
            )

        executable = (
            False
            if resolved.kind is SupportedEntryKind.SYMLINK
            else bool(resolved.entry_stat.st_mode & 0o111)
        )
        content_digest = hashlib.sha256(content).hexdigest()
        file_identity = _digest(
            b"coding-harness:file-identity:v1",
            path.identity,
            resolved.kind.value,
            resolved.symlink_target or "",
            *resolved.symlink_chain,
        )
        metadata_digest = _digest(
            b"coding-harness:file-metadata:v1",
            file_identity,
            str(resolved.entry_stat.st_mode),
            str(resolved.entry_stat.st_size),
            "executable" if executable else "non-executable",
        )
        entry = SupportedEntry(
            path=path,
            file_identity=file_identity,
            content_digest=content_digest,
            metadata_digest=metadata_digest,
            baseline_digest=baseline_digest,
            kind=resolved.kind,
            tracking=tracking,
            executable=executable,
            size=len(content),
            count_contribution=1,
            byte_contribution=len(content),
            symlink_target=resolved.symlink_target,
            symlink_chain=resolved.symlink_chain,
        )
        return InspectionResult(
            status=InspectionStatus.SUPPORTED,
            reason_code=None,
            detail="SUPPORTED_ENTRY",
            entry=entry,
            inspected_path_identity=path.identity,
            lexical_safe=True,
            physical_safe=True,
            count_contribution=entry.count_contribution,
            byte_contribution=entry.byte_contribution,
        )
    except _InspectionFailure as failure:
        return _rejected(failure.detail, path, lexical_safe=True)
    except Exception:
        return _rejected("INSPECTION_ERROR", path, lexical_safe=True)
