from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
import hashlib
import importlib
import json
from pathlib import Path
import re
import subprocess

import pytest


WP02_APPROVED_COMMIT = "d3169f6e8ed0ff32afccfdde9504c8f42e710a97"
SPEC_DIGEST = "01a30b5fcfd728bb8c334fdb76173e4d83e2667fc9b97a05672ce773f80e238e"
PLAN_DIGEST = "571c5b4cbbede66039cb6531b5512ea41a8c187d4a86225331e8d66b2ad6d37f"
WP02_REQUIREMENTS = (
    "GEN-001", "GEN-002", "GEN-003",
    "PRC-001", "PRC-002", "PRC-003", "PRC-004", "PRC-005",
    "PRC-006", "PRC-007", "PRC-008", "PRC-009", "PRC-010",
    "TST-008", "ACT-001", "ACT-002", "ACT-003", "ACT-008", "ACT-009", "ACT-010", "ACT-011",
)
CONTROL_TYPES = ("request_clarification", "propose_plan", "request_budget_extension", "request_user_confirmation", "report_blocked", "stop_with_failure", "stop_without_safe_action")
_CONTROL_FIELDS = {
    "request_clarification": "question",
    "propose_plan": "proposal",
    "request_budget_extension": "request",
    "request_user_confirmation": "condition",
    "report_blocked": "report",
    "stop_with_failure": "report",
    "stop_without_safe_action": "report",
}
TOOL_TYPES = ("inspect_repository", "list_files", "read_file", "search_text", "create_file", "replace_file", "apply_patch", "delete_file", "request_ignored_input", "run_validation", "git_repo_probe", "git_repo_root", "git_status", "git_diff_worktree", "git_diff_index", "git_list_tracked", "git_list_untracked", "git_stage_paths", "git_unstage_paths")
GOVERNANCE_TYPES = ("submit_clarification", "approve_plan", "reject_plan", "approve_action", "reject_action", "approve_budget_extension", "reject_budget_extension", "confirm_user_acceptance", "reject_user_acceptance", "continue_task", "cancel_task", "confirm_apply", "reject_apply", "request_recovery")
INTERNAL_TYPES = ("build_baseline", "materialize_workspace", "materialize_ignored_input", "create_action_approval_request", "compute_changeset", "evaluate_acceptance", "acquire_execution_lease", "release_execution_lease", "begin_apply_transaction", "advance_apply_phase", "recover_apply_transaction", "publish_domain_event")


@dataclass(frozen=True)
class PVRecord:
    requirement_id: str
    pv_id: str
    phase: int
    package: str
    day: int
    supporting_packages: tuple[str, ...]
    planned_categories_raw: str
    planned_categories: tuple[str, ...]
    planned_node: str
    status: str


@dataclass(frozen=True)
class EvidenceRange:
    requirement_prefix: str
    first_id: int
    last_id: int
    final_categories_raw: str
    final_categories: tuple[str, ...]
    is_mvp: bool


ROOT = Path(__file__).resolve().parents[3]
SPEC = ROOT / "SPEC.md"
PLAN = ROOT / "PLAN.md"
REQ_RE = re.compile(r"^\- \*\*([A-Z]{2,3}-\d{3})\*\*", re.MULTILINE)
REQUIREMENT_RE = re.compile(r"[A-Z]{2,3}-\d{3}")
PV_RE = re.compile(r"PV-[A-Z]{2,3}-\d{3}")
PV_TABLE_HEADING = "# Requirement 与 Planned Verification 追踪表（207 行）"
PV_HEADERS = (
    "Requirement", "PV", "Phase", "Package", "Day", "Supporting",
    "Category", "精确计划 node/case", "Status",
)
EVIDENCE_HEADING = "## H.3 Planned Evidence Category Matrix"
EVIDENCE_HEADERS = (
    "需求范围", "数量", "主要章节", "责任组件/关注面", "验收证据", "MVP",
    "课程要求映射", "Implementation Status",
)
ALLOWED_STATUSES = {"PLANNED", "IN_PROGRESS", "IMPLEMENTED", "VERIFIED", "BLOCKED"}


def _categories(raw: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in re.split(r"[,/]", raw) if part.strip())


def _markdown_cells(raw: str) -> list[str]:
    return [cell.strip() for cell in raw.strip().strip("|").split("|")]


def _authority_table_text(
    text: str, source: str, heading: str, headers: tuple[str, ...]
) -> list[tuple[int, str, list[str]]]:
    lines = text.splitlines()
    table_name = "PLAN PV authority table" if heading == PV_TABLE_HEADING else "SPEC Appendix H authority table"
    heading_indexes = [index for index, line in enumerate(lines) if line == heading]
    assert len(heading_indexes) == 1, (
        f"{source}: expected one authoritative table heading {heading!r}, "
        f"found {len(heading_indexes)}"
    )
    start = heading_indexes[0] + 1
    while start < len(lines) and not lines[start].startswith("|"):
        start += 1
    assert start < len(lines), f"{source}: {heading}: missing table header"
    actual_headers = tuple(_markdown_cells(lines[start]))
    assert actual_headers == headers, (
        f"{source}:{start + 1}: {heading}: header mismatch; "
        f"expected={headers}, actual={actual_headers}, raw={lines[start]!r}"
    )
    separator = start + 1
    assert separator < len(lines) and re.fullmatch(r"\|(?:\s*:?-+:?\s*\|){%d}" % len(headers), lines[separator]), (
        f"{source}:{separator + 1}: {heading}: malformed table separator: {lines[separator]!r}"
    )
    rows: list[tuple[int, str, list[str]]] = []
    for index in range(separator + 1, len(lines)):
        raw = lines[index]
        if not raw:
            next_nonempty = next((line for line in lines[index + 1:] if line), None)
            assert next_nonempty is None or not next_nonempty.startswith("|"), (
                f"{source}: line {index + 1}: Malformed row in {table_name}; raw={raw!r}; "
                f"expected a pipe-delimited row beginning with '|'; expected columns={len(headers)}"
            )
            break
        if raw.startswith("#"):
            break
        assert raw.startswith("|"), (
            f"{source}: line {index + 1}: Malformed row in {table_name}; raw={raw!r}; "
            f"expected a pipe-delimited row beginning with '|'; expected columns={len(headers)}"
        )
        cells = _markdown_cells(raw)
        assert len(cells) == len(headers), (
            f"{source}: line {index + 1}: {table_name}: malformed row; raw={raw!r}; "
            f"expected columns={len(headers)}, actual columns={len(cells)}"
        )
        rows.append((index + 1, raw, cells))
    assert rows, f"{source}: {heading}: table has no data rows"
    return rows


def _authority_table(path: Path, heading: str, headers: tuple[str, ...]) -> list[tuple[int, str, list[str]]]:
    return _authority_table_text(path.read_text(), path.name, heading, headers)


