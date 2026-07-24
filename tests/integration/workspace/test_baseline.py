"""WP-10 Baseline Manifest and Task Workspace contract tests.

All repositories and workspaces are isolated below pytest's ``tmp_path``.
Production imports are deliberately deferred until each test body so the
pre-implementation suite collects successfully and fails Red at the missing
WP-10 API boundary.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import importlib
import os
from pathlib import Path
import stat
import subprocess
from types import SimpleNamespace

import pytest


_DIGEST_LENGTH = 64
_EXPECTED_CONTENTS = {
    "clean.txt": b"clean\n",
    "mixed.txt": b"mixed-unstaged-user\n",
    "staged.txt": b"staged-user\n",
    "unstaged.txt": b"unstaged-user\n",
    "untracked.txt": b"untracked-user\n",
}


def _api() -> SimpleNamespace:
    try:
        manifest = importlib.import_module("coding_harness.workspace.manifest")
        materialize = importlib.import_module("coding_harness.workspace.materialize")
    except ModuleNotFoundError as exc:
        if exc.name in {
            "coding_harness.workspace.manifest",
            "coding_harness.workspace.materialize",
        }:
            pytest.fail("WP-10 production API is not implemented", pytrace=False)
        raise

    required = {
        "BaselineManifest": getattr(manifest, "BaselineManifest", None),
        "build_baseline": getattr(manifest, "build_baseline", None),
        "TaskWorkspace": getattr(materialize, "TaskWorkspace", None),
        "materialize_workspace": getattr(
            materialize,
            "materialize_workspace",
            None,
        ),
    }
    missing = tuple(name for name, value in required.items() if value is None)
    if missing:
        pytest.fail(
            "WP-10 production API is not implemented: " + ", ".join(missing),
            pytrace=False,
        )
    return SimpleNamespace(**required)


def _git(repo: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    git_home = repo.parent / ".git-test-home"
    git_home.mkdir(exist_ok=True)
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "HOME": str(git_home),
        }
    )
    return subprocess.run(
        ["git", *arguments],
        cwd=repo,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def _git_dir(repo: Path) -> Path:
    raw = _git(repo, "rev-parse", "--git-dir").stdout.strip()
    path = Path(raw)
    return path if path.is_absolute() else repo / path


def _make_user_state_repository(tmp_path: Path) -> Path:
    root = tmp_path / "origin"
    root.mkdir()
    _git(root, "init", "-q")
    initial = {
        "clean.txt": "clean\n",
        "mixed.txt": "mixed-base\n",
        "staged.txt": "staged-base\n",
        "unstaged.txt": "unstaged-base\n",
    }
    for relative, content in initial.items():
        (root / relative).write_text(content, encoding="utf-8")
    _git(root, "add", "--", *sorted(initial))
    _git(
        root,
        "-c",
        "user.name=WP10 Test",
        "-c",
        "user.email=wp10@example.invalid",
        "commit",
        "-q",
        "-m",
        "fixture baseline",
    )

    (root / "staged.txt").write_text("staged-user\n", encoding="utf-8")
    _git(root, "add", "--", "staged.txt")
    (root / "unstaged.txt").write_text("unstaged-user\n", encoding="utf-8")
    (root / "mixed.txt").write_text("mixed-staged-user\n", encoding="utf-8")
    _git(root, "add", "--", "mixed.txt")
    (root / "mixed.txt").write_text(
        "mixed-unstaged-user\n",
        encoding="utf-8",
    )
    (root / "untracked.txt").write_text("untracked-user\n", encoding="utf-8")
    return root


def _tree_snapshot(root: Path) -> dict[str, tuple[str, bytes | str, int]]:
    snapshot: dict[str, tuple[str, bytes | str, int]] = {}
    for current, directories, filenames in os.walk(root, followlinks=False):
        if Path(current) == root and ".git" in directories:
            directories.remove(".git")
        for name in sorted(filenames):
            path = Path(current) / name
            relative = path.relative_to(root).as_posix()
            mode = os.lstat(path).st_mode
            if stat.S_ISLNK(mode):
                snapshot[relative] = ("symlink", os.readlink(path), mode)
            else:
                snapshot[relative] = ("file", path.read_bytes(), mode)
    return snapshot


def _origin_snapshot(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        tree=_tree_snapshot(root),
        status=_git(
            root,
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
        ).stdout,
        index=(_git_dir(root) / "index").read_bytes(),
        head=_git(root, "rev-parse", "HEAD").stdout.strip(),
        branch=_git(root, "branch", "--show-current").stdout.strip(),
    )


def _assert_origin_unchanged(root: Path, before: SimpleNamespace) -> None:
    after = _origin_snapshot(root)
    assert after.tree == before.tree
    assert after.status == before.status
    assert after.index == before.index
    assert after.head == before.head
    assert after.branch == before.branch


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def _assert_digest(value: object) -> None:
    assert type(value) is str
    assert len(value) == _DIGEST_LENGTH
    assert all(character in "0123456789abcdef" for character in value)


def _entries_by_path(manifest: object) -> dict[str, object]:
    assert type(manifest.entries) is tuple
    entries: dict[str, object] = {}
    for entry in manifest.entries:
        canonical = entry.path.canonical
        assert canonical not in entries
        assert type(entry.content) is bytes
        _assert_digest(entry.content_digest)
        _assert_digest(entry.metadata_digest)
        entries[canonical] = entry
    return entries


def _assert_manifest_user_state(manifest: object) -> dict[str, object]:
    entries = _entries_by_path(manifest)
    assert set(entries) == set(_EXPECTED_CONTENTS)
    for relative, content in _EXPECTED_CONTENTS.items():
        entry = entries[relative]
        assert entry.content == content
        assert entry.content_digest == hashlib.sha256(content).hexdigest()
        assert _enum_value(entry.kind) == "REGULAR_FILE"
        assert entry.executable is False
    assert _enum_value(entries["untracked.txt"].tracking) == "UNTRACKED"
    for relative in set(entries) - {"untracked.txt"}:
        assert _enum_value(entries[relative].tracking) == "TRACKED"
    _assert_digest(manifest.digest)
    return entries


def _materialize(api: SimpleNamespace, manifest: object, destination: Path) -> object:
    workspace = api.materialize_workspace(manifest, destination)
    assert type(workspace) is api.TaskWorkspace
    assert workspace.root == destination
    assert workspace.baseline_digest == manifest.digest
    return workspace


def _assert_workspace_matches_manifest(
    workspace_root: Path,
    manifest: object,
) -> None:
    entries = _entries_by_path(manifest)
    assert set(_tree_snapshot(workspace_root)) == set(entries)
    for relative, entry in entries.items():
        path = workspace_root / relative
        assert path.read_bytes() == entry.content
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry.content_digest


def _assert_git_not_present(workspace_root: Path) -> None:
    assert not os.path.lexists(workspace_root / ".git")
    assert not any(path.name == ".git" for path in workspace_root.rglob("*"))


def test_baseline_includes_user_state(tmp_path: Path) -> None:
    api = _api()
    origin = _make_user_state_repository(tmp_path)

    manifest = api.build_baseline(origin)

    assert type(manifest) is api.BaselineManifest
    _assert_manifest_user_state(manifest)


def test_user_changes_not_agent(tmp_path: Path) -> None:
    api = _api()
    origin = _make_user_state_repository(tmp_path)
    manifest = api.build_baseline(origin)
    destination = tmp_path / "workspace"

    workspace = _materialize(api, manifest, destination)

    _assert_manifest_user_state(manifest)
    _assert_workspace_matches_manifest(workspace.root, manifest)


def test_manifest_immutable(tmp_path: Path) -> None:
    api = _api()
    origin = _make_user_state_repository(tmp_path)
    manifest = api.build_baseline(origin)
    entries = _assert_manifest_user_state(manifest)
    repeated = api.build_baseline(origin)
    original_content = entries["clean.txt"].content

    assert repeated.digest == manifest.digest
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        manifest.digest = "0" * _DIGEST_LENGTH
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        manifest.entries = ()
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        entries["clean.txt"].content = b"forged"

    (origin / "clean.txt").write_text("later-user-change\n", encoding="utf-8")
    assert entries["clean.txt"].content == original_content


def test_workspace_independent(tmp_path: Path) -> None:
    api = _api()
    origin = _make_user_state_repository(tmp_path)
    manifest = api.build_baseline(origin)
    workspace = _materialize(api, manifest, tmp_path / "workspace")

    origin_stat = os.stat(origin / "clean.txt")
    workspace_stat = os.stat(workspace.root / "clean.txt")
    assert (origin_stat.st_dev, origin_stat.st_ino) != (
        workspace_stat.st_dev,
        workspace_stat.st_ino,
    )

    (workspace.root / "clean.txt").write_text("agent-change\n", encoding="utf-8")
    assert (origin / "clean.txt").read_bytes() == b"clean\n"
    assert _entries_by_path(manifest)["clean.txt"].content == b"clean\n"


def test_workspace_only_writes(tmp_path: Path) -> None:
    api = _api()
    origin = _make_user_state_repository(tmp_path)
    before = _origin_snapshot(origin)
    manifest = api.build_baseline(origin)
    workspace = _materialize(api, manifest, tmp_path / "workspace")

    (workspace.root / "agent-created.txt").write_text(
        "workspace-only\n",
        encoding="utf-8",
    )
    (workspace.root / "staged.txt").write_text(
        "workspace-modified\n",
        encoding="utf-8",
    )

    assert (workspace.root / "agent-created.txt").is_file()
    assert not (origin / "agent-created.txt").exists()
    assert (origin / "staged.txt").read_bytes() == b"staged-user\n"
    _assert_origin_unchanged(origin, before)


def test_origin_unchanged(tmp_path: Path) -> None:
    api = _api()
    origin = _make_user_state_repository(tmp_path)
    before = _origin_snapshot(origin)

    manifest = api.build_baseline(origin)
    _materialize(api, manifest, tmp_path / "workspace")

    _assert_origin_unchanged(origin, before)


def test_git_not_copied(tmp_path: Path) -> None:
    api = _api()
    origin = _make_user_state_repository(tmp_path)
    manifest = api.build_baseline(origin)

    workspace = _materialize(api, manifest, tmp_path / "workspace")

    _assert_git_not_present(workspace.root)


def test_index_unchanged(tmp_path: Path) -> None:
    api = _api()
    origin = _make_user_state_repository(tmp_path)
    index_before = (_git_dir(origin) / "index").read_bytes()
    status_before = _origin_snapshot(origin).status

    manifest = api.build_baseline(origin)
    _materialize(api, manifest, tmp_path / "workspace")

    assert (_git_dir(origin) / "index").read_bytes() == index_before
    assert _origin_snapshot(origin).status == status_before


def test_head_metadata_only(tmp_path: Path) -> None:
    api = _api()
    origin = _make_user_state_repository(tmp_path)
    before = _origin_snapshot(origin)
    manifest = api.build_baseline(origin)

    workspace = _materialize(api, manifest, tmp_path / "workspace")

    assert manifest.source_head == before.head
    assert manifest.source_branch == before.branch
    assert workspace.source_head == before.head
    assert workspace.source_branch == before.branch
    _assert_git_not_present(workspace.root)
    _assert_origin_unchanged(origin, before)


def test_git_routing_environment_isolated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = _api()
    origin_parent = tmp_path / "trusted"
    origin_parent.mkdir()
    origin = _make_user_state_repository(origin_parent)
    origin_head = _git(origin, "rev-parse", "HEAD").stdout.strip()
    decoy_parent = tmp_path / "decoy"
    decoy_parent.mkdir()
    decoy = _make_user_state_repository(decoy_parent)
    (decoy / "clean.txt").write_text("decoy\n", encoding="utf-8")
    _git(decoy, "add", "--", "clean.txt")
    _git(
        decoy,
        "-c",
        "user.name=WP10 Test",
        "-c",
        "user.email=wp10@example.invalid",
        "commit",
        "-q",
        "-m",
        "decoy state",
    )
    monkeypatch.setenv("GIT_DIR", str(_git_dir(decoy)))
    monkeypatch.setenv("GIT_WORK_TREE", str(decoy))
    monkeypatch.setenv("GIT_INDEX_FILE", str(_git_dir(decoy) / "index"))

    manifest = api.build_baseline(origin)

    assert manifest.source_head == origin_head
    _assert_manifest_user_state(manifest)


def test_snapshot_path_set_change_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_module = importlib.import_module("coding_harness.workspace.manifest")
    origin = _make_user_state_repository(tmp_path)
    original_capture = manifest_module._capture_entry
    changed = False

    def capture_and_change(root: Path, path: object, state: object) -> object:
        nonlocal changed
        entry = original_capture(root, path, state)
        if not changed:
            changed = True
            (origin / "late-user-file.txt").write_text(
                "appeared-during-baseline\n",
                encoding="utf-8",
            )
        return entry

    monkeypatch.setattr(manifest_module, "_capture_entry", capture_and_change)

    with pytest.raises(ValueError, match="baseline construction failed"):
        manifest_module.build_baseline(origin)


def test_manifest_binds_git_start_state(tmp_path: Path) -> None:
    api = _api()
    origin = _make_user_state_repository(tmp_path)

    manifest = api.build_baseline(origin)
    entries = _entries_by_path(manifest)
    workspace = _materialize(api, manifest, tmp_path / "workspace")

    expected_index = _git(origin, "ls-files", "--stage", "-z").stdout.encode()
    expected_status = _git(
        origin,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ).stdout.encode()
    assert manifest.source_index_digest == hashlib.sha256(expected_index).hexdigest()
    assert manifest.source_status_digest == hashlib.sha256(expected_status).hexdigest()
    assert workspace.source_index_digest == manifest.source_index_digest
    assert workspace.source_status_digest == manifest.source_status_digest
    assert {
        relative: _enum_value(entry.state)
        for relative, entry in entries.items()
    } == {
        "clean.txt": "TRACKED_CLEAN",
        "mixed.txt": "TRACKED_MIXED",
        "staged.txt": "TRACKED_STAGED",
        "unstaged.txt": "TRACKED_UNSTAGED",
        "untracked.txt": "UNTRACKED",
    }


def test_git_output_limit_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_module = importlib.import_module("coding_harness.workspace.manifest")
    origin = _make_user_state_repository(tmp_path)
    monkeypatch.setattr(
        manifest_module,
        "_MAX_GIT_OUTPUT_BYTES",
        64,
        raising=False,
    )

    with pytest.raises(ValueError, match="baseline construction failed"):
        manifest_module.build_baseline(origin)


@pytest.mark.parametrize(
    "requirement_id",
    ["WS-001", "WS-006", "WS-007", "WS-008", "WS-009"],
)
def test_spec_requirement(requirement_id: str, tmp_path: Path) -> None:
    api = _api()
    origin = _make_user_state_repository(tmp_path)
    before = _origin_snapshot(origin)
    manifest = api.build_baseline(origin)
    workspace = _materialize(api, manifest, tmp_path / "workspace")

    if requirement_id == "WS-001":
        assert workspace.baseline_digest == manifest.digest
        _assert_workspace_matches_manifest(workspace.root, manifest)
    elif requirement_id == "WS-006":
        _assert_manifest_user_state(manifest)
        _assert_workspace_matches_manifest(workspace.root, manifest)
    elif requirement_id == "WS-007":
        entries = _assert_manifest_user_state(manifest)
        assert type(manifest.entries) is tuple
        assert all(type(entry.content) is bytes for entry in entries.values())
    elif requirement_id == "WS-008":
        (workspace.root / "clean.txt").write_text(
            "agent-change\n",
            encoding="utf-8",
        )
        _assert_origin_unchanged(origin, before)
    elif requirement_id == "WS-009":
        assert workspace.source_head == before.head
        assert workspace.source_branch == before.branch
        _assert_git_not_present(workspace.root)
        _assert_origin_unchanged(origin, before)
    else:  # pragma: no cover - pytest parameters are the closed requirement set.
        raise AssertionError("unexpected WP-10 requirement")
