"""Read-only doctor facts, classification, and deterministic reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json


_MAX_TEXT_BYTES = 4_096
_MAX_CAPABILITIES = 256


def _valid_text(value: object) -> bool:
    if type(value) is not str or not value or "\0" in value:
        return False
    try:
        return len(value.encode("utf-8", errors="strict")) <= _MAX_TEXT_BYTES
    except UnicodeError:
        return False


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


class DoctorCheckKind(_ClosedEnum):
    RUNTIME_AVAILABILITY = "RUNTIME_AVAILABILITY"
    WORKSPACE_MAPPING = "WORKSPACE_MAPPING"
    CONFIGURED_CAPABILITY = "CONFIGURED_CAPABILITY"


class DoctorCheckStatus(_ClosedEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class CapabilityFact:
    identity: str
    trusted: bool

    def __post_init__(self) -> None:
        if not _valid_text(self.identity) or type(self.trusted) is not bool:
            raise ValueError("doctor capability fact is invalid")


@dataclass(frozen=True, slots=True)
class DoctorFacts:
    runtime_identity: str
    runtime_available: bool
    workspace_reference: str
    workspace_mapping_valid: bool
    capabilities: tuple[CapabilityFact, ...]
    bounded_output: str
    facts_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            not _valid_text(self.runtime_identity)
            or type(self.runtime_available) is not bool
            or not _valid_text(self.workspace_reference)
            or type(self.workspace_mapping_valid) is not bool
            or type(self.capabilities) is not tuple
            or not self.capabilities
            or len(self.capabilities) > _MAX_CAPABILITIES
            or any(
                type(capability) is not CapabilityFact
                for capability in self.capabilities
            )
            or len({capability.identity for capability in self.capabilities})
            != len(self.capabilities)
            or not _valid_text(self.bounded_output)
        ):
            raise ValueError("doctor facts are invalid")
        object.__setattr__(
            self,
            "facts_digest",
            _digest(
                {
                    "bounded_output": self.bounded_output,
                    "capabilities": tuple(
                        {
                            "identity": capability.identity,
                            "trusted": capability.trusted,
                        }
                        for capability in self.capabilities
                    ),
                    "runtime_available": self.runtime_available,
                    "runtime_identity": self.runtime_identity,
                    "workspace_mapping_valid": self.workspace_mapping_valid,
                    "workspace_reference": self.workspace_reference,
                }
            ),
        )


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    kind: DoctorCheckKind
    status: DoctorCheckStatus
    bounded_summary: str

    def __post_init__(self) -> None:
        if (
            type(self.kind) is not DoctorCheckKind
            or type(self.status) is not DoctorCheckStatus
            or not _valid_text(self.bounded_summary)
        ):
            raise ValueError("doctor check is invalid")


@dataclass(frozen=True, slots=True)
class DoctorReport:
    checks: tuple[DoctorCheck, ...]
    ready: bool
    occurred_at: int
    bounded_output: str
    source_facts_digest: str
    report_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.checks) is not tuple
            or tuple(check.kind for check in self.checks)
            != (
                DoctorCheckKind.RUNTIME_AVAILABILITY,
                DoctorCheckKind.WORKSPACE_MAPPING,
                DoctorCheckKind.CONFIGURED_CAPABILITY,
            )
            or any(type(check) is not DoctorCheck for check in self.checks)
            or type(self.ready) is not bool
            or self.ready
            != all(
                check.status is DoctorCheckStatus.PASSED
                for check in self.checks
            )
            or type(self.occurred_at) is not int
            or self.occurred_at < 0
            or not _valid_text(self.bounded_output)
            or (
                type(self.source_facts_digest) is not str
                or len(self.source_facts_digest) != 64
                or set(self.source_facts_digest)
                - set("0123456789abcdef")
            )
        ):
            raise ValueError("doctor report is invalid")
        object.__setattr__(
            self,
            "report_digest",
            _digest(
                {
                    "bounded_output": self.bounded_output,
                    "checks": tuple(
                        {
                            "bounded_summary": check.bounded_summary,
                            "kind": check.kind.value,
                            "status": check.status.value,
                        }
                        for check in self.checks
                    ),
                    "occurred_at": self.occurred_at,
                    "ready": self.ready,
                    "source_facts_digest": self.source_facts_digest,
                }
            ),
        )


class Doctor:
    @staticmethod
    def evaluate(facts: DoctorFacts, *, occurred_at: int) -> DoctorReport:
        if type(facts) is not DoctorFacts:
            raise ValueError("doctor facts are invalid")
        runtime_status = (
            DoctorCheckStatus.PASSED
            if facts.runtime_available
            else DoctorCheckStatus.FAILED
        )
        workspace_status = (
            DoctorCheckStatus.PASSED
            if facts.workspace_mapping_valid
            else DoctorCheckStatus.FAILED
        )
        capability_status = (
            DoctorCheckStatus.PASSED
            if all(capability.trusted for capability in facts.capabilities)
            else DoctorCheckStatus.FAILED
        )
        checks = (
            DoctorCheck(
                kind=DoctorCheckKind.RUNTIME_AVAILABILITY,
                status=runtime_status,
                bounded_summary=(
                    "configured runtime is available"
                    if runtime_status is DoctorCheckStatus.PASSED
                    else "configured runtime is unavailable"
                ),
            ),
            DoctorCheck(
                kind=DoctorCheckKind.WORKSPACE_MAPPING,
                status=workspace_status,
                bounded_summary=(
                    "workspace mapping is valid"
                    if workspace_status is DoctorCheckStatus.PASSED
                    else "workspace mapping is invalid"
                ),
            ),
            DoctorCheck(
                kind=DoctorCheckKind.CONFIGURED_CAPABILITY,
                status=capability_status,
                bounded_summary=(
                    "configured capability facts are trusted"
                    if capability_status is DoctorCheckStatus.PASSED
                    else "configured capability facts are untrusted"
                ),
            ),
        )
        return DoctorReport(
            checks=checks,
            ready=all(
                check.status is DoctorCheckStatus.PASSED
                for check in checks
            ),
            occurred_at=occurred_at,
            bounded_output=facts.bounded_output,
            source_facts_digest=facts.facts_digest,
        )
