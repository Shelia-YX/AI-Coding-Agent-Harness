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

## WP-12 Interface Authority Freeze 批准与工作环境初始化

本段于 `2026-07-26 13:40:03 +0800 (Asia/Shanghai)` 同期记录 `WP12_INTERFACE_AUTHORITY_FREEZE_APPROVED` 及其独立工作环境初始化。人工权威方明确批准 `WP12_ACTIVE_MANIFEST_AUTHORITY_DECISION` 与 `WP12_SYNTHETIC_BASELINE_ANCHOR_DECISION`【USER_REPORTED / APPROVED DECISION】。本段只冻结跨 WP interface/security authority boundary，不修改冻结 `SPEC.md`/`PLAN.md` 的 Requirement/PV 语义，也不声称任何 WP-12、WP-15 或 WP-23 production interface 已实现。

### Approved ACTIVE Manifest Authority boundary

- ACTIVE Sandbox Input Manifest 的唯一 authority 类型冻结为 `PersistedActiveManifestAuthority`。
- WP-15 `HarnessStore` 拥有 authoritative persistence record 与 authority issuance boundary；WP-23 `TaskService` 仅拥有 application orchestration，不得自行声明、构造、恢复或由 cache 推断 ACTIVE。
- `PersistedActiveManifestAuthority` 必须来自 WP-15 对 current authoritative persistence record 的 trusted reread，并保持 task identity、workspace logical identity、WP-10 Baseline binding、manifest identity/digest/revision、Approval committed-consumption/CAS intent binding、persistence record identity及 currentness 一致。
- 类型名称、caller flag、caller-declared active、`SandboxInputManifest` 参数、candidate manifest、materialization result、manifest/CAS digest、publication receipt、workspace 文件存在性、memory cache、snapshot、SSE 或临时日志均不得产生 ACTIVE authority。
- `PUBLISHED_PENDING_COMMIT` 不是 ACTIVE，不携带 execution、Synthetic Git、ChangeSet、export、Apply 或 Recovery authority；它不得通过字段修改、状态转换、对象包装或复用原结果直接进入 ACTIVE。
- persistence operation 后仍须通过 trusted reread 产生新的 verified authority。consumer 只能消费 verified authority；persistence 不可用、记录缺失、binding 不一致、状态陈旧或 commit 无法证明时必须表现为无 ACTIVE authority并 fail closed。
- SQLite schema、transaction 字段、CAS 算法、migration/version、具体 Store/Application API、audit event payload及 recovery algorithm 不属于本次 WP-12 freeze，分别由后续 WP-15/WP-23 owner 在不弱化上述安全结果的前提下决定。

### Approved Synthetic Baseline Anchor boundary

- Synthetic Baseline Anchor 冻结为 Harness internal、immutable、task-local、non-authoritative compatibility anchor；它不是 WP-10 `BaselineManifest`、Git truth、原仓库 HEAD/index/branch/commit/refs、当前 workspace authoritative snapshot 或 ACTIVE authority。
- Anchor 必须由可信 Harness 从现有、已验证的 WP-10 Baseline contract 及匹配 Task Workspace binding 建立。LLM、caller、当前 workspace 扫描、Synthetic Git 自身状态、cache、materialization result 与原仓库 `.git` 不得创建、替换或刷新 anchor。
- Anchor 与 Synthetic index 严格分离：anchor 不可变；闭合范围内的 stage/unstage 只影响 Synthetic index，不得改变 anchor、WP-10 Baseline Manifest、原仓库 index 或任何 authority。
- Synthetic Git 仅允许冻结 SPEC 闭合清单中的 status、worktree diff、cached diff 及精确文件级 stage/unstage。commit、branch、tag、remote、merge、reset、checkout、clean、通用 config、refs、history rewrite 与 worktree restoration 保持禁止；通用 `restore` 禁止，唯一例外为闭合 `git_unstage_paths` 对应的精确 `restore --staged`，且不得修改工作树。
- Synthetic anchor、index、objects、refs、hash 与命令输出仅是 compatibility feedback，不得成为 Approval、Manifest identity/digest、ChangeSet、Acceptance、Apply、Recovery 或 `PersistedActiveManifestAuthority` 的依据。
- Synthetic Git 不解释 persistence truth，不把 `PUBLISHED_PENDING_COMMIT` 提升为 ACTIVE，也不替代 trusted persistence reread。
- Synthetic Git storage、tree/object layout、index schema、内部锁/生命周期及 adapter 细节属于后续 WP-12 implementation；WP-13 ChangeSet 算法、WP-14/WP-18 recovery implementation、WP-15 persistence implementation与 WP-23 orchestration implementation保持各自既有 ownership。

### WP-10 frozen upstream dependency

- WP-10 状态冻结为 `COMPLETED / MERGED / FROZEN UPSTREAM CONTRACT`。
- 现有 `BaselineManifest`、`TaskWorkspace`、Baseline digest 与 workspace binding 是 WP-12 必须消费的既存上游 authority contract；WP-10 不是 future deferred implementation owner。
- WP-12 不得重开、复制、替代、重新解释或扩展 WP-10 Baseline authority，也不得把当前 workspace snapshot 提升为 authoritative Baseline。
- WP-12 不得依赖 WP-10 未公开的内部表示。若现有 public contract 无法满足已批准 anchor provenance，必须停止并发起新的 cross-WP interface decision，不得直接修改 WP-10。

### Worktree、branch 与 start gate

- 创建前主 checkout 为 branch `main`、worktree clean；目标 branch/worktree 均不存在，项目本地 `.worktrees/` 由 `.gitignore` 明确忽略【VERIFIED】。
- 刷新 `origin/main` 后，`FETCH_HEAD` 与 `origin/main` 均为 WP-11 PR #2 merge commit `3eb3c1318c5a18b01bafb7593fad79c82c839267`；本地 `main` `62cb3877118070b3b66abadcf474360bc7e7e9a3` 是其祖先。`SPEC.md`、`PLAN.md` 在该推进中无差异【VERIFIED】。
- 从 `origin/main` 创建 branch `wp-12-interface-authority-freeze` 及 worktree `.worktrees/wp-12-interface-authority-freeze`；新 worktree HEAD 为 `3eb3c1318c5a18b01bafb7593fad79c82c839267` 并跟踪 `origin/main`【VERIFIED】。
- 本初始化阶段的允许修改范围仅为 `AGENT_LOG.md` 与 `SPEC_PROCESS.md`。未创建 WP-12 Red tests，未创建或修改 `src/coding_harness/workspace/synthetic_git.py`，未修改任何 production/test、`SPEC.md` 或 `PLAN.md`，未 stage、未 commit。

### Conflict review 与下一阶段

- 冻结 SPEC 已明确 Synthetic Git non-authority、闭合 Git operation、WP-10 immutable Baseline/Task Workspace、Harness ChangeSet authority及 recovery/persistence边界；本次批准记录是对跨 WP interface ownership和禁止 authority shortcut 的澄清，不改变现有 Requirement/PV 语义。
- 当前未发现 approved decision 与冻结 SPEC/PLAN 的 ownership conflict 或 cross-WP contradiction；因此无需修改 `SPEC.md`。
- 状态：`WP12_INTERFACE_AUTHORITY_FREEZE_APPROVED / WORKSPACE_INITIALIZED`。
- 下一合法阶段仅为 `WP12_SYNTHETIC_GIT_RED_PREPARATION`。本批准和初始化不得直接进入 production implementation；Red 文件尚未创建，Red 命令尚未执行。

## WP-12 Synthetic Git governance evidence 与 closeout gate

本段于 `2026-07-27 11:34:18 +0800 (Asia/Shanghai)` 记录 WP-12 从 interface freeze 到 executable verification 的过程证据。记录依据为人工批准的 decision、当前 WP-12 artifacts 及已经完成的 verification evidence；本段不修改冻结 `SPEC.md`/`PLAN.md`，不扩展 WP-12 ownership，也不替代其他 WP 的实现或验证责任。当前状态为：

`WP12_CLOSEOUT_PREPARED = APPROVED`

`COMMIT = NOT AUTHORIZED`

### Decision timeline 与 freeze rationale

1. `WP12_ACTIVE_MANIFEST_AUTHORITY_DECISION` 与 `WP12_SYNTHETIC_BASELINE_ANCHOR_DECISION` 首先获批并冻结。前者隔离 persistence authority 与 orchestration；后者把 Synthetic Baseline 限定为 non-authoritative compatibility anchor。
2. Red preparation/review 发现：仅有 security invariants、没有 consumer-observable executable binding 时，测试会被迫冻结 constructor、signature、enum representation 或 result shape，或者以 fake authority/mock behavior 制造无效 Red。项目因此停止 test revision，重新进入 interface decision。
3. `WP12_SYNTHETIC_GIT_EXECUTABLE_INTERFACE_DECISION` 与 `WP12_SYNTHETIC_GIT_CONFORMANCE_BINDING_DECISION` 获批，冻结 acquisition、semantic invocation 与 observable outcome 的行为边界，但不冻结 constructor、factory、module location、enum serialization、result object 或 exception hierarchy。
4. Static binding 首次只能报告 `BINDING_NOT_READY`；该状态不能伪装成 production behavioral Red。随后 `WP12_SYNTHETIC_GIT_MINIMUM_PRODUCTION_BINDING_INTERFACE_DECISION` 与 `WP12_SYNTHETIC_GIT_MINIMUM_PRODUCTION_SURFACE_DECISION` 获批并冻结，明确 test-only binding 只做 static translation/normalization，真实 validation 与 behavior 必须来自 WP-12 production execution boundary。
5. `WP12_SYNTHETIC_GIT_IMPLEMENTATION_ENTRY_DECISION` 在 strict gate 下获批，仅授权满足上述 frozen surface 的有限 production implementation。之后完成 Static Test-only Binding Revision、Red Test Contract Correction、Behavioral Verification Review 与 Human Closeout Preparation。

该次重开 interface decision 的理由不是扩大功能，而是避免 executable evidence 依赖 implementation discovery、测试自造 authority 或 fixture 自行实现 security policy。最终 binding failure、unexpected internal failure、真实 operation rejection 三类结果保持分离。

### Approved ownership decisions

- WP-10 保持 `COMPLETED / MERGED / FROZEN UPSTREAM CONTRACT`，拥有 `BaselineManifest` authority 与 public `TaskWorkspace` binding contract。WP-12 只消费该 public contract并拒绝不满足其 frozen binding contract 的输入，不重新拥有 Baseline validation，不用 root path、object identity 或隐藏字段发明新的 workspace authority。
- WP-12 仅拥有 Synthetic Git internal compatibility surface：non-authoritative context、Synthetic Baseline Anchor、Synthetic index、closed operation execution 与 compatibility feedback。
- WP-15 拥有 authoritative persistence record 与 `PersistedActiveManifestAuthority` issuance boundary；ACTIVE 必须来自 trusted persistence reread。
- WP-23 仅拥有 application orchestration，不得声明、恢复、缓存推断或自行签发 ACTIVE。
- WP-13 保持 ChangeSet authority 与相关 verification ownership。
- WP-14/WP-18 保持 Recovery evidence、algorithm 与相关 verification ownership。

### Frozen security invariants

- Synthetic Baseline Anchor 是 immutable、task-local、non-authoritative compatibility anchor；它不是 WP-10 `BaselineManifest`、Git truth、workspace authoritative snapshot、ACTIVE、ChangeSet 或 Recovery authority。
- Anchor provenance 只可消费已验证 WP-10 Baseline 与 matching TaskWorkspace public binding。caller、LLM、workspace snapshot、Synthetic state、cache、materialization result 与 origin `.git` 均不得创建、替换或刷新 anchor。
- Synthetic index 与 anchor 分离；stage/unstage 只改变 index，不改变 anchor、worktree、origin index 或任何 authority。
- compatibility execution scope 的闭合 allowlist 仅包含 status、diff、cached diff、stage、unstage。commit、branch、tag、remote、merge、reset、checkout、worktree restore、history rewrite、clean、refs mutation、unsafe config/options、pathspec/glob magic及 range-style index operation必须拒绝。
- 拒绝路径必须保持 zero side effect；WP-12 不修改 origin repository Git state、不读取 WP-15 persistence、不调用 WP-23 orchestration。
- ACCEPTED、REJECTED 与 INTERNAL_FAILURE 必须可区分。Unexpected internal failure 不得被转换为 REJECTED；test binding 自身的 missing symbol、wiring/provider/translation/fixture failure只能报告 `BINDING_NOT_READY`，不得成为 production behavioral outcome。
- Synthetic hash、state 与 output 只能作为 compatibility feedback，不产生或证明 Approval、Manifest identity/digest、ACTIVE、ChangeSet 或 Recovery authority。

### Implementation scope 与 modified artifacts

- Production artifact：`src/coding_harness/workspace/synthetic_git.py`。
  - 提供从真实 WP-10 `BaselineManifest` 与 matching `TaskWorkspace` 到 opaque task-local compatibility context 的 acquisition boundary。
  - 提供 closed `GitOperation` semantic capabilities、`SyntheticGit.run` execution boundary、immutable anchor、separate mutable index，以及 ACCEPTED/REJECTED/INTERNAL_FAILURE observation channel。
  - 不引用 origin repository `.git`，不运行 Git subprocess，不读取 persistence，不产生跨 WP authority。
- Verification artifact：`tests/unit/workspace/test_synthetic_git.py`。
  - `wp12_synthetic_git_conformance` 是 test-only、non-authoritative static binding，不进入 production dependency graph。
  - Binding 使用单一路径连接真实 acquisition、operation translation、`SyntheticGit.run` 与 public outcome；不使用 runtime introspection、signature/constructor/factory discovery、enum name/value inference、result field discovery、fallback invocation、private injection、fake/mock context或 fixture-owned validation/allowlist/Git behavior。
- 本 governance recording 仅修改 `AGENT_LOG.md` 与 `SPEC_PROCESS.md`；未修改上述 production/test artifacts、`SPEC.md`、`PLAN.md` 或任何其他 WP-owned file。

### Executable verification evidence

| Evidence set | Result | Frozen contract coverage |
| --- | --- | --- |
| WP-12 collect/behavioral suite | `48 collected / 48 passed / 0 failed / 0 errors` | WP-10 provenance consumption、public workspace binding rejection、anchor immutability、workspace snapshot rejection、index/anchor separation、stage/unstage isolation、status/diff/cached diff semantics、closed allowlist、forbidden operation/unsafe option/path rejection及 rejection side-effect absence |
| Full regression | `626 passed / 1 deselected / 0 failed / 0 errors` | 当前 repository regression；被 deselect 的 clean-worktree process sentinel 在预期 dirty artifact 阶段不作为 product failure |
| Static quality | Ruff：`All checks passed` | 当前 WP-12 production/test artifact 的 static quality |
| Patch hygiene | `git diff --check`：通过 | whitespace/error gate |

以上为 closeout 前已经完成的 executable evidence【CONTEMPORANEOUS / VERIFIED BEFORE THIS RECORDING】。Process documentation 追加后必须重新执行 process-scope diff check；clean-worktree sentinel 只能在最终 commit 后重新成为适用的 cleanliness evidence。

### Rejected alternatives

- 拒绝以 caller boolean、caller-declared active、candidate/materialization result、digest、publication receipt、cache、snapshot、SSE、workspace 文件存在或 memory object产生 ACTIVE authority。
- 拒绝让 `PUBLISHED_PENDING_COMMIT` 通过字段修改、对象包装或直接状态跳转成为 ACTIVE。
- 拒绝以 workspace root、object identity、隐藏字段或当前 workspace snapshot推断 WP-10 未公开的 Baseline/Workspace authority。
- 拒绝用 constructor/factory/run signature probing、AST/source inspection、enum representation、result shape、exception message/type或 private state discovery建立 conformance。
- 拒绝 fake/mock context、test-defined production adapter、fixture-owned provenance/path validation、fixture-owned allowlist、fixture-owned Git behavior及 test-only production hook。
- 拒绝把 `BINDING_NOT_READY`、fixture execution failure或 unexpected internal failure归一化为真实 ACCEPTED/REJECTED。
- 拒绝 WP-12 接管 WP-15 persistence、WP-23 orchestration、WP-13 ChangeSet 或 WP-14/WP-18 Recovery ownership。

### Verification ownership separation 与 remaining cross-WP obligations

| Owner | Remaining obligation not claimed by WP-12 |
| --- | --- |
| WP-15 | 实现 authoritative persistence record、trusted reread、ACTIVE issuance/currentness，并验证 non-authoritative evidence 不能产生 `PersistedActiveManifestAuthority` |
| WP-23 | 实现 application orchestration，消费而不签发 ACTIVE，并验证 pending/materialization/cache/snapshot 不得绕过 WP-15 authority boundary |
| WP-13 | 实现并验证 ChangeSet authority；Synthetic Git output/state 不能直接成为 ChangeSet authority |
| WP-14/WP-18 | 实现并验证 Recovery evidence/algorithm；Synthetic state、anchor、index 与 compatibility feedback 不能替代 recovery evidence |

WP-12 executable verification 只证明自身 Synthetic Anchor 与 Synthetic Git compatibility/security boundary，不声称上述 cross-WP obligations 已完成。

### Closeout 与 commit entry gate

- WP-12 owned scope 的 decision、limited production surface、static binding、behavioral verification与 final evidence review均已完成；`WP12_CLOSEOUT_PREPARED = APPROVED`。
- 当前 expected WP-12 code artifacts 为 `src/coding_harness/workspace/synthetic_git.py` 与 `tests/unit/workspace/test_synthetic_git.py`；governance artifacts 为 `AGENT_LOG.md` 与 `SPEC_PROCESS.md`。
- 下一合法动作仅为 commit entry review。必须先确认 diff check、changed-file allowlist、无 staged/unrelated file、verification evidence 与 commit scope。
- 本记录不授权 stage、commit 或 push；`COMMIT = NOT AUTHORIZED` 保持不变。

## WP-12 final governance closeout record

本段于 `2026-07-27 12:03:23 +0800 (Asia/Shanghai)` 追加 WP-12 final governance closeout evidence。它不修改上述历史 decision wording，不重新打开任何 frozen interface decision，也不产生新的 implementation task。状态冻结为：

- `WP12_IMPLEMENTATION = PASS`
- `WP12_SECURITY_BOUNDARY = PASS`
- `WP12_VERIFICATION = PASS`
- `WP12_REMOTE_SYNCHRONIZATION = PASS`

### Final commit 与 remote evidence

- Final implementation commit：`c5bbce4b27faa93f12820bccae4f58cdca9640c8`。
- Local branch：`wp-12-interface-authority-freeze`。
- Remote branch：`origin/wp-12-interface-authority-freeze`。
- Local HEAD 与 remote branch ref 均为 `c5bbce4b27faa93f12820bccae4f58cdca9640c8`【VERIFIED】。
- Push 使用显式同名 remote ref；未 push `origin/main`，未 force push、rebase、merge、修改 upstream configuration 或创建 PR。

### Fresh final verification

- WP-12 suite：`48 passed / 0 failed / 0 errors`。
- Full regression：`627 passed / 0 failed / 0 errors`；此前 dirty phase deselect 的 clean-worktree sentinel 已在 committed clean state 纳入并通过。
- Candidate Ruff：`All checks passed`。
- Committed diff check：通过。
- Final review 前 working tree 与 generated-artifact scan：clean。

上述 fresh evidence 验证最终 committed tree；本段追加后 working tree 仅允许 `AGENT_LOG.md` 与 `SPEC_PROCESS.md` 出现 process-only diff，必须在独立授权前保持 unstaged、uncommitted、unpushed。

### Known limitations

- **Synthetic Git compatibility scope limitation：** WP-12 只提供 task-local、non-authoritative compatibility context、immutable anchor、separate synthetic index 与有限 semantic feedback；它不是完整 Git repository、Git truth、WP-10 `BaselineManifest` 或 workspace authority。
- **Unsupported Git operations：** closed allowlist 仅包含 status、diff、cached diff、stage、unstage。commit、branch、tag、remote、merge、reset、checkout、worktree restore、history rewrite、clean、refs mutation、unsafe options/pathspec magic及 range-style index operation保持按设计拒绝；这不是待补 implementation。
- **Compatibility feedback formatting limitation：** feedback 仅提供 bounded semantic path/added-line/removed-line facts，不承诺完整 Git textual output、patch formatting、ordering、object/hash representation或稳定 human-facing error message。Downstream 不得把 formatting 或 feedback 升格为 authority。
- **INTERNAL_FAILURE coverage limitation：** production boundary 提供独立 `INTERNAL_FAILURE` disposition，并保证 unexpected failure 不转换为 REJECTED；当前 executable suite 不包含 deterministic fault-injection test hook。为补此覆盖而新增 private injection、mock production、test-only production hook或冻结 exception/result representation均仍被禁止。

这些限制均位于已冻结 WP-12 compatibility boundary 内，不要求重开 interface decision，也不产生新的 WP-12 implementation task。

### Ownership separation retained

WP-12 final closeout 不声称、实现或验证完成以下 downstream-owned authority：

- ACTIVE Manifest Authority 与 authoritative persistence truth：WP-15 ownership。
- Application orchestration authority：WP-23 ownership。
- ChangeSet authority：WP-13 ownership。
- Recovery evidence 与 recovery algorithm：WP-14/WP-18 ownership。

Synthetic anchor、index、context、disposition、hash 与 compatibility feedback均不得成为上述 authority 的替代来源。Remaining cross-WP verification obligations继续适用前述 WP-15/WP-23、WP-13 与 WP-14/WP-18 分工。

### Final process gate

- WP-12 production implementation不需要额外修改；final governance documentation gap 已通过本追加记录关闭。
- 本阶段只修改 `AGENT_LOG.md` 与 `SPEC_PROCESS.md`，不修改 production、tests、`SPEC.md`、`PLAN.md` 或其他 WP-owned file。
- 本记录不授权 stage、commit、push、PR 或 merge。新的 process-only commit必须等待独立 explicit authorization。

## WP-12 post-merge process reconciliation

本段于 `2026-07-27 12:48:54 +0800 (Asia/Shanghai)` 追加 WP-12 manual merge sequencing deviation 的 reconciliation evidence。该记录只描述已经发生的外部 merge 与事后技术核验，不追溯性创建 merge authorization，不修改既有 decision、commit 或 branch history。

### Merge event

- PR #3 由人工于 `2026-07-27 12:41:35 +0800`、formal merge authorization review 完成前 merge。
- Merge commit：`40230f758ebd26f36b639487717675cf28da2032`。
- First parent：`3eb3c1318c5a18b01bafb7593fad79c82c839267`。
- Reviewed head / second parent：`e9cec8e07c46dd3db03f57e9f3a95afc5e4847bd`。
- Merge subject：`Merge pull request #3 from Shelia-YX/wp-12-interface-authority-freeze`。
- `MERGE_AUTHORIZATION_SEQUENCE = DEVIATION`。

### Merge content verification

- Merge tree：`5e951926fd96cc156d825e47c7314531acf3ccd3`。
- Reviewed head tree：`5e951926fd96cc156d825e47c7314531acf3ccd3`。
- Merge tree 与 reviewed head tree完全一致；reviewed head 到 merge commit 的 diff为空。
- 未发生 conflict-resolution change、merge-induced code change、extra file或 scope expansion。
- First-parent merge scope仍精确为：
  - `AGENT_LOG.md`
  - `SPEC_PROCESS.md`
  - `src/coding_harness/workspace/synthetic_git.py`
  - `tests/unit/workspace/test_synthetic_git.py`
