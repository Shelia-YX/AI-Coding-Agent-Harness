"""Strict trusted configuration and immutable per-run snapshots."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, FrozenInstanceError
import hashlib
import json
from types import MappingProxyType
import unicodedata
from urllib.parse import urlsplit


REQUEST_TIMEOUT_SECONDS = 30
MAX_REQUEST_BYTES = 1_048_576
MAX_RESPONSE_BYTES = 2_097_152
MAX_TOKEN_LIMIT = 4_096

_MAX_TEXT_BYTES = 4_096
_MAX_BUDGET_DIMENSIONS = 64
_SNAPSHOT_FACTORY_TOKEN = object()
_FIELDS = frozenset(
    {
        "provider_identity",
        "endpoint",
        "profile_identity",
        "image_identity",
        "policy_identity",
        "budget_hard_limits",
        "sandbox_template_identity",
        "export_rules_identity",
        "request_timeout_seconds",
        "max_request_bytes",
        "max_response_bytes",
        "max_tokens",
    }
)
_BUILTIN_DEFAULTS: Mapping[str, object] = MappingProxyType(
    {
        "provider_identity": "course-provider",
        "endpoint": "https://provider.example/v1/complete",
        "profile_identity": "python312",
        "image_identity": "python:3.12",
        "policy_identity": "policy:v1",
        "budget_hard_limits": MappingProxyType(
            {"llm_requests": 4, "llm_tokens": MAX_TOKEN_LIMIT}
        ),
        "sandbox_template_identity": "sandbox:course-v1",
        "export_rules_identity": "export:v1",
        "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
        "max_request_bytes": MAX_REQUEST_BYTES,
        "max_response_bytes": MAX_RESPONSE_BYTES,
        "max_tokens": MAX_TOKEN_LIMIT,
    }
)


def _text(value: object, field_name: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{field_name} must be non-empty text")
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeError:
        raise ValueError(f"{field_name} must be valid UTF-8") from None
    if (
        len(encoded) > _MAX_TEXT_BYTES
        or any(unicodedata.category(character).startswith("C") for character in value)
    ):
        raise ValueError(f"{field_name} is outside the trusted text boundary")
    return value


def _endpoint(value: object) -> str:
    endpoint = _text(value, "endpoint")
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


def _mapping(value: object, field_name: str) -> dict[str, object]:
    if type(value) is not dict:
        raise ValueError(f"{field_name} must be a strict mapping")
    if any(type(key) is not str for key in value):
        raise ValueError(f"{field_name} contains an invalid field")
    return dict(value)


def _budget_limits(value: object) -> tuple[tuple[str, int], ...]:
    if not isinstance(value, Mapping):
        raise ValueError("budget_hard_limits must be a mapping")
    try:
        items = tuple(value.items())
    except Exception:
        raise ValueError("budget_hard_limits could not be read") from None
    if not 1 <= len(items) <= _MAX_BUDGET_DIMENSIONS:
        raise ValueError("budget_hard_limits has invalid size")
    normalized: list[tuple[str, int]] = []
    seen: set[str] = set()
    for key, limit in items:
        key = _text(key, "budget dimension")
        if key in seen or type(limit) is not int or not 0 <= limit <= 2**63 - 1:
            raise ValueError("budget_hard_limits contains an invalid item")
        seen.add(key)
        normalized.append((key, limit))
    return tuple(sorted(normalized))


def _canonical_bytes(values: Mapping[str, object]) -> bytes:
    return json.dumps(
        values,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


@dataclass(slots=True, init=False)
class RunConfigSnapshot:
    _provider_identity: str
    _endpoint: str
    _profile_identity: str
    _image_identity: str
    _policy_identity: str
    _budget_hard_limits: tuple[tuple[str, int], ...]
    _sandbox_template_identity: str
    _export_rules_identity: str
    _request_timeout_seconds: int
    _max_request_bytes: int
    _max_response_bytes: int
    _max_tokens: int
    _snapshot_digest: str

    def __setattr__(self, name: str, value: object) -> None:
        raise FrozenInstanceError(f"cannot assign to field {name!r}")

    @classmethod
    def _from_config(
        cls,
        *,
        factory_token: object,
        provider_identity: str,
        endpoint: str,
        profile_identity: str,
        image_identity: str,
        policy_identity: str,
        budget_hard_limits: tuple[tuple[str, int], ...],
        sandbox_template_identity: str,
        export_rules_identity: str,
        request_timeout_seconds: int,
        max_request_bytes: int,
        max_response_bytes: int,
        max_tokens: int,
    ) -> RunConfigSnapshot:
        if factory_token is not _SNAPSHOT_FACTORY_TOKEN:
            raise TypeError("RunConfigSnapshot requires the trusted config factory")
        instance = object.__new__(cls)
        values = {
            "_provider_identity": provider_identity,
            "_endpoint": endpoint,
            "_profile_identity": profile_identity,
            "_image_identity": image_identity,
            "_policy_identity": policy_identity,
            "_budget_hard_limits": budget_hard_limits,
            "_sandbox_template_identity": sandbox_template_identity,
            "_export_rules_identity": export_rules_identity,
            "_request_timeout_seconds": request_timeout_seconds,
            "_max_request_bytes": max_request_bytes,
            "_max_response_bytes": max_response_bytes,
            "_max_tokens": max_tokens,
        }
        for field_name, field_value in values.items():
            object.__setattr__(instance, field_name, field_value)
        _validate_fields(instance)
        object.__setattr__(
            instance,
            "_snapshot_digest",
            hashlib.sha256(instance.canonical_bytes()).hexdigest(),
        )
        return instance

    @property
    def provider_identity(self) -> str:
        return self._provider_identity

    @property
    def endpoint(self) -> str:
        return self._endpoint

    @property
    def profile_identity(self) -> str:
        return self._profile_identity

    @property
    def image_identity(self) -> str:
        return self._image_identity

    @property
    def policy_identity(self) -> str:
        return self._policy_identity

    @property
    def budget_hard_limits(self) -> tuple[tuple[str, int], ...]:
        return self._budget_hard_limits

    @property
    def sandbox_template_identity(self) -> str:
        return self._sandbox_template_identity

    @property
    def export_rules_identity(self) -> str:
        return self._export_rules_identity

    @property
    def request_timeout_seconds(self) -> int:
        return self._request_timeout_seconds

    @property
    def max_request_bytes(self) -> int:
        return self._max_request_bytes

    @property
    def max_response_bytes(self) -> int:
        return self._max_response_bytes

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def snapshot_digest(self) -> str:
        return self._snapshot_digest

    def canonical_bytes(self) -> bytes:
        return _canonical_bytes(
            {
                "budget_hard_limits": self.budget_hard_limits,
                "endpoint": self.endpoint,
                "export_rules_identity": self.export_rules_identity,
                "image_identity": self.image_identity,
                "max_request_bytes": self.max_request_bytes,
                "max_response_bytes": self.max_response_bytes,
                "max_tokens": self.max_tokens,
                "policy_identity": self.policy_identity,
                "profile_identity": self.profile_identity,
                "provider_identity": self.provider_identity,
                "request_timeout_seconds": self.request_timeout_seconds,
                "sandbox_template_identity": self.sandbox_template_identity,
            }
        )


@dataclass(frozen=True, slots=True, init=False)
class HarnessConfig:
    provider_identity: str
    endpoint: str
    profile_identity: str
    image_identity: str
    policy_identity: str
    budget_hard_limits: tuple[tuple[str, int], ...]
    sandbox_template_identity: str
    export_rules_identity: str
    request_timeout_seconds: int
    max_request_bytes: int
    max_response_bytes: int
    max_tokens: int

    @classmethod
    def from_startup(
        cls,
        *,
        startup: dict[str, object],
    ) -> HarnessConfig:
        startup_values = _mapping(startup, "startup")
        if not frozenset(startup_values).issubset(_FIELDS):
            raise ValueError("startup contains an unknown config field")
        merged = dict(_BUILTIN_DEFAULTS) | startup_values
        values = {
            "provider_identity": merged["provider_identity"],
            "endpoint": merged["endpoint"],
            "profile_identity": merged["profile_identity"],
            "image_identity": merged["image_identity"],
            "policy_identity": merged["policy_identity"],
            "budget_hard_limits": _budget_limits(merged["budget_hard_limits"]),
            "sandbox_template_identity": merged["sandbox_template_identity"],
            "export_rules_identity": merged["export_rules_identity"],
            "request_timeout_seconds": merged["request_timeout_seconds"],
            "max_request_bytes": merged["max_request_bytes"],
            "max_response_bytes": merged["max_response_bytes"],
            "max_tokens": merged["max_tokens"],
        }
        instance = object.__new__(cls)
        for field_name, field_value in values.items():
            object.__setattr__(instance, field_name, field_value)
        _validate_fields(instance)
        return instance

    def snapshot(self) -> RunConfigSnapshot:
        return RunConfigSnapshot._from_config(
            factory_token=_SNAPSHOT_FACTORY_TOKEN,
            provider_identity=self.provider_identity,
            endpoint=self.endpoint,
            profile_identity=self.profile_identity,
            image_identity=self.image_identity,
            policy_identity=self.policy_identity,
            budget_hard_limits=self.budget_hard_limits,
            sandbox_template_identity=self.sandbox_template_identity,
            export_rules_identity=self.export_rules_identity,
            request_timeout_seconds=self.request_timeout_seconds,
            max_request_bytes=self.max_request_bytes,
            max_response_bytes=self.max_response_bytes,
            max_tokens=self.max_tokens,
        )


def _validate_fields(value: HarnessConfig | RunConfigSnapshot) -> None:
    _text(value.provider_identity, "provider_identity")
    _endpoint(value.endpoint)
    _text(value.profile_identity, "profile_identity")
    _text(value.image_identity, "image_identity")
    _text(value.policy_identity, "policy_identity")
    normalized_budget = _budget_limits(dict(value.budget_hard_limits))
    if value.budget_hard_limits != normalized_budget:
        raise ValueError("budget_hard_limits must use canonical ordering")
    _text(value.sandbox_template_identity, "sandbox_template_identity")
    _text(value.export_rules_identity, "export_rules_identity")
    if (
        type(value.request_timeout_seconds) is not int
        or value.request_timeout_seconds != REQUEST_TIMEOUT_SECONDS
        or type(value.max_request_bytes) is not int
        or value.max_request_bytes != MAX_REQUEST_BYTES
        or type(value.max_response_bytes) is not int
        or value.max_response_bytes != MAX_RESPONSE_BYTES
        or type(value.max_tokens) is not int
        or value.max_tokens != MAX_TOKEN_LIMIT
    ):
        raise ValueError("course-level provider limits must use frozen values")


__all__ = [
    "HarnessConfig",
    "MAX_REQUEST_BYTES",
    "MAX_RESPONSE_BYTES",
    "MAX_TOKEN_LIMIT",
    "REQUEST_TIMEOUT_SECONDS",
    "RunConfigSnapshot",
]
