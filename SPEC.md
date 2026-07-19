# AI4SE Final Project A：Coding Agent Harness 规格说明

版本：1.0（冻结 MVP 基线）  
状态：Approved Design / Planned Implementation  
主要贡献：受治理的事务化执行

## 1. 文档目的、规范约定与变更控制

### 1.1 文档目的

本文是 Coding Agent Harness 的产品行为、安全边界、验收标准和课程合规要求的权威规格。`PLAN.md` 只能安排实现顺序，不得改变本文语义；实现、测试或其他文档与本文冲突时，必须停止相关工作并发起设计变更。

### 1.2 规范关键词

本文中的 MUST、MUST NOT、SHOULD、SHOULD NOT、MAY 为规范关键词。只有带稳定需求 ID 的句子属于可追踪规范要求；其他文字用于解释范围和理由。规范主体、触发条件和可观察结果必须明确。

- **GEN-001** Harness MUST 以本文作为 MVP 行为与验收的权威规格。
- **GEN-002** `PLAN.md`、实现和测试 MUST NOT 反向改变本文需求语义。
- **GEN-003** 每项 MVP 完成声明 MUST 关联附录 H 中的可观察证据。
- **PRC-001** 冻结需求的语义变更 MUST 形成设计变更记录并重新获得用户批准。
- **PRC-002** 范围扩大 MUST 说明对 45 天计划、测试矩阵和主要贡献的影响。
- **PRC-003** Stretch goal MUST NOT 成为 MVP 完成条件。
- **PRC-004** 已废弃的需求 ID MUST NOT 被复用。

### 1.3 变更控制

设计变更记录必须给出原需求、拟议修改、原因、风险、迁移影响、测试影响和审批结果。发现真正冲突时，规格写作、计划或实现必须停在冲突边界，不得通过隐含假设解决。

## 2. 项目概述、目标与主要贡献

### 2.1 产品定位

本项目是面向本地单一代码仓库、单用户和 dependency-ready 项目的受控型通用 Coding Agent MVP。用户提交 Issue 级自然语言任务；Agent 先只读调查并提出任务理解、计划、范围、验收契约、验证方案和风险，获得批准后才执行修改。

### 2.2 主要贡献

本项目提出“受治理的事务化执行”：确定性策略、审批、预算和验收契约构成副作用授权边界；隔离 Task Workspace、Baseline Manifest、Agent Change Set、文件级冲突检测及 Apply Transaction 构成事务主体；回滚与恢复是该事务模型的安全性质。

产品表述为：让 Coding Agent 的每次代码修改都成为可治理、可审计、可验证和可恢复的工作区事务。

- **GEN-004** Harness MUST 支持 Bug 修复、小功能、测试补充、小范围重构和构建问题，但任务 MUST 满足本文能力边界。
- **GEN-005** Harness MUST 保持核心治理与事务机制语言无关，并仅对附录 G 中的 Python 与 Node.js/TypeScript profile 提供 MVP 自动化验证。
- **GEN-006** Harness MUST NOT 宣称数据库级跨介质原子性、任意恶意代码防护、完整 Git 语义或任意语言生态兼容。

### 2.3 MVP 成功标准

MVP 成功要求：自研 Agent loop 可在 Mock LLM 下离线运行；六个 Harness 维度均有最低实现；危险动作被确定性阻止；工具失败反馈使下一动作改变；多文件写回故障能够按事务证据恢复；WebUI、正式分发、CI 和课程文档均满足第 17 章。

### 2.4 User Stories 与 INVEST 检查

| ID | User Story | 独立价值与验收边界 | INVEST 简查 |
|---|---|---|---|
| US-01 | 作为用户，我提交 Issue 后获得只读调查、计划、范围、验收契约与验证方案，以便在任何修改前评估风险。 | 以 `AWAITING_PLAN_APPROVAL` 和不可变版本为验收边界。 | 独立、可协商、有价值、可估算、小规模、可测试。 |
| US-02 | 作为用户，我批准计划后让 Agent 在隔离 Workspace 中修改并用固定 profile 验证，以保护原仓库。 | 以原仓库未变化、工具结果和验证证据为边界。 | 独立、可协商、有价值、可估算、小规模、可测试。 |
| US-03 | 作为用户，我单独审批删除已有文件或纳入 ignored input，以便精确控制高风险读取与破坏性修改。 | 以 action payload 绑定、一次消费和失效测试为边界。 | 独立、可协商、有价值、可估算、小规模、可测试。 |
| US-04 | 作为用户，我查看 Acceptance Contract、Change Set 与 diff 后确认应用，以便只提交已验证的预期变更。 | 以 `READY_TO_APPLY`、digest 绑定和成功写回复检为边界。 | 独立、可协商、有价值、可估算、小规模、可测试。 |
| US-05 | 作为用户，我在写回故障后查看回滚与恢复证据，以确认已有工作是否得到保护。 | 以事务阶段、恢复 digest 和明确终态为边界。 | 独立、可协商、有价值、可估算、小规模、可测试。 |
| US-06 | 作为用户，我在 Provider locked、Docker unavailable 或 missing dependency 时获得确定性阻塞原因与下一命令。 | 以附录 B reason 表和附录 E 错误语义为边界。 | 独立、可协商、有价值、可估算、小规模、可测试。 |

### 2.5 六个 Harness 维度

| 维度 | MVP 组件与机制 | 主要验收证据 |
|---|---|---|
| Decision | 自研 Agent loop、Context Builder、LLM Adapter、确定性停止器 | Mock LLM action 序列与停止测试 |
| Tools | 结构化文件工具、profile 验证、受限 Synthetic Git、Docker Executor | schema、路径边界与 Docker 集成测试 |
| Memory | Task/Run、版本化计划与契约、SQLite Store、审计、任务私有证据文件 | SQLite 原子性、重启与事件补发测试 |
| Governance | Policy Engine、四类授权、预算、Acceptance Contract、fail-closed | 危险动作阻止、审批绑定和旧版本冲突测试 |
| Feedback | Tool Result、验证证据、错误分类、下一轮上下文 | 注入失败后下一动作改变演示 |
| Configuration | 可信配置 schema、固定 Provider/profile/image/endpoint、安全上限与每次 Run 冻结快照 | 配置拒绝、优先级、冻结与不可覆盖测试 |

User Stories 是用户价值索引，不替代规范需求；附录 H 将其映射到相关需求范围与验收场景。

## 3. 角色、信任边界与威胁模型

### 3.1 主体与信任分类

可信主体包括用户明确安装和运行的宿主 Harness 控制平面及其内部配置。Docker daemon 是高权限外部依赖。WebUI 输入、Issue、LLM 输出、目标仓库、仓库配置、测试、构建脚本、工具输出和任务容器均不得被视为可信控制输入。远程 LLM Provider 是被明确配置的数据接收方，不是治理主体。

### 3.2 受保护资产

受保护资产包括原仓库内容、用户 staged/unstaged/untracked 工作、原 Git index、宿主 HOME 与凭据、Docker 控制能力、Baseline 内容、事务备份、审计证据和 API Key。

- **SEC-001** Harness MUST 将仓库内容、仓库脚本、LLM 输出和普通 WebUI 输入作为不可信数据处理。
- **SEC-002** 任务容器 MUST NOT 访问 Docker socket、Docker daemon API、containerd socket或其他宿主容器控制接口。
- **SEC-003** 任务容器 MUST NOT 挂载宿主 HOME、凭据、原始 `.git`、原仓库、包缓存或私有 registry 配置。
- **SEC-004** 任务容器 MUST 使用 `network none`，且 MVP MUST NOT 存在按任务开启网络的执行分支。
- **SEC-005** 目标仓库代码和任务输入 MUST NOT 改变 LLM Provider endpoint、Docker endpoint、sandbox image 或安全模板。
- **SEC-006** Harness MUST 对路径、argv、输出、资源和外传上下文实施确定性上限；解析失败 MUST fail-closed。
- **SEC-007** 只有用户明确启用的远程 LLM Adapter MAY 将经 Context Builder 选择和过滤的上下文发送给固定 Provider。
- **SEC-008** 获批 ignored input、凭据和确定性敏感路径 MUST NOT 默认获得 `exportable_to_llm` 权限。
- **SEC-009** Harness MUST NOT 将容器隔离描述为能够抵抗容器逃逸、内核漏洞、零日或已失陷宿主。
- **SEC-010** Harness MUST NOT 将凭据加密描述为能够抵抗同用户进程内存读取、弱主口令或物理介质恢复。

### 3.3 威胁与故障范围

MVP 必须处理路径逃逸、参数注入、prompt injection 导致的权限请求、资源耗尽、未授权外传、dirty worktree 覆盖、并发文件变化、多文件部分写入、进程中断、遗留租约与残留容器。ACL、owner、extended attributes、磁盘损坏和任意断电点的强持久化证明不在承诺范围内。

## 4. 核心不变量与权威边界

本章要求优先于组件便利性和 LLM 建议。

- **POL-001** LLM MUST 仅提出结构化建议；最终动作裁决 MUST 由确定性 Policy Engine 产生。
- **POL-002** Policy Engine MUST 仅返回 `ALLOW`、`REQUIRE_APPROVAL`、`DENY` 或 `BLOCKED_POLICY_ERROR`。
- **POL-003** 用户审批 MUST NOT 覆盖 `DENY`。
- **WS-001** Baseline Manifest、Task Workspace 实际文件状态和 Harness 计算结果 MUST 是 Agent Change Set 的唯一权威输入。
- **WS-002** Synthetic Git 的 index、objects、refs、branch、commit 状态和 hash MUST NOT 成为审批、验收、恢复、Change Set 或写回依据。
- **ACC-001** LLM MUST NOT 将 Acceptance Contract 条件标记为通过。
- **ACC-002** 所有 required 条件未 `PASSED` 时，任务 MUST NOT 进入 `READY_TO_APPLY`。
- **TXN-001** 任务 MUST 仅在写回成功且复检通过后进入 `COMPLETED`。
- **TXN-002** 用户拒绝应用的任务 MUST 进入 `NOT_APPLIED`，且 MUST NOT 标记为 `COMPLETED`。
- **PST-001** SQLite commit MUST NOT 被解释为文件 Apply Transaction 已完成。
- **PST-002** SSE、浏览器连接和临时日志 MUST NOT 成为任务状态或审计真相来源。
- **TXN-003** Task Workspace 中的变化 MUST NOT 绕过 Change Set 计算、资格检查和用户应用确认进入原仓库。
- **TXN-004** 不确定的外部副作用状态 MUST 进入恢复审计，且 MUST NOT 由 LLM 推测后继续。

## 5. 系统架构、组件职责与依赖方向

### 5.1 总体架构

React/TypeScript WebUI 通过 FastAPI HTTP 与 SSE 接入宿主 Python 3.12 Harness。核心包含 Agent loop、Context Builder、Policy Engine、Acceptance Evaluator、Workspace 管理、Change Set/Apply 协调、持久化接口和窄适配器。真实仓库命令仅由可信 Docker CLI adapter 在一次性容器中运行。

