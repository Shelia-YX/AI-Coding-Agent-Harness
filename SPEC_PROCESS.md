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

## 正式规格形成前 Brainstorming 证据——追溯归档

本节于 `2026-07-23 16:12:26 +0800 (Asia/Shanghai)` 追溯归档，用于保存正式 `SPEC.md` 形成前的 brainstorming 过程摘要。它不是当时的同期仓库记录，也不复制完整对话。

### Evidence Source

| 附件名称 | 当前可读行数 | SHA-256 |
|---|---:|---|
| `澄清 AI4SE 项目需求` | 2709 | `76a7497145b136950d617ceae5a3afb512a470b66ea506402f96824de2665816` |
| `澄清首个关键问题` | 4996 | `81995d79e4b0fd08d07662ae7034b82187328cf0ebf1ec4104436788cd2e2e9b` |

### VERIFIED

以下仅表示当前提供的附件文本中存在相应记录，不将附件来源或历史时间升级为仓库同期机器证据：

- 附件明确记录使用 `superpowers:using-superpowers` 与 `superpowers:brainstorming`，并采用只读探索、每轮一个核心问题、先解释影响、比较候选方案、等待人工确认后再推进的 workflow。
- 项目定位经过候选方案比较，收敛为面向本地单一代码仓库、处理中小规模编码任务的受控型通用 Coding Agent MVP。
- 任务输入收敛为 `Issue-driven interactive task contract`：用户提交 Issue 级自然语言任务，Agent 先只读调查并提出任务理解、计划、范围、验收与风险；计划批准和高风险动作批准相互独立。
- Decision、Tools、Memory、Governance、Feedback、Configuration 六个 Harness 维度均被列为最低可运行要求。
- 主要贡献先以治理、事务化执行与可恢复性作为暂定方向，随后比较“受治理的事务化执行”“确定性治理与验收”“可恢复的工作区事务”三个候选，最终收敛为“受治理的事务化执行”。
- 附件明确把设计冻结作为进入正式 `SPEC.md` 的门禁，并要求后续规范不是 brainstorming 对话的简单复制。

### USER_REPORTED

- 用户确认上述两份附件来自项目早期 brainstorming 过程。
- 用户确认这两份附件应作为正式 brainstorming evidence 的来源归档。

### UNKNOWN

- 原始 brainstorming 的精确日期与时间、原始会话平台和会话 ID。
- 当时 Agent/model 的可验证身份。
- 两份附件是否包含全部轮次、是否经过裁剪或格式转换，以及跨附件的精确时间顺序。
- 原始只读命令与完整终端输出，以及附件内容与具体 Git commit 的精确对应关系。

### Impact

- 该 brainstorming 过程为后续 `SPEC.md` 的项目定位、权威边界、主要贡献和章节重点提供了形成依据。
- 该过程影响 `PLAN.md` 对 Agent Core、治理、工作区事务、确定性演示和后续验证工作的规划。
- 后续架构叙事以“受治理的事务化执行”为中心，将 Agent loop、确定性 Policy/审批/验收、隔离工作区、Baseline、Change Set、冲突检测和可恢复 Apply 组织为同一机制链。
- 本归档仅证明过程证据及决策形成记录存在，不代表任何设计已经实现、测试或验收完成。
- 本归档不改变现有 Requirement/PV ID、ownership 或状态，也不覆盖冻结的 `SPEC.md` 与 `PLAN.md`。

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

### WP-01 正式实现前陌生开发 Agent 规约冷启动验证——追溯补记

本节于 `2026-07-23 13:17:04 +0800 (Asia/Shanghai)` 追溯补记，不是 WP-01 实施时的同期记录。本次事件是实现前陌生开发 Agent 对项目开发规约的冷启动验证，不是安装后、运行环境或产品级 cold-start。

#### USER_REPORTED

- 用户当前追溯确认：该事件发生于 WP-01 正式实现之前；使用了与主实现 Agent 不同类型的 Agent `Claude`，预期任务为尝试执行 WP-01。
- 用户当前追溯确认：Claude 未稳定遵循项目开发协作中的中文输出和中文项目文档要求；用户随后修改 fresh Agent 启动 Prompt，显式加入中文协作约束。
- 用户当前追溯确认：中文协作要求属于开发过程约束，不属于 Harness 产品语义。
- 上述事实来自用户本次追溯确认，不是仓库内保存的同期证据。

#### VERIFIED

- 当前 `SPEC_PROCESS.md` 与 `AGENT_LOG.md` 中不存在该 Claude 事件的同期记录；后续过程记录中存在中文文档及中文协作整改。
- 当前 `SPEC.md` 与 `PLAN.md` 未将中文输出或中文项目文档规定为 Harness 产品功能语义。
- 本次补记仅修改 `SPEC_PROCESS.md` 与 `AGENT_LOG.md`，不修改产品规约、实现计划、产品代码或测试。
- 后续中文整改记录只能证明后续整改存在，不能证明本次 Claude 事件本身发生。

#### UNKNOWN

- 精确发生日期和时间、原始启动 Prompt、Claude 原始输出或完整对话。
- 当时执行的命令、测试结果、关联 commit、reviewer 及其他同期证据。

#### 分类与处理

- 用户本轮批准的过程分类：该 finding 属于开发过程上下文未显式传递或过程约束执行不稳定，不属于 Harness 产品规约缺陷，因此不修改 `SPEC.md` 或 `PLAN.md`。【USER_REPORTED / 本轮批准的过程决定】
- 用户本轮批准的后续处理规则：所有 fresh implementer / reviewer 的启动 Prompt 必须显式重复中文过程约束，不应依赖用户与主 Agent 之间的隐性共享上下文。【USER_REPORTED / 本轮批准的过程决定】

#### 非影响声明

- 本追溯补记不改变产品语义，不改变任何 Requirement/PV ownership。
- 本追溯补记不完成或关闭正式产品安装/运行 cold-start 的 `PENDING` 项。
- 本追溯补记不追溯修改已有 Git 历史，也不伪装成当时的实时记录。

## WP-02..08 追溯审计重建

**RETROSPECTIVE AUDIT RECONSTRUCTION**

- 实际补录时间：`2026-07-22 13:52:55 +0800 (Asia/Shanghai)`。
- 同期记录：`SPEC_PROCESS.md` 与 `AGENT_LOG.md` 均没有 WP-02..08 的完整同期记录；WP-01 日志中的 WP-02 前置 Red 片段不构成 WP-02..08 的完整过程台账。本节是事后重建，不是同期时间线。【VERIFIED】
- 证据分级：仓库可直接证明或本次实际重新执行的事实为 `VERIFIED`；仅见于先前执行报告的事实为 `USER_REPORTED`；无法由保留证据恢复的事实为 `UNKNOWN`。
- 当前仓库依据：WP-02 的 implementation/remediation 两个 commit 及 WP-03..08 六个 commit、父链、author/commit time、branch containment、diff/stat、当前文件和测试节点、本次测试输出、当前 Git 状态及冻结摘要。【VERIFIED】
- 历史执行依据：先前会话中的 Red/Green、定向回归、finding、dirty/staged 与 baseline-clean 摘要没有作为原始机器输出保存在仓库中。【USER_REPORTED】
- 不可恢复依据：原始命令的精确执行时间、原 reviewer 身份、未保存的完整终端输出、未保存的临时报告内容，以及 commit 创建时的物理 worktree。【UNKNOWN】

### 统一过程偏差与审计缺口

| ID | 类型 | 记录 | 证据级别 | 处置 |
|---|---|---|---|---|
| `PROC-DEV-001` | process deviation / naming and housekeeping | WP-05..08 被报告为在 `wp-04-agent-loop-stopping` branch/worktree 中连续完成；Git 直接证明四个独立 commit 在该分支形成完整线性历史，且当前该分支绑定同名 linked worktree。SPEC/PLAN 未要求一 WP 一 worktree，因此这不是 Git 完整性失败；Git 不记录 commit 创建时的物理 worktree，该部分保持 `UNKNOWN`。 | 分支、commit 和当前 worktree 映射【VERIFIED】；历史物理 worktree 复用【USER_REPORTED】；创建时物理位置【UNKNOWN】 | 不改写 Git 历史。后续 WP 开始前必须明确记录 branch/worktree ownership。 |
| `AUDIT-GAP-001` | audit gap | `SPEC_PROCESS.md` 与 `AGENT_LOG.md` 未完整同期记录 WP-02..08。本节只追溯重建可证明事实；用户报告不冒充机器证据，不可恢复字段保持 `UNKNOWN`。 | 缺少完整同期条目【VERIFIED】；历史摘要【USER_REPORTED】；未保存原始证据【UNKNOWN】 | 追加本节及对应 Agent Log 聚合记录；不覆盖 WP-01 历史。 |

### 本次当前重新验证

这些结果发生于追溯重建期间，不是 WP-02..08 的历史同期结果。

| 证据 ID | 精确命令或制品 | 观察结果 | 证据级别 |
|---|---|---|---|
| `RETRO-CURRENT-TARGETED-001` | WP-05..08 四个 domain test 文件及 Agent Core 两个定向文件 | `224 passed`；未修改 production/test。 | 【VERIFIED】 |
| `RETRO-CURRENT-BASELINE-001` | `tests/unit/agent/test_actions.py::test_worktree_baseline_is_clean`，完整回归前 | `1 passed`；无项目内 cache/bytecode，Git clean。 | 【VERIFIED】 |
| `RETRO-CURRENT-FULL-001` | `PYTHONDONTWRITEBYTECODE=1 ... pytest -p no:cacheprovider -q` | `331 passed`，`0 failed`，`0 errors`，无 skipped/xfailed；无项目内 cache/bytecode。 | 【VERIFIED】 |
| `RETRO-CURRENT-BASELINE-002` | 同一 baseline-clean node，完整回归后 | `1 passed`；Git clean、staged 为空。 | 【VERIFIED】 |
| `RETRO-CURRENT-AGENT-FUNCTIONAL-002` | 当前 `test_actions.py`、`test_mock_feedback.py`、`test_loop.py` | WP-02..04 functional/directed nodes 为 `133 passed`。【VERIFIED】全局 cleanliness sentinel 因两份获批审计文档处于预期 dirty 而被用户裁决为本编辑阶段 `NOT_APPLICABLE`，不是产品回归失败。【USER_REPORTED】 |
| `RETRO-CURRENT-SCOPED-CLEAN-001` | `git status`、tracked diff allowlist、`git diff --quiet -- src tests SPEC.md PLAN.md`、staged 与 cache 检查 | dirty 精确为 `SPEC_PROCESS.md`、`AGENT_LOG.md`；staged 为空；production/test/SPEC/PLAN 无 diff；无 cache/bytecode。【VERIFIED】用户裁决本阶段以此替代全局 cleanliness sentinel，审计 commit 后必须重跑全局 baseline-clean。【USER_REPORTED】 |

### WP-02：Structured Action 协议

**RETROSPECTIVE AUDIT RECONSTRUCTION**；实际补录时间 `2026-07-22 14:26:39 +0800 (Asia/Shanghai)`。引用统一缺口 `AUDIT-GAP-001`；`PROC-DEV-001` 仅作为后续分支复用背景，不归因于 WP-02。

| 字段 | 补录内容 | 证据级别 |
|---|---|---|
| contemporaneous record / evidence basis | WP-01 日志保留了 WP-02 action API 尚不存在的前置 Red 片段，但没有 WP-02 完整同期实现、评审和关闭台账。当前 Git、PLAN、实现、测试节点及本轮 scoped gate 是直接依据。 | 现有文件与 Git【VERIFIED】；历史执行摘要【USER_REPORTED】；缺失材料【UNKNOWN】 |
| Requirement/PV | `ACT-001..003`、`ACT-008..011`；`PV-ACT-001..003`、`PV-ACT-008..011`。 | 【VERIFIED】 |
| owned files | `src/coding_harness/agent/actions.py`、`results.py`、`tests/unit/agent/test_actions.py`。 | 【VERIFIED】 |
| implementation commit | `d3169f6e8ed0ff32afccfdde9504c8f42e710a97`，parent `f8165579c44af9dfd5a916748a5e8dee9221290a`；author/commit time `2026-07-20 17:57:21 +0800`；3 files、1729 insertions、57 deletions；当前分支可达。 | 【VERIFIED】 |
| follow-up test remediation | `7cbdcf82f8d6bfde8ee9b5584c16142df6d2402f`，parent `d3169f6e8ed0ff32afccfdde9504c8f42e710a97`；author/commit time `2026-07-20 19:03:12 +0800`；仅修改 owned test `test_actions.py`，7 insertions、47 deletions；当前分支可达。 | 【VERIFIED】 |
| 当前 re-verification | `RETRO-CURRENT-AGENT-FUNCTIONAL-002` 中 WP-02 functional nodes 通过，补录前全局 baseline-clean 已由 `RETRO-CURRENT-BASELINE-001/002` 验证。【VERIFIED】用户裁决 cleanliness sentinel 在获批文档编辑阶段为 `NOT_APPLICABLE`，使用 `RETRO-CURRENT-SCOPED-CLEAN-001`。【USER_REPORTED】 | 【VERIFIED】/【USER_REPORTED】 |
| 历史执行 | WP-01 日志及先前对话报告了 action schema 的合法前置 Red；先前报告的 WP-02 当前集合结果为 `107 collected`、`107 passed`，并报告最终 staged/clean 边界已满足。 | 【USER_REPORTED】 |
| review/remediation | Git 证明后续 baseline portability test remediation commit 存在；其历史批准理由、详细 finding、两阶段评审结果及 reviewer 身份没有完整同期仓库证据。 | commit【VERIFIED】；历史过程【USER_REPORTED】；reviewer identity【UNKNOWN】 |
| 未保存证据 | WP-02 实施期 Red/Green 完整输出、精确执行时间、reviewer 原文/身份、未保存 review markdown、临时报告及 commit 创建时的物理 worktree。 | 【UNKNOWN】 |
| completion / confidence | 技术关闭结论保持；owned PV 为 `IMPLEMENTED`，在 supporting verification 完成前不提升为 `VERIFIED`。置信度 mixed。 | Git/当前测试【VERIFIED】；历史过程【USER_REPORTED】；缺失材料【UNKNOWN】 |