def _pv_records() -> list[PVRecord]:
    records: list[PVRecord] = []
    seen_requirements: dict[str, int] = {}
    seen_pvs: dict[str, int] = {}
    for line_number, raw, cells in _authority_table(PLAN, PV_TABLE_HEADING, PV_HEADERS):
        req, pv, phase_raw, package, day_raw, supporting_raw, category, node_raw, status = cells
        assert re.fullmatch(r"[A-Z]{2,3}-\d{3}", req), (
            f"PLAN.md:{line_number}: {PV_TABLE_HEADING}: invalid Requirement={req!r}; raw={raw!r}"
        )
        assert pv == f"PV-{req}", (
            f"PLAN.md:{line_number}: {PV_TABLE_HEADING}: invalid PV={pv!r}; "
            f"expected PV-{req}; raw={raw!r}"
        )
        assert phase_raw.isdigit() and day_raw.isdigit(), (
            f"PLAN.md:{line_number}: {PV_TABLE_HEADING}: Phase and Day must be integers; "
            f"Phase={phase_raw!r}, Day={day_raw!r}; raw={raw!r}"
        )
        assert re.fullmatch(r"WP-\d{2}", package), (
            f"PLAN.md:{line_number}: {PV_TABLE_HEADING}: invalid Package={package!r}; raw={raw!r}"
        )
        supporting = tuple(item.strip() for item in supporting_raw.split(",") if item.strip())
        assert all(re.fullmatch(r"WP-\d{2}", item) for item in supporting), (
            f"PLAN.md:{line_number}: {PV_TABLE_HEADING}: invalid Supporting={supporting_raw!r}; raw={raw!r}"
        )
        assert category and node_raw and status, (
            f"PLAN.md:{line_number}: {PV_TABLE_HEADING}: Category, node, and Status must be non-empty; raw={raw!r}"
        )
        assert status in ALLOWED_STATUSES, (
            f"PLAN.md:{line_number}: {PV_TABLE_HEADING}: invalid Status={status!r}; "
            f"allowed={sorted(ALLOWED_STATUSES)}; raw={raw!r}"
        )
        node_match = re.fullmatch(r"`([^`]+)`", node_raw)
        assert node_match, f"PLAN.md:{line_number}: {PV_TABLE_HEADING}: invalid planned node={node_raw!r}; raw={raw!r}"
        assert req not in seen_requirements, (
            f"PLAN.md:{line_number}: duplicate Requirement {req}; first at line {seen_requirements.get(req)}; raw={raw!r}"
        )
        assert pv not in seen_pvs, (
            f"PLAN.md:{line_number}: duplicate PV {pv}; first at line {seen_pvs.get(pv)}; raw={raw!r}"
        )
        seen_requirements[req] = line_number
        seen_pvs[pv] = line_number
        records.append(PVRecord(req, pv, int(phase_raw), package, int(day_raw), supporting,
                                category, _categories(category), node_match.group(1), status))
    return records


def _evidence_ranges() -> list[EvidenceRange]:
    ranges: list[EvidenceRange] = []
    covered: dict[str, int] = {}
    for line_number, raw_row, cells in _authority_table(SPEC, EVIDENCE_HEADING, EVIDENCE_HEADERS):
        range_raw, count_raw, _, _, category, mvp_raw, _, status = cells
        match = re.fullmatch(r"`([A-Z]{2,3})-(\d{3})\.\.([A-Z]{2,3}-)?(\d{3})`", range_raw)
        assert match, (
            f"SPEC.md:{line_number}: {EVIDENCE_HEADING}: invalid range={range_raw!r}; raw={raw_row!r}"
        )
        prefix, first_raw, end_prefix_raw, last_raw = match.groups()
        end_prefix = end_prefix_raw[:-1] if end_prefix_raw else prefix
        first, last = int(first_raw), int(last_raw)
        assert prefix == end_prefix and first <= last, (
            f"SPEC.md:{line_number}: {EVIDENCE_HEADING}: invalid range {range_raw}; "
            f"parsed prefix/start/end={prefix}/{first}/{end_prefix}-{last}; raw={raw_row!r}"
        )
        assert count_raw.isdigit() and int(count_raw) == last - first + 1, (
            f"SPEC.md:{line_number}: {EVIDENCE_HEADING}: count mismatch for {range_raw}; "
            f"expected={last - first + 1}, actual={count_raw!r}; raw={raw_row!r}"
        )
        assert category, f"SPEC.md:{line_number}: {EVIDENCE_HEADING}: empty category for {range_raw}; raw={raw_row!r}"
        assert mvp_raw in {"是", "否"}, (
            f"SPEC.md:{line_number}: {EVIDENCE_HEADING}: invalid MVP={mvp_raw!r} for {range_raw}; raw={raw_row!r}"
        )
        assert status in ALLOWED_STATUSES, (
            f"SPEC.md:{line_number}: {EVIDENCE_HEADING}: invalid status={status!r} for {range_raw}; raw={raw_row!r}"
        )
        for number in range(first, last + 1):
            requirement_id = f"{prefix}-{number:03d}"
            assert requirement_id not in covered, (
                f"SPEC.md:{line_number}: {EVIDENCE_HEADING}: overlapping range {range_raw}; "
                f"overlap target={requirement_id}, first declared line={covered.get(requirement_id)}"
            )
            covered[requirement_id] = line_number
        ranges.append(EvidenceRange(prefix, first, last, category, _categories(category), mvp_raw == "是"))
    return ranges


def _range_for(requirement_id: str) -> EvidenceRange:
    prefix, number = requirement_id.split("-")
    matches = [r for r in _evidence_ranges() if r.requirement_prefix == prefix and r.first_id <= int(number) <= r.last_id]
    assert len(matches) == 1, f"{requirement_id}: expected exactly one Appendix H range, got {matches}"
    return matches[0]


def _expand_requirement_expression(raw: str, *, source: str) -> set[str]:
    expanded: set[str] = set()
    token_re = re.compile(r"(?<!PV-)([A-Z]{2,3})-(\d{3})(?:\.\.(?:([A-Z]{2,3})-)?(\d{3}))?")
    for match in token_re.finditer(raw):
        prefix, first_raw, last_prefix, last_raw = match.groups()
        last_prefix = last_prefix or prefix
        assert last_prefix == prefix, f"{source}: mixed-prefix Requirement range {match.group()!r}"
        first = int(first_raw)
        last = int(last_raw or first_raw)
        assert first <= last, f"{source}: descending Requirement range {match.group()!r}"
        expanded.update(f"{prefix}-{number:03d}" for number in range(first, last + 1))
    return expanded


def _expand_pv_expression(raw: str, *, source: str) -> set[str]:
    expanded: set[str] = set()
    token_re = re.compile(r"PV-([A-Z]{2,3})-(\d{3})(?:\.\.(?:PV-)?(?:([A-Z]{2,3})-)?(\d{3}))?")
    for match in token_re.finditer(raw):
        prefix, first_raw, last_prefix, last_raw = match.groups()
        last_prefix = last_prefix or prefix
        assert last_prefix == prefix, f"{source}: mixed-prefix PV range {match.group()!r}"
        first = int(first_raw)
        last = int(last_raw or first_raw)
        assert first <= last, f"{source}: descending PV range {match.group()!r}"
        expanded.update(f"PV-{prefix}-{number:03d}" for number in range(first, last + 1))
    return expanded


def _wp_declarations(plan_path: Path = PLAN) -> tuple[dict[str, set[str]], dict[str, list[tuple[str, int]]]]:
    lines = plan_path.read_text().splitlines()
    headings = [
        (index, match.group(1))
        for index, line in enumerate(lines)
        if (match := re.fullmatch(r"## (WP-\d{2}):.*", line))
    ]
    assert len(headings) == 29, f"PLAN.md: expected 29 WP headings, found {len(headings)}"
    involved_by_wp: dict[str, set[str]] = {}
    declaring_wps: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for position, (start, package) in enumerate(headings):
        end = headings[position + 1][0] if position + 1 < len(headings) else next(
            (index for index in range(start + 1, len(lines)) if lines[index] == PV_TABLE_HEADING),
            len(lines),
        )
        section = lines[start:end]
        involved_lines = [
            (start + offset + 1, line)
            for offset, line in enumerate(section)
            if line.startswith("**Requirement/PV：** ")
        ]
        assert len(involved_lines) == 1, (
            f"PLAN.md:{start + 1}: {package}: expected one Requirement/PV declaration, "
            f"found {len(involved_lines)}"
        )
        involved_line, involved_raw = involved_lines[0]
        involved_by_wp[package] = _expand_requirement_expression(
            involved_raw.removeprefix("**Requirement/PV：** "),
            source=f"PLAN.md:{involved_line} {package} Requirement/PV",
        )
        owned_lines = [
            (start + offset + 1, line)
            for offset, line in enumerate(section)
            if line.startswith("**归属 PV：** ")
        ]
        assert len(owned_lines) <= 1, (
            f"PLAN.md:{start + 1}: {package}: multiple 归属 PV declarations at "
            f"{[line for line, _ in owned_lines]}"
        )
        if not owned_lines:
            continue
        owned_line, owned_raw = owned_lines[0]
        owned = _expand_pv_expression(
            owned_raw.removeprefix("**归属 PV：** "),
            source=f"PLAN.md:{owned_line} {package} 归属 PV",
        )
        assert owned, f"PLAN.md:{owned_line}: {package}: empty 归属 PV declaration"
        for pv_id in owned:
            declaring_wps[pv_id].append((package, owned_line))
    return involved_by_wp, declaring_wps