- Reviewed commit sequence保持：
  - `3a1cdf1` — `docs(process): record WP12 interface authority freeze approval`
  - `c5bbce4` — `feat(workspace): implement WP12 synthetic git compatibility`
  - `e9cec8e` — `docs(process): record WP12 final closeout`

### Post-merge technical review

- Technical review在人工 merge 后完成，结论为 `PASS`；该结论验证实际 merge tree，但不替代缺失的 pre-merge authorization gate。
- Fresh WP-12 suite：`48 passed / 0 failed / 0 errors`。
- Fresh full regression：`627 passed / 0 failed / 0 errors`。
- Candidate Ruff：`All checks passed`。
- Merge commit check、working tree 与 generated-artifact scan均通过/clean。
- Frozen WP-12 contract、authority separation、known limitations 与 downstream obligations继续成立；没有新增 WP-12 implementation requirement。

### Governance reconciliation

- Formal merge authorization gate被人工 merge提前越过；该 sequencing deviation是已发生事实，必须保留。
- Technical correctness与 governance sequencing是两个独立结论：tree equality及 tests PASS证明 merge内容未漂移，但不能把 deviation改写为正常授权流程。
- 本 reconciliation不伪装为 pre-merge approval，不补造历史授权，不改写 timestamp、decision或 reviewer chronology。
- 未执行也不建议为隐藏 deviation而进行 revert、rebase、force push、squash、history rewrite或 branch-history修改。

最终状态：

- `WP12_IMPLEMENTATION = PASS`
- `WP12_VERIFICATION = PASS`
- `WP12_SECURITY_BOUNDARY = PASS`
- `WP12_PR_TECHNICAL_REVIEW = PASS`
- `WP12_MERGE_CONTENT = VERIFIED`
- `MERGE_AUTHORIZATION_SEQUENCE = DEVIATION`
- `WP12_TECHNICAL_CLOSEOUT = COMPLETE`
- `WP12_GOVERNANCE_RECONCILIATION = RECORDED`

### Reconciliation process gate

- 本阶段只追加 `AGENT_LOG.md` 与 `SPEC_PROCESS.md`，不修改 production、tests、`SPEC.md`、`PLAN.md` 或其他 WP-owned file。
- 本记录不授权 stage、commit、push、merge、revert、rebase或任何 history mutation。
- Reconciliation documentation commit必须等待独立 explicit authorization。

## [RETROSPECTIVE] WP-13 ChangeSet and Conflict Detection process record

### [RETROSPECTIVE] Status and gate transition

- [RETROSPECTIVE] WP-13 状态为 `COMPLETED / COMMITTED / MERGED`。start、Red、Green、review blocked、authority-boundary review fix 与 Final Review PASS 可由既有 `AGENT_LOG.md` 条目重建；独立 planning checkpoint 未同期保存【USER_REPORTED】。
- [RETROSPECTIVE] Git 证明 implementation commit `bfbc08137ee45d23e0506c0aa2d99689f0ae24be` 由 merge commit `7fa31a5bb038bebdfd08f16e547e4714c3c63e08` 合入 main，且当前 main ancestry 仍包含二者【VERIFIED】。

### [RETROSPECTIVE] Important decisions

- [RETROSPECTIVE] ChangeSet 只消费已有可信 `BaselineManifest` 与 `TaskWorkspace` snapshot；WP-13 不签发 persistence/ACTIVE authority【USER_REPORTED】。
- [RETROSPECTIVE] Git diff/status/history 不作为 ChangeSet 事务真相；unsupported concurrent target change 必须形成确定性 `ConflictReport`，冲突不自动 merge；workspace snapshot 受 files/bytes/depth 资源上限约束【USER_REPORTED】。
- [RETROSPECTIVE] Requirement scope 为 `TXN-005..008, TXN-017..018`【USER_REPORTED】。

### [RETROSPECTIVE] Verification and limitations

- [RETROSPECTIVE] 既有台账记录最终 WP-13 定向 suite 为 `34 passed`，但本补录不声称保存了当时完整原始终端输出【USER_REPORTED】。
- [RETROSPECTIVE] WP-15 merge 后当前 main 全量回归为 `757 passed in 29.89s`，并验证 WP-13 commit ancestry【VERIFIED】。
- [RETROSPECTIVE] `CONTENT_LIMIT_OR_READ_FAILURE` 的原因粒度与永久 directory-swap fault-injection coverage 是当时记录的非阻断限制【USER_REPORTED】。

### [RETROSPECTIVE] Final process gate

- [RETROSPECTIVE] `WP13_PROCESS_CLOSEOUT = RECOVERED`；本节仅恢复高层证据链，不改写同期历史，不授权任何 Git history mutation。

## [RETROSPECTIVE] WP-14 Apply Transaction / Rollback / Recovery process record

### [RETROSPECTIVE] Status and gate transition

- [RETROSPECTIVE] WP-14 状态为 `COMPLETED / COMMITTED / MERGED`。过程经历 start、spec ambiguity stop、人工 runtime-boundary decision、Red/Green、多轮 security review、安全收敛与 Final Review PASS【USER_REPORTED】。
- [RETROSPECTIVE] Git 证明 implementation commit `15fd5e857f2bff4d2c60bb3434a980002f6bddf8` 由 merge commit `4473f148ed49675b05489b5294b7b690fc99fc76` 合入 main，且当前 main ancestry 仍包含二者【VERIFIED】。

### [RETROSPECTIVE] Important decisions

- [RETROSPECTIVE] Harness 私有 transaction journal、backup 与 crash recovery state detection 属于 WP-14 Transaction Runtime；SQLite、Audit Store、Event Store 与长期历史查询不属于 WP-14【USER_REPORTED】。
- [RETROSPECTIVE] Apply 必须由 transaction coordinator 执行 prepare、backup、apply、verify、rollback/recovery；禁止 Git commit/reset/checkout rollback、自动 merge及由 LLM 判定事务结果【USER_REPORTED】。
- [RETROSPECTIVE] 最终安全收敛将 target-root identity、parent identity binding 与 displaced-directory mismatch 纳入 immutable apply plan/journal evidence；startup recovery identity mismatch 必须 fail closed 为 `RECOVERY_REQUIRED`【USER_REPORTED】。
- [RETROSPECTIVE] Requirement scope 包含 foundational `TXN-001..004` 与 PLAN-owned `TXN-009..016, TXN-019`【USER_REPORTED】。

### [RETROSPECTIVE] Verification and limitations

- [RETROSPECTIVE] 既有台账记录最终 WP-14 suite 为 `66 passed`、WP-13+14 为 `100 passed`，但本补录不声称保存了当时完整原始终端输出【USER_REPORTED】。
- [RETROSPECTIVE] WP-15 merge 后当前 main 全量回归为 `757 passed in 29.89s`，并验证 WP-14 commit ancestry【VERIFIED】。
- [RETROSPECTIVE] WP-14 只拥有当前事务 runtime 与恢复证据，不提供 WP-15 长期审计查询或跨介质原子性【USER_REPORTED】。

### [RETROSPECTIVE] Final process gate

- [RETROSPECTIVE] `WP14_PROCESS_CLOSEOUT = RECOVERED`；本节不重新定义 transaction state machine、rollback/apply semantics 或 WP-15 authority。

## [RETROSPECTIVE] WP-15 Persistence / Audit process record

### [RETROSPECTIVE] Status and gate transition

- [RETROSPECTIVE] WP-15 状态为 `COMPLETED / COMMITTED / MERGED / POST_MERGE_VERIFIED`。planning review、Red、Phase A/B/C implementation、quality-review findings、四阶段 review fix 与 Final Quality Review PASS 来自已批准历史会话；planning/final-review 原文未同期保存到仓库【USER_REPORTED】。
- [RETROSPECTIVE] Git 证明 implementation commit `53751e479f82aed8e08a55d399232cc151ead5f1` 由 two-parent merge commit `0492927b4cc9f8e4298cb9810388673e337e320a` 合入 main；local main 与 origin/main 均指向该 merge commit【VERIFIED】。

### [RETROSPECTIVE] Important decisions

- [RETROSPECTIVE] WP-15 负责长期保存、查询与审计，不重新定义 WP-14 transaction state machine、apply、rollback 或 recovery semantics【USER_REPORTED】。
- [RETROSPECTIVE] `HarnessStore` 保持 domain-only abstraction，不公开 `execute_sql`、`sqlite3.Connection`、Cursor 或 Row；SQLite adapter 保存 Task/governance versions、approval lifecycle、budget、ChangeSet confirmation、audit与Apply observation【USER_REPORTED】。
- [RETROSPECTIVE] Store 只观察真实 WP-14 `ApplyResult` 并保存 identity、digests、phase、journal reference与summary；persistence 不成为 transaction、apply或recovery authority【USER_REPORTED】。
- [RETROSPECTIVE] Migration integrity 包括严格顺序与连续前缀、SHA-256 checksum、drift detection、no downgrade与失败 rollback；audit 通过原子 business-state+audit写入及 UPDATE/DELETE trigger保持 append-only【USER_REPORTED】。
- [RETROSPECTIVE] Requirement scope 为 `PST-001..003, PST-007..012`【USER_REPORTED】。

### [RETROSPECTIVE] Verification and limitations

- [RETROSPECTIVE] 既有台账记录最终 persistence suite 为 `30 passed`、WP-13+14 regression 为 `100 passed`；Final Quality Review PASS及其详细 finding closure来自批准历史会话【USER_REPORTED】。
- [RETROSPECTIVE] merge 后 main 全量回归收集 `757`、通过 `757`、失败 `0`，用时 `29.89s`；working tree clean，WP-13/14/15 ancestry均通过【VERIFIED】。
- [RETROSPECTIVE] SQLite 与 WP-14 磁盘 journal 不保证跨介质原子性；journal reference只做安全相对路径边界验证，启动一致性协调仍属于 WP-18【USER_REPORTED】。
- [RETROSPECTIVE] WP-15 未实现 WP-16 event delivery、WP-17 lease/lock 或 WP-18 startup recovery orchestration【USER_REPORTED】。

### [RETROSPECTIVE] Final process gate

- [RETROSPECTIVE] `WP15_PROCESS_CLOSEOUT = RECOVERED`；当前 main 的 WP-15 post-merge baseline 已验证【VERIFIED】。本节仅恢复过程证据，不授权 commit、merge、rebase、reset或其他 history mutation。

## WP-16 Event Delivery planning checkpoint

### Status and gate transition

- Status: `PLANNING COMPLETE / WAITING APPROVAL`.
- Gate transition: `INIT → PLANNING REVIEW`.
- 本记录为 planning 阶段同步写入的当前过程记录【CONTEMPORANEOUS / VERIFIED】；尚未进入 Red、implementation、review fix 或 commit gate。

### Baseline and scope

- 独立 branch/worktree 为 `wp-16-event-delivery` / `.worktrees/wp-16-event-delivery`，从 clean main `87a4200fe8b87843f5a1852fe0ce9cea0d186c05` 创建；WP-13、WP-14、WP-15 commit ancestry均通过【CONTEMPORANEOUS / VERIFIED】。
- planning baseline full pytest为 `757 passed in 30.41s`【CONTEMPORANEOUS / VERIFIED】。
- WP-16 owned PV严格为 `PST-013`、`PST-014`；`PST-023/024` 在本 WP 仅支持三类 evidence separation与关联引用，正式 PV ownership仍属于 WP-24。
- 当前允许范围仅为 planning与本 checkpoint；未创建 production API、tests、database schema或migration。

### Architecture and authority boundary

- WP-15 负责保存 Task、治理版本、Approval、Budget、ChangeSet confirmation、append-only audit和WP-14 Apply observation；其 SQLite事实仍是持久化来源。
- WP-16 负责把已持久化领域事实建模为 `DomainEvent`，以 `EvidenceRef` 区分正式审计、持久化领域事件与有界临时日志/私有artifact引用，并通过 `EventReader.after` 提供按event ID读取、polling和replay能力。
- WP-16不得成为 transaction、apply、recovery或persistence authority；event、reader cursor、consumer状态、内存通知与连接状态均不得改变Task生命周期或解释文件Apply结果。
- SSE server、HTTP、subscription、push、message queue、distributed event bus与at-least-once client protocol属于WP-24；WP-17 lock/lease和WP-18 startup recovery orchestration不进入本 WP。

### Proposed event and delivery contract

- `DomainEvent` 最小持久化字段为全局单调 `event_id`、稳定 event kind/source、`occurred_at`、task/entity identity、可选 run/action identity、可选 entity revision以及有界、确定性payload/evidence references。业务 identity、revision、timestamp与事实payload来自产生变化的WP-15业务意图/持久化事务；event ID由SQLite持久化序列在同一事务中分配，不能由内存publisher签发。
- `EventReader.after(event_id, limit)`只读持久化事件，按event ID严格升序返回有界结果；相同cursor可重放相同已提交事实。当前 WP 采用reader/polling，不实现主动subscription或push。
- consumer失败不删除、不确认或回滚领域事件；consumer可用最后成功处理的event ID重试。重复读取是允许的，consumer按event ID幂等去重；delivery中断不改变任务状态，恢复时继续持久化读取。

### Planning finding requiring human decision

- 冻结 SPEC `PST-013` 要求领域事件与产生它的状态变化在同一SQLite事务提交。
- PLAN WP-16 的精确文件仅列 `domain/events.py`、`persistence/evidence.py`、`test_events.py`；未包含现有 `persistence/sqlite_store.py`、`persistence/ports.py`、SQL migration或schema文件。当前WP-15 schema没有领域事件表，单靠三个精确文件无法证明state+event原子提交。
- 实现前需要人工裁决最小合法production/schema surface。未获裁决前不得创建Red tests或通过旁路store、内存event ID、audit投影冒充`PST-013`。

### Planning gate

- `WP16_PLANNING_RESULT = COMPLETE`.
- `WP16_IMPLEMENTATION_ENTRY = BLOCKED_PENDING_SCOPE_DECISION`.
- 下一合法动作仅为planning review与人工裁决；本 checkpoint不授权production、test、schema、migration、commit或merge。

### Architecture decision approval

- `2026-07-28 15:40:51 +0800`：人工批准解决`PST-013` blocker的有限persistence boundary扩展【CONTEMPORANEOUS / APPROVED DECISION】。
- State change与产生它的`DomainEvent`必须在同一SQLite transaction提交；WP-15仍是persistence authority，`DomainEvent`仅为持久化事实，不是新的Task、transaction、apply或recovery authority。
- 批准production scope：
  - `src/coding_harness/domain/events.py`
  - `src/coding_harness/persistence/evidence.py`
  - `src/coding_harness/persistence/ports.py`
  - `src/coding_harness/persistence/sqlite_store.py`
  - `src/coding_harness/persistence/sql/002_events.sql`
  - `src/coding_harness/persistence/migrations.py`，仅当现有runner无法支持002 migration时允许修改。
- 批准test scope为`tests/integration/event/test_events.py`。
- Event Delivery不得修改Task state、Transaction state、Apply state或Recovery state。WP-17 lock/lease、WP-18 recovery orchestration、SSE、HTTP、WebSocket、Message Queue与Distributed Event Bus继续禁止。
- Gate transition：`PLANNING REVIEW → APPROVED FOR RED`.
- `WP16_IMPLEMENTATION_ENTRY = APPROVED_FOR_RED`；本记录本身未创建Red、production、schema或migration，也不授权commit或merge。

### Red phase evidence

- `2026-07-28 15:48:58 +0800`：在批准路径`tests/integration/event/test_events.py`新增12个integration contract nodes【CONTEMPORANEOUS / VERIFIED】。
- 覆盖模型identity/kind/time/entity/revision与bounded payload、EvidenceRef path/digest/size/lifecycle、三类evidence separation、state+event原子回滚、持久化全局单调event ID、`EventReader.after` ordering/bound/replay、memory-not-truth及`PST-013/014`参数化行为。
- collect-only结果为`12 tests collected in 0.06s`；最终Red为`12 failed in 3.28s`，全部failure为缺失`coding_harness.domain.events`的明确WP-16 contract failure【CONTEMPORANEOUS / VERIFIED】。
- 首次Red failure带有已捕获`ModuleNotFoundError`上下文；只调整test loader后重跑，最终证据无collection error、import error或environment error。该纠正不改变测试语义。
- Failure classification：`EXPECTED_INTERFACE_MISSING`。未修改production、schema、migration、`SPEC.md`或`PLAN.md`，未开始Green。
- Gate transition：`APPROVED FOR RED → RED COMPLETE`.
- `WP16_RED_GATE = COMPLETE`；下一阶段必须等待Red review/Green授权，本记录不授权commit或merge。

### Implementation milestone

- `2026-07-28 15:54:08 +0800`：Gate transition=`RED COMPLETE → IMPLEMENTATION`【CONTEMPORANEOUS / VERIFIED】。
- 实际production scope为`domain/events.py`、`persistence/evidence.py`、`persistence/sqlite_store.py`、`persistence/sql/002_events.sql`。`ports.py`无需扩展；现有migration runner已支持连续002，故`migrations.py`未修改。
- `DomainEvent`为immutable frozen/slots model，event kind闭合，identity/time/entity/revision与canonical bounded payload均确定性验证。`EvidenceRef`只引用私有artifact元数据，不保存正文；`AuditRecord`、`DomainEvent`、temporary evidence保持不同类型。
- `domain_events.event_id`由SQLite `AUTOINCREMENT`持久分配；表以UPDATE/DELETE trigger保持append-only。WP-15 `create_task`与`transition_task`在原业务事实+audit transaction中插入对应event，event insertion failure使整个transaction rollback。
- `EventReader.after(event_id, limit)`只通过SQLite read-only/query-only connection读取持久化事件，按event ID升序返回，limit闭合为1..1000；reader无Task/transaction/apply/recovery mutation接口。
- 首轮WP-16 target suite=`12 passed in 3.48s`；reader read-only hardening后WP-15+WP-16联合回归=`42 passed in 0.43s`【CONTEMPORANEOUS / VERIFIED】。
- Scope boundary保持：WP-15仍是persistence authority；event只是持久化事实。未实现SSE、HTTP、WebSocket、queue、distributed bus、WP-17 lock/lease或WP-18 recovery orchestration；`SPEC.md`与`PLAN.md`未修改。
- `WP16_IMPLEMENTATION_MILESTONE = GREEN / REVIEW_PENDING`；当前不授权commit或merge。

### Review gate start

- `2026-07-28 15:56:48 +0800`：Gate transition=`IMPLEMENTATION → REVIEW`【CONTEMPORANEOUS / VERIFIED】。
- 独立review检查persistence authority、PST-013三写原子性与partial-failure rollback、event/evidence model、persistent reader及禁止surface；主Agent执行WP-16、WP-15和full regression。
- `WP16_REVIEW_STATUS = IN_PROGRESS`；finding、severity与resolution必须在review结束后同步记录。当前不授权commit或merge。

### Independent review result

- `2026-07-28 16:00:44 +0800`：独立review verdict=`No — Important fixes required`；Critical=`0`、Important=`3`、Minor=`2`【CONTEMPORANEOUS / VERIFIED】。
- Important 1：`DomainEvent.evidence_refs`接受任意object且只冻结外层tuple，nested mutable与arbitrary persistence/application object可进入public event model；必须建立closed、deeply immutable、bounded reference contract及adversarial tests。
- Important 2：`EvidenceRef.relative_path`无UTF-8 byte上限且未拒绝newline/tab等control characters；必须增加确定性长度/control validation及边界tests。
- Important 3：PST-013 fault test未断言audit rollback，且未覆盖`create_task` event failure与audit-insert failure；必须证明task/state、audit、domain-event三写在create/transition partial failure下共同rollback。
- Minor 1：PLAN固定`test_publisher_reads_store`名称不可删除，但当前unrelated empty-list断言不构成publisher/store证据；review fix应在不实现WP-24 publisher的前提下用真实persistent-reader/reopen行为增强。
- Minor 2：缺少已有001 database保存task/audit数据后升级002并继续atomic state/event写入的migration regression。
- Review确认通过的边界：WP-15仍是persistence authority；state+audit+event实现位于同一`with connection` transaction；event ID持久化排序；reader mode=ro/query-only、ordered/bounded/replay；无SSE/HTTP/WebSocket/queue/bus/WP-17/WP-18 surface。
- Fresh regression：WP-16=`12 passed in 0.18s`；WP-15=`30 passed in 0.39s`；full=`768 passed, 1 failed in 26.39s`，唯一failure为预期dirty-path cleanliness gate；deselect该自指门禁后=`768 passed, 1 deselected in 26.03s`【CONTEMPORANEOUS / VERIFIED】。
- Failure classification：`PROCESS_CLEANLINESS_GATE`，不是behavior regression。
- `WP16_REVIEW_STATUS = CHANGES_REQUIRED`；`WP16_REVIEW_RESOLUTION = PENDING_REVIEW_FIX`。当前不授权commit或merge。

### Review fix gate start

- `2026-07-28 16:04:47 +0800`：人工授权解决全部review findings，Gate transition=`REVIEW → REVIEW_FIX`【CONTEMPORANEOUS / VERIFIED】。
- 修复必须先建立deep immutable/closed EvidenceRef、UTF-8/control path、三写partial-failure、persistent reopen及001→002 upgrade Red，再做最小production修复。
- `test_publisher_reads_store`名称按PLAN保留，但不得实现WP-24 publisher；只证明write/close/reopen/read来自持久化source。
- `WP16_REVIEW_FIX_STATUS = STARTED`；继续禁止commit/merge、SPEC/PLAN修改及WP-17/18/24实现。

### Review fix completion

- `2026-07-28 16:11:36 +0800`：Gate transition=`REVIEW_FIX → REVIEW_FIX_COMPLETE`【CONTEMPORANEOUS / VERIFIED】。
- Review-fix Red为`4 failed, 15 passed in 0.21s`：失败精确来自任意/非精确evidence member仍可进入`DomainEvent`，以及newline、tab和4097-byte path仍被`EvidenceRef`接受。最小实现后WP-16 suite为`19 passed in 3.28s`。
- Important findings resolution：`EvidenceRef`成为closed frozen domain type，`DomainEvent`只接受精确`EvidenceRef` tuple，拒绝嵌套可变/任意成员；相对路径实施严格UTF-8、4096-byte上限、control-character及canonical relative-path校验；create-event failure、transition-event failure与audit-insert failure均验证Task fact/state、Audit、DomainEvent在同一SQLite transaction共同rollback。
- Minor findings resolution：保留PLAN固定`test_publisher_reads_store`名称，以write/close/reopen/read证明persistent source且不新增publisher；001-only database升级002后保留既有Task/Audit，并可继续执行atomic state/audit/event mutation。
- Regression evidence：WP-15=`30 passed in 4.49s`；full=`775 passed, 1 failed in 25.86s`，唯一失败为预期dirty-worktree cleanliness gate；排除该自指流程门禁的完整行为回归=`775 passed, 1 deselected in 29.28s`【CONTEMPORANEOUS / VERIFIED】。
- 独立复审结果为Critical=`0`、Important=`0`、Minor=`0`，所有原finding关闭；WP-15保持persistence authority，EventReader只读，未引入SSE/HTTP/WebSocket/queue/bus、WP-17、WP-18或WP-24 publisher。
- `WP16_REVIEW_FIX_STATUS = COMPLETE`；`WP16_NEXT_GATE = FINAL_REVIEW`。当前仍禁止stage、commit或merge，且未修改`SPEC.md`或`PLAN.md`。

