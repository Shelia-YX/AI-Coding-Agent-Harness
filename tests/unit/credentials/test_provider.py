from __future__ import annotations

import importlib
from dataclasses import FrozenInstanceError

import pytest


def _load_models():
    try:
        module = importlib.import_module("coding_harness.credentials.models")
    except ModuleNotFoundError as exc:
        if exc.name not in {
            "coding_harness.credentials",
            "coding_harness.credentials.models",
        }:
            raise
        pytest.fail(
            "EXPECTED_INTERFACE_MISSING: WP-22 credential model contract",
            pytrace=False,
        )
    if not hasattr(module, "Credential"):
        pytest.fail(
            "EXPECTED_INTERFACE_MISSING: WP-22 credential model contract",
            pytrace=False,
        )
    return module


def _load_provider():
    try:
        module = importlib.import_module("coding_harness.credentials.provider")
    except ModuleNotFoundError as exc:
        if exc.name not in {
            "coding_harness.credentials",
            "coding_harness.credentials.models",
            "coding_harness.credentials.provider",
        }:
            raise
        pytest.fail(
            "EXPECTED_INTERFACE_MISSING: WP-22 credential provider contract",
            pytrace=False,
        )
    required = (
        "CredentialError",
        "CredentialErrorCode",
        "CredentialProvider",
        "StartupCredentialProvider",
    )
    if any(not hasattr(module, name) for name in required):
        pytest.fail(
            "EXPECTED_INTERFACE_MISSING: WP-22 credential provider contract",
            pytrace=False,
        )
    return module


def _credential(provider_identity: str, secret: bytes):
    models = _load_models()
    return models.Credential(
        provider_identity=provider_identity,
        secret=secret,
    )


def _startup_provider(credentials: dict[str, bytes]):
    provider = _load_provider()
    return provider.StartupCredentialProvider.from_startup(
        credentials=credentials,
    )


class _RecordingTransport:
    def __init__(self, result: object) -> None:
        self.result = result
        self.requests: list[object] = []

    def send(self, request):
        self.requests.append(request)
        return self.result


def _gateway(credential_provider):
    gateway_api = importlib.import_module("coding_harness.agent.provider")
    config = importlib.import_module("coding_harness.config")
    result = gateway_api.ProviderResult(
        status=gateway_api.ProviderResultStatus.SUCCEEDED,
        response_bytes=b"ok",
        redirect_location=None,
    )
    transport = _RecordingTransport(result)
    gateway = gateway_api.ProviderGateway(
        snapshot=config.HarnessConfig.from_startup(startup={}).snapshot(),
        transport=transport,
        credential_provider=credential_provider,
    )
    return gateway_api, gateway, transport


def test_credential_contract_is_immutable() -> None:
    credential = _credential("course-provider", b"course-secret")

    assert credential.provider_identity == "course-provider"
    assert credential.secret_bytes() == b"course-secret"
    with pytest.raises(FrozenInstanceError):
        credential.provider_identity = "other-provider"
    with pytest.raises(FrozenInstanceError):
        credential.secret = b"replacement"


def test_credential_default_surfaces_are_redacted() -> None:
    secret = b"never-print-this-secret"
    credential = _credential("course-provider", secret)

    exposed = secret.decode("ascii")
    assert exposed not in repr(credential)
    assert exposed not in str(credential)


def test_slot_reference_does_not_contain_secret() -> None:
    secret = "slot-reference-must-not-leak-this"
    credential = _credential("course-provider", secret.encode("ascii"))

    assert credential.slot_reference.startswith("startup:")
    assert secret not in credential.slot_reference


def test_startup_injection_is_snapshotted() -> None:
    source = {"course-provider": b"initial-secret"}
    credential_provider = _startup_provider(source)
    source["course-provider"] = b"changed-after-startup"

    resolved = credential_provider.resolve("course-provider")

    assert resolved.secret_bytes() == b"initial-secret"


