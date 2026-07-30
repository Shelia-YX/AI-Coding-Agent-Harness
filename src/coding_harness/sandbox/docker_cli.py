"""Narrow subprocess boundary for the course-level Docker lifecycle."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import re
import subprocess
import time
from typing import Any


_MAX_TEXT_BYTES = 4_096
_MAX_COMMAND_ITEMS = 256
_CONTAINER_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


def _valid_text(value: object) -> bool:
    if type(value) is not str or not value or "\0" in value:
        return False
    try:
        return len(value.encode("utf-8", errors="strict")) <= _MAX_TEXT_BYTES
    except UnicodeError:
        return False


def _bounded_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    else:
        text = str(value)
    encoded = text.encode("utf-8", errors="replace")[:_MAX_TEXT_BYTES]
    return encoded.decode("utf-8", errors="ignore")


def _valid_container_name(value: object) -> bool:
    return _valid_text(value) and _CONTAINER_NAME.fullmatch(value) is not None


class DockerOperation(StrEnum):
    CREATE = "create"
    START = "start"
    WAIT = "wait"
    REMOVE = "rm"


class FixedImage(StrEnum):
    PYTHON312 = "python:3.12"
    NODE20 = "node:20"


@dataclass(frozen=True, slots=True)
class DockerCommand:
    operation: DockerOperation
    container_name: str
    image: FixedImage | None = None
    container_command: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.operation) is not DockerOperation
            or not _valid_container_name(self.container_name)
            or type(self.container_command) is not tuple
            or len(self.container_command) > _MAX_COMMAND_ITEMS
            or any(not _valid_text(item) for item in self.container_command)
        ):
            raise ValueError("Docker command is invalid")
        if self.operation is DockerOperation.CREATE:
            if type(self.image) is not FixedImage:
                raise ValueError("create requires a fixed image")
        elif self.image is not None or self.container_command:
            raise ValueError("only create accepts image and container command")


@dataclass(frozen=True, slots=True)
class DockerCLIResult:
    operation: DockerOperation
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    unavailable: bool = False
    duration_milliseconds: int = 0

    def __post_init__(self) -> None:
        if (
            type(self.operation) is not DockerOperation
            or (
                self.exit_code is not None
                and type(self.exit_code) is not int
            )
            or type(self.stdout) is not str
            or type(self.stderr) is not str
            or type(self.timed_out) is not bool
            or type(self.unavailable) is not bool
            or type(self.duration_milliseconds) is not int
            or self.duration_milliseconds < 0
            or (self.timed_out and self.unavailable)
        ):
            raise ValueError("Docker CLI result is invalid")


class DockerCLI:
    """Build and execute only the fixed lifecycle operations."""

    def __init__(
        self,
        *,
        executable: str,
        runner: Callable[..., Any] = subprocess.run,
        clock_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if (
            not _valid_text(executable)
            or not Path(executable).is_absolute()
            or not callable(runner)
            or not callable(clock_ns)
        ):
            raise ValueError("Docker CLI configuration is invalid")
        self._executable = executable
        self._runner = runner
        self._clock_ns = clock_ns

    def run(
        self,
        command: DockerCommand,
        *,
        timeout_seconds: int,
    ) -> DockerCLIResult:
        if (
            type(command) is not DockerCommand
            or type(timeout_seconds) is not int
            or timeout_seconds < 1
        ):
            raise ValueError("Docker CLI invocation is invalid")

        argv = self._argv(command)
        started_ns = self._clock_ns()
        try:
            completed = self._runner(
                argv,
                shell=False,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            return DockerCLIResult(
                operation=command.operation,
                exit_code=None,
                stdout=_bounded_text(error.stdout),
                stderr=_bounded_text(error.stderr),
                timed_out=True,
                duration_milliseconds=self._elapsed_milliseconds(started_ns),
            )
        except subprocess.SubprocessError as error:
            return DockerCLIResult(
                operation=command.operation,
                exit_code=1,
                stdout="",
                stderr=_bounded_text(str(error)),
                duration_milliseconds=self._elapsed_milliseconds(started_ns),
            )
        except OSError as error:
            return DockerCLIResult(
                operation=command.operation,
                exit_code=None,
                stdout="",
                stderr=_bounded_text(str(error)),
                unavailable=True,
                duration_milliseconds=self._elapsed_milliseconds(started_ns),
            )

        stdout = _bounded_text(completed.stdout)
        stderr = _bounded_text(completed.stderr)
        exit_code = completed.returncode
        if (
            command.operation is DockerOperation.WAIT
            and completed.returncode == 0
        ):
            try:
                exit_code = int(stdout.strip())
                stdout = ""
            except ValueError:
                exit_code = None
                stderr = _bounded_text(
                    f"{stderr}\ninvalid docker wait result".strip()
                )
        return DockerCLIResult(
            operation=command.operation,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_milliseconds=self._elapsed_milliseconds(started_ns),
        )

    def _elapsed_milliseconds(self, started_ns: int) -> int:
        return max(0, (self._clock_ns() - started_ns) // 1_000_000)

    def _argv(self, command: DockerCommand) -> tuple[str, ...]:
        if command.operation is DockerOperation.CREATE:
            assert command.image is not None
            return (
                self._executable,
                "create",
                "--name",
                command.container_name,
                command.image.value,
                *command.container_command,
            )
        if command.operation is DockerOperation.START:
            return (
                self._executable,
                "start",
                "--attach",
                command.container_name,
            )
        if command.operation is DockerOperation.WAIT:
            return (self._executable, "wait", command.container_name)
        return (
            self._executable,
            "rm",
            "--force",
            command.container_name,
        )
