from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import importlib

import pytest


def _api():
    try:
        profiles = importlib.import_module(
            "coding_harness.sandbox.profiles"
        )
        preflight = importlib.import_module(
            "coding_harness.sandbox.preflight"
        )
    except ModuleNotFoundError as error:
        if error.name in {
            "coding_harness.sandbox",
            "coding_harness.sandbox.profiles",
            "coding_harness.sandbox.preflight",
        }:
            pytest.fail(
                "EXPECTED_INTERFACE_MISSING: sandbox preflight contract",
                pytrace=False,
            )
        raise
    return profiles, preflight


def _python_profile(profiles):
    return profiles.ProfileRegistry.default().require(
        profiles.ProfileId.PYTHON312
    )


def _probe(preflight, **overrides):
    values = {
        "runtime_identity": "python:3.12",
        "available_operations": ("pytest",),
        "missing_dependencies": (),
        "validation_stderr": None,
        "bounded_summary": "runtime and pytest are available",
    }
    values.update(overrides)
    return preflight.ProbeEvidence(**values)


def test_valid_environment_is_ready() -> None:
    profiles, preflight = _api()
    result = preflight.Preflight.evaluate(
        profile=_python_profile(profiles),
        evidence=_probe(preflight),
    )
    assert result.status is preflight.PreflightStatus.READY
    assert result.blocked_reason is None


def test_structured_missing_dependency_is_blocked() -> None:
    profiles, preflight = _api()
    result = preflight.Preflight.evaluate(
        profile=_python_profile(profiles),
        evidence=_probe(
            preflight,
            missing_dependencies=("pytest",),
            bounded_summary="pytest is absent",
        ),
    )
    assert (
        result.status
        is preflight.PreflightStatus.BLOCKED_MISSING_DEPENDENCY
    )
    assert result.blocked_reason == "BLOCKED_MISSING_DEPENDENCY"


def test_stderr_does_not_infer_missing_dependency() -> None:
    profiles, preflight = _api()
    result = preflight.Preflight.evaluate(
        profile=_python_profile(profiles),
        evidence=_probe(
            preflight,
            validation_stderr="ModuleNotFoundError: project.module",
        ),
    )
    assert result.status is preflight.PreflightStatus.READY
    assert result.blocked_reason is None


def test_runtime_mismatch_is_unsupported_environment() -> None:
    profiles, preflight = _api()
    result = preflight.Preflight.evaluate(
        profile=_python_profile(profiles),
        evidence=_probe(
            preflight,
            runtime_identity="python:3.11",
            bounded_summary="unexpected runtime",
        ),
    )
    assert (
        result.status
        is preflight.PreflightStatus.BLOCKED_UNSUPPORTED_ENVIRONMENT
    )


@pytest.mark.parametrize(
    "changes",
    (
        {"available_operations": ["pytest"]},
        {"missing_dependencies": ["pytest"]},
        {"runtime_identity": ""},
    ),
)
def test_malformed_probe_evidence_fails_closed(
    changes: dict[str, object],
) -> None:
    _, preflight = _api()
    with pytest.raises(ValueError):
        _probe(preflight, **changes)


def test_oversized_probe_evidence_fails_closed() -> None:
    _, preflight = _api()
    with pytest.raises(ValueError):
        _probe(preflight, bounded_summary="é" * 2_049)


def test_validation_evidence_records_required_fields_and_digest() -> None:
    profiles, preflight = _api()
    evidence = preflight.ValidationEvidence(
        action="pytest",
        profile_identity=profiles.ProfileId.PYTHON312,
        exit_status=0,
        bounded_output_summary="52 tests passed",
        occurred_at=100,
    )
    duplicate = preflight.ValidationEvidence(
        action="pytest",
        profile_identity=profiles.ProfileId.PYTHON312,
        exit_status=0,
        bounded_output_summary="52 tests passed",
        occurred_at=100,
    )
    assert evidence.evidence_digest == duplicate.evidence_digest
    assert len(evidence.evidence_digest) == 64
    with pytest.raises(FrozenInstanceError):
        evidence.exit_status = 1


def test_validation_evidence_canonical_bytes_are_deterministic() -> None:
    profiles, preflight = _api()
    first = preflight.ValidationEvidence(
        action="pytest",
        profile_identity=profiles.ProfileId.PYTHON312,
        exit_status=0,
        bounded_output_summary="52 tests passed",
        occurred_at=100,
    )
    second = preflight.ValidationEvidence(
        action="pytest",
        profile_identity=profiles.ProfileId.PYTHON312,
        exit_status=0,
        bounded_output_summary="52 tests passed",
        occurred_at=100,
    )
    expected = (
        b'{"action":"pytest","bounded_output_summary":"52 tests passed",'
        b'"exit_status":0,"occurred_at":100,'
        b'"profile_identity":"python312"}'
    )
    assert first.canonical_bytes() == expected
    assert second.canonical_bytes() == expected


def test_validation_evidence_digest_is_sha256_of_canonical_bytes() -> None:
    profiles, preflight = _api()
    evidence = preflight.ValidationEvidence(
        action="pytest",
        profile_identity=profiles.ProfileId.PYTHON312,
        exit_status=0,
        bounded_output_summary="52 tests passed",
        occurred_at=100,
    )
    assert evidence.evidence_digest == hashlib.sha256(
        evidence.canonical_bytes()
    ).hexdigest()


def test_validation_evidence_field_change_changes_digest() -> None:
    profiles, preflight = _api()
    original = preflight.ValidationEvidence(
        action="pytest",
        profile_identity=profiles.ProfileId.PYTHON312,
        exit_status=0,
        bounded_output_summary="52 tests passed",
        occurred_at=100,
    )
    changed = preflight.ValidationEvidence(
        action="pytest",
        profile_identity=profiles.ProfileId.PYTHON312,
        exit_status=1,
        bounded_output_summary="52 tests passed",
        occurred_at=100,
    )
    assert original.evidence_digest != changed.evidence_digest


def test_validation_evidence_rejects_oversized_output() -> None:
    profiles, preflight = _api()
    with pytest.raises(ValueError):
        preflight.ValidationEvidence(
            action="pytest",
            profile_identity=profiles.ProfileId.PYTHON312,
            exit_status=0,
            bounded_output_summary="é" * 2_049,
            occurred_at=100,
        )


@pytest.mark.parametrize(
    "requirement_id",
    ("SBX-005", "ACC-008", "ACC-009"),
)
def test_spec_requirement(requirement_id: str) -> None:
    profiles, preflight = _api()
    profile = _python_profile(profiles)
    if requirement_id == "SBX-005":
        result = preflight.Preflight.evaluate(
            profile=profile,
            evidence=_probe(
                preflight,
                missing_dependencies=("pytest",),
            ),
        )
        assert result.blocked_reason == "BLOCKED_MISSING_DEPENDENCY"
        return
    if requirement_id == "ACC-008":
        result = preflight.Preflight.evaluate(
            profile=profile,
            evidence=_probe(
                preflight,
                validation_stderr="missing dependency",
            ),
        )
        assert result.status is preflight.PreflightStatus.READY
        return
    evidence = preflight.ValidationEvidence(
        action="pytest",
        profile_identity=profiles.ProfileId.PYTHON312,
        exit_status=1,
        bounded_output_summary="validation failed",
        occurred_at=101,
    )
    assert evidence.action == "pytest"
    assert evidence.profile_identity is profiles.ProfileId.PYTHON312
    assert evidence.exit_status == 1
    assert evidence.occurred_at == 101
    assert len(evidence.evidence_digest) == 64