### 5.2 组件边界

- **AGT-001** 核心 Agent、Policy、Acceptance、Transaction 和 Sandbox 领域逻辑 MUST 能脱离 FastAPI 路由并使用 Mock 依赖测试。
- **PST-003** 核心领域层 MUST 通过窄 Store 接口访问持久化，且 MUST NOT 依赖 `sqlite3.Row`、SQL 字符串或数据库表结构。
- **API-001** FastAPI 路由 MUST 通过 application service 调用领域能力，且 MUST NOT 直接操作数据库连接或 Docker CLI。
- **SBX-001** WebUI、LLM 和仓库配置 MUST NOT 提供通用 Docker 参数或通用 Docker 命令入口。
- **AGT-002** LLM Adapter MUST NOT 直接改变任务状态、批准动作或执行工具。
- **GEN-007** MVP MUST 使用单宿主后端进程、单私有数据目录和全局单执行槽。

### 5.3 技术基线

后端技术基线为 Python 3.12、FastAPI、Pydantic v2、标准库 `sqlite3` 和 pytest。前端为 React、TypeScript 与 Vite。Pydantic API 模型是 API schema 的事实来源，TypeScript 类型通过 OpenAPI 或 JSON Schema 生成。核心不使用高层 Agent Runner、ORM、消息队列或分布式 worker。

### 5.4 配置治理

- **GEN-008** Harness MUST 仅从内置安全默认值、受信任宿主配置和显式启动选项构造有效配置，并 MUST 以 schema 严格校验未知字段、类型和范围。
- **GEN-009** 配置优先级 MUST 为“显式受信任启动选项 > 受信任宿主配置 > 内置默认值”；Issue、仓库配置、`.env`、工具输出和 LLM 响应 MUST NOT 进入该优先级链。
- **GEN-010** 每个 Task Run MUST 冻结 Provider/profile/image/endpoint、Policy、预算硬上限、sandbox 安全模板和外传规则的配置摘要；运行期间配置变化 MUST 仅对后续 Run 生效。

## 6. 领域模型、版本绑定与任务状态机

### 6.1 核心对象

Task 表示用户目标；Task Run 表示一次可恢复推进；Plan Version 与 Acceptance Contract Version 为不可变版本；Approval 绑定明确目标；Structured Action 与 Tool Result 形成反馈；Budget State 由代码计数；Baseline Manifest、Change Set 和 Apply Transaction 表示文件事务；Execution Lease 表示全局执行槽占用；Audit Event 表示不可覆盖的治理事实。

- **PST-004** Plan、Acceptance Contract、Approval、Change Set digest 和 Apply Transaction 的持久化身份 MUST 明确且不可由显示文本替代。
- **POL-004** 每个审批 MUST 绑定 task、目标类型、目标 version 或 digest、expected state 和 idempotency key。
- **PST-005** 使用同一 idempotency key 的不同请求摘要 MUST 返回冲突。
- **PST-006** 状态转换 MUST 使用 expected state 或版本号进行乐观并发检查。

### 6.2 状态机原则

完整状态与转换见附录 B。主动执行状态占用执行槽；等待用户状态仅在容器、写入和清理均已结束后释放执行槽；终态不可再执行副作用；恢复状态优先于新任务。

- **AGT-003** 非附录 B 允许的任务状态转换 MUST fail-closed 并产生审计事件。
- **AGT-004** 后端重启 MUST NOT 恢复原 Python 调用栈，而 MUST 从最近可重入持久化阶段重新检查。
- **AGT-005** `AWAITING_PROVIDER_UNLOCK` 中的真实 Provider 任务 MUST 在解锁后由用户显式继续，且 MUST NOT 自动切换到 Mock LLM。

## 7. Agent Loop、Context Builder 与 LLM Adapter

### 7.1 自研循环

- **AGT-006** Harness MUST 自行实现 `context → LLM → structured action → policy → tool → result feedback → stop` 主循环。
- **AGT-007** Harness MUST 提供可注入、离线且确定性的 Mock LLM。
- **AGT-008** 初始阶段 MUST 仅执行只读调查，并在修改前生成任务理解、计划、范围、Acceptance Contract、验证方案和风险。
- **AGT-009** 工具失败和验证失败 MUST 作为结构化反馈进入下一轮上下文。
- **AGT-010** 每个 LLM attempt MUST 在调用前持久化；结果未知的 attempt MUST NOT 被当作从未发生。
- **AGT-011** Agent loop MUST 由确定性代码处理完成、等待用户、blocked、failed、cancelled、预算、循环上限和无进展停止条件。

### 7.2 Context Builder

- **SEC-011** Context Builder MUST 对文件内容、工具输出、diff 和日志分别执行 `readable` 与 `exportable_to_llm` 判定。
- **SEC-012** Context Builder MUST 记录 Provider、发送路径、片段范围、字节数和 digest，且 MUST NOT 在审计中保存 API Key 或不必要源码正文。
- **AGT-012** Context Builder MUST 按确定性顺序和预算构造最小必要上下文，并对截断产生显式标记。

### 7.3 LLM Adapter

- **AGT-013** 真实 Adapter MUST 使用可信 Harness 配置中的固定 Provider 和 endpoint，并实施超时、请求次数、token 与响应大小限制。
- **AGT-014** 固定 Provider 暂时连接失败或超时时，Harness MUST 按附录 E 产生 `PROVIDER_UNAVAILABLE`；Provider、endpoint、凭据或可信连接配置校验失败时，Harness MUST 产生 `PROVIDER_CONFIGURATION_ERROR`。两者 MUST 进入附录 E 规定的确定性状态，且 Harness MUST NOT 自动切换 Provider。
- **AGT-015** `unit-test` 和 Mock LLM 模式 MUST NOT 访问网络或需要真实 API Key。

## 8. 结构化 Action、工具接口与 Synthetic Git

### 8.1 通用 Action 规则

- **ACT-001** LLM 输出 MUST 通过严格判别联合 schema 解析；未知 action、未知字段或无效字段 MUST fail-closed。
- **ACT-002** 每个 action MUST 具有稳定 action ID、明确参数、预算影响和预期结果类型。
- **ACT-003** Harness MUST NOT 接受 LLM 提供的任意 shell、Git 或 Docker 命令字符串。
- **ACT-004** 文件路径 MUST 以结构化仓库根相对路径提供，并在执行前进行规范化、边界和符号链接检查。

### 8.2 MVP 工具能力

MVP 工具包括：仓库探测、文件列表、受限文本读取、受限搜索、结构化文件创建/替换/补丁/删除、profile 验证、Change Set 查询和附录 D 中的 Synthetic Git 操作。

- **ACT-005** 文件读取、搜索、修改和输出 MUST 受单次及累计大小限制。
- **ACT-006** 文件修改 MUST 仅作用于已批准计划范围内的 Task Workspace 路径。
- **ACT-007** 结构化依赖安装动作 MUST 获得 `DENY`；普通网络读取动作 MUST 获得 `DENY`，并使用 `BLOCKED_UNSUPPORTED_CAPABILITY` reason code 区分“当前未实现”与绝对禁止能力。
- **ACT-008** 工具结果 MUST 包含确定性状态、受限输出、资源计数和可审计摘要。
- **ACT-009** Action/Command 闭包 MUST 严格分为 LLM Control Action、LLM Tool Action、用户 HTTP Governance Command 和 Harness Internal Operation，并使用附录 D 的闭合清单。
- **ACT-010** LLM MUST NOT 产生 `approve_plan`、`approve_action`、`confirm_acceptance`、`confirm_apply`、`mark_completed` 或任何用户 Governance Command。
- **ACT-011** `compute_changeset`、Acceptance 评估、租约、Apply phase、恢复和领域事件发布 MUST 是 Harness Internal Operation，且 MUST NOT 通过普通 LLM Action schema 调用。
- **ACT-012** `delete_file` 与 `request_ignored_input` MUST 在 Policy 返回 `REQUIRE_APPROVAL` 后停在 `AWAITING_ACTION_APPROVAL`，且工具副作用 MUST 在匹配审批被消费前保持为零。

### 8.3 Synthetic Git

- **WS-003** Synthetic Git MUST 使用净化环境、临时 HOME/XDG 配置和精确到子命令及参数模式的 allowlist。
- **WS-004** Synthetic Git MUST NOT 允许 commit、refs、branch、tag、remote、history rewrite、工作树恢复、clean 或通用配置操作。
- **WS-005** Synthetic Git index 写入 MUST 仅接受已批准的明确文件数组，且 MUST NOT 接受目录、glob、pathspec magic、`.` 或范围式 add。

## 9. Policy Engine、审批、预算与停止机制

### 9.1 裁决与硬边界

- **POL-005** 未知、无法解析或缺少策略上下文的动作 MUST 返回 `BLOCKED_POLICY_ERROR`。
- **POL-006** 远程 Git 写入、PR/MR、部署、发布、云资源变更、生产数据库写入、生产凭据注入、特权容器及任务侧 Docker 控制 MUST 返回 `DENY`。
- **POL-007** 仓库内配置 MAY 提出能力请求，但 MUST NOT 授予能力或改变可信 profile。

### 9.2 审批

- **POL-008** 修改阶段 MUST 在计划、范围、Acceptance Contract 和验证方案的不可变版本获批后开始。
- **POL-009** 高风险动作 MUST 获得绑定具体 action 的独立审批；审批消费、拒绝和过期 MUST 被审计。
- **POL-010** 计划、契约、范围、预算或 Change Set 变化 MUST 使绑定旧版本的未消费审批失效。

MVP 的授权机制严格分为 Plan Approval、High-risk Action Approval、Budget Reapproval 和 Apply Confirmation。四者具有不同对象、等待状态、失效条件和恢复路径，不得互相替代。

- **POL-015** MVP 的独立 High-risk Action 集合 MUST 严格限定为 `delete_file`（删除 Baseline 已存在的受支持普通文件或符号链接）与 `include_ignored_input`（由 LLM Tool Action `request_ignored_input` 发起），其他 Tool Action MUST NOT 被临时提升为该集合而不经过设计变更。
- **POL-016** `delete_file` 审批 MUST 绑定 task ID、action ID、规范化根相对路径、expected digest、Baseline Manifest digest、Plan Version、expected task state、idempotency key、删除理由和完整 action payload digest。
- **POL-017** `delete_file` 的路径、expected digest、Baseline Manifest、Plan Version、task state 或 action payload 变化时，旧审批 MUST 失效；审批 MUST 仅消费一次且 MUST NOT 覆盖目录、递归、glob、批量或后续删除。
- **POL-018** `include_ignored_input` 审批 MUST 绑定 task ID、action ID、Plan Version、expected task state、完整 action payload digest，并冻结精确文件清单、每个规范化路径、类型、大小、digest、`read_only_input/writable_ephemeral` 模式、允许阶段、Sandbox Input Manifest Version 和 idempotency key。
- **POL-019** 获批 ignored input MUST 始终具有 `exportable_to_llm=false`；High-risk Action Approval MUST NOT 授予远程 Provider 外传能力。
- **POL-020** Plan Approval、High-risk Action Approval、Budget Reapproval 与 Apply Confirmation MUST 分别使用附录 C 的绑定字段和等待/门禁状态，且 MUST NOT 相互替代。

