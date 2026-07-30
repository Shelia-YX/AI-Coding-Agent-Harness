from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import importlib
import json
import subprocess

import pytest


_MISSING_CONTRACT = (
    "EXPECTED_INTERFACE_MISSING: WP-20 Docker execution contract"
)


def _api():
    try:
        docker_cli = importlib.import_module(
            "coding_harness.sandbox.docker_cli"
        )
        lifecycle = importlib.import_module(
            "coding_harness.sandbox.lifecycle"
        )
    except ModuleNotFoundError as error:
        if error.name in {
            "coding_harness.sandbox.docker_cli",
            "coding_harness.sandbox.lifecycle",
        }:
            pytest.fail(_MISSING_CONTRACT, pytrace=False)
        raise
    return docker_cli, lifecycle


class _RecordingRunner:
    def __init__(
        self,
        *,
        returncode: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def __call__(self, argv, **kwargs):
        normalized = tuple(argv)
        self.calls.append((normalized, dict(kwargs)))
        return subprocess.CompletedProcess(
            normalized,
            self.returncode,
            stdout=self.stdout,
            stderr=self.stderr,
        )


class _ScriptedCLI:
    def __init__(self, results) -> None:
        self._results = list(results)
        self.commands = []
        self.timeouts: list[int] = []

    def run(self, command, *, timeout_seconds: int):
        self.commands.append(command)
        self.timeouts.append(timeout_seconds)
        result = self._results.pop(0)
        assert result.operation is command.operation
        return result


class _CleanupExceptionRunner:
    def __call__(self, argv, **kwargs):
        normalized = tuple(argv)
        operation = normalized[1]
        if operation == "rm":
            raise subprocess.SubprocessError("cleanup transport failed")
        stdout = (
            "validation passed"
            if operation == "start"
            else "0\n"
            if operation == "wait"
            else ""
        )
        return subprocess.CompletedProcess(
            normalized,
            0,
            stdout=stdout,
            stderr="",
        )


def _command(
    docker_cli,
    *,
    image=None,
    operation=None,
    container_command: tuple[str, ...] = (),
):
    return docker_cli.DockerCommand(
        operation=operation or docker_cli.DockerOperation.CREATE,
        container_name="harness-run-001",
        image=image or docker_cli.FixedImage.PYTHON312,
        container_command=container_command,
    )


def _result(
    docker_cli,
    operation,
    *,
    exit_code: int | None = 0,
    stdout: str = "",
    stderr: str = "",
    timed_out: bool = False,
    unavailable: bool = False,
):
    return docker_cli.DockerCLIResult(
        operation=operation,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        unavailable=unavailable,
    )


def _request(docker_cli, lifecycle, **overrides):
    values = {
        "container_name": "harness-run-001",
        "image": docker_cli.FixedImage.PYTHON312,
        "command": ("python", "-m", "pytest", "-q"),
        "timeout_seconds": 30,
        "occurred_at": 100,
    }
    values.update(overrides)
    return lifecycle.ExecutionRequest(**values)


def _lifecycle_results(
    docker_cli,
    *,
    wait_exit: int | None = 0,
    wait_stdout: str = "12 passed",
    wait_stderr: str = "",
    wait_timed_out: bool = False,
    create_unavailable: bool = False,
    cleanup_exit: int = 0,
):
    operation = docker_cli.DockerOperation
    if create_unavailable:
        return (
            _result(
                docker_cli,
                operation.CREATE,
                exit_code=None,
                stderr="Docker is unavailable",
                unavailable=True,
            ),
        )
    return (
        _result(docker_cli, operation.CREATE),
        _result(docker_cli, operation.START),
        _result(
            docker_cli,
            operation.WAIT,
            exit_code=wait_exit,
            stdout=wait_stdout,
            stderr=wait_stderr,
            timed_out=wait_timed_out,
        ),
        _result(
            docker_cli,
            operation.REMOVE,
            exit_code=cleanup_exit,
            stderr="" if cleanup_exit == 0 else "remove failed",
        ),
    )


def _execute(docker_cli, lifecycle, results, **request_overrides):
    cli = _ScriptedCLI(results)
    coordinator = lifecycle.ContainerLifecycle(cli=cli)
    evidence = coordinator.execute(
        _request(docker_cli, lifecycle, **request_overrides)
    )
    return cli, evidence


def test_absolute_cli_structured_argv() -> None:
    docker_cli, _ = _api()
    runner = _RecordingRunner()
    cli = docker_cli.DockerCLI(
        executable="/usr/bin/docker",
        runner=runner,
    )

    cli.run(
        _command(
            docker_cli,
            image=docker_cli.FixedImage.PYTHON312,
            container_command=("python", "-m", "pytest", "-q"),
        ),
        timeout_seconds=30,
    )

    assert runner.calls[0][0] == (
        "/usr/bin/docker",
        "create",
        "--name",
        "harness-run-001",
        "python:3.12",
        "python",
        "-m",
        "pytest",
        "-q",
    )


def test_docker_cli_always_uses_shell_false() -> None:
    docker_cli, _ = _api()
    runner = _RecordingRunner()
    cli = docker_cli.DockerCLI(
        executable="/usr/bin/docker",
        runner=runner,
    )

    cli.run(_command(docker_cli), timeout_seconds=30)

    assert runner.calls[0][1]["shell"] is False


def test_fixed_image_allowlist_accepts_only_course_profiles() -> None:
    docker_cli, _ = _api()

    assert tuple(image.value for image in docker_cli.FixedImage) == (
        "python:3.12",
        "node:20",
    )
    with pytest.raises(ValueError):
        _command(docker_cli, image="ubuntu:latest")


def test_arbitrary_docker_arguments_are_rejected() -> None:
    docker_cli, _ = _api()

    with pytest.raises(TypeError):
        docker_cli.DockerCommand(
            operation=docker_cli.DockerOperation.CREATE,
            container_name="harness-run-001",
            image=docker_cli.FixedImage.PYTHON312,
            container_command=("python", "-m", "pytest"),
            docker_arguments=("--privileged",),
        )


@pytest.mark.parametrize(
    "container_name",
    ("--help", "--privileged"),
    ids=("help-option", "privileged-option"),
)
def test_container_name_option_injection(container_name: str) -> None:
    docker_cli, lifecycle = _api()

    with pytest.raises(ValueError):
        docker_cli.DockerCommand(
            operation=docker_cli.DockerOperation.CREATE,
            container_name=container_name,
            image=docker_cli.FixedImage.PYTHON312,
            container_command=("python",),
        )
    with pytest.raises(ValueError):
        lifecycle.ExecutionRequest(
            container_name=container_name,
            image=docker_cli.FixedImage.PYTHON312,
            command=("python",),
            timeout_seconds=10,
            occurred_at=1,
        )


@pytest.mark.parametrize(
    ("operation", "expected"),
    (
        (
            "START",
            ("/usr/bin/docker", "start", "--attach", "harness-run-001"),
        ),
        (
            "WAIT",
            ("/usr/bin/docker", "wait", "harness-run-001"),
        ),
        (
            "REMOVE",
            (
                "/usr/bin/docker",
                "rm",
                "--force",
                "harness-run-001",
            ),
        ),
    ),
    ids=("start", "wait", "remove"),
)
def test_fixed_lifecycle_operation_argv(
    operation: str,
    expected: tuple[str, ...],
) -> None:
    docker_cli, _ = _api()
    runner = _RecordingRunner(
        stdout="0\n" if operation == "WAIT" else "",
    )
    cli = docker_cli.DockerCLI(
        executable="/usr/bin/docker",
        runner=runner,
    )

    cli.run(
        docker_cli.DockerCommand(
            operation=getattr(docker_cli.DockerOperation, operation),
            container_name="harness-run-001",
        ),
        timeout_seconds=30,
    )

    assert runner.calls[0][0] == expected


def test_docker_cli_timeout_expired_is_structured() -> None:
    docker_cli, _ = _api()

    def timeout_runner(argv, **kwargs):
        raise subprocess.TimeoutExpired(
            argv,
            kwargs["timeout"],
            output="partial output",
            stderr="deadline reached",
        )

    result = docker_cli.DockerCLI(
        executable="/usr/bin/docker",
        runner=timeout_runner,
    ).run(_command(docker_cli), timeout_seconds=3)

    assert result.timed_out is True
    assert result.unavailable is False
    assert result.exit_code is None
    assert result.stdout == "partial output"
    assert result.stderr == "deadline reached"


def test_malformed_wait_output_is_structured_failure() -> None:
    docker_cli, _ = _api()
    runner = _RecordingRunner(stdout="not-an-exit-status")
    result = docker_cli.DockerCLI(
        executable="/usr/bin/docker",
        runner=runner,
    ).run(
        docker_cli.DockerCommand(
            operation=docker_cli.DockerOperation.WAIT,
            container_name="harness-run-001",
        ),
        timeout_seconds=30,
    )

    assert result.exit_code is None
    assert result.timed_out is False
    assert result.unavailable is False
    assert "invalid docker wait result" in result.stderr


def test_lifecycle_orders_create_start_wait_cleanup() -> None:
    docker_cli, lifecycle = _api()
    cli, _ = _execute(
        docker_cli,
        lifecycle,
        _lifecycle_results(docker_cli),
    )

    assert tuple(command.operation for command in cli.commands) == (
        docker_cli.DockerOperation.CREATE,
        docker_cli.DockerOperation.START,
        docker_cli.DockerOperation.WAIT,
        docker_cli.DockerOperation.REMOVE,
    )


def test_normal_exit_produces_success_evidence() -> None:
    docker_cli, lifecycle = _api()
    _, evidence = _execute(
        docker_cli,
        lifecycle,
        _lifecycle_results(docker_cli),
    )

    assert evidence.status is lifecycle.ExecutionStatus.SUCCEEDED
    assert evidence.exit_status == 0
    assert evidence.timed_out is False
    assert evidence.cleanup_status is lifecycle.CleanupStatus.COMPLETE
    assert evidence.stdout_summary == "12 passed"


def test_nonzero_exit_produces_failure_evidence() -> None:
    docker_cli, lifecycle = _api()
    _, evidence = _execute(
        docker_cli,
        lifecycle,
        _lifecycle_results(
            docker_cli,
            wait_exit=7,
            wait_stdout="",
            wait_stderr="tests failed",
        ),
    )

    assert evidence.status is lifecycle.ExecutionStatus.FAILED
    assert evidence.exit_status == 7
    assert evidence.cleanup_status is lifecycle.CleanupStatus.COMPLETE
    assert evidence.stderr_summary == "tests failed"


def test_timeout_is_reported_and_cleanup_still_runs() -> None:
    docker_cli, lifecycle = _api()
    cli, evidence = _execute(
        docker_cli,
        lifecycle,
        _lifecycle_results(
            docker_cli,
            wait_exit=None,
            wait_stdout="",
            wait_stderr="execution timed out",
            wait_timed_out=True,
        ),
        timeout_seconds=5,
    )

    assert evidence.status is lifecycle.ExecutionStatus.TIMED_OUT
    assert evidence.exit_status is None
    assert evidence.timed_out is True
    assert cli.commands[-1].operation is docker_cli.DockerOperation.REMOVE


def test_create_timeout_cleanup_attempt() -> None:
    docker_cli, lifecycle = _api()
    operation = docker_cli.DockerOperation
    cli, evidence = _execute(
        docker_cli,
        lifecycle,
        (
            _result(
                docker_cli,
                operation.CREATE,
                exit_code=None,
                stderr="create timed out",
                timed_out=True,
            ),
            _result(docker_cli, operation.REMOVE),
        ),
    )

    assert evidence.status is lifecycle.ExecutionStatus.TIMED_OUT
    assert evidence.timed_out is True
    assert evidence.cleanup_status is lifecycle.CleanupStatus.COMPLETE
    assert tuple(command.operation for command in cli.commands) == (
        operation.CREATE,
        operation.REMOVE,
    )


def test_cleanup_failure_is_explicit_and_never_reported_as_success() -> None:
    docker_cli, lifecycle = _api()
    _, evidence = _execute(
        docker_cli,
        lifecycle,
        _lifecycle_results(docker_cli, cleanup_exit=1),
    )

    assert evidence.status is lifecycle.ExecutionStatus.CLEANUP_FAILED
    assert evidence.cleanup_status is lifecycle.CleanupStatus.FAILED
    assert evidence.cleanup_error == "remove failed"


def test_cleanup_subprocess_error() -> None:
    docker_cli, lifecycle = _api()
    cli = docker_cli.DockerCLI(
        executable="/usr/bin/docker",
        runner=_CleanupExceptionRunner(),
    )

    evidence = lifecycle.ContainerLifecycle(cli=cli).execute(
        _request(docker_cli, lifecycle)
    )

    assert evidence.status is lifecycle.ExecutionStatus.CLEANUP_FAILED
    assert evidence.cleanup_status is lifecycle.CleanupStatus.FAILED
    assert evidence.cleanup_error == "cleanup transport failed"


def test_docker_unavailable_blocks_without_host_fallback() -> None:
    docker_cli, lifecycle = _api()
    cli, evidence = _execute(
        docker_cli,
        lifecycle,
        _lifecycle_results(docker_cli, create_unavailable=True),
    )

    assert evidence.status is lifecycle.ExecutionStatus.DOCKER_UNAVAILABLE
    assert evidence.exit_status is None
    assert len(cli.commands) == 1
    assert cli.commands[0].operation is docker_cli.DockerOperation.CREATE


def test_execution_evidence_is_deterministic() -> None:
    docker_cli, lifecycle = _api()
    _, first = _execute(
        docker_cli,
        lifecycle,
        _lifecycle_results(docker_cli),
    )
    _, second = _execute(
        docker_cli,
        lifecycle,
        _lifecycle_results(docker_cli),
    )

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.evidence_digest == second.evidence_digest
    assert len(first.evidence_digest) == 64
    assert set(first.evidence_digest) <= set("0123456789abcdef")


def test_command_identity_tampering_rejected() -> None:
    docker_cli, lifecycle = _api()
    _, evidence = _execute(
        docker_cli,
        lifecycle,
        _lifecycle_results(docker_cli),
    )
    expected = hashlib.sha256(
        json.dumps(
            evidence.command,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    assert evidence.command_identity == expected
    with pytest.raises(ValueError):
        replace(evidence, command_identity="0" * 64)


def test_execution_evidence_is_immutable() -> None:
    docker_cli, lifecycle = _api()
    _, evidence = _execute(
        docker_cli,
        lifecycle,
        _lifecycle_results(docker_cli),
    )

    with pytest.raises(FrozenInstanceError):
        evidence.status = lifecycle.ExecutionStatus.FAILED


def test_execution_evidence_rejects_malformed_command_tuple() -> None:
    docker_cli, lifecycle = _api()
    _, evidence = _execute(
        docker_cli,
        lifecycle,
        _lifecycle_results(docker_cli),
    )

    with pytest.raises(ValueError):
        replace(evidence, command=(object(),))


def test_execution_evidence_rejects_oversized_command_item() -> None:
    docker_cli, lifecycle = _api()
    _, evidence = _execute(
        docker_cli,
        lifecycle,
        _lifecycle_results(docker_cli),
    )

    with pytest.raises(ValueError):
        replace(evidence, command=("é" * 2_049,))


def test_execution_evidence_rejects_oversized_direct_output() -> None:
    docker_cli, lifecycle = _api()
    _, evidence = _execute(
        docker_cli,
        lifecycle,
        _lifecycle_results(docker_cli),
    )

    with pytest.raises(ValueError):
        replace(evidence, stdout_summary="é" * 2_049)


def test_execution_evidence_bounds_utf8_stdout_and_stderr() -> None:
    docker_cli, lifecycle = _api()
    _, evidence = _execute(
        docker_cli,
        lifecycle,
        _lifecycle_results(
            docker_cli,
            wait_exit=1,
            wait_stdout="é" * 3_000,
            wait_stderr="界" * 2_000,
        ),
    )

    assert len(evidence.stdout_summary.encode("utf-8")) <= 4_096
    assert len(evidence.stderr_summary.encode("utf-8")) <= 4_096