### Final review checkpoint

- `2026-07-28 16:17:53 +0800`：Gate transition=`REVIEW_FIX_COMPLETE → FINAL_REVIEW`【CONTEMPORANEOUS / VERIFIED】。
- Final review只读验证批准文件范围、WP-15 persistence authority、PST-013 business fact/audit/domain-event原子性、002 migration完整性、event/evidence模型与三层regression。
- 除本同步checkpoint外，不修改production、tests、`SPEC.md`或`PLAN.md`；不执行stage、commit或merge。
- `WP16_FINAL_REVIEW_STATUS = IN_PROGRESS`；最终finding、test evidence与verdict将在审查结束后同步记录。

### Final review result

- `2026-07-28 16:21:04 +0800`：最终独立review verdict=`PASS`，Critical=`0`、Important=`0`、Minor=`0`【CONTEMPORANEOUS / VERIFIED】。
- Scope精确限于批准的WP-16 event production/schema/test文件与两份同步过程文档；未实现WP-17 lock/lease、WP-18 recovery orchestration或WP-24 publisher/SSE/API/queue。
- WP-15 Store继续作为唯一business-state persistence authority；`DomainEvent`仅保存同事务事实，`EventReader`使用SQLite `mode=ro`与`query_only`并且没有mutation API。
- PST-013 review确认`create_task`和`transition_task`在同一`with connection` transaction写business fact、audit与domain event；create-event、transition-event与audit-insert failure测试分别证明三者共同rollback或保持不变。
- Migration review确认`002_events.sql`按连续版本由现有runner发现，checksum采用SHA-256，迁移运行于`BEGIN IMMEDIATE`且失败rollback；001→002测试证明旧Task/Audit保留且升级后event功能可用。
- Event review确认frozen/slots、closed exact `EvidenceRef`、canonical sorted/unique且64KiB bounded payload、UTF-8 4096-byte relative path、control/traversal/absolute/backslash拒绝、digest与size严格校验。
- Fresh regression：WP-16=`19 passed in 3.20s`；WP-15=`30 passed in 3.25s`；full collected=`776`，结果=`775 passed, 1 failed in 26.09s`，唯一failure为当前7个批准dirty paths触发的clean-worktree流程门禁；排除该自指节点后完整行为集合=`775 passed, 1 deselected in 25.95s`【CONTEMPORANEOUS / VERIFIED】。
- `WP16_FINAL_REVIEW_STATUS = PASS`；`WP16_NEXT_GATE = COMMIT_PREPARATION`。本记录不授权stage、commit或merge。

### [RETROSPECTIVE] Commit gate completion and final closeout

- [RETROSPECTIVE] 本节于post-merge验证后补录，不表示commit、push、PR merge或main verification发生时已同步写入过程文档。
- [RETROSPECTIVE] Commit gate完成：implementation commit=`52c3da9522fa8a4461c2df884cbbf009a4ad7f23`，subject=`feat(events): implement persistent domain event delivery foundation`；commit精确包含批准的7个WP-16 production/schema/test/process文件【VERIFIED】。
- [RETROSPECTIVE] PR merge完成：two-parent merge commit=`208f7bbe66705433a13f3b6fddda3c56d0272e6f`将WP-16 commit合入main；WP-16 commit为main ancestor，WP-13 `bfbc081`、WP-14 `15fd5e8`、WP-15 `53751e4` ancestry继续保持【VERIFIED】。
- [RETROSPECTIVE] Main regression verification：local main、`origin/main` tracking ref与远程实际main均为`208f7bbe66705433a13f3b6fddda3c56d0272e6f`，working tree clean；使用Python 3.12.3执行`PYTHONDONTWRITEBYTECODE=1 <python> -m pytest -p no:cacheprovider`，结果为`776 collected / 776 passed / 0 failed in 26.78s`，且未产生cache、bytecode、SQLite database或temporary artifact【VERIFIED】。
- [RETROSPECTIVE] 远程feature branch删除已由远程实际refs只读查询确认；本地同名remote-tracking ref在未prune条件下可能保留，仅属于tracking cache，不改变merge结论【VERIFIED】。
- [RETROSPECTIVE] Final process gate：`COMMIT_PREPARATION → COMMIT_AUTHORIZED → COMMITTED → PUSHED → MERGED → POST_MERGE_VERIFIED → CLOSED`。`WP16_FINAL_STATUS = CLOSED`；WP-16过程证据链闭合【VERIFIED】。

## WP-17 initialization checkpoint

### Status and gate transition

- `2026-07-29 10:57:04 +0800`：WP-17“进程锁与 Execution Lease”初始化完成，Gate transition=`INIT → PLANNING`【CONTEMPORANEOUS / VERIFIED】。
- 独立worktree=`.worktrees/wp-17-process-lock-lease`，branch=`wp-17-process-lock-lease`，baseline commit=`b3eca6c3cd713b54645dbe7dec3873a8ff894290`；创建前main与创建后worktree均为clean baseline【CONTEMPORANEOUS / VERIFIED】。
- WP-13 `bfbc081`、WP-14 `15fd5e8`、WP-15 `53751e4`、WP-16 `52c3da9`均为baseline ancestor；WP-16 commit、merge、main verification与final closeout记录完整【CONTEMPORANEOUS / VERIFIED】。
- Baseline regression使用Python 3.12.3执行`PYTHONDONTWRITEBYTECODE=1 <python> -m pytest -p no:cacheprovider`，结果=`776 collected / 776 passed / 0 failed in 26.49s`【CONTEMPORANEOUS / VERIFIED】。
- WP-17 owned requirements为`PST-015..017, PST-019..020`；当前只授权initialization/planning，未创建production或tests，未修改`SPEC.md`或`PLAN.md`。
- `WP17_STATUS = PLANNING`；`WP17_IMPLEMENTATION_ENTRY = NOT_AUTHORIZED`。本checkpoint不授权stage、commit、merge或push。

### WP-17 Planning checkpoint

#### Status and gate

- `2026-07-29 11:03:25 +0800`：WP-17 planning分析完成，但implementation-entry存在冻结文件范围冲突；Gate=`PLANNING → PLANNING REVIEW BLOCKED`【CONTEMPORANEOUS / VERIFIED】。
- `WP17_PLANNING_STATUS = BLOCKED / WAITING HUMAN DECISION`。不得进入Red、production、schema或migration实现。

#### Ownership boundary

- Serve lock authority属于OS kernel lock，由`ProcessLock`持有固定私有数据目录lock file的打开descriptor；lock file内容、PID或SQLite行均不是该锁的权威。
- Execution Lease authority属于`ExecutionLeaseService`的确定性CAS规则，唯一持久化真相必须是SQLite全局单槽记录；WP-15提供SQLite/migration/audit持久化机制，但不决定谁可执行。
- WP-14仍独占Apply、Rollback与文件Recovery语义。WP-17只在调用前授予或拒绝execution ownership，不解释`ApplyResult`、不推进phase、不执行恢复。
- WP-16仍只提供已持久化领域事件与只读delivery foundation。`PST-017`明确要求recovery audit而非新DomainEvent，因此WP-17不扩展WP-16 event schema/kind。
- WP-18负责启动时扫描非终态lease及其他残留状态并编排恢复。WP-17负责把过期heartbeat确定性标记为recovery-pending、原子追加审计并阻止普通执行，不自动清槽或授权其他task。
- Process lock contention是serve启动边界失败；lease contention是`EXECUTION_SLOT_BUSY`且Task state不变；lease SQLite失败是persistence failure。外部副作用已开始后的恢复升级仍由WP-14/WP-18决定。

#### Conditional design and verification mapping

- `PST-015`：固定私有数据目录输入→单serve lock acquire/busy结果；由OS lock/`ProcessLock`负责；验证`test_single_serve`与`test_lock_lease_separate`。
- `PST-016`：task/run/owner/acquired-at/last-progress/phase及expected revision输入→唯一active lease或busy；由SQLite lease CAS负责；验证`test_single_execution_lease`、`test_lease_binding`及参数化PV node。
- `PST-017`：current lease、trusted now与heartbeat期限输入→同task/run的recovery-pending标记和append-only audit，不产生新owner；验证`test_heartbeat`、`test_stale_audit_only`及stale-owner拒绝。
- `PST-019`：匹配lease/owner/revision与container、file-effect、cleanup安全终态证据输入→release或fail-closed拒绝；验证`test_safe_release`。
- `PST-020`：recovery-pending slot与normal/recovery acquisition intent输入→recovery优先、普通Agent/Docker/Apply acquisition blocked；验证`test_recovery_priority`与`test_recovery_blocks_execution`。WP-18及后续Docker/API层负责消费此门禁，不把恢复语义迁入WP-17。
- 候选`ExecutionLease`为frozen snapshot；acquisition内`lease_id/task_id/run_id/owner_identity/acquired_at/purpose`不可变，`last_progress_at/phase/status/revision`仅通过SQLite CAS产生新snapshot。普通acquire、heartbeat、safe release与显式recovery acquire均使用`BEGIN IMMEDIATE`和expected revision/identity检查。
- Process crash后OS自动释放process lock，但SQLite lease继续存在；过期只进入恢复审计。旧owner返回时因lease identity/revision不匹配被拒绝。数据库提交后进程退出由持久lease在下次inspect/startup scan中恢复，不依赖内存。

#### Blocker and required decision

- 冻结SPEC `PST-016`要求“SQLite Execution Lease”，`PST-011`要求所有schema migration使用仓库内严格递增显式SQL版本、checksum与`schema_migrations`。
- 当前`001_initial.sql`和`002_events.sql`没有lease表；冻结PLAN WP-17精确文件只有`process_lock.py`、`lease.py`和`test_lease.py`，不包含第三个SQL migration。
- 在`lease.py`内执行DDL、使用文件/内存lease、复用audit/domain-event作为当前lease authority都会违反冻结规范或既有authority boundary，不能作为替代。
- 推荐人工批准WP-17最小增加`src/coding_harness/persistence/sql/003_execution_lease.sql`。现有`MigrationRunner`已支持连续003，预计无需修改`migrations.py`、`ports.py`、`sqlite_store.py`、WP-14或WP-16。
- 批准前`WP17_IMPLEMENTATION_ENTRY = BLOCKED`；下一合法动作仅为人工scope裁决。当前未创建production、tests、schema或migration，未修改`SPEC.md`或`PLAN.md`。

#### Architecture decision approval

- `2026-07-29 11:10:16 +0800`：人工批准解决WP-17 planning blocker的最小scope expansion【CONTEMPORANEOUS / APPROVED DECISION】。
- 批准新增`src/coding_harness/persistence/sql/003_execution_lease.sql`。理由：`PST-016`要求Execution Lease持久化于SQLite，`PST-011`要求schema由仓库内显式、递增、带checksum记录的migration管理。
- 原冻结PLAN文件`process_lock.py`、`lease.py`、`test_lease.py`继续保持；除新增003 migration外不扩大production/test范围。
- Authority boundary保持：WP-15仍是persistence authority；WP-17不实现persistence framework；不修改WP-14 transaction runtime、WP-16 event schema，不实现WP-18 recovery orchestration。
- Lease expiration只能持久化recovery-pending事实并追加恢复审计，不能自动执行恢复、清除执行槽或把ownership转移给其他task。
- Gate transition=`PLANNING COMPLETE → APPROVED FOR RED`；`WP17_PLANNING_BLOCKER = RESOLVED`，`WP17_IMPLEMENTATION_ENTRY = APPROVED_FOR_RED`。
- 本decision checkpoint未创建Red tests、production或003 migration，不授权跳过TDD直接进入实现，也不授权stage、commit、merge或push。

### Red phase evidence

- `2026-07-29 11:19:14 +0800`：Gate transition=`APPROVED FOR RED → RED COMPLETE`【CONTEMPORANEOUS / VERIFIED】。
- `RED_STARTED`后仅新增批准路径`tests/integration/persistence/test_lease.py`；未创建或修改production、schema或migration，未修改WP-14、WP-16、`SPEC.md`或`PLAN.md`。
- Red suite覆盖OS process lock单一acquire与竞争、lock file内容非ownership truth、lock contention不改Task state、process-lock/lease authority分离；Execution Lease唯一active slot、task/run/owner绑定、owner与revision CAS heartbeat/release；expiration只产生同identity的recovery-pending与append-only audit，不自动释放、转移ownership、恢复或修改Task state；普通与recovery intent分离及同task/run recovery绑定；003 migration需求。
- Requirement evidence由参数化行为节点覆盖`PST-015`、`PST-016`、`PST-017`、`PST-019`、`PST-020`，不是仅检查类型存在。
- Collect-only命令收集`17 tests`、退出码`0`；完整Red为`17 failed in 0.11s`、退出码`1`【CONTEMPORANEOUS / VERIFIED】。
- Failure classification：`16 × EXPECTED_INTERFACE_MISSING`，因为`coding_harness.persistence.process_lock`及lease contract尚不存在；`1 × EXPECTED_BEHAVIOR_MISSING`，因为`003_execution_lease.sql`尚不存在。无collection error或environment error。
- `WP17_RED_GATE = COMPLETE`；下一阶段为`IMPLEMENTATION`，必须等待明确授权。本checkpoint不授权production/schema实现、stage、commit、merge或push。

### Implementation milestone

- `2026-07-29 11:31:15 +0800`：Gate transition=`RED COMPLETE → IMPLEMENTATION`【CONTEMPORANEOUS / VERIFIED】。
- 实际修改范围严格为批准的`src/coding_harness/persistence/process_lock.py`、`src/coding_harness/persistence/lease.py`、`src/coding_harness/persistence/sql/003_execution_lease.sql`、Red test及两份过程文档；未修改`sqlite_store.py`、`ports.py`、WP-14、WP-16、Task lifecycle、`SPEC.md`或`PLAN.md`。
- `ProcessLock`以OS `flock`及持有中的打开descriptor作为唯一authority；lock file内容与PID不参与ownership判断，descriptor关闭或进程退出即由kernel释放ownership。
- `ExecutionLease`为frozen snapshot，包含lease、global slot、task、run、owner、purpose、acquired/progress time、phase、status与revision。SQLite部分唯一索引保证每个slot只有一个`ACTIVE`或`RECOVERY_PENDING`记录；acquire、heartbeat、release与recovery acquisition使用`BEGIN IMMEDIATE`及lease/owner/revision CAS，adapter不暴露connection或通用SQL API。
- Expiration只把匹配的active lease原子标记为`RECOVERY_PENDING`并追加`EXECUTION_LEASE_STALE` audit，不自动释放、不转移ownership、不修改Task state、不执行recovery。显式recovery acquisition必须匹配pending lease的task/run/revision，并产生明确`RECOVERY` purpose；普通execution在pending/recovery lease存在时fail closed。
- `003_execution_lease.sql`仅声明lease table、开放slot唯一索引及task/run查询索引；现有`MigrationRunner`负责连续版本发现、SHA-256 checksum、drift/no-downgrade及事务应用，production Python未执行DDL。
- Green evidence：WP-17 target=`17 passed in 0.26s`；包含WP-15/WP-16/WP-17的persistence regression=`47 passed in 1.12s`【CONTEMPORANEOUS / VERIFIED】。
- Gate transition=`IMPLEMENTATION → REVIEW READY`；`WP17_IMPLEMENTATION_STATUS = COMPLETE`，`WP17_REVIEW_STATUS = PENDING`。当前不授权stage、commit、merge或push。

### Independent review and review fix

- 独立review确认原boundary未越界，但结论为`CHANGES REQUIRED`：Critical=`1`、Important=`2`【CONTEMPORANEOUS / VERIFIED】。
- Critical：`ExecutionLeaseService`接受caller-controlled `slot_identity`，003部分唯一索引只约束相同slot；不同slot可各持有open lease，也可绕过另一slot的recovery-pending，违反`PST-016`全局唯一ownership。
- Important 1：原测试只有同进程lock竞争和顺序default-slot lease竞争，缺少真实并发、持锁进程异常退出以及recovery takeover后旧owner恢复证据。
- Important 2：原migration测试只从空数据库一次应用001/002/003，缺少既有002 Task/Audit/DomainEvent保留和003中途失败完整回滚证据。
- Gate transition=`REVIEW → CHANGES REQUIRED → REVIEW_FIX`；`REVIEW_FIX_STARTED`【CONTEMPORANEOUS / VERIFIED】。
- 新增7个review-fix integration节点。首次选择run为`3 failed / 4 passed`，其中crash子进程因未继承pytest的`src`导入路径而产生无效environment failure；仅修正test-only `PYTHONPATH`后，合法review-fix Red=`2 failed / 5 passed / 17 deselected in 0.19s`【CONTEMPORANEOUS / VERIFIED】。
- 两项合法Red精确证明caller可指定alternate slot且SQLite可接受第二个不同slot的open lease。其余5项是review要求的缺失证据characterization：真实线程并发、process `os._exit`、旧owner恢复、002升级保留及003失败回滚在原基础机制下通过；未人为制造failure。
- 最小production修复删除public `slot_identity`输入并固定系统identity=`execution:global`；003对该字段增加固定值CHECK，开放lease部分唯一索引改为常量表达式`(1)`，因此SQLite层不再依赖caller slot值且全库最多一个`ACTIVE`或`RECOVERY_PENDING` lease。
- 新增行为证据确认：两个独立执行者同时acquire只有一个成功；持锁进程异常退出后新持有者可获取kernel lock；recovery takeover后旧lease/owner/revision无法heartbeat或release；真实version-002数据库中的Task、Audit与DomainEvent在003升级后完整保留；强制003中途失败不记录version 3、不留下半表且旧数据保留。
- Review-fix selected Green=`7 passed / 17 deselected in 0.17s`；完整WP-17=`24 passed in 0.34s`；persistence regression=`54 passed in 0.59s`【CONTEMPORANEOUS / VERIFIED】。
- Boundary保持：WP-15提供SQLite/migration/audit persistence；WP-17只决定execution ownership；WP-14、WP-16、Task lifecycle不变；未实现WP-18 startup orchestration或WP-24 delivery。
- Gate transition=`REVIEW_FIX → REVIEW_FIX_COMPLETE`；`WP17_REVIEW_FIX_STATUS = COMPLETE`，`WP17_NEXT_GATE = FINAL_REVIEW`。当前不授权stage、commit、merge或push。

### Final review checkpoint

- `2026-07-29 11:53:44 +0800`：Final review started，Gate transition=`WP17_REVIEW_FIX_COMPLETE → WP17_FINAL_REVIEW`【CONTEMPORANEOUS / VERIFIED】。
- 独立final reviewer对批准的ProcessLock、ExecutionLease、003 migration与integration tests执行只读审查；findings=`none`，Critical=`0`、Important=`0`、Minor=`0`。
- Final verdict=`PASS`。Boundary verification确认WP-15 persistence、WP-17 execution ownership、WP-14 transaction/recovery、WP-16 event与WP-18 startup orchestration职责保持分离；未修改Task lifecycle，未实现WP-18/WP-24。
- Global slot、kernel lock/crash release、lease/owner/revision CAS、expiration/recovery边界、concurrent acquire、旧owner拒绝、002→003保留与migration rollback均通过源码及测试证据核验。
- Fresh test evidence：WP-17=`24 passed in 0.34s`；persistence regression=`54 passed in 0.59s`【CONTEMPORANEOUS / VERIFIED】。
- Gate transition=`WP17_FINAL_REVIEW → WP17_FINAL_REVIEW_PASS`；`WP17_FINAL_REVIEW_STATUS = PASS`，下一阶段=`COMMIT_PREPARATION`。本checkpoint不授权stage、commit、merge或push。

### [RETROSPECTIVE] WP-17 Final Closeout checkpoint

- [RETROSPECTIVE] 本节于PR merge及post-merge main verification完成后补录；不表示commit、push、merge或main regression发生时已同步写入过程文档。
- [RETROSPECTIVE] Commit gate completion：implementation commit=`f0e4dd0c9e5e938b839bce376531dbe6f27205c6`，subject=`feat(lease): implement process lock and execution lease ownership`，精确包含批准的WP-17 production/schema/test/process文件【VERIFIED】。
- [RETROSPECTIVE] PR merge：two-parent merge commit=`ac1074fa93b643f7eef0e08bdea1ac350f5a4daf`，message=`Merge pull request #8 from Shelia-YX/wp-17-process-lock-lease`，parents为merge前main `b3eca6c3cd713b54645dbe7dec3873a8ff894290`与WP-17 commit `f0e4dd0c9e5e938b839bce376531dbe6f27205c6`【VERIFIED】。
- [RETROSPECTIVE] Main verification：local main、`origin/main` tracking ref与远程实际main均为merge commit，ahead/behind=`0/0`，working tree clean；WP-13～WP-17 commits均为main ancestor【VERIFIED】。
- [RETROSPECTIVE] Regression：执行禁用bytecode/cache的完整pytest，结果=`800 collected / 800 passed / 0 failed in 25.20s`；测试后main仍clean且无cache、bytecode、SQLite database或temporary/editor artifact【VERIFIED】。
- [RETROSPECTIVE] Final process gate：`WP17_FINAL_REVIEW_PASS → WP17_MERGED_VERIFIED → WP17_CLOSED`。`WP17_FINAL_STATUS = CLOSED`；WP-17过程证据链闭合【VERIFIED】。

## WP-18 Initialization checkpoint

### Status and gate transition

- `2026-07-29 12:41:05 +0800`：WP-18 Startup Recovery Orchestration ownership开始，Gate transition=`INIT → PLANNING`【CONTEMPORANEOUS / VERIFIED】。
- 创建独立linked worktree=`.worktrees/wp-18-startup-recovery`及branch=`wp-18-startup-recovery`，精确基于clean main commit `dc4dadc003e81dec15020b80ef162250dc75bace`【CONTEMPORANEOUS / VERIFIED】。
- Historical integrity：WP-13 `bfbc08137ee45d23e0506c0aa2d99689f0ae24be`、WP-14 `15fd5e857f2bff4d2c60bb3434a980002f6bddf8`、WP-15 `53751e479f82aed8e08a55d399232cc151ead5f1`、WP-16 `52c3da9522fa8a4461c2df884cbbf009a4ad7f23`、WP-17 `f0e4dd0c9e5e938b839bce376531dbe6f27205c6`及WP-17 closeout baseline均为当前HEAD ancestor【CONTEMPORANEOUS / VERIFIED】。
- Baseline regression使用禁用bytecode/cache的完整pytest，结果=`800 collected / 800 passed / 0 failed in 28.72s`；未发现cache、bytecode、SQLite database或temporary/editor artifact【CONTEMPORANEOUS / VERIFIED】。
- 本checkpoint只建立WP-18工作所有权并验证开发基线；尚未阅读或形成WP-18设计，未进入planning分析或implementation，未修改production、tests、migration、`SPEC.md`或`PLAN.md`。
- `WP18_INITIALIZATION_STATUS = COMPLETE`；`WP18_CURRENT_GATE = PLANNING`；`WP18_DESIGN_STATUS = NOT_STARTED`；`WP18_IMPLEMENTATION_ENTRY = NOT_AUTHORIZED`。当前未stage、commit、push或merge。

