"""Immutable fixed-profile contracts and deterministic repository selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
from pathlib import PurePosixPath


_MAX_SIGNAL_COUNT = 256
_MAX_TEXT_BYTES = 4_096


def _valid_text(value: object) -> bool:
    if type(value) is not str or not value or "\0" in value:
        return False
    try:
        return len(value.encode("utf-8", errors="strict")) <= _MAX_TEXT_BYTES
    except UnicodeError:
        return False


def _valid_signal(value: object) -> bool:
    if not _valid_text(value):
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and value == path.as_posix()
        and all(part not in ("", ".", "..") for part in path.parts)
    )


def _digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class _ClosedEnum(StrEnum):
    def __bool__(self) -> bool:
        raise TypeError(f"{type(self).__name__} has no truth value")


class ProfileId(_ClosedEnum):
    PYTHON312 = "python312"
    NODEJS20_NPM = "nodejs20_npm"


class ProfileSelectionStatus(_ClosedEnum):
    SELECTED = "SELECTED"
    AMBIGUOUS = "AMBIGUOUS"
    UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True, slots=True)
class SandboxProfile:
    identity: ProfileId
    runtime_identity: str
    validation_operations: tuple[str, ...]
    recognition_signals: tuple[str, ...]
    profile_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.identity) is not ProfileId
            or not _valid_text(self.runtime_identity)
            or type(self.validation_operations) is not tuple
            or not self.validation_operations
            or any(
                not _valid_text(operation)
                for operation in self.validation_operations
            )
            or len(set(self.validation_operations))
            != len(self.validation_operations)
            or type(self.recognition_signals) is not tuple
            or not self.recognition_signals
            or any(
                not _valid_signal(signal)
                for signal in self.recognition_signals
            )
            or len(set(self.recognition_signals))
            != len(self.recognition_signals)
        ):
            raise ValueError("sandbox profile is invalid")
        object.__setattr__(
            self,
            "profile_digest",
            _digest(
                {
                    "identity": self.identity.value,
                    "recognition_signals": self.recognition_signals,
                    "runtime_identity": self.runtime_identity,
                    "validation_operations": self.validation_operations,
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class RepositorySignals:
    paths: tuple[str, ...]
    runtime_override: str | None = None
    image_override: str | None = None

    def __post_init__(self) -> None:
        if self.runtime_override is not None or self.image_override is not None:
            raise ValueError("repository cannot override sandbox authority")
        if (
            type(self.paths) is not tuple
            or len(self.paths) > _MAX_SIGNAL_COUNT
            or any(not _valid_signal(path) for path in self.paths)
            or len(set(self.paths)) != len(self.paths)
        ):
            raise ValueError("repository signals are invalid")
        object.__setattr__(self, "paths", tuple(sorted(self.paths)))


@dataclass(frozen=True, slots=True)
class ProfileSelection:
    status: ProfileSelectionStatus
    profile: SandboxProfile | None
    reason: str

    def __post_init__(self) -> None:
        if (
            type(self.status) is not ProfileSelectionStatus
            or not _valid_text(self.reason)
            or (
                self.status is ProfileSelectionStatus.SELECTED
                and type(self.profile) is not SandboxProfile
            )
            or (
                self.status is not ProfileSelectionStatus.SELECTED
                and self.profile is not None
            )
        ):
            raise ValueError("profile selection is invalid")


@dataclass(frozen=True, slots=True)
class ProfileRegistry:
    profiles: tuple[SandboxProfile, ...]

    def __post_init__(self) -> None:
        if (
            type(self.profiles) is not tuple
            or len(self.profiles) != 2
            or any(type(profile) is not SandboxProfile for profile in self.profiles)
            or tuple(profile.identity for profile in self.profiles)
            != (ProfileId.PYTHON312, ProfileId.NODEJS20_NPM)
        ):
            raise ValueError("profile registry is invalid")

    @classmethod
    def default(cls) -> ProfileRegistry:
        return cls(
            profiles=(
                SandboxProfile(
                    identity=ProfileId.PYTHON312,
                    runtime_identity="python:3.12",
                    validation_operations=("pytest", "ruff"),
                    recognition_signals=(
                        "pyproject.toml",
                        "requirements.txt",
                    ),
                ),
                SandboxProfile(
                    identity=ProfileId.NODEJS20_NPM,
                    runtime_identity="nodejs:20/npm",
                    validation_operations=(
                        "test",
                        "lint",
                        "build",
                        "typecheck",
                    ),
                    recognition_signals=(
                        "package.json",
                        "package-lock.json",
                    ),
                ),
            )
        )

    def require(self, identity: ProfileId) -> SandboxProfile:
        if type(identity) is not ProfileId:
            raise ValueError("profile identity is invalid")
        for profile in self.profiles:
            if profile.identity is identity:
                return profile
        raise ValueError("profile identity is unsupported")

    def select(
        self,
        signals: RepositorySignals,
        *,
        llm_suggestion: ProfileId | None = None,
    ) -> ProfileSelection:
        if type(signals) is not RepositorySignals:
            raise ValueError("repository signals are invalid")
        if llm_suggestion is not None and type(llm_suggestion) is not ProfileId:
            raise ValueError("LLM profile suggestion is invalid")
        paths = frozenset(signals.paths)
        python_match = bool(
            paths.intersection(("pyproject.toml", "requirements.txt"))
        )
        node_match = {"package.json", "package-lock.json"}.issubset(paths)
        if python_match and node_match:
            return ProfileSelection(
                status=ProfileSelectionStatus.AMBIGUOUS,
                profile=None,
                reason="repository matches multiple fixed profiles",
            )
        if python_match:
            return ProfileSelection(
                status=ProfileSelectionStatus.SELECTED,
                profile=self.require(ProfileId.PYTHON312),
                reason="repository matches the Python 3.12 profile",
            )
        if node_match:
            return ProfileSelection(
                status=ProfileSelectionStatus.SELECTED,
                profile=self.require(ProfileId.NODEJS20_NPM),
                reason="repository matches the Node.js 20/npm profile",
            )
        return ProfileSelection(
            status=ProfileSelectionStatus.UNSUPPORTED,
            profile=None,
            reason="repository does not match a fixed MVP profile",
        )
