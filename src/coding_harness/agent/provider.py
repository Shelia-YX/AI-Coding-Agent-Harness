"""Transport-injected Provider contracts without network or credential ownership."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
from threading import Lock
from typing import Protocol, runtime_checkable
from urllib.parse import urlsplit

from coding_harness.config import (
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
    MAX_TOKEN_LIMIT,
    REQUEST_TIMEOUT_SECONDS,
    RunConfigSnapshot,
)
from coding_harness.credentials.models import Credential
from coding_harness.credentials.provider import (
    CredentialError,
    CredentialProvider,
)


_MAX_REASON_BYTES = 4_096


class ProviderResultStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    CONFIGURATION_ERROR = "PROVIDER_CONFIGURATION_ERROR"
    REDIRECT = "REDIRECT"


class ProviderErrorCode(StrEnum):
    UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    CONFIGURATION_ERROR = "PROVIDER_CONFIGURATION_ERROR"


def _bounded_text(value: object, field_name: str) -> str:
    if type(value) is not str or not value or "\0" in value:
        raise ValueError(f"{field_name} must be bounded text")
    try:
        size = len(value.encode("utf-8", errors="strict"))
    except UnicodeError:
        raise ValueError(f"{field_name} must be valid UTF-8") from None
    if size > _MAX_REASON_BYTES:
        raise ValueError(f"{field_name} exceeds its byte limit")
    return value


def _canonical_bytes(values: dict[str, object]) -> bytes:
    return json.dumps(
        values,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _trusted_endpoint(value: object) -> str:
    endpoint = _bounded_text(value, "endpoint")
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("endpoint must be a fixed HTTPS endpoint")
    return endpoint


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    provider_identity: str
    endpoint: str
    payload: bytes
    timeout_seconds: int
    max_tokens: int

    def __post_init__(self) -> None:
        _bounded_text(self.provider_identity, "provider_identity")
        _trusted_endpoint(self.endpoint)
        if type(self.payload) is not bytes or len(self.payload) > MAX_REQUEST_BYTES:
            raise ValueError("provider request exceeds the request byte limit")
        if (
            type(self.timeout_seconds) is not int
            or self.timeout_seconds != REQUEST_TIMEOUT_SECONDS
            or type(self.max_tokens) is not int
            or not 1 <= self.max_tokens <= MAX_TOKEN_LIMIT
        ):
            raise ValueError("provider request limits are invalid")


@dataclass(frozen=True, slots=True)
class ProviderResult:
    status: ProviderResultStatus
    response_bytes: bytes
    redirect_location: str | None
    result_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.status) is not ProviderResultStatus:
            raise ValueError("provider result status is invalid")
        if (
            type(self.response_bytes) is not bytes
            or len(self.response_bytes) > MAX_RESPONSE_BYTES
        ):
            raise ValueError("provider response exceeds the response byte limit")
        if self.status is ProviderResultStatus.REDIRECT:
            _bounded_text(self.redirect_location, "redirect_location")
        elif self.redirect_location is not None:
            raise ValueError("only redirect results may contain a location")
        if (
            self.status is not ProviderResultStatus.SUCCEEDED
            and self.response_bytes
        ):
            raise ValueError("failed provider result must not contain response bytes")
        object.__setattr__(
            self,
            "result_digest",
            hashlib.sha256(self.canonical_bytes()).hexdigest(),
        )

    def canonical_bytes(self) -> bytes:
        return _canonical_bytes(
            {
                "redirect_location": self.redirect_location,
                "response_base64": base64.b64encode(self.response_bytes).decode("ascii"),
                "status": self.status.value,
            }
        )


class ProviderError(RuntimeError):
    __slots__ = ("_code", "_reason")

    def __init__(self, *, code: ProviderErrorCode, reason: str) -> None:
        if type(code) is not ProviderErrorCode:
            raise ValueError("provider error code is invalid")
        reason = _bounded_text(reason, "reason")
        object.__setattr__(self, "_code", code)
        object.__setattr__(self, "_reason", reason)
        super().__init__(reason)

    @property
    def code(self) -> ProviderErrorCode:
        return self._code

    @property
    def reason(self) -> str:
        return self._reason


@runtime_checkable
class ProviderTransport(Protocol):
    def send(self, request: ProviderRequest, /) -> ProviderResult:
        """Send one bounded request through an externally supplied transport."""
        raise NotImplementedError("protocol method")


class ProviderGateway:
    __slots__ = (
        "_budget_lock",
        "_credential_provider",
        "_endpoint",
        "_provider_identity",
        "_remaining_requests",
        "_request_timeout_seconds",
        "_transport",
    )

    def __init__(
        self,
        *,
        snapshot: RunConfigSnapshot,
        transport: ProviderTransport,
        credential_provider: CredentialProvider,
    ) -> None:
        if type(snapshot) is not RunConfigSnapshot:
            raise ValueError("provider gateway requires a RunConfigSnapshot")
        if snapshot.snapshot_digest != hashlib.sha256(
            snapshot.canonical_bytes()
        ).hexdigest():
            raise ValueError("provider gateway requires an intact config snapshot")
        if not isinstance(transport, ProviderTransport):
            raise ValueError("provider transport does not satisfy the contract")
        if not isinstance(credential_provider, CredentialProvider):
            raise ValueError("credential provider does not satisfy the contract")
        budget_limits = dict(snapshot.budget_hard_limits)
        request_limit = budget_limits.get("llm_requests")
        if type(request_limit) is not int or request_limit < 0:
            raise ValueError("provider gateway requires an llm_requests limit")
        self._provider_identity = snapshot.provider_identity
        self._endpoint = snapshot.endpoint
        self._request_timeout_seconds = snapshot.request_timeout_seconds
        self._remaining_requests = request_limit
        self._budget_lock = Lock()
        self._credential_provider = credential_provider
        self._transport = transport

    def execute(self, *, payload: bytes, max_tokens: int) -> ProviderResult:
        try:
            credential = self._credential_provider.resolve(
                self._provider_identity
            )
        except CredentialError:
            raise ProviderError(
                code=ProviderErrorCode.CONFIGURATION_ERROR,
                reason="provider credential configuration is invalid",
            ) from None
        except Exception:
            raise ProviderError(
                code=ProviderErrorCode.CONFIGURATION_ERROR,
                reason="credential provider failed its contract",
            ) from None
        if (
            type(credential) is not Credential
            or credential.provider_identity != self._provider_identity
        ):
            raise ProviderError(
                code=ProviderErrorCode.CONFIGURATION_ERROR,
                reason="credential provider returned an invalid binding",
            )
        request = ProviderRequest(
            provider_identity=self._provider_identity,
            endpoint=self._endpoint,
            payload=payload,
            timeout_seconds=self._request_timeout_seconds,
            max_tokens=max_tokens,
        )
        with self._budget_lock:
            if self._remaining_requests == 0:
                raise ProviderError(
                    code=ProviderErrorCode.CONFIGURATION_ERROR,
                    reason="provider request budget is exhausted",
                )
            self._remaining_requests -= 1
        try:
            result = self._transport.send(request)
        except TimeoutError:
            raise ProviderError(
                code=ProviderErrorCode.UNAVAILABLE,
                reason="provider transport timed out",
            ) from None
        except OSError:
            raise ProviderError(
                code=ProviderErrorCode.UNAVAILABLE,
                reason="provider transport is unavailable",
            ) from None
        except Exception:
            raise ProviderError(
                code=ProviderErrorCode.CONFIGURATION_ERROR,
                reason="provider transport failed its contract",
            ) from None
        if type(result) is not ProviderResult:
            raise ProviderError(
                code=ProviderErrorCode.CONFIGURATION_ERROR,
                reason="provider transport returned an invalid result",
            )
        try:
            verified_result = ProviderResult(
                status=result.status,
                response_bytes=result.response_bytes,
                redirect_location=result.redirect_location,
            )
        except (TypeError, ValueError):
            raise ProviderError(
                code=ProviderErrorCode.CONFIGURATION_ERROR,
                reason="provider transport returned malformed evidence",
            ) from None
        if result.result_digest != hashlib.sha256(
            result.canonical_bytes()
        ).hexdigest():
            raise ProviderError(
                code=ProviderErrorCode.CONFIGURATION_ERROR,
                reason="provider transport returned tampered evidence",
            )
        if result.status is ProviderResultStatus.SUCCEEDED:
            return verified_result
        if result.status is ProviderResultStatus.UNAVAILABLE:
            raise ProviderError(
                code=ProviderErrorCode.UNAVAILABLE,
                reason="provider transport is unavailable",
            )
        if result.status is ProviderResultStatus.CONFIGURATION_ERROR:
            raise ProviderError(
                code=ProviderErrorCode.CONFIGURATION_ERROR,
                reason="provider transport configuration is invalid",
            )
        raise ProviderError(
            code=ProviderErrorCode.CONFIGURATION_ERROR,
            reason="provider redirect is outside the fixed connection policy",
        )


__all__ = [
    "ProviderGateway",
    "ProviderError",
    "ProviderErrorCode",
    "ProviderRequest",
    "ProviderResult",
    "ProviderResultStatus",
    "ProviderTransport",
]
