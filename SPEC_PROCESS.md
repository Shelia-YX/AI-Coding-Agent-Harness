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