### WP-03：Mock LLM、Context 与反馈

**RETROSPECTIVE AUDIT RECONSTRUCTION**；实际补录时间 `2026-07-22 14:26:39 +0800 (Asia/Shanghai)`。引用统一缺口 `AUDIT-GAP-001`；`PROC-DEV-001` 仅作为后续分支复用背景，不归因于 WP-03。

| 字段 | 补录内容 | 证据级别 |
|---|---|---|
| contemporaneous record / evidence basis | 两份过程文件没有 WP-03 完整同期记录；当前 Git、PLAN、实现、测试节点及本轮 scoped gate 是直接依据。 | 当前仓库【VERIFIED】；历史摘要【USER_REPORTED】；缺失材料【UNKNOWN】 |
| Requirement/PV | `AGT-007`、`AGT-009`、`AGT-012`、`AGT-015`；对应 `PV-AGT-007`、`PV-AGT-009`、`PV-AGT-012`、`PV-AGT-015`。 | 【VERIFIED】 |
| owned files | `src/coding_harness/agent/adapters.py`、`mock_llm.py`、`context.py`、`tests/unit/agent/test_mock_feedback.py`。 | 【VERIFIED】 |
| commit | `4672b013bdd8f0286cf65f56eb2eb767a40a3b27`，parent `7cbdcf82f8d6bfde8ee9b5584c16142df6d2402f`；author/commit time `2026-07-21 13:06:05 +0800`；4 files、879 insertions；当前分支可达。 | 【VERIFIED】 |
| 当前 re-verification | `RETRO-CURRENT-AGENT-FUNCTIONAL-002` 中 WP-03 functional nodes 通过；当前阶段 cleanliness 使用 `RETRO-CURRENT-SCOPED-CLEAN-001`。 | 【VERIFIED】 |
| 历史执行 | 先前对话报告 WP-03 定向结果为 `11 passed`；规格审查和代码质量审查均曾要求整改，整改与复审后获批进入 commit/integration。 | 【USER_REPORTED】 |
| review/remediation | 历史对话证明层级仅支持“发生过 finding、整改和复审”的摘要；具体 finding 文本、数量、原 reviewer 身份和原始报告位置没有仓库证据，不从 WP-04/05 数字推断。 | 摘要【USER_REPORTED】；reviewer identity/细节【UNKNOWN】 |
| 未保存证据 | WP-03 实施期 Red/Green 完整输出、精确执行时间、finding 原文、reviewer 身份、未保存 markdown 报告、临时报告及 commit 创建时的物理 worktree。 | 【UNKNOWN】 |
| completion / confidence | 技术关闭结论保持；owned PV 为 `IMPLEMENTED`，在 supporting verification 完成前不提升为 `VERIFIED`。置信度 mixed。 | Git/当前测试【VERIFIED】；历史过程【USER_REPORTED】；缺失材料【UNKNOWN】 |

### WP-04：Agent Loop 与确定性停止器

**RETROSPECTIVE AUDIT RECONSTRUCTION**；实际补录时间 `2026-07-22 14:26:39 +0800 (Asia/Shanghai)`。引用统一缺口 `AUDIT-GAP-001`；`PROC-DEV-001` 描述该 WP 的 branch/worktree 后续被 WP-05..08 复用，不把偏差归因于 WP-04 自身。

| 字段 | 补录内容 | 证据级别 |
|---|---|---|
| contemporaneous record / evidence basis | 两份过程文件没有 WP-04 完整同期记录；当前 Git、PLAN、实现、测试节点及本轮 scoped gate 是直接依据。 | 当前仓库【VERIFIED】；历史摘要【USER_REPORTED】；缺失材料【UNKNOWN】 |
| Requirement/PV | `AGT-001..002`、`AGT-006`、`AGT-008`、`AGT-010..011`、`TST-001`；对应 `PV-AGT-001`、`PV-AGT-002`、`PV-AGT-006`、`PV-AGT-008`、`PV-AGT-010`、`PV-AGT-011`、`PV-TST-001`。 | 【VERIFIED】 |
| PLAN owned files 与实际 scope | PLAN 列出 `agent/loop.py`、`agent/stopping.py`、`src/coding_harness/ports.py`、`test_loop.py`；commit 实际包含 `agent/loop.py`、`agent/stopping.py`、`agent/ports.py`、`test_loop.py`，并包含 WP-03 owned `agent/context.py`。文件路径与 diff 是当前仓库事实。 | 【VERIFIED】 |
| commit | `6fdc89c626505af403e2c066f815315a1324c88f`，parent `4672b013bdd8f0286cf65f56eb2eb767a40a3b27`；author/commit time `2026-07-21 16:12:36 +0800`；5 files、1950 insertions、4 deletions；当前分支可达。 | 【VERIFIED】 |
| WP-03 limited remediation | `context.py` 属于 WP-03 owned file；它在 WP-04 commit 中的 30-line-scale modification 可由 diff 证明。先前对话明确批准该有限 code-quality remediation，因此不记录为未授权范围漂移；批准过程本身未同期写入仓库。 | diff【VERIFIED】；历史批准【USER_REPORTED】 |
| 当前 re-verification | `RETRO-CURRENT-AGENT-FUNCTIONAL-002` 中 WP-04 functional nodes 通过；当前阶段 cleanliness 使用 `RETRO-CURRENT-SCOPED-CLEAN-001`。 | 【VERIFIED】 |
| 历史执行 | 先前报告最终定向为 `27 passed`、完整回归 `134 passed`、baseline-clean `1 passed`；历史 staged paths 为五个获批文件、最终 worktree clean、冻结摘要未变。 | 【USER_REPORTED】 |
| review/remediation | 初始 review 报告 port boundary canonical snapshot、investigation path lexical gate、sensitive exception chain 三项 Important；后续复查发现 `BuiltContext.attempts` 与 canonical history alias。报告称整改后 ContextBuilder 重建 public-contract snapshots，AgentLoop 为 Store/LLM 构造独立上下文，canonical history、Store、LLM 与 final outcome 不共享 attempt tree；最终报告 Critical 0、Important 0、Related Minor 0。 | 【USER_REPORTED】 |
| reviewer identity | 原 reviewer 的真实身份与原始报告位置没有仓库证据。 | 【UNKNOWN】 |
| 未保存证据 | WP-04 实施期 Red/Green 完整输出、精确执行时间、reviewer 原文/身份、未保存 markdown 报告、临时报告及 commit 创建时的物理 worktree。 | 【UNKNOWN】 |
| completion / confidence | 技术关闭结论保持；owned PV 为 `IMPLEMENTED`，在 supporting verification 完成前不提升为 `VERIFIED`。置信度 mixed。 | Git/当前测试【VERIFIED】；历史过程【USER_REPORTED】；缺失材料【UNKNOWN】 |

### WP-05：Task State 与不可变版本

**RETROSPECTIVE AUDIT RECONSTRUCTION**；引用统一偏差 `PROC-DEV-001` 与缺口 `AUDIT-GAP-001`。

| 字段 | 补录内容 | 证据级别 |
|---|---|---|
| Requirement/PV | `AGT-003..005`、`TXN-001..004`、`PST-004..006`；`PV-AGT-003..005`、`PV-TXN-001..004`、`PV-PST-004..006`。 | 【VERIFIED】 |
| owned files | `src/coding_harness/domain/enums.py`、`models.py`、`state_machine.py`、`tests/unit/domain/test_state_machine.py`。 | 【VERIFIED】 |
| commit | `b489b942d5d5a702bd48b22d5c0107131b42b730`，parent `6fdc89c626505af403e2c066f815315a1324c88f`；author/commit time `2026-07-22 11:23:23 +0800`；4 files、1523 insertions；当前分支可达。 | 【VERIFIED】 |
| 当前验证 | 本次 `RETRO-CURRENT-TARGETED-001` 与 `RETRO-CURRENT-FULL-001` 覆盖当前 WP-05 节点。 | 【VERIFIED】 |
| 历史执行 | 合法 Red 报告为 19 failed；整改后 WP-05 报告为 19 passed，Agent Core 定向报告为 27 passed，commit-prep 时 staged 为空且冻结摘要未变。 | 【USER_REPORTED】 |
| review/remediation | 报告曾发现取消、阻塞、不可恢复失败 guard 及 `RECOVERY_REQUIRED` 重复事件边界问题；整改后报告为 `WP05_BOUNDARY_GREEN_READY`，Critical/Important 边界问题关闭。 | 【USER_REPORTED】 |
| reviewer identity | 原 reviewer 的真实身份没有仓库证据。 | 【UNKNOWN】 |
| 未保存证据 | 原始 Red/Green 输出、逐次 reviewer 报告、精确执行时间和临时报告内容未保存在仓库。 | 【UNKNOWN】 |
| completion | 技术关闭结论保持；owned PV 状态记录为 `IMPLEMENTED`，在 WP-28/WP-29 supporting verification 完成前不提升为 `VERIFIED`。证据置信度为 mixed。 | commit/当前测试【VERIFIED】；历史过程【USER_REPORTED】；缺失材料【UNKNOWN】 |

### WP-06：Policy Engine 与硬边界

**RETROSPECTIVE AUDIT RECONSTRUCTION**；引用统一偏差 `PROC-DEV-001` 与缺口 `AUDIT-GAP-001`。

| 字段 | 补录内容 | 证据级别 |
|---|---|---|
| Requirement/PV | `POL-001..007`；`PV-POL-001..007`。 | 【VERIFIED】 |
| owned files | `src/coding_harness/domain/policy.py`、`errors.py`、`tests/unit/domain/test_policy.py`。 | 【VERIFIED】 |
| commit | `72eaef67e25e390a36150135f20bb75d70afae01`，parent `b489b942d5d5a702bd48b22d5c0107131b42b730`；author/commit time `2026-07-22 11:54:50 +0800`；3 files、696 insertions；当前分支可达。 | 【VERIFIED】 |
| 当前验证 | 本次 `RETRO-CURRENT-TARGETED-001` 与 `RETRO-CURRENT-FULL-001` 覆盖当前 WP-06 节点。 | 【VERIFIED】 |
| 历史执行 | 合法 Red 报告为 16 failed；初始 Green 报告为 16 passed；安全整改后 WP-06 报告为 44 passed，WP-05 与 Agent Core 合并回归报告为 46 passed。 | 【USER_REPORTED】 |
| review/remediation | 定向 specification review 报告 Critical 0、Important 2、Minor 0；异常 fail-closed 边界和安全不变量测试覆盖完成整改，复审报告 Critical 0、Important 0、Related Minor 0。 | 【USER_REPORTED】 |
| reviewer identity | 原 reviewer 的真实身份没有仓库证据。 | 【UNKNOWN】 |
| 未保存证据 | 原始 Red/Green 输出、reviewer 原文、精确执行时间和临时报告内容未保存在仓库。 | 【UNKNOWN】 |
| completion | 技术关闭结论保持；owned PV 状态记录为 `IMPLEMENTED`，在 supporting verification 完成前不提升为 `VERIFIED`。证据置信度为 mixed。 | commit/当前测试【VERIFIED】；历史过程【USER_REPORTED】；缺失材料【UNKNOWN】 |

### WP-07：Approval 与 Budget Governance

**RETROSPECTIVE AUDIT RECONSTRUCTION**；引用统一偏差 `PROC-DEV-001` 与缺口 `AUDIT-GAP-001`。