### 9.3 预算与停止

- **POL-011** Harness MUST 确定性计数 Agent 轮数、LLM 调用、工具调用、修改文件数、Change Set 字节数、命令次数、累计时间和输出大小。
- **POL-012** 普通任务预算超限 MUST 进入重新审批；硬安全上限 MUST NOT 通过普通审批提升。
- **POL-013** 下一工具副作用 MUST 在预算检查通过后才能开始。
- **POL-014** 重复失败、循环上限或无进展阈值达到时，Harness MUST 停止推进并记录确定性原因。
- **POL-021** Budget Reapproval MUST 绑定 task ID、Budget Version、各受影响维度当前消费量、原上限、新上限、扩展原因、Plan Version、expected task state 和 idempotency key。
- **POL-022** Budget Reapproval MUST NOT 提升文件系统硬边界、Docker 硬资源上限、输出硬上限、`network none`、Policy `DENY` 或其他绝对安全边界。
- **POL-023** 新 Budget Version MUST 仅在审批事务提交后生效；拒绝和未消费请求 MUST NOT 改变当前预算上限。
- **POL-024** 当前 Plan、范围、预算和 Policy 有效时，`list_files/read_file/search_text/create_file/replace_file/apply_patch/run_validation`、Synthetic Git allowlist 查询、内部 `compute_changeset` 与 diff 展示 MUST NOT 要求独立 High-risk Action Approval；验证方案、profile、预算或范围不匹配 MUST 分别进入 Plan 修订或 Budget Reapproval。

## 10. Acceptance Contract 与验证证据

- **ACC-003** 用户未提供验收标准时，Agent MUST 在只读调查后提出候选 Acceptance Contract 并请求批准。
- **ACC-004** Acceptance Contract MUST 使用不可变版本，并将条件分类为 machine 或 `user_confirmation`。
- **ACC-005** 契约更新 MUST 创建新版本并重新审批，且 MUST NOT 覆盖旧版本。
- **ACC-006** machine 条件 MUST 仅由结构化验证证据更新；`user_confirmation` MUST 仅由绑定当前版本的用户请求更新。
- **ACC-007** 验收条件状态 MUST 限于附录 B/附录 H 定义的 `NOT_RUN`、`PASSED`、`FAILED`、`BLOCKED`。
- **ACC-008** 预检能够证明的工具或声明模块缺失 MUST 产生环境 blocked；正式测试中的错误 MUST NOT 仅凭 stderr 被推断为依赖缺失。
- **ACC-009** 验证证据 MUST 记录动作、profile、退出状态、受限输出摘要、时间和 digest。

任务在 required 条件全部 `PASSED` 后进入 `READY_TO_APPLY`；该状态仅表示具备申请写回资格，不表示用户仓库已修改或任务已完成。

## 11. Baseline、Task Workspace 与文件治理

### 11.1 Baseline 与物化

- **WS-006** 任务启动时的 tracked、staged、unstaged 和 untracked 内容 MUST 构成 Baseline；用户已有修改 MUST NOT 被计入 Agent Change Set。
- **WS-007** Harness MUST 创建不可变 Baseline Manifest，并保存复检和恢复所需的基线内容、digest、类型和支持元数据。
- **WS-008** Agent MUST 仅修改独立 Task Workspace，且 MUST NOT stash、创建临时 commit 或修改原仓库 index。
- **WS-009** 原始 `.git` MUST NOT 被复制或挂载到 Task Workspace；原 HEAD 和分支仅作为独立只读元数据提供。

### 11.2 ignored 与文件类型

- **WS-010** ignored 文件 MUST 默认排除；显式纳入 MUST 绑定不可变清单和 `read_only_input` 或 `writable_ephemeral` 用途。
- **WS-011** ignored inputs MUST NOT 进入最终 Agent Change Set。
- **WS-012** 敏感、越界、超限、用途不明或特殊文件 MUST fail-closed。
- **WS-013** MVP MUST 支持附录 F 列出的普通文件、有限符号链接和 executable bit，并 MUST NOT 宣称保持 ACL、owner 或 extended attributes。
- **WS-014** merge、rebase、cherry-pick、bisect 中间状态及附录 F 标记的不支持仓库形态 MUST 被确定性拒绝。
- **WS-015** `include_ignored_input` MUST 仅在独立 High-risk Action Approval 提交后生成新 Sandbox Input Manifest Version，并 MUST NOT 修改 Baseline Manifest。
- **WS-016** `writable_ephemeral` ignored input MAY 在任务副本中变化，但其原始内容和派生变化 MUST NOT 进入 Agent Change Set 或原仓库写回。

## 12. Sandbox Profile 与 Docker Executor

### 12.1 Profile 与依赖边界

- **SBX-002** MVP MUST 仅提供附录 G 中固定的 Python 3.12 与 Node.js 20/npm profile。
- **SBX-003** 仓库类型和 profile 选择 MUST 由确定性代码完成；LLM MAY 建议但 MUST NOT 最终选择镜像。
- **SBX-004** profile image MUST 来自可信 allowlist 并固定版本或 digest；任务运行期间 MUST NOT 构建或拉取镜像。
- **SBX-005** Harness MUST NOT 提供项目依赖安装能力；缺少明确工具或声明模块 MUST 产生 `BLOCKED_MISSING_DEPENDENCY`。

### 12.2 Docker CLI adapter

- **SBX-006** Executor MUST 使用启动检查解析的可信 Docker CLI 绝对路径、结构化 argv 和 `shell=False`。
- **SBX-007** Docker 环境 MUST 使用正向 allowlist，并固定或隔离 `DOCKER_HOST`、`DOCKER_CONTEXT`、`DOCKER_CONFIG`、TLS、证书和代理变量。
- **SBX-008** MVP MUST 仅允许可信本地 Unix socket endpoint，且 MUST NOT 接受任务提供的 endpoint。
- **SBX-009** 容器 MUST 为非 root、非 privileged、无 host network/PID/device/任意 volume，删除 capabilities，启用 `no-new-privileges` 并设置 CPU、内存、PID、超时和输出限制。
- **SBX-010** Executor MUST 使用 `create → inspect → start/attach → inspect → cleanup` 生命周期，并在启动前验证实际容器配置。
- **SBX-011** 超时或取消 MUST 执行 stop、grace period、kill、rm 和存在性复检；清理失败 MUST 产生 `CLEANUP_FAILED`。
- **SBX-012** Docker 不可用、版本不兼容或安全基线失败时真实执行 MUST blocked，且 MUST NOT 降级为宿主裸执行。
- **SBX-013** Harness MUST 提供 doctor 检查 CLI、daemon、endpoint、固定镜像、安全能力、工作区映射和残留容器。

## 13. Change Set、冲突检测与 Apply Transaction

### 13.1 Change Set 与确认

- **TXN-005** Agent Change Set MUST 通过最终 Task Workspace 与 Baseline Manifest 比较计算，并覆盖新增、修改、删除、支持的符号链接及 executable bit 变化。
- **TXN-006** 用户应用确认 MUST 绑定 Harness 计算的 Change Set digest；确认后内容变化 MUST 使确认失效。
- **TXN-007** 应用前 MUST 比较 Baseline、原仓库当前状态与 Agent 最终状态，并对每个目标路径执行文件级冲突判断。
- **TXN-008** 目标文件发生不兼容并发变化时 Harness MUST 阻止写回，且 MUST NOT 自动文本合并。

### 13.2 Apply Transaction

- **TXN-009** Harness MUST 在写回前生成不可变 Apply Plan，包含目标、预期原状态、新状态、顺序、备份和验证摘要。
- **TXN-010** Harness MUST 在任何原仓库写入前创建并验证必要备份和事务日志。
- **TXN-011** Apply Transaction MUST 先持久化阶段，再执行对应文件副作用。
- **TXN-012** 多文件写回失败时 Harness MUST 进入 `ROLLING_BACK`，按事务日志恢复已写路径，并复检恢复结果。
- **TXN-013** 只有所有目标写入、Change Set 复检和原 index 不变检查通过后，Apply Transaction MAY 标记 `APPLIED`。
- **TXN-014** 无法证明恢复成功时任务 MUST 进入 `RECOVERY_REQUIRED`，且 MUST 阻止新的真实执行。
- **TXN-015** 自动写回 MUST 形成 unstaged 修改，并 MUST NOT 自动 commit、push 或改变用户已有 index。
- **TXN-016** MVP 的恢复承诺 MUST 限于附录 H 定义的支持文件类型、备份完整和确定性故障模型。
- **TXN-017** Apply Confirmation MUST 绑定 task ID、Change Set digest、Baseline Manifest digest、Plan Version、Acceptance Contract Version、`expected state=READY_TO_APPLY` 和 idempotency key。
- **TXN-018** Apply Confirmation MUST NOT 覆盖 Change Set 变化、Baseline 失效、目标路径冲突、required Acceptance 条件失效、非终态 Apply Transaction、`RECOVERY_REQUIRED` 或 Policy `DENY`。
- **TXN-019** Apply Transaction phase MUST 严格使用附录 B 的闭合集合和转换；每个文件步骤完成位置 MUST 同时写入磁盘事务日志并能够在启动恢复时复检。

## 14. 持久化、审计、事件与恢复协调

### 14.1 SQLite 与 Store

- **PST-007** MVP MUST 使用标准库 `sqlite3` 与显式业务意图 Store，且 MUST NOT 引入 ORM 或通用 `execute_sql` 领域接口。
- **PST-008** 任务状态转换及其审计事件 MUST 在同一 SQLite 事务中提交。
- **PST-009** 计划/契约版本、审批消费、预算更新、Change Set 确认和 Apply 阶段变化 MUST 与对应审计事件原子提交。
- **PST-010** 审计事件 MUST append-only；大型源码、diff、容器日志和 artifact MUST 存于私有任务文件并以路径、digest、大小和生命周期状态引用。

### 14.2 Migration 与事件

- **PST-011** schema migration MUST 使用仓库内严格递增的显式 SQL 版本、checksum 和 `schema_migrations` 记录。
- **PST-012** migration checksum 漂移、失败、版本不兼容或并发迁移 MUST 阻止数据库写功能，且 MVP MUST NOT 自动 downgrade。
- **PST-013** 持久化领域事件 MUST 具有全局单调 event ID，并与产生它的状态变化原子提交。
- **PST-014** SSE publisher MUST 从持久化事件读取补发数据；内存通知 MUST NOT 是唯一交付来源。

