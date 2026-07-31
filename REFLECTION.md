# WP-01 阶段性反思

项目范围是冻结的 AI4SE Coding Agent Harness MVP。WP-01 建立仓库、worktree、过程、可导入根包、可追溯性测试以及有意保留的首次 Red，不实现归属 WP-02 的产品行为。

linked worktree 将批准的 Day 1 变更与干净的 `main` 隔离，同时共享基线 commit。合法 Red 专指缺少 `coding_harness.agent.actions.parse_action`；创建父包、stub 或得到 Green 都会越过 WP-02 归属边界。

早期 sandbox 将 Git 元数据挂载为只读，并阻断 bootstrap 使用的代理路径。当前 profile 下已验证批准的 pytest bootstrap。collection 已验证为精确 19 个测试且退出码为 0。合法 Red 已验证为 18 passed、1 failed 且退出码为 1；预期失败节点为 `tests/unit/agent/test_actions.py::test_action_schema_missing_fails`。

第一次完整 Red 不合法（16 passed、3 failed）：Requirement parser 遗漏了 16 个规范性的双字母 `WS` ID，且生成的 cache 路径违反受控 dirty path 断言。修复周期将 parser 收窄到规范性 bullet 定义，同时接受双字母或三字母前缀；清理生成 cache，并在后续证据运行中禁用 bytecode 与 pytest cache。

当前风险包括意外扩大范围、混淆 `PLAN.md` 计划类别与 `SPEC.md` 附录 H 最终类别、把 supporting packages 当作 owner，或把计划中的过程证据误写成已完成。

规格整改复审随后关闭全部三个原始 finding，并批准 A-J。独立代码质量审查随后返回 `CHANGES_REQUIRED`（Critical 0、Important 3、Minor 2）。第一次质量整改在修改前暂停，因为 `Requirement/PV` 与 `归属 PV` 可能被误解为相等的归属集合。权威裁决明确：`归属 PV` 定义 owner，而 `Requirement/PV` 是 involved 超集，可以包含 supporting Requirements；因此整改在不修改冻结 `PLAN.md` 的情况下恢复。具体反例包括：WP-09（`WS-012` 被涉及但不归属）、WP-16（`PST-023..024` 为 supporting）、WP-26（仅 supporting 且没有 `归属 PV`）、WP-28（`supporting all PVs` 但只归属 `PV-TST-005`）及 WP-29（支持 PRC 与全部 PV，但只归属 `PV-DST-001..005`）。

在当时的检查点，代码质量复审、最终验证、stage、第二个 commit、CI/cold-start 证据及 WP-01 完成状态仍为 `PENDING`；后续审查结果和当前剩余 gate 记录如下。WP-01 最终反思仍为 `PENDING`。

首次代码质量复审返回 `CHANGES_REQUIRED`（Important 2、Minor 1）：权威表内不以 pipe 开头的行可能被误认为表格结束，且重复 owner mutation 声明缺少可独立恢复的原始证据。fresh remediator `/root/wp01_quality_evidence_remediator` 收紧结构边界，在隔离环境中验证缺失 pipe 和错误列数，并针对 `/tmp` 中的 PLAN 副本执行重复 owner mutation。最终 reviewer `/root/wp01_quality_final_rereviewer` 随后批准权威表边界、畸形行证据、重复 owner mutation 证据及 `CQ-1..CQ-5`，问题数为零。主 Agent 最终验证为 `COMPLETED`；stage、第二个 commit、cold-start/最终 CI 证据、WP-01 完成状态及 WP-02 仍为 `PENDING`。

前期过程文档未遵守“项目文档全部使用中文”的固定要求，本次完成合规纠正。后续所有开发 Prompt、过程文档、审查报告和用户可见说明均应使用中文；仅技术标识符保留英文。

中文化期间发现，测试把两句英文叙述和已完成快照分支当成固定契约，造成语言要求与测试运行上下文冲突。权威裁决要求测试验证稳定的过程语义与显式批准的纠正工作树，同时保留冻结摘要、main、祖先、index 和 dirty path 保护。本次仅做相应的最小测试契约修复，不改变 Requirement、PV、证据状态或历史事实；审查、stage 与 commit 仍为 `PENDING`。

# 项目最终反思

## 从机制堆叠到清晰边界

项目最终形成了 Agent、Governance、Workspace、Transaction、Persistence、Recovery、
Sandbox、Provider 和 Credential 等相互独立的能力。最重要的设计经验不是增加接口数量，
而是保持 authority boundary：ChangeSet 不负责写回，Persistence 不负责 Apply，
Startup Recovery 不执行恢复，Credential Provider 不改变 Provider protocol。清晰边界让
每个工作包可以被单独测试和审查。

## TDD 与 worktree

TDD 的价值主要体现在阻止“为了通过演示而补功能”。Red 必须来自缺失接口或可观察行为，
不能来自 collection 或环境问题。linked worktree 则让每个 WP 和最终收敛阶段都拥有明确
baseline，避免 main 上的未提交状态污染测试证据。多次 cleanliness gate 也提醒我们区分
行为回归与提交过程状态。

## 确定性与失败反馈

Mock LLM、结构化 ToolResult、Policy decision、Manifest digest、ChangeSet、transaction
journal 和 recovery finding 都采用闭合、可审计的表示。失败不是日志字符串，而是下一轮
决策输入；不确定文件副作用不能被报告为成功。这使 Harness 的主要贡献可以通过离线测试
和三个短小 examples 复现。

## Scope Reduction

原冻结计划包含 API、SSE、WebUI、完整 credential store、Node 跨 profile 和正式
distribution。人工澄清课程目标后，项目进行了明确的 scope reduction：保留核心受治理
执行机制，把产品界面和工业级安全能力延期。过程文档保留原 Requirement ID 与语义，
没有把 deferred 内容误报为已实现。

## 最终取舍

Finalization 不新增 product entrypoint，也不复制 production logic。README、离线 CI、
examples 和 verification checklist 只把已有能力组织成可运行、可演示、可复现的课程提交。
如果继续发展，下一步应先根据真实使用需求选择 API 或 distribution，而不是同时恢复所有
延期工作包。
