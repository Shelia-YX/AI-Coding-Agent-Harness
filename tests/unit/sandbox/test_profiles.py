from __future__ import annotations

from dataclasses import FrozenInstanceError
import importlib

import pytest


def _api():
    try:
        return importlib.import_module("coding_harness.sandbox.profiles")
    except ModuleNotFoundError as error:
        if error.name in {
            "coding_harness.sandbox",
            "coding_harness.sandbox.profiles",
        }:
            pytest.fail(
                "EXPECTED_INTERFACE_MISSING: sandbox profile contract",
                pytrace=False,
            )
        raise


def _registry(api):
    return api.ProfileRegistry.default()


def _signals(api, *paths: str):
    return api.RepositorySignals(paths=paths)


def test_registry_contains_exact_mvp_profiles() -> None:
    api = _api()
    profiles = _registry(api).profiles
    assert tuple(profile.identity for profile in profiles) == (
        api.ProfileId.PYTHON312,
        api.ProfileId.NODEJS20_NPM,
    )
    assert profiles[0].runtime_identity == "python:3.12"
    assert profiles[0].validation_operations == ("pytest", "ruff")
    assert profiles[1].runtime_identity == "nodejs:20/npm"
    assert profiles[1].validation_operations == (
        "test",
        "lint",
        "build",
        "typecheck",
    )


def test_profile_is_deeply_immutable() -> None:
    api = _api()
    profile = _registry(api).require(api.ProfileId.PYTHON312)
    assert type(profile.validation_operations) is tuple
    assert type(profile.recognition_signals) is tuple
    with pytest.raises(FrozenInstanceError):
        profile.runtime_identity = "python:3.13"


def test_profile_digest_is_deterministic() -> None:
    api = _api()
    first = _registry(api).require(api.ProfileId.PYTHON312)
    second = _registry(api).require(api.ProfileId.PYTHON312)
    assert first.profile_digest == second.profile_digest
    assert len(first.profile_digest) == 64
    assert set(first.profile_digest) <= set("0123456789abcdef")


def test_python_repository_signals_select_python_profile() -> None:
    api = _api()
    result = _registry(api).select(_signals(api, "pyproject.toml"))
    assert result.status is api.ProfileSelectionStatus.SELECTED
    assert result.profile.identity is api.ProfileId.PYTHON312


def test_node_repository_signals_select_node_profile() -> None:
    api = _api()
    result = _registry(api).select(
        _signals(api, "package.json", "package-lock.json")
    )
    assert result.status is api.ProfileSelectionStatus.SELECTED
    assert result.profile.identity is api.ProfileId.NODEJS20_NPM


def test_ambiguous_repository_signals_fail_closed() -> None:
    api = _api()
    result = _registry(api).select(
        _signals(
            api,
            "pyproject.toml",
            "package.json",
            "package-lock.json",
        )
    )
    assert result.status is api.ProfileSelectionStatus.AMBIGUOUS
    assert result.profile is None


def test_unsupported_repository_signals_fail_closed() -> None:
    api = _api()
    result = _registry(api).select(_signals(api, "Cargo.toml"))
    assert result.status is api.ProfileSelectionStatus.UNSUPPORTED
    assert result.profile is None


def test_llm_suggestion_does_not_override_repository_selection() -> None:
    api = _api()
    result = _registry(api).select(
        _signals(api, "pyproject.toml"),
        llm_suggestion=api.ProfileId.NODEJS20_NPM,
    )
    assert result.status is api.ProfileSelectionStatus.SELECTED
    assert result.profile.identity is api.ProfileId.PYTHON312


@pytest.mark.parametrize(
    "override",
    (
        {"runtime_override": "python:3.13"},
        {"image_override": "repository.example/untrusted:latest"},
    ),
)
def test_repository_runtime_or_image_override_is_rejected(
    override: dict[str, str],
) -> None:
    api = _api()
    with pytest.raises(ValueError):
        api.RepositorySignals(paths=("pyproject.toml",), **override)


def test_repository_signals_reject_excessive_signal_count() -> None:
    api = _api()
    with pytest.raises(ValueError):
        api.RepositorySignals(
            paths=tuple(f"src/file-{index}.py" for index in range(257))
        )


def test_repository_signals_reject_oversized_utf8_path() -> None:
    api = _api()
    with pytest.raises(ValueError):
        api.RepositorySignals(paths=("é" * 2_049,))


@pytest.mark.parametrize("requirement_id", ("SBX-002", "SBX-003"))
def test_spec_requirement(requirement_id: str) -> None:
    api = _api()
    registry = _registry(api)
    if requirement_id == "SBX-002":
        assert tuple(profile.identity for profile in registry.profiles) == (
            api.ProfileId.PYTHON312,
            api.ProfileId.NODEJS20_NPM,
        )
        return
    result = registry.select(
        _signals(api, "pyproject.toml"),
        llm_suggestion=api.ProfileId.NODEJS20_NPM,
    )
    assert result.profile.identity is api.ProfileId.PYTHON312
