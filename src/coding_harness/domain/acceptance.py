from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json

from coding_harness.domain.models import ContractVersion


class AcceptanceConditionKind(StrEnum):
    MACHINE = "machine"
    USER_CONFIRMATION = "user_confirmation"


class ConditionStatus(StrEnum):
    NOT_RUN = "NOT_RUN"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"

    def __bool__(self) -> bool:
        raise TypeError("condition status has no truth value")


class MachineEvidenceKind(StrEnum):
    VALIDATION = "VALIDATION"


class UserConfirmationAction(StrEnum):
    CONFIRM = "CONFIRM"
    REJECT = "REJECT"


def _is_text(value: object) -> bool:
    return type(value) is str and bool(value) and "\0" not in value


def _is_bounded_text(value: object) -> bool:
    return _is_text(value) and len(value) <= 256


def _is_digest(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _valid_contract_version(value: object, *, task_id: str | None = None) -> bool:
    return (
        type(value) is ContractVersion
        and _is_text(value.identity)
        and _is_text(value.task_id)
        and (task_id is None or value.task_id == task_id)
        and type(value.sequence) is int
        and value.sequence >= 0
        and _is_digest(value.content_digest)
        and _is_text(value.display_text)
    )


@dataclass(frozen=True, slots=True)
class AcceptanceCondition:
    identity: str
    display_text: str
    kind: AcceptanceConditionKind
    required: bool
    status: ConditionStatus
    expected_contract_version_identity: str
    expected_evidence_kind: MachineEvidenceKind | None = None
    expected_producer_identity: str | None = None
    expected_command_identity: str | None = None
    expected_input_digest: str | None = None
    expected_baseline_manifest_digest: str | None = None
    expected_changeset_digest: str | None = None
    reason: str = "NOT_EVALUATED"
    source_result_digest: str | None = None

    def __post_init__(self) -> None:
        if not all(
            _is_text(value)
            for value in (
                self.identity,
                self.display_text,
                self.expected_contract_version_identity,
                self.reason,
            )
        ):
            raise ValueError("invalid acceptance condition")
        if type(self.kind) is not AcceptanceConditionKind:
            raise ValueError("invalid acceptance condition")
        if type(self.required) is not bool or type(self.status) is not ConditionStatus:
            raise ValueError("invalid acceptance condition")
        if self.source_result_digest is not None and not _is_digest(
            self.source_result_digest
        ):
            raise ValueError("invalid acceptance condition")

        machine_bindings = (
            self.expected_evidence_kind,
            self.expected_producer_identity,
            self.expected_command_identity,
            self.expected_input_digest,
            self.expected_baseline_manifest_digest,
            self.expected_changeset_digest,
        )
        if self.kind is AcceptanceConditionKind.MACHINE:
            if type(self.expected_evidence_kind) is not MachineEvidenceKind:
                raise ValueError("invalid acceptance condition")
            if not all(
                _is_text(value)
                for value in (
                    self.expected_producer_identity,
                    self.expected_command_identity,
                )
            ):
                raise ValueError("invalid acceptance condition")
            if not all(
                _is_digest(value)
                for value in (
                    self.expected_input_digest,
                    self.expected_baseline_manifest_digest,
                    self.expected_changeset_digest,
                )
            ):
                raise ValueError("invalid acceptance condition")
        elif any(value is not None for value in machine_bindings):
            raise ValueError("invalid acceptance condition")


@dataclass(frozen=True, slots=True)
class AcceptanceHistoryEvent:
    previous_contract_version_identity: str
    new_contract_version_identity: str
    condition_identity: str
    previous_status: ConditionStatus
    new_status: ConditionStatus
    source_identity: str
    source_kind: str
    source_digest: str
    request_digest: str | None = None
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        if not all(
            _is_text(value)
            for value in (
                self.previous_contract_version_identity,
                self.new_contract_version_identity,
                self.condition_identity,
                self.source_identity,
                self.source_kind,
            )
        ):
            raise ValueError("invalid acceptance history")
        if type(self.previous_status) is not ConditionStatus:
            raise ValueError("invalid acceptance history")
        if type(self.new_status) is not ConditionStatus:
            raise ValueError("invalid acceptance history")
        if not _is_digest(self.source_digest):
            raise ValueError("invalid acceptance history")
        if self.request_digest is not None and not _is_digest(self.request_digest):
            raise ValueError("invalid acceptance history")
        if self.idempotency_key is not None and not _is_text(self.idempotency_key):
            raise ValueError("invalid acceptance history")


@dataclass(frozen=True, slots=True)
class AcceptanceContract:
    task_id: str
    version: ContractVersion
    conditions: tuple[AcceptanceCondition, ...]
    approved: bool
    history: tuple[AcceptanceHistoryEvent, ...] = ()

    def __post_init__(self) -> None:
        if not _is_text(self.task_id):
            raise ValueError("invalid acceptance contract")
        if not _valid_contract_version(self.version, task_id=self.task_id):
            raise ValueError("invalid acceptance contract")
        if type(self.approved) is not bool:
            raise ValueError("invalid acceptance contract")
        if type(self.conditions) not in (list, tuple) or not self.conditions:
            raise ValueError("invalid acceptance contract")
        conditions = tuple(self.conditions)
        if any(type(condition) is not AcceptanceCondition for condition in conditions):
            raise ValueError("invalid acceptance contract")
        identities = tuple(condition.identity for condition in conditions)
        if len(set(identities)) != len(identities):
            raise ValueError("invalid acceptance contract")
        if any(
            condition.expected_contract_version_identity != self.version.identity
            for condition in conditions
        ):
            raise ValueError("invalid acceptance contract")
        if type(self.history) not in (list, tuple):
            raise ValueError("invalid acceptance contract")
        history = tuple(self.history)
        if any(type(event) is not AcceptanceHistoryEvent for event in history):
            raise ValueError("invalid acceptance contract")
        object.__setattr__(self, "conditions", conditions)
        object.__setattr__(self, "history", history)

    @property
    def contract_digest(self) -> str:
        return self.version.content_digest

    @property
    def approval_version_identity(self) -> str | None:
        return self.version.identity if self.approved else None


@dataclass(frozen=True, slots=True)
class MachineEvidence:
    identity: str
    condition_identity: str
    contract_version_identity: str
    kind: MachineEvidenceKind
    producer_identity: str
    command_identity: str
    input_digest: str
    baseline_manifest_digest: str
    changeset_digest: str
    result_digest: str
    status: ConditionStatus
    sequence: int
    occurred_at: int
    bounded_summary: str
    expected_status: ConditionStatus = ConditionStatus.NOT_RUN

    def __post_init__(self) -> None:
        if not all(
            _is_text(value)
            for value in (
                self.identity,
                self.condition_identity,
                self.contract_version_identity,
                self.producer_identity,
                self.command_identity,
            )
        ):
            raise ValueError("invalid machine evidence")
        if type(self.kind) is not MachineEvidenceKind:
            raise ValueError("invalid machine evidence")
        if type(self.status) is not ConditionStatus or self.status is ConditionStatus.NOT_RUN:
            raise ValueError("invalid machine evidence")
        if type(self.expected_status) is not ConditionStatus:
            raise ValueError("invalid machine evidence")
        if not all(
            _is_digest(value)
            for value in (
                self.input_digest,
                self.baseline_manifest_digest,
                self.changeset_digest,
                self.result_digest,
            )
        ):
            raise ValueError("invalid machine evidence")
        if type(self.sequence) is not int or self.sequence < 1:
            raise ValueError("invalid machine evidence")
        if type(self.occurred_at) is not int or self.occurred_at < 0:
            raise ValueError("invalid machine evidence")
        if not _is_bounded_text(self.bounded_summary):
            raise ValueError("invalid machine evidence")


@dataclass(frozen=True, slots=True)
class UserConfirmationCommand:
    identity: str
    task_id: str
    contract_version_identity: str
    condition_identity: str
    expected_status: ConditionStatus
    action: UserConfirmationAction
    request_digest: str
    idempotency_key: str
    occurred_at: int
    authority: str = "user"

    def __post_init__(self) -> None:
        if not all(
            _is_text(value)
            for value in (
                self.identity,
                self.task_id,
                self.contract_version_identity,
                self.condition_identity,
                self.idempotency_key,
            )
        ):
            raise ValueError("invalid user confirmation")
        if type(self.expected_status) is not ConditionStatus:
            raise ValueError("invalid user confirmation")
        if type(self.action) is not UserConfirmationAction:
            raise ValueError("invalid user confirmation")
        if not _is_digest(self.request_digest):
            raise ValueError("invalid user confirmation")
        if type(self.occurred_at) is not int or self.occurred_at < 0:
            raise ValueError("invalid user confirmation")
        if type(self.authority) is not str or self.authority != "user":
            raise ValueError("invalid user confirmation")


@dataclass(frozen=True, slots=True)
class AcceptanceUpdateResult:
    accepted: bool
    conflict: bool
    duplicate: bool
    reason: str
    contract: AcceptanceContract


@dataclass(frozen=True, slots=True)
class ConditionEvaluation:
    condition_identity: str
    kind: AcceptanceConditionKind
    required: bool
    status: ConditionStatus
    satisfied: bool


@dataclass(frozen=True, slots=True)
class AcceptanceEvaluation:
    contract_version_identity: str | None
    condition_results: tuple[ConditionEvaluation, ...]
    unmet_required_conditions: tuple[str, ...]
    eligible_for_apply: bool
    should_apply: bool
    reason: str
    audit_digest: str

    def __bool__(self) -> bool:
        raise TypeError("acceptance evaluation has no truth value")


def _invalid_update(contract: object, reason: str, *, conflict: bool = False):
    if type(contract) is not AcceptanceContract:
        raise ValueError("invalid acceptance contract")
    return AcceptanceUpdateResult(False, conflict, False, reason, contract)


def _condition_by_identity(
    contract: AcceptanceContract,
    identity: str,
) -> AcceptanceCondition | None:
    return next(
        (condition for condition in contract.conditions if condition.identity == identity),
        None,
    )


def _new_version_is_valid(
    contract: AcceptanceContract,
    new_version: object,
) -> bool:
    return (
        _valid_contract_version(new_version, task_id=contract.task_id)
        and new_version.identity != contract.version.identity
        and new_version.sequence > contract.version.sequence
    )


def _updated_contract(
    *,
    contract: AcceptanceContract,
    condition: AcceptanceCondition,
    new_status: ConditionStatus,
    reason: str,
    source_result_digest: str,
    new_version: ContractVersion,
    event: AcceptanceHistoryEvent,
) -> AcceptanceContract:
    conditions = tuple(
        replace(
            item,
            status=new_status if item.identity == condition.identity else item.status,
            expected_contract_version_identity=new_version.identity,
            reason=reason if item.identity == condition.identity else item.reason,
            source_result_digest=(
                source_result_digest
                if item.identity == condition.identity
                else item.source_result_digest
            ),
        )
        for item in contract.conditions
    )
    return AcceptanceContract(
        task_id=contract.task_id,
        version=new_version,
        conditions=conditions,
        approved=False,
        history=contract.history + (event,),
    )


def _evaluation_digest(
    *,
    version_identity: str | None,
    approved: bool,
    condition_results: tuple[ConditionEvaluation, ...],
    eligible: bool,
    reason: str,
) -> str:
    payload = {
        "approved": approved,
        "conditions": [
            {
                "identity": result.condition_identity,
                "kind": result.kind.value,
                "required": result.required,
                "satisfied": result.satisfied,
                "status": result.status.value,
            }
            for result in condition_results
        ],
        "eligible": eligible,
        "reason": reason,
        "version": version_identity,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


class AcceptanceEvaluator:
    def apply_machine_evidence(
        self,
        *,
        contract: object,
        evidence: object,
        new_version: object,
    ) -> AcceptanceUpdateResult:
        if type(contract) is not AcceptanceContract:
            raise ValueError("invalid acceptance contract")
        if type(evidence) is not MachineEvidence:
            return _invalid_update(contract, "INVALID_MACHINE_EVIDENCE")
        condition = _condition_by_identity(contract, evidence.condition_identity)
        if condition is None or condition.kind is not AcceptanceConditionKind.MACHINE:
            return _invalid_update(contract, "MACHINE_EVIDENCE_BINDING_MISMATCH")
        if (
            evidence.contract_version_identity != contract.version.identity
            or condition.expected_contract_version_identity != contract.version.identity
            or evidence.kind is not condition.expected_evidence_kind
            or evidence.producer_identity != condition.expected_producer_identity
            or evidence.command_identity != condition.expected_command_identity
            or evidence.input_digest != condition.expected_input_digest
            or evidence.baseline_manifest_digest
            != condition.expected_baseline_manifest_digest
            or evidence.changeset_digest != condition.expected_changeset_digest
            or evidence.expected_status is not condition.status
        ):
            return _invalid_update(contract, "MACHINE_EVIDENCE_BINDING_MISMATCH")
        if not _new_version_is_valid(contract, new_version):
            return _invalid_update(contract, "CONTRACT_VERSION_CONFLICT", conflict=True)

        event = AcceptanceHistoryEvent(
            previous_contract_version_identity=contract.version.identity,
            new_contract_version_identity=new_version.identity,
            condition_identity=condition.identity,
            previous_status=condition.status,
            new_status=evidence.status,
            source_identity=evidence.identity,
            source_kind="MACHINE_EVIDENCE",
            source_digest=evidence.result_digest,
        )
        updated = _updated_contract(
            contract=contract,
            condition=condition,
            new_status=evidence.status,
            reason="MACHINE_EVIDENCE_ACCEPTED",
            source_result_digest=evidence.result_digest,
            new_version=new_version,
            event=event,
        )
        return AcceptanceUpdateResult(
            True,
            False,
            False,
            "MACHINE_EVIDENCE_ACCEPTED",
            updated,
        )

    def apply_user_confirmation(
        self,
        *,
        contract: object,
        command: object,
        new_version: object,
    ) -> AcceptanceUpdateResult:
        if type(contract) is not AcceptanceContract:
            raise ValueError("invalid acceptance contract")
        if type(command) is not UserConfirmationCommand:
            return _invalid_update(contract, "INVALID_USER_CONFIRMATION")

        prior = next(
            (
                event
                for event in reversed(contract.history)
                if event.idempotency_key == command.idempotency_key
            ),
            None,
        )
        if prior is not None:
            if prior.request_digest == command.request_digest:
                return AcceptanceUpdateResult(
                    True,
                    False,
                    True,
                    "USER_CONFIRMATION_REPLAY",
                    contract,
                )
            return _invalid_update(
                contract,
                "USER_CONFIRMATION_IDEMPOTENCY_CONFLICT",
                conflict=True,
            )

        condition = _condition_by_identity(contract, command.condition_identity)
        if condition is None or condition.kind is not AcceptanceConditionKind.USER_CONFIRMATION:
            return _invalid_update(contract, "USER_CONFIRMATION_BINDING_MISMATCH")
        if (
            command.authority != "user"
            or command.task_id != contract.task_id
            or command.contract_version_identity != contract.version.identity
            or condition.expected_contract_version_identity != contract.version.identity
            or command.expected_status is not condition.status
        ):
            return _invalid_update(contract, "USER_CONFIRMATION_BINDING_MISMATCH")
        if not _new_version_is_valid(contract, new_version):
            return _invalid_update(contract, "CONTRACT_VERSION_CONFLICT", conflict=True)

        new_status = (
            ConditionStatus.PASSED
            if command.action is UserConfirmationAction.CONFIRM
            else ConditionStatus.FAILED
        )
        reason = (
            "USER_CONFIRMED"
            if command.action is UserConfirmationAction.CONFIRM
            else "USER_REJECTED"
        )
        event = AcceptanceHistoryEvent(
            previous_contract_version_identity=contract.version.identity,
            new_contract_version_identity=new_version.identity,
            condition_identity=condition.identity,
            previous_status=condition.status,
            new_status=new_status,
            source_identity=command.identity,
            source_kind="USER_CONFIRMATION",
            source_digest=command.request_digest,
            request_digest=command.request_digest,
            idempotency_key=command.idempotency_key,
        )
        updated = _updated_contract(
            contract=contract,
            condition=condition,
            new_status=new_status,
            reason=reason,
            source_result_digest=command.request_digest,
            new_version=new_version,
            event=event,
        )
        return AcceptanceUpdateResult(True, False, False, reason, updated)

    def evaluate(
        self,
        *,
        contract: object,
        expected_contract_version_identity: object,
        llm_recommendation: object,
    ) -> AcceptanceEvaluation:
        del llm_recommendation
        if type(contract) is not AcceptanceContract:
            reason = "INVALID_ACCEPTANCE_INPUT"
            return AcceptanceEvaluation(
                None,
                (),
                (),
                False,
                False,
                reason,
                _evaluation_digest(
                    version_identity=None,
                    approved=False,
                    condition_results=(),
                    eligible=False,
                    reason=reason,
                ),
            )

        condition_results = tuple(
            ConditionEvaluation(
                condition_identity=condition.identity,
                kind=condition.kind,
                required=condition.required,
                status=condition.status,
                satisfied=condition.status is ConditionStatus.PASSED,
            )
            for condition in contract.conditions
        )
        unmet = tuple(
            result.condition_identity
            for result in condition_results
            if result.required and not result.satisfied
        )
        if (
            type(expected_contract_version_identity) is not str
            or expected_contract_version_identity != contract.version.identity
        ):
            eligible = False
            reason = "CONTRACT_VERSION_CONFLICT"
        elif contract.approval_version_identity != contract.version.identity:
            eligible = False
            reason = (
                "CONTRACT_REAPPROVAL_REQUIRED"
                if contract.history
                else "CONTRACT_APPROVAL_REQUIRED"
            )
        elif unmet:
            eligible = False
            reason = "REQUIRED_CONDITIONS_INCOMPLETE"
        else:
            eligible = True
            reason = "ACCEPTANCE_SATISFIED"
        return AcceptanceEvaluation(
            contract.version.identity,
            condition_results,
            unmet,
            eligible,
            eligible,
            reason,
            _evaluation_digest(
                version_identity=contract.version.identity,
                approved=contract.approved,
                condition_results=condition_results,
                eligible=eligible,
                reason=reason,
            ),
        )


__all__ = [
    "AcceptanceCondition",
    "AcceptanceConditionKind",
    "AcceptanceContract",
    "AcceptanceEvaluation",
    "AcceptanceEvaluator",
    "AcceptanceHistoryEvent",
    "AcceptanceUpdateResult",
    "ConditionEvaluation",
    "ConditionStatus",
    "MachineEvidence",
    "MachineEvidenceKind",
    "UserConfirmationAction",
    "UserConfirmationCommand",
]