| 字段 | 补录内容 | 证据级别 |
|---|---|---|
| Requirement/PV | `POL-008..024`、`ACT-012`；`PV-POL-008..024`、`PV-ACT-012`。 | 【VERIFIED】 |
| owned files | `src/coding_harness/domain/approvals.py`、`budgets.py`、`src/coding_harness/application/governance.py`、`tests/unit/domain/test_governance.py`。 | 【VERIFIED】 |
| commit | `74025acf5bb063ec20bcda297bd74ea1cb4ccd8f`，parent `72eaef67e25e390a36150135f20bb75d70afae01`；author/commit time `2026-07-22 12:49:41 +0800`；4 files、2218 insertions；当前分支可达。 | 【VERIFIED】 |
| 当前验证 | 本次 `RETRO-CURRENT-TARGETED-001` 与 `RETRO-CURRENT-FULL-001` 覆盖当前 WP-07 节点；独立 `test_policy_record_identity_mismatch_fails_closed` 当前存在。 | 【VERIFIED】 |
| 历史执行 | 合法 Red 报告为 43 failed；授权权威和绑定整改后 WP-07 报告为 90 passed，前序回归报告为 90 passed；commit-prep 时 staged 为空且摘要未变。 | 【USER_REPORTED】 |
| review/remediation | specification review 报告 `C-1`、`C-2`、`I-1`；Policy 权威、类型专属绑定及纯领域 CAS intent 整改后复审报告 Critical 0、Important 0、Related Minor 1。该 Minor 后续报告为由 WP-08 commit 中新增的独立 identity-mismatch node 关闭，未修改 WP-07 production。不得据此声称已实现 persistence 原子 CAS。 | 【USER_REPORTED】 |
| reviewer identity | 原 reviewer 的真实身份没有仓库证据。 | 【UNKNOWN】 |
| 未保存证据 | 原始 Red/Green 输出、reviewer 原文、只读对抗探针输出、精确执行时间和临时报告内容未保存在仓库。 | 【UNKNOWN】 |
| completion | 技术关闭结论保持；owned PV 状态记录为 `IMPLEMENTED`，真正 only-one-commit 原子性仍属于后续 persistence CAS；在 supporting verification 完成前不提升为 `VERIFIED`。证据置信度为 mixed。 | commit/当前测试【VERIFIED】；历史过程【USER_REPORTED】；缺失材料【UNKNOWN】 |

### WP-08：Acceptance Contract

**RETROSPECTIVE AUDIT RECONSTRUCTION**；引用统一偏差 `PROC-DEV-001` 与缺口 `AUDIT-GAP-001`。

| 字段 | 补录内容 | 证据级别 |
|---|---|---|
| Requirement/PV | `ACC-001..007`；`PV-ACC-001..007`。 | 【VERIFIED】 |
| owned files | `src/coding_harness/domain/acceptance.py`、`tests/unit/domain/test_acceptance.py`；另在 `tests/unit/domain/test_governance.py` 增加已批准的 WP-07 deferred Minor 回归 node。 | 【VERIFIED】 |
| commit | `a5805a103d0fb4ba26995ab1fc910d4d1d8b051e`，parent `74025acf5bb063ec20bcda297bd74ea1cb4ccd8f`；author/commit time `2026-07-22 13:32:40 +0800`；3 files、1443 insertions；当前 HEAD。 | 【VERIFIED】 |
| 当前验证 | 本次 `RETRO-CURRENT-TARGETED-001` 与 `RETRO-CURRENT-FULL-001` 覆盖当前 WP-08 节点；两次 baseline-clean 均通过。 | 【VERIFIED】 |
| 历史执行 | 合法 Red 报告为 41 failed；初始 Green 报告为 41 passed；重新审批整改后报告为 43 passed，前序回归报告为 181 passed；commit 后完整回归报告为 331 passed、baseline-clean 1 passed。 | 【USER_REPORTED】 |
| review/remediation | WP-05+WP-08 ordinary group review 报告 WP-08 Important 1、WP-07 deferred Minor 1；新 ContractVersion 重新审批语义和独立 Policy identity mismatch node 完成整改；复审报告 Critical 0、Important 0、Minor 0。 | 【USER_REPORTED】 |
| reviewer identity | 原 reviewer 的真实身份没有仓库证据。 | 【UNKNOWN】 |
| 未保存证据 | 原始 Red/Green 输出、reviewer 原文、精确执行时间和临时报告内容未保存在仓库。 | 【UNKNOWN】 |
| completion | 技术关闭结论保持；owned PV 状态记录为 `IMPLEMENTED`，在 supporting verification 完成前不提升为 `VERIFIED`。证据置信度为 mixed。 | commit/当前测试【VERIFIED】；历史过程【USER_REPORTED】；缺失材料【UNKNOWN】 |

## WP-09：路径与支持文件模型 — 同期启动记录

**记录类型：** `CONTEMPORANEOUS / VERIFIED`

| 字段 | 同期记录 |
|---|---|
| 实际记录时间 | `2026-07-23 10:38:15 +0800 (Asia/Shanghai)` |
| branch ownership | `wp-09-paths-file-model`，仅用于 WP-09。 |
| worktree ownership | `/home/apophis/ai4coding/MyHarness/.worktrees/wp-09-paths-file-model`，不复用旧 WP worktree。 |
| base commit | 从 `main` 的 `bf6b067ccebf1697c67c64da5c83486d29db768c` 创建；新 worktree 初始 HEAD 与该 commit 精确一致。 |
| start gate | branch、HEAD、worktree path 均符合 WP-09 ownership；初始 worktree clean、staged 为空；临时 `/tmp` venv 缺失后仅恢复 pytest 环境，同一 baseline-clean node 重跑为 `1 passed`；未产生项目内 cache/bytecode。 |
| Requirement scope | `SEC-001`、`ACT-004..006`、`WS-012..014`。 |
| owned PV | `PV-ACT-004`、`PV-ACT-005`、`PV-ACT-006`、`PV-SEC-001`、`PV-WS-013`、`PV-WS-014`；`WS-012` 为 involved Requirement，其 PV 仍由 PLAN 指定的后续 package owning。 |
| owned files | `src/coding_harness/workspace/paths.py`、`src/coding_harness/workspace/file_model.py`、`tests/unit/workspace/test_paths.py`。 |
| planned interfaces | `RepoPath.parse`、`SupportedEntry`、`inspect_supported_entry`。 |
| preceding interface dependency | PLAN 未列出必须导入的前序 public type；契约语义承接结构化 action 的仓库根相对路径边界，WP-09 自有接口仍按上述 owned files 实现。 |
| planned first Red node | `tests/unit/workspace/test_paths.py::test_relative_path`；本轮未创建或运行 WP-09 Red。 |
| current status | `STARTED / NO IMPLEMENTATION YET`；无 production/test 修改，未开始 specification review 或 code-quality review。 |
| evidence classification | 本条由当前 Git/worktree、冻结 PLAN/SPEC、baseline-clean 与文件范围命令直接证明，均为 `CONTEMPORANEOUS / VERIFIED`。 |
| STOP / 恢复事件 | `2026-07-23 10:53:02 +0800 (Asia/Shanghai)`：上次状态为 `STOPPED_FOR_WP09_PHYSICAL_OWNERSHIP_CONFLICT`。根因是上轮 Prompt 禁止 physical fixture，而 PLAN WP-09 明确拥有 physical symlink、file type/executable-bit 与 unsupported repository-state inspection；停止期间未创建 test/production，worktree clean。人工裁决允许仅在 pytest `tmp_path` 中创建隔离 filesystem/local Git fixture；当前状态为 `RESUMED_FOR_LEGAL_RED`。证据分类为 `CONTEMPORANEOUS / VERIFIED`。 |
| legal Red | `2026-07-23 10:57:28 +0800 (Asia/Shanghai)`：collect-only 成功，收集 `57` 个节点、退出码 `0`；首个 Red `tests/unit/workspace/test_paths.py::test_relative_path` 被找到并执行，退出码 `1`，准确原因为 `ModuleNotFoundError: No module named 'coding_harness.workspace'`；完整 WP-09 Red 为 `57 collected / 0 passed / 57 failed / 0 errors`、退出码 `1`，全部失败均来自同一 WP-09 production API 尚不存在。physical filesystem 与 local Git fixture 全部位于 pytest `tmp_path`，fixture 无环境失败；未创建 production 文件。当前状态为 `WP09_LEGAL_RED_READY`。证据分类为 `CONTEMPORANEOUS / VERIFIED`。 |
| Green | `2026-07-23 11:06:31 +0800 (Asia/Shanghai)`：创建 `src/coding_harness/workspace/paths.py` 与 `src/coding_harness/workspace/file_model.py`；WP-09 命令 `PYTHONDONTWRITEBYTECODE=1 /tmp/myharness-dev-venv/bin/python -m pytest -p no:cacheprovider tests/unit/workspace/test_paths.py -q` 为 `57 passed`、退出码 `0`；前序定向命令覆盖 WP-05..08 与 Agent Core 指定节点，为 `224 passed`、退出码 `0`。filesystem/symlink/special-file/local Git fixture 均位于 pytest `tmp_path`。`RepoPath` 只拥有纯 lexical canonical identity；`inspect_supported_entry` 拥有只读 physical containment、file type、tracking 与 unsupported repository-state inspection。结果明确是 inspection snapshot，并以 `requires_use_time_revalidation` 表达 TOCTOU 边界，不授权后续写入。当前 dirty 为两份同期文档、两个 production 文件和一个 WP-09 测试文件，staged 为空；状态为 `WP09_GREEN_READY`。证据分类为 `CONTEMPORANEOUS / VERIFIED`。 |
| specification/security review 与有限整改 | `2026-07-23 11:27:52 +0800 (Asia/Shanghai)`：定向 reviewer 结论为 Critical `0`、Important `5`、Minor `0`。五项 finding 分别为：symlink target 未复用 `RepoPath` lexical validation 且 executable 错误继承最终目标 mode；public `lstat` 注入暴露类型权威；linked worktree 未区分 per-worktree/common Git dir 且遗漏 common `info/attributes`；subprocess 与 metadata 读取先无界缓存；ACT-005 缺少明确累计贡献合同及安全回归。新增 `47` 个稳定安全节点；实现前精确选择这些节点为 `47 selected / 9 passed / 38 failed / 0 errors`（另 `57 deselected`），失败均对应上述缺失行为。有限整改后新增节点为 `47 passed`，完整 WP-09 为 `104 passed`，前序 WP-05..08 与 Agent Core 定向集合为 `224 passed`，全部退出码 `0`。整改统一以 `RepoPath.parse` 校验每一跳 symlink target；symlink executable 固定为 false，regular file 仅使用自身 mode；移除 public stat 注入并保留模块私有测试 seam；安全解析 linked-worktree `commondir`，读取 common config/`info/attributes` 与 per-worktree operation/index；metadata 以 regular-only、no-follow、`LIMIT + 1` 读取，Git child 以 argv、清理后的环境、2 秒 timeout 和 stdout/stderr 各 64 KiB 上限流式读取并在超限时终止；inspection 返回 immutable `count_contribution`/`byte_contribution`，累计 enforcement 由上层显式聚合，不引入全局 mutable counter。fixture 前后 manifest 证明 inspection 只读，结果仍要求 use-time revalidation。状态为 `WP09_SECURITY_FIX_GREEN_READY`，未 stage、未 commit、未开始复审或 WP-10。证据分类为 `CONTEMPORANEOUS / VERIFIED`。 |
| 第二轮安全整改 STOP 与权威裁决 | `2026-07-23 11:42:17 +0800 (Asia/Shanghai)`：复审剩余 Critical `0`、Important `3`、Minor `0`，分别为 attributes 非法 UTF-8 未 fail closed、Git subprocess 精确 `LIMIT + 1`/最终 reap 不充分、contribution/size 被要求增加固定机器整数上界。规范核对确认 SPEC 仅要求单次与累计限制；既有 `domain/budgets.py` 只冻结 `type(value) is int and value >= 0`，没有固定机器整数上界。因上界无规范来源，流程以 `STOPPED_FOR_WP09_CONTRIBUTION_LIMIT_UNDEFINED` 停止，期间未新增测试、未修改 production。人工权威裁决 contribution 使用任意精度非负 Python `int`，任务级 `configured_limit` 由后续拥有 budget snapshot 的层执行；`2**100` finding 分类为 `REVIEWER_FINDING_REJECTED_AS_UNSUPPORTED`，禁止引入 32/64-bit、`sys.maxsize` 或其他人为上界。当前恢复状态为 `RESUMED_FOR_WP09_FIX2`；本条不是 retrospective，证据分类为 `CONTEMPORANEOUS / VERIFIED`。 |
| 第二轮安全整改 Red/Green | `2026-07-23 11:49:42 +0800 (Asia/Shanghai)`：新增 `35` 个 `security_fix2` 节点；首批 `34 selected / 15 failed / 19 passed / 0 errors`，随后补充 selector-error 单节点并观察 `1 failed / 0 errors`，失败准确来自 root/common attributes 未 strict UTF-8 decode、Git stream 精确边界/生命周期结果与 finalize seam 缺失、selector error 外抛，以及原无依据的 64-bit `max_bytes` 拒绝。整改后 root/common attributes 统一走 bounded/no-follow/regular-file/strict UTF-8 text contract；每个 Git stream 最多实际保留 `64 KiB + 1`，selector 同时排空双 pipe，overflow/timeout/read/selector failure 进入 terminate→bounded wait→kill→final bounded wait，结果显式记录 `reaped`、原始稳定 failure reason 与 cleanup/reap failure。移除 `_MAX_COUNTER_VALUE`；contribution 保持 immutable、`type(value) is int and value >= 0`，`2**100` 构造与小文件 inspection 均合法，不表示 configured budget 已通过。最终 fix2 为 `35 passed`，完整 WP-09 为 `140 passed`，前序 WP-05..08 与 Agent Core 定向回归为 `224 passed`，全部退出码 `0`。当前状态为 `WP09_SECURITY_FIX2_GREEN_READY`，未 stage、未 commit、未开始复审或 WP-10；证据分类为 `CONTEMPORANEOUS / VERIFIED`。 |
| 第二轮安全整改 cleanup 合同补强 | `2026-07-23 11:53:09 +0800 (Asia/Shanghai)`：最终源码复核发现 stream close 与 terminate 异常尚缺独立回归节点；先新增两个精确节点并观察 `2 failed / 0 errors`，分别证明 terminate 异常未进入稳定 cleanup reason、统一 stream-close 合同尚不存在。最小整改后所有 process cleanup 异常均以固定 reason 记录，仍执行 kill/final wait 并报告是否 reaped；stream close 失败统一返回 `GIT_STREAM_CLOSE_FAILURE`，不包含原异常文本。第二轮最终共新增 `37` 个 `security_fix2` 节点，fix2 为 `37 passed / 105 deselected`，完整 WP-09 为 `142 passed`，前序 WP-05..08 与 Agent Core 定向回归为 `224 passed`，全部退出码 `0`。状态保持 `WP09_SECURITY_FIX2_GREEN_READY`，未 stage、未 commit、未开始复审或 WP-10；证据分类为 `CONTEMPORANEOUS / VERIFIED`。 |
| I-4b kill 异常后的最终 reap 整改 | `2026-07-23 12:05:01 +0800 (Asia/Shanghai)`：最终定向复审剩余 Critical `0`、Important `1`、Minor `0`。根因探针确认 `kill()` 异常会使 cleanup 在 `poll → terminate → first wait → kill` 后提前返回并跳过 final wait。新增两个精确参数化节点，collect-only 为 `2 collected / 0 errors`，实现前为 `2 failed / 0 errors`，均因缺少 final wait；最小整改使 kill 成功或异常均进入 bounded final wait。final wait 成功时返回 `reaped=true`、实际 returncode，并以独立 `GIT_KILL_FAILURE` 记录 kill cleanup issue；final wait 失败时返回 `reaped=false / GIT_REAP_FAILURE`。原 `GIT_TIMEOUT` 等业务 failure reason 保持在独立字段且不被覆盖，原始异常文本不进入结果。整改后新增节点 `2 passed`、完整 WP-09 `144 passed`、前序 WP-05..08 与 Agent Core 定向回归 `224 passed`，全部退出码 `0`。当前状态为 `WP09_REAP_FIX_GREEN_READY`；未 stage、未 commit、未预写复审批准、WP-09 完成或 WP-10。证据分类为 `CONTEMPORANEOUS / VERIFIED`。 |
| 最终定向复审批准 | `2026-07-23 12:34:56 +0800 (Asia/Shanghai)`：补充记录正常 WP-09 审查流程事件 `WP09_FINAL_REREVIEW_APPROVED`，不是新的代码修改。复审 finding 为 kill exception 后缺少 final wait；对应两个新增节点曾合法 Red，整改保证 kill exception 后仍执行 bounded final wait。复审依据为 WP-09 `144 passed`、前序定向回归 `224 passed`；结论为 Critical `0`、Important `0`、Minor `0`，Decision 为 `Approved for commit-prep`，State 为 `WP09_FINAL_REREVIEW_APPROVED`。本条使用实际补录时间，不改写先前事件时间；未 stage、未 commit、未合并或进入 WP-10。证据分类为 `CONTEMPORANEOUS / VERIFIED`。 |

