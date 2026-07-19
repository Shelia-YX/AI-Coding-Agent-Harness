# Coding Agent Harness MVP 实施计划

> **供 Agent 执行者使用：** 必须使用子技能 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按工作包执行本计划。步骤使用 checkbox（`- [ ]`）语法跟踪。

**目标：** 在 14 个实施日内实现冻结的 `SPEC.md` 1.0 中全部 MVP 需求，且不引入 Stretch goal。

**架构：** 可信宿主 Python 控制平面运行自研的确定性 Agent loop，并由 Policy、审批、预算和 Acceptance 治理。隔离的 Task Workspace、不可变 Baseline、Change Set、固定 Docker profile、SQLite 证据、Execution Lease 和带 journal 的 Apply Transaction，使仓库修改可审计、可恢复。

**技术栈：** Python 3.12、FastAPI、Pydantic v2、sqlite3、pytest、React、TypeScript、Vite、Node.js 20 和 Docker CLI。

## 全局约束

- `SPEC.md` 1.0 是唯一规范输入；`PLAN.md` 不得改变其语义。
- 本项目是本地单用户、单一普通 Git 仓库、Issue 级、dependency-ready 的 MVP。
- 禁止 ORM、高层 Agent Runner、任务网络、依赖安装、运行时 image pull/build、任意命令、自动 commit/push/PR/publish/deploy、消息队列或分布式 worker。
- 容器必须是 non-root、non-privileged、`network none`、移除 capabilities，且不得挂载 Docker socket、HOME、凭据、原仓库或原 `.git`。
- 固定 Docker 测试镜像由可信开发者在 Harness 执行之外准备；必须在 Day 9 前记录 digest。
- 只有固定的可信 Provider Adapter 可以使用控制平面网络。Mock 和 `unit-test` 模式必须离线且不需要 API Key。
- 产品文件必须从失败测试开始渐进创建。Day 1 只创建 WP-02 所需的最小骨架。
- Day 13–14 不新增计划外产品能力；排除 Stretch goal。

---

## Planning Gate（不计入实施日）

1. 生成本计划及其 207 行 PV 表，并执行机械检查。
2. 确认恰好包含 29 个 WP、唯一 ownership、精确的路径/接口/测试/命令/review/commit，不含占位内容，且未修改 SPEC。
3. 获得用户明确批准。只有此后，Day 1 才可初始化 Git。

## 14 个实施日安排

| Day | Phase | 工作包 | 完成条件 |
|---:|---:|---|---|
| 1 | 0 | WP-01 | Git、初始提交、worktree、最小骨架和首个 Red 测试 |
| 2 | 1 | WP-02..04 | 离线 Mock Agent loop |
| 3 | 2 | WP-05..08 | 治理核心 |
| 4 | 3 | WP-09..10 | 路径、Baseline 和 Workspace |
| 5 | 3 | WP-11..13 | ignored input、Synthetic Git、Change Set/conflict |
| 6 | 3 | WP-14 | Apply/rollback/recovery |
| 7 | 4 | WP-15..16 | SQLite/audit/events |
| 8 | 4 | WP-17..18 | 锁、Lease 和 startup recovery |
| 9 | 5 | WP-19..20 | profile、Docker 和 doctor |
| 10 | 6 | WP-21..22 | 配置、Provider、export 和 credentials |
| 11 | 7 | WP-23..24 | API/snapshot/SSE |
| 12 | 7 + 支持阶段 10 | WP-25..26 | WebUI 和 distribution/CI 骨架 |
| 13 | 8,9 | WP-27..28 | Node、演示和合规闭合 |
| 14 | 10 | WP-29 | 质量、distribution、CI、文档、cold-start 和审计 |

Day 12 结束时，除正式计划明确安排在 Day 13 的最小 Node.js/TypeScript profile、跨 profile 成功与失败反馈证明，以及三项确定性演示外，其他产品能力主体必须达到 `IMPLEMENTED`。WP-27 是正式计划内最后一个产品功能工作包，不属于临时新增功能。WP-27 完成后冻结产品功能面。WP-28 只进行演示、specification compliance review、合规修复和复验。WP-29 不得新增产品功能，只进行质量、distribution、CI、文档、cold-start 和证据闭合。

## Ownership 与证据规则

- 每条 Requirement 映射到一个 `PV-<Requirement-ID>`，并具有唯一的 Owning Phase、Owning Package 和 Owning Day。
- 只有 owner 可以首次将状态设为 `IN_PROGRESS` 或 `IMPLEMENTED`。只有全部 supporting verification 完成后才能进入 `VERIFIED`。
- 允许共享参数化测试、集成场景或演示证据，但每个 PV 必须记录精确 node/case、category、owner、support 和 status。
- 目录、文件名、仅声明 suite 已通过或仅声明演示已覆盖，均不能作为最终证据。

## API-008 与 API-009

- `API-008` / `PV-API-008`：Phase 7、WP-25、Day 12；Primary Evidence 为 React 最小治理流程测试；Supporting Packages 为 WP-23、WP-24、WP-28、WP-29。在 WP-25 通过前不得进入 `IMPLEMENTED`。
- `API-009` / `PV-API-009`：Phase 7、WP-23、Day 11；Primary Evidence 为 loopback 默认监听与 Task Detail GET API；WP-25 提供页面刷新恢复的 supporting verification。
- `API-001..003` 和 `API-010` 继续由 WP-23 拥有；`API-004..007` 继续由 WP-24 拥有。

## 评审矩阵

安全关键 WP 包括 WP-06、WP-07、WP-09、WP-10、WP-11、WP-13、WP-14、WP-15、WP-17、WP-18、WP-20、WP-21、WP-22 和 WP-28；每个工作包均使用 fresh implementer，独立执行 specification review、修复、quality review、修复、主 Agent 验证，并形成一次 commit。

普通 review group 为 WP-02..04、WP-05+08、WP-12、WP-16、WP-19、WP-23..24、WP-25..26、WP-27 和 WP-29。每个普通 WP 仍使用 fresh implementer；所属 group 统一执行两阶段评审。每天结束时检查受影响回归、PV 证据和未解决 finding。

# 工作包

## WP-01: 仓库、Worktree 与过程基线 — Day 1

**分类：** 普通

**Requirement/PV：** GEN-001..003; PRC-001..010; TST-008

**归属 PV：** PV-GEN-001, PV-GEN-002, PV-GEN-003, PV-PRC-001, PV-PRC-002, PV-PRC-003, PV-PRC-004, PV-PRC-005, PV-PRC-006, PV-PRC-007, PV-PRC-008, PV-PRC-009, PV-PRC-010, PV-TST-008

**精确文件**

- `pyproject.toml`
- `.gitignore`
- `SPEC_PROCESS.md`
- `AGENT_LOG.md`
- `REFLECTION.md`
- `src/coding_harness/__init__.py`
- `tests/unit/agent/test_actions.py`

**接口**

`PVRecord`；已批准的仓库基线；首个失败的 `parse_action` 测试。

**精确 Red case**

- `tests/unit/agent/test_actions.py::test_traceability_has_207_unique_rows`
- `tests/unit/agent/test_actions.py::test_each_requirement_has_one_owner`
- `tests/unit/agent/test_actions.py::test_no_stretch_goal_is_mvp`
- `tests/unit/agent/test_actions.py::test_worktree_baseline_is_clean`
- `tests/unit/agent/test_actions.py::test_action_schema_missing_fails`

