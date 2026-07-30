"""Course-level Docker container lifecycle orchestration and evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
from typing import Protocol

from coding_harness.sandbox.docker_cli import (
    DockerCLIResult,
    DockerCommand,
    DockerOperation,
    FixedImage,
    _valid_container_name,
)


_MAX_TEXT_BYTES = 4_096
_MAX_COMMAND_ITEMS = 256


def _valid_text(value: object) -> bool:
    if type(value) is not str or not value or "\0" in value:
        return False
    try:
        return len(value.encode("utf-8", errors="strict")) <= _MAX_TEXT_BYTES
    except UnicodeError:
        return False


def _bounded_text(value: str) -> str:
    encoded = value.encode("utf-8", errors="replace")[:_MAX_TEXT_BYTES]
    return encoded.decode("utf-8", errors="ignore")


def _combined_output(results: tuple[DockerCLIResult, ...], field_name: str) -> str:
    values = tuple(
        value
        for result in results
        if (value := getattr(result, field_name))
    )
    return _bounded_text("\n".join(values))


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _command_bytes(command: tuple[str, ...]) -> bytes:
    return json.dumps(
        command,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


class ExecutionStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CLEANUP_FAILED = "CLEANUP_FAILED"
    DOCKER_UNAVAILABLE = "DOCKER_UNAVAILABLE"


class CleanupStatus(StrEnum):
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    NOT_REQUIRED = "NOT_REQUIRED"


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    container_name: str
    image: FixedImage
    command: tuple[str, ...]
    timeout_seconds: int
    occurred_at: int

    def __post_init__(self) -> None:
        if (
            not _valid_container_name(self.container_name)
            or type(self.image) is not FixedImage
            or type(self.command) is not tuple
            or not self.command
            or len(self.command) > _MAX_COMMAND_ITEMS
            or any(not _valid_text(item) for item in self.command)
            or type(self.timeout_seconds) is not int
            or self.timeout_seconds < 1
            or type(self.occurred_at) is not int
            or self.occurred_at < 0
        ):
            raise ValueError("execution request is invalid")


@dataclass(frozen=True, slots=True)
class ExecutionEvidence:
    image: FixedImage
    command: tuple[str, ...]
    exit_status: int | None
    stdout_summary: str
    stderr_summary: str
    duration_milliseconds: int
    container_identity: str
    occurred_at: int
    status: ExecutionStatus
    timed_out: bool
    cleanup_status: CleanupStatus
    cleanup_error: str | None
    command_identity: str = field(init=False)
    evidence_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.image) is not FixedImage
            or type(self.command) is not tuple
            or not self.command
            or len(self.command) > _MAX_COMMAND_ITEMS
            or any(not _valid_text(item) for item in self.command)
            or (
                self.exit_status is not None
                and type(self.exit_status) is not int
            )
            or type(self.stdout_summary) is not str
            or len(self.stdout_summary.encode("utf-8")) > _MAX_TEXT_BYTES
            or type(self.stderr_summary) is not str
            or len(self.stderr_summary.encode("utf-8")) > _MAX_TEXT_BYTES
            or type(self.duration_milliseconds) is not int
            or self.duration_milliseconds < 0
            or not _valid_text(self.container_identity)
            or type(self.occurred_at) is not int
            or self.occurred_at < 0
            or type(self.status) is not ExecutionStatus
            or type(self.timed_out) is not bool
            or type(self.cleanup_status) is not CleanupStatus
            or (
                self.cleanup_error is not None
                and not _valid_text(self.cleanup_error)
            )
            or (
                self.cleanup_status is CleanupStatus.FAILED
                and self.cleanup_error is None
            )
            or (
                self.cleanup_status is not CleanupStatus.FAILED
                and self.cleanup_error is not None
            )
        ):
            raise ValueError("execution evidence is invalid")
        object.__setattr__(
            self,
            "command_identity",
            _sha256(_command_bytes(self.command)),
        )
        object.__setattr__(
            self,
            "evidence_digest",
            _sha256(self.canonical_bytes()),
        )

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            {
                "cleanup_error": self.cleanup_error,
                "cleanup_status": self.cleanup_status.value,
                "command": self.command,
                "command_identity": self.command_identity,
                "container_identity": self.container_identity,
                "duration_milliseconds": self.duration_milliseconds,
                "exit_status": self.exit_status,
                "image": self.image.value,
                "occurred_at": self.occurred_at,
                "status": self.status.value,
                "stderr_summary": self.stderr_summary,
                "stdout_summary": self.stdout_summary,
                "timed_out": self.timed_out,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")


class _DockerRunner(Protocol):
    def run(
        self,
        command: DockerCommand,
        *,
        timeout_seconds: int,
    ) -> DockerCLIResult: ...


class ContainerLifecycle:
    def __init__(self, *, cli: _DockerRunner) -> None:
        if not callable(getattr(cli, "run", None)):
            raise ValueError("Docker lifecycle CLI is invalid")
        self._cli = cli

    def execute(self, request: ExecutionRequest) -> ExecutionEvidence:
        if type(request) is not ExecutionRequest:
            raise ValueError("execution request is invalid")

        results: list[DockerCLIResult] = []
        create = self._run(
            DockerCommand(
                operation=DockerOperation.CREATE,
                container_name=request.container_name,
                image=request.image,
                container_command=request.command,
            ),
            request,
        )
        results.append(create)
        if create.unavailable:
            return self._evidence(
                request=request,
                results=tuple(results),
                status=ExecutionStatus.DOCKER_UNAVAILABLE,
                exit_status=None,
                timed_out=False,
                cleanup_status=CleanupStatus.NOT_REQUIRED,
                cleanup_error=None,
            )
        if create.timed_out:
            cleanup = self._run(
                DockerCommand(
                    operation=DockerOperation.REMOVE,
                    container_name=request.container_name,
                ),
                request,
            )
            results.append(cleanup)
            cleanup_failed = (
                cleanup.unavailable
                or cleanup.timed_out
                or cleanup.exit_code != 0
            )
            cleanup_error = (
                _bounded_text(cleanup.stderr or "container cleanup failed")
                if cleanup_failed
                else None
            )
            return self._evidence(
                request=request,
                results=tuple(results),
                status=(
                    ExecutionStatus.CLEANUP_FAILED
                    if cleanup_failed
                    else ExecutionStatus.TIMED_OUT
                ),
                exit_status=None,
                timed_out=True,
                cleanup_status=(
                    CleanupStatus.FAILED
                    if cleanup_failed
                    else CleanupStatus.COMPLETE
                ),
                cleanup_error=cleanup_error,
            )
        if create.exit_code != 0:
            return self._evidence(
                request=request,
                results=tuple(results),
                status=ExecutionStatus.FAILED,
                exit_status=create.exit_code,
                timed_out=create.timed_out,
                cleanup_status=CleanupStatus.NOT_REQUIRED,
                cleanup_error=None,
            )

        start = self._run(
            DockerCommand(
                operation=DockerOperation.START,
                container_name=request.container_name,
            ),
            request,
        )
        results.append(start)
        if start.unavailable or start.timed_out or start.exit_code != 0:
            execution_status = (
                ExecutionStatus.DOCKER_UNAVAILABLE
                if start.unavailable
                else ExecutionStatus.TIMED_OUT
                if start.timed_out
                else ExecutionStatus.FAILED
            )
            execution_exit = start.exit_code
            execution_timed_out = start.timed_out
        else:
            wait = self._run(
                DockerCommand(
                    operation=DockerOperation.WAIT,
                    container_name=request.container_name,
                ),
                request,
            )
            results.append(wait)
            execution_status = (
                ExecutionStatus.DOCKER_UNAVAILABLE
                if wait.unavailable
                else ExecutionStatus.TIMED_OUT
                if wait.timed_out
                else ExecutionStatus.SUCCEEDED
                if wait.exit_code == 0
                else ExecutionStatus.FAILED
            )
            execution_exit = wait.exit_code
            execution_timed_out = wait.timed_out

        cleanup = self._run(
            DockerCommand(
                operation=DockerOperation.REMOVE,
                container_name=request.container_name,
            ),
            request,
        )
        results.append(cleanup)
        cleanup_failed = (
            cleanup.unavailable
            or cleanup.timed_out
            or cleanup.exit_code != 0
        )
        cleanup_error = (
            _bounded_text(cleanup.stderr or "container cleanup failed")
            if cleanup_failed
            else None
        )
        return self._evidence(
            request=request,
            results=tuple(results),
            status=(
                ExecutionStatus.CLEANUP_FAILED
                if cleanup_failed
                else execution_status
            ),
            exit_status=execution_exit,
            timed_out=execution_timed_out,
            cleanup_status=(
                CleanupStatus.FAILED
                if cleanup_failed
                else CleanupStatus.COMPLETE
            ),
            cleanup_error=cleanup_error,
        )

    def _run(
        self,
        command: DockerCommand,
        request: ExecutionRequest,
    ) -> DockerCLIResult:
        result = self._cli.run(
            command,
            timeout_seconds=request.timeout_seconds,
        )
        if (
            type(result) is not DockerCLIResult
            or result.operation is not command.operation
        ):
            raise ValueError("Docker CLI returned invalid lifecycle evidence")
        return result

    @staticmethod
    def _evidence(
        *,
        request: ExecutionRequest,
        results: tuple[DockerCLIResult, ...],
        status: ExecutionStatus,
        exit_status: int | None,
        timed_out: bool,
        cleanup_status: CleanupStatus,
        cleanup_error: str | None,
    ) -> ExecutionEvidence:
        return ExecutionEvidence(
            image=request.image,
            command=request.command,
            exit_status=exit_status,
            stdout_summary=_combined_output(results, "stdout"),
            stderr_summary=_combined_output(results, "stderr"),
            duration_milliseconds=sum(
                result.duration_milliseconds for result in results
            ),
            container_identity=request.container_name,
            occurred_at=request.occurred_at,
            status=status,
            timed_out=timed_out,
            cleanup_status=cleanup_status,
            cleanup_error=cleanup_error,
        )