## WP-18 Planning checkpoint

### Architecture and authority

- `2026-07-29 12:45:24 +0800`：`PLANNING_STARTED`；只读检查冻结SPEC/PLAN及WP-14～WP-17 public contracts，Gate保持=`INIT → PLANNING`【CONTEMPORANEOUS / VERIFIED】。
- Startup事实源必须是WP-15 Task/Apply observation、WP-17全局Execution Lease、WP-14磁盘Apply journal及可信task/container inventory；WP-16 DomainEvent只能用于关联和证据复核，不能反向成为Task、Apply或Lease truth。
- WP-18只负责`scan → classify → acquire recovery ownership → delegate → record result`。Detection/classification由WP-18确定性代码负责；execution ownership由WP-17负责；文件recovery decision与副作用由WP-14 `RecoveryCoordinator`负责；事实/审计持久化由WP-15负责；可重放event读取由WP-16负责。
- `RecoveryFinding`应为不可变闭合结果，至少绑定finding kind、task/run/lease/transaction identity、journal reference、evidence status、decision及blocking status；任何缺失、矛盾或无法验证的证据均fail closed，不由LLM推断。

### Requirement mapping and flow

- `PST-018`：输入为当前lease、容器inventory、非终态Apply事实、task目录与validated journal；输出为确定排序的findings及global startup blocking decision；owner=WP-18 orchestration，验证=`test_scan_lease/container/apply/check_journal`。
- `PST-025`：输入为Task state、闭合blocked reason及恢复证据；输出仅为确定性continue/重新调查/外部修复/lease/next-command decision，不新增状态规则；owner=现有domain state machine，WP-18只分类；验证=`test_uncertain_effect_recovers`及requirement node。
- `PST-026`：输入为等待审批Task、lease及container/file/cleanup终态证据；输出为safe-to-release或blocking finding，审批提交不启动loop；owner=WP-17 release authority与现有governance，WP-18只检查；验证=`test_approval_cleanup_release`。
- `PST-027`：输入为持久化Plan/Contract版本历史及Approval revision；输出为history-preserved/stale-approval finding，不创建版本或改approval生命周期；owner=WP-15 persistence与governance；验证=`test_revision_history`、`test_old_approval_invalidated`。
- `PST-028`：输入为等待修订Task、Workspace存在性、当前版本审批及显式continue事实；输出为workspace-preserved但write-disabled decision；owner=Task lifecycle/Policy，WP-18只阻止startup写执行；验证=`test_unapproved_revision_no_write`。
- `TST-002`：使用临时真实SQLite、transaction/task directories及journal文件覆盖一致、缺失、损坏和中断场景；容器probe使用有界fake inventory，不提前实现Docker adapter；验证=完整`test_startup.py` integration suite。
- 正常流程：先持有serve ProcessLock；有界扫描并建立不可变snapshot；按identity确定关联Task/Lease/ApplyObservation/Journal/DomainEvent；分类safe terminal、recovery pending、manual evidence required或inconsistent；仅对证据完整且WP-17 CAS允许的项取得recovery lease；调用WP-14 coordinator；将result交回WP-15业务意图接口；只在所有blocking findings闭合后允许新execution。
- Failure handling：apply crash由journal phase/effect证据决定并委托WP-14；stale lease只由WP-17标记并取得recovery purpose；missing journal或DB/disk不一致保持blocked且不得新写；duplicate startup由serve ProcessLock加lease CAS拒绝；任何持久化失败均不宣称恢复成功。

### Scope analysis and blocker

- 冻结PLAN当前精确范围仅为`src/coding_harness/application/startup_recovery.py`与`tests/integration/recovery/test_startup.py`。
- 该范围不足以实现真实authority-preserving startup scan：WP-14 `ApplyJournal`只有按已知transaction ID打开及`has_blocking_transaction()`布尔门禁，没有公开的validated nonterminal journal enumeration；WP-15 `HarnessStore`只能按已知task/transaction identity读取，不能枚举startup recovery candidates，也没有recovery finding/audit业务意图写入。
- 仅在`startup_recovery.py`中直接查SQLite、把DomainEvent当truth、解析WP-14私有journal布局或复制恢复逻辑均违反已批准authority boundary，因此不采用。
- 推荐最小人工scope裁决：允许修改`src/coding_harness/transaction/journal.py`，只增加有界、只读、验证后的journal enumeration；允许修改`src/coding_harness/persistence/ports.py`与`src/coding_harness/persistence/sqlite_store.py`，只增加purpose-specific startup snapshot query及recovery finding persistence。不得新增通用SQL接口、schema/migration、Apply/rollback实现、lease ownership规则、Task lifecycle或DomainEvent authority。
- Alternative A（推荐）：批准上述窄扩展，使WP-18消费真实authority并可端到端验证。Alternative B：只在WP-18定义caller-supplied snapshot/fake ports，可保持文件清单但不能证明backend真实startup scan，故不满足`PST-018`。Alternative C：WP-18直读SQLite/磁盘私有格式，明确越权，拒绝。
- Container inventory在WP-18仅定义位于`startup_recovery.py`内的窄、只读probe contract并由测试fake驱动；不实现Docker命令、cleanup或WP-18以外adapter。
- `WP18_PLANNING_STATUS = BLOCKED`；`WP18_BLOCKER = AUTHORITY_DISCOVERY_AND_RECORDING_INTERFACES_OUTSIDE_FROZEN_FILE_SCOPE`；`WP18_NEXT_GATE = WAITING_HUMAN_DECISION`；`WP18_RED_ENTRY = NOT_AUTHORIZED`。本checkpoint未创建production或tests，未修改SPEC/PLAN，未stage、commit、push或merge。

## WP-18 Architecture decision checkpoint

### Human decision and blocker resolution

- `2026-07-29 12:49:56 +0800`：人工批准解决真实startup recovery candidate enumeration blocker的最小scope expansion【CONTEMPORANEOUS / APPROVED DECISION】。
- 批准修改`src/coding_harness/transaction/journal.py`，仅用于新增有界、validated、read-only journal enumeration；不得改变`RecoveryCoordinator`、journal phase语义或实现新的recovery算法。
- 批准修改`src/coding_harness/persistence/ports.py`与`src/coding_harness/persistence/sqlite_store.py`，仅用于purpose-specific startup recovery candidate query及recovery finding persistence adapter；WP-15继续拥有persistence authority。
- 原PLAN范围`src/coding_harness/application/startup_recovery.py`与`tests/integration/recovery/test_startup.py`保持有效；新增批准路径只用于解除已记录的authority discovery/recording接口缺口。
- 禁止修改WP-17 ExecutionLease authority或lease schema、Task lifecycle、WP-16 DomainEvent authority；禁止新增migration、暴露`sqlite3.Connection`/Cursor、增加通用SQL API、直接执行文件recovery或扩大到其他WP。
- Blocker resolution：`WP18_BLOCKER = RESOLVED_BY_HUMAN_SCOPE_DECISION`。
- Gate transition=`PLANNING BLOCKED → APPROVED FOR RED`；`WP18_RED_ENTRY = AUTHORIZED`，但本checkpoint仅记录decision，Red尚未开始。
- 当前未创建或修改production、tests、schema或migration；未修改SPEC/PLAN，未stage、commit、push或merge。

### Red phase evidence

- `2026-07-29 12:55:32 +0800`：Gate transition=`APPROVED FOR RED → RED COMPLETE`【CONTEMPORANEOUS / VERIFIED】。
- `RED_STARTED`后仅新增批准路径`tests/integration/recovery/test_startup.py`；未创建或修改production、schema或migration，未修改WP-14 RecoveryCoordinator、WP-17 lease、WP-16 event、Task lifecycle、`SPEC.md`或`PLAN.md`。
- Red contract覆盖candidate discovery、validated bounded/read-only journal enumeration、DomainEvent非authority；WP-18仅scan/classify/request ownership/delegate且不直接修改文件；stale/recovery lease与普通执行阻断；missing journal、DB/disk mismatch、incomplete evidence fail closed；duplicate startup ProcessLock/ExecutionLease边界。
- PLAN精确行为节点覆盖`test_scan_lease/container/apply/check_journal`、`test_uncertain_effect_recovers`、`test_clarification_paused`、`test_approval_cleanup_release`、`test_revision_history`、`test_old_approval_invalidated`及`test_unapproved_revision_no_write`；另有真实SQLite candidate query、finding append-only persistence及六个owned Requirement参数节点。
- Requirement evidence覆盖`PST-018`、`PST-025`、`PST-026`、`PST-027`、`PST-028`与`TST-002`，每个节点断言可观察行为而非类型存在。
- Collect-only命令收集`27 tests in 0.09s`、退出码`0`；完整target Red为`27 failed in 3.32s`、退出码`1`【CONTEMPORANEOUS / VERIFIED】。
- Failure classification=`27 × EXPECTED_INTERFACE_MISSING`：`coding_harness.application.startup_recovery`及批准的后续public contracts尚不存在。Failure发生于测试执行阶段并由test loader显式转换为pytest failure；无collection error、environment error或无关import error。
- `WP18_RED_GATE = COMPLETE`；下一阶段为`IMPLEMENTATION`，必须等待明确授权。本checkpoint不授权production实现、stage、commit、merge或push。

### Implementation milestone

- `2026-07-29 13:09:04 +0800`：Gate transition=`RED COMPLETE → IMPLEMENTATION`；`IMPLEMENTATION_STARTED`【CONTEMPORANEOUS / VERIFIED】。
- 实际production修改严格为批准的`src/coding_harness/application/startup_recovery.py`、`src/coding_harness/transaction/journal.py`、`src/coding_harness/persistence/ports.py`与`src/coding_harness/persistence/sqlite_store.py`；另修改Red test及两份过程文档。未修改schema/migration、SPEC/PLAN或其他WP文件。
- `RecoveryFinding`、`StartupRecoveryReport`与container observation均为frozen/slots模型；finding kind、evidence status与decision使用闭合enum，identity/reason有UTF-8 byte bounds，finding ID由规范化字段确定性digest生成。
- `StartupRecovery.scan`只编排可信authority：WP-15提供candidate/finding audit、WP-14提供validated journal snapshot与注入的recovery delegate、WP-17提供lease current/CAS recovery acquisition；DomainEvent reader不用于发现或决定truth。WP-18不实现rollback/restore、不修改journal、Task lifecycle或lease、不自动释放ownership。
- Journal enumeration只读使用既有owned/private directory验证、bounded file read、Apply Plan解析与journal phase复检；结果按目录名确定排序，超限、损坏、缺失journal phase均fail closed。
- WP-15 port新增`StartupRecoveryCandidate`、`RecoveryFindingRecord`及两个purpose-specific业务接口；SQLite adapter只返回domain model并追加幂等`STARTUP_RECOVERY_FINDING` audit marker，不暴露connection/cursor或通用SQL，不新增schema/migration。
- 首轮target Green为`22 passed / 5 failed`。Systematic root-cause analysis确认：`test_check_journal` fixture跳过既有`BACKUP_READY`；mismatch断言错误要求恰好一条；stale-approval fixture错误保留默认Apply transaction；production enumeration未拒绝被删除journal文件产生的`phase=None`。修正fixture/断言并使缺失phase fail closed后，selected=`5 passed in 0.12s`【CONTEMPORANEOUS / VERIFIED】。
- Final target Green=`27 passed in 0.19s`；persistence regression=`54 passed in 0.59s`；transaction regression=`100 passed in 8.11s`【CONTEMPORANEOUS / VERIFIED】。
- Full pytest=`826 passed / 1 failed in 25.95s`；唯一failure=`test_worktree_baseline_is_clean`，由7个批准的WP-18预提交dirty paths触发，分类为process cleanliness gate而非behavior regression。排除该自指节点的完整行为集合=`826 passed / 1 deselected in 25.90s`【CONTEMPORANEOUS / VERIFIED】。
- Gate transition=`IMPLEMENTATION → REVIEW PENDING`；`WP18_IMPLEMENTATION_STATUS = COMPLETE`，`WP18_REVIEW_STATUS = PENDING`。当前不授权stage、commit、merge或push。

### Review and review-fix checkpoint

- `2026-07-29 13:34:00 +0800`：独立review开始，Gate transition=`IMPLEMENTATION → REVIEW`【CONTEMPORANEOUS / VERIFIED】。
- Verdict=`CHANGES REQUIRED`。Critical finding为WP-15 candidate与WP-14 journal只按transaction ID匹配，未校验phase、journal reference及已有plan identity，矛盾证据可能被错误标记为verified。Important findings为task/workspace/approval/cleanup与BlockedReason证据不足、重复transaction journal静默覆盖、container probe未由orchestrator独立限界、真实WP-14 RecoveryCoordinator contract未适配、ACTIVE stale lease未经WP-17 expiration authority推进，以及candidate/finding/post-delegation observation persistence failure缺少注入证据【CONTEMPORANEOUS / VERIFIED】。
- Gate transition=`REVIEW → CHANGES_REQUIRED → REVIEW_FIX`；`REVIEW_FIX_STARTED`。修复范围保持已批准文件，不新增migration，不修改Task lifecycle、WP-14 recovery算法、WP-17 lease authority或WP-16 event authority；WP-18仍仅负责scan、deterministic classification与authority delegation。
- Review-fix Red=`29 failed / 10 passed`：新增契约在旧实现上精确暴露Apply evidence binding、workspace/cleanup/BlockedReason、duplicate journal、container bound、WP-14 adapter、ACTIVE stale lease与persistence failure缺口；无collection/environment failure【CONTEMPORANEOUS / VERIFIED】。
- Evidence consistency现同时绑定transaction ID、canonical journal reference、Apply phase及存在时的Apply Plan digest；任一矛盾均产生blocking `EVIDENCE_MISMATCH`且禁止delegate。Journal enumeration拒绝非canonical目录及重复transaction identity，orchestrator也禁止重复字典折叠。
- Approval wait只有在当前Plan Version binding、workspace安全相对引用与inode identity、container/file-effect/cleanup三项证据均verified时才可`RELEASE_ALLOWED`；缺失证据fail closed。`BLOCKED` candidate要求闭合`BlockedReason`并把reason与确定next command带入finding；WP-18不改变Task state。
- Container probe输出由WP-18再次验证为bounded tuple。`RecoveryCoordinatorAdapter`只绑定trusted target root并按真实WP-14 `recover(transaction_id, target_root)` contract委托，不复制恢复算法。ACTIVE stale lease仅调用WP-17 `mark_expired` authority，再使用返回revision执行`acquire_recovery` CAS；WP-18无直接lease mutation。
- Persistence failure注入覆盖candidate query、finding append及delegate后Apply observation；失败均中止scan且不返回recovery success。Green evidence：WP-18=`39 passed in 0.30s`、persistence=`54 passed in 4.52s`、transaction=`100 passed in 9.83s`、完整行为集合=`838 passed / 1 deselected in 25.92s`【CONTEMPORANEOUS / VERIFIED】。
- `git diff --check`与artifact检查PASS；未新增migration，未修改SPEC/PLAN、WP-14 recovery算法、WP-17 lease authority、WP-16 event authority或Task lifecycle。Gate transition=`REVIEW_FIX → REVIEW_FIX_COMPLETE`；下一阶段=`FINAL_REVIEW`，当前不授权commit。

### Final review and final-review-fix checkpoint

- `2026-07-29 14:03:00 +0800`：Gate transition=`REVIEW_FIX_COMPLETE → FINAL_REVIEW`，独立final review开始【CONTEMPORANEOUS / VERIFIED】。
- Verdict=`CHANGES REQUIRED`。Critical finding为不同owner的ACTIVE recovery lease可被startup直接复用，绕过WP-17 owner/revision CAS；Important findings为approval type/consumed/revoked/expiry未进入有效性判断、真实SQLite adapter不能提供workspace/cleanup evidence却由fake测试宣称release capability，以及workspace中间symlink可逃逸task root【CONTEMPORANEOUS / VERIFIED】。
- Gate transition=`FINAL_REVIEW → CHANGES_REQUIRED → FINAL_REVIEW_FIX`；`FINAL_REVIEW_FIX_STARTED`。本轮只允许关闭上述四项，不新增migration，不改变WP-14 recovery或WP-17 lease authority，不修改Task lifecycle、DomainEvent authority、SPEC或PLAN。
- Final-review-fix selected Red=`6 failed / 1 passed / 39 deselected`；approval lifecycle contract缺失、不同owner ACTIVE recovery lease直接delegate、workspace intermediate-symlink escape均有失败证据。旧recovery lease exact Red=`1 failed`，证明WP-14 delegate在没有新WP-17 ownership时被调用【CONTEMPORANEOUS / VERIFIED】。
- 所有ACTIVE lease均不在startup继承。WP-18只请求WP-17 `mark_expired`；只有authority确认过期并返回新revision后，才用该revision执行`acquire_recovery`并获得全新lease identity与startup owner binding。未过期、persistence failure或CAS conflict均保持blocking，不delegate。
- Startup candidate从既有approval payload携带闭合ApprovalType、consumed、revoked与expires_at；无需migration。等待Plan approval仅接受未消费、未撤销、未过期且绑定当前Plan Version的`PLAN_APPROVAL`，其他情况产生blocking evidence mismatch。
- SQLite production adapter没有已存在的cleanup/workspace持久化事实时明确返回unknown defaults；orchestrator因此禁止`RELEASE_ALLOWED`。Fake candidate仅验证窄port接受上层可信evidence，不再被解释为production persistence capability。
- Task-root inode在coordinator构造时绑定；workspace验证重新打开并核对root identity，再以descriptor-relative `O_NOFOLLOW|O_DIRECTORY`逐层遍历，拒绝root replacement、intermediate symlink与非owned目录，不执行清理或文件修改。
- Final Green：WP-18=`46 passed in 0.30s`、persistence=`54 passed in 0.75s`、transaction=`100 passed in 8.66s`；full=`845 passed / 1 failed in 29.24s`，唯一failure为预提交dirty paths触发的cleanliness gate；完整行为集合=`845 passed / 1 deselected in 26.65s`【CONTEMPORANEOUS / VERIFIED】。
- `git diff --check`、artifact、冻结SPEC/PLAN与scope检查PASS；无migration、Task lifecycle、WP-14 recovery、WP-17 lease或WP-16 event修改。Gate transition=`FINAL_REVIEW_FIX → FINAL_REVIEW_FIX_COMPLETE`；下一阶段为再次独立Final Review，当前不授权commit。

### Final review retry and fix 2 checkpoint

- `2026-07-29 14:32:00 +0800`：Final Review Retry verdict=`CHANGES_REQUIRED`。Remaining Critical为`acquire_recovery`返回对象未验证requested new lease identity、old identity排除、startup owner、RECOVERY purpose、ACTIVE status及new-acquisition revision；remaining Important为Plan Version两侧均缺失时`None == None`可被视为binding【CONTEMPORANEOUS / VERIFIED】。
- Gate transition=`FINAL_REVIEW → CHANGES_REQUIRED → FINAL_REVIEW_FIX`；`FINAL_REVIEW_FIX_STARTED`。本轮只增加完整ownership proof validation与non-null Plan Version binding；不修改WP-17 lease authority、WP-14 recovery authority，不新增migration，不修改SPEC/PLAN。
- Final-review-fix-2 selected Red=`6 failed / 46 deselected`：old lease ID、old owner、wrong purpose、wrong status、wrong revision五类adversarial returned proof均错误到达WP-14 delegate；缺失Plan Version双侧binding错误进入`RELEASE_ALLOWED`【CONTEMPORANEOUS / VERIFIED】。
- Delegate前验证returned lease ID必须等于本次requested deterministic identity且不同old lease ID，task/run必须匹配pending lease，owner必须为current startup owner，purpose/status必须为`RECOVERY/ACTIVE`，revision必须为WP-17新acquisition revision `1`。任一不一致追加blocking `EVIDENCE_MISMATCH`并清除recovery lease，禁止WP-14调用；WP-18仍不修改lease。
- Plan approval validation先要求current Plan Version identity与approval-bound Plan Version identity均明确存在，再进行equality；缺失任一identity即blocking mismatch，不允许`None == None`。
- Selected Green=`6 passed / 46 deselected in 3.03s`；WP-18=`52 passed in 3.16s`、persistence=`54 passed in 0.75s`、transaction=`100 passed in 8.44s`；full=`851 passed / 1 failed in 26.08s`，唯一failure为预提交cleanliness gate，排除后=`851 passed / 1 deselected in 27.70s`【CONTEMPORANEOUS / VERIFIED】。
- `git diff --check`、artifact、冻结SPEC/PLAN与scope检查PASS；无migration或WP-14/WP-17 authority修改。Gate transition=`FINAL_REVIEW_FIX → FINAL_REVIEW_FIX_COMPLETE`；下一阶段为独立Final Review，当前不授权commit。

### Final review pass and commit-preparation checkpoint

- `2026-07-29 14:20:13 +0800`：Final Review Retry 2完成，verdict=`PASS`，Critical=`0`、Important=`0`、Minor=`0`【CONTEMPORANEOUS / VERIFIED】。
- Recovery ownership proof finding已关闭：WP-18在WP-14 delegate前验证本次requested新lease identity且排除旧identity，并验证startup owner、`RECOVERY` purpose、`ACTIVE` status及WP-17新acquisition revision；任一不一致保持blocking且不delegate。Strict Plan Version binding finding已关闭：current与approval-bound identity必须分别非空后才允许相等比较，缺失binding不能产生`RELEASE_ALLOWED`。
- Authority boundary verification=`PASS`：WP-18仅执行startup scan、classification与authority delegation；WP-14仍执行recovery，WP-15仍负责persistence，WP-17仍负责lease mutation/CAS，WP-16 DomainEvent不作为recovery truth。无migration、Task lifecycle、SPEC/PLAN或WP-14/WP-16/WP-17越界修改。
- Final verification：WP-18=`52 passed in 4.65s`、persistence=`54 passed in 1.02s`、transaction=`100 passed in 11.13s`；full=`851 passed / 1 failed in 28.10s`，唯一failure为批准dirty paths触发的预提交cleanliness gate【CONTEMPORANEOUS / VERIFIED】。
- Gate transition=`FINAL_REVIEW_FIX_COMPLETE → FINAL_REVIEW_PASS → COMMIT_PREPARATION`。当前未stage、commit、merge或push。

### [RETROSPECTIVE] WP-18 Final Closeout checkpoint