def _validate_ownership(rows: list[PVRecord], plan_path: Path = PLAN) -> None:
    involved_by_wp, declaring_wps = _wp_declarations(plan_path)
    table_pvs = {row.pv_id for row in rows}
    extra_declarations = sorted(set(declaring_wps) - table_pvs)
    assert not extra_declarations, f"归属 PV declarations absent from PV table: {extra_declarations}"
    for row in rows:
        declarations = declaring_wps.get(row.pv_id, [])
        declared_packages = [package for package, _ in declarations]
        assert len(declarations) == 1 and declared_packages == [row.package], (
            f"{row.pv_id}: duplicate owner declaration or owner mismatch; "
            f"expected owner from PV table={row.package}; all declaring WPs/lines={declarations}; "
            "expected exactly one matching 归属 PV declaration"
        )
        assert row.requirement_id in involved_by_wp[row.package], (
            f"{row.pv_id}: owner {row.package} does not include {row.requirement_id} in its "
            f"Requirement/PV involved set; declarations={declarations}"
        )


def _git(*args: str, cwd: Path = ROOT) -> str:
    command = ["git", *args]
    completed = subprocess.run(command, cwd=cwd, check=False, text=True, capture_output=True)
    assert completed.returncode == 0, (
        f"git command failed: command={command!r}, cwd={str(cwd)!r}, "
        f"exit={completed.returncode}, stdout={completed.stdout!r}, stderr={completed.stderr!r}"
    )
    return completed.stdout.rstrip("\n")


def _porcelain_paths(output: str) -> set[str]:
    paths: set[str] = set()
    for raw in output.splitlines():
        assert len(raw) >= 4 and raw[2] == " ", f"unsupported git status porcelain line: {raw!r}"
        status = raw[:2]
        assert "R" not in status and "C" not in status and " -> " not in raw[3:], (
            f"rename/copy requires explicit porcelain parsing: {raw!r}"
        )
        path = raw[3:]
        assert path and not path.startswith('"'), f"unsupported quoted/empty git status path: {raw!r}"
        paths.add(path)
    return paths


def _validate_process_evidence_text(text: str, *, source: str) -> None:
    section_match = re.search(r"^## 证据台账\n(?P<body>.*?)(?=^## )", text, re.MULTILINE | re.DOTALL)
    assert section_match, f"{source}: 缺少证据台账章节，无法验证过程语义"
    body = section_match.group("body")
    paragraph = next((item.strip() for item in body.split("\n\n") if "未来支持证据" in item), "")
    expected = ("未来支持证据", "PENDING", "计划测试", "Requirement", "PLANNED", "不会", "改变")
    missing = [item for item in expected if item not in paragraph]
    assert not missing, (
        f"{source}: 缺失过程语义元素 {missing}；期望中文含义为未来支持证据仍为 PENDING，"
        f"且计划测试不会改变 Requirement 的 PLANNED 状态；实际相关文本={paragraph!r}"
    )


def _validate_wp02_context(
    *, head: str, staged_paths: set[str], dirty_paths: set[str],
) -> None:
    assert head, "当前工作树 HEAD 为空"
    _git("merge-base", "--is-ancestor", WP02_APPROVED_COMMIT, "HEAD")
    assert not staged_paths, (
        f"当前工作树存在 staged 路径：{sorted(staged_paths)}；HEAD={head}"
    )
    assert not dirty_paths, (
        f"当前工作树存在 dirty 路径：{sorted(dirty_paths)}；HEAD={head}"
    )


def test_traceability_has_207_unique_rows():
    plan_text = PLAN.read_text()
    valid_row = next(line for line in plan_text.splitlines() if line.startswith("| GEN-001 |"))
    missing_pipe = plan_text.replace(valid_row, valid_row.removeprefix("| "), 1)
    with pytest.raises(AssertionError) as missing_pipe_error:
        _authority_table_text(missing_pipe, "isolated PLAN.md", PV_TABLE_HEADING, PV_HEADERS)
    missing_pipe_message = str(missing_pipe_error.value)
    assert all(fragment in missing_pipe_message for fragment in (
        "Malformed row", "PLAN PV authority table", "line ", valid_row.removeprefix("| "),
        "expected a pipe-delimited row beginning with '|'", f"expected columns={len(PV_HEADERS)}",
    )), missing_pipe_message

    cells = _markdown_cells(valid_row)
    wrong_columns_row = "| " + " | ".join(cells[:-1]) + " |"
    wrong_columns = plan_text.replace(valid_row, wrong_columns_row, 1)
    with pytest.raises(AssertionError) as wrong_columns_error:
        _authority_table_text(wrong_columns, "isolated PLAN.md", PV_TABLE_HEADING, PV_HEADERS)
    wrong_columns_message = str(wrong_columns_error.value)
    assert all(fragment in wrong_columns_message for fragment in (
        wrong_columns_row, f"expected columns={len(PV_HEADERS)}", f"actual columns={len(PV_HEADERS) - 1}",
    )), wrong_columns_message

    spec_ids = REQ_RE.findall(SPEC.read_text())
    rows = _pv_records()
    plan_ids = [row.requirement_id for row in rows]
    assert len(spec_ids) == 207, (
        "SPEC normative Requirement bullets changed format or count: "
        f"parsed {len(spec_ids)}, expected 207"
    )
    duplicate_spec_ids = [item for item, count in Counter(spec_ids).items() if count != 1]
    assert not duplicate_spec_ids, f"duplicate SPEC normative Requirement definitions: {duplicate_spec_ids}"
    assert len(rows) == 207, f"PLAN.md {PV_TABLE_HEADING}: parsed {len(rows)} rows, expected 207"
    duplicate_plan_ids = [item for item, count in Counter(plan_ids).items() if count != 1]
    assert not duplicate_plan_ids, f"duplicate PLAN PV rows: {duplicate_plan_ids}"
    missing_from_plan = sorted(set(spec_ids) - set(plan_ids))
    extra_in_plan = sorted(set(plan_ids) - set(spec_ids))
    assert not missing_from_plan and not extra_in_plan, (
        f"SPEC/PLAN Requirement mismatch: missing from PLAN={missing_from_plan}, "
        f"extra in PLAN={extra_in_plan}"
    )
    for row in rows:
        assert row.pv_id == f"PV-{row.requirement_id}", (
            f"{row.requirement_id}: expected PV-{row.requirement_id}, got {row.pv_id}"
        )
        evidence = _range_for(row.requirement_id)
        assert row.planned_categories, row.requirement_id
        assert evidence.final_categories, row.requirement_id


def test_each_requirement_has_one_owner():
    rows = _pv_records()
    counts = Counter(row.requirement_id for row in rows)
    bad_counts = [f"{item}: {count} PV rows" for item, count in counts.items() if count != 1]
    assert not bad_counts, f"PLAN PV Requirement ownership row counts invalid: {bad_counts}"
    _validate_ownership(rows)
    for row in rows:
        assert row.phase >= 0, f"{row.requirement_id}: invalid owning phase"
        assert re.fullmatch(r"WP-\d{2}", row.package), f"{row.requirement_id}: invalid owning package"
        assert row.day > 0, f"{row.requirement_id}: invalid owning day"
        assert row.package not in row.supporting_packages, f"{row.requirement_id}: owner duplicated as support"


