"""Trusted startup credential injection and exact provider lookup."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Protocol, runtime_checkable

from coding_harness.credentials.models import Credential


class CredentialErrorCode(StrEnum):
    MISSING = "MISSING_CREDENTIAL"
    PROVIDER_MISMATCH = "CREDENTIAL_PROVIDER_MISMATCH"


class CredentialError(RuntimeError):
    __slots__ = ("_code", "_reason")

    def __init__(self, *, code: CredentialErrorCode, reason: str) -> None:
        if type(code) is not CredentialErrorCode:
            raise ValueError("credential error code is invalid")
        object.__setattr__(self, "_code", code)
        object.__setattr__(self, "_reason", reason)
        super().__init__(reason)

    @property
    def code(self) -> CredentialErrorCode:
        return self._code

    @property
    def reason(self) -> str:
        return self._reason


@runtime_checkable
class CredentialProvider(Protocol):
    def resolve(self, provider_identity: str, /) -> Credential:
        """Resolve one exact provider binding or fail closed."""

        raise NotImplementedError("protocol method")


class StartupCredentialProvider:
    """Immutable snapshot of credentials injected by the trusted host startup."""

    __slots__ = ("_credentials",)

    def __init__(self, credentials: tuple[Credential, ...]) -> None:
        object.__setattr__(self, "_credentials", credentials)

    @classmethod
    def from_startup(
        cls,
        *,
        credentials: Mapping[str, bytes],
    ) -> StartupCredentialProvider:
        if type(credentials) is not dict:
            raise ValueError("startup credentials must be a strict mapping")
        snapshot = tuple(
            Credential(provider_identity=provider_identity, secret=secret)
            for provider_identity, secret in sorted(credentials.items())
        )
        return cls(snapshot)

    def resolve(self, provider_identity: str, /) -> Credential:
        if type(provider_identity) is not str or not provider_identity:
            raise ValueError("provider_identity must be non-empty text")
        for credential in self._credentials:
            if credential.provider_identity == provider_identity:
                return credential
        if not self._credentials:
            raise CredentialError(
                code=CredentialErrorCode.MISSING,
                reason=f"credential is missing for provider {provider_identity!r}",
            )
        raise CredentialError(
            code=CredentialErrorCode.PROVIDER_MISMATCH,
            reason=f"credential does not match provider {provider_identity!r}",
        )

    def __repr__(self) -> str:
        provider_identities = tuple(
            credential.provider_identity for credential in self._credentials
        )
        return (
            "StartupCredentialProvider("
            f"provider_identities={provider_identities!r})"
        )


__all__ = [
    "CredentialError",
    "CredentialErrorCode",
    "CredentialProvider",
    "StartupCredentialProvider",
]
