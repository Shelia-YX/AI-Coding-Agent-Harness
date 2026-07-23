"""WP-09 path and supported-entry contract tests.

All filesystem and Git fixtures are isolated below pytest's ``tmp_path``.
Imports deliberately happen inside test bodies so the pre-implementation suite
collects successfully and fails Red at the missing WP-09 production boundary.
"""

from __future__ import annotations

import importlib
import hashlib
import os
from pathlib import Path
import signal
import socket
import stat
import subprocess
from types import SimpleNamespace

import pytest


PATH_POLICY_VIOLATION = "PATH_POLICY_VIOLATION"
SUPPORTED = "SUPPORTED"
REJECTED = "REJECTED"


def _api() -> SimpleNamespace:
    paths = importlib.import_module("coding_harness.workspace.paths")
    file_model = importlib.import_module("coding_harness.workspace.file_model")
    return SimpleNamespace(
        file_model=file_model,
        RepoPath=paths.RepoPath,
        SupportedEntry=file_model.SupportedEntry,
        inspect_supported_entry=file_model.inspect_supported_entry,
    )


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def _assert_supported(result: object) -> object:
    assert _enum_value(result.status) == SUPPORTED
    assert result.entry is not None
    return result.entry


def _assert_rejected(result: object, detail: str | None = None) -> None:
    assert _enum_value(result.status) == REJECTED
    assert _enum_value(result.reason_code) == PATH_POLICY_VIOLATION
    assert result.entry is None
    if detail is not None:
        assert result.detail == detail


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    git_home = repo.parent / ".git-test-home"
    git_home.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "HOME": str(git_home),
        }
    )
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> str:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    (root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    _git(root, "add", "tracked.txt")
    _git(
        root,
        "-c",
        "user.name=WP09 Test",
        "-c",
        "user.email=wp09@example.invalid",
        "commit",
        "-q",
        "-m",
        "fixture",
    )
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def _git_dir(root: Path) -> Path:
    value = _git(root, "rev-parse", "--git-dir").stdout.strip()
    path = Path(value)
    return path if path.is_absolute() else root / path


def _inspect(root: Path, relative: str, **kwargs: object) -> object:
    api = _api()
    return api.inspect_supported_entry(
        root,
        api.RepoPath.parse(relative),
        **kwargs,
    )


def test_relative_path() -> None:
    api = _api()

    path = api.RepoPath.parse("src/coding_harness/workspace/paths.py")

    assert path.canonical == "src/coding_harness/workspace/paths.py"
    assert path.segments == (
        "src",
        "coding_harness",
        "workspace",
        "paths.py",
    )
    assert path.identity != path.display_name


@pytest.mark.parametrize(
    "value",
    [
        "",
        ".",
        "..",
        "a/../b",
        "a//b",
        "a/b/",
        "-option",
        ":pathspec",
        "a/*",
        "a/?",
        "a/[b]",
    ],
    ids=[
        "empty",
        "dot",
        "parent",
        "middle-parent",
        "repeated-separator",
        "trailing-separator",
        "option-like",
        "pathspec-magic",
        "glob-star",
        "glob-question",
        "glob-bracket",
    ],
)
def test_noncanonical_relative_path_rejected(value: str) -> None:
    api = _api()

    with pytest.raises(ValueError, match="repository path is invalid"):
        api.RepoPath.parse(value)


@pytest.mark.parametrize(
    "value",
    [
        "/etc/passwd",
        "\\\\server\\share\\file",
        "C:\\Windows\\system.ini",
        "C:/Windows/system.ini",
        "\\rooted",
    ],
    ids=["posix", "unc", "windows-backslash", "windows-drive", "rooted-backslash"],
)
def test_absolute_rejected(value: str) -> None:
    api = _api()

    with pytest.raises(ValueError, match="repository path is invalid"):
        api.RepoPath.parse(value)


@pytest.mark.parametrize(
    "value",
    ["../secret", "a/../../secret", "safe/../escape"],
    ids=["leading", "multi", "middle"],
)
def test_parent_rejected(value: str) -> None:
    api = _api()

    with pytest.raises(ValueError, match="repository path is invalid"):
        api.RepoPath.parse(value)


@pytest.mark.parametrize(
    "value",
    ["safe\x00name", "control\nname", "control\tname", "ｓｒｃ/file.py"],
    ids=["nul", "newline", "tab", "noncanonical-unicode"],
)
def test_nul_rejected(value: str) -> None:
    api = _api()

    with pytest.raises(ValueError, match="repository path is invalid") as exc_info:
        api.RepoPath.parse(value)

    assert value not in str(exc_info.value)


def test_string_prefix_is_not_containment(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    sibling = tmp_path / "repo-escape"
    root.mkdir()
    sibling.mkdir()
    (sibling / "secret.txt").write_text("secret\n", encoding="utf-8")
    (root / "link").symlink_to(sibling, target_is_directory=True)

    result = _inspect(root, "link/secret.txt")

    _assert_rejected(result)


@pytest.mark.parametrize("target_kind", ["relative-escape", "absolute"])
def test_symlink_escape(tmp_path: Path, target_kind: str) -> None:
    root = tmp_path / "repo"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("secret\n", encoding="utf-8")
    target = (
        Path("../outside/secret.txt")
        if target_kind == "relative-escape"
        else (outside / "secret.txt").resolve()
    )
    (root / "link.txt").symlink_to(target)

    result = _inspect(root, "link.txt")

    _assert_rejected(result)


def test_bounded_symlink(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    (root / "data" / "target.txt").write_text("bounded\n", encoding="utf-8")
    (root / "middle.txt").symlink_to("data/target.txt")
    (root / "entry.txt").symlink_to("middle.txt")

    entry = _assert_supported(_inspect(root, "entry.txt"))

    assert _enum_value(entry.kind) == "SYMLINK"
    assert entry.symlink_target == "middle.txt"
    assert entry.symlink_chain == ("entry.txt", "middle.txt", "data/target.txt")


@pytest.mark.parametrize(
    "case",
    ["dangling", "intermediate-directory", "loop"],
    ids=["dangling", "intermediate-directory", "loop"],
)
def test_unsafe_symlink_shapes_rejected(tmp_path: Path, case: str) -> None:
    root = tmp_path / "repo"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()

    if case == "dangling":
        (root / "entry.txt").symlink_to("missing.txt")
        relative = "entry.txt"
    elif case == "intermediate-directory":
        (outside / "secret.txt").write_text("secret\n", encoding="utf-8")
        (root / "linked-dir").symlink_to(outside, target_is_directory=True)
        relative = "linked-dir/secret.txt"
    else:
        (root / "first").symlink_to("second")
        (root / "second").symlink_to("first")
        relative = "first"

    _assert_rejected(_inspect(root, relative))


def test_executable_bit(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    script = root / "tool.sh"
    script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    script.chmod(0o755)

    entry = _assert_supported(_inspect(root, "tool.sh"))

    assert entry.executable is True
    assert _enum_value(entry.kind) == "REGULAR_FILE"


@pytest.mark.parametrize("kind", ["fifo", "socket"], ids=["fifo", "unix-socket"])
def test_special_file_rejected(tmp_path: Path, kind: str) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    target = root / "special"
    unix_socket: socket.socket | None = None
    if kind == "fifo":
        os.mkfifo(target)
    else:
        unix_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        unix_socket.bind(str(target))

    try:
        _assert_rejected(_inspect(root, "special"))
    finally:
        if unix_socket is not None:
            unix_socket.close()


@pytest.mark.parametrize(
    "mode",
    [stat.S_IFCHR | 0o600, stat.S_IFBLK | 0o600],
    ids=["character-device", "block-device"],
)
def test_controlled_device_mode_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: int,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    target = root / "device"
    target.write_bytes(b"fixture")
    api = _api()
    real_lstat = os.lstat

    def controlled_lstat(path: Path) -> os.stat_result:
        if path != target:
            return real_lstat(path)
        values = [0] * 10
        values[stat.ST_MODE] = mode
        values[stat.ST_SIZE] = 0
        return os.stat_result(values)

    monkeypatch.setattr(api.file_model, "_LSTAT", controlled_lstat)

    _assert_rejected(_inspect(root, "device"))


@pytest.mark.parametrize(
    "tracking",
    ["tracked", "untracked", "ignored"],
    ids=["tracked", "untracked", "ignored-excluded"],
)
def test_supported_tracking_states(tmp_path: Path, tracking: str) -> None:
    root = tmp_path / "repo"
    _init_repo(root)
    if tracking == "tracked":
        relative = "tracked.txt"
    elif tracking == "untracked":
        relative = "untracked.txt"
        (root / relative).write_text("untracked\n", encoding="utf-8")
    else:
        relative = "ignored.txt"
        (root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        (root / relative).write_text("ignored\n", encoding="utf-8")

    result = _inspect(root, relative)

    if tracking == "ignored":
        _assert_rejected(result)
    else:
        entry = _assert_supported(result)
        assert _enum_value(entry.tracking) == tracking.upper()


def test_supported_entry_identity_and_immutability(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    target = root / "entry.txt"
    target.write_text("first\n", encoding="utf-8")
    first = _assert_supported(_inspect(root, "entry.txt"))
    target.write_text("second\n", encoding="utf-8")
    second = _assert_supported(_inspect(root, "entry.txt"))

    assert first.file_identity == second.file_identity
    assert first.content_digest != second.content_digest
    assert first != second
    with pytest.raises((AttributeError, TypeError)):
        first.content_digest = second.content_digest
    with pytest.raises((AttributeError, TypeError)):
        first.symlink_chain += ("forged",)


def test_path_model_has_no_external_collection_alias() -> None:
    api = _api()
    source_segments = ["src", "module.py"]

    path = api.RepoPath.from_segments(source_segments)
    source_segments[0] = "forged"

    assert path.canonical == "src/module.py"
    assert path.segments == ("src", "module.py")


@pytest.mark.parametrize(
    "state",
    [
        "submodule",
        "git-lfs",
        "sparse-checkout",
        "nested-repository",
        "merge",
        "rebase",
        "cherry-pick",
        "bisect",
    ],
    ids=[
        "submodule",
        "git-lfs",
        "sparse-checkout",
        "nested-repository",
        "merge",
        "rebase",
        "cherry-pick",
        "bisect",
    ],
)
def test_unsupported_repo_state(tmp_path: Path, state: str) -> None:
    root = tmp_path / "repo"
    commit = _init_repo(root)
    git_dir = _git_dir(root)
    relative = "tracked.txt"

    if state == "submodule":
        _git(
            root,
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{commit},vendor/component",
        )
    elif state == "git-lfs":
        (root / ".gitattributes").write_text(
            "*.bin filter=lfs diff=lfs merge=lfs -text\n",
            encoding="utf-8",
        )
        (root / "asset.bin").write_text(
            "version https://git-lfs.github.com/spec/v1\n"
            "oid sha256:" + ("0" * 64) + "\nsize 1\n",
            encoding="utf-8",
        )
        relative = "asset.bin"
    elif state == "sparse-checkout":
        _git(root, "config", "core.sparseCheckout", "true")
        info = git_dir / "info"
        info.mkdir(exist_ok=True)
        (info / "sparse-checkout").write_text("/tracked.txt\n", encoding="utf-8")
    elif state == "nested-repository":
        nested = root / "nested"
        nested.mkdir()
        _git(nested, "init", "-q")
        (nested / "entry.txt").write_text("nested\n", encoding="utf-8")
        relative = "nested/entry.txt"
    elif state == "merge":
        (git_dir / "MERGE_HEAD").write_text(commit + "\n", encoding="ascii")
    elif state == "rebase":
        (git_dir / "rebase-merge").mkdir()
    elif state == "cherry-pick":
        (git_dir / "CHERRY_PICK_HEAD").write_text(commit + "\n", encoding="ascii")
    else:
        (git_dir / "BISECT_LOG").write_text("git bisect start\n", encoding="utf-8")

    _assert_rejected(_inspect(root, relative))


def test_per_operation_read_limit_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "large.bin").write_bytes(b"x" * 9)

    _assert_rejected(_inspect(root, "large.bin", max_bytes=8))


def test_approved_workspace_path_scope_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "allowed.txt").write_text("allowed\n", encoding="utf-8")
    (root / "other.txt").write_text("other\n", encoding="utf-8")
    api = _api()
    allowed = api.RepoPath.parse("allowed.txt")
    other = api.RepoPath.parse("other.txt")

    result = api.inspect_supported_entry(root, other, allowed_paths=(allowed,))

    _assert_rejected(result)


@pytest.mark.parametrize(
    "requirement",
    ["SEC-001", "ACT-004", "ACT-005", "ACT-006", "WS-013", "WS-014"],
    ids=["SEC-001", "ACT-004", "ACT-005", "ACT-006", "WS-013", "WS-014"],
)
def test_spec_requirement(requirement: str, tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    target = root / "entry.txt"
    target.write_text("content\n", encoding="utf-8")
    api = _api()

    if requirement == "SEC-001":
        class ForgedString(str):
            pass

        with pytest.raises(ValueError, match="repository path is invalid"):
            api.RepoPath.parse(ForgedString("entry.txt"))
    elif requirement == "ACT-004":
        path = api.RepoPath.parse("entry.txt")
        assert path.canonical == "entry.txt"
        _assert_supported(api.inspect_supported_entry(root, path))
    elif requirement == "ACT-005":
        _assert_rejected(_inspect(root, "entry.txt", max_bytes=1))
    elif requirement == "ACT-006":
        allowed = api.RepoPath.parse("allowed.txt")
        candidate = api.RepoPath.parse("entry.txt")
        _assert_rejected(
            api.inspect_supported_entry(
                root,
                candidate,
                allowed_paths=(allowed,),
            )
        )
    elif requirement == "WS-013":
        target.chmod(0o755)
        entry = _assert_supported(_inspect(root, "entry.txt"))
        assert entry.executable is True
    else:
        _init_repo(root)
        (_git_dir(root) / "MERGE_HEAD").write_text(
            _git(root, "rev-parse", "HEAD").stdout.strip() + "\n",
            encoding="ascii",
        )
        _assert_rejected(_inspect(root, "tracked.txt"))


def _linked_worktree(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    primary = tmp_path / "primary"
    _init_repo(primary)
    linked = tmp_path / "linked"
    _git(
        primary,
        "worktree",
        "add",
        "-q",
        "-b",
        "wp09-linked-fixture",
        str(linked),
    )
    marker = (linked / ".git").read_text(encoding="utf-8")
    assert marker.startswith("gitdir: ")
    worktree_git_dir = Path(marker.removeprefix("gitdir: ").strip())
    common_relative = (worktree_git_dir / "commondir").read_text(
        encoding="utf-8"
    ).strip()
    common_git_dir = (worktree_git_dir / common_relative).resolve()
    return primary, linked, worktree_git_dir, common_git_dir


def _fixture_manifest(root: Path) -> tuple[tuple[object, ...], ...]:
    records: list[tuple[object, ...]] = []
    for path in sorted(root.rglob("*")):
        metadata = os.lstat(path)
        relative = path.relative_to(root).as_posix()
        if stat.S_ISREG(metadata.st_mode):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        elif stat.S_ISLNK(metadata.st_mode):
            digest = os.readlink(path)
        else:
            digest = None
        records.append(
            (
                relative,
                metadata.st_mode,
                metadata.st_size,
                metadata.st_mtime_ns,
                digest,
            )
        )
    return tuple(records)


def _fake_git_program(
    tmp_path: Path,
    *,
    stream: str,
    payload_size: int = 0,
    other_stream_payload_size: int = 0,
    sleep_seconds: float = 0.0,
    completion_marker: Path | None = None,
    ignore_terminate: bool = False,
) -> Path:
    program = tmp_path / f"fake-git-{stream}.py"
    marker_statement = (
        "pathlib.Path(" + repr(str(completion_marker)) + ").write_text('done')"
        if completion_marker is not None
        else "pass"
    )
    file_descriptor = 1 if stream == "stdout" else 2
    other_file_descriptor = 2 if stream == "stdout" else 1
    ignore_statement = (
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        if ignore_terminate
        else ""
    )
    script = (
        "#!/usr/bin/python3\n"
        "import os\n"
        "import pathlib\n"
        "import signal\n"
        "import time\n"
        + ignore_statement
        + f"os.write({file_descriptor}, b'x' * {payload_size})\n"
        + f"os.write({other_file_descriptor}, b'y' * {other_stream_payload_size})\n"
        + f"time.sleep({sleep_seconds!r})\n"
        + f"{marker_statement}\n"
    )
    program.write_text(
        script,
        encoding="utf-8",
    )
    program.chmod(0o755)
    return program


@pytest.mark.parametrize(
    "target",
    [
        "dir/../target.txt",
        "dir/./target.txt",
        "/absolute/target.txt",
        "C:/target.txt",
        "\\\\server\\share\\target.txt",
        "dir\\target.txt",
        "control\nname",
        "target.txt/",
        "dir//target.txt",
        "a*",
        ":pathspec",
        "ｔａｒｇｅｔ.txt",
    ],
    ids=[
        "parent",
        "dot",
        "absolute",
        "drive",
        "unc",
        "backslash",
        "control",
        "trailing-separator",
        "repeated-separator",
        "glob",
        "pathspec",
        "nfkc",
    ],
)
def test_security_fix_symlink_target_uses_repo_path_lexical_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "target.txt").write_text("target\n", encoding="utf-8")
    link = root / "entry.txt"
    link.symlink_to("target.txt")
    api = _api()
    monkeypatch.setattr(api.file_model, "_READLINK", lambda _: target)

    result = _inspect(root, "entry.txt")

    _assert_rejected(result, "INVALID_SYMLINK_TARGET")


def test_security_fix_symlink_target_nul_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "target.txt").write_text("target\n", encoding="utf-8")
    (root / "entry.txt").symlink_to("target.txt")
    api = _api()
    monkeypatch.setattr(api.file_model, "_READLINK", lambda _: "nul\x00target")

    _assert_rejected(_inspect(root, "entry.txt"), "INVALID_SYMLINK_TARGET")


def test_security_fix_later_symlink_target_uses_lexical_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    (root / "dir").mkdir(parents=True)
    (root / "target.txt").write_text("target\n", encoding="utf-8")
    (root / "first").symlink_to("second")
    (root / "second").symlink_to("target.txt")
    api = _api()

    def controlled_readlink(path: Path) -> str:
        return "second" if path.name == "first" else "dir/../target.txt"

    monkeypatch.setattr(api.file_model, "_READLINK", controlled_readlink)

    _assert_rejected(_inspect(root, "first"), "INVALID_SYMLINK_TARGET")


def test_security_fix_symlink_does_not_inherit_target_executable(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    target = root / "tool.sh"
    target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    target.chmod(0o755)
    (root / "entry").symlink_to("tool.sh")

    target_entry = _assert_supported(_inspect(root, "tool.sh"))
    symlink_entry = _assert_supported(_inspect(root, "entry"))

    assert target_entry.executable is True
    assert _enum_value(target_entry.kind) == "REGULAR_FILE"
    assert symlink_entry.executable is False
    assert _enum_value(symlink_entry.kind) == "SYMLINK"


@pytest.mark.parametrize(
    "forged_mode",
    [stat.S_IFREG | 0o600, stat.S_IFIFO | 0o600, stat.S_IFCHR | 0o600],
    ids=["regular", "fifo", "device"],
)
def test_security_fix_public_lstat_injection_is_rejected(
    tmp_path: Path,
    forged_mode: int,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "entry").write_text("entry\n", encoding="utf-8")

    def forged_lstat(_: Path) -> os.stat_result:
        values = [0] * 10
        values[stat.ST_MODE] = forged_mode
        return os.stat_result(values)

    with pytest.raises(TypeError):
        _inspect(root, "entry", lstat=forged_lstat)


def test_security_fix_linked_worktree_regular_file_supported(
    tmp_path: Path,
) -> None:
    _, linked, _, _ = _linked_worktree(tmp_path)

    entry = _assert_supported(_inspect(linked, "tracked.txt"))

    assert _enum_value(entry.tracking) == "TRACKED"


@pytest.mark.parametrize(
    "state",
    ["operation-marker", "common-sparse-config", "common-lfs-attributes"],
    ids=["per-worktree-marker", "common-config", "common-info-attributes"],
)
def test_security_fix_linked_worktree_uses_correct_git_dirs(
    tmp_path: Path,
    state: str,
) -> None:
    primary, linked, worktree_git_dir, common_git_dir = _linked_worktree(tmp_path)
    if state == "operation-marker":
        commit = _git(primary, "rev-parse", "HEAD").stdout.strip()
        (worktree_git_dir / "MERGE_HEAD").write_text(commit + "\n", encoding="ascii")
    elif state == "common-sparse-config":
        _git(primary, "config", "core.sparseCheckout", "true")
    else:
        info = common_git_dir / "info"
        info.mkdir(exist_ok=True)
        (info / "attributes").write_text(
            "*.bin filter=lfs diff=lfs merge=lfs -text\n",
            encoding="utf-8",
        )

    _assert_rejected(_inspect(linked, "tracked.txt"), "UNSUPPORTED_REPOSITORY_STATE")


@pytest.mark.parametrize(
    "commondir",
    ["missing", "/tmp/wp09-forbidden-common-dir"],
    ids=["malformed", "absolute-escape"],
)
def test_security_fix_linked_worktree_invalid_commondir_fails_closed(
    tmp_path: Path,
    commondir: str,
) -> None:
    _, linked, worktree_git_dir, _ = _linked_worktree(tmp_path)
    (worktree_git_dir / "commondir").write_text(commondir + "\n", encoding="utf-8")

    _assert_rejected(_inspect(linked, "tracked.txt"), "UNSUPPORTED_REPOSITORY_STATE")


def test_security_fix_normal_repo_common_info_lfs_detected(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _init_repo(root)
    info = root / ".git" / "info"
    info.mkdir(exist_ok=True)
    (info / "attributes").write_text("*.txt filter=lfs\n", encoding="utf-8")

    _assert_rejected(_inspect(root, "tracked.txt"), "UNSUPPORTED_REPOSITORY_STATE")


@pytest.mark.parametrize("stream", ["stdout", "stderr"], ids=["stdout", "stderr"])
def test_security_fix_git_output_is_terminated_at_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stream: str,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    marker = tmp_path / f"{stream}-completed"
    program = _fake_git_program(
        tmp_path,
        stream=stream,
        payload_size=(64 * 1024) + 1,
        sleep_seconds=0.25,
        completion_marker=marker,
    )
    api = _api()
    monkeypatch.setattr(api.file_model, "_GIT_EXECUTABLE", str(program))

    result = api.file_model._run_git_read_only(root, ("probe",))

    assert result.valid is False
    assert marker.exists() is False
    assert len(result.output) <= 64 * 1024


def test_security_fix_git_timeout_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    marker = tmp_path / "timeout-completed"
    program = _fake_git_program(
        tmp_path,
        stream="stdout",
        sleep_seconds=5.0,
        completion_marker=marker,
    )
    api = _api()
    monkeypatch.setattr(api.file_model, "_GIT_EXECUTABLE", str(program))

    result = api.file_model._run_git_read_only(root, ("probe",))

    assert result.valid is False
    assert marker.exists() is False


def test_security_fix_git_startup_error_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    api = _api()
    monkeypatch.setattr(
        api.file_model,
        "_GIT_EXECUTABLE",
        str(tmp_path / "missing-git"),
    )

    result = api.file_model._run_git_read_only(root, ("probe",))

    assert result.valid is False
    assert result.output == b""


@pytest.mark.parametrize(
    "kind",
    ["git-marker", "config", "root-attributes", "info-attributes"],
    ids=["git-marker", "config", "root-attributes", "info-attributes"],
)
def test_security_fix_metadata_reads_are_bounded(
    tmp_path: Path,
    kind: str,
) -> None:
    root = tmp_path / "repo"
    if kind == "git-marker":
        root.mkdir()
        metadata = root / ".git"
    else:
        _init_repo(root)
        if kind == "config":
            metadata = root / ".git" / "config"
        elif kind == "root-attributes":
            metadata = root / ".gitattributes"
        else:
            metadata = root / ".git" / "info" / "attributes"
    metadata.parent.mkdir(parents=True, exist_ok=True)
    metadata.write_bytes(b"x" * ((64 * 1024) + 1))
    api = _api()

    assert api.file_model._read_bounded_metadata(metadata, 64 * 1024) is None
    _assert_rejected(_inspect(root, "tracked.txt" if kind != "git-marker" else "x"))


def test_security_fix_metadata_symlink_is_not_followed(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _init_repo(root)
    outside = tmp_path / "outside-attributes"
    outside.write_text("ordinary metadata\n", encoding="utf-8")
    (root / ".gitattributes").symlink_to(outside)
    api = _api()

    assert api.file_model._read_bounded_metadata(
        root / ".gitattributes",
        64 * 1024,
    ) is None
    _assert_rejected(_inspect(root, "tracked.txt"), "UNSUPPORTED_REPOSITORY_STATE")


@pytest.mark.parametrize(
    ("size", "limit", "supported"),
    [(4, 4, True), (5, 4, False)],
    ids=["at-boundary", "over-boundary"],
)
def test_security_fix_single_file_limit_boundary(
    tmp_path: Path,
    size: int,
    limit: int,
    supported: bool,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "entry").write_bytes(b"x" * size)

    result = _inspect(root, "entry", max_bytes=limit)

    if supported:
        entry = _assert_supported(result)
        assert entry.count_contribution == 1
        assert entry.byte_contribution == size
    else:
        _assert_rejected(result)
        assert result.count_contribution == 0
        assert result.byte_contribution == 0


def test_security_fix_contributions_are_additive_across_split_inspection(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "first").write_bytes(b"1234")
    (root / "second").write_bytes(b"5678")

    entries = [
        _assert_supported(_inspect(root, relative))
        for relative in ("first", "second")
    ]

    assert sum(entry.count_contribution for entry in entries) == 2
    assert sum(entry.byte_contribution for entry in entries) == 8
    assert sum(entry.byte_contribution for entry in entries) > 7


def test_security_fix_symlink_contribution_counts_content_not_metadata(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "target").write_bytes(b"12345")
    (root / "entry").symlink_to("target")

    entry = _assert_supported(_inspect(root, "entry"))

    assert entry.count_contribution == 1
    assert entry.byte_contribution == 5


@pytest.mark.parametrize(
    "limit",
    [True, -1, 1.5, "1"],
    ids=["bool", "negative", "float", "string"],
)
def test_security_fix_invalid_limit_fails_closed(
    tmp_path: Path,
    limit: object,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "entry").write_text("entry\n", encoding="utf-8")

    result = _inspect(root, "entry", max_bytes=limit)

    _assert_rejected(result, "INVALID_INSPECTION_INPUT")
    assert result.count_contribution == 0
    assert result.byte_contribution == 0


def test_security_fix_symlink_self_loop_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "entry").symlink_to("entry")

    _assert_rejected(_inspect(root, "entry"))


def test_security_fix_symlink_multihop_escape_rejected(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "secret").write_text("secret\n", encoding="utf-8")
    (root / "first").symlink_to("second")
    (root / "second").symlink_to("../outside/secret")

    _assert_rejected(_inspect(root, "first"))


@pytest.mark.parametrize(
    ("depth", "supported"),
    [(40, True), (41, False)],
    ids=["depth-40", "depth-41"],
)
def test_security_fix_symlink_depth_boundary(
    tmp_path: Path,
    depth: int,
    supported: bool,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "target").write_text("target\n", encoding="utf-8")
    for index in reversed(range(depth)):
        target = "target" if index == depth - 1 else f"link-{index + 1}"
        (root / f"link-{index}").symlink_to(target)

    result = _inspect(root, "link-0")

    if supported:
        _assert_supported(result)
    else:
        _assert_rejected(result)


def test_security_fix_symlink_root_fails_closed(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    (actual / "entry").write_text("entry\n", encoding="utf-8")
    root = tmp_path / "repo"
    root.symlink_to(actual, target_is_directory=True)

    _assert_rejected(_inspect(root, "entry"), "INVALID_ROOT")


def test_security_fix_inspection_is_read_only_and_marks_snapshot(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    _init_repo(root)
    before = _fixture_manifest(root)

    result = _inspect(root, "tracked.txt")

    entry = _assert_supported(result)
    assert result.requires_use_time_revalidation is True
    assert entry.requires_use_time_revalidation is True
    assert _fixture_manifest(root) == before


@pytest.mark.parametrize(
    ("location", "payload"),
    [
        ("root", b"\xff invalid"),
        ("common", b"\xff invalid"),
        ("root", b"*.bin filter=lfs \xff"),
    ],
    ids=["root", "common-info", "lfs-bytes-plus-invalid"],
)
def test_security_fix2_invalid_utf8_attributes_fail_closed(
    tmp_path: Path,
    location: str,
    payload: bytes,
) -> None:
    root = tmp_path / "repo"
    if location == "common":
        _init_repo(root)
        attributes = root / ".git" / "info" / "attributes"
        relative = "tracked.txt"
    else:
        root.mkdir()
        (root / "entry").write_bytes(b"entry")
        attributes = root / ".gitattributes"
        relative = "entry"
    attributes.parent.mkdir(parents=True, exist_ok=True)
    attributes.write_bytes(payload)

    result = _inspect(root, relative)

    _assert_rejected(result, "UNSUPPORTED_REPOSITORY_STATE")
    assert payload.hex() not in result.detail


@pytest.mark.parametrize(
    ("location", "uses_lfs"),
    [
        ("root", True),
        ("root", False),
        ("common", True),
        ("common", False),
    ],
    ids=["root-lfs", "root-ordinary", "common-lfs", "common-ordinary"],
)
def test_security_fix2_valid_utf8_attributes_are_parsed(
    tmp_path: Path,
    location: str,
    uses_lfs: bool,
) -> None:
    root = tmp_path / "repo"
    if location == "common":
        _init_repo(root)
        attributes = root / ".git" / "info" / "attributes"
        relative = "tracked.txt"
    else:
        root.mkdir()
        (root / "entry").write_bytes(b"entry")
        attributes = root / ".gitattributes"
        relative = "entry"
    attributes.parent.mkdir(parents=True, exist_ok=True)
    attributes.write_text(
        "*.bin filter=lfs diff=lfs\n" if uses_lfs else "*.txt text\n",
        encoding="utf-8",
    )

    result = _inspect(root, relative)

    if uses_lfs:
        _assert_rejected(result, "UNSUPPORTED_REPOSITORY_STATE")
    else:
        _assert_supported(result)


@pytest.mark.parametrize(
    ("stream", "payload_size", "valid"),
    [
        ("stdout", 64 * 1024, True),
        ("stdout", (64 * 1024) + 1, False),
        ("stderr", 64 * 1024, True),
        ("stderr", (64 * 1024) + 1, False),
    ],
    ids=["stdout-exact", "stdout-over", "stderr-exact", "stderr-over"],
)
def test_security_fix2_git_stream_precise_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stream: str,
    payload_size: int,
    valid: bool,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    program = _fake_git_program(tmp_path, stream=stream, payload_size=payload_size)
    api = _api()
    monkeypatch.setattr(api.file_model, "_GIT_EXECUTABLE", str(program))

    result = api.file_model._run_git_read_only(root, ("probe",))

    assert result.valid is valid
    retained = (
        result.max_output_bytes_retained
        if stream == "stdout"
        else result.max_error_bytes_retained
    )
    assert retained == payload_size
    assert retained <= (64 * 1024) + 1
    assert result.reaped is True
    if valid:
        assert result.failure_reason is None
    else:
        assert result.failure_reason == "GIT_OUTPUT_LIMIT"


def test_security_fix2_pipe_read_never_retains_more_than_limit_plus_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    program = _fake_git_program(
        tmp_path,
        stream="stdout",
        payload_size=(64 * 1024) + 8192,
    )
    api = _api()
    monkeypatch.setattr(api.file_model, "_GIT_EXECUTABLE", str(program))

    result = api.file_model._run_git_read_only(root, ("probe",))

    assert result.valid is False
    assert result.max_output_bytes_retained == (64 * 1024) + 1
    assert result.reaped is True


def test_security_fix2_git_drains_both_streams_near_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    program = _fake_git_program(
        tmp_path,
        stream="stdout",
        payload_size=64 * 1024,
        other_stream_payload_size=64 * 1024,
    )
    api = _api()
    monkeypatch.setattr(api.file_model, "_GIT_EXECUTABLE", str(program))

    result = api.file_model._run_git_read_only(root, ("probe",))

    assert result.valid is True
    assert result.max_output_bytes_retained == 64 * 1024
    assert result.max_error_bytes_retained == 64 * 1024
    assert result.reaped is True


@pytest.mark.parametrize(
    "failure",
    ["timeout", "overflow"],
    ids=["timeout", "overflow"],
)
def test_security_fix2_failed_git_child_is_reaped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    program = _fake_git_program(
        tmp_path,
        stream="stdout",
        payload_size=(64 * 1024) + 1 if failure == "overflow" else 0,
        sleep_seconds=5.0 if failure == "timeout" else 0.25,
    )
    api = _api()
    monkeypatch.setattr(api.file_model, "_GIT_EXECUTABLE", str(program))

    result = api.file_model._run_git_read_only(root, ("probe",))

    assert result.valid is False
    assert result.reaped is True
    assert result.cleanup_failure_reason is None
    assert result.failure_reason == (
        "GIT_TIMEOUT" if failure == "timeout" else "GIT_OUTPUT_LIMIT"
    )


def test_security_fix2_child_ignoring_terminate_is_killed_and_reaped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    program = _fake_git_program(
        tmp_path,
        stream="stdout",
        sleep_seconds=5.0,
        ignore_terminate=True,
    )
    api = _api()
    monkeypatch.setattr(api.file_model, "_GIT_EXECUTABLE", str(program))

    result = api.file_model._run_git_read_only(root, ("probe",))

    assert result.valid is False
    assert result.failure_reason == "GIT_TIMEOUT"
    assert result.cleanup_failure_reason is None
    assert result.reaped is True
    assert result.returncode == -signal.SIGKILL


def test_security_fix2_finalize_escalates_and_waits_again() -> None:
    api = _api()

    class Process:
        returncode: int | None = None

        def __init__(self) -> None:
            self.events: list[str] = []
            self.wait_calls = 0

        def poll(self) -> None:
            self.events.append("poll")
            return None

        def terminate(self) -> None:
            self.events.append("terminate")

        def kill(self) -> None:
            self.events.append("kill")

        def wait(self, timeout: float) -> int:
            self.events.append("wait")
            self.wait_calls += 1
            if self.wait_calls == 1:
                raise subprocess.TimeoutExpired("git", timeout)
            self.returncode = -signal.SIGKILL
            return self.returncode

    process = Process()
    cleanup = api.file_model._finalize_process(process)

    assert process.events == ["poll", "terminate", "wait", "kill", "wait"]
    assert cleanup.reaped is True
    assert cleanup.failure_reason is None
    assert cleanup.returncode == -signal.SIGKILL


def test_security_fix2_finalize_reports_reap_failure() -> None:
    api = _api()

    class Process:
        returncode: int | None = None

        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            return None

        def kill(self) -> None:
            return None

        def wait(self, timeout: float) -> int:
            raise subprocess.TimeoutExpired("git", timeout)

    cleanup = api.file_model._finalize_process(Process())

    assert cleanup.reaped is False
    assert cleanup.failure_reason == "GIT_REAP_FAILURE"
    assert cleanup.returncode is None


def test_security_fix2_finalize_records_terminate_cleanup_error() -> None:
    api = _api()

    class Process:
        returncode: int | None = None

        def __init__(self) -> None:
            self.events: list[str] = []

        def poll(self) -> None:
            self.events.append("poll")
            return None

        def terminate(self) -> None:
            self.events.append("terminate")
            raise OSError("terminate-secret")

        def kill(self) -> None:
            self.events.append("kill")

        def wait(self, timeout: float) -> int:
            self.events.append("wait")
            self.returncode = -signal.SIGKILL
            return self.returncode

    process = Process()
    cleanup = api.file_model._finalize_process(process)

    assert process.events == ["poll", "terminate", "kill", "wait"]
    assert cleanup.reaped is True
    assert cleanup.failure_reason == "GIT_CLEANUP_ERROR"
    assert cleanup.returncode == -signal.SIGKILL
    assert "terminate-secret" not in repr(cleanup)


@pytest.mark.parametrize(
    "final_wait_succeeds",
    [True, False],
    ids=["final-wait-succeeds", "final-wait-fails"],
)
def test_reap_fix_kill_error_still_performs_final_wait(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    final_wait_succeeds: bool,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    api = _api()

    class Stream:
        def __init__(self, descriptor: int) -> None:
            self.descriptor = descriptor
            self.closed = False

        def fileno(self) -> int:
            return self.descriptor

        def close(self) -> None:
            self.closed = True

    class Process:
        def __init__(self) -> None:
            self.stdout = Stream(100)
            self.stderr = Stream(101)
            self.events: list[str] = []
            self.wait_calls = 0

        def poll(self) -> None:
            self.events.append("poll")
            return None

        def terminate(self) -> None:
            self.events.append("terminate")

        def kill(self) -> None:
            self.events.append("kill")
            raise OSError("kill-secret")

        def wait(self, timeout: float) -> int:
            self.events.append("wait")
            self.wait_calls += 1
            if self.wait_calls == 1:
                raise subprocess.TimeoutExpired("git", timeout)
            if not final_wait_succeeds:
                raise OSError("wait-secret")
            return -signal.SIGKILL

    class TimeoutSelector:
        def register(self, *_args: object) -> None:
            return None

        def get_map(self) -> dict[str, bool]:
            return {"open": True}

        def select(self, _timeout: float) -> list[object]:
            return []

        def close(self) -> None:
            return None

    process = Process()
    monkeypatch.setattr(
        api.file_model.subprocess,
        "Popen",
        lambda *_args, **_kwargs: process,
    )
    monkeypatch.setattr(
        api.file_model.selectors,
        "DefaultSelector",
        TimeoutSelector,
    )

    result = api.file_model._run_git_read_only(root, ("probe",))

    assert process.events == ["poll", "terminate", "wait", "kill", "wait"]
    assert result.failure_reason == "GIT_TIMEOUT"
    assert result.reaped is final_wait_succeeds
    if final_wait_succeeds:
        assert result.returncode == -signal.SIGKILL
        assert result.cleanup_failure_reason == "GIT_KILL_FAILURE"
    else:
        assert result.returncode == -1
        assert result.cleanup_failure_reason == "GIT_REAP_FAILURE"
    assert "kill-secret" not in repr(result)
    assert "wait-secret" not in repr(result)


def test_security_fix2_stream_close_failure_is_recorded() -> None:
    api = _api()

    class Stream:
        def close(self) -> None:
            raise OSError("close-secret")

    reason = api.file_model._close_streams((Stream(),))

    assert reason == "GIT_STREAM_CLOSE_FAILURE"
    assert "close-secret" not in reason


def test_security_fix2_git_read_error_is_fail_closed_and_reaped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    program = _fake_git_program(tmp_path, stream="stdout", payload_size=1)
    api = _api()
    monkeypatch.setattr(api.file_model, "_GIT_EXECUTABLE", str(program))
    monkeypatch.setattr(
        api.file_model,
        "_PIPE_READ",
        lambda _descriptor, _size: (_ for _ in ()).throw(OSError("secret")),
    )

    result = api.file_model._run_git_read_only(root, ("probe",))

    assert result.valid is False
    assert result.failure_reason == "GIT_READ_ERROR"
    assert result.cleanup_failure_reason is None
    assert result.reaped is True
    assert "secret" not in repr(result)


def test_security_fix2_git_selector_error_is_fail_closed_and_reaped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    program = _fake_git_program(tmp_path, stream="stdout", payload_size=1)
    api = _api()
    real_selector = api.file_model.selectors.DefaultSelector

    class ExplodingSelector:
        def __init__(self) -> None:
            self.inner = real_selector()

        def register(self, *args: object) -> object:
            return self.inner.register(*args)

        def get_map(self) -> object:
            return self.inner.get_map()

        def select(self, _timeout: float) -> object:
            raise OSError("selector-secret")

        def close(self) -> None:
            self.inner.close()

    monkeypatch.setattr(api.file_model, "_GIT_EXECUTABLE", str(program))
    monkeypatch.setattr(
        api.file_model.selectors,
        "DefaultSelector",
        ExplodingSelector,
    )

    result = api.file_model._run_git_read_only(root, ("probe",))

    assert result.valid is False
    assert result.failure_reason == "GIT_SELECTOR_ERROR"
    assert result.cleanup_failure_reason is None
    assert result.reaped is True
    assert "selector-secret" not in repr(result)


def test_security_fix2_contribution_contract_accepts_arbitrary_precision_int(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "entry").write_bytes(b"entry")
    api = _api()

    result = _inspect(root, "entry", max_bytes=2**100)
    entry = _assert_supported(result)
    huge = api.SupportedEntry(
        path=entry.path,
        file_identity=entry.file_identity,
        content_digest=entry.content_digest,
        metadata_digest=entry.metadata_digest,
        baseline_digest=entry.baseline_digest,
        kind=entry.kind,
        tracking=entry.tracking,
        executable=entry.executable,
        size=2**100,
        count_contribution=1,
        byte_contribution=2**100,
        symlink_target=entry.symlink_target,
        symlink_chain=entry.symlink_chain,
    )

    assert huge.byte_contribution == 2**100
    assert hasattr(api.file_model, "_MAX_COUNTER_VALUE") is False
    assert result.count_contribution == 1
    assert result.byte_contribution == len(b"entry")
    assert hasattr(result, "configured_limit_passed") is False
    with pytest.raises((AttributeError, TypeError)):
        huge.byte_contribution = 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("size", -1),
        ("size", True),
        ("size", 1.5),
        ("size", "1"),
        ("count_contribution", -1),
        ("count_contribution", True),
        ("count_contribution", 1.5),
        ("count_contribution", "1"),
        ("byte_contribution", -1),
        ("byte_contribution", True),
        ("byte_contribution", 1.5),
        ("byte_contribution", "1"),
    ],
    ids=[
        "size-negative",
        "size-bool",
        "size-float",
        "size-string",
        "count-negative",
        "count-bool",
        "count-float",
        "count-string",
        "bytes-negative",
        "bytes-bool",
        "bytes-float",
        "bytes-string",
    ],
)
def test_security_fix2_contribution_model_rejects_invalid_values(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "entry").write_bytes(b"entry")
    api = _api()
    entry = _assert_supported(_inspect(root, "entry"))
    values = {
        "path": entry.path,
        "file_identity": entry.file_identity,
        "content_digest": entry.content_digest,
        "metadata_digest": entry.metadata_digest,
        "baseline_digest": entry.baseline_digest,
        "kind": entry.kind,
        "tracking": entry.tracking,
        "executable": entry.executable,
        "size": entry.size,
        "count_contribution": entry.count_contribution,
        "byte_contribution": entry.byte_contribution,
        "symlink_target": entry.symlink_target,
        "symlink_chain": entry.symlink_chain,
    }
    values[field] = value

    with pytest.raises(ValueError, match="supported entry is invalid"):
        api.SupportedEntry(**values)


def test_security_fix2_rejected_result_uses_zero_contribution_and_is_immutable(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    result = _inspect(root, "missing")

    _assert_rejected(result)
    assert result.count_contribution == 0
    assert result.byte_contribution == 0
    with pytest.raises((AttributeError, TypeError)):
        result.count_contribution = 1


def test_security_fix2_caller_cannot_declare_inspection_contribution(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "entry").write_bytes(b"entry")

    with pytest.raises(TypeError):
        _inspect(
            root,
            "entry",
            count_contribution=0,
            byte_contribution=0,
            safe=True,
            approved=True,
        )