每个 owned PV 还使用精确参数化 node `tests/unit/agent/test_actions.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/unit/agent/test_actions.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/unit/agent/test_actions.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，执行指定 ordinary group 的 specification review 与 quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `chore: establish implementation baseline`.

## WP-02: Structured Action 协议 — Day 2

**分类：** 普通

**Requirement/PV：** ACT-001..003; ACT-008..011

**归属 PV：** PV-ACT-001, PV-ACT-002, PV-ACT-003, PV-ACT-008, PV-ACT-009, PV-ACT-010, PV-ACT-011

**精确文件**

- `src/coding_harness/agent/actions.py`
- `src/coding_harness/agent/results.py`
- `tests/unit/agent/test_actions.py`

**接口**

`StructuredAction`、`ControlAction`、`ToolAction`、`ToolResult`、`parse_action(raw)`。

**精确 Red case**

- `tests/unit/agent/test_actions.py::test_known_control_action`
- `tests/unit/agent/test_actions.py::test_known_tool_action`
- `tests/unit/agent/test_actions.py::test_unknown_action_fails_closed`
- `tests/unit/agent/test_actions.py::test_unknown_field_fails_closed`
- `tests/unit/agent/test_actions.py::test_action_identity_and_budget`
- `tests/unit/agent/test_actions.py::test_required_bounded_tool_result`
- `tests/unit/agent/test_actions.py::test_llm_governance_rejected`
- `tests/unit/agent/test_actions.py::test_internal_operation_rejected`

每个 owned PV 还使用精确参数化 node `tests/unit/agent/test_actions.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/unit/agent/test_actions.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/unit/agent/test_actions.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，执行指定 ordinary group 的 specification review 与 quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(agent): define structured action protocol`.

## WP-03: Mock LLM、Context 与反馈 — Day 2

**分类：** 普通

**Requirement/PV：** AGT-007; AGT-009; AGT-012; AGT-015

**归属 PV：** PV-AGT-007, PV-AGT-009, PV-AGT-012, PV-AGT-015

**精确文件**

- `src/coding_harness/agent/adapters.py`
- `src/coding_harness/agent/mock_llm.py`
- `src/coding_harness/agent/context.py`
- `tests/unit/agent/test_mock_feedback.py`

**接口**

`LLMAdapter.complete`、`MockLLM`、`ContextBuilder.build`。

**精确 Red case**

- `tests/unit/agent/test_mock_feedback.py::test_mock_script_deterministic`
- `tests/unit/agent/test_mock_feedback.py::test_failure_enters_next_context`
- `tests/unit/agent/test_mock_feedback.py::test_failure_changes_next_action`
- `tests/unit/agent/test_mock_feedback.py::test_context_order_stable`
- `tests/unit/agent/test_mock_feedback.py::test_context_budget_marks_truncation`
- `tests/unit/agent/test_mock_feedback.py::test_mock_has_no_network`
- `tests/unit/agent/test_mock_feedback.py::test_mock_needs_no_key`

每个 owned PV 还使用精确参数化 node `tests/unit/agent/test_mock_feedback.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/unit/agent/test_mock_feedback.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/unit/agent/test_mock_feedback.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，执行指定 ordinary group 的 specification review 与 quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(agent): add deterministic mock feedback`.

## WP-04: Agent Loop 与确定性停止器 — Day 2

**分类：** 普通

**Requirement/PV：** AGT-001..002; AGT-006; AGT-008; AGT-010..011; TST-001

**归属 PV：** PV-AGT-001, PV-AGT-002, PV-AGT-006, PV-AGT-008, PV-AGT-010, PV-AGT-011, PV-TST-001

**精确文件**

- `src/coding_harness/agent/loop.py`
- `src/coding_harness/agent/stopping.py`
- `src/coding_harness/ports.py`
- `tests/unit/agent/test_loop.py`

**接口**

`AgentLoop.run`、`StopController.evaluate`、LLM/Policy/Tool/Store/Clock port。

**精确 Red case**

- `tests/unit/agent/test_loop.py::test_loop_order`
- `tests/unit/agent/test_loop.py::test_investigation_read_only`
- `tests/unit/agent/test_loop.py::test_attempt_persisted_before_call`
- `tests/unit/agent/test_loop.py::test_complete_stops`
- `tests/unit/agent/test_loop.py::test_waiting_stops`
- `tests/unit/agent/test_loop.py::test_blocked_failed_cancelled_stop`
- `tests/unit/agent/test_loop.py::test_loop_limit`
- `tests/unit/agent/test_loop.py::test_repeated_failure`
- `tests/unit/agent/test_loop.py::test_no_progress`

每个 owned PV 还使用精确参数化 node `tests/unit/agent/test_loop.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/unit/agent/test_loop.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/unit/agent/test_loop.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，执行指定 ordinary group 的 specification review 与 quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(agent): implement deterministic loop`.

## WP-05: Task State 与不可变版本 — Day 3

**分类：** 普通

**Requirement/PV：** AGT-003..005; TXN-001..004; PST-004..006

**归属 PV：** PV-AGT-003, PV-AGT-004, PV-AGT-005, PV-PST-004, PV-PST-005, PV-PST-006, PV-TXN-001, PV-TXN-002, PV-TXN-003, PV-TXN-004

**精确文件**

- `src/coding_harness/domain/enums.py`
- `src/coding_harness/domain/models.py`
- `src/coding_harness/domain/state_machine.py`
- `tests/unit/domain/test_state_machine.py`

**接口**

`TaskState`、`PlanVersion`、`ContractVersion`、`StateMachine.transition`。

**精确 Red case**

- `tests/unit/domain/test_state_machine.py::test_task_state_closed`
- `tests/unit/domain/test_state_machine.py::test_allowed_transition_matrix`
- `tests/unit/domain/test_state_machine.py::test_illegal_transition_fails_closed`
- `tests/unit/domain/test_state_machine.py::test_clarification_pauses`
- `tests/unit/domain/test_state_machine.py::test_continue_acquires_lease`
- `tests/unit/domain/test_state_machine.py::test_terminal_rejects_effect`
- `tests/unit/domain/test_state_machine.py::test_expected_state_conflict`
- `tests/unit/domain/test_state_machine.py::test_idempotency_digest_conflict`
- `tests/unit/domain/test_state_machine.py::test_uncertain_effect_recovers`

每个 owned PV 还使用精确参数化 node `tests/unit/domain/test_state_machine.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/unit/domain/test_state_machine.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/unit/domain/test_state_machine.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，执行指定 ordinary group 的 specification review 与 quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(domain): enforce state and versions`.

## WP-06: Policy Engine 与硬边界 — Day 3

**分类：** 安全关键

**Requirement/PV：** POL-001..007

**归属 PV：** PV-POL-001, PV-POL-002, PV-POL-003, PV-POL-004, PV-POL-005, PV-POL-006, PV-POL-007

**精确文件**

- `src/coding_harness/domain/policy.py`
- `src/coding_harness/domain/errors.py`
- `tests/unit/domain/test_policy.py`

**接口**

`PolicyContext`、`PolicyDecisionRecord`、`PolicyEngine.decide`。

**精确 Red case**

- `tests/unit/domain/test_policy.py::test_decision_set_closed`
- `tests/unit/domain/test_policy.py::test_unknown_context_blocks`
- `tests/unit/domain/test_policy.py::test_deny_not_approvable`
- `tests/unit/domain/test_policy.py::test_remote_git_denied`
- `tests/unit/domain/test_policy.py::test_deploy_denied`
- `tests/unit/domain/test_policy.py::test_task_docker_denied`
- `tests/unit/domain/test_policy.py::test_privileged_denied`
- `tests/unit/domain/test_policy.py::test_repo_config_cannot_grant`
- `tests/unit/domain/test_policy.py::test_network_read_unsupported`

每个 owned PV 还使用精确参数化 node `tests/unit/domain/test_policy.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/unit/domain/test_policy.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/unit/domain/test_policy.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，独立执行 specification review、修复、quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(policy): enforce hard boundaries`.

## WP-07: 审批与预算治理 — Day 3

**分类：** 安全关键

**Requirement/PV：** POL-008..024; ACT-012

**归属 PV：** PV-ACT-012, PV-POL-008, PV-POL-009, PV-POL-010, PV-POL-011, PV-POL-012, PV-POL-013, PV-POL-014, PV-POL-015, PV-POL-016, PV-POL-017, PV-POL-018, PV-POL-019, PV-POL-020, PV-POL-021, PV-POL-022, PV-POL-023, PV-POL-024

**精确文件**

- `src/coding_harness/domain/approvals.py`
- `src/coding_harness/domain/budgets.py`
- `src/coding_harness/application/governance.py`
- `tests/unit/domain/test_governance.py`

**接口**

`Approval`、`BudgetVersion`、`ApprovalService`、`RunLimits`。

**精确 Red case**

- `tests/unit/domain/test_governance.py::test_plan_binding`
- `tests/unit/domain/test_governance.py::test_authorization_types_distinct`
- `tests/unit/domain/test_governance.py::test_delete_zero_effect`
- `tests/unit/domain/test_governance.py::test_ignored_zero_effect`
- `tests/unit/domain/test_governance.py::test_payload_change_invalidates`
- `tests/unit/domain/test_governance.py::test_consume_once`
- `tests/unit/domain/test_governance.py::test_budget_dimensions`
- `tests/unit/domain/test_governance.py::test_soft_limit_reapproval`
- `tests/unit/domain/test_governance.py::test_hard_limit_fixed`
- `tests/unit/domain/test_governance.py::test_budget_before_effect`

每个 owned PV 还使用精确参数化 node `tests/unit/domain/test_governance.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/unit/domain/test_governance.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/unit/domain/test_governance.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，独立执行 specification review、修复、quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(governance): bind approvals and budgets`.

## WP-08: Acceptance Contract — Day 3

**分类：** 普通

**Requirement/PV：** ACC-001..007

**归属 PV：** PV-ACC-001, PV-ACC-002, PV-ACC-003, PV-ACC-004, PV-ACC-005, PV-ACC-006, PV-ACC-007

**精确文件**

- `src/coding_harness/domain/acceptance.py`
- `tests/unit/domain/test_acceptance.py`

**接口**

`AcceptanceContract`、`AcceptanceCondition`、`AcceptanceEvaluator.evaluate`。

**精确 Red case**

- `tests/unit/domain/test_acceptance.py::test_contract_immutable`
- `tests/unit/domain/test_acceptance.py::test_condition_kinds_closed`
- `tests/unit/domain/test_acceptance.py::test_llm_cannot_pass`
- `tests/unit/domain/test_acceptance.py::test_machine_needs_evidence`
- `tests/unit/domain/test_acceptance.py::test_user_needs_bound_command`
- `tests/unit/domain/test_acceptance.py::test_history_preserved`
- `tests/unit/domain/test_acceptance.py::test_required_incomplete_blocks_apply`

每个 owned PV 还使用精确参数化 node `tests/unit/domain/test_acceptance.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/unit/domain/test_acceptance.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/unit/domain/test_acceptance.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，执行指定 ordinary group 的 specification review 与 quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(acceptance): enforce evidence contracts`.

## WP-09: 路径与支持文件模型 — Day 4

**分类：** 安全关键

**Requirement/PV：** SEC-001; ACT-004..006; WS-012..014

**归属 PV：** PV-ACT-004, PV-ACT-005, PV-ACT-006, PV-SEC-001, PV-WS-013, PV-WS-014

**精确文件**

- `src/coding_harness/workspace/paths.py`
- `src/coding_harness/workspace/file_model.py`
- `tests/unit/workspace/test_paths.py`

**接口**

`RepoPath.parse`、`SupportedEntry`、`inspect_supported_entry`。

**精确 Red case**

- `tests/unit/workspace/test_paths.py::test_relative_path`
- `tests/unit/workspace/test_paths.py::test_absolute_rejected`
- `tests/unit/workspace/test_paths.py::test_parent_rejected`
- `tests/unit/workspace/test_paths.py::test_nul_rejected`
- `tests/unit/workspace/test_paths.py::test_symlink_escape`
- `tests/unit/workspace/test_paths.py::test_bounded_symlink`
- `tests/unit/workspace/test_paths.py::test_executable_bit`
- `tests/unit/workspace/test_paths.py::test_special_file_rejected`
- `tests/unit/workspace/test_paths.py::test_unsupported_repo_state`

每个 owned PV 还使用精确参数化 node `tests/unit/workspace/test_paths.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/unit/workspace/test_paths.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/unit/workspace/test_paths.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，独立执行 specification review、修复、quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(workspace): govern paths and files`.

## WP-10: Baseline Manifest 与 Task Workspace — Day 4

**分类：** 安全关键

**Requirement/PV：** WS-001; WS-006..009

**归属 PV：** PV-WS-001, PV-WS-006, PV-WS-007, PV-WS-008, PV-WS-009

**精确文件**

- `src/coding_harness/workspace/manifest.py`
- `src/coding_harness/workspace/materialize.py`
- `tests/integration/workspace/test_baseline.py`

**接口**

`BaselineManifest`、`TaskWorkspace`、`materialize_workspace`。

**精确 Red case**

- `tests/integration/workspace/test_baseline.py::test_baseline_includes_user_state`
- `tests/integration/workspace/test_baseline.py::test_user_changes_not_agent`
- `tests/integration/workspace/test_baseline.py::test_manifest_immutable`
- `tests/integration/workspace/test_baseline.py::test_workspace_independent`
- `tests/integration/workspace/test_baseline.py::test_workspace_only_writes`
- `tests/integration/workspace/test_baseline.py::test_origin_unchanged`
- `tests/integration/workspace/test_baseline.py::test_git_not_copied`
- `tests/integration/workspace/test_baseline.py::test_index_unchanged`
- `tests/integration/workspace/test_baseline.py::test_head_metadata_only`

每个 owned PV 还使用精确参数化 node `tests/integration/workspace/test_baseline.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/integration/workspace/test_baseline.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/integration/workspace/test_baseline.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，独立执行 specification review、修复、quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(workspace): materialize baseline`.

## WP-11: Ignored Input 治理 — Day 5

**分类：** 安全关键

**Requirement/PV：** WS-010..012; WS-015..016

**归属 PV：** PV-WS-010, PV-WS-011, PV-WS-012, PV-WS-015, PV-WS-016

**精确文件**

- `src/coding_harness/workspace/ignored.py`
- `tests/integration/workspace/test_ignored.py`

**接口**

`SandboxInputManifest`、`materialize_ignored_input`。

**精确 Red case**

- `tests/integration/workspace/test_ignored.py::test_ignored_default_excluded`
- `tests/integration/workspace/test_ignored.py::test_unapproved_not_materialized`
- `tests/integration/workspace/test_ignored.py::test_approval_freezes_manifest`
- `tests/integration/workspace/test_ignored.py::test_baseline_unchanged`
- `tests/integration/workspace/test_ignored.py::test_readonly_rejects_write`
- `tests/integration/workspace/test_ignored.py::test_ephemeral_copy_only`
- `tests/integration/workspace/test_ignored.py::test_source_not_changeset`
- `tests/integration/workspace/test_ignored.py::test_derived_not_writeback`
- `tests/integration/workspace/test_ignored.py::test_never_exportable`

每个 owned PV 还使用精确参数化 node `tests/integration/workspace/test_ignored.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/integration/workspace/test_ignored.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/integration/workspace/test_ignored.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，独立执行 specification review、修复、quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(workspace): govern ignored inputs`.

## WP-12: Synthetic Git 边界 — Day 5

**分类：** 普通

**Requirement/PV：** WS-002..005

**归属 PV：** PV-WS-002, PV-WS-003, PV-WS-004, PV-WS-005

**精确文件**

- `src/coding_harness/workspace/synthetic_git.py`
- `tests/unit/workspace/test_synthetic_git.py`

**接口**

`SyntheticGit.run`；闭合的 `GitOperation`。

**精确 Red case**

- `tests/unit/workspace/test_synthetic_git.py::test_sanitized_environment`
- `tests/unit/workspace/test_synthetic_git.py::test_exact_allowlist`
- `tests/unit/workspace/test_synthetic_git.py::test_commit_branch_remote_clean_rejected`
- `tests/unit/workspace/test_synthetic_git.py::test_config_rejected`
- `tests/unit/workspace/test_synthetic_git.py::test_explicit_files`
- `tests/unit/workspace/test_synthetic_git.py::test_required_path_rejections`
- `tests/unit/workspace/test_synthetic_git.py::test_glob_magic_rejected`
- `tests/unit/workspace/test_synthetic_git.py::test_global_options_rejected`
- `tests/unit/workspace/test_synthetic_git.py::test_not_changeset_authority`

每个 owned PV 还使用精确参数化 node `tests/unit/workspace/test_synthetic_git.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/unit/workspace/test_synthetic_git.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/unit/workspace/test_synthetic_git.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，执行指定 ordinary group 的 specification review 与 quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(workspace): constrain synthetic git`.

## WP-13: Change Set 与冲突检测 — Day 5

**分类：** 安全关键

**Requirement/PV：** TXN-005..008; TXN-017..018

**归属 PV：** PV-TXN-005, PV-TXN-006, PV-TXN-007, PV-TXN-008, PV-TXN-017, PV-TXN-018

**精确文件**

- `src/coding_harness/workspace/changeset.py`
- `src/coding_harness/transaction/conflicts.py`
- `tests/integration/transaction/test_changeset.py`

**接口**

`ChangeSet`、`ConflictReport`、`compute_changeset`、`detect_conflicts`。

**精确 Red case**

- `tests/integration/transaction/test_changeset.py::test_create_modify_delete`
- `tests/integration/transaction/test_changeset.py::test_mode_symlink`
- `tests/integration/transaction/test_changeset.py::test_digest_changes`
- `tests/integration/transaction/test_changeset.py::test_confirmation_binds_digest`
- `tests/integration/transaction/test_changeset.py::test_unrelated_change`
- `tests/integration/transaction/test_changeset.py::test_target_conflict`
- `tests/integration/transaction/test_changeset.py::test_confirmation_invalidated`
- `tests/integration/transaction/test_changeset.py::test_no_auto_merge`
- `tests/integration/transaction/test_changeset.py::test_acceptance_blocks`

每个 owned PV 还使用精确参数化 node `tests/integration/transaction/test_changeset.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/integration/transaction/test_changeset.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/integration/transaction/test_changeset.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，独立执行 specification review、修复、quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(transaction): compute changes and conflicts`.

## WP-14: Apply Transaction、Rollback 与 Recovery — Day 6

**分类：** 安全关键

**Requirement/PV：** TXN-009..016; TXN-019

**归属 PV：** PV-TXN-009, PV-TXN-010, PV-TXN-011, PV-TXN-012, PV-TXN-013, PV-TXN-014, PV-TXN-015, PV-TXN-016, PV-TXN-019

**精确文件**

- `src/coding_harness/transaction/models.py`
- `src/coding_harness/transaction/journal.py`
- `src/coding_harness/transaction/apply.py`
- `src/coding_harness/transaction/recovery.py`
- `tests/integration/transaction/test_apply.py`

**接口**

`ApplyPlan`、`ApplyJournal`、`ApplyCoordinator.apply`、`RecoveryCoordinator.recover`。

**精确 Red case**

- `tests/integration/transaction/test_apply.py::test_plan_immutable`
- `tests/integration/transaction/test_apply.py::test_backup_before_write`
- `tests/integration/transaction/test_apply.py::test_backup_digest`
- `tests/integration/transaction/test_apply.py::test_phase_before_effect`
- `tests/integration/transaction/test_apply.py::test_pending_completed`
- `tests/integration/transaction/test_apply.py::test_success_rechecks`
- `tests/integration/transaction/test_apply.py::test_unstaged_write`
- `tests/integration/transaction/test_apply.py::test_second_write_failure`
- `tests/integration/transaction/test_apply.py::test_reverse_rollback`
- `tests/integration/transaction/test_apply.py::test_unprovable_requires_recovery`

每个 owned PV 还使用精确参数化 node `tests/integration/transaction/test_apply.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/integration/transaction/test_apply.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/integration/transaction/test_apply.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，独立执行 specification review、修复、quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(transaction): add durable apply rollback`.

## WP-15: HarnessStore、Migration 与原子 Audit — Day 7

**分类：** 安全关键

**Requirement/PV：** PST-001..003; PST-007..012

**归属 PV：** PV-PST-001, PV-PST-002, PV-PST-003, PV-PST-007, PV-PST-008, PV-PST-009, PV-PST-010, PV-PST-011, PV-PST-012

**精确文件**

- `src/coding_harness/persistence/ports.py`
- `src/coding_harness/persistence/sqlite_store.py`
- `src/coding_harness/persistence/migrations.py`
- `src/coding_harness/persistence/sql/001_initial.sql`
- `tests/integration/persistence/test_store.py`

**接口**

`HarnessStore`、`MigrationRunner`；原子的业务意图方法。

**精确 Red case**

- `tests/integration/persistence/test_store.py::test_no_execute_sql`
- `tests/integration/persistence/test_store.py::test_domain_models_only`
- `tests/integration/persistence/test_store.py::test_sqlite_not_apply_truth`
- `tests/integration/persistence/test_store.py::test_ordered_migrations`
- `tests/integration/persistence/test_store.py::test_checksum_drift`
- `tests/integration/persistence/test_store.py::test_migration_failure`
- `tests/integration/persistence/test_store.py::test_no_downgrade`
- `tests/integration/persistence/test_store.py::test_state_audit_atomic`
- `tests/integration/persistence/test_store.py::test_governance_audit_atomic`
- `tests/integration/persistence/test_store.py::test_audit_append_only`

每个 owned PV 还使用精确参数化 node `tests/integration/persistence/test_store.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/integration/persistence/test_store.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/integration/persistence/test_store.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，独立执行 specification review、修复、quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(persistence): add atomic sqlite store`.

## WP-16: 持久化 Event 与证据存储 — Day 7

**分类：** 普通

**Requirement/PV：** PST-013..014; PST-023..024

**归属 PV：** PV-PST-013, PV-PST-014

**精确文件**

- `src/coding_harness/domain/events.py`
- `src/coding_harness/persistence/evidence.py`
- `tests/integration/persistence/test_events.py`

**接口**

`DomainEvent`、`EvidenceRef`、`EventReader.after`。

**精确 Red case**

- `tests/integration/persistence/test_events.py::test_event_id_monotonic`
- `tests/integration/persistence/test_events.py::test_event_state_atomic`
- `tests/integration/persistence/test_events.py::test_three_evidence_kinds`
- `tests/integration/persistence/test_events.py::test_artifact_reference`
- `tests/integration/persistence/test_events.py::test_artifact_digest_size`
- `tests/integration/persistence/test_events.py::test_publisher_reads_store`
- `tests/integration/persistence/test_events.py::test_memory_not_truth`

每个 owned PV 还使用精确参数化 node `tests/integration/persistence/test_events.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/integration/persistence/test_events.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/integration/persistence/test_events.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，执行指定 ordinary group 的 specification review 与 quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(persistence): persist events and evidence`.

## WP-17: 进程锁与 Execution Lease — Day 8

**分类：** 安全关键

**Requirement/PV：** PST-015..017; PST-019..020

**归属 PV：** PV-PST-015, PV-PST-016, PV-PST-017, PV-PST-019, PV-PST-020

**精确文件**

- `src/coding_harness/persistence/process_lock.py`
- `src/coding_harness/persistence/lease.py`
- `tests/integration/persistence/test_lease.py`

**接口**

`ProcessLock`、`ExecutionLeaseService`。

**精确 Red case**

- `tests/integration/persistence/test_lease.py::test_single_serve`
- `tests/integration/persistence/test_lease.py::test_lock_lease_separate`
- `tests/integration/persistence/test_lease.py::test_single_execution_lease`
- `tests/integration/persistence/test_lease.py::test_lease_binding`
- `tests/integration/persistence/test_lease.py::test_heartbeat`
- `tests/integration/persistence/test_lease.py::test_stale_audit_only`
- `tests/integration/persistence/test_lease.py::test_safe_release`
- `tests/integration/persistence/test_lease.py::test_recovery_priority`
- `tests/integration/persistence/test_lease.py::test_recovery_blocks_execution`

每个 owned PV 还使用精确参数化 node `tests/integration/persistence/test_lease.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/integration/persistence/test_lease.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/integration/persistence/test_lease.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，独立执行 specification review、修复、quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(recovery): coordinate locks and lease`.

## WP-18: 启动恢复与持久化失败 — Day 8

**分类：** 安全关键

**Requirement/PV：** PST-018; PST-025..028; TST-002

**归属 PV：** PV-PST-018, PV-PST-025, PV-PST-026, PV-PST-027, PV-PST-028, PV-TST-002

**精确文件**

- `src/coding_harness/application/startup_recovery.py`
- `tests/integration/recovery/test_startup.py`

**接口**

`StartupRecovery.scan`、`RecoveryFinding`；确定性的恢复推进决策。

**精确 Red case**

- `tests/integration/recovery/test_startup.py::test_scan_lease`
- `tests/integration/recovery/test_startup.py::test_scan_container`
- `tests/integration/recovery/test_startup.py::test_scan_apply`
- `tests/integration/recovery/test_startup.py::test_check_journal`
- `tests/integration/recovery/test_startup.py::test_uncertain_effect_recovers`
- `tests/integration/recovery/test_startup.py::test_clarification_paused`
- `tests/integration/recovery/test_startup.py::test_approval_cleanup_release`
- `tests/integration/recovery/test_startup.py::test_revision_history`
- `tests/integration/recovery/test_startup.py::test_old_approval_invalidated`
- `tests/integration/recovery/test_startup.py::test_unapproved_revision_no_write`

每个 owned PV 还使用精确参数化 node `tests/integration/recovery/test_startup.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/integration/recovery/test_startup.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/integration/recovery/test_startup.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，独立执行 specification review、修复、quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(recovery): audit startup state`.

## WP-19: 固定 Profile、Preflight 与 Doctor — Day 9

**分类：** 普通

**Requirement/PV：** SBX-002..005; SBX-013; ACC-008..009; TST-003

**归属 PV：** PV-ACC-008, PV-ACC-009, PV-SBX-002, PV-SBX-003, PV-SBX-004, PV-SBX-005, PV-SBX-013, PV-TST-003

**精确文件**

- `src/coding_harness/sandbox/profiles.py`
- `src/coding_harness/sandbox/doctor.py`
- `tests/unit/sandbox/test_profiles.py`
- `tests/docker/test_doctor.py`

**接口**

`ProfileRegistry`、`PreflightResult`、`DoctorReport`。

**精确 Red case**

- `tests/docker/test_doctor.py::test_python_profile`
- `tests/docker/test_doctor.py::test_trusted_digest`
- `tests/docker/test_doctor.py::test_llm_cannot_select`
- `tests/docker/test_doctor.py::test_no_pull_build`
- `tests/docker/test_doctor.py::test_missing_dependency`
- `tests/docker/test_doctor.py::test_stderr_not_inference`
- `tests/docker/test_doctor.py::test_validation_evidence`
- `tests/docker/test_doctor.py::test_doctor_runtime`
- `tests/docker/test_doctor.py::test_doctor_residual`

每个 owned PV 还使用精确参数化 node `tests/docker/test_doctor.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/docker/test_doctor.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/docker/test_doctor.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，执行指定 ordinary group 的 specification review 与 quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(sandbox): add profiles and doctor`.

## WP-20: Docker Sandbox 与生命周期 — Day 9

**分类：** 安全关键

**Requirement/PV：** SEC-002..006; SEC-009; ACT-007; SBX-001; SBX-006..012

**归属 PV：** PV-ACT-007, PV-SBX-001, PV-SBX-006, PV-SBX-007, PV-SBX-008, PV-SBX-009, PV-SBX-010, PV-SBX-011, PV-SBX-012, PV-SEC-002, PV-SEC-003, PV-SEC-004, PV-SEC-005, PV-SEC-006, PV-SEC-009

**精确文件**

- `src/coding_harness/sandbox/docker_cli.py`
- `src/coding_harness/sandbox/lifecycle.py`
- `tests/docker/test_executor.py`

**接口**

`DockerCLI.run`、`ContainerLifecycle.execute`。

**精确 Red case**

- `tests/docker/test_executor.py::test_absolute_cli_structured_argv`
- `tests/docker/test_executor.py::test_environment_allowlist`
- `tests/docker/test_executor.py::test_local_unix_endpoint`
- `tests/docker/test_executor.py::test_network_none_security`
- `tests/docker/test_executor.py::test_resource_limits`
- `tests/docker/test_executor.py::test_forbidden_mounts`
- `tests/docker/test_executor.py::test_inspect_before_start`
- `tests/docker/test_executor.py::test_timeout_cancel_cleanup`
- `tests/docker/test_executor.py::test_cleanup_failure_recovery`
- `tests/docker/test_executor.py::test_no_host_fallback`

每个 owned PV 还使用精确参数化 node `tests/docker/test_executor.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/docker/test_executor.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/docker/test_executor.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，独立执行 specification review、修复、quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(sandbox): enforce docker isolation`.

## WP-21: 可信配置与 Provider 边界 — Day 10

**分类：** 安全关键

**Requirement/PV：** GEN-008..010; SEC-014..015; AGT-013..014

**归属 PV：** PV-AGT-013, PV-AGT-014, PV-GEN-008, PV-GEN-009, PV-GEN-010, PV-SEC-014, PV-SEC-015

**精确文件**

- `src/coding_harness/config.py`
- `src/coding_harness/agent/provider.py`
- `tests/unit/test_config.py`
- `tests/unit/agent/test_provider.py`

**接口**

`HarnessConfig`、`RunConfigSnapshot`、`ProviderAdapter.complete`。

**精确 Red case**

- `tests/unit/agent/test_provider.py::test_unknown_config_rejected`
- `tests/unit/agent/test_provider.py::test_trusted_precedence`
- `tests/unit/agent/test_provider.py::test_untrusted_no_override`
- `tests/unit/agent/test_provider.py::test_snapshot_frozen`
- `tests/unit/agent/test_provider.py::test_provider_endpoint_fixed`
- `tests/unit/agent/test_provider.py::test_redirect_rejected`
- `tests/unit/agent/test_provider.py::test_limits_enforced`
- `tests/unit/agent/test_provider.py::test_unavailable_distinct`
- `tests/unit/agent/test_provider.py::test_config_error_distinct`
- `tests/unit/agent/test_provider.py::test_no_fallback`

每个 owned PV 还使用精确参数化 node `tests/unit/agent/test_provider.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/unit/agent/test_provider.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/unit/agent/test_provider.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，独立执行 specification review、修复、quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(provider): freeze trusted configuration`.

## WP-22: Context Export 与凭据安全 — Day 10

**分类：** 安全关键

**Requirement/PV：** SEC-007..008; SEC-010..013; CRD-001..013; TST-007

**归属 PV：** PV-CRD-001, PV-CRD-002, PV-CRD-003, PV-CRD-004, PV-CRD-005, PV-CRD-006, PV-CRD-007, PV-CRD-008, PV-CRD-009, PV-CRD-010, PV-CRD-011, PV-CRD-012, PV-CRD-013, PV-SEC-007, PV-SEC-008, PV-SEC-010, PV-SEC-011, PV-SEC-012, PV-SEC-013, PV-TST-007

**精确文件**

- `src/coding_harness/agent/export.py`
- `src/coding_harness/credentials/crypto.py`
- `src/coding_harness/credentials/store.py`
- `src/coding_harness/credentials/runtime.py`
- `src/coding_harness/cli/credentials.py`
- `tests/unit/credentials/test_credentials.py`

**接口**

`ExportDecision`、`ExportAudit`、`CredentialStore`、`ProviderRuntime`。

**精确 Red case**

- `tests/unit/credentials/test_credentials.py::test_readable_exportable_distinct`
- `tests/unit/credentials/test_credentials.py::test_ignored_sensitive_no_export`
- `tests/unit/credentials/test_credentials.py::test_export_audit`
- `tests/unit/credentials/test_credentials.py::test_kdf_aead_randomness`
- `tests/unit/credentials/test_credentials.py::test_associated_data`
- `tests/unit/credentials/test_credentials.py::test_bad_input_fail_closed`
- `tests/unit/credentials/test_credentials.py::test_tty_lock_cli`
- `tests/unit/credentials/test_credentials.py::test_memory_only_unlock`
- `tests/unit/credentials/test_credentials.py::test_env_not_formal_storage`
- `tests/unit/credentials/test_credentials.py::test_no_secret_surfaces`

每个 owned PV 还使用精确参数化 node `tests/unit/credentials/test_credentials.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/unit/credentials/test_credentials.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/unit/credentials/test_credentials.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，独立执行 specification review、修复、quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(credentials): secure export and unlock`.

## WP-23: Application Service、Governance 与 Snapshot API — Day 11

**分类：** 普通

**Requirement/PV：** GEN-007; API-001..003; API-009..010

**归属 PV：** PV-API-001, PV-API-002, PV-API-003, PV-API-009, PV-API-010, PV-GEN-007

**精确文件**

- `src/coding_harness/application/tasks.py`
- `src/coding_harness/application/commands.py`
- `src/coding_harness/api/schemas.py`
- `src/coding_harness/api/routes.py`
- `tests/api/test_governance.py`

**接口**

`TaskService`、`GovernanceService`、Task Detail GET API、独立 POST command。

**精确 Red case**

- `tests/api/test_governance.py::test_route_uses_service`
- `tests/api/test_governance.py::test_command_set_closed`
- `tests/api/test_governance.py::test_independent_posts`
- `tests/api/test_governance.py::test_expected_bindings`
- `tests/api/test_governance.py::test_idempotent_retry`
- `tests/api/test_governance.py::test_only_continue_runs`
- `tests/api/test_governance.py::test_task_detail_snapshot`
- `tests/api/test_governance.py::test_loopback_default`

每个 owned PV 还使用精确参数化 node `tests/api/test_governance.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/api/test_governance.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/api/test_governance.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，执行指定 ordinary group 的 specification review 与 quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(api): expose governed task services`.

## WP-24: SSE 投递与错误证据 — Day 11

**分类：** 普通

**Requirement/PV：** PST-021..024; API-004..007; TST-006

**归属 PV：** PV-API-004, PV-API-005, PV-API-006, PV-API-007, PV-PST-021, PV-PST-022, PV-PST-023, PV-PST-024, PV-TST-006

**精确文件**

- `src/coding_harness/api/sse.py`
- `src/coding_harness/application/errors.py`
- `tests/api/test_sse.py`

**接口**

`SSEPublisher.stream_after`、`ErrorClassifier`。

**精确 Red case**

- `tests/api/test_sse.py::test_deterministic_error`
- `tests/api/test_sse.py::test_error_semantics`
- `tests/api/test_sse.py::test_last_event_replay`
- `tests/api/test_sse.py::test_at_least_once`
- `tests/api/test_sse.py::test_deduplicate`
- `tests/api/test_sse.py::test_no_subscriber_state`
- `tests/api/test_sse.py::test_failed_submit_no_success`
- `tests/api/test_sse.py::test_log_gap_marker`

每个 owned PV 还使用精确参数化 node `tests/api/test_sse.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/api/test_sse.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/api/test_sse.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，执行指定 ordinary group 的 specification review 与 quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(api): stream persistent events`.

## WP-25: 最小 React 治理 WebUI — Day 12

**分类：** 普通

**Requirement/PV：** API-008

**归属 PV：** PV-API-008

**精确文件**

- `web/package.json`
- `web/vite.config.ts`
- `web/src/main.tsx`
- `web/src/api/client.ts`
- `web/src/App.tsx`
- `web/src/components/GovernancePanel.tsx`
- `web/src/components/TaskView.tsx`
- `web/src/App.test.tsx`

**接口**

Governance UI 消费 WP-23 的 snapshot/command 和 WP-24 的 SSE。

**精确 Red case**

- `web/src/App.test.tsx::test_issue_submission`
- `web/src/App.test.tsx::test_task_state`
- `web/src/App.test.tsx::test_approval_commands`
- `web/src/App.test.tsx::test_acceptance_confirmation`
- `web/src/App.test.tsx::test_diff_apply`
- `web/src/App.test.tsx::test_conflict_recovery`
- `web/src/App.test.tsx::test_refresh_from_task_detail`
- `web/src/App.test.tsx::test_sse_dedup_reconnect`

每个 owned PV 还使用精确参数化 node `web/src/App.test.tsx::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest web/src/App.test.tsx -q` （React：`npm test -- --run`；Docker：`pytest -m docker web/src/App.test.tsx -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，执行指定 ordinary group 的 specification review 与 quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(web): add minimal governance flow`.

## WP-26: Packaging、静态资源、CLI 与 CI 骨架 — Day 12

**分类：** 普通

**Requirement/PV：** Supporting DST-001..003; PRC-005

**精确文件**

- `pyproject.toml`
- `src/coding_harness/cli/main.py`
- `src/coding_harness/api/static.py`
- `web/vite.config.ts`
- `.gitlab-ci.yml`
- `tests/unit/distribution/test_skeleton.py`

**接口**

固定 frontend/package 路径；`harness` CLI；精确的 `unit-test` job 骨架。

**精确 Red case**

- `tests/unit/distribution/test_skeleton.py::test_package_config`
- `tests/unit/distribution/test_skeleton.py::test_vite_output`
- `tests/unit/distribution/test_skeleton.py::test_static_target`
- `tests/unit/distribution/test_skeleton.py::test_static_build_input`
- `tests/unit/distribution/test_skeleton.py::test_cli_entry`
- `tests/unit/distribution/test_skeleton.py::test_serve_static`
- `tests/unit/distribution/test_skeleton.py::test_unit_job_exact`
- `tests/unit/distribution/test_skeleton.py::test_unit_job_offline`

每个 owned PV 还使用精确参数化 node `tests/unit/distribution/test_skeleton.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/unit/distribution/test_skeleton.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/unit/distribution/test_skeleton.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，执行指定 ordinary group 的 specification review 与 quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `build: establish distribution skeleton`.

