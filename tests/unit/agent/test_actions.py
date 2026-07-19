from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import importlib
from pathlib import Path
import re
import subprocess

import pytest


BASELINE_COMMIT = "c90f02f30df4ce65328ff397714cc06c4d7b1a27"
ALLOWED_WP01_PATHS = {
    "pyproject.toml",
    "SPEC_PROCESS.md",
    "AGENT_LOG.md",
    "REFLECTION.md",
    "src/coding_harness/__init__.py",
    "tests/unit/agent/test_actions.py",
}
WP01_REQUIREMENTS = (
    "GEN-001", "GEN-002", "GEN-003",
    "PRC-001", "PRC-002", "PRC-003", "PRC-004", "PRC-005",
    "PRC-006", "PRC-007", "PRC-008", "PRC-009", "PRC-010",
    "TST-008",
)


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
    return completed.stdout.strip()


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


def _main_worktree() -> Path:
    records = _git("worktree", "list", "--porcelain").split("\n\n")
    matches: list[Path] = []
    for record in records:
        fields = record.splitlines()
        worktree = next((line.removeprefix("worktree ") for line in fields if line.startswith("worktree ")), None)
        branch = next((line.removeprefix("branch ") for line in fields if line.startswith("branch ")), None)
        if worktree and branch == "refs/heads/main":
            matches.append(Path(worktree))
    assert len(matches) == 1, f"expected one main worktree in git worktree list, found {matches}"
    return matches[0]


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
    branch = _git("branch", "--show-current")
    assert branch == "wp-01-process-baseline", f"linked worktree branch mismatch: {branch!r}"
    _git("merge-base", "--is-ancestor", BASELINE_COMMIT, "HEAD")
    head = _git("rev-parse", "HEAD")
    assert head == BASELINE_COMMIT, f"linked worktree HEAD mismatch: expected {BASELINE_COMMIT}, got {head}"
    assert not _git("diff", "--", "SPEC.md", "PLAN.md", ".gitignore")
    assert not _git("diff", "--cached", "--name-only")
    dirty_paths = _porcelain_paths(_git("status", "--porcelain=v1", "--untracked-files=all"))
    unexpected = sorted(dirty_paths - ALLOWED_WP01_PATHS)
    assert not unexpected, f"unexpected linked-worktree dirty paths: {unexpected}; all dirty={sorted(dirty_paths)}"
    main_root = _main_worktree()
    main_branch = _git("branch", "--show-current", cwd=main_root)
    assert main_branch == "main", f"main worktree branch mismatch at {main_root}: {main_branch!r}"
    main_head = _git("rev-parse", "HEAD", cwd=main_root)
    assert main_head == BASELINE_COMMIT, f"main worktree HEAD mismatch: expected {BASELINE_COMMIT}, got {main_head}"
    main_status = _git("status", "--porcelain=v1", "--untracked-files=all", cwd=main_root)
    assert not main_status, f"main worktree is dirty at {main_root}: {main_status!r}"


def test_action_schema_missing_fails():
    root_package = importlib.import_module("coding_harness")
    assert root_package.__name__ == "coding_harness"

    target_module = "coding_harness.agent.actions"
    expected_missing = {
        "coding_harness.agent",
        target_module,
    }

    try:
        actions = importlib.import_module(target_module)
    except ModuleNotFoundError as exc:
        if exc.name not in expected_missing:
            raise

        pytest.fail(
            "parse_action is not implemented by WP-02: "
            f"required module is missing ({exc.name})",
            pytrace=False,
        )

    parse_action = getattr(actions, "parse_action", None)
    if not callable(parse_action):
        pytest.fail(
            "parse_action is not implemented by WP-02: "
            "coding_harness.agent.actions does not expose callable parse_action",
            pytrace=False,
        )

    pytest.fail(
        "parse_action unexpectedly exists before WP-02 implementation",
        pytrace=False,
    )


@pytest.mark.parametrize("requirement_id", WP01_REQUIREMENTS, ids=WP01_REQUIREMENTS)
def test_spec_requirement(requirement_id: str):
    matches = [row for row in _pv_records() if row.requirement_id == requirement_id]
    assert len(matches) == 1, requirement_id
    row = matches[0]
    expected_planned = ("DOC",) if requirement_id.startswith("GEN-") else (("DOC", "CI") if requirement_id.startswith("PRC-") else ("UT", "IT", "DT", "AT", "DEMO"))
    expected_final = ("DOC", "COLD") if requirement_id.startswith("GEN-") else (("DOC", "CI", "process evidence") if requirement_id.startswith("PRC-") else ("CI", "DEMO", "COLD"))
    assert row.pv_id == f"PV-{requirement_id}"
    assert (row.phase, row.package, row.day) == (0, "WP-01", 1)
    assert row.planned_node == f"tests/unit/agent/test_actions.py::test_spec_requirement[{requirement_id}]"
    assert row.planned_categories == expected_planned
    assert row.supporting_packages == ("WP-28", "WP-29")
    assert row.status == "PLANNED"
    evidence = _range_for(requirement_id)
    assert evidence.final_categories == expected_final
    assert evidence.is_mvp
    process = (ROOT / "SPEC_PROCESS.md").read_text()
    assert "Future supporting evidence slots remain `PENDING`" in process
    assert "Passing a WP-01 planning test does not change any Requirement from `PLANNED`" in process