- [RETROSPECTIVE] [VERIFIED] Commit completion：WP-18 implementation commit=`91dcc65893a2b58209a66bdbb6b72d277fb807b7`，message=`feat(recovery): implement startup recovery orchestration`。
- [RETROSPECTIVE] [VERIFIED] PR merge：merge commit=`e1086b3cf3975b03a06d42039e9f34fd853325e9`，message=`Merge pull request #9 from Shelia-YX/wp-18-startup-recovery`；其第二parent为WP-18 implementation commit。
- [RETROSPECTIVE] [VERIFIED] Main synchronization：local main、local `origin/main` tracking ref与remote actual main均为merge commit，ahead/behind=`0/0`，working tree clean；remote feature branch已删除。
- [RETROSPECTIVE] [VERIFIED] Regression evidence：clean main完整pytest=`852 collected / 852 passed / 0 failed in 28.36s`；WP-13至WP-18 commits均为main ancestor，当前main artifact scan clean。
- [RETROSPECTIVE] [VERIFIED] Final process gate：`WP18_FINAL_REVIEW_PASS → WP18_MERGED_VERIFIED → WP18_CLOSED`。

## WP-19 Initialization checkpoint

- `2026-07-29 15:03:10 +0800`：WP-19 ownership开始；从clean main创建linked worktree=`.worktrees/wp-19-profile-preflight-doctor`与branch=`wp-19-profile-preflight-doctor`【CONTEMPORANEOUS / VERIFIED】。
- Main baseline与WP-19 HEAD均为`03c255e2d0a290a75bb076cda239651b75c00c68`；初始worktree clean，WP-13至WP-18 implementation commits均为HEAD ancestor【CONTEMPORANEOUS / VERIFIED】。
- 文档修改前的完整baseline regression=`852 collected / 852 passed / 0 failed in 26.45s`，禁用bytecode与pytest cache【CONTEMPORANEOUS / VERIFIED】。
- 当前仅完成初始化证据记录；未开始planning分析，未创建或修改production、tests、migration、SPEC或PLAN。
- Gate transition=`INIT → PLANNING`；当前状态=`INIT COMPLETE / READY FOR PLANNING`，尚未授权planning之外的工作、stage、commit或push。

### WP-20 Planning checkpoint

- `2026-07-30 11:00:36 +0800`：`PLANNING_STARTED`；读取WP-20 frozen Requirement/PV、错误表与精确文件/测试接口，并核对WP-13至WP-19现有authority和消费接口【CONTEMPORANEOUS / VERIFIED】。
- Authority boundary：WP-20仅拥有Docker CLI adapter、container lifecycle、runtime evidence及timeout/cancel/cleanup行为。WP-13/14/15/16/17/18/19分别继续拥有ChangeSet、Apply/Recovery runtime、Persistence/Audit、DomainEvent、ExecutionLease、Startup Recovery orchestration及Profile/Preflight/Doctor；WP-20不得修改这些authority、Task lifecycle或SQLite。
- Requirement mapping覆盖PLAN-owned `SEC-002..006, SEC-009, ACT-007, SBX-001, SBX-006..012`；WP-19 scope ADR延期的image trust `SBX-004`与真实Docker evidence `TST-003`由WP-20实现/验证。Supporting boundary包括`SEC-013`的输出过滤以及Appendix E中Docker/timeout/cleanup结果，但状态转换与持久化由其既有owner处理。
- Recommended design：`DockerCLI.run`仅接受内部闭合operation并使用startup-resolved absolute executable、positive environment allowlist、固定local Unix endpoint、structured argv与`shell=False`；`ContainerLifecycle.execute`消费trusted profile/workspace/run binding，执行image inspect/allowlist、`create --pull=never`、pre-start inspect安全复核、start/attach、post-run inspect及确定性cleanup。用户/仓库/LLM不能提供Docker argv、endpoint、image或安全模板。
- Lifecycle evidence使用frozen/slots closed enums与canonical digest，绑定container/image/command/task-run identity、phase/exit、timeout/cancel、bounded output、timestamps和cleanup verification。`CLEANUP_FAILED`只作为blocking runtime result/evidence返回；WP-20不直接转Task、修改Lease或执行WP-18 recovery。
- Unit strategy使用fake process/clock/cancel source覆盖argv/env、bounded parsing、all failure points及cleanup ordering；单独真实Docker marker覆盖安全inspect、timeout、cancel、crash、cleanup和residual detection，满足`TST-003`，且没有host fallback。
- Blocker 1：两个MVP profile均无人工批准的精确`name@sha256`可信image identity；floating tag与自行选择public image均不允许。
- Blocker 2：冻结SPEC要求CPU、memory、PID、timeout、output与stop-grace硬限制，但未给数值；实现者不得自行建立安全策略。
- Blocker 3：当前`/snap/bin/docker`执行`docker version`失败（DBus transient-scope error），可信local Unix endpoint未确认，因此当前环境不能提供真实Docker Green evidence。
- Proposed scope严格为production=`src/coding_harness/sandbox/docker_cli.py`、`src/coding_harness/sandbox/lifecycle.py`；tests=`tests/docker/test_executor.py`。无需schema/migration，不修改WP-13至WP-19文件。
- Gate=`INIT → PLANNING → PLANNING BLOCKED / WAITING HUMAN DECISION`；`RED_NOT_AUTHORIZED`，当前未创建production/tests或进入implementation。

### WP-19 Planning checkpoint

- `2026-07-29 15:08:13 +0800`：`PLANNING_STARTED`；读取冻结`SBX-002..005`、`SBX-013`、`ACC-008..009`、`TST-003`、Appendix G与PLAN WP-19精确文件/PV，并核对WP-13至WP-18 authority及现有`run_validation`、Acceptance evidence接口【CONTEMPORANEOUS / VERIFIED】。
- Architecture boundary：WP-19只定义固定、不可变profile registry，按可信repository signals确定性选择profile，以结构化probe facts进行preflight classification，并生成有界、确定性、read-only doctor report。WP-19不执行Docker workload、不安装依赖、不通过stderr推断missing dependency、不修改Task/Lease/Transaction/Recovery、不成为persistence/event authority。
- Requirement mapping覆盖owned `SBX-002..005`、`SBX-013`、`ACC-008..009`、`TST-003`；supporting boundary包括`GEN-005`、`GEN-008..010`、`SEC-005`、`SEC-013`、`POL-024`与Appendix B blocked reasons。WP-20依赖profile/doctor contract实现Docker adapter/lifecycle；WP-27依赖Node profile；WP-28/29消费最终acceptance evidence。
- Proposed scope保持PLAN精确文件：production=`src/coding_harness/sandbox/profiles.py`、`src/coding_harness/sandbox/doctor.py`；tests=`tests/unit/sandbox/test_profiles.py`、`tests/docker/test_doctor.py`。无需schema/migration，不修改WP-14至WP-18 authority实现。
- Blocker 1：SPEC规定profile image必须来自可信allowlist并固定version或digest，但未提供Python 3.12和Node.js 20/npm的具体可信image identity；实现者不能自行选择镜像并建立trust。
- Blocker 2：PLAN将`TST-003`归属WP-19，但该requirement要求真实Docker CLI adapter对安全配置、timeout、cancel、cleanup的独立集成测试；adapter/lifecycle及`test_executor.py`明确属于WP-20，不在WP-19 scope。WP-19只能建立doctor/probe contract，不能复制或提前实现WP-20。
- Human decision requested：提供/批准两个MVP固定image identity；并裁决`TST-003`为WP-19 contract/PV占位且真实adapter evidence延至WP-20（推荐），或显式批准新的requirement ownership/scope。Gate=`INIT → PLANNING → PLANNING BLOCKED / WAITING HUMAN DECISION`；`RED_NOT_AUTHORIZED`。

### WP-19 Scope Reduction Architecture Decision Record

- `2026-07-29 15:15:18 +0800`：人工批准scope reduction，将WP-19定义为`Sandbox Profile / Preflight / Doctor Contract Layer`，原planning blockers关闭【CONTEMPORANEOUS / APPROVED DECISION】。
- WP-19 responsibility：固定Python 3.12与Node.js 20/npm profile的runtime identity、validation operations、repository recognition signals及deterministic profile digest；bounded `RepositorySignals`的deterministic/immutable/fail-closed selection；只根据structured facts产生`READY`、`BLOCKED_MISSING_DEPENDENCY`或`BLOCKED_UNSUPPORTED_ENVIRONMENT`的preflight classification；生成只读`DoctorReport`及`ValidationEvidence` contract。禁止LLM、repository或user覆盖runtime/profile authority，禁止根据stderr推断dependency failure。
- Deferred to WP-20：可信image resolution/digest verification（`SBX-004`），以及真实Docker CLI、安全配置、timeout、cancellation、cleanup和execution evidence（`TST-003`）。WP-19不得以fake contract证据宣称上述deferred requirements已满足。
- Authority boundary保持：WP-14拥有Apply/Rollback/Recovery；WP-15拥有Persistence/Audit；WP-16拥有DomainEvent facts；WP-17拥有Execution ownership；WP-18拥有Startup recovery orchestration；WP-19只拥有Profile/Preflight/Doctor contracts；WP-20拥有Docker execution与image resolution。WP-19不得执行Docker lifecycle/pull/build/run/repair/cleanup，不得直接持久化或修改Task/Lease。
- Approved file scope：production=`src/coding_harness/sandbox/profiles.py`、`src/coding_harness/sandbox/preflight.py`、`src/coding_harness/sandbox/doctor.py`；tests=`tests/unit/sandbox/test_profiles.py`、`tests/unit/sandbox/test_preflight.py`、`tests/unit/sandbox/test_doctor.py`。禁止migration/schema/`sqlite_store.py`/lease/transaction/recovery修改。
- Requirement ownership调整：WP-19 owned=`SBX-002, SBX-003, SBX-005, SBX-013, ACC-008, ACC-009`；deferred to WP-20=`SBX-004, TST-003`。
- Gate transition=`PLANNING BLOCKED → PLANNING COMPLETE → APPROVED FOR RED`；`RED_NOT_STARTED`，当前未授权production implementation。

### WP-19 Red checkpoint

- `2026-07-29 15:21:08 +0800`：`RED_STARTED`；仅新增批准的`tests/unit/sandbox/test_profiles.py`、`tests/unit/sandbox/test_preflight.py`、`tests/unit/sandbox/test_doctor.py`【CONTEMPORANEOUS / VERIFIED】。
- Profile contract tests覆盖精确Python 3.12与Node.js 20/npm registry、immutability、deterministic digest、repository-signal selection、ambiguous/unsupported fail-closed、LLM suggestion不覆盖确定性选择，以及repository image/runtime override拒绝。
- Preflight contract tests覆盖structured READY/missing dependency/unsupported environment、stderr不得推断dependency missing、malformed/UTF-8 oversized evidence fail-closed及ACC-009 `ValidationEvidence`必需字段、immutability与deterministic digest。
- Doctor contract tests覆盖runtime availability、workspace mapping、configured capability classification、UTF-8 byte bound、deterministic report digest，并明确report无repair/cleanup能力。Requirement behavior nodes覆盖owned `SBX-002, SBX-003, SBX-005, SBX-013, ACC-008, ACC-009`。
- Collect-only=`30 tests collected in 0.02s`、exit 0；target Red=`30 failed in 0.06s`，全部为`EXPECTED_INTERFACE_MISSING`，无collection、syntax、test-import或environment failure【CONTEMPORANEOUS / VERIFIED】。
- 未创建production/schema/migration/Docker adapter，未修改SPEC/PLAN。Gate transition=`APPROVED FOR RED → RED COMPLETE`；下一阶段=`IMPLEMENTATION`，当前仍未授权implementation/commit/push。

### WP-19 Implementation checkpoint

- `2026-07-29 15:29:22 +0800`：Gate transition=`RED COMPLETE → IMPLEMENTATION`；`IMPLEMENTATION_STARTED`【CONTEMPORANEOUS / VERIFIED】。
- Approved scope内新增`src/coding_harness/sandbox/profiles.py`、`preflight.py`、`doctor.py`。所有公开contract为frozen/slots模型与闭合enum；UTF-8 byte bounds、tuple normalization及canonical JSON/SHA-256提供deep immutability与deterministic digest。
- `ProfileRegistry`精确包含Python 3.12与Node.js 20/npm；bounded `RepositorySignals`只接收规范化相对文件信号，拒绝runtime/image override。Selection由代码根据Python/Node recognition signals确定；mixed为`AMBIGUOUS`、无匹配为`UNSUPPORTED`，均fail closed；LLM suggestion不改变选择结果。
- `Preflight`只消费structured `ProbeEvidence`，按runtime identity、explicit missing dependencies与required validation operation产生`READY`、`BLOCKED_MISSING_DEPENDENCY`或`BLOCKED_UNSUPPORTED_ENVIRONMENT`；`validation_stderr`只作为有界事实进入digest，绝不参与dependency分类。`ValidationEvidence`绑定action/profile/exit/bounded summary/time并产生deterministic digest。
- `Doctor`只把runtime availability、workspace mapping与configured capability facts转换为有界`DoctorReport`；没有repair/cleanup或Docker lifecycle API，不执行任何外部命令。
- Target首次Green=`30 passed in 0.05s`。Full pytest=`881 passed / 1 failed in 26.01s`，唯一failure为批准的8个预提交dirty paths触发cleanliness gate；排除该自指节点后=`881 passed / 1 deselected in 26.89s`【CONTEMPORANEOUS / VERIFIED】。
- Scope/diff/artifact检查PASS：无SQLite、Task/Lease/Transaction/Recovery、Docker adapter/execution/lifecycle、schema/migration、SPEC/PLAN修改。Gate=`IMPLEMENTATION COMPLETE / REVIEW PENDING`；本阶段不进入Review且未commit/push。

### WP-19 Review and review-fix checkpoint

- `2026-07-29 15:46:45 +0800`：`REVIEW_STARTED`；review verdict=`CHANGES_REQUIRED`。Important findings为DoctorReport digest未绑定runtime、workspace及capability事实身份，以及ValidationEvidence没有公开、可测试的canonical bytes合同；Minor finding为RepositorySignals/ValidationEvidence资源限界及`SBX-013`显式requirement evidence不足【CONTEMPORANEOUS / VERIFIED】。
- Gate transition=`REVIEW → CHANGES_REQUIRED → REVIEW_FIX_STARTED`。修复严格限于批准的WP-19 contract production、unit tests与两份过程文档；不增加Docker/image resolution、SQLite/migration/persistence、lease、transaction或recovery能力。
- Review-fix Red=`5 failed / 34 passed`：runtime identity、workspace reference、capability identity变化均未改变DoctorReport digest；`ValidationEvidence.canonical_bytes()`两个合同节点因接口缺失失败。失败来自预期behavior/interface缺口，无collection或environment failure【CONTEMPORANEOUS / VERIFIED】。
- `DoctorFacts`现生成绑定runtime identity/availability、workspace reference/mapping、capability identities/trust及bounded output的immutable事实digest，`DoctorReport`显式绑定该source digest。`ValidationEvidence.canonical_bytes()`使用固定字段、canonical JSON及UTF-8 bytes；evidence digest直接由`sha256(canonical_bytes())`计算。
- Bounds evidence覆盖RepositorySignals最大signal count与UTF-8 path byte limit、ValidationEvidence oversized output rejection；参数化行为节点显式覆盖owned `SBX-002, SBX-003, SBX-005, SBX-013, ACC-008, ACC-009`。
- Green=`39 passed in 0.05s`。Full pytest=`890 passed / 1 failed in 29.56s`，唯一failure为8个批准预提交dirty paths触发的process cleanliness gate，不是behavior regression【CONTEMPORANEOUS / VERIFIED】。
- Gate transition=`REVIEW_FIX_STARTED → REVIEW_FIX_COMPLETE`；下一阶段=`FINAL_REVIEW`。当前未stage、commit或push。

### WP-19 Final Review checkpoint

- `2026-07-29 15:55:37 +0800`：Final Review verdict=`PASS`，Critical=`0`、Important=`0`、Minor=`0`【CONTEMPORANEOUS / VERIFIED】。
- Doctor evidence integrity=`PASS`：runtime identity、workspace reference与capability identities完整进入immutable DoctorFacts digest，DoctorReport绑定source facts digest；对抗测试证明任一身份变化均改变report digest。
- ValidationEvidence canonical serialization=`PASS`：公开`canonical_bytes()`为固定字段、确定性UTF-8 canonical JSON表示，digest直接等于`sha256(canonical_bytes())`。
- Requirement verification=`SBX-002, SBX-003, SBX-005, SBX-013, ACC-008, ACC-009 PASS`。Scope boundary=`PASS`：无Docker/image authority、SQLite/migration/persistence、lease、transaction或recovery越界。
- Sandbox evidence=`39 passed in 0.05s`。Full regression=`890 passed / 1 failed in 29.68s`；唯一failure为8个批准WP-19预提交dirty paths触发的process cleanliness gate，不是behavior regression，提交后需在clean worktree重新关闭该门禁【CONTEMPORANEOUS / VERIFIED】。
- Gate transition=`FINAL_REVIEW_FIX_COMPLETE → FINAL_REVIEW_PASS → COMMIT_PREPARATION`。当前未stage、commit或push。

### [RETROSPECTIVE] WP-19 Final Closeout checkpoint

- [RETROSPECTIVE] [VERIFIED] Commit completion：WP-19 implementation commit=`0867baefa6eb90652063f85a8521230d56aac656`，message=`feat(sandbox): implement profile preflight and doctor contracts`。
- [RETROSPECTIVE] [VERIFIED] PR merge：merge commit=`4108ec6a64cb90e948f4a0d5c4291262bdb73563`，message=`Merge pull request #10 from Shelia-YX/wp-19-profile-preflight-doctor`；其第二parent为WP-19 implementation commit。
- [RETROSPECTIVE] [VERIFIED] Main synchronization：local main、local `origin/main` tracking ref与remote actual main均为merge commit，ahead/behind=`0/0`，working tree clean；remote feature branch已删除。
- [RETROSPECTIVE] [VERIFIED] Main regression evidence：clean main完整pytest=`891 collected / 891 passed / 0 failed in 28.87s`；WP-13至WP-19 commits均为main ancestor，main-scope artifact scan clean。
- [RETROSPECTIVE] [VERIFIED] Final process gate：`WP19_FINAL_REVIEW_PASS → WP19_MERGED_VERIFIED → WP19_CLOSED`。

## WP-20 Initialization checkpoint

- `2026-07-30 10:53:51 +0800`：WP-20 ownership开始；从最新clean main创建linked worktree=`.worktrees/wp-20-docker-execution-lifecycle`与branch=`wp-20-docker-execution-lifecycle`【CONTEMPORANEOUS / VERIFIED】。
- Main与WP-20 HEAD均为baseline commit=`b43b26bc6d08f817c534d8e21f820aa600b0b4f5`；新worktree初始clean、staging empty，WP-13至WP-19 implementation commits均为HEAD ancestor【CONTEMPORANEOUS / VERIFIED】。
- 文档修改前的完整baseline regression=`891 collected / 891 passed / 0 failed in 26.63s`，使用Python 3.12并禁用bytecode与pytest cache【CONTEMPORANEOUS / VERIFIED】。
- 当前仅完成初始化；未开始planning分析，未创建或修改production、tests、schema、migration、SPEC或PLAN。
- Gate transition=`INIT → PLANNING`；当前状态=`INIT COMPLETE / READY FOR PLANNING`，尚未授权planning之外的工作、stage、commit或push。

### WP-20 Scope Reduction Architecture Decision

- `2026-07-30 11:06:49 +0800`：人工批准课程项目级scope reduction，关闭先前关于digest image identity、工业级安全策略数值与当前Docker环境的planning blocker【CONTEMPORANEOUS / APPROVED DECISION】。
- Architecture understanding：WP-19选择固定profile并提供Preflight/Doctor contract；WP-20把批准profile映射到固定tag `python:3.12`或`node:20`，通过窄Docker CLI adapter执行create、start、wait与cleanup，处理timeout并返回有界execution result evidence。WP-20不持久化事实、不取得lease、不修改Task/transaction/recovery状态，也不替代WP-14至WP-19任何authority。
- Requirement mapping：
  - `SBX-006`：输入为内部闭合Docker operation；输出为结构化CLI结果；owner=WP-20 adapter；以无shell、无用户Docker argv的unit test验证。
  - `SBX-010`：输入为固定profile/tag、workspace与validation operation；输出为create/start/wait/cleanup生命周期结果；owner=WP-20 lifecycle wrapper；以调用顺序、失败短路与cleanup integration test验证。原security-inspect部分不在本次课程scope。
  - `SBX-011`：WP-20只拥有timeout与cleanup结果；cancel/security hardening部分延期；以timeout后cleanup及残留结果测试验证当前子集。
  - `SBX-012`：Docker不可用或生命周期失败必须结构化失败且不得host fallback；以unavailable/failure tests验证。
  - `SBX-004`：人工批准课程实现固定tag policy=`python:3.12`,`node:20`；digest verification与供应链安全延期。生产环境应使用digest pinning，本WP不得宣称完成该安全保证。
  - `TST-003`：WP-20提供真实Docker adapter/lifecycle的课程级integration evidence；digest trust、capability/namespace/security-hardening证据延期。
  - `ACC-009`：WP-20仅产出可供既有Acceptance owner消费的execution evidence，不决定acceptance结论。
  - 冻结PLAN中`SEC-002..006, SEC-009, SBX-007..009`及`SBX-010/011/TST-003`的工业安全部分被明确延期、未验证；`ACT-007`继续由既有Policy authority负责，不迁移至Docker runtime。
- Implementation scope：production仅允许`src/coding_harness/sandbox/docker_cli.py`与`src/coding_harness/sandbox/lifecycle.py`；tests仅允许`tests/docker/test_executor.py`。不新增schema/migration，不修改SQLite、lease、event、transaction、recovery、profile/preflight/doctor或Task lifecycle。
- Test strategy：使用fake subprocess/clock对structured argv、固定tag allowlist、create/start/wait/cleanup ordering、non-zero exit、timeout、cleanup failure、bounded output与deterministic evidence做离线测试；在Docker可用环境对Python与Node固定tag执行真实success/failure/timeout/cleanup integration。Docker不可用必须明确分类为environment/unavailable且无host fallback。当前Snap Docker错误是后续真实integration Green的环境依赖，不阻塞Red contract。
- Risks：floating tags可变且不提供供应链完整性；本scope不提供工业级container isolation；Docker daemon本身是高权限外部依赖；timeout后的cleanup可能失败并留下residual container；output bounds与evidence只能证明wrapper观察结果，不能构成安全沙箱证明。以上限制必须在完成报告中保留。
- Human decision：人工接受上述课程级保证与延期项，无剩余architecture blocker；Red仅应针对已批准的adapter/lifecycle contract建立失败证据，不得用测试重新引入延期的工业安全scope。
- Gate transition=`PLANNING BLOCKED → PLANNING COMPLETE → APPROVED FOR RED`；当前=`RED_NOT_STARTED`，尚未创建production/test或进入implementation。

### WP-20 Red checkpoint