## F-02 远程 PR/MR 协作证据缺失——追溯补记

本节于 `2026-07-23 14:40:29 +0800 (Asia/Shanghai)` 追溯补记，用于记录 WP-01～WP-09 的历史远程协作证据状态，不是开发期间的同期记录。

### USER_REPORTED

- 用户确认：WP-01～WP-09 开发期间未初始化远程仓库，也未创建 PR/MR。
- 用户确认：后续决定补充远程协作流程。
- 本记录只说明历史状态，不创建或伪造历史协作证据。
- 上述历史事实来自用户本次确认，不是远程平台或仓库内保存的同期证据。

### VERIFIED

- 当前仓库不存在 configured remote，也不存在 remote refs。
- WP-01～WP-09 的 commit 均存在；本地 branch、worktree、commit 与 retained reflog 证据存在。
- 当前 `main` 历史保持单父线性；未发现 merge commit，本地 fast-forward 事件可由 retained reflog 核对。
- 当前仓库与过程文档中没有 PR/MR 平台对象编号、URL、approval、platform checks 或 remote merge 记录。
- 本地 Git evidence 不等于 remote PR/MR evidence，不能据此补造远程审查结论。

### UNKNOWN

- 是否曾在仓库外进行远程讨论，以及是否存在未连接或当前不可访问的平台记录。
- 历史 PR/MR URL、远程 reviewer、approval、CI checks、merge API 记录及其他平台证据。

### 分类

- 该 finding 不是产品缺陷、Git 历史损坏或代码质量问题。
- 该 finding 属于工程协作流程缺失与远程审查证据缺失。

### 后续整改规则

用户本轮批准：从 WP-10 开始，每个 WP 必须：

1. 创建独立 branch；
2. 创建对应 worktree；
3. 推送远程 branch；
4. 创建真实 MR/PR；
5. 在 MR/PR 中记录 subagent、人工修改、测试结果与 review evidence；
6. 经过批准后 merge；
7. 保持禁止 rebase、squash 与 history rewrite。

### 非影响声明

- 本追溯补记不修改 WP-01～WP-09 commit，不创建或伪造历史 MR。
- 本追溯补记不改变 `SPEC.md`、`PLAN.md` 或已有产品语义。
- 本追溯补记不进入 WP-10，也不执行任何后续远程流程。

## CLI-only 课程 MVP 与 WebUI Future Extension——范围决策记录

本节记录时间为 `2026-07-23 15:58:21 +0800 (Asia/Shanghai)`。这是当前人工范围决策的过程审计记录，不是对既有 WebUI 设计的删除，也不是 WebUI 完成证据。

### 原始设计与课程约束

- 当前冻结的 `SPEC.md` 与 `PLAN.md` 保留原始 WebUI、API/SSE、静态资源和相关验证设计；本次记录不修改这些权威文档或任何 Requirement/PV ID。【VERIFIED】
- 用户确认当前课程交付允许两种路径：CLI-only 加 hosted release，或 CLI 加 WebUI。【USER_REPORTED】

### 人工范围决策

- 用户批准当前课程 MVP 选择 `CLI-only + GitHub Release` 交付路径。【USER_REPORTED / APPROVED DECISION】
- WebUI 状态为 `DEFERRED / FUTURE EXTENSION`；该状态不表示删除原始设计，不表示已经实现或验证 WebUI，也不把相关 Requirement/PV 伪装为完成。【USER_REPORTED / APPROVED DECISION】
- GitHub Release、CLI distribution、README、CI、Mock LLM 集成演示和 fresh-agent cold-start 仍须按后续实际证据分别闭合；本条不预先记录任何完成状态。【USER_REPORTED / APPROVED DECISION】

### 影响分析

- Agent Loop、Decision Control、Tool Boundary、Governance、Approval、Acceptance 与 Workspace Safety 的既有架构和安全边界保持不变。
- 本决策只调整当前课程 MVP 的交付界面选择，不修改已有实现、测试、Requirement/PV ownership 或 Git 历史。
- 当前冻结 `SPEC.md` 中的 WebUI 设计文本继续保留；本记录不把课程 CLI-only 选择冒充为对冻结规范文本的静默修改。最终若需声明冻结 SPEC 全量符合，仍须单独处理该范围差异并保留批准证据。

### 非影响声明

- 本次仅修改 `SPEC_PROCESS.md` 与 `AGENT_LOG.md`，不修改 `SPEC.md`、`PLAN.md`、产品代码或测试。
- 本次不创建 GitHub Release，不创建 WebUI、WP-10 文件或其他交付制品。
- 本次不创建 commit，不改写 Git 历史，也不进入 WP-10 implementation。

## WP-10 `build_baseline` Ownership Clarification

本节记录时间为 `2026-07-24 10:53:29 +0800 (Asia/Shanghai)`，是 WP-10 进入 Red/implementation 前的同期接口 ownership 澄清。

### Ambiguity

- `SPEC.md` 附录 D.4 将 `build_baseline` 定义为 Harness Internal Operation。【VERIFIED】
- `PLAN.md` 的 WP-10 接口仅列出 `BaselineManifest`、`TaskWorkspace` 和 `materialize_workspace`，且 PLAN 全文未将 `build_baseline` 分配给其他 WP。【VERIFIED】

### Approved Decision 与边界

- 用户权威决定 `build_baseline` 由 WP-10 拥有。【APPROVED DECISION】
- WP-10 拥有 `build_baseline`、`BaselineManifest`、`TaskWorkspace` 和 `materialize_workspace`。
- WP-23 仅拥有 `TaskService` 的 application orchestration；它可以在后续任务启动流程中调用 `build_baseline`，但不重新实现或拥有 Baseline 构建规则。
- WP-11～14 仅消费 WP-10 产生的 Baseline/Task Workspace 输出，并保持各自既有 Requirement/PV 与文件 ownership。

### Non-change

- 本澄清不修改 `SPEC.md` 或 `PLAN.md`，不改变任何 Requirement/PV ownership。
- 本澄清仅补齐冻结 SPEC operation 与 PLAN WP-10 既有领域/文件范围之间的接口归属，不新增产品语义。
- 本轮不创建 `build_baseline` 接口，不修改产品代码或测试，不进入 Red/implementation。

### WP-10 Red 阶段证据

本段于 `2026-07-24 11:13:49 +0800 (Asia/Shanghai)` 同期补录 WP-10 Red 阶段证据，不表示 WP-10 已实现或完成。

#### VERIFIED

- Red 测试文件 `tests/integration/workspace/test_baseline.py` 已创建；当前 SHA-256 为 `b8d0dae4b6265c9f1a1440e6f9076239804d950d889362bf1e07ebb2d3306fbe`。
- 使用 `PYTHONDONTWRITEBYTECODE=1 /tmp/myharness-dev-venv/bin/python -m pytest -p no:cacheprovider --collect-only tests/integration/workspace/test_baseline.py -q` 成功收集 `14` 个节点，退出码为 `0`。
- 使用 `PYTHONDONTWRITEBYTECODE=1 /tmp/myharness-dev-venv/bin/python -m pytest -p no:cacheprovider tests/integration/workspace/test_baseline.py -q` 执行完整 Red，结果为 `14 collected / 0 passed / 14 failed / 0 errors`，退出码为 `1`。
- 全部失败均由测试内部转换为固定的 `WP-10 production API is not implemented`，对应缺少 `coding_harness.workspace.manifest` 及尚未实现的 WP-10 API；没有 collection、fixture、syntax 或环境错误。
- 当前 `src/` 无差异，staged 为空；未创建临时 production/mock implementation，未进入 Green。

#### USER_REPORTED

- 用户确认当前阶段为 `WP10_RED_EXECUTION_COMPLETE`，并批准将 `14` 个失败分类为 `EXPECTED_RED`。

#### UNKNOWN

- 后续 production 实现、Green、回归、review、commit、push 与 PR 的结果均尚不存在，不能提前记录。

本证据不关闭 WS-001、WS-006～009 或对应 PV，也不改变其状态。

### WP-10 Green 阶段证据

本段于 `2026-07-24 11:29:07 +0800 (Asia/Shanghai)` 同期记录 WP-10 从合法 Red 到最小 Green 的实现证据；当前仍等待 review，不表示 WP-10 已完成、已 commit 或已 merge。

#### VERIFIED

