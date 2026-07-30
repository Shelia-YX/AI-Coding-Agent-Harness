from __future__ import annotations

import importlib
from dataclasses import FrozenInstanceError
import hashlib

import pytest


def _load_provider_api():
    try:
        module = importlib.import_module("coding_harness.agent.provider")
    except ModuleNotFoundError as exc:
        if exc.name != "coding_harness.agent.provider":
            raise
        pytest.fail(
            "EXPECTED_INTERFACE_MISSING: WP-21 provider contract",
            pytrace=False,
        )
    required = (
        "ProviderError",
        "ProviderErrorCode",
        "ProviderGateway",
        "ProviderRequest",
        "ProviderResult",
        "ProviderResultStatus",
        "ProviderTransport",
    )
    if any(not hasattr(module, name) for name in required):
        pytest.fail(
            "EXPECTED_INTERFACE_MISSING: WP-21 provider contract",
            pytrace=False,
        )
    return module


def _snapshot():
    try:
        config = importlib.import_module("coding_harness.config")
    except ModuleNotFoundError as exc:
        if exc.name != "coding_harness.config":
            raise
        pytest.fail(
            "EXPECTED_INTERFACE_MISSING: WP-21 trusted config contract",
            pytrace=False,
        )
    return config.HarnessConfig.from_startup(startup={}).snapshot()


class _FakeTransport:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.requests: list[object] = []

    def send(self, request):
        self.requests.append(request)
        if not self.outcomes:
            raise AssertionError("transport called more than expected")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _result(provider, status, *, response=b"", redirect_location=None):
    return provider.ProviderResult(
        status=status,
        response_bytes=response,
        redirect_location=redirect_location,
    )


def _gateway(provider, outcomes: list[object]):
    transport = _FakeTransport(outcomes)
    gateway = provider.ProviderGateway(
        snapshot=_snapshot(),
        transport=transport,
    )
    return gateway, transport


def _assert_fixed_request_and_limits() -> None:
    provider = _load_provider_api()
    success = _result(
        provider,
        provider.ProviderResultStatus.SUCCEEDED,
        response=b'{"action":"stop_without_safe_action"}',
    )
    gateway, transport = _gateway(provider, [success])
    result = gateway.execute(payload=b'{"context":"bounded"}', max_tokens=128)
    assert result == success
    assert len(transport.requests) == 1
    request = transport.requests[0]
    assert request.provider_identity == "course-provider"
    assert request.endpoint == "https://provider.example/v1/complete"
    assert request.timeout_seconds == 30
    assert request.max_tokens == 128


def _assert_cumulative_request_budget() -> None:
    provider = _load_provider_api()
    successes = [
        _result(
            provider,
            provider.ProviderResultStatus.SUCCEEDED,
            response=f"response-{index}".encode(),
        )
        for index in range(5)
    ]
    gateway, transport = _gateway(provider, successes)
    for index in range(4):
        result = gateway.execute(payload=b"{}", max_tokens=1)
        assert result.response_bytes == f"response-{index}".encode()
    with pytest.raises(provider.ProviderError) as failure:
        gateway.execute(payload=b"{}", max_tokens=1)
    assert failure.value.code is provider.ProviderErrorCode.CONFIGURATION_ERROR
    assert len(transport.requests) == 4


def _assert_unavailable_and_configuration_separate() -> None:
    provider = _load_provider_api()
    unavailable_gateway, _ = _gateway(
        provider,
        [
            _result(
                provider,
                provider.ProviderResultStatus.UNAVAILABLE,
            )
        ],
    )
    with pytest.raises(provider.ProviderError) as unavailable:
        unavailable_gateway.execute(payload=b"{}", max_tokens=1)
    assert unavailable.value.code is provider.ProviderErrorCode.UNAVAILABLE

    config_gateway, _ = _gateway(
        provider,
        [
            _result(
                provider,
                provider.ProviderResultStatus.CONFIGURATION_ERROR,
            )
        ],
    )
    with pytest.raises(provider.ProviderError) as configuration:
        config_gateway.execute(payload=b"{}", max_tokens=1)
    assert (
        configuration.value.code
        is provider.ProviderErrorCode.CONFIGURATION_ERROR
    )