- `2026-07-30 11:17:00 +0800`：Gate从`APPROVED FOR RED`进入Red；`RED_STARTED`，仅创建批准的`tests/docker/test_executor.py`，未创建或修改production【CONTEMPORANEOUS / VERIFIED】。
- 12个behavior nodes覆盖：(1) structured argv；(2) `shell=False`；(3) 仅固定`python:3.12`/`node:20` tag；(4) 任意Docker参数拒绝；(5) create/start/wait/cleanup ordering；(6) normal-exit evidence；(7) non-zero evidence；(8) timeout与cleanup；(9) cleanup failure；(10) Docker unavailable/no-host-fallback；(11) deterministic canonical evidence；(12) stdout/stderr UTF-8 byte bounds。
- 测试使用记录型process runner验证真实`DockerCLI`边界、使用脚本化CLI fake隔离外部Docker并验证真实`ContainerLifecycle`行为；Red不调用Docker daemon、网络或host fallback。
- Collect-only命令=`PYTHONDONTWRITEBYTECODE=1 <project-python> -m pytest -p no:cacheprovider --collect-only tests/docker/test_executor.py -q`，结果=`12 tests collected in 0.01s`、exit 0。
- Red命令=`PYTHONDONTWRITEBYTECODE=1 <project-python> -m pytest -p no:cacheprovider tests/docker/test_executor.py -q`，结果=`12 failed in 0.02s`；全部为`EXPECTED_INTERFACE_MISSING: WP-20 Docker execution contract`，production module缺失是唯一失败原因，无collection、syntax、test-import、Docker或environment failure【CONTEMPORANEOUS / VERIFIED】。
- 环境说明：裸`python`不存在且system `python3`无pytest，正式证据改用仓库已有Python 3.12.3 / pytest 9.1.1环境；uv探测临时创建的`.venv`与`uv.lock`已在证据完成后删除，不属于工作包diff。
- Scope check：SPEC/PLAN、schema/migration及WP-13至WP-19 production均未修改；Red未重新引入digest trust、security hardening、capability/namespace policy或其他延期scope。
- Gate transition=`APPROVED FOR RED → RED COMPLETE`；下一阶段=`IMPLEMENTATION`，当前=`IMPLEMENTATION_NOT_STARTED / COMMIT_NOT_AUTHORIZED`。

### WP-20 Implementation checkpoint

- `2026-07-30 11:23:39 +0800`：Gate transition=`RED COMPLETE → IMPLEMENTATION`；`IMPLEMENTATION_STARTED`，仅创建批准的`src/coding_harness/sandbox/docker_cli.py`与`src/coding_harness/sandbox/lifecycle.py`【CONTEMPORANEOUS / VERIFIED】。
- `DockerCLI` contract：frozen closed `DockerOperation`仅含create/start/wait/remove，`FixedImage`精确为`python:3.12`与`node:20`；`DockerCommand`不暴露Docker flags，adapter使用绝对CLI path、structured argv、`subprocess` runner与固定`shell=False`。不提供build/pull/push、shell或host fallback。
- CLI result将normal/non-zero、timeout与`OSError`/Docker unavailable转为显式immutable result；wait解析container exit status，start/attach提供workload output，所有观察文本在adapter边界截断至4096 UTF-8 bytes。
- `ContainerLifecycle.execute`执行create→start/attach→wait→remove；create unavailable不尝试宿主执行，已创建容器在start/wait失败或timeout后仍进入remove，cleanup失败覆盖为`CLEANUP_FAILED`且不伪装成功。
- Frozen `ExecutionEvidence`绑定fixed image、command tuple及其SHA-256 identity、container identity、exit status、stdout/stderr summary、累计duration、occurred_at、timeout、cleanup及execution status；`evidence_digest=sha256(canonical_bytes())`，不写SQLite或其他persistence。
- Authority boundary保持：WP-20只拥有Docker process/lifecycle与runtime evidence；不选择profile、不分类preflight/doctor、不修改Task/Lease、transaction/recovery或DomainEvent，不重新引入延期的digest trust/security hardening/capability/namespace scope。
- Target命令=`PYTHONDONTWRITEBYTECODE=1 <project-python> -m pytest -p no:cacheprovider tests/docker/test_executor.py -q`，首次Green=`12 passed in 0.02s`【CONTEMPORANEOUS / VERIFIED】。
- Full regression=`902 passed / 1 failed in 26.85s`；唯一failure为五个批准WP-20预提交路径触发`test_worktree_baseline_is_clean`，属于流程cleanliness gate。排除该自指节点的完整行为集合=`902 passed / 1 deselected in 25.45s`【CONTEMPORANEOUS / VERIFIED】。
- 当前未调用真实Docker、未修改SPEC/PLAN、schema/migration或WP-13至WP-19 production，未stage/commit。Gate=`IMPLEMENTATION COMPLETE / REVIEW PENDING`。

### WP-20 Review and review-fix checkpoint

- `2026-07-30 11:38:23 +0800`：`REVIEW_STARTED`；只读review verdict=`CHANGES_REQUIRED`，Critical=`0`、Important=`5`、Minor=`1`【CONTEMPORANEOUS / VERIFIED】。
- Review findings：`container_name`仅做通用文本检查，使`--help`/`--privileged`进入start/wait/remove option位置；create timeout落入`FAILED + NOT_REQUIRED`且不cleanup；非timeout `subprocess.SubprocessError`在cleanup逃逸；`ExecutionEvidence`接受caller提供的任意hex command identity；原12 tests只验证未知keyword与脚本化CLI happy/error结果，未覆盖value-level injection、adapter/lifecycle组合及public evidence member validation。
- Gate transition=`IMPLEMENTATION COMPLETE → REVIEW → CHANGES_REQUIRED → REVIEW_FIX_STARTED`。Fix严格限于`docker_cli.py`、`lifecycle.py`、`test_executor.py`及两份过程文档，不扩大Docker security或其他WP authority。
- Review-fix collect=`26 tests collected in 0.02s`。旧实现Red=`7 failed / 19 passed in 0.10s`；七项失败为两种option-like name、create timeout cleanup、cleanup SubprocessError、command identity tampering、malformed command member与oversized command member，无collection/environment/Docker failure【CONTEMPORANEOUS / VERIFIED】。
- Fix 1：container identity必须匹配`[A-Za-z0-9][A-Za-z0-9_.-]*`，DockerCommand与ExecutionRequest使用同一验证，option-like identity在argv构造前拒绝。
- Fix 2：create timeout明确分类`TIMED_OUT`并强制请求remove；remove结果进入`COMPLETE`或`CLEANUP_FAILED` evidence，不再宣称cleanup无需执行。
- Fix 3：`DockerCLI`在`TimeoutExpired`专门分支之后捕获其他`subprocess.SubprocessError`并转换为结构化non-zero result，因此cleanup transport exception由lifecycle稳定转换为`CLEANUP_FAILED`。
- Fix 4：`ExecutionEvidence.command_identity`改为`init=False`，仅由validated command canonical bytes的SHA-256派生；caller不能传入或replace伪造。Evidence自身验证tuple、item type/count/UTF-8 bytes、output bounds，继续保持frozen/slots及deterministic digest。
- Expanded tests同时覆盖固定start/wait/remove argv、runner TimeoutExpired、malformed wait output、immutable evidence与oversized direct output；全部使用recording runner/fake adapter，不调用真实Docker。
- Green=`26 passed in 0.03s`。Full regression=`916 passed / 1 failed in 29.08s`，唯一failure为五个批准预提交paths触发cleanliness gate；排除该自指节点后=`916 passed / 1 deselected in 28.98s`【CONTEMPORANEOUS / VERIFIED】。
- Scope/boundary保持：无digest trust、industrial security hardening、build/pull/push、SQLite/persistence、lease、recovery、Profile/Preflight/Doctor或schema/migration修改；未stage/commit/push。
- Gate transition=`REVIEW_FIX_STARTED → REVIEW_FIX_COMPLETE`；下一阶段=`FINAL_REVIEW`，当前=`COMMIT_NOT_AUTHORIZED`。

### WP-20 Final Review checkpoint

- `2026-07-30 11:44:31 +0800`：Final Review verdict=`PASS`，Critical=`0`、Important=`0`、Minor=`0`【CONTEMPORANEOUS / VERIFIED】。
- Finding resolution=`PASS`：container identity option injection、create-timeout cleanup、cleanup subprocess exception、command identity tampering及Evidence validation五类finding均由production validation与adversarial tests关闭。
- DockerCLI boundary=`PASS`：绝对CLI、structured argv、固定`shell=False`、闭合create/start/wait/remove operation与固定`python:3.12`/`node:20` tag；无任意Docker flags、shell、build、pull或push。
- Lifecycle/evidence=`PASS`：create→start/attach→wait→collect→remove；normal/non-zero/timeout/unavailable/cleanup-failure均返回结构化结果；frozen Evidence绑定derived command identity、image、container、exit、duration、bounded output及deterministic digest，无host fallback或persistence side effect。
- Requirement verification=`PASS` for approved course subset：`SBX-006`、`SBX-010`、`SBX-011`、`SBX-012`及固定tag/runtime evidence合同。Deferred requirements保持：digest-level image trust与industrial container security hardening未实现、未验证、不得在WP-20 closeout中宣称满足。
- Fresh target evidence=`26 passed in 0.03s`。Full regression=`916 passed / 1 failed in 28.92s`，唯一failure为五个批准预提交paths触发cleanliness gate；排除该自指节点的行为集合=`916 passed / 1 deselected in 28.59s`【CONTEMPORANEOUS / VERIFIED】。
- Scope confirmation：无WP-15 persistence、WP-17 lease、WP-18 recovery、WP-19 Profile/Preflight/Doctor、schema/migration、SPEC/PLAN修改；staging empty，未commit/push。
- Gate transition=`FINAL_REVIEW_FIX_COMPLETE → FINAL_REVIEW_PASS → COMMIT_PREPARATION`。

### [RETROSPECTIVE] WP-20 Final Closeout checkpoint

- [RETROSPECTIVE] [VERIFIED] Implementation commit=`620d6a8f73acc84c48bd27cc00c880f2169da4b6`；commit completion由main history验证。
- [RETROSPECTIVE] [VERIFIED] PR merge message=`Merge pull request #11 from Shelia-YX/wp-20-docker-execution-lifecycle`；two-parent merge commit=`854a2969e1e459dc1ab88cfee5fd30c245251436`。
- [RETROSPECTIVE] [VERIFIED] Main synchronization=`PASS`：local main、`origin/main` tracking ref与remote actual main一致，ahead/behind=`0/0`，post-test working tree clean。
- [RETROSPECTIVE] [VERIFIED] Historical integrity=`WP-13 ~ WP-20 PASS`；clean-main regression=`917 collected / 917 passed / 0 failed in 28.88s`。
- [RETROSPECTIVE] [VERIFIED] Final process gate=`WP20_FINAL_REVIEW_PASS → WP20_MERGED_VERIFIED → WP20_CLOSED`。

## WP-21 Initialization checkpoint

- `2026-07-30 12:32:48 +0800`：WP-21 Trusted Configuration / Provider Boundary ownership开始；从clean main创建linked worktree=`.worktrees/wp-21-trusted-config-provider`及branch=`wp-21-trusted-config-provider`【CONTEMPORANEOUS / VERIFIED】。
- Main baseline与WP-21 feature HEAD均为`72ecb75e774eaa9b3b6333a0952761dc93a83b74`；`.worktrees/` ignore rule已验证，新worktree初始clean且staging empty【CONTEMPORANEOUS / VERIFIED】。
- Historical integrity=`WP-13 ~ WP-20 PASS`；各implementation commit均为WP-21 HEAD ancestor【CONTEMPORANEOUS / VERIFIED】。
- Baseline regression使用项目既有Python 3.12环境，命令禁用bytecode与pytest cache，结果=`917 collected / 917 passed / 0 failed in 28.83s`【CONTEMPORANEOUS / VERIFIED】。
- 当前仅完成初始化；未开始planning分析，未创建或修改production、tests、schema、migration、SPEC或PLAN。
- Gate transition=`INIT → PLANNING`；当前状态=`INIT COMPLETE / READY FOR PLANNING`，尚未授权implementation、stage、commit或push。

### WP-21 Planning checkpoint

- `2026-07-30 12:37:24 +0800`：`PLANNING_STARTED`；读取冻结`GEN-008..010`、`AGT-013..014`、`SEC-014..015`、Appendix E、PLAN WP-21精确文件/PV，并核对WP-13至WP-20现有authority和消费接口【CONTEMPORANEOUS / VERIFIED】。
- Architecture：WP-21位于既有Agent `LLMAdapter`与未来WP-22 credential runtime之间。它消费已经由宿主信任边界分类的defaults/host/startup配置以及WP-19 profile identity、既有Policy/Budget/sandbox/export identities；产出严格`HarnessConfig`、每Run不可变`RunConfigSnapshot`及固定Provider adapter结果。WP-21不成为Persistence、Lease、Docker execution、Transaction/Recovery、Task lifecycle或Credential authority。
- 推荐设计：`config.py`使用闭合字段、严格类型/范围和显式`startup > trusted host > defaults`合并；untrusted sources不进入API。Snapshot用canonical bytes/digest绑定provider/profile/image/endpoint、policy、budget hard limits、sandbox template和export rules。`provider.py`保持`complete(context)`兼容，构造时绑定snapshot和窄runtime credential/transport，限制timeout/request/token/response，拒绝redirect与endpoint override，以闭合错误区分`PROVIDER_UNAVAILABLE`和`PROVIDER_CONFIGURATION_ERROR`，且不自动fallback。
- Requirement mapping：`GEN-008`=strict trusted-source config construction；`GEN-009`=deterministic precedence/untrusted exclusion；`GEN-010`=immutable per-run snapshot；`AGT-013`=fixed provider/endpoint and limits；`AGT-014`=deterministic provider failure classification/no fallback；`SEC-014`=redirect rejection；`SEC-015`=untrusted endpoint override impossible。验证位置保持PLAN精确`test_config.py`与`test_provider.py`及7个参数化PV nodes。
- Failure strategy：unknown/type/range/missing/conflicting trusted configuration均在任何Provider调用前fail closed；Issue/repository/`.env`/tool/LLM/header/WebUI中的endpoint文本仅作为普通内容，不能进入配置；malformed transport/result、oversized response和redirect返回结构化failure，不能切换Provider。
- Scope保持PLAN：production仅`src/coding_harness/config.py`与`src/coding_harness/agent/provider.py`；tests仅`tests/unit/test_config.py`与`tests/unit/agent/test_provider.py`。无需schema/migration，禁止修改WP-13至WP-20 authority modules。
- Blocker 1：SPEC/PLAN未指定真实Provider identity、固定endpoint或vendor wire protocol；实现者不得自行选择OpenAI/Anthropic或发明payload schema。
- Blocker 2：SPEC/PLAN未指定trusted host/startup source representation、内置默认值以及timeout/request/token/response的具体安全硬上限；这些值影响`GEN-008`与`AGT-013`，不能凭经验冻结。
- Blocker 3：`GEN-010`要求每个Task Run冻结摘要，但PLAN WP-21精确scope只允许配置/provider文件；现有Task Run/persistence无config snapshot binding。需明确本WP只产出immutable contract、由后续orchestration/persistence接入，或显式批准scope expansion。
- Human decision requested：推荐批准课程级窄transport injection、不在WP-21实现credential store；由可信host/startup显式提供经批准的单Provider/endpoint并给出具体默认/硬上限；确认WP-21只拥有snapshot contract而不修改Task/persistence。未裁决前不得进入Red。
- Gate=`INIT COMPLETE → PLANNING → PLANNING BLOCKED / WAITING HUMAN DECISION`；`RED_NOT_AUTHORIZED`。

### WP-21 Scope Reduction Architecture Decision

- `2026-07-30 12:41:13 +0800`：人工批准scope reduction并关闭WP-21全部planning blockers【CONTEMPORANEOUS / APPROVED DECISION】。
- Provider architecture：WP-21只拥有`ProviderRequest`、`ProviderResult`、闭合`ProviderError` classification及`ProviderTransport` injection contract。HTTP client、vendor SDK、OpenAI/client implementation、credential storage与endpoint discovery均明确不属于WP-21。
- Trusted config：有效来源固定为`startup trusted config > built-in defaults`。Repository config、Issue fields、LLM suggestion、environment与`.env`不进入配置链，也不能覆盖provider或endpoint。
- Snapshot boundary：`RunConfigSnapshot`只提供immutable configuration snapshot与deterministic digest；不绑定或修改Task lifecycle、ExecutionLease、Persistence及其schema。
- Course limits冻结为：request timeout=`30 seconds`；max request bytes=`1 MiB (1,048,576 bytes)`；max response bytes=`2 MiB (2,097,152 bytes)`；max token limit=`4096`。这些值是WP-21 contract validation与ProviderTransport request边界。
- Requirement ownership调整：`GEN-008..010`由strict two-source config、precedence及immutable snapshot验证；`AGT-013..014`由fixed configured identity、四项限额、transport result/error classification及no-fallback合同验证；`SEC-014..015`由redirect rejection与untrusted endpoint override impossibility验证。真实HTTP/vendor execution和credentials不在本WP完成声明中。
- Approved scope保持：production仅`src/coding_harness/config.py`、`src/coding_harness/agent/provider.py`；tests仅`tests/unit/test_config.py`、`tests/unit/agent/test_provider.py`。禁止Persistence、Lease、Docker、Recovery、Credential module及schema/migration修改。
- Blocker resolution：provider wire/SDK问题由transport injection消除；配置来源与课程硬限额已冻结；GEN-010明确为snapshot-only contract，无Task/Persistence scope expansion。无剩余human decision。
- Gate transition=`PLANNING BLOCKED → PLANNING COMPLETE → APPROVED FOR RED`；当前=`RED_NOT_STARTED`，本checkpoint仅同步人工decision，未创建production/tests。

### WP-21 Red checkpoint

- `2026-07-30 12:45:18 +0800`：Gate从`APPROVED FOR RED`进入Red；`RED_STARTED`，仅创建批准的`tests/unit/test_config.py`与`tests/unit/agent/test_provider.py`，未创建或修改production【CONTEMPORANEOUS / VERIFIED】。
- Config coverage共16 nodes：`HarnessConfig` contract、`startup trusted config > defaults`、repository/environment source exclusion、unknown/type/range拒绝、immutable `RunConfigSnapshot`、canonical determinism、digest binding，以及`GEN-008..010`三个参数化Requirement行为节点。
- Provider coverage共13 nodes：`ProviderRequest`、`ProviderResult`、`ProviderError` classification、runtime-checkable `ProviderTransport`、timeout→unavailable、unavailable/configuration separation、redirect rejection、single-transport/no fallback、request/response byte limits，以及`AGT-013..014`,`SEC-014..015`四个参数化Requirement行为节点。
- 测试只用记录型fake transport替代外部网络；被测配置、adapter与分类逻辑仍为未来production接口。测试不访问网络、不需要API Key、不实现HTTP/vendor/credential行为。
- Collect-only命令=`PYTHONDONTWRITEBYTECODE=1 <project-python-3.12> -m pytest -p no:cacheprovider --collect-only tests/unit/test_config.py tests/unit/agent/test_provider.py -q`，结果=`29 tests collected in 0.02s`、exit 0。
- Red命令=`PYTHONDONTWRITEBYTECODE=1 <project-python-3.12> -m pytest -p no:cacheprovider tests/unit/test_config.py tests/unit/agent/test_provider.py -q`，结果=`29 failed in 0.04s`、exit 1【CONTEMPORANEOUS / VERIFIED】。
- Failure classification=`29 EXPECTED_INTERFACE_MISSING`：16个config nodes精确因`coding_harness.config`不存在失败；13个provider nodes精确因`coding_harness.agent.provider`不存在失败。无collection、syntax、test-import、network或environment failure。
- Scope check：SPEC/PLAN、production、schema/migration、Persistence、Lease、Docker、Recovery与Credential均未修改；未进入implementation。
- Gate transition=`PLANNING COMPLETE → RED → RED COMPLETE`；下一阶段=`IMPLEMENTATION`，当前=`IMPLEMENTATION_NOT_STARTED / COMMIT_NOT_AUTHORIZED`。

### WP-21 Implementation checkpoint

- `2026-07-30 12:50:32 +0800`：Gate transition=`RED COMPLETE → IMPLEMENTATION`；`IMPLEMENTATION_STARTED`，仅创建批准的`src/coding_harness/config.py`与`src/coding_harness/agent/provider.py`【CONTEMPORANEOUS / VERIFIED】。
- Config design：frozen/slots `HarnessConfig`只从strict defaults与startup mappings构造，要求defaults精确闭合、startup为闭合集合子集，优先级固定`startup > defaults`。Module不读取environment、`.env`、repository、Issue或LLM。
- `RunConfigSnapshot`保持snapshot-only boundary：canonical JSON bytes与SHA-256 digest绑定provider/endpoint、profile/image、policy、budget hard limits、sandbox template、export rules及全部课程级limits；不引用或修改Task、ExecutionLease、Persistence。
- Frozen course limits在config construction、snapshot与ProviderRequest三层一致验证：timeout=`30s`、request=`1,048,576 bytes`、response=`2,097,152 bytes`、tokens=`4096`。
- Provider design：frozen `ProviderRequest`/`ProviderResult`；runtime-checkable `ProviderTransport.send`；闭合`ProviderResultStatus`/`ProviderErrorCode`；`ProviderAdapter`只调用注入的单一transport一次。Timeout/OSError确定性分类为`PROVIDER_UNAVAILABLE`，configuration result分类为`PROVIDER_CONFIGURATION_ERROR`，redirect为`REDIRECT_REJECTED`且不跟随，非合同result fail closed；无fallback。
- Boundary：无HTTP client、vendor/OpenAI SDK、endpoint discovery、credential/API Key、network、subprocess、SQLite/Persistence、Lease、Docker、Recovery或schema/migration依赖。
- Target命令=`PYTHONDONTWRITEBYTECODE=1 <project-python-3.12> -m pytest -p no:cacheprovider tests/unit/test_config.py tests/unit/agent/test_provider.py -q`，首次Green=`29 passed in 0.04s`【CONTEMPORANEOUS / VERIFIED】。
- Full regression=`945 passed / 1 failed in 29.26s`；唯一failure为六个批准WP-21预提交paths触发`test_worktree_baseline_is_clean`，属于流程cleanliness gate。排除该自指节点后行为集合=`945 passed / 1 deselected in 29.24s`【CONTEMPORANEOUS / VERIFIED】。
- Scope check：SPEC/PLAN、schema/migration、Persistence、Lease、Docker、Recovery与Credential均未修改；未commit/push。
- Gate=`IMPLEMENTATION COMPLETE / REVIEW PENDING`。

### WP-21 Review and review-fix checkpoint

