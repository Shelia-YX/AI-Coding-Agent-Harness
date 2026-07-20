"""Bounded parsing for the WP-02 structured action wire format."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import math
import re
from typing import Any
import unicodedata


_MAX_INPUT_BYTES = 65_536
_MAX_CONTAINER_DEPTH = 16
_MAX_CONTAINER_KEYS = 64
_MAX_ARRAY_ITEMS = 256
_MAX_INTEGER = 2**63 - 1
_MAX_ERROR_COMPONENT = 256
_MAX_NORMALIZED_DEPTH = _MAX_CONTAINER_DEPTH + 3

_TOP_LEVEL_FIELDS = frozenset(
    {"action_id", "action_type", "parameters", "budget_impact", "expected_result_type"}
)
_ACTION_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", re.ASCII)
_BUDGET_KEY_RE = re.compile(r"[a-z][a-z0-9_]{0,63}", re.ASCII)
_SAFE_PATH_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}", re.ASCII)
_FORBIDDEN_COMMAND_FIELDS = frozenset(
    {"command", "cmd", "shell", "argv", "git_command", "docker_command", "script"}
)
_NORMALIZED_FORBIDDEN_COMMAND_FIELDS = frozenset(
    unicodedata.normalize("NFKC", field).casefold()
    for field in _FORBIDDEN_COMMAND_FIELDS
)
_IGNORED_INPUT_MODES = frozenset({"read_only_input", "writable_ephemeral"})
_IGNORED_INPUT_PHASES = frozenset({"INVESTIGATING", "EXECUTING", "VERIFYING"})
_VALIDATION_OPERATIONS = {
    "python312": frozenset({"pytest", "ruff"}),
    "nodejs20_npm": frozenset({"test", "lint", "build", "typecheck"}),
}

_CONTROL_FIELDS = {
    "request_clarification": "question",
    "propose_plan": "proposal",
    "request_budget_extension": "request",
    "request_user_confirmation": "condition",
    "report_blocked": "report",
    "stop_with_failure": "report",
    "stop_without_safe_action": "report",
}
_TOOL_TYPES = frozenset(
    {
        "inspect_repository",
        "list_files",
        "read_file",
        "search_text",
        "create_file",
        "replace_file",
        "apply_patch",
        "delete_file",
        "request_ignored_input",
        "run_validation",
        "git_repo_probe",
        "git_repo_root",
        "git_status",
        "git_diff_worktree",
        "git_diff_index",
        "git_list_tracked",
        "git_list_untracked",
        "git_stage_paths",
        "git_unstage_paths",
    }
)
_GOVERNANCE_TYPES = frozenset(
    {
        "submit_clarification",
        "approve_plan",
        "reject_plan",
        "approve_action",
        "reject_action",
        "approve_budget_extension",
        "reject_budget_extension",
        "confirm_user_acceptance",
        "reject_user_acceptance",
        "continue_task",
        "cancel_task",
        "confirm_apply",
        "reject_apply",
        "request_recovery",
    }
)
_INTERNAL_TYPES = frozenset(
    {
        "build_baseline",
        "materialize_workspace",
        "materialize_ignored_input",
        "create_action_approval_request",
        "compute_changeset",
        "evaluate_acceptance",
        "acquire_execution_lease",
        "release_execution_lease",
        "begin_apply_transaction",
        "advance_apply_phase",
        "recover_apply_transaction",
        "publish_domain_event",
    }
)


class ActionParseError(ValueError):
    """A bounded, structured rejection of an action payload."""

    _CODES = frozenset(
        {"INVALID_JSON", "INVALID_ACTION", "INVALID_FIELD", "INVALID_VALUE", "INPUT_TOO_LARGE"}
    )

    def __init__(self, code: str, field_path: str, reason: str) -> None:
        if code not in self._CODES:
            raise ValueError("unknown action parse error code")
        if type(field_path) is not str or not field_path:
            raise ValueError("field_path must be a non-empty string")
        if type(reason) is not str or not reason:
            raise ValueError("reason must be a non-empty string")
        if len(field_path) > _MAX_ERROR_COMPONENT:
            field_path = "$.<path-omitted>"
        if len(reason) > _MAX_ERROR_COMPONENT:
            reason = "error details omitted"
        self.code = code
        self.field_path = field_path
        self.reason = reason
        super().__init__(f"{code} at {field_path}: {reason}")


def _field_path(path: str, key: object) -> str:
    if isinstance(key, str) and _SAFE_PATH_KEY_RE.fullmatch(key) is not None:
        candidate = f"{path}.{key}"
    else:
        candidate = f"{path}.<field>"
    return candidate if len(candidate) <= _MAX_ERROR_COMPONENT else "$.<path-omitted>"


def _forbidden_field_path(path: str, original_key: str) -> str:
    if original_key.isidentifier():
        candidate = f"{path}.{original_key}"
    else:
        candidate = f"{path}[{json.dumps(original_key, ensure_ascii=False)}]"
    return candidate if len(candidate) <= _MAX_ERROR_COMPONENT else "$.<path-omitted>"


def _index_path(path: str, index: int) -> str:
    candidate = f"{path}[{index}]"
    return candidate if len(candidate) <= _MAX_ERROR_COMPONENT else "$.<path-omitted>"


class _FrozenObject(tuple):
    """Tagged tuple used to distinguish frozen objects from arrays."""


class _FrozenArray(tuple):
    """Tagged tuple used to distinguish frozen arrays from objects."""


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return _FrozenObject((key, _freeze(item)) for key, item in sorted(value.items()))
    if isinstance(value, list):
        return _FrozenArray(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, _FrozenObject):
        return {key: _thaw(item) for key, item in value}
    if isinstance(value, _FrozenArray):
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True, slots=True, init=False)
class StructuredAction:
    action_id: str
    action_type: str
    parameters: _FrozenObject
    budget_impact: _FrozenObject
    expected_result_type: str

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("StructuredAction instances must be created by parse_action")

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "parameters": _thaw(self.parameters),
            "budget_impact": _thaw(self.budget_impact),
            "expected_result_type": self.expected_result_type,
        }


@dataclass(frozen=True, slots=True, init=False)
class ControlAction(StructuredAction):
    """A validated action handled by the agent control plane."""


@dataclass(frozen=True, slots=True, init=False)
class ToolAction(StructuredAction):
    """A validated declaration of a bounded tool operation."""


class _ObjectPairs(list[tuple[str, object]]):
    pass


_MISSING_ITEM = object()


def _mapping_items(value: Mapping[object, object], path: str):
    failed = False
    try:
        iterator = iter(value.items())
    except Exception:
        failed = True
        iterator = iter(())
    if failed:
        raise ActionParseError("INVALID_JSON", path, "mapping could not be read") from None

    while True:
        failed = False
        try:
            pair = next(iterator)
        except StopIteration:
            pair = _MISSING_ITEM
        except Exception:
            failed = True
            pair = _MISSING_ITEM
        if failed:
            raise ActionParseError("INVALID_JSON", path, "mapping could not be read") from None
        if pair is _MISSING_ITEM:
            return

        failed = False
        try:
            key, item = pair
        except Exception:
            failed = True
            key = item = None
        if failed:
            raise ActionParseError("INVALID_JSON", path, "mapping contains an invalid item") from None
        yield key, item


def _invalid_json_constant(_: str) -> None:
    raise ValueError("non-finite number")


class _NormalizationBudget:
    def __init__(self) -> None:
        self.bytes_used = 0

    def add(self, size: int, path: str) -> None:
        self.bytes_used += size
        if self.bytes_used > _MAX_INPUT_BYTES:
            raise ActionParseError(
                "INPUT_TOO_LARGE", path, "normalized input exceeds the byte limit"
            )


def _json_string_size(value: str, path: str) -> int:
    size = 2
    for character in value:
        if character == "\0":
            raise ActionParseError("INVALID_VALUE", path, "string must not contain NUL")
        try:
            encoded_size = len(character.encode("utf-8"))
        except UnicodeEncodeError:
            encoded_size = None
        if encoded_size is None:
            raise ActionParseError("INVALID_VALUE", path, "string is not valid UTF-8 text") from None
        if character in {'"', "\\", "\b", "\f", "\n", "\r", "\t"}:
            size += 2
        elif ord(character) < 0x20:
            size += 6
        else:
            size += encoded_size
    return size


def _copy_json_value(
    value: object,
    path: str,
    budget: _NormalizationBudget,
    container_depth: int,
) -> object:
    if value is None:
        budget.add(4, path)
        return value
    if type(value) is str:
        budget.add(_json_string_size(value, path), path)
        return value
    if type(value) is bool:
        budget.add(4 if value else 5, path)
        return value
    if type(value) is int:
        try:
            size = len(str(value))
        except ValueError:
            size = None
        if size is None:
            raise ActionParseError("INVALID_VALUE", path, "integer representation is too large") from None
        budget.add(size, path)
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ActionParseError("INVALID_VALUE", path, "number must be finite")
        budget.add(len(json.dumps(value)), path)
        return value
    if isinstance(value, (_ObjectPairs, Mapping)):
        if container_depth > _MAX_NORMALIZED_DEPTH:
            raise ActionParseError("INVALID_VALUE", path, "container nesting exceeds the limit")
        budget.add(2, path)
        copied: dict[str, object] = {}
        items = value if isinstance(value, _ObjectPairs) else _mapping_items(value, path)
        for index, (key, item) in enumerate(items):
            if index >= _MAX_CONTAINER_KEYS:
                raise ActionParseError("INPUT_TOO_LARGE", path, "object has too many keys")
            if type(key) is not str:
                raise ActionParseError("INVALID_JSON", path, "object keys must be strings")
            child_path = _field_path(path, key)
            key_size = _json_string_size(key, child_path)
            if key in copied:
                raise ActionParseError("INVALID_JSON", path, "object contains a duplicate key")
            budget.add((1 if index else 0) + key_size + 1, child_path)
            copied[key] = _copy_json_value(item, child_path, budget, container_depth + 1)
        return copied
    if type(value) is list:
        if container_depth > _MAX_NORMALIZED_DEPTH:
            raise ActionParseError("INVALID_VALUE", path, "container nesting exceeds the limit")
        budget.add(2, path)
        copied_items: list[object] = []
        for index, item in enumerate(value):
            if index >= _MAX_ARRAY_ITEMS:
                raise ActionParseError("INPUT_TOO_LARGE", path, "array has too many items")
            if index:
                budget.add(1, path)
            child_path = _index_path(path, index)
            copied_items.append(
                _copy_json_value(item, child_path, budget, container_depth + 1)
            )
        return copied_items
    raise ActionParseError("INVALID_JSON", path, "unsupported JSON value type")


def _normalize(raw: str | Mapping[str, object]) -> dict[str, object]:
    if type(raw) is str:
        try:
            encoded_size = len(raw.encode("utf-8"))
        except UnicodeEncodeError:
            encoded_size = None
        if encoded_size is None:
            raise ActionParseError("INVALID_JSON", "$", "input is not valid UTF-8 text") from None
        if encoded_size > _MAX_INPUT_BYTES:
            raise ActionParseError(
                "INPUT_TOO_LARGE", "$", f"JSON input length is {encoded_size} bytes"
            )
        parse_failure: str | None = None
        try:
            decoded = json.loads(
                raw,
                object_pairs_hook=_ObjectPairs,
                parse_constant=_invalid_json_constant,
            )
        except json.JSONDecodeError as exc:
            parse_failure = f"invalid JSON at line {exc.lineno}, column {exc.colno}"
            decoded = None
        except ValueError:
            parse_failure = "invalid JSON number"
            decoded = None
        except RecursionError:
            parse_failure = "JSON input nesting is too deep"
            decoded = None
        if parse_failure is not None:
            raise ActionParseError("INVALID_JSON", "$", parse_failure) from None
        normalized = _copy_json_value(decoded, "$", _NormalizationBudget(), 1)
    elif isinstance(raw, Mapping):
        normalized = _copy_json_value(raw, "$", _NormalizationBudget(), 1)
    else:
        raise ActionParseError("INVALID_JSON", "$", "input must be a JSON string or mapping")
    if not isinstance(normalized, dict):
        raise ActionParseError("INVALID_ACTION", "$", "top-level value must be an object")
    return normalized


def _exact_fields(value: dict[str, object], expected: set[str] | frozenset[str], path: str) -> None:
    actual = set(value)
    extra = sorted(actual - expected)
    if extra:
        raise ActionParseError("INVALID_FIELD", _field_path(path, extra[0]), "field is not allowed")
    missing = sorted(expected - actual)
    if missing:
        raise ActionParseError(
            "INVALID_FIELD", _field_path(path, missing[0]), "required field is missing"
        )


def _object(value: object, path: str) -> dict[str, object]:
    if type(value) is not dict:
        raise ActionParseError("INVALID_VALUE", path, "value must be an object")
    return value


def _string(
    value: object,
    path: str,
    *,
    minimum: int = 1,
    maximum: int = 4_096,
) -> str:
    if type(value) is not str:
        raise ActionParseError("INVALID_VALUE", path, "value must be a string")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        size = None
    if size is None:
        raise ActionParseError("INVALID_VALUE", path, "string is not valid UTF-8 text") from None
    if "\0" in value:
        raise ActionParseError("INVALID_VALUE", path, "string must not contain NUL")
    if not minimum <= size <= maximum:
        raise ActionParseError(
            "INPUT_TOO_LARGE" if size > maximum else "INVALID_VALUE",
            path,
            f"string length is {size} bytes; expected {minimum}..{maximum}",
        )
    return value


def _integer(value: object, path: str, *, minimum: int = 0, maximum: int = _MAX_INTEGER) -> int:
    if type(value) is not int:
        raise ActionParseError("INVALID_VALUE", path, "value must be an integer")
    if not minimum <= value <= maximum:
        raise ActionParseError("INVALID_VALUE", path, "integer is outside the allowed range")
    return value


def _enum_string(value: object, path: str, allowed: frozenset[str]) -> str:
    normalized = _string(value, path)
    if normalized not in allowed:
        raise ActionParseError("INVALID_VALUE", path, "value is outside the closed protocol set")
    return normalized


def _nonempty_bounded_object(value: object, path: str) -> dict[str, object]:
    normalized = _object(value, path)
    if not normalized:
        raise ActionParseError("INVALID_VALUE", path, "object must not be empty")
    _bounded_container(normalized, path)
    return normalized


def _paths(value: object, path: str, *, required: bool) -> None:
    if type(value) is not list:
        raise ActionParseError("INVALID_VALUE", path, "value must be an array")
    if required and not value:
        raise ActionParseError("INVALID_VALUE", path, "array must not be empty")
    if len(value) > _MAX_ARRAY_ITEMS:
        raise ActionParseError("INPUT_TOO_LARGE", path, "array has too many items")
    for index, item in enumerate(value):
        _string(item, _index_path(path, index))


def _is_forbidden_command_field(key: str) -> bool:
    return unicodedata.normalize("NFKC", key).casefold() in _NORMALIZED_FORBIDDEN_COMMAND_FIELDS


def _reject_command_fields(value: object, path: str) -> None:
    if type(value) is dict:
        for key, item in value.items():
            if _is_forbidden_command_field(key):
                raise ActionParseError(
                    "INVALID_FIELD",
                    _forbidden_field_path(path, key),
                    "command field is not allowed",
                )
            _reject_command_fields(item, _field_path(path, key))
    elif type(value) is list:
        for index, item in enumerate(value):
            _reject_command_fields(item, _index_path(path, index))


def _bounded_container(value: object, path: str, depth: int = 1) -> None:
    if type(value) is dict:
        if depth > _MAX_CONTAINER_DEPTH:
            raise ActionParseError("INVALID_VALUE", path, "container nesting exceeds 16 levels")
        if len(value) > _MAX_CONTAINER_KEYS:
            raise ActionParseError("INPUT_TOO_LARGE", path, "object has too many keys")
        for key, item in value.items():
            if _is_forbidden_command_field(key):
                raise ActionParseError(
                    "INVALID_FIELD",
                    _forbidden_field_path(path, key),
                    "command field is not allowed",
                )
            _bounded_container(item, _field_path(path, key), depth + 1)
    elif type(value) is list:
        if depth > _MAX_CONTAINER_DEPTH:
            raise ActionParseError("INVALID_VALUE", path, "container nesting exceeds 16 levels")
        if len(value) > _MAX_ARRAY_ITEMS:
            raise ActionParseError("INPUT_TOO_LARGE", path, "array has too many items")
        for index, item in enumerate(value):
            _bounded_container(item, _index_path(path, index), depth + 1)


def _validate_budget(value: object) -> dict[str, object]:
    budget = _object(value, "$.budget_impact")
    if not 1 <= len(budget) <= 16:
        raise ActionParseError("INVALID_VALUE", "$.budget_impact", "budget must contain 1..16 items")
    any_positive = False
    for key, item in budget.items():
        if _BUDGET_KEY_RE.fullmatch(key) is None:
            raise ActionParseError(
                "INVALID_FIELD", _field_path("$.budget_impact", key), "invalid budget key"
            )
        amount = _integer(item, _field_path("$.budget_impact", key))
        any_positive = any_positive or amount > 0
    if not any_positive:
        raise ActionParseError("INVALID_VALUE", "$.budget_impact", "at least one budget value must be positive")
    return dict(sorted(budget.items()))


def _validate_control(action_type: str, value: object) -> dict[str, object]:
    parameters = _object(value, "$.parameters")
    field = _CONTROL_FIELDS[action_type]
    _exact_fields(parameters, {field}, "$.parameters")
    path = f"$.parameters.{field}"
    if action_type == "request_clarification":
        _string(parameters[field], path)
    else:
        _nonempty_bounded_object(parameters[field], path)
    return parameters


def _validate_tool(action_type: str, value: object) -> dict[str, object]:
    parameters = _object(value, "$.parameters")
    schemas: dict[str, tuple[set[str], set[str]]] = {
        "inspect_repository": (set(), set()),
        "list_files": ({"path", "limit"}, set()),
        "read_file": ({"path", "start_byte", "max_bytes"}, set()),
        "search_text": ({"text", "paths", "limit"}, set()),
        "create_file": ({"path", "content"}, set()),
        "replace_file": ({"path", "expected_digest", "content"}, set()),
        "apply_patch": ({"path", "patch", "expected_digest"}, set()),
        "delete_file": ({"path", "expected_digest", "reason"}, set()),
        "request_ignored_input": ({"paths", "mode", "phase", "manifest_version"}, set()),
        "run_validation": ({"profile", "operation"}, set()),
        "git_repo_probe": (set(), set()),
        "git_repo_root": (set(), set()),
        "git_status": (set(), set()),
        "git_diff_worktree": (set(), {"paths"}),
        "git_diff_index": (set(), {"paths"}),
        "git_list_tracked": (set(), {"paths"}),
        "git_list_untracked": (set(), {"paths"}),
        "git_stage_paths": ({"paths"}, set()),
        "git_unstage_paths": ({"paths"}, set()),
    }
    required, optional = schemas[action_type]
    extra = sorted(set(parameters) - required - optional)
    if extra:
        raise ActionParseError(
            "INVALID_FIELD", _field_path("$.parameters", extra[0]), "field is not allowed"
        )
    missing = sorted(required - set(parameters))
    if missing:
        raise ActionParseError(
            "INVALID_FIELD", _field_path("$.parameters", missing[0]), "required field is missing"
        )
    _reject_command_fields(parameters, "$.parameters")

    for field in ("path", "text", "expected_digest", "reason", "mode", "phase", "manifest_version", "profile", "operation"):
        if field in parameters:
            _string(parameters[field], f"$.parameters.{field}")
    if "content" in parameters:
        _string(parameters["content"], "$.parameters.content", minimum=0, maximum=_MAX_INPUT_BYTES)
    if "limit" in parameters:
        _integer(parameters["limit"], "$.parameters.limit", minimum=1)
    if "start_byte" in parameters:
        _integer(parameters["start_byte"], "$.parameters.start_byte")
    if "max_bytes" in parameters:
        _integer(parameters["max_bytes"], "$.parameters.max_bytes", minimum=1)
    if "paths" in parameters:
        _paths(
            parameters["paths"],
            "$.parameters.paths",
            required=action_type in {"search_text", "request_ignored_input", "git_stage_paths", "git_unstage_paths"},
        )
    if "patch" in parameters:
        patch = _object(parameters["patch"], "$.parameters.patch")
        if not patch:
            raise ActionParseError("INVALID_VALUE", "$.parameters.patch", "patch must not be empty")
        _bounded_container(patch, "$.parameters.patch")
    if action_type == "request_ignored_input":
        _enum_string(parameters["mode"], "$.parameters.mode", _IGNORED_INPUT_MODES)
        _enum_string(parameters["phase"], "$.parameters.phase", _IGNORED_INPUT_PHASES)
    elif action_type == "run_validation":
        profile = _enum_string(
            parameters["profile"],
            "$.parameters.profile",
            frozenset(_VALIDATION_OPERATIONS),
        )
        _enum_string(
            parameters["operation"],
            "$.parameters.operation",
            _VALIDATION_OPERATIONS[profile],
        )
    return parameters


def _build_action(
    action_class: type[StructuredAction],
    *,
    action_id: str,
    action_type: str,
    parameters: dict[str, object],
    budget_impact: dict[str, object],
    expected_result_type: str,
) -> StructuredAction:
    action = object.__new__(action_class)
    object.__setattr__(action, "action_id", action_id)
    object.__setattr__(action, "action_type", action_type)
    object.__setattr__(action, "parameters", _freeze(parameters))
    object.__setattr__(action, "budget_impact", _freeze(budget_impact))
    object.__setattr__(action, "expected_result_type", expected_result_type)
    return action


def parse_action(raw: str | Mapping[str, object]) -> StructuredAction:
    """Normalize and validate one structured action without executing it."""

    action = _normalize(raw)
    _exact_fields(action, _TOP_LEVEL_FIELDS, "$")

    action_id = action["action_id"]
    if type(action_id) is not str or _ACTION_ID_RE.fullmatch(action_id) is None:
        raise ActionParseError("INVALID_VALUE", "$.action_id", "action_id has invalid format")

    action_type = action["action_type"]
    if type(action_type) is not str:
        raise ActionParseError("INVALID_VALUE", "$.action_type", "action_type must be a string")
    if action_type in _GOVERNANCE_TYPES or action_type in _INTERNAL_TYPES:
        raise ActionParseError("INVALID_ACTION", "$.action_type", "action type is not an agent action")
    if action_type in _CONTROL_FIELDS:
        action_class = ControlAction
        expected = "control_result"
        parameters = _validate_control(action_type, action["parameters"])
    elif action_type in _TOOL_TYPES:
        action_class = ToolAction
        expected = "tool_result"
        parameters = _validate_tool(action_type, action["parameters"])
    else:
        raise ActionParseError("INVALID_ACTION", "$.action_type", "unknown action type")

    expected_result_type = action["expected_result_type"]
    if type(expected_result_type) is not str:
        raise ActionParseError(
            "INVALID_VALUE", "$.expected_result_type", "expected result type must be a string"
        )
    if expected_result_type not in {"control_result", "tool_result"}:
        raise ActionParseError(
            "INVALID_VALUE", "$.expected_result_type", "unknown expected result type"
        )
    if expected_result_type != expected:
        raise ActionParseError(
            "INVALID_VALUE", "$.expected_result_type", "result type does not match action category"
        )

    budget = _validate_budget(action["budget_impact"])
    return _build_action(
        action_class,
        action_id=action_id,
        action_type=action_type,
        parameters=parameters,
        budget_impact=budget,
        expected_result_type=expected_result_type,
    )


__all__ = [
    "ActionParseError",
    "StructuredAction",
    "ControlAction",
    "ToolAction",
    "parse_action",
]