- Red 基线为 `14 collected / 0 passed / 14 failed / 0 errors`，全部分类为缺少 WP-10 production API 的 `EXPECTED_RED`；最小实现后，以相同定向文件执行得到 `14 passed / 0 failed`。
- 新增 `src/coding_harness/workspace/manifest.py`，提供不可变 `BaselineManifest` 与 WP-10 ownership 内的 `build_baseline`；新增 `src/coding_harness/workspace/materialize.py`，提供不可变 `TaskWorkspace` 与 `materialize_workspace`。
- 实现捕获任务启动时 tracked、staged、unstaged、untracked 用户文件状态，并从不可变 manifest 内容创建独立可写 Task Workspace。
- 定向测试验证 origin repository 内容、index、HEAD 与 branch 均保持不变，且 materialized workspace 不复制或挂载 `.git`。
- WP-09 定向回归 `tests/unit/workspace/test_paths.py` 为 `144 passed / 0 failed`。
- 当前 production diff 仅新增 WP-10 owned 的 `manifest.py` 与 `materialize.py`；未修改 WP-09 的 `paths.py` 或 `file_model.py`，未实现 WP-11 ignored input、WP-12 synthetic Git、WP-13 Change Set 或 WP-14 apply/recovery。

#### USER_REPORTED

- 用户批准本轮目标为以最小 WP-10 production 将既有 `14` 个 Red 节点推进到 Green，并要求完成后等待 review。

#### UNKNOWN

- 后续 review、整改、Green commit、push、PR 与 merge 结果尚不存在，不能提前记录。

本阶段不关闭 WS-001、WS-006～009 或对应 PV；状态为 `WP10_GREEN_DOCUMENTATION_READY` 前的同期 Green 证据。

### WP-10 Security/Specification Review

本段于 `2026-07-24 11:39:16 +0800 (Asia/Shanghai)` 同期记录 WP-10 Green implementation 的只读 security/specification review 结论。

#### Review result

- Critical：`0`
- Important：`4`
- Minor：`0`
- Decision：`CHANGES_REQUIRED`
- 当前 implementation 不进入 merge 或 merge-prep。

#### Important findings

1. **Git routing environment isolation**：`build_baseline` 必须隔离 `GIT_DIR`、`GIT_WORK_TREE`、`GIT_INDEX_FILE` 等可改变 repository、worktree 或 index 路由的 ambient Git 环境变量，确保 HEAD、branch、候选路径和 inspected root 绑定到同一权威 repository。
2. **Baseline snapshot consistency verification**：构建过程必须在完成前重新验证候选路径集合及相关 Git/filesystem 状态，或以等价 fail-closed 合同拒绝构建期间发生的新增、删除、tracking/index 漂移，避免生成跨时点 manifest。
3. **Git state metadata completeness**：Baseline Manifest 必须补齐 re-check/recovery 所需的 Git 起始状态绑定，不能只以 `TRACKED/UNTRACKED` 和 HEAD/branch 替代 index/status 或 staged/unstaged/mixed 相关权威 metadata。
4. **Bounded subprocess output**：Git 子进程 stdout/stderr 必须采用有界读取与稳定 fail-closed 结果，不能通过无界 `capture_output` 在 timeout 前累积任意输出。

#### Boundary

- 整改保持在 WP-10 的 `BaselineManifest`、`build_baseline`、`TaskWorkspace`、`materialize_workspace` 及其 owned tests 范围内，不扩大 WP ownership。
- 本记录不修改 `SPEC.md` 或 `PLAN.md`，不改变 Requirement/PV ownership。
- 本阶段不修改 production/tests，不声称 finding 已关闭，不声称 WP-10 已完成、已 push 或已 merge。

### WP-10 Security Review Remediation

本段于 `2026-07-24 11:49:54 +0800 (Asia/Shanghai)` 同期记录上述 Critical `0`、Important `4`、Minor `0` review findings 的有限整改与验证证据。

#### Fix summary

1. **Git routing environment isolation**：Git 子进程环境移除 ambient `GIT_*` 路由变量，并仅设置固定的只读配置、locale 与 optional-lock 行为，使 `GIT_DIR`、`GIT_WORK_TREE`、`GIT_INDEX_FILE` 不能把 baseline 构建重定向到其他 repository。
2. **Snapshot consistency verification**：baseline 构建前后比较 HEAD、branch、候选路径集合、index/status 原始状态及 staged/unstaged 路径集合，并在最终返回前重新捕获全部 entries；任一漂移均 fail closed，不引入 workspace lock 或 WP-14 recovery。
3. **Git state metadata completeness**：`BaselineManifest` 与 `TaskWorkspace` 绑定 `source_index_digest`、`source_status_digest`；每个 baseline entry 使用闭合状态区分 `TRACKED_CLEAN`、`TRACKED_STAGED`、`TRACKED_UNSTAGED`、`TRACKED_MIXED`、`UNTRACKED`，不实现 Change Set。
4. **Bounded subprocess behavior**：Git stdout 改为有界流式读取，stderr 不缓存；timeout、读取失败、输出超限或非零退出均返回稳定 fail-closed 结果，不再使用无界 `capture_output`。

#### Verification

- 四个新增 security regression 节点：`4 passed / 0 failed`。
- 完整 WP-10：`18 passed / 0 failed`。
- WP-09 定向回归：`144 passed / 0 failed`。
- `paths.py`、`file_model.py`、冻结 `SPEC.md`/`PLAN.md` 未修改；未实现 WP-11～14。

#### Current state

- 状态：`CHANGES_FIXED_PENDING_REREVIEW`。
- 上述结果仅证明整改实现及定向测试当前通过；尚未获得复审批准，不能进入 merge。
- 当前未 push、未 merge、未进入 main，不声称 WP-10 已完成。

### WP-10 Security Re-review

本段于 `2026-07-24 11:55:10 +0800 (Asia/Shanghai)` 同期记录对原四项 Important finding 的限定复审。

#### Review result

- 原 review：Critical `0`、Important `4`、Minor `0`，Decision `CHANGES_REQUIRED`。
- 本次 re-review：Critical `0`、Important `0`、Minor `0`。
- Git routing environment isolation：`CLOSED`。
- Baseline snapshot consistency：`CLOSED`。
- Manifest Git state metadata completeness：`CLOSED`。
- Bounded subprocess output handling：`CLOSED`。

#### Verification evidence

- Security regression：`4 passed / 0 failed`。
- 完整 WP-10：`18 passed / 0 failed`。
- WP-09 定向回归：`144 passed / 0 failed`。
- 限定复审未发现新的 scope 问题。

#### Decision 与当前边界

- Decision：`APPROVED_FOR_MERGE_PREP`。
- 该决定仅批准进入后续 merge-prep 流程；整改及本次记录尚未 commit，尚未 push，尚未创建 PR，尚未 merge main。
- 本记录不修改 production/tests、冻结 `SPEC.md`/`PLAN.md` 或 WP ownership，也不声称 WP-10 已完成。

### WP-10 PR 合并与 main 同步证据

本段于 `2026-07-24 12:53:57 +0800 (Asia/Shanghai)` 同期记录 WP-10 远程合并及本地 main 同步结果。

#### VERIFIED

- GitHub Pull Request `#1` 已合并，base 为 `main`，head 为 `wp-10-baseline-task-workspace`；PR head 为 `479322b136aaf7f4169e9a43155cd19497782a99`。
- merge commit 为 `3910ed48944fb2c63dac9ecaa8b5bfcb5a1aaafd`，其两个 parent 分别为合并前 main `cbbe64f637b3914fa46f644c2cc56901924b17c0` 与 WP-10 head `479322b136aaf7f4169e9a43155cd19497782a99`，merge strategy 为普通 merge commit，不是 squash。
- 本地 `main` 已通过 `git pull origin main` fast-forward 到 `3910ed48944fb2c63dac9ecaa8b5bfcb5a1aaafd`，与 `origin/main` 一致；WP-10 implementation 已进入 main。
- 既有 Red `14 failed`、Green `18 passed`、security regression `4 passed`、WP-09 regression `144 passed` 及最终 Critical `0` / Important `0` / Minor `0` 的证据保持在前述 WP-10 记录中，本次不改写这些证据。

#### Boundary

- 本次同步与记录不修改 `SPEC.md`、`PLAN.md`、production 或 tests。
- 本次不删除 WP-10 branch/worktree，不开始 WP-11。

## WP-11 Ignored Input 接口 Ownership 决策

本节于 `2026-07-24 13:08:53 +0800 (Asia/Shanghai)` 记录 WP-11 只读调查发现的接口歧义、候选方案和 ownership 决策；本轮不进入 Red 或 implementation。

### Ambiguity

- `SPEC.md` 定义 `SandboxInputManifest` 与 Harness Internal Operation `materialize_ignored_input`，并要求 `include_ignored_input` 经过独立 High-risk Action Approval 后才生成新 Sandbox Input Manifest Version。
- `PLAN.md` 将 `SandboxInputManifest`、`materialize_ignored_input`、`ignored.py` 和 `test_ignored.py` 分配给 WP-11，但未定义 trusted Approval binding 的输入形式、Sandbox Input Manifest Version identity 或 materialization 返回合同。
- 现有 WP-07 `consume_approval` 需要 trusted current Approval、expected revision、presented reference、current execution context、trusted Policy record 及 identity 和当前时间；其 `ApprovalResult` 本身不能脱离这些可信输入被当作可伪造不了的授权凭证。
- 因此不能在缺少 ownership 决策时直接进入 Red：让调用方只传布尔值、任意 digest、自声明 identity 或单独构造的 `ApprovalResult`，都会削弱既有审批权威和一次消费/CAS 合同。

### Candidate options

1. **Option A — WP-11 权威 materialization gateway（选择）**：`materialize_ignored_input` 接收 WP-07 `consume_approval` 所需的完整可信输入，在 WP-11 权威入口内调用既有消费合同；只有 `include_ignored_input` 的匹配 Action Approval 成功消费且 `side_effect_permitted=true` 时，才创建新 Sandbox Input Manifest Version 并物化输入。返回不可变组合结果，包含 Approval consumption/CAS intent、当前版本 manifest 和更新后的 Task Workspace binding；任何失败均无物化副作用。
2. **Option B — 调用方预消费后仅传 `ApprovalResult`**：接口较窄，但 `ApprovalResult` 可由调用方构造，单独使用不能证明 trusted record、Policy record 和 execution context 已被完整核对，拒绝。
3. **Option C — 全部延后到 WP-23 application service**：可由后续 orchestration 组合 persistence transaction，但会使 WP-11 无法拥有并验证 WS-015 的领域门禁，且错误转移当前 PLAN ownership，拒绝。

### Chosen ownership boundary

- WP-07 继续拥有 Approval/Policy 权威、完整绑定校验、一次消费领域合同和 persistence CAS 前置条件。
- WP-11 拥有 `SandboxInputManifest`、其不可变 version identity、ignored input entry/mode/allowed-stage/exportability 合同，以及 `materialize_ignored_input` 的 fail-closed 权威入口和不可变组合结果。
- WP-11 复用 WP-07 `consume_approval`，不得复制、降低或绕过 Approval 校验；不得接受裸 bool、调用方声明的 approved 状态或单独的 forged result 作为授权。
- WP-23 后续只拥有 application orchestration 和 persistence transaction 协调；数据库原子提交不由 WP-11 实现。
- WP-10 的 Baseline authority 与 Task Workspace identity 保持只读依赖；WP-11 不修改 Baseline Manifest，也不拥有 WP-12 Synthetic Git、WP-13 Change Set 或 WP-14 Apply/recovery。

### Return contract 与未决项

- 成功结果必须同时绑定：新 Sandbox Input Manifest Version、未改变的 Baseline digest、Task Workspace identity、已消费 Approval 的 previous/expected/new revision，以及物化的精确 ignored entry/mode。
- 失败结果必须 fail closed，`side_effect_permitted=false`，不产生新 manifest version，不修改 workspace。
- Red 前仍需在 WP-11 owned tests 中固定具体字段名称、稳定 reason code 和版本 identity 的构造格式；这些是本决策边界内的合同细化，不得改变上述权威来源和 ownership。

### Non-change

- 本决策不修改冻结 `SPEC.md` 或 `PLAN.md`，不改变 Requirement/PV ownership。
- 本轮不创建 `ignored.py`、`test_ignored.py` 或任何 production/test，不实现 ignored input，不进入 Red。

### WP-11 合法 Red 阶段证据

本段于 `2026-07-24 13:19:40 +0800 (Asia/Shanghai)` 同期记录 WP-11 Red 测试创建与执行结果；不表示 ignored input 已实现或进入 Green。

#### VERIFIED

- 创建唯一 WP-11 test owner 文件 `tests/integration/workspace/test_ignored.py`；未创建 `src/coding_harness/workspace/ignored.py`，production 无变化。
- 测试覆盖 WS-010、WS-011、WS-012、WS-015、WS-016，并包含 PLAN 九个具名节点、五个 owned PV 参数化节点、十三个 approval binding drift 节点，以及 manifest version、CAS revision、invalid input、immutability 和 forged result 边界。
- collect-only 命令使用 `PYTHONDONTWRITEBYTECODE=1` 与 `-p no:cacheprovider`，结果为 `37 collected / 0 collection errors`，退出码 `0`。
- 完整 Red 使用相同环境和测试文件，结果为 `37 collected / 0 passed / 37 failed / 0 errors`，退出码 `1`。
- 全部 `37` 个失败均在测试执行期被转换为固定 `WP-11 production API is not implemented`，准确对应 `coding_harness.workspace.ignored` 尚不存在；没有 syntax、fixture、collection、network 或环境失败。

