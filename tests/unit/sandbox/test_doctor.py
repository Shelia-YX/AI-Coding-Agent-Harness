from __future__ import annotations

from dataclasses import FrozenInstanceError
import importlib

import pytest


def _api():
    try:
        return importlib.import_module("coding_harness.sandbox.doctor")
    except ModuleNotFoundError as error:
        if error.name in {
            "coding_harness.sandbox",
            "coding_harness.sandbox.doctor",
        }:
            pytest.fail(
                "EXPECTED_INTERFACE_MISSING: sandbox doctor contract",
                pytrace=False,
            )
        raise


def _facts(api, **overrides):
    values = {
        "runtime_identity": "python:3.12",
        "runtime_available": True,
        "workspace_reference": "workspace:task-1",
        "workspace_mapping_valid": True,
        "capabilities": (
            api.CapabilityFact(identity="network:none", trusted=True),
        ),
        "bounded_output": "doctor checks completed",
    }
    values.update(overrides)
    return api.DoctorFacts(**values)


def test_runtime_availability_is_reported() -> None:
    api = _api()
    report = api.Doctor.evaluate(_facts(api), occurred_at=100)
    runtime = next(
        check
        for check in report.checks
        if check.kind is api.DoctorCheckKind.RUNTIME_AVAILABILITY
    )
    assert runtime.status is api.DoctorCheckStatus.PASSED
    assert report.ready is True


def test_workspace_mapping_failure_blocks_report() -> None:
    api = _api()
    report = api.Doctor.evaluate(
        _facts(api, workspace_mapping_valid=False),
        occurred_at=100,
    )
    mapping = next(
        check
        for check in report.checks
        if check.kind is api.DoctorCheckKind.WORKSPACE_MAPPING
    )
    assert mapping.status is api.DoctorCheckStatus.FAILED
    assert report.ready is False


def test_untrusted_capability_is_reported_without_repair() -> None:
    api = _api()
    report = api.Doctor.evaluate(
        _facts(
            api,
            capabilities=(
                api.CapabilityFact(
                    identity="network:none",
                    trusted=False,
                ),
            ),
        ),
        occurred_at=100,
    )
    capability = next(
        check
        for check in report.checks
        if check.kind is api.DoctorCheckKind.CONFIGURED_CAPABILITY
    )
    assert capability.status is api.DoctorCheckStatus.FAILED
    assert report.ready is False
    assert not hasattr(report, "repair")
    assert not hasattr(report, "cleanup")


def test_doctor_output_is_utf8_byte_bounded() -> None:
    api = _api()
    with pytest.raises(ValueError):
        _facts(api, bounded_output="é" * 2_049)


def test_doctor_report_digest_is_deterministic() -> None:
    api = _api()
    first = api.Doctor.evaluate(_facts(api), occurred_at=100)
    second = api.Doctor.evaluate(_facts(api), occurred_at=100)
    assert first.report_digest == second.report_digest
    assert len(first.report_digest) == 64
    assert set(first.report_digest) <= set("0123456789abcdef")
    with pytest.raises(FrozenInstanceError):
        first.ready = False


@pytest.mark.parametrize(
    ("field_name", "changed_value"),
    (
        ("runtime_identity", "nodejs:20/npm"),
        ("workspace_reference", "workspace:task-2"),
        ("capabilities", "different-capability"),
    ),
)
def test_doctor_report_digest_binds_fact_identities(
    field_name: str,
    changed_value: str,
) -> None:
    api = _api()
    value: object = changed_value
    if field_name == "capabilities":
        value = (
            api.CapabilityFact(
                identity="filesystem:workspace-only",
                trusted=True,
            ),
        )
    original = api.Doctor.evaluate(_facts(api), occurred_at=100)
    changed = api.Doctor.evaluate(
        _facts(api, **{field_name: value}),
        occurred_at=100,
    )
    assert original.report_digest != changed.report_digest


@pytest.mark.parametrize("requirement_id", ("SBX-013",))
def test_spec_requirement(requirement_id: str) -> None:
    api = _api()
    report = api.Doctor.evaluate(_facts(api), occurred_at=100)
    assert requirement_id == "SBX-013"
    assert tuple(check.kind for check in report.checks) == (
        api.DoctorCheckKind.RUNTIME_AVAILABILITY,
        api.DoctorCheckKind.WORKSPACE_MAPPING,
        api.DoctorCheckKind.CONFIGURED_CAPABILITY,
    )
    assert report.ready is True
