from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from coding_harness.domain.enums import TaskState
from coding_harness.domain.errors import PolicyErrorCode, PolicyReason


class PolicyDecision(StrEnum):
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"
    BLOCKED_POLICY_ERROR = "BLOCKED_POLICY_ERROR"


class PolicyActionKind(StrEnum):
    INSPECT_REPOSITORY = "inspect_repository"
    LIST_FILES = "list_files"
    READ_FILE = "read_file"
    SEARCH_TEXT = "search_text"
    CREATE_FILE = "create_file"
    REPLACE_FILE = "replace_file"
    APPLY_PATCH = "apply_patch"
    RUN_VALIDATION = "run_validation"
    GIT_REPO_PROBE = "git_repo_probe"
    GIT_REPO_ROOT = "git_repo_root"
    GIT_STATUS = "git_status"
    GIT_DIFF_WORKTREE = "git_diff_worktree"
    GIT_DIFF_INDEX = "git_diff_index"
    GIT_LIST_TRACKED = "git_list_tracked"
    DELETE_FILE = "delete_file"
    REQUEST_IGNORED_INPUT = "request_ignored_input"
    NETWORK_READ = "network_read"
    REMOTE_GIT_WRITE = "remote_git_write"
    GIT_PUSH = "git_push"
    CREATE_PULL_REQUEST = "create_pull_request"
    CREATE_MERGE_REQUEST = "create_merge_request"
    DEPLOY = "deploy"
    PUBLISH = "publish"
    RELEASE = "release"
    CLOUD_RESOURCE_CHANGE = "cloud_resource_change"
    PRODUCTION_RESOURCE_CHANGE = "production_resource_change"
    PRODUCTION_DATABASE_WRITE = "production_database_write"
    PRODUCTION_CREDENTIAL_INJECTION = "production_credential_injection"
    EXPOSE_PRODUCTION_SECRET = "expose_production_secret"
    TASK_DOCKER_BUILD = "task_docker_build"
    TASK_DOCKER_RUN = "task_docker_run"
    TASK_DOCKER_CONTROL = "task_docker_control"
    PRIVILEGED_CONTAINER = "privileged_container"
    HOST_NETWORK = "host_network"
    HOST_PID_NAMESPACE = "host_pid_namespace"
    HOST_DEVICE = "host_device"
    ARBITRARY_VOLUME = "arbitrary_volume"
    DOCKER_SOCKET_ACCESS = "docker_socket_access"


@dataclass(frozen=True, slots=True)
class PolicyContext:
    task_id: str
    task_state: TaskState
    action_name: str
    action_identity: str
    action_digest: str
    target_type: str
    target_identity: str | None
    plan_identity: str
    contract_identity: str
    expected_state: TaskState
    idempotency_key: str
    trusted_profile: str
    repository_capability_requests: frozenset[str] | set[str]
    user_approval_present: bool
    llm_suggested_decision: str | None

    def __post_init__(self) -> None:
        requests = self.repository_capability_requests
        if type(requests) not in (set, frozenset):
            raise ValueError("invalid policy context")
        if any(type(request) is not str for request in requests):
            raise ValueError("invalid policy context")
        object.__setattr__(self, "repository_capability_requests", frozenset(requests))
        suggestion = self.llm_suggested_decision
        if suggestion is not None and type(suggestion) is not str:
            raise ValueError("invalid policy context")


@dataclass(frozen=True, slots=True)
class PolicyDecisionRecord:
    decision: PolicyDecision
    reason: PolicyReason
    detail: str | None
    error_code: PolicyErrorCode | None
    action_identity: str | None
    action_digest: str | None
    tool_execution_permitted: bool
    approval_can_override: bool
    effective_profile: str | None
    bound_task_id: str | None
    bound_target_type: str | None
    bound_target_identity: str | None
    bound_digest: str | None
    bound_expected_state: TaskState | None
    bound_idempotency_key: str | None


_ALLOW_ACTIONS = frozenset(
    {
        PolicyActionKind.INSPECT_REPOSITORY,
        PolicyActionKind.LIST_FILES,
        PolicyActionKind.READ_FILE,
        PolicyActionKind.SEARCH_TEXT,
        PolicyActionKind.CREATE_FILE,
        PolicyActionKind.REPLACE_FILE,
        PolicyActionKind.APPLY_PATCH,
        PolicyActionKind.RUN_VALIDATION,
        PolicyActionKind.GIT_REPO_PROBE,
        PolicyActionKind.GIT_REPO_ROOT,
        PolicyActionKind.GIT_STATUS,
        PolicyActionKind.GIT_DIFF_WORKTREE,
        PolicyActionKind.GIT_DIFF_INDEX,
        PolicyActionKind.GIT_LIST_TRACKED,
    }
)

_APPROVAL_ACTIONS = frozenset(
    {
        PolicyActionKind.DELETE_FILE,
        PolicyActionKind.REQUEST_IGNORED_INPUT,
    }
)

_UNSUPPORTED_ACTIONS = frozenset({PolicyActionKind.NETWORK_READ})