#### Classification 与边界

- Red 分类：`EXPECTED_RED = 37`，invalid Red 为 `0`。
- 当前未实现 WP-07 Approval/Policy、WP-10 Baseline、WP-12 Synthetic Git、WP-13 Change Set 或 WP-14 Apply/recovery；未修改冻结 `SPEC.md`/`PLAN.md`。
- 当前状态为 `WP11_RED_EXECUTION_COMPLETE`；未进入 Green、未 commit、未 push、未创建 PR。

### WP-11 Green 实现证据

本段于 `2026-07-24 13:38:32 +0800 (Asia/Shanghai)` 同期记录 WP-11 从合法 Red 到最小 Green 的实现与验证结果；当前等待 security/spec review，不表示已 commit、push、创建 PR 或 merge。

#### VERIFIED

- 新增 WP-11 owned production 文件 `src/coding_harness/workspace/ignored.py`。
- 实现不可变 `SandboxInputManifest` 及其 version identity、revision、digest 与 baseline binding；实现 trusted Approval consumption gateway，复用 WP-07 `consume_approval` 的 trusted current record、Policy record、execution context 与 revision 校验。
- materialization 对 approval binding、path、entry type、size、digest、用途、stage、manifest identity 和 limit 执行 fail-closed validation；只有匹配审批成功消费后才允许产生新 manifest version 和 workspace 副作用。
- `read_only_input` 物化为只读任务副本，`writable_ephemeral` 物化为独立可写临时副本；两者均不可导出给 LLM，不具备 Change Set eligibility 或原仓库 writeback 权限。
- 使用 `PYTHONDONTWRITEBYTECODE=1 /tmp/myharness-dev-venv/bin/python -m pytest -p no:cacheprovider tests/integration/workspace/test_ignored.py -q`，结果为 `37 passed / 0 failed`，退出码 `0`。
- WP-07 Approval/Policy、WP-10 `manifest.py`/`materialize.py`、冻结 `SPEC.md`/`PLAN.md` 均未修改。

#### Current state

- 状态：`WP11_GREEN_IMPLEMENTATION_COMPLETE`。
- 当前新增 `ignored.py`，尚未 commit Green implementation。
- 当前等待独立 security/spec review；未进入 WP-12、WP-13 或 WP-14。

### WP-11 Security/Specification Review

本段于 `2026-07-24 13:54:12 +0800 (Asia/Shanghai)` 同期记录对 commit `ab2efb1124dd600bd9c693c6f448140876716394` 的只读定向 review。Review 前重新运行 WP-11 定向测试，结果为 `37 passed in 1.81s`；测试通过不替代源码合同审查。

#### Review result

- Critical：`0`
- Important：`4`
- Minor：`0`
- Decision：`CHANGES_REQUIRED`

#### Findings

- **I-1 — Approval consumption 与失败原子性（Important）**
  - Contract：审批消费、CAS intent、WP-11 验证、文件物化和 manifest version 必须组成 fail-closed 合同；失败不得返回可被误认为已经成功消费的状态。
  - Evidence：`consume_approval()` 先于 WP-11 专属 binding、源文件及物化校验执行；后续 `_denied()` 虽将 permitted/side-effect 改为 false，仍保留 consumed Approval 与新 revision。
  - Required remediation：调整组合顺序或结果合同，使任何 WP-11 验证/物化失败保持原 Approval revision 和未消费状态；不得修改、复制或弱化 WP-07 authority。若 WP-07 public contract 无法支持该原子组合，必须重新暂停并进行接口裁决。
  - Test gap：现有 tests 未断言消费成功之后的 WP-11 binding/materialization failure 不返回 consumed record/CAS intent。
- **I-2 — 文件副作用失败原子性（Important）**
  - Contract：任一物化失败不得残留本次创建的文件或目录，不得推进 manifest，不得返回成功 workspace binding。
  - Evidence：`_write_copy()` 创建目录后存在直接 false-return 路径；写后内容比较为 false 时可能保留目标文件，现有清理路径未统一覆盖全部失败分支。
  - Required remediation：建立单一可验证的 cleanup/finalize 路径，清除本次创建的文件与目录；清理结果不确定时返回稳定 fail-closed cleanup 状态。
  - Test gap：现有 tests 只覆盖写入前拒绝，未覆盖部分目录/文件已创建后的失败与清理。
- **I-3 — SandboxInputManifest 完整绑定（Important）**
  - Contract：manifest identity/digest 必须完整绑定前序 manifest、consumed Approval revision/CAS intent、source metadata/content、mode 和 materialized workspace binding。
  - Evidence：当前 digest 只覆盖当前 identity、revision、baseline 和 entries，未覆盖前序 manifest identity/digest、Approval identity/revision 或 TaskWorkspace binding。
  - Required remediation：扩充 immutable manifest contract 和确定性 digest，加入前序版本、可信 approval consumption 及 workspace identity/binding，并验证任一字段漂移 fail closed。
  - Test gap：现有 version/digest tests 未覆盖上述绑定字段漂移或不同历史错误产生等价 identity 的情况。
- **I-4 — Path/file safety 与 bounded failure（Important）**
  - Contract：source/destination 必须保持 lexical/physical containment，抵抗 symlink/hardlink/path replacement/TOCTOU，且所有读取有界。
  - Evidence：source 中间目录采用 `lstat` 后再按路径打开，`O_NOFOLLOW` 只保护最终分量；未定义 hardlink 拒绝；destination 直接信任可构造的 `TaskWorkspace.root`，父目录检查存在替换窗口；写后 `Path.read_bytes()` 可能在竞争替换后无界读取。
  - Required remediation：采用 descriptor-relative no-follow traversal 或等价受控根机制，验证 workspace root authority/physical containment，明确 hardlink 策略，并以已打开 descriptor 进行有界写后验证。
  - Test gap：现有 tests 未覆盖中间目录替换、hardlink、伪造 workspace root、destination race 或写后无界替换。

#### Gate 与边界

- WP-11 当前不得进入 merge preparation，production 修复尚未获准。
- I-1 整改不得修改或复制 WP-07 Approval/Policy authority；如公共合同不足，必须先停止并裁决接口 ownership。
- 本次只记录 review，不修改 production/tests、冻结 `SPEC.md`/`PLAN.md`，不 stage、commit、push 或创建 PR。
- WP-12、WP-13、WP-14 均未开始。

### WP-11 Remediation Design Refinement 与 Red 准备审批

本段于 `2026-07-24 14:08:57 +0800 (Asia/Shanghai)` 同期记录 I-1～I-4 整改设计 refinement 及人工审批。当前四项 finding 仍为 open：I-1 Approval consumption 与失败原子性、I-2 文件副作用失败原子性、I-3 `SandboxInputManifest` 完整绑定、I-4 Path/file safety 与 bounded failure。

#### Interface decision

- 结论：`NO_INTERFACE_REDECISION_REQUIRED`。
- WP-07 `consume_approval` 返回 immutable consumed candidate 以及 previous/expected/new revision 构成的 CAS intent，不执行持久化。
- WP-11 可复用该既有 authority，在成功时返回 pending-persistence 组合结果；不得修改、复制或弱化 WP-07 Approval/Policy authority。

#### R-1 — Published-pending-commit

- 选择的成功语义为 `PUBLISHED_PENDING_COMMIT`：文件已经安全发布，但 candidate manifest 尚未 active，Approval CAS 尚未持久化。
- 结果必须明确 `persistence_committed=false`、`active_manifest=None`；提交成功前，candidate manifest 不得用于 Agent execution、ChangeSet 或 export。
- 后续 CAS 失败由 WP-23 按冻结错误语义 `PERSISTENCE_AFTER_SIDE_EFFECT_FAILED → RECOVERY_REQUIRED` 处理；不得把 CAS intent 描述为已经持久化消费。

#### R-2 — Exact no-clobber mechanism

- 在目标同目录创建 owned temporary file，使用 descriptor-based bounded write、digest/metadata verification、权限设置与 fsync。
- 持有 parent directory fd，通过 `os.link()` 从 temporary name 创建 target；target 已存在时必须失败且不得覆盖既有 inode/content。
- 所需 dir-fd/no-follow/link 原语不可用的平台确定性 fail closed；不得退化到 `replace` 或可能覆盖目标的 `rename` 语义。
- 本次创建的 temporary、target link 与目录必须有精确 ownership receipt 并逆序清理；不得删除调用前已存在路径。

#### R-3 — Identity/digest/runtime split

- `expected_manifest_identity` 在 Approval 创建前由 normalized request、task/Plan/baseline、workspace logical identity、前序 manifest、next revision、entries/mode/stages/destination 和 idempotency key 确定性生成。
- Approval 冻结该 expected identity；trusted consumption candidate 产生后，actual `manifest_digest` 进一步绑定 Approval identity、Policy binding 和 CAS revisions。
- Runtime publication receipt 仅记录本次物理验证与 cleanup 所需的 fd/inode/dev/temporary/target 状态，不进入长期 identity。
- 固定合同：

  `candidate_manifest.identity == expected_manifest_identity`

  `candidate_manifest.digest == approval/CAS-bound digest`

- 明确禁止 `manifest_digest == expected_manifest_identity`；两者语义不同，构造顺序不形成循环依赖。

#### Approval 与下一阶段边界

- 人工结论：`APPROVED_FOR_REMEDIATION_RED_PREP`。
- 下一阶段仅允许进入 `WP11_REMEDIATION_RED`，且只允许修改 `tests/integration/workspace/test_ignored.py`；production remediation 仍未授权。
- I-1～I-4 尚未关闭；不得进入 merge preparation。
- WP-12～WP-15、WP-23 均未进入，冻结 `SPEC.md`/`PLAN.md` 保持不变。

### WP-11 Remediation Red 证据

本段于 `2026-07-24 14:21:42 +0800 (Asia/Shanghai)` 同期记录 I-1～I-4 整改回归测试的合法 Red；production remediation 尚未授权。

#### VERIFIED

- `tests/integration/workspace/test_ignored.py` collect-only 成功：`61 collected / 0 collection errors`。
- 原有 WP-11 tests 为 `37 passed`，无旧测试回归。
- 新增整改 tests 为 `24` 个，完整执行结果为 `37 passed / 24 failed / 0 errors`。
- 新增节点分类为 `EXPECTED_RED = 24`、unexpected pass `0`、errors `0`。
- Finding 映射：I-1 为 `5` 个节点，I-2 为 `4` 个节点，I-3 为 `6` 个节点，I-4 为 `9` 个节点；四组新增节点均为 EXPECTED_RED。

#### Failure classification

- I-1：当前缺少 `PUBLISHED_PENDING_COMMIT`、candidate/active manifest 分离及精确 Approval CAS 组合合同。
- I-2：当前缺少本次调用创建对象的 cleanup ownership、完成状态和稳定 cleanup failure result。
- I-3：当前 manifest identity/digest 未完整绑定前序 manifest、Approval CAS intent 和 workspace logical binding。
- I-4：当前未实现 descriptor-relative traversal、明确 hardlink policy、approved-size bounded I/O 和 `os.link()` no-clobber publication。

#### Boundary

- 本次仅修改 WP-11 test owner 文件；production、WP-07、WP-09、WP-10、冻结 `SPEC.md`/`PLAN.md` 均未修改。
- I-1～I-4 仍保持 open；合法 Red 不表示 finding 已关闭。
- Production remediation 尚未授权，未进入 WP-12～WP-15 或 WP-23。
- 当前状态：`WP11_REMEDIATION_RED_EXECUTION_COMPLETE`。

### WP-11 第一次 Remediation Security/Specification Re-review

本段于 `2026-07-24 14:44:48 +0800 (Asia/Shanghai)` 同期记录对 review base `a5fea62e031b4692105bb12c8f3a2d551ac7b7fb` 之未提交整改实现的第一次只读定向复审。Dirty production diff 精确为 `src/coding_harness/workspace/ignored.py`。新鲜验证为 WP-11 `61 passed`，WP-07/WP-09/WP-10 定向回归 `253 passed`；测试通过不替代源码控制流与安全合同审查。

#### Finding closure

- **I-1 — Approval consumption 与失败原子性：CLOSED**
  - 成功结果明确为 `PUBLISHED_PENDING_COMMIT`，分别返回 trusted consumed candidate、精确 Approval CAS intent 和 candidate manifest；`active_manifest=None`、`persistence_committed=false`，未声称 CAS 已提交。
  - 失败结果返回原 current Approval 并保持原 revision，不暴露 consumed candidate、CAS intent 或 candidate manifest，也不返回成功 publication state。