def _assert_redirect_rejected() -> None:
    provider = _load_provider_api()
    gateway, transport = _gateway(
        provider,
        [
            _result(
                provider,
                provider.ProviderResultStatus.REDIRECT,
                redirect_location="https://other.example/complete",
            )
        ],
    )
    with pytest.raises(provider.ProviderError) as failure:
        gateway.execute(payload=b"{}", max_tokens=1)
    assert failure.value.code is provider.ProviderErrorCode.CONFIGURATION_ERROR
    assert len(transport.requests) == 1


def _assert_no_fallback() -> None:
    provider = _load_provider_api()
    gateway, transport = _gateway(
        provider,
        [
            _result(provider, provider.ProviderResultStatus.UNAVAILABLE),
            _result(
                provider,
                provider.ProviderResultStatus.SUCCEEDED,
                response=b"fallback-result",
            ),
        ],
    )
    with pytest.raises(provider.ProviderError) as failure:
        gateway.execute(payload=b"{}", max_tokens=1)
    assert failure.value.code is provider.ProviderErrorCode.UNAVAILABLE
    assert len(transport.requests) == 1


def test_provider_request_contract_missing() -> None:
    provider = _load_provider_api()
    request = provider.ProviderRequest(
        provider_identity="course-provider",
        endpoint="https://provider.example/v1/complete",
        payload=b"{}",
        timeout_seconds=30,
        max_tokens=128,
    )
    assert request.payload == b"{}"
    with pytest.raises(FrozenInstanceError):
        request.endpoint = "https://evil.example/complete"


def test_provider_result_contract_missing() -> None:
    provider = _load_provider_api()
    first = _result(
        provider,
        provider.ProviderResultStatus.SUCCEEDED,
        response=b"bounded-result",
    )
    second = _result(
        provider,
        provider.ProviderResultStatus.SUCCEEDED,
        response=b"bounded-result",
    )
    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.result_digest == second.result_digest
    assert first.result_digest == hashlib.sha256(first.canonical_bytes()).hexdigest()


def test_provider_error_classification_contract_missing() -> None:
    provider = _load_provider_api()
    error = provider.ProviderError(
        code=provider.ProviderErrorCode.UNAVAILABLE,
        reason="provider transport unavailable",
    )
    assert isinstance(error, Exception)
    assert error.code is provider.ProviderErrorCode.UNAVAILABLE


def test_provider_transport_interface_missing() -> None:
    provider = _load_provider_api()
    success = _result(
        provider,
        provider.ProviderResultStatus.SUCCEEDED,
        response=b"ok",
    )
    transport = _FakeTransport([success])
    assert isinstance(transport, provider.ProviderTransport)


def test_timeout_is_classified_as_unavailable() -> None:
    provider = _load_provider_api()
    gateway, transport = _gateway(provider, [TimeoutError("timeout")])
    with pytest.raises(provider.ProviderError) as failure:
        gateway.execute(payload=b"{}", max_tokens=1)
    assert failure.value.code is provider.ProviderErrorCode.UNAVAILABLE
    assert len(transport.requests) == 1


def test_unavailable_and_configuration_error_are_distinct() -> None:
    _assert_unavailable_and_configuration_separate()


def test_redirect_is_rejected_without_following() -> None:
    _assert_redirect_rejected()


def test_provider_failure_does_not_fallback() -> None:
    _assert_no_fallback()


def test_malformed_transport_result_maps_to_configuration_error() -> None:
    provider = _load_provider_api()
    gateway, transport = _gateway(provider, [object()])
    with pytest.raises(provider.ProviderError) as failure:
        gateway.execute(payload=b"{}", max_tokens=1)
    assert failure.value.code is provider.ProviderErrorCode.CONFIGURATION_ERROR
    assert len(transport.requests) == 1