### 14.3 锁、租约与恢复

- **PST-015** 同一私有数据目录 MUST 由 OS 进程锁限制为单个 serve 实例；该锁 MUST 与 SQLite Execution Lease 分离。
- **PST-016** 全局仅一个 Execution Lease MAY 处于有效执行状态，并绑定 task、run、owner、获取时间、最近进展和阶段。
- **PST-017** 过期 heartbeat MUST 仅触发恢复审计，且 MUST NOT 自动授权另一任务抢占执行槽。
- **PST-018** 后端启动 MUST 检查非终态租约、残留容器、非终态 Apply Transaction、任务目录和事务日志一致性。
- **PST-019** 等待用户时只有在容器、文件副作用和清理均处于安全终态后，Execution Lease MAY 释放。
- **PST-020** 恢复流程 MUST 优先占用执行槽；未完成恢复 MUST 阻止新的 Agent loop、Docker 命令和 Apply Transaction。
- **PST-025** `BLOCKED` Task State MUST 伴随附录 B 的闭合 reason code；reason MUST 确定性规定 continue、重新调查、外部修复、授权失效、Execution Lease 和下一用户命令。
- **PST-026** 等待 Plan、Action 或 Budget 审批前，Harness MUST 完成容器与副作用安全清理并释放 Execution Lease；审批提交 MUST NOT 自动启动 Agent loop。
- **PST-027** 计划修订 MUST 创建并保留新 Plan Version，保留旧版本历史，使旧未消费 Action Approval 失效，并在 Acceptance 语义变化时创建新 Contract Version。
- **PST-028** 计划修订等待期间 MAY 保留 Task Workspace 已有修改，但新版本获批并由用户显式 `continue_task` 前 MUST NOT 执行新的写操作。

## 15. API、SSE、WebUI 与凭据管理

### 15.1 HTTP 与 SSE

- **API-002** 澄清提交、Plan Approval、High-risk Action Approval、Budget Reapproval、用户 Acceptance 确认、取消、显式继续、Apply Confirmation 和恢复请求 MUST 通过独立 HTTP POST API 提交。
- **API-003** 控制请求 MUST 包含 expected state、相关 version/digest 和 idempotency key；不匹配 MUST 返回冲突。
- **API-004** SSE MUST 仅推送状态、动作摘要、进度、有界日志、审批请求、验收、Change Set、冲突和恢复视图。
- **API-005** 持久化 SSE 事件 MUST 采用至少一次投递；客户端 MUST 按 event ID 去重并支持 `Last-Event-ID` 补发。
- **API-006** 临时日志 MAY 不完整补发，但 MUST 有界并明确标记截断或重连缺口。
- **API-007** SSE 断线、无订阅者或浏览器关闭 MUST NOT 改变任务生命周期。
- **API-008** WebUI MUST 提供 Issue、计划审批、动作审批、状态、验收、diff、应用确认及冲突/恢复结果的最小流程。
- **API-009** 正式服务 MUST 默认监听 loopback，并提供任务详情 GET API用于页面恢复。
- **API-010** 用户 Governance Command MUST 严格限定为附录 D 清单，并通过 HTTP 的 expected state、版本/digest 与 idempotency key 检查后才能改变领域状态。

除独立的 `continue_task` 外，澄清、审批、拒绝、Acceptance、Apply 和恢复请求的提交不得隐式启动 Agent loop；`request_recovery` 只进入附录 B 定义的恢复获取路径。

### 15.2 凭据管理

- **CRD-001** 正式 API Key MUST 存于 Harness 私有数据目录中的口令加密凭据文件，且 MUST NOT 仅依赖环境变量。
- **CRD-002** 凭据加密 MUST 使用成熟库提供的 password-based KDF 与认证加密，并为每个文件使用随机 salt、每次加密使用新 nonce。
- **CRD-003** 凭据格式 MUST 包含版本、受界 KDF 参数和非敏感元数据，并 MUST 通过 associated data 检测元数据篡改。
- **CRD-004** 私有数据目录和凭据文件权限 MUST 分别限制为 `0700` 和 `0600`；权限过宽、格式未知、认证失败或文件损坏 MUST fail-closed。
- **CRD-005** `harness serve --unlock` MUST 仅从 TTY 隐藏输入主口令，并在同一 Python 进程解密后启动 API 与 Agent 服务。
- **CRD-006** 无 TTY、错误口令或解密失败时 `serve --unlock` MUST NOT 以 unlocked 状态启动，也 MUST NOT 明文回退。
- **CRD-007** 主口令、派生密钥和明文 API Key MUST NOT 进入 argv、持久环境、SQLite、日志、SSE、错误响应、Task Workspace、任务容器或 LLM 上下文。
- **CRD-008** CLI `credentials status` MUST 仅报告文件状态、serve 锁占用、Provider 标识和格式版本；运行中 WebUI/API MAY 报告 `not_configured/locked/unlocked/error`。
- **CRD-009** `unlocked` MUST 仅存在于当前后端内存，且 MUST NOT 写入 SQLite；后端重启 MUST 从 locked 开始。
- **CRD-010** `credentials update` 和 `credentials clear` MUST 在 serve 锁被占用时拒绝，并使用安全的临时文件、权限设置、原子替换和复检更新磁盘状态。
- **CRD-011** 环境变量凭据 MAY 作为显式启用的兼容模式，但 MUST NOT 自动写入凭据文件或传入任务环境，并 MUST 被文档标记为非正式安全存储。
- **CRD-012** `credentials init` MUST 通过 TTY 隐藏输入主口令与 API Key，仅创建一个正式 Provider 凭据槽，并在 serve 进程锁被占用时拒绝。
- **CRD-013** `credentials init` MUST NOT 从 argv、普通环境变量、WebUI 或文件参数读取主口令；初始化成功 MUST NOT 被解释为运行中后端已 `unlocked`。
- **SEC-014** Provider Adapter MUST NOT 跟随超出固定可信 Provider 连接策略的 redirect。
- **SEC-015** Provider endpoint MUST NOT 被 Issue、仓库配置、`.env`、工具输出、LLM response、普通 HTTP header 或 WebUI 任务字段覆盖。

## 16. 错误模型、恢复建议与可观测证据

本章仅定义分类原则和语义；附录 E 是闭合错误码的唯一权威清单。

- **PST-021** 正式错误类别 MUST 由确定性代码根据操作阶段、结构化结果和持久化状态产生，且 MUST NOT 由 LLM 解释自由文本决定。
- **PST-022** 每个附录 E 错误码 MUST 定义状态影响、可重试性、审批失效、执行槽行为、用户建议和审计要求。
- **SEC-013** 用户可见错误、Provider 错误、Docker stderr 和工具输出 MUST 经过大小限制与敏感信息过滤。
- **PST-023** Harness MUST 区分正式 append-only 审计、持久化领域事件和有界临时日志。
- **PST-024** Policy 裁决、审批、预算、验证、Change Set、Apply 阶段、故障和恢复结果 MUST 产生可关联 task/run/action 的审计证据。

## 17. 测试、验收、分发与课程合规

### 17.1 测试与演示

- **TST-001** 核心 Agent loop、Policy、预算、验收和停止机制 MUST 在 Mock LLM、Fake Store/Clock/Executor 下离线确定性测试。
- **TST-002** SQLite、migration、并发、Manifest、Change Set 和 Apply Transaction MUST 使用临时真实文件系统与 SQLite 文件进行集成测试。
- **TST-003** Docker CLI adapter MUST 由单独真实 Docker 集成测试验证安全配置、超时、取消和清理。
- **TST-004** MVP MUST 提供 dependency-ready Python fixture 的完整主贡献路径及 Node.js/TypeScript fixture 的跨 profile 成功与失败反馈路径。
- **TST-005** MVP MUST 演示危险动作被阻止、注入失败后下一动作改变、多文件写回故障恢复三项确定性机制。
- **TST-006** API/SSE 测试 MUST 覆盖提交失败不发布成功事件、重连顺序、重复去重、旧审批冲突及无订阅者状态正确性。
- **TST-007** 凭据测试 MUST 离线覆盖正确/错误口令、随机化、篡改、权限、原子更新和已知输出面无明文泄漏。
- **TST-008** 每项 MVP 需求 MUST 在附录 H 关联 planned evidence category，并 MUST 在后续 `PLAN.md` 或测试证据索引中获得独立 Planned Verification ID。

### 17.2 分发与环境

- **DST-001** 正式分发 MUST 是宿主 Python 应用包，并包含已构建 React WebUI 静态资源。
- **DST-002** 最终用户运行环境 MUST 要求支持的 Linux/WSL2、Python 3.12、Docker CLI 和可访问 daemon；Node.js 20 MUST 仅作为开发及前端构建依赖。
- **DST-003** 正式分发 MUST 提供 doctor、凭据管理、serve 启动命令和默认本地可访问 URL。
- **DST-004** Docker 不可用时 WebUI MAY 查看历史，但真实命令执行 MUST blocked。
- **DST-005** README MUST 准确说明 dependency-ready、支持环境、威胁边界、安装、启动、恢复和卸载约束。

### 17.3 课程与过程合规

- **PRC-005** `.gitlab-ci.yml` MUST 包含名称严格为 `unit-test` 的离线 job，且该 job MUST NOT 需要 Docker、网络或真实 API Key。
- **PRC-006** 项目 MUST 提供 `SPEC.md`、`PLAN.md`、`SPEC_PROCESS.md`、`AGENT_LOG.md`、`README.md` 和 `REFLECTION.md`。
- **PRC-007** 开发过程 MUST 留存 Superpowers、TDD、Git worktree、subagent、两阶段评审和冷启动验证证据。
- **PRC-008** 冷启动验证 MUST 从全新支持环境复现安装、doctor、WebUI 和至少一个 Mock LLM 任务。

## 18. MVP 边界、Stretch Goals 与需求追踪

### 18.1 MVP 边界

带 ID 的 MUST 与 MUST NOT 是 MVP 强制完成和验收条件。SHOULD 与 SHOULD NOT 默认必须满足；偏离时必须有获批的偏离记录、理由、风险与替代证据。MAY 是可选能力，不构成 MVP 完成门槛；一旦实现，必须遵守该 MAY 句中的约束。六个 Harness 维度均须运行，评估重点为受治理事务执行。

### 18.2 明确排除项

MVP 明确排除：自动 commit/push/PR/发布/部署；任务网络；依赖安装；动态镜像构建或拉取；第三种语言；自定义 profile；完整 Git/history/submodule/LFS/sparse checkout；自动文本合并；多 worker、自动队列和分布式执行；多用户认证；WebSocket；ORM；消息队列；通用后代进程监控；原生 Windows/macOS；数据库与文件系统统一原子事务；任意崩溃点或磁盘损坏的自动恢复。

### 18.3 Stretch Goals