## WP-27: 最小 Node Profile 与跨 Profile 路径 — Day 13

**分类：** 普通

**Requirement/PV：** GEN-004..006; TST-004

**归属 PV：** PV-GEN-004, PV-GEN-005, PV-GEN-006, PV-TST-004

**精确文件**

- `src/coding_harness/sandbox/profiles.py`
- `tests/fixtures/node_project/package.json`
- `tests/fixtures/node_project/package-lock.json`
- `tests/docker/test_cross_profile.py`

**接口**

单根 Node.js 20/npm profile；跨 profile 证明。

**精确 Red case**

- `tests/docker/test_cross_profile.py::test_node_detected`
- `tests/docker/test_cross_profile.py::test_workspace_rejected`
- `tests/docker/test_cross_profile.py::test_other_managers_rejected`
- `tests/docker/test_cross_profile.py::test_no_install`
- `tests/docker/test_cross_profile.py::test_network_none`
- `tests/docker/test_cross_profile.py::test_python_success`
- `tests/docker/test_cross_profile.py::test_node_success`
- `tests/docker/test_cross_profile.py::test_node_failure_changes_action`

每个 owned PV 还使用精确参数化 node `tests/docker/test_cross_profile.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/docker/test_cross_profile.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/docker/test_cross_profile.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，执行指定 ordinary group 的 specification review 与 quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `feat(profile): prove node cross-profile flow`.

## WP-28: 三项演示与合规闭合 — Day 13

**分类：** 安全关键

**Requirement/PV：** TST-005; supporting all PVs

**归属 PV：** PV-TST-005

**精确文件**

- `tests/demos/test_governance_demo.py`
- `tests/demos/test_feedback_demo.py`
- `tests/demos/test_transaction_demo.py`
- `tests/demos/test_conflict_demo.py`
- `AGENT_LOG.md`

**接口**

集成的确定性演示和合规 finding。

**精确 Red case**

- `AGENT_LOG.md::test_denied_action_zero_calls`
- `AGENT_LOG.md::test_failure_changes_action`
- `AGENT_LOG.md::test_multifile_failure_recovers`
- `AGENT_LOG.md::test_dirty_target_conflicts`

每个 owned PV 还使用精确参数化 node `AGENT_LOG.md::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest AGENT_LOG.md -q` （React：`npm test -- --run`；Docker：`pytest -m docker AGENT_LOG.md -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，独立执行 specification review、修复、quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `test: close deterministic demonstrations`.