#### Open findings

- **I-2 — 文件副作用失败原子性：OPEN**
  - Cleanup ledger 仅使用 `Path`/name，未为每个 owned object 保存并在删除前复核 parent/name/dev/inode。
  - `ENOTEMPTY` 被当作 cleanup complete；descriptor close 异常被静默忽略。
  - 残余风险为遗留本次创建的 owned object，或删除竞争替换后的同名非 owned 对象。
- **I-3 — SandboxInputManifest 完整绑定：OPEN**
  - Genesis `expected_manifest_identity` 直接采用 `approval.sandbox_manifest_identity`，未由 WP-11 从稳定规范化字段确定性构造。
  - 当前只能证明 Approval 提供了某个 identity 值，不能证明该值完整绑定 task、PlanVersion、baseline 与 ordered entries。
- **I-4 — Path/file safety 与 bounded failure：OPEN**
  - Source root fd 在初次检查后关闭，后续按路径重新打开；ignore/source validation 仍包含路径式操作。
  - 发布后仍使用路径式 `os.chmod(target_path)`；cleanup 仍使用路径式 `target.unlink()`、`directory.rmdir()`，辅助检查仍使用 `os.lstat(path)`，尚未由 parent fd 与 dev/inode ownership 完整约束。
  - 因此仍存在 source root、published target 或 cleanup object 被替换的窗口。

#### Unsafe API search

- 未发现 `Path.read_bytes()`、`Path.write_bytes()`、`Path.replace()`、`shutil.copy*`、`shutil.rmtree()`、`os.rename()` 或 `os.replace()`。
- 仍存在需整改的路径式 `target.unlink()`、`directory.rmdir()`、`os.chmod(target_path)` 和辅助 `os.lstat(path)`。

#### Gate 与边界

- Original findings closed：`1`；Original findings open：`3`。
- New Critical：`0`；New Important：`0`；New Minor：`0`。
- Decision：`CHANGES_REQUIRED`。
- 当前 `ignored.py` 不得提交；I-1 后续不得进行无关重构。
- I-2～I-4 需要第二轮定向 Red；第二轮 production remediation 尚未授权。
- 本次仅记录复审，不修改 production/tests、WP-07/WP-09/WP-10 或冻结 `SPEC.md`/`PLAN.md`，不 stage、commit、push、创建 PR 或进入 WP-12。

### WP-11 第二轮 Residual Red 证据

本段于 `2026-07-24 15:05:50 +0800 (Asia/Shanghai)` 同期记录 I-2～I-4 第二轮 residual regression tests 的合法 Red；I-1 保持 CLOSED，round-2 production remediation 尚未授权。

#### VERIFIED

- `tests/integration/workspace/test_ignored.py` collect-only 成功：`82 collected / 0 collection errors`。
- 原有 WP-11 tests 为 `61 passed`，无旧测试回归。
- 新增 residual tests 为 `21` 个，完整执行结果为 `61 passed / 21 failed / 0 errors`。
- 新增节点分类为 `EXPECTED_RED = 21`、unexpected pass `0`、errors `0`。
- Finding 映射完整：I-2 为 `4` 个 EXPECTED_RED，I-3 为 `11` 个 EXPECTED_RED，I-4 为 `6` 个 EXPECTED_RED。

#### Failure classification

- **I-2 — OPEN**：cleanup ledger 缺少 dev/inode ownership 证明；`ENOTEMPTY` 与 descriptor close failure 的完成状态不正确；路径替换后仍可能误删非 owned 同名对象。
- **I-3 — OPEN**：genesis `expected_manifest_identity` 尚未由稳定规范化字段确定性构造；Approval 提供的 identity 仍可能成为事实来源；task、PlanVersion、baseline、source、mode、destination 与 idempotency 等 stable-field binding 不完整。
- **I-4 — OPEN**：descriptor authority 生命周期不连续；source/ignore validation 仍存在路径式重建；post-publish chmod 与 cleanup 仍可能作用于竞争替换后的 inode。

#### Boundary

- I-1 保持 CLOSED；I-2、I-3、I-4 仍为 OPEN，合法 residual Red 不表示 finding 已关闭。
- 本轮新增 Red 时 production 未变化；既有 `src/coding_harness/workspace/ignored.py` 第一轮 remediation working diff 保持未提交，其 diff SHA-256 指纹仍为 `d1fb1e9d68fe18613853b622bec8711d25f878c1d845b4f3cce305af552293b8`。
- Round-2 production remediation 尚未授权；未进入 PR 或 WP-12，未修改 WP-07、WP-09、WP-10 或冻结 `SPEC.md`/`PLAN.md`。
- 当前状态：`WP11_RESIDUAL_RED_EXECUTION_COMPLETE`。

### WP-11 Residual Test Contract Conflict 与合法停止

本段于 `2026-07-24 15:25:24 +0800 (Asia/Shanghai)` 同期记录第二轮 production remediation 开始前发现的测试合同冲突。停止状态为 `STOPPED_FOR_WP11_RESIDUAL_TEST_CONTRACT_CONFLICT`；本次停止不授权弱化 production security。

#### I-3 conflict

- 部分既有测试将任意字符串 `sandbox-manifest:1`、`sandbox-manifest:genesis`、`sandbox-manifest:next` 作为 Approval 的 sandbox manifest identity，同时要求 WP-11 从稳定请求字段独立、确定性计算 expected identity。
- 两项要求无法同时成立，除非实现继续将 Approval 值作为 identity 事实来源，或对测试字符串进行硬编码；两种做法均违反已冻结的整改设计。
- 正确合同为：

  `computed_expected_identity = deterministic stable-request hash`

  `approval.sandbox_manifest_identity = approval-frozen expected identity`

  `computed_expected_identity == approval.sandbox_manifest_identity`

- Approval revision 漂移不得重写 computed expected identity；对应测试必须使用规范计算出的 expected identity，而不是任意调用方字符串。

#### I-4 conflict

- 部分既有测试通过 monkeypatch 路径式 `os.chmod(target_path)` 注入失败或路径替换，并要求该不安全 API 实际执行。
- 整改合同要求移除发布后的路径式 chmod，改为发布前对 owned temporary descriptor 执行 `os.fchmod()`。
- 测试不得以不安全 API 被调用作为成功前提；后续获批修订应在 descriptor-safe 原语上注入失败，或断言竞争替换对象的 mode/content 均未被修改。

#### Classification、完整性与 gate

- 该问题分类为 test contract defect，不是允许弱化 production security；当前 `82` 项测试不能全部继续视为冻结的正确合同。
- 后续仅冲突节点可在明确审批后修订；未冲突测试继续保持冻结。
- I-1 保持 CLOSED；I-2、I-3、I-4 保持 OPEN。Round-2 production remediation 暂停，未进入 PR 或 WP-12。
- 既有 `src/coding_harness/workspace/ignored.py` working diff 不得丢失、reset、stash、stage 或提交；其当前 diff SHA-256 指纹为 `d1fb1e9d68fe18613853b622bec8711d25f878c1d845b4f3cce305af552293b8`。
- `tests/integration/workspace/test_ignored.py` 当前 SHA-256 为 `9eb659dbc95b2017d23eba0f57a7e41cbbdb3ccbb0f880d0862bb6fe8a4e28ce`。
- 本次仅记录冲突和合法停止事件，不修改 production/tests、WP-07/WP-09/WP-10 或冻结 `SPEC.md`/`PLAN.md`。

### WP-11 Identity Algorithm 与 Stage Set 人工裁决

本段于 `2026-07-24 16:07:22 +0800 (Asia/Shanghai)` 同期记录人工裁决 `IDENTITY_ALGORITHM_APPROVED`。接口结论保持 `NO_INTERFACE_REDECISION_REQUIRED`；本次只批准 identity v1 与 stage-set 合同，不授权修改 tests 或继续 production remediation。

#### 唯一 Identity v1

- WP-11 采用 typed length-prefixed binary canonical encoding、SHA-256 和恰好 `64` 个 lowercase hexadecimal 字符输出。
- 当前只支持唯一固定 schema v1；builder 与 gateway 均不接受调用方提供的 algorithm/schema version。Approval 通过冻结 v1 计算出的 expected identity 间接绑定算法；当前不新增或声称已有独立 schema-version 字段，不修改 WP-07 Approval 公共合同。
- Future v2 必须重新进行 identity migration/interface/security decision；当前不支持多版本并存、自动 downgrade 或 fallback。
- 三个独立 domain 为：
  - `coding-harness:workspace-logical-identity`
  - `coding-harness:sandbox-input-expected-identity`
  - `coding-harness:sandbox-input-manifest-digest`

#### Canonical binary grammar

- `VarUInt` 为最短形式的 canonical unsigned LEB128。
- `TypedValue := TypeCode || VarUInt(payload_length) || payload`。
- `Field := VarUInt(field_tag) || TypedValue`。
- `StructPayload := VarUInt(field_count) || Field[0] || ... || Field[n-1]`。
- `ListPayload := VarUInt(element_count) || TypedValue[0] || ... || TypedValue[n-1]`。
- `OptionalPayload := 0x00 | 0x01 || TypedValue`。
- `VariantPayload := VarUInt(variant_tag) || TypedValue`；genesis 使用独立 tagged variant，不使用普通字符串 sentinel。
- Struct field tags 必须严格递增；duplicate、missing、unknown 或 out-of-order tag 均 fail closed。Digest payload 固定为 `32` raw bytes，boolean payload 固定为 `1` byte；所有 nested payload 均受外层长度约束，decoder 必须拒绝 trailing bytes。相同抽象输入只能产生唯一 canonical byte stream。

#### RepoPath、Unicode、Destination 与 Stage Set

- RepoPath 仅复用 WP-09 public canonical validation，并编码 `RepoPath.canonical` 的 exact strict UTF-8 bytes；WP-11 不追加 normalization 或路径字符限制，不接受 bytes、隐式转换或 OS path。
- 普通 identifier 必须是非空 `str` 且可 strict UTF-8 编码；WP-11 不静默 normalization，identity 绑定 exact code-point/UTF-8 sequence，并仅复用所属 public contract 的字符限制。
- `destination_repo_path` 固定派生为 TaskWorkspace namespace 中与 source 相同的 canonical RepoPath；builder 自行派生，调用方不得覆盖。Source 与 destination 即使文本相同也使用不同 field tag。
- 批准 stage set `S2 = {EXECUTING, VERIFYING}`。每个 entry 的合法 canonical `allowed_stages` 仅为 `("EXECUTING",)` 或 `("EXECUTING", "VERIFYING")`；必须包含 `EXECUTING`，`VERIFYING` 可选。Token 为大小写敏感的 uppercase ASCII，按 ASCII bytes 排序；duplicate、unknown token fail closed。
- 运行时 `TaskState` 扩展不得自动扩展 v1；任何新 stage 必须经过新 schema/security decision。

#### Public pure builder 与 identity layering

- 批准 WP-11 public pure builder `compute_expected_manifest_identity(...)`。其职责仅限输入 validation、normalization、workspace logical identity 计算、destination derivation 和 expected identity computation。
- Builder 不得 consume Approval、决定 Policy、创建 CAS intent、materialize 文件或返回 authorization state；它不创建新的 WP-07 authority 类型。
- 固定分层：

  `candidate_manifest.identity == expected_manifest_identity`

  `candidate_manifest.digest == approval/CAS-bound manifest digest`

- Expected identity 与 candidate manifest digest 使用不同 domain 和字段集，不得相等或互换；expected identity 只绑定审批前稳定请求，manifest digest 进一步绑定 Approval/CAS、Policy、immutable exclusion flags 与 ordered manifest entries。

#### Vectors、findings 与 gate

- Genesis minimal、genesis multi-entry/multi-stage、continuation 和 stable-field mutation 四类 vector 输入计划获批。
- Exact vector digest 尚未生成或冻结；后续必须由 encoder A、independent oracle B 和 annotated byte-stream review 三方一致后才能冻结进 tests/process evidence，production builder 不得作为自身 oracle。
- I-1 保持 `CLOSED`；I-2、I-3、I-4 保持 `OPEN`。
- Test-contract revision 尚未开始，production remediation 保持暂停；未进入 PR 或 WP-12。
- 本次不修改 production/tests、WP-07/WP-09/WP-10 或冻结 `SPEC.md`/`PLAN.md`，不生成 vector digest，不 stage、commit 或 push。

### WP-11 Identity v1 规范向量证据冻结

本段于 `2026-07-24 16:53:07 +0800 (Asia/Shanghai)` 同期记录 `WP11_NORMATIVE_VECTOR_EVIDENCE_FREEZE`。候选审查裁决为 `CANDIDATE_DIGESTS_APPROVED`；本次只把批准的 exact values 与 Vector 1 annotation 固化为证据，不修改测试合同或 production builder。

#### 冻结文件与来源