Stretch goals 包括可信离线依赖缓存、自定义 profile、宿主网络读取 broker、Synthetic commit、更多生态、跨仓库有限并发、高级残留资源清理、高级 diff UI、进程级行为检测、Docker SDK adapter、远程访问认证和跨平台 sandbox。它们不属于附录 H 的 MVP 验收集合。

### 18.4 追踪方法

附录 H 是 Planned Evidence Category Matrix，不声称已建立逐需求 Verification ID。`Implementation Status` 初始统一为 `PLANNED`；后续 `PLAN.md`、测试和实现 MAY 更新状态与证据引用，但 MUST NOT 改写需求语义。

- **PRC-009** 每项需求状态更新 MUST 保留需求 ID、原语义和证据引用。
- **PRC-010** 未经批准，Stretch goal MUST NOT 被重分类为 MVP。

# 附录 A：术语表

| 术语 | 定义 |
|---|---|
| Baseline | 用户启动任务时 Harness 可见的原仓库工作树状态。 |
| Baseline Manifest | Baseline 文件内容、类型、digest 和受支持元数据的不可变清单。 |
| Task Workspace | Agent 唯一允许修改的一次性独立任务副本。 |
| Agent Change Set | Task Workspace 最终状态相对 Baseline Manifest 的 Harness 计算差异。 |
| Synthetic Git | Task Workspace 内提供有限 Git 查询与 index 兼容的非权威仓库。 |
| Acceptance Contract | 经审批、不可变版本化的 machine 与用户确认验收条件集合。 |
| Apply Transaction | 使用 Apply Plan、备份、事务日志、复检和回滚向原仓库写回的文件事务。 |
| Execution Lease | SQLite 中记录唯一真实执行槽占用及恢复线索的业务租约。 |
| serve 进程锁 | 限制同一私有数据目录只有一个后端实例的 OS 锁。 |
| dependency-ready | 能在固定 profile、默认断网且不安装依赖的沙箱中执行批准验证的仓库。 |
| 持久化领域事件 | 与状态变化原子提交、可供 SSE 补发和审计关联的事件。 |
| 临时运行事件 | 有界日志或进度；允许截断，不是状态真相。 |
| `exportable_to_llm` | Context Builder 对内容是否可发送给固定远程 Provider 的独立判定。 |

# 附录 B：完整状态转换表

## B.1 Task State 闭合集合

`DRAFT`、`INVESTIGATING`、`AWAITING_CLARIFICATION`、`AWAITING_PLAN_APPROVAL`、`READY_TO_EXECUTE`、`EXECUTING`、`AWAITING_ACTION_APPROVAL`、`AWAITING_BUDGET_APPROVAL`、`VERIFYING`、`AWAITING_USER_CONFIRMATION`、`READY_TO_APPLY`、`APPLYING`、`ROLLING_BACK`、`RECOVERY_REQUIRED`、`AWAITING_PROVIDER_UNLOCK`、`BLOCKED`、`FAILED`、`CANCELLED`、`NOT_APPLIED`、`COMPLETED`。

| 当前状态 | 确定性触发与前置条件 | 目标状态 | Execution Lease 与副作用 |
|---|---|---|---|
| `DRAFT` | 用户提交有效任务 | `INVESTIGATING` | 获取 Lease，建立 Baseline |
| `INVESTIGATING` | 需要用户澄清 | `AWAITING_CLARIFICATION` | 安全清理后释放 Lease |
| `INVESTIGATING` | 新 Plan/Contract/验证方案已持久化 | `AWAITING_PLAN_APPROVAL` | 安全清理后释放 Lease |
| `AWAITING_CLARIFICATION` | `submit_clarification` 原子持久化澄清与审计事件 | `INVESTIGATING` | 不获取 Lease，不自动执行；等待独立 `continue_task` |
| `INVESTIGATING` | 澄清已提交后的 `continue_task`，且 Lease、Provider、Baseline/仓库身份、调查上下文、恢复任务和硬预算检查全部通过 | `INVESTIGATING` | 原子获取 Lease，继续只读调查 |
| `AWAITING_PLAN_APPROVAL` | 当前 Plan Version 获批 | `READY_TO_EXECUTE` | 新授权生效；不自动执行 |
| `AWAITING_PLAN_APPROVAL` | 当前 Plan Version 被拒 | `CANCELLED` | 终态，无写回 |
| `READY_TO_EXECUTE` | `continue_task` 且 Provider、Lease、Baseline、Plan、Contract、Budget、恢复检查通过 | `EXECUTING` | 原子获取 Lease |
| `READY_TO_EXECUTE` | 绑定真实 Provider 且运行时 locked | `AWAITING_PROVIDER_UNLOCK` | 不获取 Lease |
| `EXECUTING` | 提出 `delete_file` 或 `request_ignored_input` | `AWAITING_ACTION_APPROVAL` | 持久化请求，安全清理后释放 Lease |
| `AWAITING_ACTION_APPROVAL` | 当前 action 获批 | `READY_TO_EXECUTE` | 审批可消费；仍需 `continue_task` |
| `AWAITING_ACTION_APPROVAL` | 当前 action 被拒 | `READY_TO_EXECUTE` | 拒绝反馈持久化；仍需 `continue_task` |
| `EXECUTING` / `VERIFYING` | RunLimits 达到普通阈值，或策略接受阈值前的 `request_budget_extension`；扩展请求已持久化 | `AWAITING_BUDGET_APPROVAL` | 安全清理后释放 Lease；旧预算保持有效 |
| `AWAITING_BUDGET_APPROVAL` | `approve_budget_extension` 原子提交新 Budget Version | `READY_TO_EXECUTE` | 新预算生效；仍需 `continue_task` |
| `AWAITING_BUDGET_APPROVAL` | `reject_budget_extension` 且用户选择保留任务 | `BLOCKED` | reason=`BUDGET_EXTENSION_REJECTED`；释放 Lease |
| `AWAITING_BUDGET_APPROVAL` | `cancel_task` | `CANCELLED` | 终态 |
| `EXECUTING` | Action 超出批准范围且新 Plan Version/必要 Contract Version 已持久化 | `AWAITING_PLAN_APPROVAL` | 已有 Workspace 修改保留；禁止继续写；释放 Lease |
| `EXECUTING` | 开始批准验证 | `VERIFYING` | 保持 Lease |
| `VERIFYING` | required machine 条件通过且仍有用户确认 | `AWAITING_USER_CONFIRMATION` | 清理后释放 Lease |
| `VERIFYING` | required 条件全部通过且 Change Set 已确定性计算 | `READY_TO_APPLY` | 释放 Lease，等待 Apply Confirmation |
| `VERIFYING` | 验证失败、允许反馈且预算未达阈值 | `EXECUTING` | 保持 Lease，进入结构化反馈 |
| `AWAITING_USER_CONFIRMATION` | 当前 Contract 的 required 用户条件均确认 | `READY_TO_APPLY` | 计算/复检 Change Set，不自动应用 |
| `AWAITING_USER_CONFIRMATION` | 用户拒绝 required 条件 | `BLOCKED` | reason=`USER_ACCEPTANCE_REJECTED`；释放 Lease |
| `READY_TO_APPLY` | `confirm_apply` 绑定均匹配且冲突/恢复检查通过 | `APPLYING` | 获取 Lease，创建 Apply Transaction |
| `READY_TO_APPLY` | `reject_apply` | `NOT_APPLIED` | 终态，无写回 |
| `APPLYING` | phase=`APPLIED` 且写回/复检/index 检查通过 | `COMPLETED` | 清理并释放 Lease |
| `APPLYING` | 文件写入失败且回滚证据可用 | `ROLLING_BACK` | 保持 Lease，phase 进入 `ROLLING_BACK` |
| `ROLLING_BACK` | phase=`ROLLED_BACK` 且恢复 digest 复检成功 | `FAILED` | 释放 Lease，保留事务证据 |
| `ROLLING_BACK` | phase=`RECOVERY_REQUIRED` | `RECOVERY_REQUIRED` | 阻止新执行 |
| `RECOVERY_REQUIRED` | `request_recovery` 且恢复证据检查通过 | `ROLLING_BACK` | 优先获取 Lease |
| `AWAITING_PROVIDER_UNLOCK` | unlocked 后 `continue_task` 且全部恢复检查通过 | `EXECUTING` | 获取 Lease；不得自动继续 |
| `BLOCKED` | reason 为 missing dependency、Docker、Provider、persistence 或已修复 Policy error，且 `continue_task` 前置复检通过 | `EXECUTING` | 原子获取 Lease；一次显式命令恢复执行 |
| `BLOCKED` | reason 为 unsupported capability、context export、budget extension rejection 或 user acceptance rejection，且 `submit_clarification` 已持久化 | `INVESTIGATING` | 不获取 Lease，不自动调查；等待独立 `continue_task`；旧授权按 B.2 失效 |
| `BLOCKED` | reason=`APPLY_CONFLICT` 且用户提交 `continue_task`，重新调查前置检查通过 | `INVESTIGATING` | 原子获取 Lease，重新调查目标路径；旧授权按 B.2 失效 |
| 任意非终态（无不确定文件副作用） | `cancel_task` 且安全清理完成 | `CANCELLED` | 释放 Lease |
| 任意主动状态 | 附录 E 指定 blocked reason | `BLOCKED` | 按 B.2 处理 Lease 与下一命令 |
| 任意主动状态（无不确定文件副作用） | 附录 E 指定不可恢复失败 | `FAILED` | 安全清理后释放 Lease |

终态严格为 `COMPLETED`、`NOT_APPLIED`、`FAILED`、`CANCELLED`。存在不确定文件副作用时必须使用 `RECOVERY_REQUIRED`。`EXECUTION_SLOT_BUSY` 是 HTTP 命令结果，不是 Task State。Acceptance 条件状态严格为 `NOT_RUN`、`PASSED`、`FAILED`、`BLOCKED`。

`submit_clarification` 只持久化用户输入和审计事件。澄清后的 `INVESTIGATING` 在没有 Execution Lease 时是暂停的调查状态；`continue_task` 通过表中全部复检后才恢复只读调查。该路径必须继续创建 Plan Version、Acceptance Contract Version 和验证方案并进入 `AWAITING_PLAN_APPROVAL`，不得直接进入 `READY_TO_EXECUTE` 或修改阶段。MVP 不引入通用 `resume_state`。

## B.2 `BLOCKED` reason 闭合语义