_HARD_DENY_ACTIONS = frozenset(
    {
        PolicyActionKind.REMOTE_GIT_WRITE,
        PolicyActionKind.GIT_PUSH,
        PolicyActionKind.CREATE_PULL_REQUEST,
        PolicyActionKind.CREATE_MERGE_REQUEST,
        PolicyActionKind.DEPLOY,
        PolicyActionKind.PUBLISH,
        PolicyActionKind.RELEASE,
        PolicyActionKind.CLOUD_RESOURCE_CHANGE,
        PolicyActionKind.PRODUCTION_RESOURCE_CHANGE,
        PolicyActionKind.PRODUCTION_DATABASE_WRITE,
        PolicyActionKind.PRODUCTION_CREDENTIAL_INJECTION,
        PolicyActionKind.EXPOSE_PRODUCTION_SECRET,
        PolicyActionKind.TASK_DOCKER_BUILD,
        PolicyActionKind.TASK_DOCKER_RUN,
        PolicyActionKind.TASK_DOCKER_CONTROL,
        PolicyActionKind.PRIVILEGED_CONTAINER,
        PolicyActionKind.HOST_NETWORK,
        PolicyActionKind.HOST_PID_NAMESPACE,
        PolicyActionKind.HOST_DEVICE,
        PolicyActionKind.ARBITRARY_VOLUME,
        PolicyActionKind.DOCKER_SOCKET_ACCESS,
    }
)


class PolicyEngine:
    @staticmethod
    def decide(*, context: object) -> PolicyDecisionRecord:
        try:
            return PolicyEngine._decide(context=context)
        except Exception:
            return PolicyEngine._blocked(
                error_code=PolicyErrorCode.POLICY_EVALUATION_FAILURE,
            )

    @staticmethod
    def _decide(*, context: object) -> PolicyDecisionRecord:
        if type(context) is not PolicyContext:
            return PolicyEngine._blocked(
                error_code=PolicyErrorCode.INVALID_POLICY_CONTEXT,
            )
        if not PolicyEngine._context_is_valid(context):
            return PolicyEngine._blocked(
                context=context,
                error_code=PolicyErrorCode.INVALID_POLICY_CONTEXT,
            )
        try:
            action = PolicyActionKind(context.action_name)
        except ValueError:
            return PolicyEngine._blocked(
                context=context,
                error_code=PolicyErrorCode.UNKNOWN_ACTION,
            )

        if action in _HARD_DENY_ACTIONS:
            return PolicyEngine._record(
                context=context,
                decision=PolicyDecision.DENY,
                reason=PolicyReason.DENIED_CAPABILITY,
                detail="permanent hard boundary",
                tool_execution_permitted=False,
                approval_can_override=False,
            )
        if action in _UNSUPPORTED_ACTIONS:
            return PolicyEngine._record(
                context=context,
                decision=PolicyDecision.DENY,
                reason=PolicyReason.BLOCKED_UNSUPPORTED_CAPABILITY,
                detail="unsupported capability",
                tool_execution_permitted=False,
                approval_can_override=False,
            )
        if action in _APPROVAL_ACTIONS:
            return PolicyEngine._record(
                context=context,
                decision=PolicyDecision.REQUIRE_APPROVAL,
                reason=PolicyReason.APPROVAL_REQUIRED,
                detail="bound approval required",
                tool_execution_permitted=False,
                approval_can_override=True,
            )
        if action in _ALLOW_ACTIONS:
            return PolicyEngine._record(
                context=context,
                decision=PolicyDecision.ALLOW,
                reason=PolicyReason.ALLOWED,
                detail=None,
                tool_execution_permitted=True,
                approval_can_override=False,
            )
        return PolicyEngine._blocked(
            context=context,
            error_code=PolicyErrorCode.POLICY_EVALUATION_FAILURE,
        )

    @staticmethod
    def _context_is_valid(context: PolicyContext) -> bool:
        required_strings = (
            context.task_id,
            context.action_name,
            context.action_identity,
            context.action_digest,
            context.target_type,
            context.target_identity,
            context.plan_identity,
            context.contract_identity,
            context.idempotency_key,
            context.trusted_profile,
        )
        if any(type(value) is not str or not value for value in required_strings):
            return False
        if type(context.task_state) is not TaskState:
            return False
        if type(context.expected_state) is not TaskState:
            return False
        if context.expected_state is not context.task_state:
            return False
        if type(context.user_approval_present) is not bool:
            return False
        if type(context.repository_capability_requests) is not frozenset:
            return False
        if len(context.action_digest) != 64:
            return False
        if any(character not in "0123456789abcdef" for character in context.action_digest):
            return False
        return True

    @staticmethod
    def _blocked(
        *,
        error_code: PolicyErrorCode,
        context: PolicyContext | None = None,
    ) -> PolicyDecisionRecord:
        return PolicyDecisionRecord(
            decision=PolicyDecision.BLOCKED_POLICY_ERROR,
            reason=PolicyReason.BLOCKED_POLICY_ERROR,
            detail="policy context rejected",
            error_code=error_code,
            action_identity=context.action_identity if context is not None else None,
            action_digest=context.action_digest if context is not None else None,
            tool_execution_permitted=False,
            approval_can_override=False,
            effective_profile=context.trusted_profile if context is not None else None,
            bound_task_id=None,
            bound_target_type=None,
            bound_target_identity=None,
            bound_digest=None,
            bound_expected_state=None,
            bound_idempotency_key=None,
        )

    @staticmethod
    def _record(
        *,
        context: PolicyContext,
        decision: PolicyDecision,
        reason: PolicyReason,
        detail: str | None,
        tool_execution_permitted: bool,
        approval_can_override: bool,
    ) -> PolicyDecisionRecord:
        return PolicyDecisionRecord(
            decision=decision,
            reason=reason,
            detail=detail,
            error_code=None,
            action_identity=context.action_identity,
            action_digest=context.action_digest,
            tool_execution_permitted=tool_execution_permitted,
            approval_can_override=approval_can_override,
            effective_profile=context.trusted_profile,
            bound_task_id=context.task_id,
            bound_target_type=context.target_type,
            bound_target_identity=context.target_identity,
            bound_digest=context.action_digest,
            bound_expected_state=context.expected_state,
            bound_idempotency_key=context.idempotency_key,
        )