def test_unexpected_transport_exception_maps_to_configuration_error() -> None:
    provider = _load_provider_api()
    gateway, transport = _gateway(
        provider,
        [RuntimeError("transport implementation failure")],
    )
    with pytest.raises(provider.ProviderError) as failure:
        gateway.execute(payload=b"{}", max_tokens=1)
    assert failure.value.code is provider.ProviderErrorCode.CONFIGURATION_ERROR
    assert len(transport.requests) == 1


def test_request_and_response_byte_limits_are_enforced() -> None:
    provider = _load_provider_api()
    with pytest.raises(ValueError):
        provider.ProviderRequest(
            provider_identity="course-provider",
            endpoint="https://provider.example/v1/complete",
            payload=b"x" * 1_048_577,
            timeout_seconds=30,
            max_tokens=1,
        )
    with pytest.raises(ValueError):
        _result(
            provider,
            provider.ProviderResultStatus.SUCCEEDED,
            response=b"x" * 2_097_153,
        )


def test_exact_request_and_response_byte_limits_are_allowed() -> None:
    provider = _load_provider_api()
    success = _result(
        provider,
        provider.ProviderResultStatus.SUCCEEDED,
        response=b"y" * 2_097_152,
    )
    gateway, transport = _gateway(provider, [success])
    result = gateway.execute(payload=b"x" * 1_048_576, max_tokens=4096)
    assert len(result.response_bytes) == 2_097_152
    assert len(transport.requests[0].payload) == 1_048_576


def test_cumulative_request_budget_fails_closed_after_limit() -> None:
    _assert_cumulative_request_budget()


def test_gateway_rejects_post_construction_endpoint_tampering() -> None:
    provider = _load_provider_api()
    snapshot = _snapshot()
    success = _result(
        provider,
        provider.ProviderResultStatus.SUCCEEDED,
        response=b"ok",
    )
    transport = _FakeTransport([success])
    gateway = provider.ProviderGateway(snapshot=snapshot, transport=transport)
    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(
            snapshot,
            "endpoint",
            "https://evil.example/complete",
        )
    gateway.execute(payload=b"{}", max_tokens=1)
    assert transport.requests[0].endpoint == (
        "https://provider.example/v1/complete"
    )


def test_digest_field_tampering_is_rejected() -> None:
    provider = _load_provider_api()
    snapshot = _snapshot()
    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(snapshot, "snapshot_digest", "0" * 64)
    assert snapshot.snapshot_digest == hashlib.sha256(
        snapshot.canonical_bytes()
    ).hexdigest()

    success = _result(
        provider,
        provider.ProviderResultStatus.SUCCEEDED,
        response=b"ok",
    )
    object.__setattr__(success, "result_digest", "0" * 64)
    gateway, _ = _gateway(provider, [success])
    with pytest.raises(provider.ProviderError) as failure:
        gateway.execute(payload=b"{}", max_tokens=1)
    assert failure.value.code is provider.ProviderErrorCode.CONFIGURATION_ERROR


def _assert_endpoint_override_rejected() -> None:
    provider = _load_provider_api()
    success = _result(
        provider,
        provider.ProviderResultStatus.SUCCEEDED,
        response=b"ok",
    )
    gateway, transport = _gateway(provider, [success])
    gateway.execute(
        payload=b'{"endpoint":"https://evil.example/complete"}',
        max_tokens=1,
    )
    assert transport.requests[0].endpoint == (
        "https://provider.example/v1/complete"
    )
    with pytest.raises(TypeError):
        gateway.execute(
            payload=b"{}",
            max_tokens=1,
            endpoint="https://evil.example/complete",
        )


def test_untrusted_endpoint_override_is_rejected() -> None:
    _assert_endpoint_override_rejected()


PROVIDER_REQUIREMENTS = {
    "AGT-013": _assert_cumulative_request_budget,
    "AGT-014": _assert_unavailable_and_configuration_separate,
    "SEC-014": _assert_redirect_rejected,
    "SEC-015": _assert_endpoint_override_rejected,
}


@pytest.mark.parametrize("requirement", tuple(PROVIDER_REQUIREMENTS))
def test_spec_requirement(requirement: str) -> None:
    PROVIDER_REQUIREMENTS[requirement]()
