# 规格过程基线

## 权威文档

| 文件 | 状态 | 批准的 SHA-256 |
|---|---|---|
| `SPEC.md` | FROZEN | `01a30b5fcfd728bb8c334fdb76173e4d83e2667fc9b97a05672ce773f80e238e` |
| `PLAN.md` | FROZEN | `571c5b4cbbede66039cb6531b5512ea41a8c187d4a86225331e8d66b2ad6d37f` |

`SPEC.md` 定义 MVP 行为和验收语义。`PLAN.md` 定义工作包归属、计划验证（Planned Verification）记录、文件和测试安排。本文档只记录过程证据，不重新定义任何权威文档。

## Requirement 与 PV 台账结构

每条记录保留：Requirement ID、原始需求引用、Planned Verification ID、归属阶段、归属工作包、归属日期、支持工作包、计划类别原始值、规范化计划类别、精确计划节点或用例、状态、最终证据类别原始值、规范化最终类别及证据引用。

归属是 `PLAN.md` 可追溯性行中的唯一阶段、工作包和日期三元组。支持工作包是验证贡献者，绝不是额外归属方。状态从 `PLANNED` 开始；只有归属方可首次设置 `IN_PROGRESS` 或 `IMPLEMENTED`，而 `VERIFIED` 要求完成全部支持验证。

`PLAN.md` 的计划类别与 `SPEC.md` 附录 H 的最终证据类别是两个独立字段，二者不得相互替代。

## 变更、范围与退役台账

设计变更记录包含：Change/Requirement ID、日期与时间、提出原因、原语义及冻结文本引用、拟议语义、范围影响、45 天计划影响、迁移影响、测试影响、主要贡献影响、风险影响、批准状态以及批准证据或批准人。WP-01 未提出设计变更：`NONE`。

范围扩展影响记录包含：扩展 ID、拟议能力、MVP 或 Stretch 分类、受影响的 Requirements/PVs、归属、日期、文件及测试影响、安全与验收影响、批准状态和证据引用。

退役 ID 记录包含：退役的 Requirement/PV ID、日期与时间、原因、替代 ID 或 `NONE`、批准引用及保留的历史证据链接。WP-01 没有退役 ID。

## 证据台账

每条记录包含：证据 ID、Requirement/PV ID、类别层（`PLANNED` 或 `FINAL`）、类别原始值、精确制品、节点或命令、观察结果、产出角色、日期与时间、状态以及支持工作包完成情况引用。

未来支持证据槽仍为 `PENDING`：CI 证据、cold-start 验证、六文档闭环、第二个 commit 以及 WP-01 完成状态。通过 WP-01 计划测试不会改变任何 Requirement 的 `PLANNED` 状态。

## WP-01 证据状态

- 冻结基线 commit：已记录。
- linked worktree 与受控文件基线：已记录。
- pytest 环境 bootstrap：已记录于 `AGENT_LOG.md`。
- collection 与预期 Red：执行后已记录于 `AGENT_LOG.md`。
- 规格整改复审：`APPROVED`；首次代码质量审查：`CHANGES_REQUIRED`；整改过程已记录于 `AGENT_LOG.md`。
- 最终代码质量复审：`APPROVED`；权威表边界、畸形行、重复归属 mutation 以及 `CQ-1..CQ-5` 检查均通过，问题数为零。
- 主 Agent 最终验证：`COMPLETED`。
- stage、cold-start、最终 CI 证据和第二个 commit：`PENDING`。
- WP-01 完成状态：`PENDING`。
- 首次代码质量复审返回 `CHANGES_REQUIRED`（Important 2、Minor 1）；权威表边界整改和隔离 mutation 证据已记录于 `AGENT_LOG.md`。整改后 reviewer `/root/wp01_quality_final_rereviewer` 返回 `APPROVED`，全部检查通过。
- 中文文档合规整改已删除英文叙述模板，并将测试契约改为验证稳定的中文过程语义及显式批准的纠正工作树上下文；本次审查、stage 与 commit 仍为 `PENDING`。