def test_provider_interface_supports_exact_lookup() -> None:
    provider = _load_provider()
    credential_provider = _startup_provider(
        {
            "course-provider": b"course-secret",
            "other-provider": b"other-secret",
        }
    )

    assert isinstance(credential_provider, provider.CredentialProvider)
    resolved = credential_provider.resolve("course-provider")
    assert resolved.provider_identity == "course-provider"
    assert resolved.secret_bytes() == b"course-secret"


def test_missing_credential_fails_deterministically() -> None:
    provider = _load_provider()
    credential_provider = _startup_provider({})

    with pytest.raises(provider.CredentialError) as failure:
        credential_provider.resolve("course-provider")

    assert failure.value.code is provider.CredentialErrorCode.MISSING
    assert "course-provider" in failure.value.reason


def test_provider_mismatch_fails_deterministically() -> None:
    provider = _load_provider()
    credential_provider = _startup_provider(
        {"configured-provider": b"configured-secret"}
    )

    with pytest.raises(provider.CredentialError) as failure:
        credential_provider.resolve("requested-provider")

    assert failure.value.code is provider.CredentialErrorCode.PROVIDER_MISMATCH
    assert "requested-provider" in failure.value.reason


def test_provider_lookup_does_not_fallback() -> None:
    provider = _load_provider()
    credential_provider = _startup_provider(
        {
            "provider-a": b"secret-a",
            "provider-b": b"secret-b",
        }
    )

    with pytest.raises(provider.CredentialError) as failure:
        credential_provider.resolve("provider-c")

    assert failure.value.code is provider.CredentialErrorCode.PROVIDER_MISMATCH


def test_secret_is_absent_from_missing_and_mismatch_failures() -> None:
    provider = _load_provider()
    secret = "never-leak-from-error"
    credential_provider = _startup_provider(
        {"configured-provider": secret.encode("ascii")}
    )

    with pytest.raises(provider.CredentialError) as failure:
        credential_provider.resolve("requested-provider")

    surfaces = (
        str(failure.value),
        repr(failure.value),
        failure.value.reason,
        repr(credential_provider),
    )
    assert all(secret not in surface for surface in surfaces)


def test_untrusted_startup_values_are_rejected_without_echoing_secret() -> None:
    provider = _load_provider()
    secret = "string-secret-must-not-be-accepted"

    with pytest.raises(ValueError) as failure:
        provider.StartupCredentialProvider.from_startup(
            credentials={"course-provider": secret}
        )

    assert secret not in str(failure.value)


def test_gateway_with_matching_credential_calls_transport() -> None:
    credential_provider = _startup_provider(
        {"course-provider": b"matching-secret"}
    )
    _, gateway, transport = _gateway(credential_provider)

    result = gateway.execute(payload=b"{}", max_tokens=1)

    assert result.response_bytes == b"ok"
    assert len(transport.requests) == 1


def test_gateway_missing_credential_does_not_call_transport() -> None:
    credential_provider = _startup_provider({})
    gateway_api, gateway, transport = _gateway(credential_provider)

    with pytest.raises(gateway_api.ProviderError) as failure:
        gateway.execute(payload=b"{}", max_tokens=1)

    assert failure.value.code is gateway_api.ProviderErrorCode.CONFIGURATION_ERROR
    assert transport.requests == []


def test_gateway_mismatch_does_not_call_transport_or_leak_secret() -> None:
    secret = "mismatched-secret-must-not-leak"
    credential_provider = _startup_provider(
        {"other-provider": secret.encode("ascii")}
    )
    gateway_api, gateway, transport = _gateway(credential_provider)

    with pytest.raises(gateway_api.ProviderError) as failure:
        gateway.execute(payload=b"{}", max_tokens=1)

    assert failure.value.code is gateway_api.ProviderErrorCode.CONFIGURATION_ERROR
    assert transport.requests == []
    assert secret not in str(failure.value)
    assert secret not in repr(failure.value)