## WP-29: 质量、Distribution、CI、文档与 Cold Start — Day 14

**分类：** 普通收敛

**Requirement/PV：** DST-001..005; supporting PRC-001..010 and all PVs

**归属 PV：** PV-DST-001, PV-DST-002, PV-DST-003, PV-DST-004, PV-DST-005

**精确文件**

- `pyproject.toml`
- `.gitlab-ci.yml`
- `README.md`
- `SPEC_PROCESS.md`
- `AGENT_LOG.md`
- `REFLECTION.md`
- `tests/cold/test_installed_smoke.py`

**接口**

wheel/sdist、内嵌 UI、离线 CI、文档、cold-start 和最终审计。

**精确 Red case**

- `tests/cold/test_installed_smoke.py::test_wheel_builds`
- `tests/cold/test_installed_smoke.py::test_wheel_has_assets`
- `tests/cold/test_installed_smoke.py::test_installed_cli`
- `tests/cold/test_installed_smoke.py::test_loopback_url`
- `tests/cold/test_installed_smoke.py::test_unit_job_exact`
- `tests/cold/test_installed_smoke.py::test_unit_job_offline`
- `tests/cold/test_installed_smoke.py::test_cold_doctor_webui`
- `tests/cold/test_installed_smoke.py::test_cold_mock_task`
- `tests/cold/test_installed_smoke.py::test_all_pvs_precise`