def test_no_stretch_goal_is_mvp():
    spec_text = SPEC.read_text()
    stretch = re.search(r"^### 18\.3 Stretch Goals\n\n(.+?)(?=^### 18\.4)", spec_text, re.MULTILINE | re.DOTALL)
    assert stretch
    goals_text = stretch.group(1)
    goals = [item.strip("。 \n") for item in re.search(r"Stretch goals 包括(.+?)。", goals_text, re.DOTALL).group(1).split("、")]
    assert len(goals) >= 10
    assert not REQ_RE.findall(goals_text)
    assert not re.findall(r"[A-Z]{2,3}-\d{3}", goals_text)
    assert all(r.is_mvp for r in _evidence_ranges())
    plan_ids = {row.requirement_id for row in _pv_records()}
    ownership_text = "\n".join(re.findall(r"^\*\*归属 PV：\*\* .+$", PLAN.read_text(), re.MULTILINE))
    for goal in goals:
        assert goal not in plan_ids
        assert goal not in ownership_text


def test_worktree_baseline_is_clean():
    head = _git("rev-parse", "HEAD")
    assert not _git("diff", "--", "SPEC.md", "PLAN.md", ".gitignore")
    assert hashlib.sha256(SPEC.read_bytes()).hexdigest() == SPEC_DIGEST, "SPEC.md 冻结摘要不匹配"
    assert hashlib.sha256(PLAN.read_bytes()).hexdigest() == PLAN_DIGEST, "PLAN.md 冻结摘要不匹配"
    staged_paths = set(filter(None, _git("diff", "--cached", "--name-only").splitlines()))
    dirty_paths = _porcelain_paths(_git("status", "--porcelain=v1", "--untracked-files=all"))
    _validate_wp02_context(
        head=head,
        staged_paths=staged_paths,
        dirty_paths=dirty_paths,
    )


@pytest.mark.parametrize("requirement_id", WP02_REQUIREMENTS, ids=WP02_REQUIREMENTS)
def test_spec_requirement(requirement_id: str):
    matches = [row for row in _pv_records() if row.requirement_id == requirement_id]
    assert len(matches) == 1, requirement_id
    row = matches[0]
    expected_planned = ("DOC",) if requirement_id.startswith("GEN-") else (("DOC", "CI") if requirement_id.startswith("PRC-") else (("UT", "IT", "DT", "AT", "DEMO") if requirement_id.startswith("TST-") else ("UT",)))
    expected_final = ("DOC", "COLD") if requirement_id.startswith("GEN-") else (("DOC", "CI", "process evidence") if requirement_id.startswith("PRC-") else (("CI", "DEMO", "COLD") if requirement_id.startswith("TST-") else ("UT", "IT")))
    assert row.pv_id == f"PV-{requirement_id}"
    assert (row.phase, row.package, row.day) == ((1, "WP-02", 2) if requirement_id.startswith("ACT-") else (0, "WP-01", 1))
    assert row.planned_node == f"tests/unit/agent/test_actions.py::test_spec_requirement[{requirement_id}]"
    assert row.planned_categories == expected_planned
    assert row.supporting_packages == ("WP-28", "WP-29")
    assert row.status == "PLANNED"
    evidence = _range_for(requirement_id)
    assert evidence.final_categories == expected_final
    assert evidence.is_mvp
    process = (ROOT / "SPEC_PROCESS.md").read_text()
    _validate_process_evidence_text(process, source="SPEC_PROCESS.md")
    if requirement_id.startswith("ACT-"):
        _assert_owned_action_requirement(requirement_id)


def _load_actions_api():
    try:
        module = importlib.import_module("coding_harness.agent.actions")
    except ModuleNotFoundError as exc:
        if exc.name in {"coding_harness.agent", "coding_harness.agent.actions"}:
            pytest.fail(f"WP-02 actions API is missing ({exc.name})", pytrace=False)
        raise
    required = ("ActionParseError", "StructuredAction", "ControlAction", "ToolAction", "parse_action")
    missing = [name for name in required if not hasattr(module, name)]
    if missing:
        pytest.fail(f"WP-02 actions API symbols are missing: {missing}", pytrace=False)
    return module


def _load_results_api():
    try:
        module = importlib.import_module("coding_harness.agent.results")
    except ModuleNotFoundError as exc:
        if exc.name in {"coding_harness.agent", "coding_harness.agent.results"}:
            pytest.fail(f"WP-02 results API is missing ({exc.name})", pytrace=False)
        raise
    missing = [name for name in ("ToolResultStatus", "ToolResult") if not hasattr(module, name)]
    if missing:
        pytest.fail(f"WP-02 results API symbols are missing: {missing}", pytrace=False)
    return module


def _action(action_type: str, parameters: object, expected: str | None = None) -> dict[str, object]:
    return {"action_id": f"action:{action_type}", "action_type": action_type, "parameters": parameters, "budget_impact": {"action_proposals": 1}, "expected_result_type": expected or ("control_result" if action_type in CONTROL_TYPES else "tool_result")}


class _MustRejectBeforeSecondItem(Mapping[str, object]):
    """A Mapping probe proving normalization rejects before traversing later items."""

    def __getitem__(self, key: str) -> object:
        if key == "oversized":
            return "x" * 65_536
        raise AssertionError("normalizer traversed beyond the exhausted byte budget")

    def __iter__(self) -> Iterator[str]:
        return iter(("oversized", "must_not_be_read"))

    def __len__(self) -> int:
        return 2


class _ExplodingMapping(Mapping[str, object]):
    def __init__(self, marker: str) -> None:
        self.marker = marker

    def __getitem__(self, key: str) -> object:
        raise RuntimeError(self.marker)

    def __iter__(self) -> Iterator[str]:
        raise RuntimeError(self.marker)

    def __len__(self) -> int:
        return 1

    def items(self):
        raise RuntimeError(self.marker)


class _EvilStr(str):
    def __new__(cls, value: str):
        instance = super().__new__(cls, value)
        instance.mutable = ["caller-owned"]
        return instance

    def encode(self, *_args, **_kwargs):
        return b"x"

    def __str__(self) -> str:
        return "TOP_SECRET_EVIL_STR_MARKER_41ce"


class _EvilInt(int):
    def __new__(cls, value: int):
        instance = super().__new__(cls, value)
        instance.mutable = ["caller-owned"]
        return instance

    def __str__(self) -> str:
        return "1"


class _SequencedResourceCounts(Mapping[str, int]):
    def __init__(
        self,
        batches: list[list[tuple[str, int]]],
        *,
        reported_length: int = 1,
    ) -> None:
        self.batches = batches
        self.reported_length = reported_length
        self.items_calls = 0

    def __getitem__(self, key: str) -> int:
        for candidate, value in self.batches[0]:
            if candidate == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(key for key, _ in self.batches[0])

    def __len__(self) -> int:
        return self.reported_length

    def items(self):
        batch_index = min(self.items_calls, len(self.batches) - 1)
        self.items_calls += 1
        return iter(self.batches[batch_index])


def _nested_object(container_depth: int) -> dict[str, object]:
    assert container_depth >= 1
    value: dict[str, object] = {"leaf": 1}
    for _ in range(container_depth - 1):
        value = {"nested": value}
    return value