- `2026-07-30 13:06:03 +0800`：`REVIEW_STARTED`；review verdict=`CHANGES_REQUIRED`。Findings覆盖closed error taxonomy、built-in defaults authority、窄Provider boundary、transport exception封装及redirect/malformed/boundary/digest/endpoint contract evidence。
- Gate transition=`IMPLEMENTATION → REVIEW → CHANGES_REQUIRED → REVIEW_FIX_STARTED`。整改严格限于批准的`config.py`、`agent/provider.py`、两份WP-21 unit tests及过程文档；不进入Persistence、Lease、Docker、Recovery、Credential、schema/migration或冻结SPEC/PLAN。
- Review-fix先补充7个adversarial/edge nodes，总数增至36。旧实现Red=`36 failed in 0.11s`：`HarnessConfig.from_startup`与`ProviderGateway`尚不存在；最终authority复核再增加direct-constructor bypass节点并观察旧实现`1 failed in 0.02s`。两轮均无collection、syntax或environment failure【CONTEMPORANEOUS / VERIFIED】。
- Config authority修复为module-owned immutable built-in defaults，public construction仅接受trusted startup mapping；caller无法传入defaults，environment/repository/Issue/LLM仍不在API。
- Provider boundary修复为窄`ProviderGateway.execute`与transport injection，不声称实现既有`LLMAdapter.complete(context)`。`ProviderErrorCode`精确闭合为`PROVIDER_UNAVAILABLE`、`PROVIDER_CONFIGURATION_ERROR`；redirect、malformed/tampered result及unexpected exception映射configuration error，timeout/OSError映射unavailable，raw transport exception不逃逸。
- Snapshot与ProviderResult digest直接按各自`canonical_bytes()`的SHA-256复验；请求/响应精确limit边界可接受，越界拒绝；SEC-015行为节点验证payload/keyword均不能覆盖trusted endpoint。
- Final Green=`37 passed in 0.07s`。Full regression=`953 passed / 1 failed in 29.60s`；唯一failure为六个批准预提交paths触发`test_worktree_baseline_is_clean`，分类为流程cleanliness gate而非行为回归【CONTEMPORANEOUS / VERIFIED】。
- Gate transition=`REVIEW_FIX_STARTED → REVIEW_FIX_COMPLETE`；下一阶段=`FINAL_REVIEW`，当前=`COMMIT_NOT_AUTHORIZED`。

### WP-21 Final Review Fix Phase 2 checkpoint

- `2026-07-30 13:20:50 +0800`：Final Review verdict=`CHANGES_REQUIRED`。Critical findings：`AGT-013`的`llm_requests`累计预算未由Provider执行边界消费；`RunConfigSnapshot`可被直接构造且gateway创建后仍可用`object.__setattr__`篡改endpoint。Important finding：`GEN-009`四类非可信输入与`AGT-013`累计行为PV证据不完整。
- Gate transition=`FINAL_REVIEW → CHANGES_REQUIRED → REVIEW_FIX_STARTED`。修复严格限于WP-21批准的两个production、两个tests及过程文档；不修改Task/Run state、Persistence、Lease、Docker、Recovery、Credential、schema/migration或SPEC/PLAN。
- TDD Red新增4个阻断nodes：direct snapshot construction、snapshot public authority mutation、第5次request budget越界、gateway后endpoint篡改。旧实现=`4 failed in 0.05s`，失败均为预期behavior missing，无collection/environment failure【CONTEMPORANEOUS / VERIFIED】。
- Snapshot最小修复：仅`HarnessConfig.snapshot()`持有内部factory token；外部direct construction拒绝；public provider/endpoint等authority由无setter property暴露，`object.__setattr__`不能覆盖实际public authority；canonical bytes与SHA-256 digest保持确定性绑定。
- Provider最小修复：gateway构造时复制已验证的provider/endpoint/timeout authority；从snapshot `budget_hard_limits`读取`llm_requests`，以进程内Lock原子消费累计请求额度。额度内请求成功，下一请求在transport前以闭合既有`PROVIDER_CONFIGURATION_ERROR` fail closed；无Task/Run/Persistence side effect或新error code。
- Requirement evidence补齐：`GEN-009`显式拒绝dotenv、Issue、tool output、LLM suggestion；`AGT-013`参数化节点验证4次成功、第5次拒绝且transport仅调用4次。
- Selected Green=`4 passed in 0.03s`；完整WP-21=`41 passed in 0.08s`。Full regression=`957 passed / 1 failed in 29.61s`，唯一failure为六个批准预提交paths触发`test_worktree_baseline_is_clean`，分类为流程cleanliness gate【CONTEMPORANEOUS / VERIFIED】。
- Gate transition=`REVIEW_FIX_STARTED → REVIEW_FIX_COMPLETE`；当前=`FINAL_REVIEW_PENDING / COMMIT_NOT_AUTHORIZED`。

### WP-21 Revised Final Review and documentation sync checkpoint

- `2026-07-30 13:31:48 +0800`：人工确认课程级threat model不要求防御同进程Python reflection/private API/object-model bypass【CONTEMPORANEOUS / APPROVED DECISION】。
- Revised Final Review verdict=`PASS`；Critical=`0`、Important=`0`、Minor=`1`。通过private `_SNAPSHOT_FACTORY_TOKEN`/`RunConfigSnapshot._from_config`构造对象，以及用`object.__setattr__`直接改写private slots的两项finding均重新分类为`OUT_OF_SCOPE`，不阻断本课程实现。
- 唯一Minor为`AGT-013`缺少真实并发behavior test。Production以同一`Lock`覆盖request-budget check-and-decrement，静态控制流与串行行为均证明超限在transport前fail closed；该测试缺口为non-blocking。
- Threat model boundary：WP-21保证正常公开API、可信factory contract、canonical digest、固定Provider/endpoint与累计request budget；不保证抵抗已经拥有同进程任意Python执行能力的代码通过reflection、private attribute或object-model bypass修改内部对象。
- Requirement verification=`PASS` for approved course scope：`GEN-008`,`GEN-009`,`GEN-010`,`AGT-013`,`AGT-014`,`SEC-014`,`SEC-015`。
- Test evidence：WP-21=`41 passed in 0.08s`；full regression=`957 passed / 1 failed in 30.92s`。唯一failure为六个批准预提交paths触发`test_worktree_baseline_is_clean`，分类为流程cleanliness gate，不是行为回归【CONTEMPORANEOUS / VERIFIED】。
- Gate transition=`FINAL_REVIEW_PASS → DOCUMENTATION_SYNC_COMPLETE`；下一阶段=`COMMIT_PREPARATION`。本checkpoint仅同步文档，未修改production/tests/SPEC/PLAN，未stage/commit/push。

### [RETROSPECTIVE] [VERIFIED] WP-21 Final Closeout checkpoint

- [RETROSPECTIVE] [VERIFIED] Implementation commit=`a0eccb326820812d8ed5255b63ae441a2ecbc6b4`；commit completion及六个批准文件由main history验证。
- [RETROSPECTIVE] [VERIFIED] PR merge commit=`91621af5a9523cce7b252fd0b3be0a2ac9d8086c`，message=`Merge pull request #12 from Shelia-YX/wp-21-trusted-config-provider`；parents=`72ecb75e774eaa9b3b6333a0952761dc93a83b74 a0eccb326820812d8ed5255b63ae441a2ecbc6b4`。
- [RETROSPECTIVE] [VERIFIED] Main synchronization=`PASS`：local main、`origin/main` tracking ref与remote actual main一致，ahead/behind=`0/0`；remote feature branch已删除，post-test working tree clean。
- [RETROSPECTIVE] [VERIFIED] Historical integrity=`WP-13 ~ WP-21 PASS`。
- [RETROSPECTIVE] [VERIFIED] Clean-main regression=`958 collected / 958 passed / 0 failed in 30.52s`；`test_worktree_baseline_is_clean`通过。
- [RETROSPECTIVE] [VERIFIED] Current main-workspace artifact check=`PASS`：排除其他linked worktrees后无`__pycache__`、`.pyc`、`.pytest_cache`、database或temporary artifact。
- 本closeout不修改此前Revised Final Review：Critical/Important/Minor=`0/0/1`，两项reflection finding维持`OUT_OF_SCOPE`，AGT-013并发test缺口维持Minor/non-blocking。
- Final process gate：

```text
WP21_FINAL_REVIEW_PASS
        ↓
WP21_MERGED_VERIFIED
        ↓
WP21_MAIN_VERIFICATION_VERIFIED
        ↓
WP21_CLOSED
```

## WP-22 Initialization checkpoint

- `2026-07-31 10:42:18 +0800`：WP-22课程级Credential/Provider Boundary ownership开始；创建linked worktree=`.worktrees/wp-22-credential-provider`及branch=`wp-22-credential-provider`【CONTEMPORANEOUS / VERIFIED】。
- Baseline=`609705da3e892b08330e589000ea3d2c0972db18`，与创建时clean main HEAD一致；`.worktrees/` ignore rule已验证，新worktree初始clean、staging empty，main工作区内容与HEAD未修改【CONTEMPORANEOUS / VERIFIED】。
- Historical integrity=`WP-13 ~ WP-21 PASS`；全部implementation commits均为WP-22 HEAD ancestor【CONTEMPORANEOUS / VERIFIED】。
- Baseline regression在本checkpoint文档修改前执行，命令禁用bytecode与pytest cache，结果=`958 collected / 958 passed / 0 failed in 24.37s`【CONTEMPORANEOUS / VERIFIED】。
- Scope保持课程级：当前不引入工业级Secret Management、Vault/KMS/HSM或扩展threat model；尚未开始credential contract/provider boundary的planning设计或implementation。
- 当前仅修改`AGENT_LOG.md`与`SPEC_PROCESS.md`以记录初始化；无production、tests、schema/migration、SPEC或PLAN修改，未stage/commit/push。
- Gate transition=`INIT → PLANNING`；当前状态=`INIT COMPLETE / READY FOR PLANNING`。

## WP-22 Planning checkpoint

- `2026-07-31 10:47:27 +0800`：`PLANNING_STARTED`；复核WP-13~WP-21现有authority、WP-21 `RunConfigSnapshot` / `ProviderGateway` / `ProviderTransport`接口，以及冻结`SPEC.md`与`PLAN.md`中的WP-22 requirements、PV、精确文件和Red cases【CONTEMPORANEOUS / VERIFIED】。
- 课程级候选设计：immutable且provider-bound的credential contract；由宿主startup trusted injection构造的窄`CredentialProvider`；exact provider matching；missing/mismatch deterministic fail-closed；`repr`、异常、日志和普通evidence只暴露非敏感状态，不暴露credential value。
- Threat model边界：不防御同进程Python reflection、memory dump、已失陷runtime、弱口令或物理介质恢复；不引入Vault、KMS/HSM、云Secret Manager、credential rotation platform、多用户IAM或WebUI secret management。
- Authority boundary：WP-22 MAY提供credential capability与非敏感状态；MUST NOT修改Task lifecycle、Agent state、Execution Lease、SQLite/Persistence、Docker execution、Apply/Recovery或WP-21 Provider protocol，也不得把credential注入Task Workspace、任务容器或LLM上下文。
- Requirement mapping发现：冻结WP-22 owned=`CRD-001..013`,`SEC-007..008`,`SEC-010..013`,`TST-007`。其中`CRD-001..006`,`CRD-008`,`CRD-010..013`与`TST-007`要求本地口令加密文件、KDF+AEAD、权限、TTY unlock、CLI lifecycle和原子更新；`SEC-007..008`,`SEC-011..012`要求Context Export治理。仅实现credential provider contract只能支持`CRD-007`,`CRD-009`,`SEC-010`,`SEC-013`及`AGT-014`的部分边界，不能宣称关闭完整owned PV。
- Frozen PLAN精确production范围=`agent/export.py`,`credentials/crypto.py`,`credentials/store.py`,`credentials/runtime.py`,`cli/credentials.py`，test=`tests/unit/credentials/test_credentials.py`。若保留冻结WP-22范围，应沿用这些文件；若批准scope reduction，建议最小范围为`credentials/models.py`,`credentials/provider.py`及`tests/unit/credentials/test_provider.py`，并由人工明确延期requirements和integration seam，不能由实现者自行替换PLAN authority。
- Integration blocker：现有WP-21 `ProviderGateway`仅接收`RunConfigSnapshot`与`ProviderTransport`，`ProviderRequest`没有credential capability；在“不修改Provider protocol”的约束下，WP-22无法证明credential被固定Provider可信消费。必须由人工选择窄集成方式或明确本WP只产出未接线contract。
- Failure strategy候选：missing、unknown provider、provider mismatch、malformed/oversized trusted injection均返回闭合、无secret的configuration failure；不fallback、不读取repository/Issue/LLM/tool output，不将credential写入Persistence、workspace、container或context。
- Planned tests候选：contract immutability与provider binding；trusted source allow/reject；missing/mismatch fail-closed；无fallback；`repr`/`str`/error/audit-like summary masking；bounded inputs；不测试reflection、memory dump或runtime compromise。正式Red节点和文件须等待scope裁决后冻结。
- 本checkpoint仅修改`AGENT_LOG.md`与`SPEC_PROCESS.md`；未创建production/tests/schema/migration，未修改SPEC/PLAN，未stage/commit/push。
- Gate：

```text
INIT COMPLETE
        ↓
PLANNING
        ↓
PLANNING BLOCKED / WAITING HUMAN DECISION
```

## WP-22 Scope Reduction Decision checkpoint

- `2026-07-31 10:52:04 +0800`：人工批准课程级scope reduction，planning中发现的requirement范围冲突与Provider integration seam blocker均已裁决【CONTEMPORANEOUS / APPROVED DECISION】。
- Final WP-22 responsibility：immutable Credential contract、窄`CredentialProvider` interface、trusted startup injection、exact Provider binding、missing/mismatch deterministic fail-closed、secret non-leak behavior。
- Trusted source限定为宿主startup composition显式注入；repository、Issue、LLM response、tool output、Task字段、workspace与container均不是credential authority。Missing或Provider mismatch不得调用transport、不得fallback，并映射到既有确定性configuration failure。
- Approved production=`src/coding_harness/credentials/models.py`,`src/coding_harness/credentials/provider.py`；approved test=`tests/unit/credentials/test_provider.py`。
- Integration exception：允许在既有WP-21 `ProviderGateway`增加最小credential seam，以消费WP-22 capability；不得修改`ProviderRequest`/`ProviderTransport` protocol、Provider error taxonomy、AgentLoop、Task lifecycle或其他authority。该例外仅用于固定Provider调用前的credential resolution与fail-closed门禁。
- Explicitly excluded：encrypted credential store、KDF/AEAD、TTY unlock、credential CLI lifecycle、Context Export subsystem、Vault/KMS/HSM、rotation、enterprise IAM、WebUI secret management。
- Deferred requirements：`CRD-001..013`中未被本scope覆盖的部分；`SEC-007..013`中依赖Context Export的部分；完整`TST-007`。本WP的contract/non-leak测试只能作为覆盖到的部分证据，不得被记录为上述完整PV已关闭。
- Authority boundary保持：WP-22不修改Task或Agent state、Persistence/SQLite、Execution Lease、Docker、Apply/Recovery；不保存长期credential history；不把secret放入payload、日志、错误、普通evidence、workspace、container或LLM context。
- Red阶段文件和行为范围已冻结，但本checkpoint尚未创建production/tests，也未进入Red执行；`SPEC.md`与`PLAN.md`保持不变。
- Gate：

```text
PLANNING BLOCKED
        ↓
PLANNING COMPLETE
        ↓
APPROVED FOR RED
```

## WP-22 Red checkpoint

- `2026-07-31 10:56:17 +0800`：`RED_STARTED`；仅创建批准的`tests/unit/credentials/test_provider.py`，production仍不存在【CONTEMPORANEOUS / VERIFIED】。
- Test scope共9个真实行为节点：Credential immutability；默认`str/repr` redaction；trusted startup source snapshot；`CredentialProvider` contract与exact lookup；missing与provider mismatch deterministic failure；no fallback；secret不进入error/provider surfaces；非bytes untrusted startup value拒绝且不回显。
- Collect-only=`9 tests collected in 0.01s`，collection成功【CONTEMPORANEOUS / VERIFIED】。
- Red=`9 failed in 0.02s`：2个model nodes为`EXPECTED_INTERFACE_MISSING: WP-22 credential model contract`，7个provider nodes为`EXPECTED_INTERFACE_MISSING: WP-22 credential provider contract`；失败原因精确为批准接口尚不存在，不是collection、syntax、test mistake、network或环境错误【CONTEMPORANEOUS / VERIFIED】。
- Runner evidence：工作区无`python`命令且system `python3`无pytest；这两次只用于定位项目runner，不计入Red。最终通过现有uv/pytest隔离环境执行有效collect-only和Red，不创建project virtualenv或依赖artifact。
- Scope保持：未创建`credentials/models.py`或`credentials/provider.py`，未修改`ProviderRequest`、`ProviderTransport`、Task、Persistence、Lease、Docker、Recovery、schema/migration、SPEC或PLAN；未进入Green。
- Gate：

```text
APPROVED FOR RED
        ↓
RED COMPLETE
        ↓
IMPLEMENTATION PENDING
```

## WP-22 Implementation checkpoint

- `2026-07-31 11:05:51 +0800`：Gate=`RED COMPLETE → IMPLEMENTATION`；`IMPLEMENTATION_STARTED`【CONTEMPORANEOUS / VERIFIED】。
- Created only approved production：`src/coding_harness/credentials/models.py`,`src/coding_harness/credentials/provider.py`。
- `Credential`为frozen/slots contract：bounded provider identity、immutable bytes secret、非敏感deterministic startup slot reference；默认`repr/str` redacted，显式`secret_bytes()`是唯一正常secret access。
- `StartupCredentialProvider`仅从strict startup mapping构造immutable tuple snapshot；实现runtime-checkable `CredentialProvider`与exact lookup。空source返回`MISSING_CREDENTIAL`；存在credential但无exact provider binding返回`CREDENTIAL_PROVIDER_MISMATCH`；不fallback，错误/repr不包含secret。
- Existing Red suite首次Green=`9 passed in 0.02s`【CONTEMPORANEOUS / VERIFIED】。
- Minimality：当前9个contract nodes不要求`ProviderGateway` seam，故未修改WP-21文件；未触及Provider protocol、Task、Persistence、Lease、Docker、Recovery、schema/migration、SPEC或PLAN。
- Full regression blocker：pytest默认prepend import mode把`tests/unit/agent/test_provider.py`与`tests/unit/credentials/test_provider.py`都作为顶层module `test_provider`，产生`import file mismatch` collection error。根因由重复basename、两目录均无package marker及完整error复现确认。
- Diagnostic full run使用`--import-mode=importlib`隔离module identity，结果=`966 passed / 1 failed in 25.02s`；唯一failure为5个批准dirty paths触发pre-commit cleanliness gate，说明未观察到行为回归，但不能替代默认full suite门禁。
- 最小持久修复需要新增`tests/unit/credentials/__init__.py`，或由人工批准重命名已冻结测试文件。两者均超出当前精确文件清单，故未执行。
- Current gate：

```text
RED COMPLETE
        ↓
IMPLEMENTATION
        ↓
IMPLEMENTATION BLOCKED / WAITING SCOPE AUTHORIZATION
```

## WP-22 Implementation Gate Completion checkpoint

- `2026-07-31 11:13:25 +0800`：人工授权新增`tests/unit/credentials/__init__.py`，仅用于赋予批准测试目录稳定package identity；不属于credential功能或测试行为scope扩展【CONTEMPORANEOUS / APPROVED DECISION】。
- 空package marker关闭pytest默认prepend import mode下`tests/unit/agent/test_provider.py`与`tests/unit/credentials/test_provider.py`的顶层module collision。未修改production、已有测试逻辑、pytest配置、WP-21 Provider protocol或其他authority。
- Default WP-22 Green=`9 passed in 0.02s`【CONTEMPORANEOUS / VERIFIED】。
- Default full pytest已成功collect并执行967 nodes：`966 passed / 1 failed in 24.88s`。唯一failure=`test_worktree_baseline_is_clean`，原因是当前六个批准WP-22 paths处于预提交dirty状态；该节点同时拒绝dirty与staged paths，在“不要commit”约束下无法为PASS，不属于behavior regression。
- 排除上述单一自指流程门禁后的完整行为回归=`966 passed / 1 deselected in 27.49s`【CONTEMPORANEOUS / VERIFIED】。
- Implementation与default-import collision均已完成；clean-worktree最终证据必须在commit后clean HEAD重跑。当前记录真实结果，不将pre-commit full pytest描述为全PASS。
- Scope仍严格限定为`credentials/models.py`,`credentials/provider.py`,`tests/unit/credentials/test_provider.py`,`tests/unit/credentials/__init__.py`及两份过程文档；无ProviderGateway seam、SPEC/PLAN、schema/migration或其他authority修改。
- Gate：

```text
IMPLEMENTATION BLOCKED
        ↓
TEST PACKAGE AUTHORIZED
        ↓
IMPLEMENTATION COMPLETE / REVIEW PENDING
```

## WP-22 Review and Review-Fix Scope checkpoint

- `2026-07-31 11:25:59 +0800`：`REVIEW_STARTED`；只读review verdict=`CHANGES_REQUIRED`，Critical/Important/Minor=`0/1/1`【CONTEMPORANEOUS / VERIFIED】。
- Important finding：`CredentialProvider`尚无production consumer；当前`ProviderGateway`未resolve credential即可调用transport，missing/mismatch没有映射到既有`PROVIDER_CONFIGURATION_ERROR`。
- Minor finding：tests未绑定`slot_reference`安全性，也没有Gateway success/missing/mismatch、transport zero-call与configuration mapping行为证据。
- Review evidence：WP-22=`9 passed in 0.02s`；default full=`966 passed / 1 failed in 27.78s`，唯一failure为六个批准dirty paths触发pre-commit cleanliness gate。
- 人工批准的fix语义要求credential seam成为调用transport前的必需门禁，且不得修改`ProviderRequest`/`ProviderTransport`。
- Scope verification发现既有WP-21 `tests/unit/agent/test_provider.py`有两个`ProviderGateway`构造点，均未注入credential。正确的required seam会使这些既有contract tests在构造阶段失败；optional/default credential seam则保留无credential执行路径，无法关闭finding。
- 因`tests/unit/agent/test_provider.py`未在当前批准文件清单，当前未开始review-fix Red、未修改production/tests，也未引入implicit credential。需要人工授权仅为这两个既有Gateway test构造点注入trusted test credential。
- Gate：

```text
IMPLEMENTATION COMPLETE
        ↓
REVIEW / CHANGES REQUIRED
        ↓
REVIEW FIX BLOCKED / WAITING TEST SCOPE AUTHORIZATION
```

## WP-22 Review Fix checkpoint

- `2026-07-31 11:43:48 +0800`：人工批准`tests/unit/agent/test_provider.py`作为窄测试兼容范围，仅给两个既有Gateway构造点注入trusted fake credential；不改变WP-21行为断言【CONTEMPORANEOUS / APPROVED DECISION】。
- `REVIEW_FIX_STARTED`；新增4个behavior nodes，覆盖slot reference non-leak、credential success→transport called、missing→configuration error/zero-call、mismatch→configuration error/zero-call/error non-leak。
- Old implementation Red=`3 failed / 10 passed in 0.04s`；3个失败均为`ProviderGateway.__init__() got an unexpected keyword argument 'credential_provider'`，准确证明mandatory seam缺失【CONTEMPORANEOUS / VERIFIED】。
- Minimal production fix仅修改`src/coding_harness/agent/provider.py`：`CredentialProvider`成为required dependency；execute在request、budget和transport之前resolve固定provider；返回值必须是绑定同一provider identity的`Credential`。
- Missing、mismatch、unexpected resolver failure与invalid binding统一映射到既有`ProviderErrorCode.CONFIGURATION_ERROR`，reason为无secret固定文本，transport调用次数保持0。`ProviderRequest`与`ProviderTransport` protocol不变。
- Green evidence：WP-22=`13 passed in 0.03s`；WP-21 provider=`20 passed in 0.07s`；combined=`33 passed in 0.08s`【CONTEMPORANEOUS / VERIFIED】。
- Default full regression=`970 passed / 1 failed in 27.92s`，唯一failure为8个批准dirty paths触发`test_worktree_baseline_is_clean`；排除该自指流程门禁后的行为集合=`970 passed / 1 deselected in 27.71s`，无行为回归。
- Scope verification：无encrypted store、CLI、rotation、Context Export、Vault/KMS/HSM、schema/migration、Task、Persistence、Lease、Docker、Recovery、SPEC或PLAN修改；未stage/commit/push。
- Gate：

