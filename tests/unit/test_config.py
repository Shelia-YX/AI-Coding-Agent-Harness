from __future__ import annotations

import importlib
from dataclasses import FrozenInstanceError
import hashlib

import pytest


def _load_config_api():
    try:
        module = importlib.import_module("coding_harness.config")
    except ModuleNotFoundError as exc:
        if exc.name != "coding_harness.config":
            raise
        pytest.fail(
            "EXPECTED_INTERFACE_MISSING: WP-21 trusted config contract",
            pytrace=False,
        )
    required = ("HarnessConfig", "RunConfigSnapshot")
    if any(not hasattr(module, name) for name in required):
        pytest.fail(
            "EXPECTED_INTERFACE_MISSING: WP-21 trusted config contract",
            pytrace=False,
        )
    return module


def _build(*, startup=None):
    config = _load_config_api()
    return config.HarnessConfig.from_startup(
        startup={} if startup is None else startup,
    )


def _assert_strict_trusted_config() -> None:
    config = _build()
    assert config.provider_identity == "course-provider"
    assert config.endpoint == "https://provider.example/v1/complete"
    assert config.request_timeout_seconds == 30
    assert config.max_request_bytes == 1_048_576
    assert config.max_response_bytes == 2_097_152
    assert config.max_tokens == 4096
    with pytest.raises(ValueError):
        _build(startup={"unknown_field": "not-approved"})


def _assert_trusted_precedence() -> None:
    config = _build(
        startup={
            "provider_identity": "startup-provider",
            "endpoint": "https://startup.example/v1/complete",
        }
    )
    assert config.provider_identity == "startup-provider"
    assert config.endpoint == "https://startup.example/v1/complete"
    module = _load_config_api()
    with pytest.raises(TypeError):
        module.HarnessConfig.from_startup(
            startup={},
            repository={"endpoint": "https://evil.example/complete"},
        )
    for source_name in ("dotenv", "issue", "tool_output", "llm_suggestion"):
        with pytest.raises(TypeError):
            module.HarnessConfig.from_startup(
                startup={},
                **{source_name: {"endpoint": "https://evil.example/complete"}},
            )


def _assert_untrusted_sources_excluded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER_ENDPOINT", "https://evil.example/complete")
    monkeypatch.setenv("HARNESS_PROVIDER", "evil-provider")
    config = _build()
    assert config.provider_identity == "course-provider"
    assert config.endpoint == "https://provider.example/v1/complete"


def _assert_snapshot_contract() -> None:
    startup = {
        "provider_identity": "startup-provider",
        "endpoint": "https://startup.example/v1/complete",
    }
    first = _build(startup=startup).snapshot()
    second = _build(startup=dict(reversed(tuple(startup.items())))).snapshot()
    assert type(first) is type(second)
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.snapshot_digest == second.snapshot_digest
    assert first.snapshot_digest == hashlib.sha256(first.canonical_bytes()).hexdigest()
    with pytest.raises(FrozenInstanceError):
        first.endpoint = "https://evil.example/complete"


def test_harness_config_contract_missing() -> None:
    _assert_strict_trusted_config()


def test_startup_trusted_config_overrides_defaults() -> None:
    _assert_trusted_precedence()


def test_repository_config_is_rejected() -> None:
    config = _load_config_api()
    with pytest.raises(TypeError):
        config.HarnessConfig.from_startup(
            startup={},
            repository={"endpoint": "https://evil.example/complete"},
        )


def test_environment_variables_are_not_config_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _assert_untrusted_sources_excluded(monkeypatch)


def test_unknown_config_field_is_rejected() -> None:
    with pytest.raises(ValueError):
        _build(startup={"unknown_field": "not-approved"})


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("provider_identity", 7),
        ("request_timeout_seconds", 0),
        ("max_request_bytes", 1_048_577),
        ("max_response_bytes", 2_097_153),
        ("max_tokens", 4097),
    ),
)
def test_invalid_config_type_or_range_is_rejected(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValueError):
        _build(startup={field: value})


def test_caller_cannot_replace_builtin_defaults() -> None:
    config = _load_config_api()
    with pytest.raises(TypeError):
        config.HarnessConfig.from_startup(
            startup={},
            defaults={
                "provider_identity": "caller-provider",
                "endpoint": "https://caller.example/complete",
            },
        )


def test_caller_cannot_bypass_defaults_with_direct_construction() -> None:
    config = _load_config_api()
    with pytest.raises(TypeError):
        config.HarnessConfig(
            provider_identity="caller-provider",
            endpoint="https://caller.example/complete",
            profile_identity="caller-profile",
            image_identity="caller:image",
            policy_identity="caller-policy",
            budget_hard_limits=(("llm_tokens", 1),),
            sandbox_template_identity="caller-sandbox",
            export_rules_identity="caller-export",
            request_timeout_seconds=30,
            max_request_bytes=1_048_576,
            max_response_bytes=2_097_152,
            max_tokens=4096,
        )


def test_run_config_snapshot_is_immutable() -> None:
    snapshot = _build().snapshot()
    with pytest.raises(FrozenInstanceError):
        snapshot.provider_identity = "changed-provider"


def test_run_config_snapshot_direct_construction_is_rejected() -> None:
    config = _load_config_api()
    with pytest.raises(TypeError):
        config.RunConfigSnapshot(
            provider_identity="caller-provider",
            endpoint="https://caller.example/complete",
            profile_identity="caller-profile",
            image_identity="caller:image",
            policy_identity="caller-policy",
            budget_hard_limits=(("llm_requests", 4),),
            sandbox_template_identity="caller-sandbox",
            export_rules_identity="caller-export",
            request_timeout_seconds=30,
            max_request_bytes=1_048_576,
            max_response_bytes=2_097_152,
            max_tokens=4096,
        )


def test_run_config_snapshot_authority_fields_reject_object_setattr() -> None:
    snapshot = _build().snapshot()
    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(snapshot, "provider_identity", "evil-provider")
    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(
            snapshot,
            "endpoint",
            "https://evil.example/complete",
        )
    assert snapshot.provider_identity == "course-provider"
    assert snapshot.endpoint == "https://provider.example/v1/complete"
    assert snapshot.snapshot_digest == hashlib.sha256(
        snapshot.canonical_bytes()
    ).hexdigest()


def test_snapshot_canonical_serialization_is_deterministic() -> None:
    _assert_snapshot_contract()


def test_snapshot_digest_is_sha256_of_canonical_bytes() -> None:
    snapshot = _build().snapshot()
    assert snapshot.snapshot_digest == hashlib.sha256(
        snapshot.canonical_bytes()
    ).hexdigest()


def test_snapshot_digest_changes_when_config_changes() -> None:
    first = _build().snapshot()
    second = _build(
        startup={
            "provider_identity": "startup-provider",
            "endpoint": "https://startup.example/v1/complete",
        }
    ).snapshot()
    assert first.canonical_bytes() != second.canonical_bytes()
    assert first.snapshot_digest != second.snapshot_digest


CONFIG_REQUIREMENTS = {
    "GEN-008": _assert_strict_trusted_config,
    "GEN-009": _assert_trusted_precedence,
    "GEN-010": _assert_snapshot_contract,
}


@pytest.mark.parametrize("requirement", tuple(CONFIG_REQUIREMENTS))
def test_spec_requirement(requirement: str) -> None:
    CONFIG_REQUIREMENTS[requirement]()