- 规范向量证据容器：`tests/fixtures/workspace/wp11_identity_v1_vectors.json`。
- Vector 1 人工审查证据：`tests/fixtures/workspace/wp11_identity_v1_vector1.annotated.txt`。
- Candidate input SHA-256：`aa2cee0e4c2c3daaf508f6be9421d4597ee2e52dc98d256a984dd262f837066d`。
- Encoder A SHA-256：`89b3e6cc65eb6bf50ce802ddd8a78b10bf435c293e9723aed22020623f5f9d9b`。
- Independent Oracle B SHA-256：`2eb1d38cb13280f2a5cc03c3ae046f948c42de42cc8f28bbc706b1fe24217d26`。
- JSON 仅为 evidence container，不是 identity canonical serialization；`derived` 明确为 audit evidence only、not builder input。

#### Frozen exact values

| Vector | Workspace stream length | `workspace_logical_identity` | Expected stream length | `expected_manifest_identity` |
|---|---:|---|---:|---|
| `genesis-minimal` | 119 | `38e94d8a651e0f6c14637741c6fcbcac7ec22aad68fa88076b331ac1dcaf987f` | 332 | `e6afddcfd83e130635dafb4b54c403b56fb1f70919d70e52708670d614b776f5` |
| `genesis-multi` | 117 | `8d6857d6a53fa3ec4edc7bca6891ee81a030f29b808ee2b83c55f6b2cb67cf27` | 471 | `aed196b5b8ea7e9420b414e8a4dd4e72b4e48ac5f1dfecb3ec2bb1972fcda5b5` |
| `continuation-single-entry` | 124 | `86ac0d68835aef7c600926f39da547a422b16ac49e67b5b5496b32821c631bc0` | 409 | `8c00a0f8331c19de2ea4a9d282c4aeaec444f7436848ae3419ce10e464d915f9` |

#### Review evidence 与边界

- Encoder A 与独立 Oracle B 的三个 base vectors、十三个合法 mutations 均为 byte-for-byte `PASS`；Vector 1 人工 byte-stream/offset review 为 `PASS`。
- Validation-limit non-binding 为 `PASS`；二十二个 abstract invalid 均 fail-before-hash 且不产生 stream/digest；五个 fixture-conformance invalid 由 comparison/reviewer 层检查。
- Decoder conformance 为 `DEFERRED_TO_DECODER_CONFORMANCE_TESTS`、`OUT_OF_SCOPE_FOR_VECTOR_FREEZE`，不得据此声称 wire-invalid 已验证。
- Reproducibility rerun 为 `DEFERRED`，原因是 candidate scripts 不支持 non-overwriting output root；该延期不等于 reproducibility `PASS`。
- Candidate scripts 本身不进入仓库。本次冻结不开始 test-contract revision，不继续 production remediation；I-1 保持 `CLOSED`，I-2、I-3、I-4 保持 `OPEN`，未进入 PR 或 WP-12。

### WP-11 Public Identity Builder Interface 人工裁决

本段于 `2026-07-24 17:17:25 +0800 (Asia/Shanghai)` 同期记录人工裁决 `WP11_PUBLIC_BUILDER_INTERFACE_APPROVED`。接口结果为 `NO_INTERFACE_REDECISION_REQUIRED`；本次只冻结 public identity builder 的最小公共接口，不恢复 test-contract revision，也不授权 production remediation。

#### Signature、Request 与 Previous Reference

- 批准唯一签名：

  ```python
  def compute_expected_manifest_identity(
      request: ExpectedManifestIdentityRequest,
  ) -> ExpectedManifestIdentityResult:
      ...
  ```

- 函数只接受单一 `ExpectedManifestIdentityRequest`；固定使用 identity v1，不接受 version/schema 参数。非精确 request 类型 fail closed。函数必须 pure、deterministic，不承担 Approval、Policy、CAS 或 filesystem authority。
- `ExpectedManifestIdentityRequest` 为 `@dataclass(frozen=True, slots=True)`，字段精确为：
  - `task_id: str`
  - `plan_version_identity: str`
  - `baseline_digest: str`
  - `previous_manifest: PreviousSandboxInputManifestRef | None`
  - `new_revision: int`
  - `entries: tuple[ExpectedManifestEntry, ...]`
  - `idempotency_key: str`
  - `max_input_count: int`
  - `max_input_bytes: int`
- `entries` 必须为精确 tuple。Request 不接受 caller-supplied destination、workspace identity、expected identity、Approval、Policy 或 CAS intent；validation limits 不进入 identity，builder 不修改输入。
- `PreviousSandboxInputManifestRef` 为不可变、slots 类型，字段为 `revision: int`、`identity: str`、`digest: str`。`None` 是唯一 genesis 表示，ref 表示 continuation；revision 必须为正的精确 int且拒绝 bool，identity/digest 必须是 `64` lowercase hex，`new_revision == previous.revision + 1`。
- Builder 不验证 previous ref 是否对应当前 active manifest；currentness 由 gateway/Approval/CAS 验证，该引用不依赖 WP-23。

#### Entry、Identifier 与 Limits

- `ExpectedManifestEntry` 为不可变、slots 类型，字段为：
  - `source: RepoPath`
  - `kind: IgnoredInputKind`
  - `approved_size: int`
  - `content_digest: str`
  - `mode: IgnoredInputMode`
  - `allowed_stages: tuple[str, ...]`
- V1 的 kind 仅允许 `REGULAR_FILE`；approved size 必须为非负精确 int并拒绝 bool。Stage 必须为 tuple 且仅允许 `("EXECUTING",)` 或 `("EXECUTING", "VERIFYING")`；list、reversed、duplicate 或 unknown stage 均 fail closed。Destination 从 source 派生，duplicate source fail closed。
- Required identifier 必须为非空 `str` 且可 strict UTF-8 编码。WP-11 不静默 normalization，只复用 identifier 所属 public contract 已有的字符限制，不无条件新增 NUL 或 Unicode 字符禁令；exact UTF-8 sequence 进入 identity。
- `max_input_count` 与 `max_input_bytes` 必须为非负精确 int，拒绝 bool；`0` 合法。二者只约束当前 request，只参与 validation，不进入 identity。非法 limit 使用 `INVALID_LIMIT`，实际超限分别使用 `COUNT_LIMIT_EXCEEDED` 与 `BYTE_LIMIT_EXCEEDED`。

#### Result、Failure Contract 与 Public Exports

- `ExpectedManifestIdentityResult` 为不可变、slots 类型，仅包含：
  - `workspace_logical_identity: str`
  - `expected_manifest_identity: str`
- Result 不返回 normalized entries、destination、canonical bytes、authorization、Approval/CAS、manifest、runtime receipt 或任何 filesystem authority。
- 公共异常为 `ExpectedManifestIdentityError(ValueError)`，其稳定字段为 `reason: ExpectedManifestIdentityReason`。最终 reason set 为：
  - `INVALID_REQUEST`
  - `INVALID_IDENTIFIER`
  - `INVALID_DIGEST`
  - `INVALID_REPO_PATH`
  - `INVALID_ENTRY_TYPE`
  - `INVALID_MODE`
  - `INVALID_STAGE_SET`
  - `DUPLICATE_SOURCE`
  - `INVALID_SIZE`
  - `INVALID_LIMIT`
  - `INVALID_REVISION`
  - `INVALID_PREVIOUS_MANIFEST`
  - `COUNT_LIMIT_EXCEEDED`
  - `BYTE_LIMIT_EXCEEDED`
- Reason 是稳定测试合同；message 非稳定且不得泄漏文件内容、secret、绝对路径或底层异常。所有失败必须 fail before hash，不返回部分 result、不修改输入，也不进行 filesystem、Approval、Policy 或 CAS 操作。
- 从 `coding_harness.workspace.ignored` 公开：
  - `compute_expected_manifest_identity`
  - `ExpectedManifestIdentityRequest`
  - `ExpectedManifestEntry`
  - `PreviousSandboxInputManifestRef`
  - `ExpectedManifestIdentityResult`
  - `ExpectedManifestIdentityError`
  - `ExpectedManifestIdentityReason`
- 不新建 `coding_harness.workspace.__init__`，也不公开 encoder、canonical byte stream helper 或 authorization state。

#### Frozen Vector Mapping 与 Gate

- Frozen fixture 的 `input` 无歧义映射为 request；`derived` 仅为 audit evidence，不是 builder input；`expected.workspace_logical_identity` 与 `expected.expected_manifest_identity` 分别映射到 result 的同名字段。
- `genesis-minimal`、`genesis-multi` 与 `continuation-single-entry` 三个 base vector 均适用上述映射。Destination 由 source 派生；validation limits 仅用于校验。
- 当前状态：public builder interface `APPROVED`；identity algorithm v1 `APPROVED`；normative vectors `FROZEN / REMOTE-SYNCED`；test-contract revision 仍为 `PAUSED`，production remediation 仍为 `PAUSED`。
- I-1 保持 `CLOSED`；I-2、I-3、I-4 保持 `OPEN`。本次未修改 production/tests、frozen fixtures 或冻结 `SPEC.md`/`PLAN.md`，未进入 PR 或 WP-12。

### WP-11 最终关闭记录

本段于 `2026-07-26 12:41:39 +0800 (Asia/Shanghai)` 同期记录 WP-11 最终实现、验证与远程同步结果。最终 commit 为 `deff0382a64b67859090891de1f95b9988d30bfd`，commit subject 为 `fix(workspace): implement WP11 manifest digest v1`；本地与 `origin/wp-11-ignored-input-governance` 均指向该 commit，工作区 clean。状态明确更新为：

`WP11 CLOSED`

#### Finding closure

- **I-1 — Approval consumption 与失败原子性：CLOSED。** 成功结果保持 `PUBLISHED_PENDING_COMMIT`，明确分离 consumed candidate、Approval CAS intent 与 candidate manifest；`active_manifest=None` 且 `persistence_committed=False`。失败路径不暴露 consumed candidate，并保持原 Approval/revision。WP-07 Approval/CAS authority 未被复制或修改。
- **I-2 — 文件副作用与 cleanup ownership：CLOSED。** Cleanup 使用 owned receipt 绑定并在删除前复核 object type、device 与 inode；cleanup failure 独立、稳定地传播且不覆盖 primary operation reason，descriptor close failure 不伪装为成功。
- **I-3 — Identity 与 manifest digest 完整绑定：CLOSED。** Public expected-identity builder 使用批准的 identity v1；candidate identity 与 manifest digest 保持分层。Manifest digest 使用 `coding-harness:sandbox-input-manifest-digest`、schema v1 和批准的 typed length-prefixed canonical binary encoding，绑定 identity、revision、baseline digest、Approval CAS intent digest、workspace logical identity、immutable exclusion flags 与 canonical ordered full entry set；旧 v2 domain 与 fallback 均不存在。
- **I-4 — Path/file safety 与 bounded failure：CLOSED。** Descriptor authority、bounded I/O、source/target physical verification、owned temporary、`os.link()` no-clobber publication、替换竞争检测与 unsupported-platform fail-closed 合同均由 WP-11 regression nodes 覆盖；未退化为覆盖式 rename/replace 或路径式安全关键 publish。

#### Verification evidence

- Frozen manifest digest v1 vectors 三项 exact match：
  - `genesis-minimal`：`af25dfe44494a5689c09364242261ebe066e441fc648d3a978eca23ab7f0e0ed`
  - `genesis-multi`：`35acc09a22c9ea553486ca13df145ede3301a301f564ec47a91b6bbae6e7c4e5`
  - `continuation-single-entry`：`5503b9f1b4d02d3e6143f2ae69d3e9641d930e0ea9759148ff9905a74077fd8e`
- Fixture strict validation：`1 passed`；duplicate key、非法 UTF-8、NaN/Infinity、schema、stream length、SHA-256、offset partition、mutation coverage、ordering invariance 与 provenance 均受验证。
- WP-11 integration suite：`85 passed / 0 failed / 0 errors`。
- WP-07/WP-09/WP-10 定向 cross regression：`253 passed / 0 failed / 0 errors`。
- `git diff --check` 通过；未生成 cache 或 bytecode。

#### 实现范围与非修改边界

- 最终 closure commit 精确包含：
  - `src/coding_harness/workspace/ignored.py`
  - `tests/integration/workspace/test_ignored.py`
  - `tests/fixtures/workspace/wp11_manifest_digest_v1_*`
  - `tests/unit/workspace/test_wp11_manifest_digest_fixture.py`
- WP-11 保持既定 ownership：ignored-input governance、manifest/version、approved materialization gateway、identity/digest binding、non-export/non-writeback 与 filesystem safety。
- 未修改 `SPEC.md`、`PLAN.md`、WP-07 Approval/Policy authority、WP-09 path/file model、WP-10 baseline authority或任何 WP-12+ 文件；未进入 WP-12。
- 本记录只关闭 WP-11，不声称 WP-23 persistence orchestration 已实现，也不改变既有 Requirement/PV ownership。
