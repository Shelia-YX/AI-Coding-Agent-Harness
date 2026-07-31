"""Course-level immutable credential contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import unicodedata


_MAX_PROVIDER_IDENTITY_BYTES = 256
_MAX_SECRET_BYTES = 65_536


def _provider_identity(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("provider_identity must be non-empty text")
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeError:
        raise ValueError("provider_identity must be valid UTF-8") from None
    if (
        len(encoded) > _MAX_PROVIDER_IDENTITY_BYTES
        or any(unicodedata.category(character).startswith("C") for character in value)
    ):
        raise ValueError("provider_identity is outside the trusted boundary")
    return value


def _secret(value: object) -> bytes:
    if type(value) is not bytes or not value or len(value) > _MAX_SECRET_BYTES:
        raise ValueError("credential secret must be non-empty bounded bytes")
    return value


def _slot_reference(provider_identity: str) -> str:
    identity_digest = hashlib.sha256(provider_identity.encode("utf-8")).hexdigest()
    return f"startup:{identity_digest[:16]}"


@dataclass(frozen=True, slots=True, repr=False)
class Credential:
    """One provider-bound credential held only in the current process."""

    provider_identity: str
    secret: bytes = field(repr=False)
    slot_reference: str = field(init=False)

    def __post_init__(self) -> None:
        provider_identity = _provider_identity(self.provider_identity)
        _secret(self.secret)
        object.__setattr__(
            self,
            "slot_reference",
            _slot_reference(provider_identity),
        )

    def secret_bytes(self) -> bytes:
        """Return secret material only through an explicit access operation."""

        return self.secret

    def __repr__(self) -> str:
        return (
            "Credential("
            f"provider_identity={self.provider_identity!r}, "
            f"slot_reference={self.slot_reference!r}, "
            "secret=<redacted>)"
        )

    __str__ = __repr__


__all__ = ["Credential"]