每个 owned PV 还使用精确参数化 node `tests/cold/test_installed_smoke.py::test_spec_requirement[<Requirement-ID>]`；该 case 必须断言对应 Requirement 的可观察结果。

- [ ] **Red：** 在实现前添加上面列出的全部 case。
- [ ] **确认 Red：** 运行 `pytest tests/cold/test_installed_smoke.py -q` （React：`npm test -- --run`；Docker：`pytest -m docker tests/cold/test_installed_smoke.py -q`）。预期：因接口或行为尚不存在而 FAIL，不得是无关的 collection failure。
- [ ] **最小实现：** 只实现已命名接口和可观察 case，使用严格 model、闭合 enum、显式 result 和窄依赖。
- [ ] **Green：** 重复 Red 命令。预期：列出的所有 case 均 PASS；离线测试不访问网络或 API Key。
- [ ] **回归：** 运行受影响的既有 unit/integration node；Docker 和 React 工作包还需运行各自精确的原生测试集。
- [ ] **评审 Gate：** 使用 fresh implementer，执行指定 ordinary group 的 specification review 与 quality review、修复和主 Agent 验证。
- [ ] **Commit：** 只 stage 这些路径；建议消息： `release: close mvp evidence`.

# Requirement 与 Planned Verification 追踪表（207 行）