| reason code | `continue_task` | 重新调查/外部修复 | 授权影响 | Lease | 用户下一命令 |
|---|---|---|---|---|---|
| `BLOCKED_MISSING_DEPENDENCY` | 环境修复并重新 preflight 后允许 | 外部准备 dependency-ready 环境；重新调查环境 | Plan/Contract 保留；环境证据失效 | 释放 | 修复环境后 `continue_task` |
| `BLOCKED_UNSUPPORTED_CAPABILITY` | 当前 MVP 内不允许 | 修改任务目标或提交新 Plan | 当前 action 失效；Plan 需修订 | 释放 | `cancel_task` 或提交澄清后 `continue_task` |
| `DOCKER_UNAVAILABLE` | doctor 恢复通过后允许 | 外部修复 Docker；无需代码调查 | Plan/Contract 保留；运行环境证据失效 | 释放 | 运行 doctor 后 `continue_task` |
| `PROVIDER_UNAVAILABLE` | Provider 健康检查通过后允许 | 外部修复固定 Provider 配置/服务 | Plan/Contract 保留；未知 attempt 仍计预算 | 释放 | 修复后 `continue_task` |
| `CONTEXT_EXPORT_DENIED` | 提供不需要被禁内容的新任务/计划后允许 | 重新调查可导出上下文 | 当前 Plan 需修订；相关审批失效 | 释放 | 提交澄清后 `continue_task` |
| `APPLY_CONFLICT` | 重新调查并产生新 Baseline/Plan/Change Set 后允许 | 必须重新调查目标路径 | Apply Confirmation 及旧 Change Set 失效 | 释放 | `continue_task` 进入重新调查 |
| `BLOCKED_POLICY_ERROR` | Policy 输入/实现问题修复且审计确认后允许 | 重新执行 Policy 前置检查 | 当前 action 不获授权；审批不得覆盖 | 释放 | 修复配置后 `continue_task` |
| `PROVIDER_CONFIGURATION_ERROR` | 修复可信配置并重启后允许 | 外部修复固定 Provider 配置 | Plan/Contract 保留；Provider 环境证据失效 | 释放 | 修复后 `continue_task` |
| `PERSISTENCE_FAILED` | 存储健康检查通过后允许 | 外部修复 Harness 私有存储 | 未提交状态/审批保持未生效 | 释放 | 修复后 `continue_task` |
| `BUDGET_EXTENSION_REJECTED` | 提交缩小任务目标的澄清后允许 | 重新调查原预算内的安全方案 | 扩展请求失效；原预算保留 | 释放 | `submit_clarification` 后 `continue_task` |
| `USER_ACCEPTANCE_REJECTED` | 新 Contract Version 获批后允许 | 修订实现与契约 | 当前 Contract 相关 Apply 资格失效 | 释放 | 提交澄清后 `continue_task` |

## B.3 Apply Transaction Phase Transition Table

phase 闭合集合为 `PREPARING`、`BACKUP_READY`、`APPLYING`、`APPLIED`、`ROLLING_BACK`、`ROLLED_BACK`、`RECOVERY_REQUIRED`。

| 目标 phase | 合法前置 | SQLite 与磁盘日志顺序 | 文件副作用 | 启动恢复行为 | 终态/阻止新执行 |
|---|---|---|---|---|---|
| `PREPARING` | 无现存非终态事务；Apply Confirmation 有效 | 先原子持久化 Apply Plan 与 phase并创建日志头，再逐项写入备份 pending/completed 记录 | 在 Harness 私有事务目录创建备份；不改原仓库 | 验证 Plan 与备份日志；备份不完整时进入 `RECOVERY_REQUIRED` | 非终态；阻止 |
| `BACKUP_READY` | `PREPARING` 且全部备份 digest 复检成功 | 先写入并刷新完整备份证据，再持久化 phase | 不新增文件副作用 | 复检全部备份；失败则 `RECOVERY_REQUIRED` | 非终态；阻止 |
| `APPLYING` | `BACKUP_READY` | 先持久化 phase；每个文件写入前记录 pending step，完成后记录 completed step | 按 Apply Plan 修改目标文件 | 依据最后 completed step 复检；不能证明一致则回滚 | 非终态；阻止 |
| `APPLIED` | `APPLYING` 且全部新 digest、Change Set 和 index 复检成功 | 先记录最终复检证据，再持久化 phase | 不再新增写入 | 确认终态证据后完成 Task；证据不完整则 `RECOVERY_REQUIRED` | 终态；不阻止 |
| `ROLLING_BACK` | `APPLYING` 或启动恢复判定需回滚 | 先持久化 phase；每个恢复步骤同样记录 pending/completed | 由备份逆序恢复已影响路径 | 从最后 completed rollback step 继续并复检 | 非终态；阻止 |
| `ROLLED_BACK` | `ROLLING_BACK` 且全部原 digest 复检成功 | 先记录恢复复检证据，再持久化 phase | 不再新增写入 | 将 Task 转为 `FAILED` 并保留证据 | 终态；不阻止 |
| `RECOVERY_REQUIRED` | 任意非终态 phase 无法证明安全状态 | 先持久化 reason 与已知日志位置 | 禁止自动新增写入 | 等待 `request_recovery` 和证据检查 | 非终态；阻止 |

# 附录 C：Policy 决策矩阵

## C.1 四类授权机制

| 机制 | 授权对象 | 必需绑定 | 等待/门禁状态 | 生效与恢复 |
|---|---|---|---|---|
| Plan Approval | Plan、范围、Acceptance Contract、验证方案 | task、Plan Version、Contract Version、范围 digest、expected state、idempotency key | `AWAITING_PLAN_APPROVAL` | 批准后到 `READY_TO_EXECUTE`；必须显式 `continue_task` |
| High-risk Action Approval | 仅 `delete_file`、`include_ignored_input` | POL-016 或 POL-018 的完整字段 | `AWAITING_ACTION_APPROVAL` | Policy 对原 Tool Action 返回 `REQUIRE_APPROVAL` 后由 Internal Operation 创建；批准/拒绝后到 `READY_TO_EXECUTE`；必须显式 `continue_task` |
| Budget Reapproval | 新 Budget Version，不是 Tool Action | POL-021 的完整字段 | `AWAITING_BUDGET_APPROVAL` | LLM 可提前建议；RunLimits 达到普通阈值时必须自动创建请求；批准后到 `READY_TO_EXECUTE`并显式继续 |
| Apply Confirmation | 当前 Change Set 的事务提交门禁，不是 Tool Action | TXN-017 的完整字段 | `READY_TO_APPLY` | 匹配且复检通过后到 `APPLYING` |

## C.2 Action Policy 决策

| 能力/动作 | 当前授权条件 | PolicyDecision | reason code / 后续状态 |
|---|---|---|---|
| 调查阶段受限只读文件动作 | 调查预算和路径策略有效 | `ALLOW` | 保持 `INVESTIGATING` |
| `list_files/read_file/search_text` | 当前 Plan 范围与预算有效 | `ALLOW` | 保持主动状态 |
| `create_file/replace_file/apply_patch` | 当前 Plan、Contract、范围和预算有效 | `ALLOW` | 保持 `EXECUTING` |
| 固定 profile 的 `run_validation` | 已批准验证方案、profile、范围和预算均匹配 | `ALLOW` | `VERIFYING`；每次验证不独立审批 |
| Synthetic Git allowlist 查询 | 路径和预算有效 | `ALLOW` | 保持主动状态 |
| `delete_file` 删除 Baseline 已有文件 | 尚无匹配未消费审批 | `REQUIRE_APPROVAL` | `AWAITING_ACTION_APPROVAL` |
| `include_ignored_input` | 尚无匹配未消费审批 | `REQUIRE_APPROVAL` | `AWAITING_ACTION_APPROVAL` |
| 普通预算达到阈值 | 未达到硬上限 | `REQUIRE_APPROVAL` | 治理请求进入 `AWAITING_BUDGET_APPROVAL` |
| 阈值前的有效 `request_budget_extension` | 请求上限不超过硬边界且绑定字段完整 | `REQUIRE_APPROVAL` | 治理请求进入 `AWAITING_BUDGET_APPROVAL` |
| 计划范围外或验证方案/profile 不匹配 | 需要新 Plan Version | `REQUIRE_APPROVAL` | 进入 `AWAITING_PLAN_APPROVAL`；不是 Action Approval |
| 当前 Change Set 申请应用 | 满足 `READY_TO_APPLY` 前置条件 | `REQUIRE_APPROVAL` | Apply Confirmation 门禁；保持 `READY_TO_APPLY` |
| 未知 action、参数或策略上下文 | 无法安全裁决 | `BLOCKED_POLICY_ERROR` | `BLOCKED`，reason=`BLOCKED_POLICY_ERROR` |
| 普通网络读取 | MVP 能力未实现 | `DENY` | `BLOCKED`，reason=`BLOCKED_UNSUPPORTED_CAPABILITY` |
| 敏感/越界/特殊文件、任意命令字符串、安装、远程写入、部署、发布、生产资源、凭据注入、任务 Docker 控制、privileged/host namespace/device/任意 volume | 绝对边界 | `DENY` | 工具副作用为零；审批不可覆盖 |

PolicyDecision、reason code 和 Task State 是三个独立枚举。`REQUIRE_APPROVAL` 只描述裁决；具体使用四类机制中的哪一种，由本附录的动作/治理对象映射确定。

# 附录 D：结构化 Action 清单

## D.1 LLM Control Actions

| Action | 必需语义 | 直接副作用 |
|---|---|---|
| `request_clarification` | 仅在调查或重新调查阶段提出完成调查所需的一个明确问题 | 无；进入澄清等待路径 |
| `propose_plan` | 提交新不可变 Plan/Contract/验证方案候选 | 仅持久化候选；不批准 |
| `request_budget_extension` | 提交受影响维度、当前消费量、新上限和原因 | 仅创建治理请求 |
| `request_user_confirmation` | 引用当前 Contract Version 的 `user_confirmation` 条件 | 无 |
| `report_blocked` | 引用附录 E 的可用 reason code 和结构化证据 | 状态由确定性状态机决定 |
| `stop_with_failure` | 报告不能继续的失败及证据 | 是否进入 `FAILED` 由状态机决定 |
| `stop_without_safe_action` | 明确没有安全可执行 action | 进入安全停止评估 |

LLM Control Action 闭合集合仅为上表。LLM 不得产生 `approve_plan`、`approve_action`、`confirm_acceptance`、`confirm_apply`、`mark_completed` 或 D.3 的 Governance Command。

`delete_file` 和 `request_ignored_input` 本身就是高风险能力请求。Policy Engine 对原 Tool Action 返回 `REQUIRE_APPROVAL` 后，Harness Internal Operation `create_action_approval_request` 使用原 action ID、完整 payload digest、task、Plan Version、expected state 及 POL-016/POL-018 的额外字段创建审批记录；LLM 不再提出第二个审批请求，原 Tool Action 在审批消费前没有工具副作用。

`request_budget_extension` 允许 LLM 在普通阈值到达前提出预算扩展建议，但不是建立 Budget Reapproval 的必要条件。确定性 RunLimits 在普通阈值到达时必须自行创建绑定当前消费量和 Budget Version 的 Budget Reapproval 请求。

## D.2 LLM Tool Actions