```text
REVIEW FIX BLOCKED
        ↓
REVIEW FIX SCOPE APPROVED
        ↓
REVIEW FIX COMPLETE / FINAL REVIEW PENDING
```

## WP-22 Final Review and Documentation Sync checkpoint

- `2026-07-31 11:49:30 +0800`：严格只读Final Review完成；verdict=`FINAL_REVIEW_PASS`，Critical/Important/Minor=`0/0/0`【CONTEMPORANEOUS / VERIFIED】。
- Provider integration=`PASS`：`credential_provider`为Gateway required dependency；execute在request、budget和transport之前resolve固定provider；missing、mismatch、resolver exception与invalid binding均产生既有`PROVIDER_CONFIGURATION_ERROR`且transport zero-call。
- Secret boundary=`PASS`：Credential `repr/str`、slot reference、lookup exception、Gateway ProviderError、provider repr与`ProviderRequest`均不暴露credential secret；Gateway不传播CredentialError reason。
- WP-21 compatibility=`PASS`：`ProviderRequest`与`ProviderTransport` protocol未修改；WP-21 tests只在两个既有Gateway构造点注入trusted fake credential，原行为断言保持。
- Fresh test evidence：WP-22=`13 passed in 0.03s`；WP-21 Provider=`20 passed in 0.07s`；default full=`970 passed / 1 failed in 28.13s`。唯一failure=`test_worktree_baseline_is_clean`，精确由8个批准pre-commit dirty paths触发，分类为process cleanliness gate，不是behavior regression。
- Scope confirmation：未实现encrypted credential store、credential CLI lifecycle、rotation、Context Export、Vault/KMS/HSM；未修改Task lifecycle、Persistence、Lease、Docker、Recovery或schema/migration。
- 本documentation sync仅修改`AGENT_LOG.md`与`SPEC_PROCESS.md`；production/tests内容保持Final Review时状态，`SPEC.md`/`PLAN.md`不变，未stage/commit/push。
- Gate：

```text
REVIEW_FIX_COMPLETE
        ↓
FINAL_REVIEW_PASS
        ↓
DOCUMENTATION_SYNC_COMPLETE
```

## [RETROSPECTIVE] WP-22 Final Closeout checkpoint

- `[RETROSPECTIVE] [VERIFIED]` Implementation commit=`b70b555acec9a6e6acedf262519853445261dc1e`，其提交范围为已批准的credential contract、`ProviderGateway` seam、对应tests与当期过程文档。
- `[RETROSPECTIVE] [VERIFIED]` PR merge commit=`7ba9be369632428696a0fc224dc2246337fd344a`，message=`Merge pull request #13 from Shelia-YX/wp-22-credential-provider`；merge parents=`609705da3e892b08330e589000ea3d2c0972db18`与`b70b555acec9a6e6acedf262519853445261dc1e`。
- `[RETROSPECTIVE] [VERIFIED]` Local main、`origin/main`与remote actual main一致，均为`7ba9be369632428696a0fc224dc2246337fd344a`；ahead/behind=`0/0`，working tree与staging均clean。
- `[RETROSPECTIVE] [VERIFIED]` Historical integrity=`WP-13 ~ WP-22 PASS`；WP-22 implementation commit为当前main ancestor，全部批准文件已进入main。
- `[RETROSPECTIVE] [VERIFIED]` Clean-main regression=`971 collected / 971 passed / 0 failed in 27.66s`；`test_worktree_baseline_is_clean`已恢复通过。
- `[RETROSPECTIVE] [VERIFIED]` Artifact verification=`PASS`：扫描当前main并排除`.worktrees/`后，无`__pycache__`、`.pyc`、`.pytest_cache`、database或temporary/editor artifact。
- Final process gate：

```text
WP22_FINAL_REVIEW_PASS
        ↓
WP22_MERGED_VERIFIED
        ↓
WP22_MAIN_VERIFICATION_VERIFIED
        ↓
WP22_CLOSED
```

## Project Finalization Scope Decision and Red checkpoint

- `2026-07-31 13:18:29 +0800`：人工批准采用`Evidence-first Course Closeout`，本阶段定位为课程提交证据收敛，不是产品化开发【CONTEMPORANEOUS / APPROVED DECISION】。
- Worktree=`.worktrees/project-finalization-course-submission`，branch=`project-finalization-course-submission`，baseline=`65bdf9fac2a9bc92abb772e2df425f6a4732778c`；初始化完整回归=`971 passed in 26.49s`【CONTEMPORANEOUS / VERIFIED】。
- Finalization owned scope：
  - `README.md`：准确描述现有能力、运行/测试/演示命令、环境、威胁边界、恢复、清理与延期项。
  - `examples/governance_demo.py`、`examples/feedback_demo.py`、`examples/recovery_demo.py`：只组合现有public contracts展示治理拒绝、失败反馈改变下一动作、事务失败后无partial effect并进入recovery；由tests验证。
  - `.gitlab-ci.yml`：包含名称严格为`unit-test`的job；允许dependency installation，但测试执行必须offline、不得需要API key、Docker daemon或其他external service。
  - `REFLECTION.md`：追加项目最终反思并保留早期历史。
  - Finalization contract tests与最终verification checklist。
- Scope adjustment：不新增product entrypoint；packaging/install smoke降为optional；任何production gap必须停止并申请scope decision，不得为演示越权修改`src/coding_harness/**`。
- Deferred/deviation items：
  - WP-23 API、WP-24 SSE、WP-25 WebUI。
  - WP-27 Node跨profile runtime evidence。
  - WP-26中API/static/serve CLI部分，以及WP-29中依赖WebUI/serve的distribution/cold-start部分。
  - 完整encrypted credential store、credential CLI lifecycle、Context Export。
  - 真实Docker security integration evidence与工业级安全强化。
- `SPEC.md`与`PLAN.md`继续冻结；上述延期项保持原Requirement ID与语义，不得报告为`IMPLEMENTED`或`VERIFIED`。课程Finalization完成状态只表示人工批准后的提交范围闭合，不表示冻结完整MVP全部实现。
- Red contract限定为过程文档与`tests/finalization/`；缺失的README、CI、final reflection与三个examples必须产生可归因的artifact/behavior failures，禁止collection/import/environment failure。
- Gate：

```text
FINALIZATION_PLANNING_COMPLETE
        ↓
SCOPE_ADJUSTMENT_APPROVED
        ↓
APPROVED_FOR_RED
        ↓
RED_STARTED
```

### Finalization Red evidence

- `2026-07-31 13:19:46 +0800`：仅新增`tests/finalization/test_submission.py`，未创建任何提交物实现或修改production。
- Collect-only=`7 tests collected in 0.01s`；无syntax、import或collection error【CONTEMPORANEOUS / VERIFIED】。
- Target Red=`6 failed / 1 passed in 0.02s`【CONTEMPORANEOUS / VERIFIED】：
  - README：`EXPECTED_DOCUMENTATION_MISSING: README.md`。
  - CI：`EXPECTED_ARTIFACT_MISSING: .gitlab-ci.yml`。
  - Reflection：`EXPECTED_DOCUMENTATION_MISSING: final reflection`。
  - Governance、feedback、recovery三个examples：各自为`EXPECTED_ARTIFACT_MISSING`。
  - Scope-deviation record节点PASS，证明人工批准的Finalization boundary与deferred items已落盘。
- Failure classification=`EXPECTED_DOCUMENTATION_MISSING / EXPECTED_ARTIFACT_MISSING`；无environment或无关failure。
- Gate：

```text
RED_STARTED
        ↓
RED_COMPLETE
        ↓
IMPLEMENTATION_PENDING
```

### Finalization Implementation checkpoint

- `2026-07-31 13:30:14 +0800`：Gate=`RED_COMPLETE → IMPLEMENTATION_STARTED`；实现严格限于批准的课程提交artifact、finalization contracts与过程文档【CONTEMPORANEOUS】。
- Artifacts：
  - `README.md`说明实际能力、architecture authority、Python 3.12运行方式、tests/demos、CI、recovery、课程级threat boundary、deferred scope、cleanup与final verification checklist。
  - `.gitlab-ci.yml`提供单一`unit-test` job；dependency installation允许联网，但测试执行不使用API key、Docker daemon或external service。
  - `governance_demo.py`直接使用`PolicyEngine`，确定性证明policy DENY与executor zero-call。
  - `feedback_demo.py`直接使用`MockLLM`、`ContextBuilder`与`ToolResult`，证明失败反馈进入下一轮context并改变action。
  - `recovery_demo.py`直接使用`ApplyCoordinator`与真实baseline/workspace/changeset contracts；文件系统拒绝首个目标操作后，无partial effect并进入`RECOVERY_REQUIRED`。现有public API没有演示专用fault-injection seam，因此不伪造`ROLLED_BACK`，更深rollback/startup-recovery故障注入继续由既有transaction integration suite验证。
  - `REFLECTION.md`追加最终课程反思，不改写早期记录。
- Green evidence：`pytest tests/finalization/test_submission.py -q = 7 passed in 0.12s`；`pytest tests/demos -q = 3 passed in 0.12s`【CONTEMPORANEOUS / VERIFIED】。
- Full regression=`980 passed / 1 failed in 25.03s`；唯一failure=`test_worktree_baseline_is_clean`，由10个批准pre-commit dirty paths触发，分类为process cleanliness gate而非behavior regression。排除该自指节点后，完整行为集合分拆验证为`874 passed`与`106 passed / 1 deselected`【CONTEMPORANEOUS / VERIFIED】。
- Scope verification：未修改`src/coding_harness/**`、既有tests、`SPEC.md`或`PLAN.md`；未实现API、WebUI、SSE、Node profile或product entrypoint；未stage/commit/push。
- Gate：

```text
RED_COMPLETE
        ↓
IMPLEMENTATION_STARTED
        ↓
IMPLEMENTATION_COMPLETE
        ↓
REVIEW_PENDING
```

### Finalization Review Fix checkpoint

- `2026-07-31 13:43:40 +0800`：Final Review verdict=`CHANGES_REQUIRED`，Critical/Important/Minor=`0/1/1`【CONTEMPORANEOUS / VERIFIED】。
- Important finding：`recovery_demo.py`依赖`chmod(0555)`阻止目标操作；root/特权执行身份可以绕过该权限，因此不满足跨执行身份deterministic要求。Minor finding：存在三个`__pycache__`目录及对应`.pyc`。
- Review Fix Red：在demo test中令任何`Path.chmod`调用直接失败；旧实现结果=`1 failed`，精确证明permission依赖，无collection/environment failure【CONTEMPORANEOUS / VERIFIED】。
- Minimal fix：删除chmod与filesystem-permission fault；通过公开`ApplyJournal.record` contract临时注入PREPARING journal persistence failure，并由真实`ApplyCoordinator`返回`RECOVERY_REQUIRED`。注入使用标准context patch自动恢复；未调用transaction私有函数、未复制Apply/rollback/recovery逻辑、未增加production seam。
- Green evidence：
  - exact recovery node=`1 passed in 0.13s`；
  - direct demo=`{"partial_effect":false,"result":"RECOVERY_REQUIRED","scenario":"recovery_rollback"}`；
  - finalization=`7 passed in 0.12s`；
  - demos=`3 passed in 0.11s`；
  - full pytest=`980 passed / 1 failed in 26.80s`，唯一failure为10个批准dirty paths触发pre-commit cleanliness gate；
  - 排除该自指门禁=`980 passed / 1 deselected in 26.68s`。
- Artifact fix：删除`examples/__pycache__`、`tests/demos/__pycache__`、`tests/finalization/__pycache__`及其`.pyc`。
- Boundary：未修改`src/coding_harness/**`、既有tests、`SPEC.md`或`PLAN.md`；未新增功能、product entrypoint或production contract；未stage/commit/push。
- Gate：

```text
REVIEW
        ↓
CHANGES_REQUIRED
        ↓
REVIEW_FIX_STARTED
        ↓
REVIEW_FIX_COMPLETE
        ↓
FINAL_REVIEW_RETRY_PENDING
```

### Project Finalization Final Review PASS checkpoint

- `2026-07-31 13:51:57 +0800`：严格只读Final Review Retry verdict=`FINAL REVIEW PASS`，Critical/Important/Minor=`0/0/0`【CONTEMPORANEOUS / VERIFIED】。
- Recovery finding closure：
  - 不再依赖`chmod`、filesystem permission或root/non-root行为；
  - 通过公开`ApplyJournal.record` contract注入PREPARING journal persistence failure；
  - 真实`ApplyCoordinator`返回`RECOVERY_REQUIRED`，repository验证为`partial_effect=false`；
  - 未复制production rollback/recovery logic，未新增production seam。
- Finalization artifact verification：
  - `README.md`
  - `.gitlab-ci.yml`
  - `REFLECTION.md`
  - `examples/governance_demo.py`
  - `examples/feedback_demo.py`
  - `examples/recovery_demo.py`
  - `tests/demos/test_examples.py`
  - `tests/finalization/test_submission.py`
- Fresh test evidence：
  - Finalization=`7 passed in 0.12s`；
  - Demos=`3 passed in 0.11s`；
  - Full regression=`980 passed / 1 failed in 26.76s`。
- Full regression唯一failure=`test_worktree_baseline_is_clean`，由10个批准pre-commit dirty paths触发，分类为process cleanliness gate而非behavior regression；提交后的clean HEAD必须重新运行并关闭该门禁。
- Scope/deviation confirmation：
  - `SPEC.md`与`PLAN.md`保持冻结；
  - 原PLAN延期的API、SSE、WebUI、Node runtime profile等能力没有被宣称已实现；
  - Finalization仅完成课程提交范围的evidence、demo、CI、README与reflection；
  - 未修改任何production contract。
- Documentation sync validation：仅`AGENT_LOG.md`与`SPEC_PROCESS.md`发生本阶段修改；八个Finalization artifact在同步前后SHA-256一致；staging empty；artifact scan clean。
- Gate：

```text
FINALIZATION_REVIEW_FIX_COMPLETE
        ↓
FINALIZATION_FINAL_REVIEW_PASS
        ↓
FINALIZATION_DOCUMENTATION_SYNC_COMPLETE
```

## GitHub Actions Finalization checkpoint

- `2026-07-31 14:08:19 +0800`：人工确认远程托管平台为GitHub，并批准在Finalization feature branch增加最小真实GitHub Actions workflow【CONTEMPORANEOUS / APPROVED DECISION】。
- `.gitlab-ci.yml`继续保留为课程要求artifact；本扩展不删除、不替换或修改GitLab配置。
- Dependency investigation：
  - source of truth=`pyproject.toml`；
  - project dependencies=`[]`；
  - 无`.[test]`、`.[dev]`、requirements、lock file或显式build backend；
  - clean Python 3.12实测可安装project与pytest。
- 初始Red：exact GitHub Actions contract node=`1 failed in 0.01s`，唯一failure=`EXPECTED_GITHUB_ACTIONS_MISSING`，无production/collection/environment failure【CONTEMPORANEOUS / VERIFIED】。
- Workflow=`.github/workflows/unit-test.yml`：
  - triggers=`main`与feature branch push、针对`main`的pull request、`workflow_dispatch`；
  - job=`unit-test`，runner=`ubuntu-latest`，Python=`3.12`，permissions=`contents: read`；
  - 无API key、Docker daemon、services、cache、artifact upload、coverage或外部测试服务；
  - `PYTHONDONTWRITEBYTECODE=1`且pytest使用`-p no:cacheprovider`。
- Install investigation发现editable及普通in-tree pip install会分别生成`src/coding_harness.egg-info/`和`build/`，使既有cleanliness gate失败；上述调查artifact已精确删除。最终workflow用`git archive HEAD`导出同一提交到`$RUNNER_TEMP`，从临时副本普通安装project，再安装pytest，不污染checkout且不修改packaging metadata。
- 安装策略review-fix Red=`1 failed in 0.01s`；workflow修正后exact Green=`1 passed in 0.01s`【CONTEMPORANEOUS / VERIFIED】。
- Local evidence：
  - Finalization=`8 passed in 0.13s`；
  - Demos=`3 passed in 0.12s`；
  - Full regression=`981 passed / 1 failed in 27.39s`；
  - 唯一failure=`test_worktree_baseline_is_clean`，由三个批准pre-commit dirty paths触发，不是behavior regression。
- README仅说明workflow位置、triggers、Python 3.12、完整pytest与无外部authority；明确远程GitHub Actions run尚待push后验证。
- Boundary：新增scope仅为远程CI artifact、Finalization contract与必要README/process同步；未修改production behavior、既有tests、`SPEC.md`、`PLAN.md`或`.gitlab-ci.yml`；未commit/push/PR/merge。
- Gate：

```text
GITHUB_ACTIONS_RED_COMPLETE
        ↓
GITHUB_ACTIONS_IMPLEMENTATION_COMPLETE
        ↓
GITHUB_ACTIONS_REVIEW_PENDING
```

### GitHub Actions Review Fix checkpoint

- `2026-08-01 15:43:56 +0800`：GitHub Actions只读review verdict=`CHANGES_REQUIRED`，Critical/Important/Minor=`0/2/1`【CONTEMPORANEOUS / VERIFIED】。
- Important findings：安装step以固定目录配合`mkdir -p`，不能证明目录全新且archive pipeline没有显式pipefail；Finalization contract仅做substring matching，不能证明GitHub Actions YAML的trigger/job/permissions/steps真实结构。
- `GITHUB_ACTIONS_REVIEW_FIX_STARTED`：TDD先将contract改为用PyYAML `BaseLoader`解析mapping/list结构，显式验证字符串键`on`及其trigger层级，避免普通YAML 1.1 loader把`on`解释为布尔值。旧workflow精确Red=`1 failed in 0.05s`，失败原因与上述安装finding一致，无collection/environment failure【CONTEMPORANEOUS / VERIFIED】。
- 最小fix：安装step首行使用`set -euo pipefail`；通过`mktemp -d "$RUNNER_TEMP/coding-harness-source.XXXXXX"`创建fresh目录；`git archive --format=tar HEAD | tar -xf - -C "$source_dir"`在同一受pipefail保护的shell中执行；project从临时副本安装，checkout不生成packaging artifact。为结构化contract显式安装`pytest PyYAML`。
- Network boundary：dependency provisioning通常需要访问Python package index；安装完成后的pytest逻辑不访问外部服务，不需要API key、Docker daemon、远程模型或业务API。README已与此边界同步；远程GitHub Actions run仍待push后验证。
- Green evidence：exact contract=`1 passed in 0.04s`；真实archive/temp pip install及package import smoke=`PASS`，checkout无`build/`、`dist/`或`*.egg-info`；Finalization=`8 passed in 0.20s`；Demos=`3 passed in 0.14s`；full=`981 passed / 1 failed in 28.52s`。唯一failure=`test_worktree_baseline_is_clean`，精确由五个批准pre-commit dirty paths触发，不是behavior regression【CONTEMPORANEOUS / VERIFIED】。
- Boundary：`actions/setup-python@v5`按人工决定不升级；未修改production、`SPEC.md`、`PLAN.md`、`.gitlab-ci.yml`、既有tests、`REFLECTION.md`或`examples/**`；未stage/commit/push/PR。
- Gate：

```text
GITHUB_ACTIONS_REVIEW
        ↓
CHANGES_REQUIRED
        ↓
GITHUB_ACTIONS_REVIEW_FIX_STARTED
        ↓
GITHUB_ACTIONS_REVIEW_FIX_COMPLETE
        ↓
GITHUB_ACTIONS_FINAL_REVIEW_PENDING
```

### GitHub Actions Final Review and Documentation Sync checkpoint

- `2026-08-01 15:51:42 +0800`：严格只读Final Review Retry verdict=`GITHUB ACTIONS REVIEW PASS`，Critical/Important/Minor=`0/0/0`【CONTEMPORANEOUS / VERIFIED】。
- Findings closure：archive安装使用`mktemp` fresh directory与`set -euo pipefail`，pipeline failure propagation独立验证为PASS；workflow contract使用PyYAML `BaseLoader`结构化验证真实mapping/list，字符串键`on`及push/PR/manual trigger层级正确，不再依赖全文substring matching。
- Workflow boundary：仅实现最小GitHub Actions CI/finalization infrastructure；依赖provisioning可访问Python package index，测试逻辑不访问外部服务且不需要API key或Docker daemon；remote GitHub Actions run仍待push后验证，不声明在线CI通过。
- Fresh local evidence：Finalization=`8 passed`；Demos=`3 passed`；full regression=`981 passed / 1 failed`。唯一failure=`test_worktree_baseline_is_clean`，由五个批准pre-commit dirty paths触发，分类为process cleanliness gate而非behavior regression【VERIFIED】。
- Scope：无production behavior变化；`SPEC.md`、`PLAN.md`、`.gitlab-ci.yml`、既有tests、`REFLECTION.md`与`examples/**`未修改。本documentation sync仅修改`AGENT_LOG.md`与`SPEC_PROCESS.md`，未stage/commit/push/PR。
- Gate：

```text
GITHUB_ACTIONS_REVIEW_PASS
        ↓
GITHUB_ACTIONS_DOCUMENTATION_SYNC_COMPLETE
        ↓
GITHUB_ACTIONS_COMMIT_PENDING
```

### GitHub Actions Remote Verification checkpoint

- `2026-08-01 16:19:43 +0800`：人工报告`.github/workflows/unit-test.yml`在commit `90d76b5c1e72b7fe4f50c85b38809fb7ca4170c0`的远程GitHub Actions run状态为`Success`，remote verification=`PASS`【USER_REPORTED】。
- 原失败根因：`actions/checkout@v6`默认shallow clone，导致ancestry verification所需commit `d3169f6e8ed0ff32afccfdde9504c8f42e710a97`不存在于checkout history。
- 修复：checkout step增加`with.fetch-depth: 0`；Finalization contract同时要求该结构。修复没有删除、绕过或弱化ancestor verification，也没有修改历史commit identity。
- Remote evidence：人工确认shallow-checkout问题已关闭且workflow成功；本地`git ls-remote`独立确认feature remote HEAD=`90d76b5c1e72b7fe4f50c85b38809fb7ca4170c0`【USER_REPORTED / VERIFIED AS MARKED】。
- Boundary：`SPEC.md`、`PLAN.md`、production、tests、workflow与README在本sync中均未修改；仅同步`AGENT_LOG.md`和`SPEC_PROCESS.md`，未stage/commit/push/PR。
- Gate：

```text
GITHUB_ACTIONS_REMOTE_VERIFICATION_PASS
        ↓
GITHUB_ACTIONS_REMOTE_DOCUMENTATION_SYNC_COMPLETE
        ↓
CLOSEOUT_COMMIT_PENDING
```
