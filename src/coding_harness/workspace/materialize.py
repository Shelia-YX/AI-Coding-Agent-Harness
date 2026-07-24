"""Independent task-workspace materialization for WP-10."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil
import stat

from coding_harness.workspace.file_model import SupportedEntryKind
from coding_harness.workspace.manifest import BaselineEntry, BaselineManifest


_INVALID_WORKSPACE = "workspace materialization failed"


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


@dataclass(frozen=True, slots=True)
class TaskWorkspace:
    """Identity and baseline binding for an independently writable tree."""

    root: Path
    baseline_digest: str
    source_head: str
    source_branch: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.root, Path)
            or not _is_digest(self.baseline_digest)
            or not _is_git_object_id(self.source_head)
            or type(self.source_branch) is not str
        ):
            raise ValueError("task workspace is invalid")

    def __bool__(self) -> bool:
        raise TypeError("TaskWorkspace has no truth value")


def _destination_path(root: Path, entry: BaselineEntry) -> Path:
    if any(segment == ".git" for segment in entry.path.segments):
        raise ValueError(_INVALID_WORKSPACE)
    candidate = root.joinpath(*entry.path.segments)
    try:
        candidate.relative_to(root)
    except ValueError:
        raise ValueError(_INVALID_WORKSPACE) from None
    return candidate


def _write_regular(destination: Path, entry: BaselineEntry) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(destination, flags, 0o600)
        try:
            remaining = memoryview(entry.content)
            while remaining:
                written = os.write(descriptor, remaining)
                if written <= 0:
                    raise OSError("write failed")
                remaining = remaining[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.chmod(destination, 0o755 if entry.executable else 0o644)
    except OSError:
        raise ValueError(_INVALID_WORKSPACE) from None
    try:
        written_status = os.lstat(destination)
        written_content = destination.read_bytes()
    except OSError:
        raise ValueError(_INVALID_WORKSPACE) from None
    if (
        not stat.S_ISREG(written_status.st_mode)
        or hashlib.sha256(written_content).hexdigest() != entry.content_digest
    ):
        raise ValueError(_INVALID_WORKSPACE)


def _write_symlink(destination: Path, entry: BaselineEntry) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if type(entry.symlink_target) is not str:
        raise ValueError(_INVALID_WORKSPACE)
    try:
        os.symlink(entry.symlink_target, destination)
    except OSError:
        raise ValueError(_INVALID_WORKSPACE) from None


def materialize_workspace(
    manifest: BaselineManifest,
    destination: Path,
) -> TaskWorkspace:
    """Create a fresh writable tree using only immutable manifest contents."""

    if type(manifest) is not BaselineManifest or not isinstance(destination, Path):
        raise ValueError(_INVALID_WORKSPACE)
    if os.path.lexists(destination):
        raise ValueError(_INVALID_WORKSPACE)
    parent = destination.parent
    try:
        parent_status = os.lstat(parent)
    except OSError:
        raise ValueError(_INVALID_WORKSPACE) from None
    if stat.S_ISLNK(parent_status.st_mode) or not stat.S_ISDIR(parent_status.st_mode):
        raise ValueError(_INVALID_WORKSPACE)

    created = False
    try:
        destination.mkdir(mode=0o700)
        created = True
        for entry in manifest.entries:
            target = _destination_path(destination, entry)
            if entry.kind is SupportedEntryKind.REGULAR_FILE:
                _write_regular(target, entry)
            elif entry.kind is SupportedEntryKind.SYMLINK:
                _write_symlink(target, entry)
            else:
                raise ValueError(_INVALID_WORKSPACE)
        if os.path.lexists(destination / ".git") or any(
            path.name == ".git" for path in destination.rglob("*")
        ):
            raise ValueError(_INVALID_WORKSPACE)
    except Exception:
        if created:
            shutil.rmtree(destination, ignore_errors=True)
        raise

    return TaskWorkspace(
        root=destination,
        baseline_digest=manifest.digest,
        source_head=manifest.source_head,
        source_branch=manifest.source_branch,
    )