| Requirement | PV | Phase | Package | Day | Supporting | Category | 精确计划 node/case | Status |
|---|---|---:|---|---:|---|---|---|---|
| ACC-001 | PV-ACC-001 | 2 | WP-08 | 3 | WP-28, WP-29 | UT/IT | `tests/unit/domain/test_acceptance.py::test_spec_requirement[ACC-001]` | PLANNED |
| ACC-002 | PV-ACC-002 | 2 | WP-08 | 3 | WP-28, WP-29 | UT/IT | `tests/unit/domain/test_acceptance.py::test_spec_requirement[ACC-002]` | PLANNED |
| ACC-003 | PV-ACC-003 | 2 | WP-08 | 3 | WP-28, WP-29 | UT/IT | `tests/unit/domain/test_acceptance.py::test_spec_requirement[ACC-003]` | PLANNED |
| ACC-004 | PV-ACC-004 | 2 | WP-08 | 3 | WP-28, WP-29 | UT/IT | `tests/unit/domain/test_acceptance.py::test_spec_requirement[ACC-004]` | PLANNED |
| ACC-005 | PV-ACC-005 | 2 | WP-08 | 3 | WP-28, WP-29 | UT/IT | `tests/unit/domain/test_acceptance.py::test_spec_requirement[ACC-005]` | PLANNED |
| ACC-006 | PV-ACC-006 | 2 | WP-08 | 3 | WP-28, WP-29 | UT/IT | `tests/unit/domain/test_acceptance.py::test_spec_requirement[ACC-006]` | PLANNED |
| ACC-007 | PV-ACC-007 | 2 | WP-08 | 3 | WP-28, WP-29 | UT/IT | `tests/unit/domain/test_acceptance.py::test_spec_requirement[ACC-007]` | PLANNED |
| ACC-008 | PV-ACC-008 | 5 | WP-19 | 9 | WP-28, WP-29 | UT/IT | `tests/docker/test_doctor.py::test_spec_requirement[ACC-008]` | PLANNED |
| ACC-009 | PV-ACC-009 | 5 | WP-19 | 9 | WP-28, WP-29 | UT/IT | `tests/docker/test_doctor.py::test_spec_requirement[ACC-009]` | PLANNED |
| ACT-001 | PV-ACT-001 | 1 | WP-02 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_actions.py::test_spec_requirement[ACT-001]` | PLANNED |
| ACT-002 | PV-ACT-002 | 1 | WP-02 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_actions.py::test_spec_requirement[ACT-002]` | PLANNED |
| ACT-003 | PV-ACT-003 | 1 | WP-02 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_actions.py::test_spec_requirement[ACT-003]` | PLANNED |
| ACT-004 | PV-ACT-004 | 3 | WP-09 | 4 | WP-28, WP-29 | UT | `tests/unit/workspace/test_paths.py::test_spec_requirement[ACT-004]` | PLANNED |
| ACT-005 | PV-ACT-005 | 3 | WP-09 | 4 | WP-28, WP-29 | UT | `tests/unit/workspace/test_paths.py::test_spec_requirement[ACT-005]` | PLANNED |
| ACT-006 | PV-ACT-006 | 3 | WP-09 | 4 | WP-28, WP-29 | UT | `tests/unit/workspace/test_paths.py::test_spec_requirement[ACT-006]` | PLANNED |
| ACT-007 | PV-ACT-007 | 5 | WP-20 | 9 | WP-28, WP-29 | UT | `tests/docker/test_executor.py::test_spec_requirement[ACT-007]` | PLANNED |
| ACT-008 | PV-ACT-008 | 1 | WP-02 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_actions.py::test_spec_requirement[ACT-008]` | PLANNED |
| ACT-009 | PV-ACT-009 | 1 | WP-02 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_actions.py::test_spec_requirement[ACT-009]` | PLANNED |
| ACT-010 | PV-ACT-010 | 1 | WP-02 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_actions.py::test_spec_requirement[ACT-010]` | PLANNED |
| ACT-011 | PV-ACT-011 | 1 | WP-02 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_actions.py::test_spec_requirement[ACT-011]` | PLANNED |
| ACT-012 | PV-ACT-012 | 2 | WP-07 | 3 | WP-28, WP-29 | UT | `tests/unit/domain/test_governance.py::test_spec_requirement[ACT-012]` | PLANNED |
| AGT-001 | PV-AGT-001 | 1 | WP-04 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_loop.py::test_spec_requirement[AGT-001]` | PLANNED |
| AGT-002 | PV-AGT-002 | 1 | WP-04 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_loop.py::test_spec_requirement[AGT-002]` | PLANNED |
| AGT-003 | PV-AGT-003 | 2 | WP-05 | 3 | WP-28, WP-29 | UT | `tests/unit/domain/test_state_machine.py::test_spec_requirement[AGT-003]` | PLANNED |
| AGT-004 | PV-AGT-004 | 2 | WP-05 | 3 | WP-28, WP-29 | UT | `tests/unit/domain/test_state_machine.py::test_spec_requirement[AGT-004]` | PLANNED |
| AGT-005 | PV-AGT-005 | 2 | WP-05 | 3 | WP-28, WP-29 | UT | `tests/unit/domain/test_state_machine.py::test_spec_requirement[AGT-005]` | PLANNED |
| AGT-006 | PV-AGT-006 | 1 | WP-04 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_loop.py::test_spec_requirement[AGT-006]` | PLANNED |
| AGT-007 | PV-AGT-007 | 1 | WP-03 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_mock_feedback.py::test_spec_requirement[AGT-007]` | PLANNED |
| AGT-008 | PV-AGT-008 | 1 | WP-04 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_loop.py::test_spec_requirement[AGT-008]` | PLANNED |
| AGT-009 | PV-AGT-009 | 1 | WP-03 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_mock_feedback.py::test_spec_requirement[AGT-009]` | PLANNED |
| AGT-010 | PV-AGT-010 | 1 | WP-04 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_loop.py::test_spec_requirement[AGT-010]` | PLANNED |
| AGT-011 | PV-AGT-011 | 1 | WP-04 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_loop.py::test_spec_requirement[AGT-011]` | PLANNED |
| AGT-012 | PV-AGT-012 | 1 | WP-03 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_mock_feedback.py::test_spec_requirement[AGT-012]` | PLANNED |
| AGT-013 | PV-AGT-013 | 6 | WP-21 | 10 | WP-28, WP-29 | UT | `tests/unit/agent/test_provider.py::test_spec_requirement[AGT-013]` | PLANNED |
| AGT-014 | PV-AGT-014 | 6 | WP-21 | 10 | WP-28, WP-29 | UT | `tests/unit/agent/test_provider.py::test_spec_requirement[AGT-014]` | PLANNED |
| AGT-015 | PV-AGT-015 | 1 | WP-03 | 2 | WP-28, WP-29 | UT | `tests/unit/agent/test_mock_feedback.py::test_spec_requirement[AGT-015]` | PLANNED |
| API-001 | PV-API-001 | 7 | WP-23 | 11 | WP-28, WP-29 | AT | `tests/api/test_governance.py::test_spec_requirement[API-001]` | PLANNED |
| API-002 | PV-API-002 | 7 | WP-23 | 11 | WP-28, WP-29 | AT | `tests/api/test_governance.py::test_spec_requirement[API-002]` | PLANNED |
| API-003 | PV-API-003 | 7 | WP-23 | 11 | WP-28, WP-29 | AT | `tests/api/test_governance.py::test_spec_requirement[API-003]` | PLANNED |
| API-004 | PV-API-004 | 7 | WP-24 | 11 | WP-28, WP-29 | AT | `tests/api/test_sse.py::test_spec_requirement[API-004]` | PLANNED |
| API-005 | PV-API-005 | 7 | WP-24 | 11 | WP-28, WP-29 | AT | `tests/api/test_sse.py::test_spec_requirement[API-005]` | PLANNED |
| API-006 | PV-API-006 | 7 | WP-24 | 11 | WP-28, WP-29 | AT | `tests/api/test_sse.py::test_spec_requirement[API-006]` | PLANNED |
| API-007 | PV-API-007 | 7 | WP-24 | 11 | WP-28, WP-29 | AT | `tests/api/test_sse.py::test_spec_requirement[API-007]` | PLANNED |
| API-008 | PV-API-008 | 7 | WP-25 | 12 | WP-23, WP-24, WP-28, WP-29 | AT | `web/src/App.test.tsx::test_spec_requirement[API-008]` | PLANNED |
| API-009 | PV-API-009 | 7 | WP-23 | 11 | WP-25 | AT | `tests/api/test_governance.py::test_spec_requirement[API-009]` | PLANNED |
| API-010 | PV-API-010 | 7 | WP-23 | 11 | WP-28, WP-29 | AT | `tests/api/test_governance.py::test_spec_requirement[API-010]` | PLANNED |
| CRD-001 | PV-CRD-001 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[CRD-001]` | PLANNED |
| CRD-002 | PV-CRD-002 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[CRD-002]` | PLANNED |
| CRD-003 | PV-CRD-003 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[CRD-003]` | PLANNED |
| CRD-004 | PV-CRD-004 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[CRD-004]` | PLANNED |
| CRD-005 | PV-CRD-005 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[CRD-005]` | PLANNED |
| CRD-006 | PV-CRD-006 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[CRD-006]` | PLANNED |
| CRD-007 | PV-CRD-007 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[CRD-007]` | PLANNED |
| CRD-008 | PV-CRD-008 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[CRD-008]` | PLANNED |
| CRD-009 | PV-CRD-009 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[CRD-009]` | PLANNED |
| CRD-010 | PV-CRD-010 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[CRD-010]` | PLANNED |
| CRD-011 | PV-CRD-011 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[CRD-011]` | PLANNED |
| CRD-012 | PV-CRD-012 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[CRD-012]` | PLANNED |
| CRD-013 | PV-CRD-013 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[CRD-013]` | PLANNED |
| DST-001 | PV-DST-001 | 10 | WP-29 | 14 | WP-26 | DOC/COLD | `tests/cold/test_installed_smoke.py::test_spec_requirement[DST-001]` | PLANNED |
| DST-002 | PV-DST-002 | 10 | WP-29 | 14 | WP-26 | DOC/COLD | `tests/cold/test_installed_smoke.py::test_spec_requirement[DST-002]` | PLANNED |
| DST-003 | PV-DST-003 | 10 | WP-29 | 14 | WP-26 | DOC/COLD | `tests/cold/test_installed_smoke.py::test_spec_requirement[DST-003]` | PLANNED |
| DST-004 | PV-DST-004 | 10 | WP-29 | 14 | WP-26 | DOC/COLD | `tests/cold/test_installed_smoke.py::test_spec_requirement[DST-004]` | PLANNED |
| DST-005 | PV-DST-005 | 10 | WP-29 | 14 | WP-26 | DOC/COLD | `tests/cold/test_installed_smoke.py::test_spec_requirement[DST-005]` | PLANNED |
| GEN-001 | PV-GEN-001 | 0 | WP-01 | 1 | WP-28, WP-29 | DOC | `tests/unit/agent/test_actions.py::test_spec_requirement[GEN-001]` | PLANNED |
| GEN-002 | PV-GEN-002 | 0 | WP-01 | 1 | WP-28, WP-29 | DOC | `tests/unit/agent/test_actions.py::test_spec_requirement[GEN-002]` | PLANNED |
| GEN-003 | PV-GEN-003 | 0 | WP-01 | 1 | WP-28, WP-29 | DOC | `tests/unit/agent/test_actions.py::test_spec_requirement[GEN-003]` | PLANNED |
| GEN-004 | PV-GEN-004 | 8 | WP-27 | 13 | WP-28, WP-29 | DOC | `tests/docker/test_cross_profile.py::test_spec_requirement[GEN-004]` | PLANNED |
| GEN-005 | PV-GEN-005 | 8 | WP-27 | 13 | WP-28, WP-29 | DOC | `tests/docker/test_cross_profile.py::test_spec_requirement[GEN-005]` | PLANNED |
| GEN-006 | PV-GEN-006 | 8 | WP-27 | 13 | WP-28, WP-29 | DOC | `tests/docker/test_cross_profile.py::test_spec_requirement[GEN-006]` | PLANNED |
| GEN-007 | PV-GEN-007 | 7 | WP-23 | 11 | WP-28, WP-29 | DOC | `tests/api/test_governance.py::test_spec_requirement[GEN-007]` | PLANNED |
| GEN-008 | PV-GEN-008 | 6 | WP-21 | 10 | WP-28, WP-29 | DOC | `tests/unit/agent/test_provider.py::test_spec_requirement[GEN-008]` | PLANNED |
| GEN-009 | PV-GEN-009 | 6 | WP-21 | 10 | WP-28, WP-29 | DOC | `tests/unit/agent/test_provider.py::test_spec_requirement[GEN-009]` | PLANNED |
| GEN-010 | PV-GEN-010 | 6 | WP-21 | 10 | WP-28, WP-29 | DOC | `tests/unit/agent/test_provider.py::test_spec_requirement[GEN-010]` | PLANNED |
| POL-001 | PV-POL-001 | 2 | WP-06 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_policy.py::test_spec_requirement[POL-001]` | PLANNED |
| POL-002 | PV-POL-002 | 2 | WP-06 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_policy.py::test_spec_requirement[POL-002]` | PLANNED |
| POL-003 | PV-POL-003 | 2 | WP-06 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_policy.py::test_spec_requirement[POL-003]` | PLANNED |
| POL-004 | PV-POL-004 | 2 | WP-06 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_policy.py::test_spec_requirement[POL-004]` | PLANNED |
| POL-005 | PV-POL-005 | 2 | WP-06 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_policy.py::test_spec_requirement[POL-005]` | PLANNED |
| POL-006 | PV-POL-006 | 2 | WP-06 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_policy.py::test_spec_requirement[POL-006]` | PLANNED |
| POL-007 | PV-POL-007 | 2 | WP-06 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_policy.py::test_spec_requirement[POL-007]` | PLANNED |
| POL-008 | PV-POL-008 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-008]` | PLANNED |
| POL-009 | PV-POL-009 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-009]` | PLANNED |
| POL-010 | PV-POL-010 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-010]` | PLANNED |
| POL-011 | PV-POL-011 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-011]` | PLANNED |
| POL-012 | PV-POL-012 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-012]` | PLANNED |
| POL-013 | PV-POL-013 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-013]` | PLANNED |
| POL-014 | PV-POL-014 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-014]` | PLANNED |
| POL-015 | PV-POL-015 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-015]` | PLANNED |
| POL-016 | PV-POL-016 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-016]` | PLANNED |
| POL-017 | PV-POL-017 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-017]` | PLANNED |
| POL-018 | PV-POL-018 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-018]` | PLANNED |
| POL-019 | PV-POL-019 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-019]` | PLANNED |
| POL-020 | PV-POL-020 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-020]` | PLANNED |
| POL-021 | PV-POL-021 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-021]` | PLANNED |
| POL-022 | PV-POL-022 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-022]` | PLANNED |
| POL-023 | PV-POL-023 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-023]` | PLANNED |
| POL-024 | PV-POL-024 | 2 | WP-07 | 3 | WP-28, WP-29 | UT/DEMO | `tests/unit/domain/test_governance.py::test_spec_requirement[POL-024]` | PLANNED |
| PRC-001 | PV-PRC-001 | 0 | WP-01 | 1 | WP-28, WP-29 | DOC/CI | `tests/unit/agent/test_actions.py::test_spec_requirement[PRC-001]` | PLANNED |
| PRC-002 | PV-PRC-002 | 0 | WP-01 | 1 | WP-28, WP-29 | DOC/CI | `tests/unit/agent/test_actions.py::test_spec_requirement[PRC-002]` | PLANNED |
| PRC-003 | PV-PRC-003 | 0 | WP-01 | 1 | WP-28, WP-29 | DOC/CI | `tests/unit/agent/test_actions.py::test_spec_requirement[PRC-003]` | PLANNED |
| PRC-004 | PV-PRC-004 | 0 | WP-01 | 1 | WP-28, WP-29 | DOC/CI | `tests/unit/agent/test_actions.py::test_spec_requirement[PRC-004]` | PLANNED |
| PRC-005 | PV-PRC-005 | 0 | WP-01 | 1 | WP-28, WP-29 | DOC/CI | `tests/unit/agent/test_actions.py::test_spec_requirement[PRC-005]` | PLANNED |
| PRC-006 | PV-PRC-006 | 0 | WP-01 | 1 | WP-28, WP-29 | DOC/CI | `tests/unit/agent/test_actions.py::test_spec_requirement[PRC-006]` | PLANNED |
| PRC-007 | PV-PRC-007 | 0 | WP-01 | 1 | WP-28, WP-29 | DOC/CI | `tests/unit/agent/test_actions.py::test_spec_requirement[PRC-007]` | PLANNED |
| PRC-008 | PV-PRC-008 | 0 | WP-01 | 1 | WP-28, WP-29 | DOC/CI | `tests/unit/agent/test_actions.py::test_spec_requirement[PRC-008]` | PLANNED |
| PRC-009 | PV-PRC-009 | 0 | WP-01 | 1 | WP-28, WP-29 | DOC/CI | `tests/unit/agent/test_actions.py::test_spec_requirement[PRC-009]` | PLANNED |
| PRC-010 | PV-PRC-010 | 0 | WP-01 | 1 | WP-28, WP-29 | DOC/CI | `tests/unit/agent/test_actions.py::test_spec_requirement[PRC-010]` | PLANNED |
| PST-001 | PV-PST-001 | 4 | WP-15 | 7 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_store.py::test_spec_requirement[PST-001]` | PLANNED |
| PST-002 | PV-PST-002 | 4 | WP-15 | 7 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_store.py::test_spec_requirement[PST-002]` | PLANNED |
| PST-003 | PV-PST-003 | 4 | WP-15 | 7 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_store.py::test_spec_requirement[PST-003]` | PLANNED |
| PST-004 | PV-PST-004 | 2 | WP-05 | 3 | WP-28, WP-29 | UT/IT | `tests/unit/domain/test_state_machine.py::test_spec_requirement[PST-004]` | PLANNED |
| PST-005 | PV-PST-005 | 2 | WP-05 | 3 | WP-28, WP-29 | UT/IT | `tests/unit/domain/test_state_machine.py::test_spec_requirement[PST-005]` | PLANNED |
| PST-006 | PV-PST-006 | 2 | WP-05 | 3 | WP-28, WP-29 | UT/IT | `tests/unit/domain/test_state_machine.py::test_spec_requirement[PST-006]` | PLANNED |
| PST-007 | PV-PST-007 | 4 | WP-15 | 7 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_store.py::test_spec_requirement[PST-007]` | PLANNED |
| PST-008 | PV-PST-008 | 4 | WP-15 | 7 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_store.py::test_spec_requirement[PST-008]` | PLANNED |
| PST-009 | PV-PST-009 | 4 | WP-15 | 7 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_store.py::test_spec_requirement[PST-009]` | PLANNED |
| PST-010 | PV-PST-010 | 4 | WP-15 | 7 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_store.py::test_spec_requirement[PST-010]` | PLANNED |
| PST-011 | PV-PST-011 | 4 | WP-15 | 7 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_store.py::test_spec_requirement[PST-011]` | PLANNED |
| PST-012 | PV-PST-012 | 4 | WP-15 | 7 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_store.py::test_spec_requirement[PST-012]` | PLANNED |
| PST-013 | PV-PST-013 | 4 | WP-16 | 7 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_events.py::test_spec_requirement[PST-013]` | PLANNED |
| PST-014 | PV-PST-014 | 4 | WP-16 | 7 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_events.py::test_spec_requirement[PST-014]` | PLANNED |
| PST-015 | PV-PST-015 | 4 | WP-17 | 8 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_lease.py::test_spec_requirement[PST-015]` | PLANNED |
| PST-016 | PV-PST-016 | 4 | WP-17 | 8 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_lease.py::test_spec_requirement[PST-016]` | PLANNED |
| PST-017 | PV-PST-017 | 4 | WP-17 | 8 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_lease.py::test_spec_requirement[PST-017]` | PLANNED |
| PST-018 | PV-PST-018 | 4 | WP-18 | 8 | WP-28, WP-29 | UT/IT | `tests/integration/recovery/test_startup.py::test_spec_requirement[PST-018]` | PLANNED |
| PST-019 | PV-PST-019 | 4 | WP-17 | 8 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_lease.py::test_spec_requirement[PST-019]` | PLANNED |
| PST-020 | PV-PST-020 | 4 | WP-17 | 8 | WP-28, WP-29 | UT/IT | `tests/integration/persistence/test_lease.py::test_spec_requirement[PST-020]` | PLANNED |
| PST-021 | PV-PST-021 | 7 | WP-24 | 11 | WP-28, WP-29 | UT/IT | `tests/api/test_sse.py::test_spec_requirement[PST-021]` | PLANNED |
| PST-022 | PV-PST-022 | 7 | WP-24 | 11 | WP-28, WP-29 | UT/IT | `tests/api/test_sse.py::test_spec_requirement[PST-022]` | PLANNED |
| PST-023 | PV-PST-023 | 7 | WP-24 | 11 | WP-28, WP-29 | UT/IT | `tests/api/test_sse.py::test_spec_requirement[PST-023]` | PLANNED |
| PST-024 | PV-PST-024 | 7 | WP-24 | 11 | WP-28, WP-29 | UT/IT | `tests/api/test_sse.py::test_spec_requirement[PST-024]` | PLANNED |
| PST-025 | PV-PST-025 | 4 | WP-18 | 8 | WP-28, WP-29 | UT/IT | `tests/integration/recovery/test_startup.py::test_spec_requirement[PST-025]` | PLANNED |
| PST-026 | PV-PST-026 | 4 | WP-18 | 8 | WP-28, WP-29 | UT/IT | `tests/integration/recovery/test_startup.py::test_spec_requirement[PST-026]` | PLANNED |
| PST-027 | PV-PST-027 | 4 | WP-18 | 8 | WP-28, WP-29 | UT/IT | `tests/integration/recovery/test_startup.py::test_spec_requirement[PST-027]` | PLANNED |
| PST-028 | PV-PST-028 | 4 | WP-18 | 8 | WP-28, WP-29 | UT/IT | `tests/integration/recovery/test_startup.py::test_spec_requirement[PST-028]` | PLANNED |
| SBX-001 | PV-SBX-001 | 5 | WP-20 | 9 | WP-28, WP-29 | UT/DT | `tests/docker/test_executor.py::test_spec_requirement[SBX-001]` | PLANNED |
| SBX-002 | PV-SBX-002 | 5 | WP-19 | 9 | WP-28, WP-29 | UT/DT | `tests/docker/test_doctor.py::test_spec_requirement[SBX-002]` | PLANNED |
| SBX-003 | PV-SBX-003 | 5 | WP-19 | 9 | WP-28, WP-29 | UT/DT | `tests/docker/test_doctor.py::test_spec_requirement[SBX-003]` | PLANNED |
| SBX-004 | PV-SBX-004 | 5 | WP-19 | 9 | WP-28, WP-29 | UT/DT | `tests/docker/test_doctor.py::test_spec_requirement[SBX-004]` | PLANNED |
| SBX-005 | PV-SBX-005 | 5 | WP-19 | 9 | WP-28, WP-29 | UT/DT | `tests/docker/test_doctor.py::test_spec_requirement[SBX-005]` | PLANNED |
| SBX-006 | PV-SBX-006 | 5 | WP-20 | 9 | WP-28, WP-29 | UT/DT | `tests/docker/test_executor.py::test_spec_requirement[SBX-006]` | PLANNED |
| SBX-007 | PV-SBX-007 | 5 | WP-20 | 9 | WP-28, WP-29 | UT/DT | `tests/docker/test_executor.py::test_spec_requirement[SBX-007]` | PLANNED |
| SBX-008 | PV-SBX-008 | 5 | WP-20 | 9 | WP-28, WP-29 | UT/DT | `tests/docker/test_executor.py::test_spec_requirement[SBX-008]` | PLANNED |
| SBX-009 | PV-SBX-009 | 5 | WP-20 | 9 | WP-28, WP-29 | UT/DT | `tests/docker/test_executor.py::test_spec_requirement[SBX-009]` | PLANNED |
| SBX-010 | PV-SBX-010 | 5 | WP-20 | 9 | WP-28, WP-29 | UT/DT | `tests/docker/test_executor.py::test_spec_requirement[SBX-010]` | PLANNED |
| SBX-011 | PV-SBX-011 | 5 | WP-20 | 9 | WP-28, WP-29 | UT/DT | `tests/docker/test_executor.py::test_spec_requirement[SBX-011]` | PLANNED |
| SBX-012 | PV-SBX-012 | 5 | WP-20 | 9 | WP-28, WP-29 | UT/DT | `tests/docker/test_executor.py::test_spec_requirement[SBX-012]` | PLANNED |
| SBX-013 | PV-SBX-013 | 5 | WP-19 | 9 | WP-28, WP-29 | UT/DT | `tests/docker/test_doctor.py::test_spec_requirement[SBX-013]` | PLANNED |
| SEC-001 | PV-SEC-001 | 3 | WP-09 | 4 | WP-28, WP-29 | UT/IT | `tests/unit/workspace/test_paths.py::test_spec_requirement[SEC-001]` | PLANNED |
| SEC-002 | PV-SEC-002 | 5 | WP-20 | 9 | WP-28, WP-29 | UT/IT | `tests/docker/test_executor.py::test_spec_requirement[SEC-002]` | PLANNED |
| SEC-003 | PV-SEC-003 | 5 | WP-20 | 9 | WP-28, WP-29 | UT/IT | `tests/docker/test_executor.py::test_spec_requirement[SEC-003]` | PLANNED |
| SEC-004 | PV-SEC-004 | 5 | WP-20 | 9 | WP-28, WP-29 | UT/IT | `tests/docker/test_executor.py::test_spec_requirement[SEC-004]` | PLANNED |
| SEC-005 | PV-SEC-005 | 5 | WP-20 | 9 | WP-28, WP-29 | UT/IT | `tests/docker/test_executor.py::test_spec_requirement[SEC-005]` | PLANNED |
| SEC-006 | PV-SEC-006 | 5 | WP-20 | 9 | WP-28, WP-29 | UT/IT | `tests/docker/test_executor.py::test_spec_requirement[SEC-006]` | PLANNED |
| SEC-007 | PV-SEC-007 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[SEC-007]` | PLANNED |
| SEC-008 | PV-SEC-008 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[SEC-008]` | PLANNED |
| SEC-009 | PV-SEC-009 | 5 | WP-20 | 9 | WP-28, WP-29 | UT/IT | `tests/docker/test_executor.py::test_spec_requirement[SEC-009]` | PLANNED |
| SEC-010 | PV-SEC-010 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[SEC-010]` | PLANNED |
| SEC-011 | PV-SEC-011 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[SEC-011]` | PLANNED |
| SEC-012 | PV-SEC-012 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[SEC-012]` | PLANNED |
| SEC-013 | PV-SEC-013 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/credentials/test_credentials.py::test_spec_requirement[SEC-013]` | PLANNED |
| SEC-014 | PV-SEC-014 | 6 | WP-21 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/agent/test_provider.py::test_spec_requirement[SEC-014]` | PLANNED |
| SEC-015 | PV-SEC-015 | 6 | WP-21 | 10 | WP-28, WP-29 | UT/IT | `tests/unit/agent/test_provider.py::test_spec_requirement[SEC-015]` | PLANNED |
| TST-001 | PV-TST-001 | 1 | WP-04 | 2 | WP-28, WP-29 | UT/IT/DT/AT/DEMO | `tests/unit/agent/test_loop.py::test_spec_requirement[TST-001]` | PLANNED |
| TST-002 | PV-TST-002 | 4 | WP-18 | 8 | WP-28, WP-29 | UT/IT/DT/AT/DEMO | `tests/integration/recovery/test_startup.py::test_spec_requirement[TST-002]` | PLANNED |
| TST-003 | PV-TST-003 | 5 | WP-19 | 9 | WP-28, WP-29 | UT/IT/DT/AT/DEMO | `tests/docker/test_doctor.py::test_spec_requirement[TST-003]` | PLANNED |
| TST-004 | PV-TST-004 | 8 | WP-27 | 13 | WP-28, WP-29 | UT/IT/DT/AT/DEMO | `tests/docker/test_cross_profile.py::test_spec_requirement[TST-004]` | PLANNED |
| TST-005 | PV-TST-005 | 9 | WP-28 | 13 | WP-29 | UT/IT/DT/AT/DEMO | `AGENT_LOG.md::test_spec_requirement[TST-005]` | PLANNED |
| TST-006 | PV-TST-006 | 7 | WP-24 | 11 | WP-28, WP-29 | UT/IT/DT/AT/DEMO | `tests/api/test_sse.py::test_spec_requirement[TST-006]` | PLANNED |
| TST-007 | PV-TST-007 | 6 | WP-22 | 10 | WP-28, WP-29 | UT/IT/DT/AT/DEMO | `tests/unit/credentials/test_credentials.py::test_spec_requirement[TST-007]` | PLANNED |
| TST-008 | PV-TST-008 | 0 | WP-01 | 1 | WP-28, WP-29 | UT/IT/DT/AT/DEMO | `tests/unit/agent/test_actions.py::test_spec_requirement[TST-008]` | PLANNED |
| TXN-001 | PV-TXN-001 | 2 | WP-05 | 3 | WP-28, WP-29 | IT/DEMO | `tests/unit/domain/test_state_machine.py::test_spec_requirement[TXN-001]` | PLANNED |
| TXN-002 | PV-TXN-002 | 2 | WP-05 | 3 | WP-28, WP-29 | IT/DEMO | `tests/unit/domain/test_state_machine.py::test_spec_requirement[TXN-002]` | PLANNED |
| TXN-003 | PV-TXN-003 | 2 | WP-05 | 3 | WP-28, WP-29 | IT/DEMO | `tests/unit/domain/test_state_machine.py::test_spec_requirement[TXN-003]` | PLANNED |
| TXN-004 | PV-TXN-004 | 2 | WP-05 | 3 | WP-28, WP-29 | IT/DEMO | `tests/unit/domain/test_state_machine.py::test_spec_requirement[TXN-004]` | PLANNED |
| TXN-005 | PV-TXN-005 | 3 | WP-13 | 5 | WP-28, WP-29 | IT/DEMO | `tests/integration/transaction/test_changeset.py::test_spec_requirement[TXN-005]` | PLANNED |
| TXN-006 | PV-TXN-006 | 3 | WP-13 | 5 | WP-28, WP-29 | IT/DEMO | `tests/integration/transaction/test_changeset.py::test_spec_requirement[TXN-006]` | PLANNED |
| TXN-007 | PV-TXN-007 | 3 | WP-13 | 5 | WP-28, WP-29 | IT/DEMO | `tests/integration/transaction/test_changeset.py::test_spec_requirement[TXN-007]` | PLANNED |
| TXN-008 | PV-TXN-008 | 3 | WP-13 | 5 | WP-28, WP-29 | IT/DEMO | `tests/integration/transaction/test_changeset.py::test_spec_requirement[TXN-008]` | PLANNED |
| TXN-009 | PV-TXN-009 | 3 | WP-14 | 6 | WP-28, WP-29 | IT/DEMO | `tests/integration/transaction/test_apply.py::test_spec_requirement[TXN-009]` | PLANNED |
| TXN-010 | PV-TXN-010 | 3 | WP-14 | 6 | WP-28, WP-29 | IT/DEMO | `tests/integration/transaction/test_apply.py::test_spec_requirement[TXN-010]` | PLANNED |
| TXN-011 | PV-TXN-011 | 3 | WP-14 | 6 | WP-28, WP-29 | IT/DEMO | `tests/integration/transaction/test_apply.py::test_spec_requirement[TXN-011]` | PLANNED |
| TXN-012 | PV-TXN-012 | 3 | WP-14 | 6 | WP-28, WP-29 | IT/DEMO | `tests/integration/transaction/test_apply.py::test_spec_requirement[TXN-012]` | PLANNED |
| TXN-013 | PV-TXN-013 | 3 | WP-14 | 6 | WP-28, WP-29 | IT/DEMO | `tests/integration/transaction/test_apply.py::test_spec_requirement[TXN-013]` | PLANNED |
| TXN-014 | PV-TXN-014 | 3 | WP-14 | 6 | WP-28, WP-29 | IT/DEMO | `tests/integration/transaction/test_apply.py::test_spec_requirement[TXN-014]` | PLANNED |
| TXN-015 | PV-TXN-015 | 3 | WP-14 | 6 | WP-28, WP-29 | IT/DEMO | `tests/integration/transaction/test_apply.py::test_spec_requirement[TXN-015]` | PLANNED |
| TXN-016 | PV-TXN-016 | 3 | WP-14 | 6 | WP-28, WP-29 | IT/DEMO | `tests/integration/transaction/test_apply.py::test_spec_requirement[TXN-016]` | PLANNED |
| TXN-017 | PV-TXN-017 | 3 | WP-13 | 5 | WP-28, WP-29 | IT/DEMO | `tests/integration/transaction/test_changeset.py::test_spec_requirement[TXN-017]` | PLANNED |
| TXN-018 | PV-TXN-018 | 3 | WP-13 | 5 | WP-28, WP-29 | IT/DEMO | `tests/integration/transaction/test_changeset.py::test_spec_requirement[TXN-018]` | PLANNED |
| TXN-019 | PV-TXN-019 | 3 | WP-14 | 6 | WP-28, WP-29 | IT/DEMO | `tests/integration/transaction/test_apply.py::test_spec_requirement[TXN-019]` | PLANNED |
| WS-001 | PV-WS-001 | 3 | WP-10 | 4 | WP-28, WP-29 | UT/IT | `tests/integration/workspace/test_baseline.py::test_spec_requirement[WS-001]` | PLANNED |
| WS-002 | PV-WS-002 | 3 | WP-12 | 5 | WP-28, WP-29 | UT/IT | `tests/unit/workspace/test_synthetic_git.py::test_spec_requirement[WS-002]` | PLANNED |
| WS-003 | PV-WS-003 | 3 | WP-12 | 5 | WP-28, WP-29 | UT/IT | `tests/unit/workspace/test_synthetic_git.py::test_spec_requirement[WS-003]` | PLANNED |
| WS-004 | PV-WS-004 | 3 | WP-12 | 5 | WP-28, WP-29 | UT/IT | `tests/unit/workspace/test_synthetic_git.py::test_spec_requirement[WS-004]` | PLANNED |
| WS-005 | PV-WS-005 | 3 | WP-12 | 5 | WP-28, WP-29 | UT/IT | `tests/unit/workspace/test_synthetic_git.py::test_spec_requirement[WS-005]` | PLANNED |
| WS-006 | PV-WS-006 | 3 | WP-10 | 4 | WP-28, WP-29 | UT/IT | `tests/integration/workspace/test_baseline.py::test_spec_requirement[WS-006]` | PLANNED |
| WS-007 | PV-WS-007 | 3 | WP-10 | 4 | WP-28, WP-29 | UT/IT | `tests/integration/workspace/test_baseline.py::test_spec_requirement[WS-007]` | PLANNED |
| WS-008 | PV-WS-008 | 3 | WP-10 | 4 | WP-28, WP-29 | UT/IT | `tests/integration/workspace/test_baseline.py::test_spec_requirement[WS-008]` | PLANNED |
| WS-009 | PV-WS-009 | 3 | WP-10 | 4 | WP-28, WP-29 | UT/IT | `tests/integration/workspace/test_baseline.py::test_spec_requirement[WS-009]` | PLANNED |
| WS-010 | PV-WS-010 | 3 | WP-11 | 5 | WP-28, WP-29 | UT/IT | `tests/integration/workspace/test_ignored.py::test_spec_requirement[WS-010]` | PLANNED |
| WS-011 | PV-WS-011 | 3 | WP-11 | 5 | WP-28, WP-29 | UT/IT | `tests/integration/workspace/test_ignored.py::test_spec_requirement[WS-011]` | PLANNED |
| WS-012 | PV-WS-012 | 3 | WP-11 | 5 | WP-28, WP-29 | UT/IT | `tests/integration/workspace/test_ignored.py::test_spec_requirement[WS-012]` | PLANNED |
| WS-013 | PV-WS-013 | 3 | WP-09 | 4 | WP-28, WP-29 | UT/IT | `tests/unit/workspace/test_paths.py::test_spec_requirement[WS-013]` | PLANNED |
| WS-014 | PV-WS-014 | 3 | WP-09 | 4 | WP-28, WP-29 | UT/IT | `tests/unit/workspace/test_paths.py::test_spec_requirement[WS-014]` | PLANNED |
| WS-015 | PV-WS-015 | 3 | WP-11 | 5 | WP-28, WP-29 | UT/IT | `tests/integration/workspace/test_ignored.py::test_spec_requirement[WS-015]` | PLANNED |
| WS-016 | PV-WS-016 | 3 | WP-11 | 5 | WP-28, WP-29 | UT/IT | `tests/integration/workspace/test_ignored.py::test_spec_requirement[WS-016]` | PLANNED |