| Action | 核心字段 | 约束/效果 |
|---|---|---|
| `inspect_repository` | 无任务自定义命令 | 只读仓库身份、状态和 profile 信号 |
| `list_files` | 明确根相对路径、限制 | 只读；边界和输出预算 |
| `read_file` | 文件、范围、字节上限 | 只读；敏感/类型/大小检查 |
| `search_text` | 固定文本、明确路径清单、上限 | 不接受 shell 命令或 glob 路径 |
| `create_file` | 路径、内容 | 仅批准范围和 Task Workspace |
| `replace_file` | 路径、expected digest、内容 | 乐观检查后替换 |
| `apply_patch` | 路径、结构化 patch、expected digest | 不接受 shell patch 命令 |
| `delete_file` | 单个路径、expected digest、理由 | 仅受支持文件；必须独立 Action Approval |
| `request_ignored_input` | 精确文件清单、模式、阶段、manifest version | 必须独立 Action Approval；批准后由内部操作物化 |
| `run_validation` | profile、固定 operation | 附录 G 操作；Docker 沙箱 |
| `git_repo_probe` | 无 | `git rev-parse --is-inside-work-tree` |
| `git_repo_root` | 无 | `git rev-parse --show-toplevel` |
| `git_status` | 无 | `git status --porcelain=v1 -z --untracked-files=all` |
| `git_diff_worktree` | 可选明确文件数组 | `git diff --no-ext-diff --no-textconv -- <paths>` |
| `git_diff_index` | 可选明确文件数组 | `git diff --cached --no-ext-diff --no-textconv -- <paths>` |
| `git_list_tracked` | 可选明确文件数组 | `git ls-files -z --cached -- <paths>` |
| `git_list_untracked` | 可选明确文件数组 | `git ls-files -z --others --exclude-standard -- <paths>` |
| `git_stage_paths` | 非空明确文件数组 | `git add -- <paths>`；须在批准 writable 范围 |
| `git_unstage_paths` | 非空明确文件数组 | `git restore --staged -- <paths>`；不改工作树 |

LLM Tool Action 闭合集合仅为上表。Git 路径不得为目录、`.`、绝对路径、含 `..`/NUL、以 `-` 开头、glob 或 pathspec magic。未列出的 Git 子命令、选项、缩写、`-c`、`--config-env`、`--git-dir`、`--work-tree` 和 `-C` 均 fail-closed。

## D.3 用户 HTTP Governance Commands

`submit_clarification`、`approve_plan`、`reject_plan`、`approve_action`、`reject_action`、`approve_budget_extension`、`reject_budget_extension`、`confirm_user_acceptance`、`reject_user_acceptance`、`continue_task`、`cancel_task`、`confirm_apply`、`reject_apply`、`request_recovery`。

该清单是 MVP Governance Command 闭合集合。这些命令只能来自用户 HTTP 请求，必须经过身份为本地用户的运行边界、expected state、版本/digest 和 idempotency 检查；它们不是 LLM Action。

## D.4 Harness Internal Operations

`build_baseline`、`materialize_workspace`、`materialize_ignored_input`、`create_action_approval_request`、`compute_changeset`、`evaluate_acceptance`、`acquire_execution_lease`、`release_execution_lease`、`begin_apply_transaction`、`advance_apply_phase`、`recover_apply_transaction`、`publish_domain_event`。

该清单是 MVP Internal Operation 闭合集合。Internal Operation 由确定性状态机触发，不得通过普通 LLM Action schema 或用户通用调用接口执行。`compute_changeset` 明确属于 Internal Operation，不是 Tool Action。

# 附录 E：错误码清单

本附录是闭合错误码的唯一权威清单。

“预算”列中的“是”表示本次已开始的 LLM/tool/command attempt 按其类别计入消费量；Policy 与 HTTP 前置拒绝不产生工具消费。等待状态前均先执行安全清理。

| 错误码与确定性条件 | Task transition | 自动重试 | 预算 | Lease | 授权影响 | 用户操作 | 自动反馈 LLM |
|---|---|---|---|---|---|---|---|
| `INVALID_ACTION`：本 Run 无效响应次数小于固定上限 | 保持主动状态 | 是，最多至上限 | 是，LLM attempt | 保持 | 不失效 | 无 | 是 |
| `INVALID_ACTION`：次数达到固定上限 | `FAILED` | 否 | 是 | 清理后释放 | 未消费审批失去执行用途 | 查看报告 | 否 |
| `BLOCKED_POLICY_ERROR` | `BLOCKED` | 否 | action proposal 计数 | 清理后释放 | 当前 action 不获授权；审批不可覆盖 | 修复可信配置后 `continue_task` | 否 |
| `DENIED_CAPABILITY` | 当前主动状态不变；被拒 action 结束 | 否 | action proposal 计数 | 保持 | 当前 action 永久拒绝 | 无 | 是，仅反馈拒绝事实 |
| `BLOCKED_UNSUPPORTED_CAPABILITY` | `BLOCKED` | 否 | action proposal 计数 | 清理后释放 | 当前 action 失效；Plan 修订 | 修改任务目标后 `continue_task` | 否 |
| `APPROVAL_REQUIRED`：Plan | `AWAITING_PLAN_APPROVAL` | 否 | 否 | 清理后释放 | 等待 Plan Approval | `approve_plan/reject_plan` | 否 |
| `APPROVAL_REQUIRED`：High-risk Action | `AWAITING_ACTION_APPROVAL` | 否 | action proposal 计数 | 清理后释放 | Internal Operation 根据原 Tool Action 创建绑定审批 | `approve_action/reject_action` | 否 |
| `APPROVAL_REQUIRED`：Apply | 保持 `READY_TO_APPLY` | 否 | 否 | 不获取 | 等待 Apply Confirmation | `confirm_apply/reject_apply` | 否 |
| `APPROVAL_CONFLICT` | 状态不变 | 否 | 否 | 不变 | 提交的旧授权不生效 | 刷新快照后重新提交 | 否 |
| `BUDGET_REAPPROVAL_REQUIRED` | `AWAITING_BUDGET_APPROVAL` | 否 | 记录当前消费 | 清理后释放 | RunLimits 确定性创建请求；旧 Budget Version 保持 | `approve_budget_extension/reject_budget_extension` | 否 |
| `BUDGET_EXTENSION_REJECTED` | `BLOCKED` | 否 | 否 | 释放 | 扩展请求失效；旧预算保留 | `submit_clarification` 缩小目标后 `continue_task` | 否 |
| `HARD_LIMIT_REACHED` | `FAILED` | 否 | 是 | 清理后释放 | 普通审批不可提升；未消费审批失去执行用途 | 查看报告 | 否 |
| `EXECUTION_SLOT_BUSY` | 状态不变 | 否 | 否 | 当前任务未获取 | 不失效 | 稍后 `continue_task` | 否 |
| `PROVIDER_LOCKED` | `AWAITING_PROVIDER_UNLOCK` | 否 | 否 | 进入状态前安全释放，等待期间不持有 | 不失效 | 以 `serve --unlock` 重启后 `continue_task` | 否 |
| `PROVIDER_UNAVAILABLE`：固定 endpoint 的暂时连接/超时且配置校验通过 | `BLOCKED` | 否 | 是，Provider attempt | 清理后释放 | Plan/Contract 保留 | Provider 恢复后 `continue_task` | 否 |
| `PROVIDER_CONFIGURATION_ERROR`：endpoint/provider/凭据配置校验失败 | `BLOCKED` | 否 | 否 | 进入状态前安全释放，等待期间不持有 | Plan/Contract 保留 | 修复可信配置并重启后 `continue_task` | 否 |
| `PROVIDER_RESPONSE_INVALID`：次数小于无效响应上限 | 保持主动状态 | 是，最多至上限 | 是 | 保持 | 不失效 | 无 | 是 |
| `PROVIDER_RESPONSE_INVALID`：次数达到上限 | `FAILED` | 否 | 是 | 清理后释放 | 未消费审批失去执行用途 | 查看报告 | 否 |
| `CONTEXT_EXPORT_DENIED` | `BLOCKED` | 否 | 否 | 清理后释放 | 当前 Plan 需修订；相关审批失效 | 提交澄清后 `continue_task` | 否 |
| `PATH_POLICY_VIOLATION` | 保持主动状态；当前 action 失败 | 否 | action proposal 计数 | 保持至安全停点 | 当前 action 永久拒绝 | 无 | 是，仅反馈拒绝事实 |
| `FILE_CONFLICT`：Task Workspace expected digest 不匹配 | `INVESTIGATING` | 否 | tool attempt 计数 | 保持 | 当前 action 与相关审批失效 | 无 | 是，反馈重新调查 |
| `OUTPUT_LIMIT`：只读/日志输出达到软截断限额 | 保持当前状态 | 否 | 是 | 保持 | 不失效 | 无 | 是，携带截断标记 |
| `OUTPUT_LIMIT`：命令达到硬输出上限 | `FAILED` | 否 | 是 | 清理后释放 | 未消费审批失去执行用途 | 查看报告 | 否 |
| `BLOCKED_MISSING_DEPENDENCY` | `BLOCKED` | 否 | preflight 计数 | 清理后释放 | Plan/Contract 保留；环境证据失效 | 修复环境后 `continue_task` | 否 |
| `DOCKER_UNAVAILABLE` | `BLOCKED` | 否 | 否 | 进入状态前安全释放，等待期间不持有 | Plan/Contract 保留；环境证据失效 | doctor 通过后 `continue_task` | 否 |
| `IMAGE_NOT_AVAILABLE` | `BLOCKED`，reason=`DOCKER_UNAVAILABLE` | 否 | 否 | 进入状态前安全释放，等待期间不持有 | Plan/Contract 保留；环境证据失效 | 管理员准备固定镜像后 `continue_task` | 否 |
| `CREATE_FAILED` | `FAILED` | 否 | command attempt 计数 | 清理复检后释放 | 未消费审批失去执行用途 | 新 Run 重试 | 否 |
| `START_FAILED` | `FAILED` | 否 | command attempt 计数 | 清理复检后释放 | 未消费审批失去执行用途 | 新 Run 重试 | 否 |
| `COMMAND_FAILED` | `EXECUTING` | 否（由下一 LLM action 决定） | 是 | 保持 | 不失效 | 无 | 是 |
| `TIMED_OUT` | `EXECUTING` | 否（由下一 LLM action 决定） | 是 | stop/kill/rm 成功后保持 | 不失效 | 无 | 是 |
| `CANCELLED` | `CANCELLED` | 否 | 已开始 attempt 计数 | 安全清理后释放 | 未消费审批失去执行用途 | 无 | 否 |
| `RESOURCE_LIMIT` | `FAILED` | 否 | 是 | 清理复检后释放 | 未消费审批失去执行用途 | 调整可信硬配置需新 Run | 否 |
| `CLEANUP_FAILED` | `RECOVERY_REQUIRED` | 否 | 是 | 保留恢复优先权 | 所有新执行授权暂停 | `request_recovery` | 否 |
| `CHANGESET_STALE` | `READY_TO_APPLY` | 否 | 否 | 进入状态前安全释放，等待期间不持有 | 旧 Apply Confirmation 失效 | 刷新 diff 后提交 Apply Governance Command | 否 |
| `APPLY_CONFLICT` | `BLOCKED` | 否 | apply attempt 计数 | 释放 | Change Set、Apply Confirmation 失效；Plan 需重新调查 | `continue_task` | 否 |
| `APPLY_FAILED` | `ROLLING_BACK` | 否 | apply attempt 计数 | 保持 | Apply Confirmation 已消费 | 无，自动回滚 | 否 |
| `ROLLBACK_FAILED` | `RECOVERY_REQUIRED` | 否 | rollback attempt 计数 | 保留恢复优先权 | 新执行授权暂停 | `request_recovery` | 否 |
| `PERSISTENCE_FAILED`：尚未开始对应外部副作用 | `BLOCKED`，reason=`PERSISTENCE_FAILED` | 否 | 否 | 清理后释放 | 当前转换未生效；审批未消费 | 修复存储后 `continue_task` | 否 |
| `PERSISTENCE_AFTER_SIDE_EFFECT_FAILED`：外部副作用可能已开始 | `RECOVERY_REQUIRED` | 否 | 已开始 attempt 计数 | 保留恢复优先权 | 新执行授权暂停 | `request_recovery` | 否 |
| `MIGRATION_FAILED` | 服务写功能 blocked，不改变既有 Task State | 否 | 否 | 不创建 | 所有写命令禁用 | 修复 migration 后重启 | 否 |
| `CREDENTIAL_ERROR` | Provider runtime=`error`；需 Provider 的任务到 `AWAITING_PROVIDER_UNLOCK` | 否 | 否 | 需 Provider 时不获取 | 不改变任务 Provider 绑定 | 修复凭据后重启 | 否 |
| `USER_ACCEPTANCE_REJECTED` | `BLOCKED` | 否 | 否 | 释放 | 当前 Contract 的 Apply 资格失效 | 提交澄清后 `continue_task` | 否 |
| `RECOVERY_REQUIRED` | `RECOVERY_REQUIRED` | 否 | 否 | 保留恢复优先权 | 新执行授权暂停 | `request_recovery` | 否 |

