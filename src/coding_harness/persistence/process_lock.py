"""Kernel-authoritative process lock for a single Harness serve process."""

from __future__ import annotations

from enum import StrEnum
import errno
import fcntl
import os
from pathlib import Path


class ProcessLockOutcome(StrEnum):
    ACQUIRED = "ACQUIRED"
    BUSY = "BUSY"


class ProcessLockError(RuntimeError):
    pass


class ProcessLock:
    """Hold an advisory OS lock for as long as its descriptor remains open."""

    def __init__(self, *, lock_path: Path) -> None:
        if not isinstance(lock_path, Path):
            raise ValueError("process lock path is invalid")
        self._lock_path = lock_path
        self._descriptor: int | None = None

    def acquire(self) -> ProcessLockOutcome:
        if self._descriptor is not None:
            return ProcessLockOutcome.ACQUIRED
        try:
            descriptor = os.open(
                self._lock_path,
                os.O_CREAT | os.O_RDWR,
                0o600,
            )
        except OSError:
            raise ProcessLockError("process lock is unavailable") from None
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            os.close(descriptor)
            if error.errno in {errno.EACCES, errno.EAGAIN}:
                return ProcessLockOutcome.BUSY
            raise ProcessLockError("process lock acquisition failed") from None
        self._descriptor = descriptor
        return ProcessLockOutcome.ACQUIRED

    def release(self) -> None:
        descriptor = self._descriptor
        if descriptor is None:
            return
        self._descriptor = None
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        except OSError:
            raise ProcessLockError("process lock release failed") from None
        finally:
            os.close(descriptor)


__all__ = [
    "ProcessLock",
    "ProcessLockError",
    "ProcessLockOutcome",
]