# 每日 Gate

- [ ] 运行当天新增的每个精确行为 node 及受影响的回归测试。
- [ ] 检查发生变化的 PV 行、review、finding 和 commit boundary。
- [ ] 确认没有运行时 pull/build、依赖安装、网络 fallback、任意命令或 Stretch goal。

# Day 13–14 收敛

- [ ] 完成 WP-27，并冻结产品功能面。
- [ ] 运行三项确定性演示和 dirty-target conflict case。
- [ ] 在 Day 13 执行完整 specification review，修复合规 finding 并复验。
- [ ] 在 Day 14 执行完整 quality review，并只进行质量修复。
- [ ] 使用 Day 12 建立的结构构建 assets/wheel；运行精确的离线 `unit-test` CI。
- [ ] 完成 `README.md`、`SPEC_PROCESS.md`、`AGENT_LOG.md` 和 `REFLECTION.md`。
- [ ] 执行 cold-start 安装、doctor、WebUI 和一个 Mock task。
- [ ] 审计恰好 207 个 PV，并确认 WP-29 未新增产品能力。

# 可行性

这是一个高风险且有前置条件的计划。它要求在 Day 1 前批准计划、持续可用的 subagent 容量、已预构建并记录 digest 的固定镜像、dependency-ready fixture，以及每日完成收敛。只能通过减少 UI 美化、高级 diff、可选 lint 组合、额外 Provider/演示、非必要优化/重构和文档样式来回收时间；不得削减冻结需求、治理、恢复、Docker 隔离、Mock 测试、演示、离线 CI、cold-start、PV 证据或评审。