PolicyDecision 严格为 `ALLOW/REQUIRE_APPROVAL/DENY/BLOCKED_POLICY_ERROR`；reason code 严格为本附录用于 Policy 或 Task 阻塞解释的代码；Task State 严格为附录 B.1 集合。三者不得共享字段或相互替代。

# 附录 F：文件类型支持矩阵

| 类型/仓库状态 | Baseline | Workspace 修改 | Change Set/写回 |
|---|---:|---:|---:|
| 普通 tracked 文件 | 支持 | 支持 | 支持 |
| staged/unstaged tracked 内容 | 支持且属于用户 Baseline | 支持任务副本 | 保护原 index |
| untracked 普通文件 | 支持且属于用户 Baseline | 支持 | 支持 |
| ignored 文件 | 默认排除 | 仅批准 input/ephemeral | 永不进入 Change Set |
| executable bit | 支持 | 支持 | 支持 |
| 仓库内有限相对符号链接 | 经边界检查支持 | 受限支持 | 受限支持 |
| 绝对或越界符号链接 | 拒绝 | 拒绝 | 拒绝 |
| FIFO/socket/device | 拒绝 | 拒绝 | 拒绝 |
| ACL/owner/xattr | 不保证保持 | 不治理 | 不承诺恢复 |
| submodule 修改 | 不支持 | 拒绝 | 拒绝 |
| LFS 特殊操作 | 不支持 | 拒绝 | 拒绝 |
| sparse checkout | 不支持 | 拒绝 | 拒绝 |
| 嵌套仓库 | 不支持 | 拒绝 | 拒绝 |
| merge/rebase/cherry-pick/bisect 中间状态 | 任务启动拒绝 | 不适用 | 不适用 |

# 附录 G：Python/Node Profile 能力矩阵

| 能力 | Python profile | Node.js/TypeScript profile |
|---|---|---|
| 固定运行时 | Python 3.12 | Node.js 20 |
| 识别文件 | `pyproject.toml`、`requirements.txt` | `package.json`、`package-lock.json` |
| 必需验证 | `pytest` | `npm test` |
| 可用附加验证 | `ruff` | 固定 `lint`、`build`、`typecheck` script 类别 |
| 包管理器安装 | 不支持 | 不支持 |
| 网络 | `none` | `none` |
| 依赖前提 | profile 已提供或仓库离线可运行 | profile 已提供或仓库离线可运行 |
| 项目布局 | 单根项目 | 单根 package；无 workspace |
| 深度验收 | 完整主贡献测试矩阵 | 一条完整路径和一次失败反馈 |
| 明确排除 | Conda、完整 Poetry、复杂原生依赖、mypy 官方验证 | pnpm/Yarn/Bun、workspace、长期服务、浏览器集群 |

# 附录 H：三项确定性演示与 Planned Evidence Category Matrix

## H.1 三项确定性演示

| 演示 | 确定性输入 | 预期行为 | 必需证据 |
|---|---|---|---|
| 危险动作阻止 | Mock LLM 提出远程 Git 写入或 Docker socket 动作 | Policy 返回 `DENY`，工具不执行 | Policy 结果、零工具调用、审计事件 |
| 失败反馈改变动作 | Mock Executor 对首个验证动作注入失败，Mock LLM 脚本读取反馈 | 下一 action 与失败前计划动作不同且符合脚本 | action 序列、反馈摘要、预算计数 |
| 事务故障恢复 | 多文件 Change Set，在指定写入点注入故障 | 进入回滚，恢复已写文件，原仓库回到应用前支持状态 | Apply 日志、备份 digest、恢复后 digest、任务状态、审计事件 |

辅助事务证据：dirty worktree fixture 中，在应用确认后并发修改一个目标文件，Harness 必须在首次原仓库写入前返回 `APPLY_CONFLICT`。

## H.2 User Story 验收映射

| User Story | 相关需求范围 | 主要验收场景 |
|---|---|---|
| US-01 | `AGT-006..015`、`POL-008..010`、`ACC-003..005` | 澄清回到暂停的 `INVESTIGATING`；显式继续后完成只读调查、版本化计划和审批等待 |
| US-02 | `ACT-001..008`、`WS-006..014`、`SBX-002..013` | 原仓库不变，Task Workspace 修改并完成固定 profile 验证 |
| US-03 | `POL-015..020`、`WS-015..016`、`ACT-012` | Policy 识别原高风险 Tool Action，Internal Operation 创建审批，验证绑定、失效、一次消费和零越权副作用 |
| US-04 | `ACC-001..009`、`TXN-005..018` | required 条件、Change Set digest、冲突复检和 Apply Confirmation |
| US-05 | `TXN-009..019`、`PST-018..024` | 注入写回故障，回滚/恢复证据和明确终态 |
| US-06 | `CRD-005..013`、附录 B.2、附录 E | Provider、Docker、依赖阻塞的 reason 与下一命令 |

## H.3 Planned Evidence Category Matrix

证据类别：UT=离线单元测试，IT=文件/SQLite 集成测试，DT=Docker 集成测试，AT=API/UI 测试，DEMO=确定性演示，DOC=文档/人工检查，COLD=冷启动验证。

下表使用连续 ID 范围压缩重复字段；范围内每一个 ID 均独立继承该行的章节、组件、证据、MVP、课程映射和初始状态。正文中的单条规范句是需求语义来源。

| 需求范围 | 数量 | 主要章节 | 责任组件/关注面 | 验收证据 | MVP | 课程要求映射 | Implementation Status |
|---|---:|---|---|---|---:|---|---|
| `GEN-001..010` | 10 | 1,2,5 | 产品边界、总体架构、配置治理 | DOC, COLD | 是 | 产品定位、六维 Harness | PLANNED |
| `SEC-001..015` | 15 | 3,4,7,15,16 | Trust Boundary、Context Governance、Provider Boundary | UT, DT, DOC | 是 | 安全边界、API Key、风险说明 | PLANNED |
| `AGT-001..015` | 15 | 5,6,7 | Agent Core、Context Builder、LLM Adapter | UT, IT, DEMO | 是 | 自研 loop、Mock LLM、反馈闭环 | PLANNED |
| `ACT-001..012` | 12 | 8 | Action Schema、Tool Layer、Command Boundary | UT, IT | 是 | 结构化工具、确定性动作 | PLANNED |
| `POL-001..024` | 24 | 4,6,9 | Policy Engine、四类授权、RunLimits | UT, DEMO | 是 | 危险动作阻止、治理主维度 | PLANNED |
| `ACC-001..009` | 9 | 4,10 | Acceptance Evaluator | UT, IT | 是 | 可验证完成判定 | PLANNED |
| `WS-001..016` | 16 | 4,8,11 | Workspace、Manifest、Synthetic Git、Sandbox Input | UT, IT | 是 | 本地仓库工具与记忆 | PLANNED |
| `SBX-001..013` | 13 | 5,12 | Sandbox Profile、Docker Executor | UT, DT | 是 | 隔离执行、正式运行环境 | PLANNED |
| `TXN-001..019` | 19 | 4,13,14 | Change Set、Apply Coordinator、Apply Phase | UT, IT, DEMO | 是 | 机制丰富主维度、故障恢复 | PLANNED |
| `PST-001..028` | 28 | 4,5,6,14,16 | HarnessStore、Audit、Lease、Recovery、Blocked Reason | UT, IT, AT | 是 | 记忆、审计、可恢复性 | PLANNED |
| `API-001..010` | 10 | 5,15 | FastAPI、SSE、WebUI、Governance Command | UT, AT | 是 | WebUI 与可访问 URL | PLANNED |
| `CRD-001..013` | 13 | 15 | Credential Store、CLI、Provider Runtime | UT, IT, DOC | 是 | 安全 API Key 管理 | PLANNED |
| `TST-001..008` | 8 | 17 | Test Harness、Fixtures、CI Evidence | CI, DEMO, COLD | 是 | 三项演示、Mock 离线测试 | PLANNED |
| `DST-001..005` | 5 | 17 | Packaging、Doctor、Runtime Distribution | DOC, COLD | 是 | 正式分发方式 | PLANNED |
| `PRC-001..010` | 10 | 1,17,18 | Change Control、Development Process | DOC, CI, process evidence | 是 | 文档、unit-test、Superpowers/TDD/worktree/subagent/评审 | PLANNED |

每条范围内 ID 均对应正文中唯一的规范性需求。本矩阵只规划 evidence category，不是逐需求 Verification ID 索引。后续 `PLAN.md` 必须为每项需求建立独立 Planned Verification ID，并可将 Implementation Status 更新为 `IN_PROGRESS`、`IMPLEMENTED`、`VERIFIED` 或 `BLOCKED`；状态变化不得修改需求文本。Stretch goals 当前没有规范 ID，也不进入本矩阵的 MVP 强制验收计数。
