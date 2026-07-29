"""Structured, side-effect-free sandbox preflight contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json

from coding_harness.sandbox.profiles import ProfileId, SandboxProfile


_MAX_TEXT_BYTES = 4_096
_MAX_ITEMS = 256


def _valid_text(value: object) -> bool:
    if type(value) is not str or not value or "\0" in value:
        return False
    try:
        return len(value.encode("utf-8", errors="strict")) <= _MAX_TEXT_BYTES
    except UnicodeError:
        return False


def _valid_optional_text(value: object) -> bool:
    return value is None or _valid_text(value)


def _valid_text_tuple(value: object) -> bool:
    return (
        type(value) is tuple
        and len(value) <= _MAX_ITEMS
        and all(_valid_text(item) for item in value)
        and len(set(value)) == len(value)
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


class PreflightStatus(_ClosedEnum):
    READY = "READY"
    BLOCKED_MISSING_DEPENDENCY = "BLOCKED_MISSING_DEPENDENCY"
    BLOCKED_UNSUPPORTED_ENVIRONMENT = "BLOCKED_UNSUPPORTED_ENVIRONMENT"


@dataclass(frozen=True, slots=True)
class ProbeEvidence:
    runtime_identity: str
    available_operations: tuple[str, ...]
    missing_dependencies: tuple[str, ...]
    validation_stderr: str | None
    bounded_summary: str
    evidence_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            not _valid_text(self.runtime_identity)
            or not _valid_text_tuple(self.available_operations)
            or not _valid_text_tuple(self.missing_dependencies)
            or not _valid_optional_text(self.validation_stderr)
            or not _valid_text(self.bounded_summary)
        ):
            raise ValueError("preflight probe evidence is invalid")
        object.__setattr__(
            self,
            "evidence_digest",
            _digest(
                {
                    "available_operations": self.available_operations,
                    "bounded_summary": self.bounded_summary,
                    "missing_dependencies": self.missing_dependencies,
                    "runtime_identity": self.runtime_identity,
                    "validation_stderr": self.validation_stderr,
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class PreflightResult:
    profile_identity: ProfileId
    status: PreflightStatus
    blocked_reason: str | None
    bounded_explanation: str
    source_evidence_digest: str
    result_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.profile_identity) is not ProfileId
            or type(self.status) is not PreflightStatus
            or not _valid_optional_text(self.blocked_reason)
            or not _valid_text(self.bounded_explanation)
            or (
                type(self.source_evidence_digest) is not str
                or len(self.source_evidence_digest) != 64
                or set(self.source_evidence_digest)
                - set("0123456789abcdef")
            )
            or (
                self.status is PreflightStatus.READY
                and self.blocked_reason is not None
            )
            or (
                self.status is not PreflightStatus.READY
                and self.blocked_reason != self.status.value
            )
        ):
            raise ValueError("preflight result is invalid")
        object.__setattr__(
            self,
            "result_digest",
            _digest(
                {
                    "blocked_reason": self.blocked_reason,
                    "bounded_explanation": self.bounded_explanation,
                    "profile_identity": self.profile_identity.value,
                    "source_evidence_digest": self.source_evidence_digest,
                    "status": self.status.value,
                }
            ),
        )


class Preflight:
    @staticmethod
    def evaluate(
        *,
        profile: SandboxProfile,
        evidence: ProbeEvidence,
    ) -> PreflightResult:
        if (
            type(profile) is not SandboxProfile
            or type(evidence) is not ProbeEvidence
        ):
            raise ValueError("preflight input is invalid")
        if evidence.runtime_identity != profile.runtime_identity:
            status = PreflightStatus.BLOCKED_UNSUPPORTED_ENVIRONMENT
            explanation = "runtime does not match the selected profile"
        elif evidence.missing_dependencies:
            status = PreflightStatus.BLOCKED_MISSING_DEPENDENCY
            explanation = "structured probe reports a missing dependency"
        elif profile.validation_operations[0] not in frozenset(
            evidence.available_operations
        ):
            status = PreflightStatus.BLOCKED_MISSING_DEPENDENCY
            explanation = "required validation operation is unavailable"
        else:
            status = PreflightStatus.READY
            explanation = "structured preflight checks are ready"
        return PreflightResult(
            profile_identity=profile.identity,
            status=status,
            blocked_reason=None if status is PreflightStatus.READY else status.value,
            bounded_explanation=explanation,
            source_evidence_digest=evidence.evidence_digest,
        )


@dataclass(frozen=True, slots=True)
class ValidationEvidence:
    action: str
    profile_identity: ProfileId
    exit_status: int
    bounded_output_summary: str
    occurred_at: int
    evidence_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            not _valid_text(self.action)
            or type(self.profile_identity) is not ProfileId
            or type(self.exit_status) is not int
            or not _valid_text(self.bounded_output_summary)
            or type(self.occurred_at) is not int
            or self.occurred_at < 0
        ):
            raise ValueError("validation evidence is invalid")
        object.__setattr__(
            self,
            "evidence_digest",
            hashlib.sha256(self.canonical_bytes()).hexdigest(),
        )

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            {
                "action": self.action,
                "bounded_output_summary": self.bounded_output_summary,
                "exit_status": self.exit_status,
                "occurred_at": self.occurred_at,
                "profile_identity": self.profile_identity.value,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