def _normalized_size(value: object) -> int:
    return len(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _action_with_normalized_size(size: int) -> dict[str, object]:
    raw = _action("create_file", {"path": "src/new.py", "content": ""})
    remaining = size - _normalized_size(raw)
    assert remaining >= 0
    raw["parameters"]["content"] = "x" * remaining
    assert _normalized_size(raw) == size
    return raw


def _control_parameters(action_type: str) -> dict[str, object]:
    return {
        "request_clarification": {
            "question": "Please clarify the bounded requirement.",
        },
        "propose_plan": {
            "proposal": {
                "summary": "local proposal",
                "risks": ["scope change"],
                "metadata": {"owner": "user", "priority": 1},
            },
        },
        "request_budget_extension": {
            "request": {
                "reason": "additional work",
                "requested": {"tool_calls": 3},
            },
        },
        "request_user_confirmation": {
            "condition": {
                "prompt": "Confirm completion",
                "context": {"source": "user"},
            },
        },
        "report_blocked": {
            "report": {
                "summary": "blocked",
                "details": ["missing input"],
            },
        },
        "stop_with_failure": {
            "report": {
                "summary": "validation failed",
                "details": ["exit status 2"],
            },
        },
        "stop_without_safe_action": {
            "report": {
                "summary": "no safe action",
                "details": ["remaining actions exceed the boundary"],
            },
        },
    }[action_type]


def _tool_parameters(action_type: str) -> dict[str, object]:
    return {"inspect_repository": {}, "list_files": {"path": "src", "limit": 10}, "read_file": {"path": "src/file.py", "start_byte": 0, "max_bytes": 128}, "search_text": {"text": "needle", "paths": ["src"], "limit": 10}, "create_file": {"path": "src/new.py", "content": "x = 1\n"}, "replace_file": {"path": "src/file.py", "expected_digest": "abc", "content": "x = 2\n"}, "apply_patch": {"path": "src/file.py", "patch": {"operations": []}, "expected_digest": "abc"}, "delete_file": {"path": "src/file.py", "expected_digest": "abc", "reason": "requested change"}, "request_ignored_input": {"paths": ["input.txt"], "mode": "read_only_input", "phase": "INVESTIGATING", "manifest_version": "v1"}, "run_validation": {"profile": "python312", "operation": "pytest"}, "git_repo_probe": {}, "git_repo_root": {}, "git_status": {}, "git_diff_worktree": {"paths": ["src/file.py"]}, "git_diff_index": {"paths": ["src/file.py"]}, "git_list_tracked": {"paths": ["src/file.py"]}, "git_list_untracked": {"paths": ["src/file.py"]}, "git_stage_paths": {"paths": ["src/file.py"]}, "git_unstage_paths": {"paths": ["src/file.py"]}}[action_type]


def _control_container(action_type: str, container: object) -> dict[str, object]:
    return {_CONTROL_FIELDS[action_type]: container}


def _wire_forms(raw: dict[str, object]) -> tuple[dict[str, object], str]:
    return raw, json.dumps(raw)


def _invalid_control_parameters(action_type: str) -> tuple[dict[str, object], ...]:
    if action_type == "request_clarification":
        return ({}, {"question": "One question?", "extra": "not allowed"}, {"question": 7})
    field = _CONTROL_FIELDS[action_type]
    return (
        {},
        {field: _control_parameters(action_type)[field], "extra": "not allowed"},
        {field: {}},
        {field: "not an object"},
    )


def _rejected(api, raw: object) -> None:
    with pytest.raises(api.ActionParseError) as caught:
        api.parse_action(raw)
    error = caught.value
    assert error.code in {"INVALID_JSON", "INVALID_ACTION", "INVALID_FIELD", "INVALID_VALUE", "INPUT_TOO_LARGE"}
    assert isinstance(error.field_path, str) and isinstance(error.reason, str) and error.reason


def _assert_bounded_safe_rejection(api, raw: object, secret_marker: str) -> None:
    with pytest.raises(api.ActionParseError) as caught:
        api.parse_action(raw)
    error = caught.value
    assert secret_marker not in error.field_path
    assert secret_marker not in error.reason
    assert secret_marker not in str(error)
    assert len(error.field_path) <= 256
    assert len(error.reason) <= 256
    assert len(str(error)) <= 600


def _assert_exception_graph_is_safe(error: BaseException, secret_marker: str) -> None:
    pending: list[BaseException] = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        exposed = (
            str(current),
            repr(current),
            repr(current.args),
            repr(getattr(current, "doc", None)),
            repr(getattr(current, "object", None)),
        )
        assert all(secret_marker not in value for value in exposed), exposed
        for linked in (current.__cause__, current.__context__):
            if linked is not None:
                pending.append(linked)


def _assert_invalid_action_value(api, raw: object, field_path: str) -> None:
    with pytest.raises(api.ActionParseError) as caught:
        api.parse_action(raw)
    assert caught.value.code == "INVALID_VALUE"
    assert caught.value.field_path == field_path
    assert caught.value.reason


def _assert_owned_action_requirement(requirement_id: str) -> None:
    actions = _load_actions_api()
    if requirement_id == "ACT-001":
        for candidate in _wire_forms(
            _action(
                "request_budget_extension",
                {"request": {"detail": "missing the D.1 required semantics"}},
            )
        ):
            assert actions.parse_action(candidate).to_dict()["parameters"] == {
                "request": {"detail": "missing the D.1 required semantics"}
            }
        for candidate in _wire_forms(
            _action(
                "run_validation",
                {"profile": "anything", "operation": "arbitrary"},
            )
        ):
            _rejected(actions, candidate)
        non_finite_json = (
            '{"action_id":"action:propose_plan","action_type":"propose_plan",'
            '"parameters":{"proposal":{"number":1e999}},'
            '"budget_impact":{"action_proposals":1},'
            '"expected_result_type":"control_result"}'
        )
        non_finite_mapping = _action("propose_plan", _control_container("propose_plan", {"number": float("inf")}))
        for raw in (non_finite_json, non_finite_mapping):
            _assert_invalid_action_value(actions, raw, "$.parameters.proposal.number")
        for invalid_type in ([], {}):
            raw = _action("inspect_repository", {}) | {"expected_result_type": invalid_type}
            _assert_invalid_action_value(actions, raw, "$.expected_result_type")
        exact_limit = _action_with_normalized_size(65_536)
        for raw in (exact_limit, json.dumps(exact_limit, ensure_ascii=False, sort_keys=True, separators=(",", ":"))):
            assert actions.parse_action(raw).to_dict() == exact_limit
        over_limit = _action_with_normalized_size(65_537)
        for raw in (over_limit, json.dumps(over_limit, ensure_ascii=False, sort_keys=True, separators=(",", ":"))):
            _rejected(actions, raw)
        for raw in (
            _action("propose_plan", _control_container("propose_plan", {"text": "\ud800"})),
            json.dumps(_action("propose_plan", _control_container("propose_plan", {"text": "\ud800"}))),
        ):
            _assert_invalid_action_value(actions, raw, "$.parameters.proposal.text")
        secret_marker = "deep-json-input-must-not-leak"
        deeply_nested_json = "[" * 30_000 + json.dumps(secret_marker) + "]" * 30_000
        assert len(deeply_nested_json.encode("utf-8")) < 65_536
        _assert_bounded_safe_rejection(actions, deeply_nested_json, secret_marker)
        _rejected(actions, _action("unknown_action", {}))
    elif requirement_id == "ACT-002":
        raw = _action("inspect_repository", {}) | {
            "action_id": "stable.action:2",
            "budget_impact": {"action_proposals": 1, "token_budget": 2},
        }
        assert actions.parse_action(raw).to_dict() == raw
        semantic = _action("request_budget_extension", _control_parameters("request_budget_extension"))
        assert actions.parse_action(semantic).to_dict()["parameters"] == semantic["parameters"]
        for action_class in (actions.StructuredAction, actions.ControlAction, actions.ToolAction):
            with pytest.raises(TypeError):
                action_class()
            with pytest.raises(TypeError):
                action_class(
                    action_id="action:direct",
                    action_type="inspect_repository",
                    parameters={"mutable": []},
                    budget_impact={"action_proposals": 1},
                    expected_result_type="tool_result",
                )
    elif requirement_id == "ACT-003":
        _rejected(actions, _action("list_files", {"path": "src", "limit": 1, "command": "ls"}))
        for raw in (
            _action("propose_plan", _control_container("propose_plan", {"nested": {"command": "ls"}})),
            _action("apply_patch", {"path": "src/file.py", "patch": {"nested": {"command": "ls"}}, "expected_digest": "abc"}),
        ):
            _rejected(actions, raw)
        secret_marker = "private-key-material"
        secret = secret_marker + "-" + "z" * 20_000
        for raw in (
            _action("inspect_repository", {}) | {secret: 1},
            json.dumps({"safe": 1})[:-1] + f',"{secret}":1,"{secret}":2}}',
            _action("inspect_repository", {}) | {"budget_impact": {secret: 1}},
        ):
            _assert_bounded_safe_rejection(actions, raw, secret_marker)
    elif requirement_id == "ACT-008":
        results = _load_results_api()
        result = results.ToolResult(
            action_id="action:result",
            status=results.ToolResultStatus.SUCCEEDED,
            summary="bounded result",
            output="",
            resource_counts={"files": 1},
            truncated=False,
            error=None,
        )
        assert result.to_dict() == {
            "action_id": "action:result", "status": "SUCCEEDED", "summary": "bounded result",
            "output": "", "resource_counts": {"files": 1}, "truncated": False, "error": None,
        }
        with pytest.raises(ValueError):
            results.ToolResult(
                action_id="action:result\0secret",
                status=results.ToolResultStatus.SUCCEEDED,
                summary="bounded result",
                output="",
                resource_counts={"files": 1},
                truncated=False,
                error=None,
            )
    elif requirement_id == "ACT-009":
        control = actions.parse_action(_action("request_clarification", _control_parameters("request_clarification")))
        tool = actions.parse_action(_action("inspect_repository", {}))
        assert isinstance(control, actions.ControlAction)
        assert isinstance(tool, actions.ToolAction)
        assert isinstance(control, actions.StructuredAction)
        assert isinstance(tool, actions.StructuredAction)
        ignored_input = actions.parse_action(
            _action("request_ignored_input", _tool_parameters("request_ignored_input"))
        )
        validation = actions.parse_action(
            _action("run_validation", {"profile": "nodejs20_npm", "operation": "typecheck"})
        )
        assert ignored_input.to_dict()["parameters"]["mode"] == "read_only_input"
        assert validation.to_dict()["parameters"] == {
            "profile": "nodejs20_npm",
            "operation": "typecheck",
        }
        for rejected in (
            _action("request_ignored_input", {"paths": ["input.txt"], "mode": "copy", "phase": "INVESTIGATING", "manifest_version": "v1"}),
            _action("run_validation", {"profile": "nodejs20_npm", "operation": "pytest"}),
        ):
            _rejected(actions, rejected)
    elif requirement_id == "ACT-010":
        for action_type in GOVERNANCE_TYPES:
            with pytest.raises(actions.ActionParseError) as caught:
                actions.parse_action(_action(action_type, {}))
            assert (caught.value.code, caught.value.field_path) == ("INVALID_ACTION", "$.action_type")
    elif requirement_id == "ACT-011":
        for action_type in INTERNAL_TYPES:
            with pytest.raises(actions.ActionParseError) as caught:
                actions.parse_action(_action(action_type, {}))
            assert (caught.value.code, caught.value.field_path) == ("INVALID_ACTION", "$.action_type")
    else:
        raise AssertionError(f"unexpected WP-02 requirement {requirement_id}")


@pytest.mark.parametrize("action_type", CONTROL_TYPES, ids=CONTROL_TYPES)
def test_known_control_action(action_type: str):
    api = _load_actions_api()
    raw = _action(action_type, _control_parameters(action_type))
    parsed = api.parse_action(raw)
    parsed_json = api.parse_action(json.dumps(raw))
    snapshot = parsed.to_dict()
    if action_type == "propose_plan":
        raw["parameters"]["proposal"]["metadata"]["owner"] = "caller mutation"
    assert isinstance(parsed, api.ControlAction) and parsed.expected_result_type == "control_result"
    assert parsed.to_dict() == snapshot
    assert parsed_json.to_dict() == snapshot
    if action_type == "request_clarification":
        exact_utf8 = "界" * 1_365 + "a"
        assert len(exact_utf8.encode("utf-8")) == 4_096
        assert api.parse_action(_action(action_type, {"question": exact_utf8})).to_dict()["parameters"]["question"] == exact_utf8
        for invalid in (exact_utf8 + "b", "question\0tail"):
            _rejected(api, _action(action_type, {"question": invalid}))
    else:
        field = _CONTROL_FIELDS[action_type]
        for valid in (
            {f"key_{index}": index for index in range(64)},
            {"items": list(range(256))},
            _nested_object(16),
        ):
            assert api.parse_action(
                _action(action_type, _control_container(action_type, valid))
            ).to_dict()["parameters"][field] == valid
        for invalid in (
            {f"key_{index}": index for index in range(65)},
            {"items": list(range(257))},
            _nested_object(17),
        ):
            _rejected(api, _action(action_type, _control_container(action_type, invalid)))
    for parameters in _invalid_control_parameters(action_type):
        for candidate in _wire_forms(_action(action_type, parameters)):
            _rejected(api, candidate)


@pytest.mark.parametrize("action_type", TOOL_TYPES, ids=TOOL_TYPES)
def test_known_tool_action(action_type: str):
    api = _load_actions_api()
    raw = _action(action_type, _tool_parameters(action_type))
    parsed = api.parse_action(json.dumps(raw))
    assert isinstance(parsed, api.ToolAction) and parsed.expected_result_type == "tool_result" and parsed.to_dict() == raw
    assert api.parse_action(raw).to_dict() == raw
    if action_type == "apply_patch":
        invalid_values = ("\ud800", "patch\0tail")
        for invalid in invalid_values:
            mapping = _action(action_type, {"path": "src/file.py", "patch": {"text": invalid}, "expected_digest": "abc"})
            for candidate in (mapping, json.dumps(mapping)):
                _rejected(api, candidate)
    elif action_type == "git_stage_paths":
        valid = _action(action_type, {"paths": [f"src/{index}.py" for index in range(256)]})
        assert len(api.parse_action(valid).to_dict()["parameters"]["paths"]) == 256
        _rejected(api, _action(action_type, {"paths": [f"src/{index}.py" for index in range(257)]}))
    elif action_type == "request_ignored_input":
        for mode in ("read_only_input", "writable_ephemeral"):
            valid = _action(
                action_type,
                {"paths": ["input.txt"], "mode": mode, "phase": "EXECUTING", "manifest_version": "v1"},
            )
            for candidate in _wire_forms(valid):
                assert api.parse_action(candidate).to_dict() == valid
        invalid_parameters = (
            {"paths": ["input.txt"], "phase": "INVESTIGATING", "manifest_version": "v1"},
            {"paths": ["input.txt"], "mode": "read_only_input", "phase": "INVESTIGATING", "manifest_version": "v1", "extra": "not allowed"},
            {"paths": ["input.txt"], "mode": "copy", "phase": "INVESTIGATING", "manifest_version": "v1"},
            {"paths": ["input.txt"], "mode": "read_only_input", "phase": "made_up", "manifest_version": "v1"},
            {"paths": ["input.txt"], "mode": 7, "phase": "INVESTIGATING", "manifest_version": "v1"},
        )
        for parameters in invalid_parameters:
            for candidate in _wire_forms(_action(action_type, parameters)):
                _rejected(api, candidate)
    elif action_type == "run_validation":
        for profile, operation in (
            ("python312", "pytest"),
            ("python312", "ruff"),
            ("nodejs20_npm", "test"),
            ("nodejs20_npm", "lint"),
            ("nodejs20_npm", "build"),
            ("nodejs20_npm", "typecheck"),
        ):
            valid = _action(action_type, {"profile": profile, "operation": operation})
            for candidate in _wire_forms(valid):
                assert api.parse_action(candidate).to_dict() == valid
        invalid_parameters = (
            {"profile": "python312"},
            {"profile": "python312", "operation": "pytest", "extra": "not allowed"},
            {"profile": "anything", "operation": "pytest"},
            {"profile": "python312", "operation": "test"},
            {"profile": "nodejs20_npm", "operation": "pytest"},
            {"profile": "python312", "operation": 7},
        )
        for parameters in invalid_parameters:
            for candidate in _wire_forms(_action(action_type, parameters)):
                _rejected(api, candidate)


def test_unknown_action_fails_closed():
    api = _load_actions_api()
    cases: list[object] = [_action("made_up_action", {}), _action("inspect_repository", {}) | {"action_type": 7}, {key: value for key, value in _action("inspect_repository", {}).items() if key != "action_type"}, "{not json", '{"action_id":"a","action_id":"b"}', '{"action_id":"a","action_type":"inspect_repository","parameters":{"x":1,"x":2},"budget_impact":{"a":1},"expected_result_type":"tool_result"}', "[]", b"{}", _action("inspect_repository", {"bad": {"x"}}), _action("inspect_repository", {"bad": object()}), _action("inspect_repository", {1: "bad"}), "x" * 65537, _action("propose_plan", {"proposal": _MustRejectBeforeSecondItem()})]
    for raw in cases:
        _rejected(api, raw)
    for raw in (
        _action("propose_plan", _control_container("propose_plan", {"text": "\ud800"})),
        json.dumps(_action("propose_plan", _control_container("propose_plan", {"text": "\ud800"}))),
        _action("propose_plan", _control_container("propose_plan", {"text": "embedded\0nul"})),
        json.dumps(_action("propose_plan", _control_container("propose_plan", {"text": "embedded\0nul"}))),
    ):
        _rejected(api, raw)


def test_unknown_field_fails_closed():
    api = _load_actions_api()
    cases = [_action("inspect_repository", {}) | {"extra": 1}, _action("inspect_repository", {"extra": 1})]
    cases += [_action("list_files", {"path": "src", "limit": 1, field: "value"}) for field in ("command", "cmd", "shell", "argv", "git_command", "docker_command", "script")]
    cases += [_action("propose_plan", _control_container("propose_plan", {"nested": {"command": "value"}})), _action("propose_plan", {"proposal": {}}), _action("propose_plan", _control_container("propose_plan", {"text": "x" * 65537}))]
    cases += [
        _action("propose_plan", _control_container("propose_plan", {f"key_{index}": index for index in range(65)})),
        _action("propose_plan", _control_container("propose_plan", {"items": list(range(257))})),
        _action("propose_plan", _control_container("propose_plan", _nested_object(17))),
    ]
    for raw in cases:
        _rejected(api, raw)
    for valid in (
        {f"key_{index}": index for index in range(64)},
        {"items": list(range(256))},
        _nested_object(16),
    ):
        assert api.parse_action(_action("propose_plan", _control_container("propose_plan", valid))).to_dict()["parameters"]["proposal"] == valid

    secret_marker = "do-not-leak-this-secret"
    secret = secret_marker + "-" + "x" * 20_000
    unknown_top = _action("inspect_repository", {}) | {secret: 1}
    duplicate_json = json.dumps({"safe": 1})[:-1] + f',"{secret}":1,"{secret}":2}}'
    invalid_budget = _action("inspect_repository", {}) | {"budget_impact": {secret: 1}}
    for raw in (unknown_top, duplicate_json, invalid_budget):
        _assert_bounded_safe_rejection(api, raw, secret_marker)


def test_action_identity_and_budget():
    api = _load_actions_api()
    parsed = api.parse_action(_action("inspect_repository", {}) | {"action_id": "A.1:_ok-2", "budget_impact": {"zeta": 2, "alpha": 0}})
    copied = parsed.to_dict(); copied["budget_impact"]["zeta"] = 99
    assert parsed.to_dict()["budget_impact"] == {"alpha": 0, "zeta": 2}
    cases = [_action("inspect_repository", {}) | {"action_id": ""}, _action("inspect_repository", {}) | {"action_id": "a" * 129}, _action("inspect_repository", {}) | {"action_id": "é"}, _action("inspect_repository", {}) | {"action_id": "id\0tail"}, _action("inspect_repository", {}) | {"action_id": "_bad"}, _action("inspect_repository", {}) | {"budget_impact": {}}, _action("inspect_repository", {}) | {"budget_impact": {f"k{i}": 1 for i in range(17)}}, _action("inspect_repository", {}) | {"budget_impact": {"Bad": 1}}, _action("inspect_repository", {}) | {"budget_impact": {"cost": -1}}, _action("inspect_repository", {}) | {"budget_impact": {"cost": 2 ** 63}}, _action("inspect_repository", {}) | {"budget_impact": {"cost": True}}, _action("inspect_repository", {}) | {"budget_impact": {"cost": 0}}, _action("inspect_repository", {}, "control_result")]
    for raw in cases:
        _rejected(api, raw)


def test_required_bounded_tool_result():
    api = _load_results_api(); Result, Status = api.ToolResult, api.ToolResultStatus
    base = {"action_id": "action:result", "summary": "bounded result", "output": "", "resource_counts": {"files": 1}, "truncated": False, "error": None}
    succeeded = Result(status=Status.SUCCEEDED, **base)
    assert Result(status=Status.TRUNCATED, **(base | {"truncated": True})).status == Status.TRUNCATED
    assert Result(status=Status.FAILED, **(base | {"error": "failed"})).status == Status.FAILED
    assert Result(status=Status.DENIED, **(base | {"error": "denied"})).status == Status.DENIED
    summary_limit = "界" * 1_365 + "a"
    output_limit = "界" * 21_845 + "a"
    assert len(summary_limit.encode("utf-8")) == 4_096
    assert len(output_limit.encode("utf-8")) == 65_536
    assert Result(status=Status.SUCCEEDED, **(base | {"summary": summary_limit})).summary == summary_limit
    assert Result(status=Status.SUCCEEDED, **(base | {"output": output_limit})).output == output_limit
    max_resources = {f"key_{index}": 2**63 - 1 for index in range(16)}
    assert len(Result(status=Status.SUCCEEDED, **(base | {"resource_counts": max_resources})).resource_counts) == 16
    assert Result(status=Status.SUCCEEDED, **(base | {"resource_counts": {"k" * 64: 2**63 - 1}})).to_dict()["resource_counts"] == {"k" * 64: 2**63 - 1}
    cases = [base | {"status": Status.SUCCEEDED, "action_id": ""}, base | {"status": Status.SUCCEEDED, "action_id": "é"}, base | {"status": Status.SUCCEEDED, "action_id": "id\0tail"}, base | {"status": "SUCCEEDED"}, base | {"status": Status.SUCCEEDED, "summary": ""}, base | {"status": Status.SUCCEEDED, "summary": summary_limit + "b"}, base | {"status": Status.SUCCEEDED, "summary": "summary\0tail"}, base | {"status": Status.SUCCEEDED, "output": output_limit + "b"}, base | {"status": Status.SUCCEEDED, "output": "output\0tail"}, base | {"status": Status.SUCCEEDED, "resource_counts": {f"k{i}": i for i in range(17)}}, base | {"status": Status.SUCCEEDED, "resource_counts": {"k" * 65: 1}}, base | {"status": Status.SUCCEEDED, "resource_counts": {"Bad": 1}}, base | {"status": Status.SUCCEEDED, "resource_counts": {"files": -1}}, base | {"status": Status.SUCCEEDED, "resource_counts": {"files": 2**63}}, base | {"status": Status.SUCCEEDED, "resource_counts": {"files": True}}, base | {"status": Status.SUCCEEDED, "truncated": 1}, base | {"status": Status.SUCCEEDED, "error": "no"}, base | {"status": Status.SUCCEEDED, "truncated": True}, base | {"status": Status.TRUNCATED}, base | {"status": Status.TRUNCATED, "truncated": True, "error": "no"}, base | {"status": Status.FAILED}, base | {"status": Status.DENIED}, base | {"status": Status.FAILED, "error": ""}, base | {"status": Status.DENIED, "error": ""}, base | {"status": Status.FAILED, "error": "error\0tail"}, base | {"status": Status.FAILED, "error": summary_limit + "b"}, base | {"status": Status.FAILED, "error": 1}, base | {"status": Status.FAILED, "truncated": True, "error": "failed"}, base | {"status": Status.DENIED, "truncated": True, "error": "denied"}, base | {"status": Status.SUCCEEDED, "extra": 1}]
    for raw in cases:
        with pytest.raises((TypeError, ValueError), match="."):
            Result(**raw)
    copied = succeeded.to_dict(); copied["resource_counts"]["files"] = 99
    assert succeeded.to_dict()["resource_counts"] == {"files": 1}


def test_quality_q01_json_parse_error_does_not_retain_raw_input():
    api = _load_actions_api()
    secret = "TOP_SECRET_JSON_MARKER_9f4a"
    raw = '{"action_id": "' + secret

    with pytest.raises(api.ActionParseError) as caught:
        api.parse_action(raw)

    _assert_exception_graph_is_safe(caught.value, secret)


def test_quality_q01_mapping_exception_is_safely_converted():
    api = _load_actions_api()
    secret = "TOP_SECRET_MAPPING_MARKER_7b2c"

    with pytest.raises(api.ActionParseError) as caught:
        api.parse_action(_ExplodingMapping(secret))

    _assert_exception_graph_is_safe(caught.value, secret)


def test_quality_q01_tool_result_mapping_exception_is_safely_converted():
    api = _load_results_api()
    secret = "TOP_SECRET_RESULT_MAPPING_MARKER_a81d"

    with pytest.raises(ValueError) as caught:
        api.ToolResult(
            action_id="action:result",
            status=api.ToolResultStatus.SUCCEEDED,
            summary="bounded result",
            output="",
            resource_counts=_ExplodingMapping(secret),
            truncated=False,
            error=None,
        )

    _assert_exception_graph_is_safe(caught.value, secret)


def test_quality_q01_unsupported_value_type_name_does_not_leak():
    api = _load_actions_api()
    secret = "MAIN_UNIQUE_TYPE_MARKER_c3e17"
    evil_type = type(secret, (), {})
    raw = _action(
        "propose_plan",
        {"proposal": {"value": evil_type()}},
    )

    with pytest.raises(api.ActionParseError) as caught:
        api.parse_action(raw)

    _assert_exception_graph_is_safe(caught.value, secret)


def test_quality_q02_action_rejects_scalar_subclasses():
    api = _load_actions_api()
    evil_action_id = _EvilStr("action:evil")
    evil_question = _EvilStr("Please clarify")
    evil_budget = _EvilInt(1)
    evil_nested = _EvilStr("nested value")
    cases = (
        _action("inspect_repository", {}) | {"action_id": evil_action_id},
        _action("request_clarification", {"question": evil_question}),
        _action("inspect_repository", {}) | {"budget_impact": {"action_proposals": evil_budget}},
        _action("propose_plan", {"proposal": {"nested": evil_nested}}),
    )

    for raw in cases:
        with pytest.raises(api.ActionParseError):
            api.parse_action(raw)

    for value in (evil_action_id, evil_question, evil_budget, evil_nested):
        value.mutable.append("caller mutation")


@pytest.mark.parametrize("field", ("summary", "output"))
def test_quality_q02_tool_result_rejects_string_subclasses(field: str):
    api = _load_results_api()
    evil = _EvilStr("bounded value")
    values = {
        "action_id": "action:result",
        "status": api.ToolResultStatus.SUCCEEDED,
        "summary": "bounded result",
        "output": "",
        "resource_counts": {"files": 1},
        "truncated": False,
        "error": None,
    }
    values[field] = evil

    with pytest.raises(ValueError):
        api.ToolResult(**values)

    evil.mutable.append("caller mutation")


def test_quality_q02_tool_result_rejects_resource_count_integer_subclass():
    api = _load_results_api()
    evil = _EvilInt(1)

    with pytest.raises(ValueError):
        api.ToolResult(
            action_id="action:result",
            status=api.ToolResultStatus.SUCCEEDED,
            summary="bounded result",
            output="",
            resource_counts={"files": evil},
            truncated=False,
            error=None,
        )

    evil.mutable.append("caller mutation")


@pytest.mark.parametrize("container_kind", ("control", "patch"))
@pytest.mark.parametrize(
    "forbidden_key",
    ("Command", "COMMAND", "ｃｏｍｍａｎｄ", "ＣＭＤ", "git＿command", "Ｓｃｒｉｐｔ"),
)
def test_quality_q03_forbidden_command_keys_are_unicode_normalized(
    container_kind: str, forbidden_key: str
):
    api = _load_actions_api()
    nested = {"level_one": {"level_two": {forbidden_key: "payload"}}}
    if container_kind == "control":
        raw = _action("propose_plan", {"proposal": nested})
    else:
        raw = _action(
            "apply_patch",
            {"path": "src/file.py", "patch": nested, "expected_digest": "abc"},
        )

    with pytest.raises(api.ActionParseError) as caught:
        api.parse_action(raw)

    assert caught.value.code == "INVALID_FIELD"


@pytest.mark.parametrize(
    ("raw", "expected_path"),
    (
        (
            _action(
                "propose_plan",
                {"proposal": {"metadata": {"ＣＭＤ": "do not execute"}}},
            ),
            "$.parameters.proposal.metadata.ＣＭＤ",
        ),
        (
            _action(
                "apply_patch",
                {
                    "path": "src/file.py",
                    "patch": {"report": {"details": {"git＿command": "example"}}},
                    "expected_digest": "abc",
                },
            ),
            "$.parameters.patch.report.details.git＿command",
        ),
    ),
)
def test_quality_q03_unicode_forbidden_field_path_preserves_original_key(
    raw: dict[str, object], expected_path: str
):
    api = _load_actions_api()

    with pytest.raises(api.ActionParseError) as caught:
        api.parse_action(raw)

    assert caught.value.code == "INVALID_FIELD"
    assert caught.value.field_path == expected_path
    assert "<field>" not in caught.value.field_path
    assert "do not execute" not in str(caught.value)
    assert "example" not in str(caught.value)


def test_quality_q03_command_words_in_string_values_remain_valid():
    api = _load_actions_api()
    text_values = (
        "run this command",
        "shell documentation",
        "git command example",
    )
    control = _action("propose_plan", {"proposal": {"notes": list(text_values)}})
    patch = _action(
        "apply_patch",
        {
            "path": "src/file.py",
            "patch": {"notes": list(text_values)},
            "expected_digest": "abc",
        },
    )

    assert api.parse_action(control).to_dict() == control
    assert api.parse_action(patch).to_dict() == patch


def test_quality_q04_resource_counts_limit_uses_actual_iteration_count():
    api = _load_results_api()
    mapping = _SequencedResourceCounts(
        [[(f"key_{index}", index) for index in range(17)]],
        reported_length=1,
    )

    with pytest.raises(ValueError, match="at most 16"):
        api.ToolResult(
            action_id="action:result",
            status=api.ToolResultStatus.SUCCEEDED,
            summary="bounded result",
            output="",
            resource_counts=mapping,
            truncated=False,
            error=None,
        )

    assert mapping.items_calls == 1


def test_quality_q04_resource_counts_rejects_duplicate_keys():
    api = _load_results_api()
    mapping = _SequencedResourceCounts(
        [[("files", 1), ("files", 2)]],
        reported_length=1,
    )

    with pytest.raises(ValueError, match="duplicate key"):
        api.ToolResult(
            action_id="action:result",
            status=api.ToolResultStatus.SUCCEEDED,
            summary="bounded result",
            output="",
            resource_counts=mapping,
            truncated=False,
            error=None,
        )


def test_quality_q04_resource_counts_uses_one_stable_snapshot():
    api = _load_results_api()
    mapping = _SequencedResourceCounts(
        [[("files", 1), ("bytes", 2)], [("changed", 99)]],
        reported_length=1,
    )
    result = api.ToolResult(
        action_id="action:result",
        status=api.ToolResultStatus.SUCCEEDED,
        summary="bounded result",
        output="",
        resource_counts=mapping,
        truncated=False,
        error=None,
    )

    mapping.batches[:] = [[("mutated", 1000)]]
    assert mapping.items_calls == 1
    assert result.resource_counts == (("bytes", 2), ("files", 1))
    assert result.to_dict()["resource_counts"] == {"bytes": 2, "files": 1}
    assert mapping.items_calls == 1


@pytest.mark.parametrize("action_type", GOVERNANCE_TYPES, ids=GOVERNANCE_TYPES)
def test_llm_governance_rejected(action_type: str):
    _rejected(_load_actions_api(), _action(action_type, {}))


@pytest.mark.parametrize("action_type", INTERNAL_TYPES, ids=INTERNAL_TYPES)
def test_internal_operation_rejected(action_type: str):
    _rejected(_load_actions_api(), _action(action_type, {}))
